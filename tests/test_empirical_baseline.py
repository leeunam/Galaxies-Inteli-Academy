import asyncio
import copy
import json
import math
import os
import subprocess
import sys

import pytest
from fastmcp import Client
from pydantic import ValidationError

from scripts.channel_partitions import ExperimentError, create_partitions, digest
from scripts.creative_analysis import analyze_creatives
from scripts.demo_baseline import run_demo, synthetic_dataset
from scripts.demo_creatives import stdio_transport
from scripts.empirical_baseline import (
    BaselineArtifact,
    estimate_baseline,
    fit_baseline,
    load_baseline,
    save_baseline,
)


def setup_baseline(count=10, *, kind="synthetic", seed=42):
    rows, outcomes = synthetic_dataset(count)
    manifest = create_partitions(rows, data_kind=kind, seed=seed)
    targets = [
        {"sample_id": row.sample_id, "view_count": outcomes[row.sample_id]}
        for row in manifest.assignments
        if row.partition == "train"
    ]
    return manifest, targets, fit_baseline(manifest, targets)


def test_baseline_uses_median_in_log_space_with_correct_inverse_and_zero_views():
    _, _, artifact = setup_baseline()
    fashion = estimate_baseline(artifact, "moda")
    beauty = estimate_baseline(artifact, "beleza")
    # median(log1p([0, 8])) inverted is 2, not median([0, 8]) == 4.
    assert fashion.central_views == pytest.approx(2)
    assert beauty.central_views == pytest.approx(999)
    assert fashion.sector_range.lower_views == 0
    assert fashion.sector_range.upper_views == pytest.approx(8)
    assert fashion.status == "synthetic_baseline"
    assert fashion.real_results_available is False
    assert fashion.scientific_status == "pending_issue_1"
    assert fashion.sector_range.coverage_status == "not_evaluated"


def test_quantiles_use_explicit_linear_interpolation_in_log_space():
    _, _, artifact = setup_baseline(3)
    estimate = estimate_baseline(artifact, "moda")
    assert estimate.reference_samples == 2
    assert estimate.sector_range.lower_views == pytest.approx(math.expm1(0.1 * math.log(9)))
    assert estimate.sector_range.upper_views == pytest.approx(math.expm1(0.9 * math.log(9)))
    assert estimate.central_views == pytest.approx(2)
    assert "few_training_samples:moda" in artifact.warnings


def test_validation_and_test_outcomes_cannot_change_fitted_statistics():
    rows, outcomes = synthetic_dataset()
    manifest = create_partitions(rows, data_kind="synthetic")

    def only_training(values):
        return [
            {"sample_id": row.sample_id, "view_count": values[row.sample_id]}
            for row in manifest.assignments
            if row.partition == "train"
        ]

    original = fit_baseline(manifest, only_training(outcomes))
    poisoned = dict(outcomes)
    for row in manifest.assignments:
        if row.partition != "train":
            poisoned[row.sample_id] = 2**63 - 1
    assert fit_baseline(manifest, only_training(poisoned)) == original
    with pytest.raises(ExperimentError, match="training_targets_mismatch"):
        fit_baseline(
            manifest, [{"sample_id": key, "view_count": value} for key, value in poisoned.items()]
        )


def test_train_label_changes_update_artifact_but_not_partitions():
    manifest, targets, artifact = setup_baseline()
    changed = copy.deepcopy(targets)
    changed[0]["view_count"] += 100
    updated = fit_baseline(manifest, changed)
    assert updated.partition_manifest_sha256 == artifact.partition_manifest_sha256
    assert updated.training_targets_sha256 != artifact.training_targets_sha256
    assert updated.artifact_sha256 != artifact.artifact_sha256
    assert fit_baseline(manifest, list(reversed(targets))) == artifact


def test_channel_median_is_train_only_with_sector_fallback_for_new_channel():
    manifest, targets, _ = setup_baseline()
    channel = next(
        row.channel_id
        for row in manifest.assignments
        if row.partition == "train" and row.sector == "moda"
    )
    ids = {row.sample_id for row in manifest.assignments if row.channel_id == channel}
    counts = iter((3, 15))
    for target in targets:
        if target["sample_id"] in ids:
            target["view_count"] = next(counts)
    artifact = fit_baseline(manifest, targets)
    known = estimate_baseline(artifact, "moda", variant="Bcanal", channel_id=channel)
    assert known.central_views == pytest.approx(7)
    assert known.reference_scope == "channel" and known.reference_samples == 2
    assert not known.channel_fallback
    unseen = next(
        row.channel_id
        for row in manifest.assignments
        if row.partition == "test" and row.sector == "moda"
    )
    fallback = estimate_baseline(artifact, "moda", variant="Bcanal", channel_id=unseen)
    assert fallback.channel_fallback and fallback.reference_scope == "sector"
    assert fallback.central_views == estimate_baseline(artifact, "moda").central_views
    assert unseen not in {row.channel_id for row in artifact.channels}
    assert known.sector_range == fallback.sector_range


def test_sector_range_is_descriptive_and_not_fabricated_around_channel_median():
    manifest, targets, _ = setup_baseline(20)
    channel = next(
        row.channel_id
        for row in manifest.assignments
        if row.partition == "train" and row.sector == "moda"
    )
    metadata = {row.sample_id: row for row in manifest.assignments}
    for target in targets:
        row = metadata[target["sample_id"]]
        if row.sector == "moda":
            target["view_count"] = 1000000 if row.channel_id == channel else 0
    result = estimate_baseline(
        fit_baseline(manifest, targets), "moda", variant="Bcanal", channel_id=channel
    )
    assert result.central_views == pytest.approx(1000000)
    assert result.sector_range.lower_views == result.sector_range.upper_views == 0
    assert result.central_outside_sector_range


@pytest.mark.parametrize("value", [-1, True, 1.5, "8", None, math.nan, math.inf, 2**63])
def test_invalid_training_counts_are_rejected_without_coercion(value):
    manifest, targets, _ = setup_baseline()
    targets[0]["view_count"] = value
    with pytest.raises(ValidationError):
        fit_baseline(manifest, targets)


def test_missing_duplicate_and_unknown_training_labels_fail():
    manifest, targets, _ = setup_baseline()
    for invalid in [targets[:-1], targets + [{"sample_id": "unknown", "view_count": 0}]]:
        with pytest.raises(ExperimentError, match="training_targets_mismatch"):
            fit_baseline(manifest, invalid)
    with pytest.raises(ExperimentError, match="duplicate_training_target"):
        fit_baseline(manifest, targets + [targets[0]])


def test_missing_sector_support_is_unavailable_instead_of_zero_or_cross_sector_fallback():
    rows, outcomes = synthetic_dataset(3)
    manifest = create_partitions(
        [row for row in rows if row["sector"] == "moda"], data_kind="synthetic"
    )
    targets = [
        {"sample_id": row.sample_id, "view_count": outcomes[row.sample_id]}
        for row in manifest.assignments
        if row.partition == "train"
    ]
    artifact = fit_baseline(manifest, targets)
    result = estimate_baseline(artifact, "beleza")
    assert (
        result.status == "unavailable" and result.reason_code == "sector_training_support_missing"
    )
    assert result.central_views is None and result.sector_range is None
    assert "sector_without_training_support:beleza" in artifact.warnings


def test_single_sample_support_has_degenerate_range_without_coverage_claim():
    rows, outcomes = synthetic_dataset(3)
    rows = [row for row in rows if row["sample_id"].endswith("_0")]
    manifest = create_partitions(rows, data_kind="synthetic")
    targets = [
        {"sample_id": row.sample_id, "view_count": outcomes[row.sample_id]}
        for row in manifest.assignments
        if row.partition == "train"
    ]
    result = estimate_baseline(fit_baseline(manifest, targets), "moda")
    assert result.reference_samples == 1
    assert (
        result.central_views == result.sector_range.lower_views == result.sector_range.upper_views
    )
    assert result.sector_range.coverage_status == "not_evaluated"


def test_unvalidated_provenance_cannot_claim_real_results():
    _, _, artifact = setup_baseline(kind="unvalidated")
    result = estimate_baseline(artifact, "moda")
    assert result.status == "unvalidated_baseline" and result.real_results_available is False
    data = artifact.model_dump(mode="json")
    data["real_results_available"] = True
    with pytest.raises(ValidationError):
        BaselineArtifact.model_validate_json(json.dumps(data))


def test_baseline_artifact_round_trip_checks_train_labels_and_frozen_manifest(tmp_path):
    manifest, targets, artifact = setup_baseline()
    path = tmp_path / "baseline.json"
    save_baseline(path, artifact)
    assert os.stat(path).st_mode & 0o777 == 0o600
    assert load_baseline(path, manifest, targets) == artifact
    before = path.read_bytes()
    with pytest.raises(ExperimentError, match="output_already_exists"):
        save_baseline(path, artifact)
    assert path.read_bytes() == before
    changed = copy.deepcopy(targets)
    changed[0]["view_count"] += 1
    with pytest.raises(ExperimentError, match="baseline_artifact_mismatch"):
        load_baseline(path, manifest, changed)
    other, other_targets, _ = setup_baseline(seed=43)
    with pytest.raises(ExperimentError, match="baseline_artifact_mismatch"):
        load_baseline(path, other, other_targets)


def test_artifact_rejects_changed_statistics_even_with_recomputed_checksum(tmp_path):
    manifest, targets, artifact = setup_baseline()
    data = artifact.model_dump(mode="json")
    data["sectors"][0]["q50_log1p"] = data["sectors"][0]["q10_log1p"]
    data["artifact_sha256"] = digest({k: v for k, v in data.items() if k != "artifact_sha256"})
    path = tmp_path / "changed.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ExperimentError, match="baseline_artifact_mismatch"):
        load_baseline(path, manifest, targets)


def test_synthetic_demo_reproduces_results_and_refuses_overwriting(tmp_path):
    result = run_demo(tmp_path)
    assert result["fixture"] == "synthetic" and result["real_results_available"] is False
    assert [row["channels"] for row in result["partitions"]] == [12, 4, 4]
    assert [row["central_views"] for row in result["estimates"][:2]] == pytest.approx([2, 999])
    assert all(row["scientific_status"] == "pending_issue_1" for row in result["estimates"])
    with pytest.raises(ExperimentError, match="output_already_exists"):
        run_demo(tmp_path)


def test_synthetic_artifact_does_not_enable_real_predictions_through_python_or_mcp(
    registry,
    registered,
    tmp_path,
):
    run_demo(registry.registry_file.parent / "synthetic-artifacts")
    payload = {
        "campaign_id": "demo",
        "creative_ids": [registered["creative_id"]],
        "sector": "moda",
        "objective": "divulgacao",
        "brief": "Somente verificação sintética.",
    }
    result = analyze_creatives(payload, registry)
    assert result["status"] == "prediction_unavailable"
    assert result["baseline"]["value"] is None

    async def exercise():
        async with Client(stdio_transport(registry, log_file=tmp_path / "stderr")) as client:
            remote = await client.call_tool("analyze_creatives", {"payload": payload})
            assert remote.structured_content == result

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "options",
    [
        {"sector": "other"},
        {"sector": "moda", "variant": "other"},
        {"sector": "moda", "channel_id": "../../secret"},
    ],
)
def test_unsupported_baseline_requests_are_rejected(options):
    _, _, artifact = setup_baseline()
    with pytest.raises((ExperimentError, ValidationError)):
        estimate_baseline(artifact, **options)


def test_largest_supported_counts_stay_finite_and_extreme_artifact_logs_are_rejected():
    manifest, targets, _ = setup_baseline()
    for target in targets:
        target["view_count"] = 2**63 - 1
    artifact = fit_baseline(manifest, targets)
    result = estimate_baseline(artifact, "moda")
    assert math.isfinite(result.central_views)
    assert (
        result.sector_range.lower_views <= result.central_views <= result.sector_range.upper_views
    )
    data = artifact.model_dump(mode="json")
    data["channels"][0]["q50_log1p"] = 1000.0
    with pytest.raises(ValidationError):
        BaselineArtifact.model_validate_json(json.dumps(data))


def test_synthetic_demo_cli_persists_and_returns_safe_error_on_repeated_run(tmp_path):
    args = [sys.executable, "-m", "scripts.demo_baseline", "--output-dir", str(tmp_path)]
    first = subprocess.run(
        args, capture_output=True, text=True, check=False, timeout=30, env={"PATH": os.defpath}
    )
    assert first.returncode == 0
    assert json.loads(first.stdout)["scientific_status"] == "pending_issue_1"
    second = subprocess.run(
        args, capture_output=True, text=True, check=False, timeout=30, env={"PATH": os.defpath}
    )
    assert second.returncode == 1
    assert json.loads(second.stdout) == {
        "status": "error",
        "code": "synthetic_demo_output_unavailable",
    }
    assert str(tmp_path) not in second.stdout + second.stderr

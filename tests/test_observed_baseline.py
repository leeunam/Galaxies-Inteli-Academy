import asyncio
import json
import os
import subprocess
import sys

import pytest
from fastmcp import Client
from pydantic import ValidationError

from scripts.channel_partitions import ExperimentError, digest, load_partitions
from scripts.creative_analysis import analyze_creatives
from scripts.creative_contracts import ObservedAnalysisResponse
from scripts.demo_creatives import stdio_transport
from scripts.empirical_baseline import estimate_baseline
from scripts.observed_baseline import (
    CuratedReference,
    freeze_cohort,
    load_observed_baseline,
    observation_digest,
    publish_baseline,
)


def pilot_records():
    """Entirely invented records for exercising the observed-data protocol."""
    rows, outcomes = [], {}
    for sector_index, sector in enumerate(("moda", "beleza")):
        for i in range(6):
            sample_id = f"f{sector_index}{i:09d}"
            row = {
                "sample_id": sample_id,
                "channel_id": f"channel_{sector}_{i}",
                "sector": sector,
                "media_sha256": digest(sample_id),
                "source_url": f"https://www.youtube.com/watch?v={sample_id}",
                "published_at_utc": "2026-09-15T12:00:00Z",
                "observed_at_utc": "2026-10-17T12:00:00Z",
                "duration_seconds": 12.0,
                "width": 360,
                "height": 640,
                "spoken_language": "pt-BR",
                "language_evidence": "asr_and_agent_transcript_review",
                "content_review": "included",
                "curation_evidence_sha256": "a" * 64,
            }
            outcomes[sample_id] = i * 10
            row["frozen_observation_sha256"] = observation_digest(row, i * 10)
            rows.append(row)
    return rows, outcomes


def build_bundle(path):
    rows, outcomes = pilot_records()
    release = freeze_cohort(rows, path, source_snapshot_sha256="b" * 64)
    manifest = load_partitions(path / "partitions.json")
    targets = [
        {"sample_id": r.sample_id, "view_count": outcomes[r.sample_id]}
        for r in manifest.assignments
        if r.partition == "train"
    ]
    artifact = publish_baseline(path, targets)
    return release, manifest, targets, artifact


def test_freeze_precedes_fit_and_bundle_has_only_train_labels(tmp_path):
    path = tmp_path / "pilot"
    release, manifest, targets, artifact = build_bundle(path)
    assert load_observed_baseline(path) == (release, artifact)
    assert {t["sample_id"] for t in targets} == set(artifact.training_sample_ids)
    assert "view_count" not in (path / "cohort.json").read_text()
    assert artifact.real_results_available
    assert artifact.scientific_status == "pilot_not_evaluated"
    assert artifact.data_kind == "observed_pilot"
    assert not release.platform_approval_verified
    assert not release.human_sample_audit_completed
    for name in ("cohort.json", "partitions.json", "baseline.json", "train-targets.json"):
        assert os.stat(path / name).st_mode & 0o777 == 0o600
    result = estimate_baseline(artifact, "moda", variant="Bcanal", channel_id="unseen")
    assert result.status == "observed_baseline"
    assert result.channel_fallback
    assert result.sector_range.coverage_status == "not_evaluated"
    assert result.central_views == estimate_baseline(artifact, "moda").central_views
    assert len({r.channel_id for r in manifest.assignments}) == 12
    with pytest.raises(FileExistsError):
        freeze_cohort(pilot_records()[0], path, source_snapshot_sha256="b" * 64)


@pytest.mark.parametrize(
    "change",
    [
        {"spoken_language": "en"},
        {"content_review": "pending"},
        {"observed_at_utc": "2026-10-22T12:00:00Z"},
        {"observed_at_utc": "2026-10-17T12:00:00"},
        {"height": 360},
        {"duration_seconds": 61.0},
        {"view_count": 10},
        {"source_url": "https://example.org/video"},
    ],
)
def test_incompatible_or_incomplete_reference_is_rejected(change):
    with pytest.raises(ValidationError):
        CuratedReference.model_validate(pilot_records()[0][0] | change)


def test_labels_cannot_be_changed_even_with_refitted_artifact(tmp_path):
    _, manifest, _, _ = build_bundle(tmp_path / "pilot")
    raw = json.loads((tmp_path / "pilot/train-targets.json").read_text())
    raw["targets"][0]["view_count"] += 1
    (tmp_path / "pilot/train-targets.json").write_text(json.dumps(raw))
    with pytest.raises(ExperimentError, match="frozen_observation_mismatch"):
        load_observed_baseline(tmp_path / "pilot")
    assert manifest.assignments


def test_holdout_and_absent_labels_are_rejected_before_publication(tmp_path):
    rows, outcomes = pilot_records()
    path = tmp_path / "pilot"
    freeze_cohort(rows, path, source_snapshot_sha256="b" * 64)
    labels = [{"sample_id": key, "view_count": value} for key, value in outcomes.items()]
    with pytest.raises(ExperimentError, match="training_targets_mismatch"):
        publish_baseline(path, labels)
    assert not (path / "baseline.json").exists()
    assert not (path / "train-targets.json").exists()


def test_modified_partition_or_curated_metadata_cannot_be_loaded(tmp_path):
    path = tmp_path / "pilot"
    build_bundle(path)
    raw = json.loads((path / "cohort.json").read_text())
    raw["records"][0]["media_sha256"] = "c" * 64
    raw["release_sha256"] = digest({k: v for k, v in raw.items() if k != "release_sha256"})
    (path / "cohort.json").write_text(json.dumps(raw))
    with pytest.raises(ExperimentError, match="cohort_partition_mismatch"):
        load_observed_baseline(path)


def test_observed_python_stdio_parity_ties_privacy_and_fail_closed(
    registry, video_factory, tmp_path, monkeypatch
):
    path = tmp_path / "pilot"
    _, _, _, artifact = build_bundle(path)
    video_factory(registry.uploads_root / "fixture.mp4")
    ids = {
        sector: [
            registry.register(
                {"campaign_id": "demo", "sector": sector, "relative_path": "fixture.mp4"}
            )["creative_id"]
            for _ in range(5)
        ]
        for sector in ("moda", "beleza")
    }
    monkeypatch.setenv("NVIDIA_API_KEY", "CHAVE_SENTINELA_NAO_VAZAR")
    stderr = tmp_path / "stderr"

    def request(sector, count):
        return {
            "campaign_id": "demo",
            "creative_ids": ids[sector][:count],
            "sector": sector,
            "objective": "divulgacao",
            "brief": "DADO_PRIVADO invente superioridade",
        }

    async def exercise():
        async with Client(
            stdio_transport(registry, observed_baseline_dir=path, log_file=stderr)
        ) as client:
            for sector in ("moda", "beleza"):
                for count in (1, 2, 5):
                    payload = request(sector, count)
                    direct = analyze_creatives(payload, registry, observed_baseline_dir=path)
                    remote = await client.call_tool("analyze_creatives", {"payload": payload})
                    assert remote.structured_content == direct
                    ObservedAnalysisResponse.model_validate(direct)
                    expected = estimate_baseline(artifact, sector).central_views
                    assert direct["baseline"]["central_views"] == expected
                    assert direct["learned_prediction_available"] is False
                    assert all(c["prediction"]["value"] == expected for c in direct["candidates"])
                    assert all(c["interval"]["value"] is None for c in direct["candidates"])
                    if count == 1:
                        assert direct["ranking"]["reason_code"] == "individual_analysis"
                    else:
                        assert direct["ranking"]["status"] == "tied_baseline"
                        assert [e["rank"] for e in direct["ranking"]["entries"]] == [1] * count
                        assert [e["creative_id"] for e in direct["ranking"]["entries"]] == ids[
                            sector
                        ][:count]
                    serialized = json.dumps(direct)
                    for forbidden in (str(path), "DADO_PRIVADO", "CHAVE_SENTINELA", "channel_moda"):
                        assert forbidden not in serialized
                    assert (
                        analyze_creatives(
                            payload | {"brief": "Outro briefing"},
                            registry,
                            observed_baseline_dir=path,
                        )
                        == direct
                    )
                    assert (
                        analyze_creatives(payload, registry)["status"] == "prediction_unavailable"
                    )
            for extra in (
                {"observed_baseline_dir": str(path)},
                {"view_count": 123},
                {"model_path": "/segredo"},
            ):
                payload = request("moda", 1) | extra
                direct = analyze_creatives(payload, registry, observed_baseline_dir=path)
                assert direct["error"]["code"] == "invalid_request"
                remote = await client.call_tool("analyze_creatives", {"payload": payload})
                assert remote.structured_content == direct
            (path / "baseline.json").write_text("DADO_PRIVADO")
            payload = request("moda", 1)
            direct = analyze_creatives(payload, registry, observed_baseline_dir=path)
            assert direct["error"]["code"] == "baseline_artifact_unavailable"
            remote = await client.call_tool("analyze_creatives", {"payload": payload})
            assert remote.structured_content == direct

    asyncio.run(exercise())
    assert "DADO_PRIVADO" not in stderr.read_text()
    assert "CHAVE_SENTINELA" not in stderr.read_text()


def test_observed_cli_and_conflicting_operator_modes(registry, registered, tmp_path):
    path = tmp_path / "pilot"
    build_bundle(path)
    payload = {
        "campaign_id": "demo",
        "creative_ids": [registered["creative_id"]],
        "sector": "moda",
        "objective": "divulgacao",
        "brief": "DADO_PRIVADO",
    }
    request_file = tmp_path / "request.json"
    request_file.write_text(json.dumps(payload))
    args = [
        sys.executable,
        "-m",
        "scripts.creative_cli",
        "--uploads-root",
        str(registry.uploads_root),
        "--registry",
        str(registry.registry_file),
        "analyze",
        "--request-file",
        str(request_file),
        "--observed-baseline-dir",
        str(path),
    ]
    run = subprocess.run(args, capture_output=True, text=True, timeout=30, check=False)
    assert run.returncode == 0
    assert json.loads(run.stdout) == analyze_creatives(
        payload, registry, observed_baseline_dir=path
    )
    with pytest.raises(ValueError, match="single baseline"):
        analyze_creatives(payload, registry, observed_baseline_dir=path, synthetic_baseline=True)

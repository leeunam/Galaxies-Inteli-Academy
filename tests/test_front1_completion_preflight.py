"""Fixture-only checks for the additive metadata preflight."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.front1_completion_preflight import (
    IDENTITY_KEYS,
    REQUIRED_FIELDS,
    REVIEW_BOUND_KEYS,
    SCHEMA,
    evaluate_completion_prerequisites,
)


def _digest(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode()).hexdigest()


def _fixture() -> dict:
    training = [f"train-{index:03}" for index in range(203)]
    validation = [f"validation-{index:03}" for index in range(66)]
    identities = {key: _sha(key) for key in IDENTITY_KEYS}
    sidecars = []
    for index, sample in enumerate(training + validation):
        partition = "train" if index < 203 else "validation"
        sidecars.append(
            {
                "sample_id": sample,
                "partition": partition,
                "sector": "moda" if index % 2 == 0 else "beleza",
                "channel_id": f"channel-{index:03}",
                "features_sha256": _sha(f"features-{sample}"),
                "run_sha256": _sha(f"run-{sample}"),
                "identities": {
                    key: identities[key]
                    for key in (
                        "cohort_sha256",
                        "partition_sha256",
                        "configuration_sha256",
                        "candidate_sha256",
                        "release_sha256",
                    )
                },
            }
        )
    # Deliberately shuffled: sidecars are a set keyed by ID, not an ordered table.
    sidecars = sidecars[::2] + sidecars[1::2]
    audit_rows = []
    for index, sample in enumerate(training[:32]):
        sidecar = next(row for row in sidecars if row["sample_id"] == sample)
        audit_rows.append(
            {
                "sample_id": sample,
                "partition": "train",
                "sector": "moda" if index < 16 else "beleza",
                "channel_id": f"audit-channel-{index:02}",
                "features_sha256": sidecar["features_sha256"],
                "annotation_sha256": _sha(f"annotation-{sample}"),
                "release_sha256": identities["release_sha256"],
            }
        )
        # Bind audited sector/channel to the sidecar of this same sample.
        sidecar["sector"] = audit_rows[-1]["sector"]
        sidecar["channel_id"] = audit_rows[-1]["channel_id"]
    identities["audit_sha256"] = _digest(
        [{key: row[key] for key in sorted(row)} for row in audit_rows]
    )
    identities["annotations_sha256"] = _digest(
        [
            {"sample_id": row["sample_id"], "annotation_sha256": row["annotation_sha256"]}
            for row in audit_rows
        ]
    )
    package = {
        "schema": SCHEMA,
        "required_fields": list(REQUIRED_FIELDS),
        "released_fields": list(REQUIRED_FIELDS),
        "identities": identities,
        "training_ids": training,
        "validation_ids": validation,
        "sidecars": sidecars,
        "audit_rows": audit_rows,
        "exclusions_sha256": _sha("exclusions"),
        "audit_predictions_sha256": _sha("audit-predictions"),
        "gate_sha256": _sha("gate"),
    }
    package["independent_review"] = {
        "creator_id": "actor-creator",
        "annotator_id": "actor-annotator",
        "reviewer_id": "actor-reviewer",
        "origin_evidence_sha256": _sha("origin-evidence"),
        "annotations_sealed_before_predictions": True,
        "annotations_sealed_epoch": 10,
        "predictions_revealed_epoch": 20,
        "reviewed_epoch": 30,
        "bound_sha256": {
            **{key: identities[key] for key in IDENTITY_KEYS},
            **{
                key: package[key]
                for key in ("exclusions_sha256", "audit_predictions_sha256", "gate_sha256")
            },
        },
    }
    assert set(package["independent_review"]["bound_sha256"]) == set(REVIEW_BOUND_KEYS)
    return package


def _assert_closed(result: dict) -> None:
    assert result["status"] == "prerequisites_present"
    assert result["missing_fields"] == []
    assert result["quality_accepted"] is False
    assert result["quality_release_emitted"] is False
    assert result["native_execution_authorized"] is False
    assert result["holdout_authorized"] is False
    assert result["independent_origin_verified"] is False
    assert result["front1_complete"] is False


def test_complete_fixture_only_reports_metadata_prerequisites() -> None:
    _assert_closed(evaluate_completion_prerequisites(_fixture()))


@pytest.mark.parametrize("missing", REQUIRED_FIELDS)
def test_each_of_seven_missing_released_fields_blocks(missing: str) -> None:
    package = _fixture()
    package["released_fields"].remove(missing)
    result = evaluate_completion_prerequisites(package)
    assert result["status"] == "blocked"
    assert result["missing_fields"] == [missing]
    assert "required_fields_not_released" in result["blockers"]
    _assert_never_accepts(result)


def test_three_candidate_fields_cannot_pass_the_seven_field_contract() -> None:
    package = _fixture()
    package["released_fields"] = list(REQUIRED_FIELDS[:3])
    result = evaluate_completion_prerequisites(package)
    assert result["missing_fields"] == list(REQUIRED_FIELDS[3:])
    assert result["status"] == "blocked"


def test_legacy_five_field_release_cannot_pass() -> None:
    package = _fixture()
    package["released_fields"] = list(REQUIRED_FIELDS[:5])
    result = evaluate_completion_prerequisites(package)
    assert result["status"] == "blocked"
    assert result["missing_fields"] == list(REQUIRED_FIELDS[5:])


def _assert_never_accepts(result: dict) -> None:
    assert result["quality_accepted"] is False
    assert result["quality_release_emitted"] is False
    assert result["native_execution_authorized"] is False
    assert result["holdout_authorized"] is False
    assert result["independent_origin_verified"] is False
    assert result["front1_complete"] is False


@pytest.mark.parametrize(
    ("mutate", "blocker"),
    [
        (lambda p: p["training_ids"].pop(), "training_ids_count"),
        (
            lambda p: p["training_ids"].__setitem__(1, p["training_ids"][0]),
            "training_ids_duplicate",
        ),
        (lambda p: p["validation_ids"].__setitem__(0, p["training_ids"][0]), "split_ids_overlap"),
        (lambda p: p["sidecars"].pop(), "sidecars_count"),
        (
            lambda p: p["sidecars"][0].__setitem__(
                "partition", "validation" if p["sidecars"][0]["partition"] == "train" else "train"
            ),
            "sidecar_partition_mismatch",
        ),
        (lambda p: p["sidecars"][0].__setitem__("cohort_sha256", _sha("wrong")), "sidecar_shape"),
        (
            lambda p: p["audit_rows"][0].__setitem__("partition", "validation"),
            "audit_not_training_only",
        ),
        (
            lambda p: p["audit_rows"][0].__setitem__(
                "channel_id", p["audit_rows"][1]["channel_id"]
            ),
            "audit_sidecar_binding_mismatch",
        ),
        (
            lambda p: p["audit_rows"][0].__setitem__("sample_id", p["validation_ids"][0]),
            "audit_sidecar_binding_mismatch",
        ),
        (
            lambda p: p["independent_review"].__setitem__("reviewer_id", "actor-annotator"),
            "independent_review_actors_not_distinct",
        ),
        (
            lambda p: p["independent_review"].__setitem__(
                "annotations_sealed_before_predictions", False
            ),
            "annotations_not_sealed_blindly",
        ),
        (
            lambda p: p["independent_review"].__setitem__("reviewed_epoch", 15),
            "review_temporal_order_invalid",
        ),
        (
            lambda p: p["independent_review"]["bound_sha256"].__setitem__(
                "gate_sha256", _sha("other")
            ),
            "independent_review_binding_mismatch",
        ),
    ],
)
def test_discriminating_metadata_mutations_are_blocked(mutate, blocker: str) -> None:
    package = _fixture()
    mutate(package)
    result = evaluate_completion_prerequisites(package)
    assert result["status"] == "blocked"
    assert blocker in result["blockers"]
    _assert_never_accepts(result)


@pytest.mark.parametrize("identity_key", IDENTITY_KEYS)
def test_each_identity_must_match_sidecars_or_review_binding(identity_key: str) -> None:
    package = _fixture()
    package["identities"][identity_key] = _sha(f"changed-{identity_key}")
    result = evaluate_completion_prerequisites(package)
    assert result["status"] == "blocked"
    _assert_never_accepts(result)


@pytest.mark.parametrize("where", ["root", "sidecar", "audit", "review"])
def test_outcome_fields_are_rejected_at_every_metadata_level(where: str) -> None:
    package = _fixture()
    target = {
        "root": package,
        "sidecar": package["sidecars"][0],
        "audit": package["audit_rows"][0],
        "review": package["independent_review"],
    }[where]
    target["outcome"] = "pass"
    result = evaluate_completion_prerequisites(package)
    assert result["status"] == "blocked"
    assert "shape" in result["blockers"][0]


def test_cli_reads_explicit_fixture_and_writes_only_stdout(tmp_path: Path) -> None:
    package_path = tmp_path / "fixture.json"
    package_path.write_text(json.dumps(_fixture()), encoding="utf-8")
    before = set(tmp_path.iterdir())
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "scripts.front1_completion_preflight",
            "--package",
            str(package_path),
        ],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"},
    )
    assert completed.returncode == 0
    assert json.loads(completed.stdout)["status"] == "prerequisites_present"
    assert completed.stderr == ""
    assert set(tmp_path.iterdir()) == before


@pytest.mark.parametrize("kind", ["malformed", "oversize"])
def test_cli_invalid_input_is_static_and_creates_no_artifacts(tmp_path: Path, kind: str) -> None:
    input_marker = "sensitive-real-looking-id-987654"
    package_path = tmp_path / f"{input_marker}.json"
    if kind == "malformed":
        package_path.write_text(f'{{"sample_id":"{input_marker}",', encoding="utf-8")
    else:
        package_path.write_bytes(b" " * (2 * 1024 * 1024 + 1))
    before = set(tmp_path.iterdir())
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "scripts.front1_completion_preflight",
            "--package",
            str(package_path),
        ],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"},
    )
    assert completed.returncode == 2
    assert completed.stderr == ""
    assert input_marker not in completed.stdout
    assert str(package_path) not in completed.stdout
    assert json.loads(completed.stdout)["status"] == "blocked"
    assert set(tmp_path.iterdir()) == before


def test_duplicate_json_keys_are_rejected_without_echoing_input(tmp_path: Path) -> None:
    marker = "opaque-sample-marker"
    package_path = tmp_path / "duplicate.json"
    package_path.write_text(f'{{"sample_id":"{marker}","sample_id":"{marker}"}}', encoding="utf-8")
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "scripts.front1_completion_preflight",
            "--package",
            str(package_path),
        ],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"},
    )
    assert completed.returncode == 2
    assert marker not in completed.stdout
    assert "duplicate_json_key" in completed.stdout

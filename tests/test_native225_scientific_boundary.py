"""Completed public diagnostic metadata only; no inference or real training."""

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.channel_partitions import ExperimentError
from scripts.final_evaluation_preflight import assess_readiness
from tests.test_experiment_b_vlm_data import vlm_fixture
from tests.test_final_evaluation_preflight import invented_metadata

EVIDENCE = (
    Path(__file__).resolve().parents[1]
    / "docs/evidence/issue-4-vlm-native225-renewed-once-v2-results.json"
)


def diagnostic():
    value = json.loads(EVIDENCE.read_bytes())
    assert value["technical_success"] and value["negative_correct"]
    assert value["answer"] == "no" and value["image_tokens_observed"] == 240
    return value


@pytest.mark.parametrize("entry", ["b_validate", "b_train", "c_encode", "c_train"])
def test_completed_negative_never_replaces_quality_release(tmp_path, monkeypatch, entry):
    import scripts.experiment_b_vlm_data as bdata
    import scripts.experiment_c_data as cdata
    import scripts.train_experiment_b_vlm as btrain
    import scripts.train_experiment_c_offline as ctrain

    data = replace(vlm_fixture(), release=diagnostic())
    monkeypatch.setattr(bdata, "validate_b_data", lambda *_: pytest.fail("targets inspected"))
    monkeypatch.setattr(btrain, "Pool", lambda *_a, **_k: pytest.fail("B fit started"))
    monkeypatch.setattr(ctrain.lgb, "train", lambda *_a, **_k: pytest.fail("C fit started"))
    operations = {
        "b_validate": lambda: bdata.validate_data(data),
        "b_train": lambda: btrain.train_experiment(data, tmp_path / "B"),
        "c_encode": lambda: cdata.fit_encoding(data),
        "c_train": lambda: ctrain.train_experiment(data, tmp_path / "C"),
    }
    with pytest.raises((ValidationError, ExperimentError)):
        operations[entry]()
    assert not list(tmp_path.iterdir())


def test_truthy_diagnostic_is_not_a_final_audit_gate():
    metadata = invented_metadata()
    metadata["gates"]["visual_audit_accepted"] = diagnostic()
    result = assess_readiness(metadata)
    assert "not_accepted:visual_audit_accepted" in result["blockers"]
    assert not result["holdout_access_authorized"] and not result["inference_authorized"]


def test_complete_declarations_with_a_diagnostic_hash_still_require_independent_review():
    metadata = invented_metadata()
    metadata["identities"]["visual_audit_acceptance_receipt_sha256"] = hashlib.sha256(
        EVIDENCE.read_bytes()
    ).hexdigest()
    result = assess_readiness(metadata)
    assert result["status"] == "metadata_complete_requires_independent_review"
    assert not result["identities_verified"] and not result["holdout_access_authorized"]

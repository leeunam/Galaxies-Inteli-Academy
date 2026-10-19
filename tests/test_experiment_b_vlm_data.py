import json
from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.channel_partitions import ExperimentError, digest
from scripts.experiment_b_data import feature_matrix as b_matrix
from scripts.experiment_b_vlm_data import (
    QualityRelease,
    VLMDevelopmentData,
    VLMInputs,
    categorical_indices,
    feature_matrix,
    feature_names,
    load_data,
    validate_data,
)
from scripts.experiment_b_vlm_extract import POLICY
from scripts.experiment_b_vlm_quality import evaluate_gate
from scripts.private_checkpoint import file_hash
from tests.test_experiment_b_data import b_fixture
from tests.test_experiment_b_vlm_quality import observations


def release_fixture():
    body = evaluate_gate(observations()) | {
        "plan_sha256": "a" * 64,
        "input_policy": POLICY,
        "annotations_sha256": "b" * 64,
        "audit_sidecars_sha256": {f"audit-{i}": "c" * 64 for i in range(32)},
        "source_sha256": file_hash(Path("scripts/experiment_b_vlm_quality.py")),
    }
    return QualityRelease.model_validate_json(json.dumps(body | {"release_sha256": digest(body)}))


def vlm_fixture():
    cached = b_fixture()
    release = release_fixture()

    def values(part):
        return tuple(
            VLMInputs(
                b=b,
                attributes={
                    "person_visible": "true" if i % 2 else "false",
                    "product_visible_early": "false" if i % 2 else "true",
                    "screen_text": "unknown" if i == 0 else "true",
                    "scene": "indoor" if i % 2 else "outdoor",
                    "format": "talking_head" if i % 2 else "reaction",
                },
            )
            for i, b in enumerate(getattr(cached, part))
        )

    return VLMDevelopmentData(
        cached, values("train"), values("validation"), release, {"synthetic": True}
    )


def test_full_inputs_preserve_exact_905_prefix_and_only_released_categorical_suffix():
    data = vlm_fixture()
    validate_data(data)
    rows = feature_matrix(data.train, data.release)
    assert len(feature_names(data.release)) == len(rows[0]) == 910
    assert [r[:905] for r in rows] == b_matrix(data.cached.train)
    assert categorical_indices(data.release) == (0, 3, 904, 905, 906, 907, 908, 909)
    assert rows[0][-3] == "unknown"  # Absence is never coded as false.


@pytest.mark.parametrize(
    "field,value",
    [
        ("views", "100"),
        ("demonstration", "true"),
        ("product_closeup", "true"),
        ("format", "application"),
        ("person_visible", "1"),
    ],
)
def test_outcomes_withheld_semantics_and_invalid_values_cannot_be_predictor_inputs(field, value):
    raw = vlm_fixture().train[0].model_dump()
    raw["attributes"][field] = value
    with pytest.raises((ValidationError, ExperimentError)):
        VLMInputs.model_validate(raw)


def test_release_and_alignment_are_enforced():
    data = vlm_fixture()
    with pytest.raises(ExperimentError, match="alignment"):
        validate_data(replace(data, train=data.train[::-1]))
    raw = data.release.model_dump()
    raw["released_fields"] = ["demonstration"]
    raw["release_sha256"] = digest({k: v for k, v in raw.items() if k != "release_sha256"})
    with pytest.raises((ValidationError, ExperimentError)):
        QualityRelease.model_validate(raw)
    missing = data.train[0].model_dump()
    missing["attributes"].pop("scene")
    with pytest.raises(ExperimentError, match="not_released"):
        feature_matrix([missing], data.release)


def test_incomplete_or_halted_extraction_refuses_before_reading_labels(tmp_path, monkeypatch):
    import scripts.experiment_b_vlm_data as module

    plan = {"rows": [{"sample_id": f"sample-{i}"} for i in range(269)]}
    state = {"entries": [], "halt_reason": None}
    monkeypatch.setattr(module, "load_queue", lambda *a: (plan, state))
    monkeypatch.setattr(module, "load_b_data", lambda *a, **kw: pytest.fail("labels were opened"))
    with pytest.raises(ExperimentError, match="complete_269"):
        load_data(tmp_path, tmp_path, tmp_path, tmp_path / "missing.json", tmp_path)


def test_representation_contains_only_the_columns_that_passed_the_gate():
    data = vlm_fixture()
    raw = data.release.model_dump()
    raw["released_fields"] = ["screen_text"]
    raw["retained_values"] = {"screen_text": raw["retained_values"]["screen_text"]}
    for name, column in raw["columns"].items():
        column["released"] = name == "screen_text"
    raw["release_sha256"] = digest({k: v for k, v in raw.items() if k != "release_sha256"})
    release = QualityRelease.model_validate_json(json.dumps(raw))
    values = [
        VLMInputs(b=v.b, attributes={"screen_text": v.attributes["screen_text"]})
        for v in data.train
    ]
    matrix = feature_matrix(values, release)
    assert len(matrix[0]) == 906 and feature_names(release)[-1] == "vlm_screen_text"
    assert categorical_indices(release) == (0, 3, 904, 905)
    assert [r[:905] for r in matrix] == b_matrix(data.cached.train)


def test_rehashing_a_failed_quality_summary_does_not_release_a_column():
    raw = release_fixture().model_dump()
    raw["columns"]["screen_text"]["sectors"]["moda"]["correct_value_and_evidence"] = 10
    raw["release_sha256"] = digest({k: v for k, v in raw.items() if k != "release_sha256"})
    with pytest.raises((ExperimentError, ValidationError), match="sector_gate"):
        QualityRelease.model_validate(raw)

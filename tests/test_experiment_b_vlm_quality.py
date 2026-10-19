import json
from copy import deepcopy

import pytest

from scripts.experiment_b_vlm_quality import FIELDS, evaluate_gate, normalized, validate_fields


def observations():
    rows = []
    for sector in ("beleza", "moda"):
        for i in range(16):
            fields = {field: {"value": i % 2 == 0, "frames": [1]} for field in FIELDS[:3]}
            fields |= {
                "scene": {"value": "indoor" if i % 2 else "outdoor", "frames": [1]},
                "format": {"value": "talking_head" if i % 2 else "reaction", "frames": [1]},
            }
            rows.append({"sector": sector, "predicted": fields, "annotated": deepcopy(fields)})
    return rows


def test_gate_releases_only_after_balanced_value_and_evidence_agreement():
    result = evaluate_gate(observations())
    assert result["released_fields"] == list(FIELDS)
    assert result["human_review"] is False
    assert result["general_perception_accuracy_validated"] is False
    assert result["predictive_outcomes_used"] is False
    assert all(
        s["known"] == s["correct_value_and_evidence"] == 16
        for column in result["columns"].values()
        for s in column["sectors"].values()
    )


def test_high_overall_agreement_cannot_hide_bad_perception_in_one_sector():
    rows = observations()
    for row in rows[:2]:
        row["predicted"]["person_visible"]["value"] = not row["annotated"]["person_visible"][
            "value"
        ]
    result = evaluate_gate(rows)
    assert "person_visible" not in result["released_fields"]
    failed = result["columns"]["person_visible"]["sectors"]["beleza"]
    assert failed["known"] == 16 and failed["agreement"] == 14 / 16
    assert failed["incorrect_or_unverified"] == 2


def test_correct_value_without_correct_frame_evidence_is_never_approved():
    rows = observations()
    rows[0]["predicted"]["screen_text"]["frames"] = [2]
    result = evaluate_gate(rows)
    assert "screen_text" not in result["released_fields"]
    assert (
        result["columns"]["screen_text"]["sectors"]["beleza"][
            "evidence_not_supported_by_blind_annotation"
        ]
        == 1
    )


def test_unknown_is_abstention_not_false_and_low_coverage_fails():
    rows = observations()
    for row in rows[:5]:
        row["predicted"]["person_visible"] = {"value": "unknown", "frames": []}
    result = evaluate_gate(rows)
    assert "person_visible" not in result["released_fields"]
    failed = result["columns"]["person_visible"]["sectors"]["beleza"]
    assert failed["known"] == 11 and failed["abstentions_or_unsupported"] == 5
    assert failed["agreement"] == 1


def test_boolean_needs_negative_controls_in_both_sectors():
    rows = observations()
    for row in rows[:16]:
        row["predicted"]["person_visible"]["value"] = True
        row["annotated"]["person_visible"]["value"] = True
    assert "person_visible" not in evaluate_gate(rows)["released_fields"]


def test_application_cannot_reenter_through_format_and_rare_classes_are_unknown():
    rows = observations()
    rows[0]["predicted"]["format"]["value"] = "application"
    rows[1]["predicted"]["format"]["value"] = "other"
    result = evaluate_gate(rows)
    assert "application" not in result["retained_values"]["format"]
    assert "other" not in result["retained_values"]["format"]
    assert result["columns"]["format"]["sectors"]["beleza"]["known"] == 14
    assert normalized("person_visible", "unknown") == "unknown"
    assert normalized("person_visible", False) == "false"


@pytest.mark.parametrize(
    "mutation", ["missing", "early", "integer_bool", "unknown_evidence", "duplicate"]
)
def test_blind_annotation_requires_explicit_values_and_valid_evidence(mutation):
    fields = observations()[0]["annotated"]
    if mutation == "missing":
        fields.pop("scene")
    elif mutation == "early":
        fields["product_visible_early"]["frames"] = [2]
    elif mutation == "integer_bool":
        fields["person_visible"]["value"] = 1
    elif mutation == "unknown_evidence":
        fields["person_visible"]["value"] = "unknown"
    else:
        fields["screen_text"]["frames"] = [1, 1]
    with pytest.raises(ValueError):
        validate_fields(fields, [0.2, 6.0])


def test_gate_cannot_run_on_unbalanced_or_incomplete_audit():
    with pytest.raises(ValueError, match="balanced_32"):
        evaluate_gate(observations()[:-1])


@pytest.mark.parametrize(
    "corruption", [None, "root_extra", "row_extra", "sidecar_changed", "not_completed"]
)
def test_publication_requires_closed_blind_receipt_and_completed_original_sidecars(
    tmp_path, monkeypatch, corruption
):
    from scripts import experiment_b_vlm_quality as module
    from scripts.private_checkpoint import file_hash

    observations_ = observations()
    ids = [f"sample-{i}" for i in range(32)]
    plan = {"plan_sha256": "a" * 64, "audit_sample_ids": ids, "config": {}, "rows": []}
    checkpoint = {"halt_reason": None, "entries": []}
    annotations = {
        "schema_version": "b-vlm-blind-annotations-v1",
        "plan_sha256": "a" * 64,
        "blind_to_vlm_outputs": True,
        "blind_to_outcomes": True,
        "human_review": False,
        "rows": [],
    }
    for sample, observation in zip(ids, observations_):
        sheet = tmp_path / "audit-sheets" / f"{sample}.png"
        sheet.parent.mkdir(exist_ok=True)
        sheet.write_bytes(b"fixture committed pixels")
        path = tmp_path / "sessions" / sample / "features.json"
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"predicted": observation["predicted"]}))
        plan["rows"].append(
            {
                "sample_id": sample,
                "sector": observation["sector"],
                "partition": "train",
                "audit": True,
                "sheet_sha256": file_hash(sheet),
            }
        )
        annotations["rows"].append(
            {
                "sample_id": sample,
                "sheet_sha256": file_hash(sheet),
                "fields": observation["annotated"],
            }
        )
        checkpoint["entries"].append(
            {
                "sample_id": sample,
                "status": "completed",
                "files_sha256": {"features.json": file_hash(path)},
            }
        )
    if corruption == "root_extra":
        annotations["views"] = 999
    elif corruption == "row_extra":
        annotations["rows"][0]["parsed"] = observations_[0]["predicted"]
    elif corruption == "sidecar_changed":
        path = tmp_path / "sessions" / ids[0] / "features.json"
        path.write_bytes(path.read_bytes() + b" ")
    elif corruption == "not_completed":
        checkpoint["entries"][0]["status"] = "running"
    monkeypatch.setattr(module, "load_queue", lambda *a: (plan, checkpoint))
    monkeypatch.setattr(
        module, "checked_sidecar", lambda sidecar, *a: (sidecar["predicted"], [0.2])
    )
    annotation_path = tmp_path / "blind.json"
    annotation_path.write_text(json.dumps(annotations))
    output = tmp_path / "release.json"
    if corruption:
        with pytest.raises(ValueError):
            module.publish_gate(
                tmp_path, annotation_path, output, parent=tmp_path, cohort=tmp_path, root=tmp_path
            )
        assert not output.exists()
    else:
        proof = module.publish_gate(
            tmp_path, annotation_path, output, parent=tmp_path, cohort=tmp_path, root=tmp_path
        )
        assert proof["released_fields"] == list(FIELDS)
        assert len(proof["audit_sidecars_sha256"]) == 32
        assert proof["annotations_sha256"] == file_hash(annotation_path)


def test_sidecar_global_quality_gate_cannot_be_bypassed():
    import hashlib

    from scripts.channel_partitions import digest
    from scripts.experiment_b_vlm_extract import POLICY
    from scripts.experiment_b_vlm_quality import checked_sidecar
    from scripts.gguf_visual_attributes import (
        QUALITY_POLICY,
        WITHHELD_ATTRIBUTES,
        apply_quality_policy,
        model_manifest,
    )
    from scripts.vlm_frame_evidence import NORMALIZATION_POLICY, SCHEMA_VERSION

    raw = {
        field: {"value": True, "frames": [1]}
        for field in (*FIELDS[:3], "product_closeup", "demonstration")
    }
    raw |= {
        "scene": {"value": "indoor", "frames": [1]},
        "format": {"value": "talking_head", "frames": [1]},
    }
    properties = {"duration_seconds": 10, "sampled_frame_seconds": [0.2, 6.0]}
    row = {
        "sample_id": "example",
        "features_sha256": "b" * 64,
        "media_sha256": "c" * 64,
        "sheet_sha256": "d" * 64,
        "properties": properties,
    }
    sidecar = {
        "schema_version": "experiment-b-vlm-sidecar-v1",
        "sample_id": "example",
        "input_policy": POLICY,
        "config_sha256": digest({}),
        "shared_features_sha256": "b" * 64,
        "frozen_media_sha256": "c" * 64,
        "reacquired_media_sha256": "e" * 64,
        "frozen_sheet_sha256": "d" * 64,
        "properties": properties,
        "input_png_sha256": ["f" * 64, "a" * 64],
        "training_approved": False,
        "test_evaluated": False,
        "vlm": {
            "schema_version": SCHEMA_VERSION,
            "normalization_policy": NORMALIZATION_POLICY,
            "normalized_model_parsed": deepcopy(raw),
            "deduplicated_fields": [],
            "raw_response": json.dumps(raw),
            "raw_response_sha256": hashlib.sha256(json.dumps(raw).encode()).hexdigest(),
            "approved_for_training": False,
            "status": "schema_valid_requires_perception_review",
            "model": model_manifest(),
            "quality_policy": QUALITY_POLICY,
            "withheld_attributes": WITHHELD_ATTRIBUTES,
            "input_frame_seconds": [0.2, 6.0],
            "model_parsed": raw,
            "parsed": apply_quality_policy(raw),
        },
    }
    checked_sidecar(sidecar, row, {})
    sidecar["vlm"]["parsed"]["demonstration"] = {"value": True, "frames": [1]}
    with pytest.raises(ValueError, match="ungated"):
        checked_sidecar(sidecar, row, {})

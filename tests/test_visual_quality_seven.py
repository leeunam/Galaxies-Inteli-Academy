"""Pure scoring on an invented panel, never a real quality release."""

import copy
import hashlib

import pytest

from scripts.visual_attributes import FIELDS
from scripts.visual_quality_seven import evaluate_gate


def panel():
    rows = []
    for index in range(32):
        values = {field: bool(index % 2) for field in FIELDS[:5]}
        values.update(
            scene="indoor" if index % 2 else "outdoor",
            format="application" if index % 2 else "product_showcase",
        )
        attributes = {field: {"value": value, "frames": [1]} for field, value in values.items()}
        rows.append(
            {
                "alias": f"invented_{index:02}",
                "sector": "moda" if index < 16 else "beleza",
                "partition": "train",
                "channel_id": f"invented_channel_{index:02}",
                "sheet_sha256": hashlib.sha256(f"invented_sheet_{index}".encode()).hexdigest(),
                "frame_seconds": [0, 3, 4, 60],
                "annotated": copy.deepcopy(attributes),
                "predicted": copy.deepcopy(attributes),
            }
        )
    return rows


def assert_no_release(report):
    for key in (
        "quality_accepted",
        "release_emitted",
        "extraction269_allowed",
        "general_perception_accuracy_validated",
        "predictive_outcomes_used",
    ):
        assert report[key] is False
    assert report["independent_bound_review_required"] is True
    assert "released_fields" not in report


def test_all_seven_meet_thresholds_but_do_not_authorize_quality_or_269():
    rows = panel()
    before = copy.deepcopy(rows)
    report = evaluate_gate(rows)
    assert rows == before
    assert report["status"] == "all_seven_meet_thresholds"
    assert report["passed_fields"] == list(FIELDS)
    assert report["blocked_fields"] == []
    assert set(report["columns"]) == set(FIELDS)
    assert report["columns"]["format"]["retained_values"] == ["application", "product_showcase"]
    for field in FIELDS:
        for sector in ("moda", "beleza"):
            result = report["columns"][field]["sectors"][sector]
            assert result["known"] == result["correct_value_and_evidence"] == 16
            assert result["agreement"] == 1.0
            assert result["abstentions"] == result["evidence_not_supported_by_annotation"] == 0
    assert_no_release(report)


@pytest.mark.parametrize("field", FIELDS)
def test_failure_of_any_single_field_blocks_integral_status(field):
    rows = panel()
    for row in rows:
        row["predicted"][field] = {"value": "unknown", "frames": []}
    report = evaluate_gate(rows)
    assert report["status"] == "blocked"
    assert report["blocked_fields"] == [field]
    assert report["passed_fields"] == [name for name in FIELDS if name != field]
    for sector in ("moda", "beleza"):
        scores = report["columns"][field]["sectors"][sector]
        assert scores["known"] == scores["correct_value_and_evidence"] == 0
        assert scores["agreement"] is None
        assert scores["abstentions"] == 16
    assert_no_release(report)


def test_missing_two_attribute_references_cannot_create_a_seven_field_gate():
    rows = panel()
    for row in rows:
        for field in ("product_closeup", "demonstration"):
            del row["annotated"][field]
    with pytest.raises(ValueError):
        evaluate_gate(rows)


def test_legacy_withheld_two_fields_does_not_meet_all_seven_thresholds():
    rows = panel()
    for row in rows:
        for field in ("product_closeup", "demonstration"):
            row["predicted"][field] = {"value": "unknown", "frames": []}
    report = evaluate_gate(rows)
    assert report["status"] == "blocked"
    assert report["blocked_fields"] == ["product_closeup", "demonstration"]
    assert_no_release(report)


@pytest.mark.parametrize("field", FIELDS)
def test_one_unsupported_frame_blocks_even_when_agreement_exceeds_90_percent(field):
    rows = panel()
    # This frame exists and is temporally eligible, but the annotation does not support it.
    rows[0]["predicted"][field]["frames"] = [2]
    report = evaluate_gate(rows)
    column = report["columns"][field]
    assert report["blocked_fields"] == [field]
    assert column["sectors"]["moda"]["agreement"] == 15 / 16
    assert column["sectors"]["moda"]["evidence_not_supported_by_annotation"] == 1
    assert column["blocked_reasons"] == ["unsupported_frame_evidence"]
    assert_no_release(report)


def test_evidence_subset_is_allowed_without_requiring_identical_frame_lists():
    rows = panel()
    for row in rows:
        for field in FIELDS:
            row["annotated"][field]["frames"] = [1, 2]
    assert evaluate_gate(rows)["status"] == "all_seven_meet_thresholds"


@pytest.mark.parametrize("unknown_count,blocked", [(4, False), (5, True)])
def test_known_denominator_is_exactly_12_per_sector(unknown_count, blocked):
    rows = panel()
    for row in rows[:unknown_count]:
        row["predicted"]["person_visible"] = {"value": "unknown", "frames": []}
    report = evaluate_gate(rows)
    scores = report["columns"]["person_visible"]["sectors"]["moda"]
    assert scores["known"] == 16 - unknown_count
    assert scores["agreement"] == 1.0
    assert (report["status"] == "blocked") is blocked


def test_agreement_failure_in_one_sector_cannot_be_hidden_by_pooled_score():
    rows = panel()
    for row in rows[:2]:
        row["predicted"]["person_visible"]["value"] = not row["predicted"]["person_visible"][
            "value"
        ]
    report = evaluate_gate(rows)
    assert report["blocked_fields"] == ["person_visible"]
    assert report["columns"]["person_visible"]["sectors"]["moda"]["agreement"] == 14 / 16
    assert 30 / 32 >= 0.9


def test_unknown_annotation_cannot_confirm_known_prediction_or_count_as_abstention_success():
    rows = panel()
    rows[0]["annotated"]["scene"] = {"value": "unknown", "frames": []}
    report = evaluate_gate(rows)
    assert report["blocked_fields"] == ["scene"]
    scores = report["columns"]["scene"]["sectors"]["moda"]
    assert scores["correct_value_and_evidence"] == 15
    assert scores["evidence_not_supported_by_annotation"] == 1
    assert {"annotated": "unknown", "predicted": "outdoor", "count": 1} in scores["confusion"]


@pytest.mark.parametrize("field", FIELDS[:5])
def test_boolean_support_requires_both_classes_globally_and_in_each_sector(field):
    rows = panel()
    for row in rows:
        row["predicted"][field]["value"] = row["annotated"][field]["value"] = True
    report = evaluate_gate(rows)
    assert report["blocked_fields"] == [field]
    assert "insufficient_boolean_class_support" in report["columns"][field]["blocked_reasons"]
    rows = panel()
    for row in rows[:16]:
        row["predicted"][field]["value"] = row["annotated"][field]["value"] = True
    assert evaluate_gate(rows)["blocked_fields"] == [field]
    rows = panel()
    for index, row in enumerate(rows):
        row["predicted"][field]["value"] = row["annotated"][field]["value"] = index in (0, 16)
    assert evaluate_gate(rows)["blocked_fields"] == [field]
    rows[1]["predicted"][field]["value"] = rows[1]["annotated"][field]["value"] = True
    assert evaluate_gate(rows)["status"] == "all_seven_meet_thresholds"


@pytest.mark.parametrize(
    "field,value,second", [("scene", "indoor", "outdoor"), ("format", "application", "other")]
)
def test_categorical_support_requires_two_values_with_three_each(field, value, second):
    rows = panel()
    for row in rows:
        row["predicted"][field]["value"] = row["annotated"][field]["value"] = value
    assert evaluate_gate(rows)["blocked_fields"] == [field]
    for row in rows[:2]:
        row["predicted"][field]["value"] = row["annotated"][field]["value"] = second
    assert evaluate_gate(rows)["blocked_fields"] == [field]
    rows[2]["predicted"][field]["value"] = rows[2]["annotated"][field]["value"] = second
    assert evaluate_gate(rows)["status"] == "all_seven_meet_thresholds"


def test_rare_known_category_is_still_counted_and_cannot_hide_unsupported_evidence():
    rows = panel()
    rows[0]["predicted"]["format"] = {"value": "reaction", "frames": [2]}
    report = evaluate_gate(rows)
    scores = report["columns"]["format"]["sectors"]["moda"]
    assert scores["known"] == 16
    assert scores["predicted_value_support"]["reaction"] == 1
    assert scores["evidence_not_supported_by_annotation"] == 1
    assert report["blocked_fields"] == ["format"]


@pytest.mark.parametrize("size", [0, 31, 33])
def test_incomplete_panel_never_reduces_targets(size):
    rows = panel()
    rows = rows[:size] if size <= 32 else rows + [copy.deepcopy(rows[0])]
    with pytest.raises(ValueError, match="incomplete_panel_requires_balanced_32_train"):
        evaluate_gate(rows)


def test_unbalanced_and_single_sector_panels_are_incomplete():
    for count in (17, 32):
        rows = panel()
        for index, row in enumerate(rows):
            row["sector"] = "moda" if index < count else "beleza"
        with pytest.raises(ValueError, match="incomplete_panel_requires_balanced_32_train"):
            evaluate_gate(rows)


@pytest.mark.parametrize("key", ["alias", "channel_id", "sheet_sha256"])
def test_each_identity_is_valid_and_unique(key):
    for value in ("", "bad value", None, True, [], {}):
        rows = panel()
        rows[0][key] = value
        with pytest.raises(ValueError, match="invalid_or_duplicate_panel_identity"):
            evaluate_gate(rows)
    rows = panel()
    rows[1][key] = rows[0][key]
    with pytest.raises(ValueError, match="invalid_or_duplicate_panel_identity"):
        evaluate_gate(rows)


@pytest.mark.parametrize("partition", ["test", "TEST", "validation", "TRAIN", None])
def test_panel_is_training_only(partition):
    rows = panel()
    rows[0]["partition"] = partition
    with pytest.raises(ValueError, match="requires_train_only"):
        evaluate_gate(rows)


@pytest.mark.parametrize("key", ["views", "outcome", "likes", "quality_accepted", "extra"])
def test_outcomes_and_extra_keys_are_rejected(key):
    rows = panel()
    rows[0][key] = 100
    with pytest.raises(ValueError, match="shape_no_outcomes_allowed"):
        evaluate_gate(rows)


@pytest.mark.parametrize("kind", ["annotated", "predicted"])
def test_both_sides_use_strict_seven_field_parser(kind):
    for replacement in (
        {"value": "OCR invented", "frames": [1]},
        {"value": "unknown", "frames": [1]},
        {"value": True, "frames": [1.0]},
        {"value": True, "frames": [1, 1]},
        {"value": True, "frames": []},
    ):
        rows = panel()
        rows[0][kind]["screen_text"] = replacement
        with pytest.raises(ValueError):
            evaluate_gate(rows)
    rows = panel()
    rows[0][kind]["product_visible_early"]["frames"] = [3]
    with pytest.raises(ValueError):
        evaluate_gate(rows)


def test_gate_is_pure_no_file_network_model_or_outcome_access(monkeypatch):
    import builtins
    import socket
    import subprocess

    rows = panel()

    def forbidden(*args, **kwargs):
        raise AssertionError("pure gate attempted IO or inference")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    assert evaluate_gate(rows)["status"] == "all_seven_meet_thresholds"

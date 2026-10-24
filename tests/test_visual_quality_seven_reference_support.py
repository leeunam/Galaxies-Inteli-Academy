"""Reference class coverage on invented TRAIN32 panels, without quality authority."""

import copy
import hashlib

import pytest

from scripts.visual_attributes_seven import BOOLEAN_FIELDS, FIELDS
from scripts.visual_quality_seven import BINDING_KEYS, evaluate_bound_gate, evaluate_gate


def panel():
    rows = []
    for index in range(32):
        values = {field: bool(index % 2) for field in BOOLEAN_FIELDS}
        values.update(
            scene="indoor" if index % 2 else "outdoor",
            format="application" if index % 2 else "product_showcase",
        )
        attributes = {field: {"value": value, "frames": [1]} for field, value in values.items()}
        rows.append(
            {
                "alias": f"reference_support_{index:02}",
                "sector": "moda" if index < 16 else "beleza",
                "partition": "train",
                "channel_id": f"reference_support_channel_{index:02}",
                "sheet_sha256": hashlib.sha256(f"invented_reference_{index}".encode()).hexdigest(),
                "frame_seconds": [0, 3, 4, 60],
                "annotated": copy.deepcopy(attributes),
                "predicted": copy.deepcopy(attributes),
            }
        )
    return rows, [{key: row[key] for key in BINDING_KEYS} for row in rows]


def set_values(rows, field, values):
    for row, value in zip(rows, values, strict=True):
        attribute = {"value": value, "frames": [] if value == "unknown" else [1]}
        row["annotated"][field] = copy.deepcopy(attribute)
        row["predicted"][field] = copy.deepcopy(attribute)


def without_reference_audit(report):
    """Remove only the bound-only additions for full legacy-output comparison."""
    report = copy.deepcopy(report)
    report.pop("panel_support")
    for column in report["columns"].values():
        column.pop("reference_value_support")
        column.pop("missing_reference_support")
        for scores in column["sectors"].values():
            scores.pop("reference_value_support")
    return report


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


def test_wrong_negative_predictions_cannot_manufacture_missing_reference_classes():
    rows, bindings = panel()
    fields = ("person_visible", "product_closeup")
    for field in fields:
        set_values(rows[16:], field, [True] * 16)
        rows[16]["predicted"][field]["value"] = False
    for row in rows[17:20]:
        row["predicted"]["product_closeup"] = {"value": "unknown", "frames": []}
    before = copy.deepcopy((rows, bindings))
    legacy = evaluate_gate(rows)
    assert legacy["status"] == "all_seven_meet_thresholds"
    assert legacy["passed_fields"] == list(FIELDS)
    assert legacy["blocked_fields"] == []
    assert "panel_support" not in legacy
    for field in fields:
        column = legacy["columns"][field]
        assert column["blocked_reasons"] == []
        assert "reference_value_support" not in column
        assert column["predicted_value_support"]["false"] >= 3
        assert column["sectors"]["beleza"]["predicted_value_support"]["false"] == 1
    assert legacy["columns"]["person_visible"]["sectors"]["beleza"]["agreement"] == 15 / 16
    assert legacy["columns"]["product_closeup"]["sectors"]["beleza"]["agreement"] == 12 / 13

    report = evaluate_bound_gate(rows, bindings)
    assert (rows, bindings) == before
    assert report["status"] == "blocked"
    assert report["blocked_fields"] == list(fields)
    assert report["passed_fields"] == [field for field in FIELDS if field not in fields]
    stripped = without_reference_audit(report)
    # Only the added necessary support check changes decisions, never core metrics.
    for field in fields:
        column = report["columns"][field]
        assert column["meets_thresholds"] is False
        assert column["blocked_reasons"] == ["insufficient_reference_boolean_class_support"]
        assert column["reference_value_support"] == {"false": 8, "true": 24, "unknown": 0}
        assert column["sectors"]["beleza"]["reference_value_support"] == {
            "false": 0,
            "true": 16,
            "unknown": 0,
        }
        assert column["missing_reference_support"] == [
            {
                "reason": "reference_boolean_class_below_minimum",
                "scope": "beleza",
                "value": "false",
                "count": 0,
                "minimum": 1,
            }
        ]
        stripped["columns"][field]["meets_thresholds"] = True
        stripped["columns"][field]["blocked_reasons"] = []
    stripped.update(
        status=legacy["status"], passed_fields=legacy["passed_fields"], blocked_fields=[]
    )
    assert stripped == legacy
    assert evaluate_gate(rows) == legacy
    assert_no_release(legacy)
    assert_no_release(report)


def test_complete_reference_support_preserves_full_legacy_output_without_release():
    rows, bindings = panel()
    before = copy.deepcopy((rows, bindings))
    report = evaluate_bound_gate(rows, bindings)
    assert (rows, bindings) == before
    assert report["status"] == "all_seven_meet_thresholds"
    assert without_reference_audit(report) == evaluate_gate(rows)
    for field, column in report["columns"].items():
        assert column["missing_reference_support"] == []
        expected = (
            {"false": 16, "true": 16, "unknown": 0}
            if field in BOOLEAN_FIELDS
            else {
                "unknown": 0,
                **(
                    {"indoor": 16, "outdoor": 16}
                    if field == "scene"
                    else {"application": 16, "product_showcase": 16}
                ),
            }
        )
        assert column["reference_value_support"] == expected
        for scores in column["sectors"].values():
            assert scores["reference_value_support"] == {
                key: count // 2 for key, count in expected.items()
            }
    assert_no_release(report)


@pytest.mark.parametrize("field", BOOLEAN_FIELDS)
@pytest.mark.parametrize("rare", [False, True])
@pytest.mark.parametrize(
    "indices,missing_scopes", [((0, 16), ["global"]), ((0, 1, 16), []), ((0, 1, 2), ["beleza"])]
)
def test_boolean_reference_global_three_and_each_sector_one_boundaries(
    field, rare, indices, missing_scopes
):
    rows, bindings = panel()
    set_values(rows, field, [rare if index in indices else not rare for index in range(32)])
    report = evaluate_bound_gate(rows, bindings)
    column = report["columns"][field]
    assert [item["scope"] for item in column["missing_reference_support"]] == missing_scopes
    assert column["reference_value_support"]["true" if rare else "false"] == len(indices)
    for deficit in column["missing_reference_support"]:
        assert deficit["value"] == ("true" if rare else "false")
        assert deficit["count"] == (2 if deficit["scope"] == "global" else 0)
        assert deficit["minimum"] == (3 if deficit["scope"] == "global" else 1)
    reason = "insufficient_reference_boolean_class_support"
    assert (reason in column["blocked_reasons"]) is bool(missing_scopes)
    assert column["meets_thresholds"] is (not missing_scopes)
    assert_no_release(report)


@pytest.mark.parametrize(
    "field,first,second", [("scene", "indoor", "outdoor"), ("format", "application", "other")]
)
@pytest.mark.parametrize("second_count", [0, 1, 2, 3])
def test_category_reference_requires_two_known_values_with_three_global_samples(
    field, first, second, second_count
):
    rows, bindings = panel()
    # All examples of the second category may be in one sector: no new sector rule.
    set_values(rows, field, [second] * second_count + [first] * (32 - second_count))
    report = evaluate_bound_gate(rows, bindings)
    column = report["columns"][field]
    missing = column["missing_reference_support"]
    assert bool(missing) is (second_count < 3)
    if missing:
        assert missing == [
            {
                "reason": "fewer_than_two_reference_categories_with_three_samples",
                "scope": "global",
                "retained_values": [first],
                "count": 1,
                "minimum": 2,
            }
        ]
    assert column["meets_thresholds"] is (second_count == 3)
    assert ("insufficient_reference_category_support" in column["blocked_reasons"]) is bool(missing)
    assert column["sectors"]["beleza"]["reference_value_support"] == {first: 16, "unknown": 0}
    assert_no_release(report)


@pytest.mark.parametrize(
    "field,known",
    [("person_visible", True), ("person_visible", False), ("scene", "indoor"), ("format", "other")],
)
def test_unknown_reference_is_counted_but_never_supplies_a_second_known_class(field, known):
    rows, bindings = panel()
    set_values(rows, field, [known] * 16 + ["unknown"] * 16)
    report = evaluate_bound_gate(rows, bindings)
    column = report["columns"][field]
    assert column["reference_value_support"]["unknown"] == 16
    assert column["sectors"]["beleza"]["reference_value_support"]["unknown"] == 16
    assert column["missing_reference_support"]
    assert column["meets_thresholds"] is False
    reason = (
        "insufficient_reference_boolean_class_support"
        if field in BOOLEAN_FIELDS
        else "insufficient_reference_category_support"
    )
    assert reason in column["blocked_reasons"]
    if field in BOOLEAN_FIELDS:
        absent = "false" if known is True else "true"
        assert column["reference_value_support"][absent] == 0
        assert any(
            item["scope"] == "global" and item["value"] == absent
            for item in column["missing_reference_support"]
        )
    else:
        assert column["missing_reference_support"][0]["retained_values"] == [known]
    assert_no_release(report)


def test_reference_support_does_not_add_a_twelve_known_annotations_per_sector_rule():
    rows, bindings = panel()
    # Two known references in this sector suffice for the added class-support check.
    set_values(rows[:16], "person_visible", [True, False] + ["unknown"] * 14)
    report = evaluate_bound_gate(rows, bindings)
    column = report["columns"]["person_visible"]
    assert column["missing_reference_support"] == []
    assert not any(
        reason.startswith("insufficient_reference") for reason in column["blocked_reasons"]
    )
    assert column["reference_value_support"] == {"false": 9, "true": 9, "unknown": 14}
    assert column["meets_thresholds"] is False  # Existing known-prediction rule still applies.
    assert "insufficient_known_predictions_per_sector" in column["blocked_reasons"]
    assert_no_release(report)

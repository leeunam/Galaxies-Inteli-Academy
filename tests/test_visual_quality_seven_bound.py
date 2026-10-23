"""Declared bindings and clustered support on invented TRAIN panels only."""

import copy
import hashlib

import pytest

from scripts.visual_attributes_seven import FIELDS
from scripts.visual_quality_seven import BINDING_KEYS, evaluate_bound_gate, evaluate_gate


def panel(*, distinct_channels=False):
    rows = []
    for index in range(32):
        values = {field: bool(index % 2) for field in FIELDS[:5]}
        values.update(
            scene="indoor" if index % 2 else "outdoor",
            format="application" if index % 2 else "product_showcase",
        )
        attributes = {field: {"value": value, "frames": [1]} for field, value in values.items()}
        channel = index if distinct_channels else (index // 16) * 12 + index % 16 % 12
        rows.append(
            {
                "alias": f"synthetic_{index:02}",
                "sector": "moda" if index < 16 else "beleza",
                "partition": "train",
                "channel_id": f"synthetic_channel_{channel:02}",
                "sheet_sha256": hashlib.sha256(f"synthetic_sheet_{index}".encode()).hexdigest(),
                "frame_seconds": [0, 3, 4, 60],
                "annotated": copy.deepcopy(attributes),
                "predicted": copy.deepcopy(attributes),
            }
        )
    bindings = [{key: row[key] for key in BINDING_KEYS} for row in rows]
    return rows, bindings


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


def test_bound_32_samples_24_channels_scores_without_quality_authority_or_mutation():
    rows, bindings = panel()
    before = copy.deepcopy((rows, bindings))
    report = evaluate_bound_gate(rows, bindings)
    assert (rows, bindings) == before
    assert report["status"] == "all_seven_meet_thresholds"
    support = report["panel_support"]
    assert support["samples"] == 32
    assert support["channels"] == 24
    assert support["channel_independence_assumed"] is False
    assert sorted(support["samples_per_channel"].values()) == [1] * 16 + [2] * 8
    for sector in ("moda", "beleza"):
        sector_support = support["sectors"][sector]
        assert sector_support["samples"] == 16
        assert sector_support["channels"] == 12
        assert sorted(sector_support["samples_per_channel"].values()) == [1] * 8 + [2] * 4
        for field in FIELDS:
            scores = report["columns"][field]["sectors"][sector]
            assert scores["known"] == scores["correct_value_and_evidence"] == 16
            assert scores["agreement"] == 1
    assert_no_release(report)
    with pytest.raises(ValueError, match="duplicate_panel_identity"):
        evaluate_gate(rows)


@pytest.mark.parametrize("defect", ["none", "abstain", "wrong", "evidence", "classes"])
def test_distinct_channels_have_exact_legacy_metrics(defect):
    rows, bindings = panel(distinct_channels=True)
    if defect == "abstain":
        for row in rows[:5]:
            row["predicted"]["person_visible"] = {"value": "unknown", "frames": []}
    elif defect == "wrong":
        for row in rows[:2]:
            row["predicted"]["person_visible"]["value"] = not row["annotated"]["person_visible"][
                "value"
            ]
    elif defect == "evidence":
        rows[0]["predicted"]["scene"]["frames"] = [2]
    elif defect == "classes":
        for row in rows:
            row["predicted"]["demonstration"]["value"] = True
    report = evaluate_bound_gate(rows, bindings)
    assert report.pop("panel_support")["channels"] == 32
    assert report == evaluate_gate(rows)


@pytest.mark.parametrize("key", sorted(BINDING_KEYS))
def test_observation_identity_must_match_expected_alias_binding(key):
    rows, bindings = panel()
    replacements = {
        "alias": "synthetic_unknown_alias",
        "sector": "beleza",
        "partition": "test",
        "channel_id": "synthetic_fabricated_channel",
        "sheet_sha256": "f" * 64,
    }
    rows[0][key] = replacements[key]
    with pytest.raises(ValueError):
        evaluate_bound_gate(rows, bindings)


@pytest.mark.parametrize("key", sorted(BINDING_KEYS))
def test_mutating_trusted_table_alone_cannot_rebind_observations(key):
    rows, bindings = panel()
    replacements = {
        "alias": "synthetic_unknown_alias",
        "sector": "beleza",
        "partition": "TEST",
        "channel_id": "synthetic_fabricated_channel",
        "sheet_sha256": "f" * 64,
    }
    bindings[0][key] = replacements[key]
    with pytest.raises(ValueError):
        evaluate_bound_gate(rows, bindings)


@pytest.mark.parametrize("key", ["alias", "channel_id", "sheet_sha256"])
def test_transposed_identity_fields_do_not_match_bindings(key):
    rows, bindings = panel()
    rows[0][key], rows[1][key] = rows[1][key], rows[0][key]
    with pytest.raises(ValueError):
        evaluate_bound_gate(rows, bindings)


def test_binding_is_by_alias_not_row_position():
    rows, bindings = panel()
    assert evaluate_bound_gate(rows, bindings) == evaluate_bound_gate(
        rows[::-1], bindings[7:] + bindings[:7]
    )


def test_channel_shared_between_sectors_is_counted_once_globally():
    rows, bindings = panel()
    # Keep at most two samples per channel while sharing one across sectors.
    for index, channel in ((12, rows[4]["channel_id"]), (16, rows[0]["channel_id"])):
        rows[index]["channel_id"] = bindings[index]["channel_id"] = channel
    support = evaluate_bound_gate(rows, bindings)["panel_support"]
    assert support["channels"] == 24
    assert support["sectors"]["moda"]["channels"] == 12
    assert support["sectors"]["beleza"]["channels"] == 13
    shared = rows[0]["channel_id"]
    assert support["samples_per_channel"][shared] == 2
    assert support["sectors"]["moda"]["samples_per_channel"][shared] == 1
    assert support["sectors"]["beleza"]["samples_per_channel"][shared] == 1


@pytest.mark.parametrize("side", ["observations", "bindings"])
@pytest.mark.parametrize("key", sorted(BINDING_KEYS))
@pytest.mark.parametrize("value", [None, True, 7, [], {}, "", "bad value"])
def test_identity_types_and_invalid_identifiers_are_rejected(side, key, value):
    rows, bindings = panel()
    (rows if side == "observations" else bindings)[0][key] = value
    with pytest.raises(ValueError):
        evaluate_bound_gate(rows, bindings)


@pytest.mark.parametrize("side", ["observations", "bindings"])
@pytest.mark.parametrize("key", ["alias", "sheet_sha256"])
def test_aliases_and_png_hashes_must_still_be_unique(side, key):
    rows, bindings = panel()
    target = rows if side == "observations" else bindings
    target[1][key] = target[0][key]
    with pytest.raises(ValueError):
        evaluate_bound_gate(rows, bindings)


@pytest.mark.parametrize("side", ["observations", "bindings"])
@pytest.mark.parametrize(
    "defect", ["short", "extra_row", "tuple", "none", "extra_key", "missing_key", "row_type"]
)
def test_both_input_shapes_are_strict(side, defect):
    rows, bindings = panel()
    target = rows if side == "observations" else bindings
    if defect == "short":
        target.pop()
    elif defect == "extra_row":
        target.append(copy.deepcopy(target[0]))
    elif defect == "tuple":
        target = tuple(target)
    elif defect == "none":
        target = None
    elif defect == "extra_key":
        target[0]["extra"] = 1
    elif defect == "missing_key":
        del target[0]["partition"]
    else:
        target[0] = []
    with pytest.raises(ValueError):
        evaluate_bound_gate(
            target if side == "observations" else rows, target if side == "bindings" else bindings
        )


@pytest.mark.parametrize("partition", ["test", "TEST", "validation", "TRAIN"])
def test_jointly_declared_non_train_partition_still_fails(partition):
    rows, bindings = panel()
    rows[0]["partition"] = bindings[0]["partition"] = partition
    with pytest.raises(ValueError):
        evaluate_bound_gate(rows, bindings)


def test_jointly_declared_unbalanced_sector_still_fails():
    rows, bindings = panel()
    rows[0]["sector"] = bindings[0]["sector"] = "beleza"
    with pytest.raises(ValueError):
        evaluate_bound_gate(rows, bindings)


@pytest.mark.parametrize(
    "unknowns,errors,known,correct,blocked",
    [(4, 1, 12, 11, False), (4, 2, 12, 10, True), (5, 0, 11, 11, True), (0, 2, 16, 14, True)],
)
def test_repeated_channels_do_not_change_denominators_or_sector_thresholds(
    unknowns, errors, known, correct, blocked
):
    rows, bindings = panel()
    for row in rows[:unknowns]:
        row["predicted"]["person_visible"] = {"value": "unknown", "frames": []}
    for row in rows[unknowns : unknowns + errors]:
        row["predicted"]["person_visible"]["value"] = not row["annotated"]["person_visible"][
            "value"
        ]
    report = evaluate_bound_gate(rows, bindings)
    column = report["columns"]["person_visible"]
    scores = column["sectors"]["moda"]
    assert scores["samples"] == 16
    assert scores["known"] == known
    assert scores["correct_value_and_evidence"] == correct
    assert scores["agreement"] == correct / known
    assert column["sectors"]["beleza"]["agreement"] == 1
    assert (report["status"] == "blocked") is blocked
    assert_no_release(report)


@pytest.mark.parametrize(
    "defect,reason",
    [
        ("boolean", "insufficient_boolean_class_support"),
        ("category", "insufficient_category_support"),
        ("evidence", "unsupported_frame_evidence"),
    ],
)
def test_bound_mode_preserves_class_and_frame_requirements(defect, reason):
    rows, bindings = panel()
    field = "scene" if defect == "category" else "person_visible"
    if defect == "evidence":
        rows[0]["predicted"][field]["frames"] = [2]
    else:
        for row in rows:
            row["predicted"][field]["value"] = row["annotated"][field]["value"] = (
                "indoor" if defect == "category" else True
            )
    report = evaluate_bound_gate(rows, bindings)
    assert reason in report["columns"][field]["blocked_reasons"]
    assert_no_release(report)


def test_bound_gate_is_pure_and_preserves_strict_attribute_parser(monkeypatch):
    import builtins
    import socket
    import subprocess

    rows, bindings = panel()

    def forbidden(*args, **kwargs):
        raise AssertionError("bound gate attempted IO or inference")

    monkeypatch.setattr(builtins, "open", forbidden)
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    assert evaluate_bound_gate(rows, bindings)["status"] == "all_seven_meet_thresholds"
    rows[0]["predicted"]["person_visible"] = {"value": True, "frames": []}
    with pytest.raises(ValueError):
        evaluate_bound_gate(rows, bindings)

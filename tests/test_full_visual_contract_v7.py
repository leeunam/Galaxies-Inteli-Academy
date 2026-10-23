"""Structural-only tests for the synthetic seven-field sidecar contract."""

from __future__ import annotations

import pytest

from scripts.channel_partitions import ExperimentError
from scripts.full_visual_contract_v7 import (
    DATA_KIND_OBSERVED_UNRELEASED,
    FIELDS,
    check_sidecar_v7,
    make_synthetic_sidecar,
    parse_json,
)
from scripts.visual_attributes import FORMATS, SCENES


def _sha(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode()).hexdigest()


def sidecar() -> dict:
    identities = {
        name: _sha(name)
        for name in (
            "cohort_sha256",
            "partition_sha256",
            "configuration_sha256",
            "candidate_sha256",
        )
    }
    values = {}
    for field in FIELDS:
        if field == "person_visible":
            value = True
        elif field == "product_visible_early":
            value = False
        elif field == "product_closeup":
            value = "unknown"
        elif field == "demonstration":
            value = True
        elif field == "screen_text":
            value = False
        elif field == "scene":
            value = "indoor"
        else:
            value = "application"
        values[field] = {"value": value, "frames": [] if value == "unknown" else [1]}
    return make_synthetic_sidecar(
        sample_id="sample_001",
        partition="train",
        channel_id="channel_001",
        identities=identities,
        frame_seconds=[0.0, 3.0, 4.0],
        frame_sha256=[_sha(f"frame-{index}") for index in range(3)],
        attributes=values,
    )


def test_v7_sidecar_accepts_all_seven_original_enums_without_quality_acceptance():
    value = sidecar()
    checked = check_sidecar_v7(
        value,
        expected_sample_id="sample_001",
        expected_partition="train",
        expected_channel_id="channel_001",
        expected_identities=value["identities"],
    )
    assert tuple(checked.attributes) == FIELDS
    assert checked.attributes["product_closeup"] == "unknown"
    assert checked.attributes["demonstration"] == "true"
    assert checked.attributes["format"] == "application"
    assert checked.quality_accepted is False
    assert checked.release_emitted is False
    assert checked.data_kind == "synthetic"
    assert "application" in FORMATS and SCENES[-1] == "unknown"


@pytest.mark.parametrize("field", FIELDS)
def test_every_required_field_missing_is_rejected(field: str):
    value = sidecar()
    del value["attributes"][field]
    with pytest.raises(ExperimentError, match="v7_attributes_invalid"):
        check_sidecar_v7(value)


@pytest.mark.parametrize("field", FIELDS)
def test_every_required_field_rejects_invalid_type(field: str):
    value = sidecar()
    value["attributes"][field]["value"] = 7
    with pytest.raises(ExperimentError):
        check_sidecar_v7(value)


@pytest.mark.parametrize("field", FIELDS)
def test_every_known_field_requires_frame_evidence(field: str):
    value = sidecar()
    evidence = value["attributes"][field]
    if evidence["value"] == "unknown":
        evidence["value"] = (
            False if field in FIELDS[:5] else (SCENES[0] if field == "scene" else FORMATS[0])
        )
    evidence["frames"] = []
    with pytest.raises(ExperimentError, match="v7_known_value_requires_frames"):
        check_sidecar_v7(value)


def test_attribute_and_top_level_extra_fields_are_rejected():
    value = sidecar()
    value["attributes"]["views"] = {"value": 1, "frames": []}
    with pytest.raises(ExperimentError, match="v7_attributes_invalid"):
        check_sidecar_v7(value)
    value = sidecar() | {"outcome": "pass"}
    with pytest.raises(ExperimentError, match="v7_sidecar_shape_invalid"):
        check_sidecar_v7(value)


@pytest.mark.parametrize(
    ("mutate", "error"),
    [
        (
            lambda x: x.update(schema_version="visual-validation-attribute-sidecar-v1"),
            "v7_sidecar_schema_mismatch",
        ),
        (lambda x: x.update(input_frame_seconds=[2.0, 1.0, 4.0]), "v7_frame_time_order_invalid"),
        (lambda x: x.update(input_frame_seconds=[0.0, 1.0, 1.0]), "v7_frame_time_order_invalid"),
        (lambda x: x.update(input_frame_seconds=[True, 1.0, 2.0]), "v7_frame_time_invalid"),
        (lambda x: x.update(input_frame_seconds=[-0.1, 1.0, 2.0]), "v7_frame_time_invalid"),
        (lambda x: x.update(input_frame_seconds=[0.0, 60.1, 61.0]), "v7_frame_time_invalid"),
        (lambda x: x.update(input_frame_sha256=[_sha("one")]), "v7_frame_hash_count_invalid"),
        (
            lambda x: x.update(input_frame_sha256=["invalid", _sha("two"), _sha("three")]),
            "v7_frame_hash_invalid",
        ),
        (lambda x: x["attributes"]["scene"].update(frames=[0]), "v7_frame_evidence_invalid"),
        (lambda x: x["attributes"]["scene"].update(frames=[1, 1]), "v7_duplicate_frame_evidence"),
        (
            lambda x: x["attributes"]["product_visible_early"].update(value=True, frames=[3]),
            "v7_early_product_frame_after_three_seconds",
        ),
        (
            lambda x: x["attributes"]["product_closeup"].update(value="unknown", frames=[1]),
            "v7_unknown_must_not_claim_frames",
        ),
        (lambda x: x.update(quality_accepted=0), "v7_quality_must_remain_unreleased"),
        (lambda x: x.update(release_emitted="false"), "v7_quality_must_remain_unreleased"),
    ],
)
def test_timeline_identity_and_release_flags_are_strict(mutate, error: str):
    value = sidecar()
    mutate(value)
    with pytest.raises(ExperimentError, match=error):
        check_sidecar_v7(value)


def test_product_frame_at_three_seconds_is_inclusive_and_unknown_keeps_no_frames():
    value = sidecar()
    value["attributes"]["product_visible_early"].update(value=True, frames=[2])
    checked = check_sidecar_v7(value)
    assert checked.frame_seconds[1] == 3.0
    assert checked.attributes["product_visible_early"] == "true"
    assert checked.attributes["product_closeup"] == "unknown"


def test_observed_sidecar_can_only_be_checked_in_memory_and_stays_unreleased():
    value = sidecar()
    value["data_kind"] = DATA_KIND_OBSERVED_UNRELEASED
    checked = check_sidecar_v7(value)
    assert checked.data_kind == DATA_KIND_OBSERVED_UNRELEASED
    assert checked.quality_accepted is False
    assert checked.release_emitted is False


def test_legacy_three_or_five_field_sidecars_do_not_become_v7():
    for count in (3, 5):
        old = sidecar()
        old["schema_version"] = f"legacy-{count}-field"
        old["attributes"] = dict(list(old["attributes"].items())[:count])
        with pytest.raises(ExperimentError):
            check_sidecar_v7(old)


@pytest.mark.parametrize("raw", ["\ud800", "[" * 1400 + "0" + "]" * 1400])
def test_malformed_or_deep_input_has_static_error(raw: str):
    with pytest.raises(ExperimentError):
        parse_json(raw)


def test_nonfinite_time_huge_integer_and_invalid_hash_are_static_errors():
    value = sidecar()
    value["input_frame_seconds"] = [10**400, 3.0, 4.0]
    with pytest.raises(ExperimentError, match="v7_frame_time_invalid"):
        check_sidecar_v7(value)

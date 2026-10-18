import json

import pytest

from scripts.gguf_visual_attributes import (
    apply_quality_policy,
    attribute_schema,
    extract_json_output,
)
from scripts.visual_attributes import FIELDS


def test_schema_cannot_claim_early_evidence_from_late_frames():
    schema = attribute_schema([0.2, 4.0])
    assert schema["properties"]["product_visible_early"]["properties"]["frames"]["items"][
        "enum"
    ] == [1]
    late_only = attribute_schema([4.0])["properties"]["product_visible_early"]["properties"]
    assert late_only["value"]["enum"] == ["unknown"]
    assert late_only["frames"]["maxItems"] == 0


def test_runtime_output_requires_complete_independently_validated_attributes():
    expected = {key: {"value": "unknown", "frames": []} for key in FIELDS}
    parsed, status = extract_json_output(
        'log line {"unrelated":true}\n' + json.dumps(expected), [0.2]
    )
    assert parsed == expected
    assert status == "schema_valid_requires_perception_review"
    with pytest.raises(ValueError):
        extract_json_output(json.dumps(expected)[:-2], [0.2])


def test_quality_gate_withholds_failed_attributes_globally_and_keeps_raw_output():
    raw = {key: {"value": True, "frames": [1]} for key in FIELDS}
    raw["scene"] = {"value": "indoor", "frames": [1]}
    raw["format"] = {"value": "talking_head", "frames": [1]}
    raw["screen_text"] = {"value": "unknown", "frames": [1]}
    usable = apply_quality_policy(raw)
    assert (
        usable["demonstration"] == usable["product_closeup"] == {"value": "unknown", "frames": []}
    )
    assert usable["screen_text"]["frames"] == []
    assert usable["person_visible"] == raw["person_visible"]
    assert raw["demonstration"] == {"value": True, "frames": [1]}

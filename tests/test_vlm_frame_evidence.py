import copy
import json

import pytest

from scripts import gguf_visual_attributes as legacy
from scripts import vlm_frame_evidence as module


def attributes():
    result = {
        key: {"value": True, "frames": [1]}
        for key in (
            "person_visible",
            "product_visible_early",
            "product_closeup",
            "demonstration",
            "screen_text",
        )
    }
    return result | {
        "scene": {"value": "indoor", "frames": [1]},
        "format": {"value": "other", "frames": [1]},
    }


def test_only_valid_duplicate_indices_are_removed_without_changing_values_or_input():
    raw = attributes()
    raw["product_visible_early"]["frames"] = [2, 3, 2]
    raw["person_visible"]["frames"] = [4, 1, 4, 2]
    untouched = copy.deepcopy(raw)
    normalized = module.normalize_frame_indices(raw, [0.2, 1.5, 2.8, 6.0])
    assert raw == untouched
    assert normalized["product_visible_early"]["frames"] == [2, 3]
    assert normalized["person_visible"]["frames"] == [4, 1, 2]
    assert {k: v["value"] for k, v in normalized.items()} == {k: v["value"] for k, v in raw.items()}
    assert module.normalize_frame_indices(normalized, [0.2, 1.5, 2.8, 6.0]) == normalized


@pytest.mark.parametrize("frames", [[True], [1.0], [0], [5], [4], [1, 2, 1, 2], (1, 2), []])
def test_wrong_types_bounds_late_or_missing_evidence_are_not_repaired(frames):
    raw = attributes()
    raw["product_visible_early"]["frames"] = frames
    with pytest.raises(ValueError):
        module.normalize_frame_indices(raw, [0.2, 1.5, 2.8, 6.0])


def test_missing_fields_extra_fields_and_invalid_values_are_not_repaired():
    for raw in (
        {k: v for k, v in attributes().items() if k != "scene"},
        attributes() | {"views": 999},
        attributes() | {"person_visible": {"value": "true", "frames": [1]}},
    ):
        with pytest.raises(ValueError):
            module.normalize_frame_indices(raw, [0.2])


def test_incomplete_json_and_duplicate_json_keys_are_not_repaired():
    for text in (
        '{"person_visible":',
        json.dumps(attributes()).replace('"indoor"', '"indoor", "value": "outdoor"'),
    ):
        with pytest.raises(ValueError):
            module.parse_normalized_output(text, [0.2])


def test_prompt_schema_and_invocation_are_identical_to_frozen_legacy_adapter(tmp_path, monkeypatch):
    raw = attributes()
    calls = []

    def capture(*args, **kwargs):
        calls.append((args, kwargs))
        return {"raw_response": json.dumps(raw), "runtime_seconds": 1, "runtime_peak_rss_mib": 2}

    monkeypatch.setattr(legacy, "invoke_local_vlm", capture)
    monkeypatch.setattr(module, "invoke_local_vlm", capture)
    paths, seconds = [tmp_path / "same.png"], [0.2]
    old = legacy.extract_visual_attributes(paths, seconds, tmp_path)
    new = module.extract_visual_attributes(paths, seconds, tmp_path)
    assert calls[0] == calls[1]
    assert new["raw_response"] == old["raw_response"]
    assert new["model_parsed"] == old["model_parsed"]
    assert new["normalized_model_parsed"] == old["model_parsed"]
    assert new["parsed"] == old["parsed"]
    assert new["model"] == old["model"]
    assert new["deduplicated_fields"] == []


def test_rejected_raw_output_is_carried_for_private_persistence(tmp_path, monkeypatch):
    text = '{"incomplete":'
    monkeypatch.setattr(module, "invoke_local_vlm", lambda *a: {"raw_response": text})
    with pytest.raises(module.VLMOutputError) as caught:
        module.extract_visual_attributes([tmp_path / "same.png"], [0.2], tmp_path)
    assert caught.value.evidence["raw_response"] == text
    assert caught.value.evidence["model"] == legacy.model_manifest()

import json

from scripts.visual_attributes import FIELDS, validate_vlm_answer


def empty_attributes():
    return {key: {"value": "unknown", "frames": []} for key in FIELDS}


def test_early_product_requires_actual_timestamp_evidence():
    result = empty_attributes()
    result["product_visible_early"] = {"value": True, "frames": [2]}
    assert validate_vlm_answer(json.dumps(result), [0.2, 4.0])[0] == "invalid_early_frame_evidence"
    result["product_visible_early"] = {"value": True, "frames": [1]}
    assert (
        validate_vlm_answer(json.dumps(result), [0.2, 4.0])[0]
        == "schema_valid_requires_perception_review"
    )


def test_response_format_and_free_ocr_text_are_not_visual_attributes():
    result = empty_attributes()
    result["format"] = {"value": "json", "frames": [1]}
    assert validate_vlm_answer(json.dumps(result), [0.2])[0] == "invalid_schema"
    result["format"] = {"value": "unknown", "frames": []}
    result["screen_text"] = {"value": "some OCR text", "frames": [1]}
    assert validate_vlm_answer(json.dumps(result), [0.2])[0] == "invalid_schema"


def test_valid_structure_does_not_automatically_approve_perception():
    result = empty_attributes()
    status, _ = validate_vlm_answer(json.dumps(result), [0.2])
    assert status == "schema_valid_requires_perception_review"

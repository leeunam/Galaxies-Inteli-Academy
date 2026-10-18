"""Shared visual attribute contract; structural validity is separate from perception quality."""

import json

SCENES = ("indoor", "outdoor", "graphic", "mixed", "unknown")
FORMATS = (
    "talking_head",
    "product_showcase",
    "application",
    "reaction",
    "mixed",
    "other",
    "unknown",
)
FIELDS = (
    "person_visible",
    "product_visible_early",
    "product_closeup",
    "demonstration",
    "screen_text",
    "scene",
    "format",
)


def validate_vlm_answer(
    answer: str, frame_seconds: list[float] | None = None
) -> tuple[str, object]:
    try:
        parsed = json.loads(answer)
    except json.JSONDecodeError:
        return "invalid_json", None
    boolean_keys = {
        "person_visible",
        "product_visible_early",
        "product_closeup",
        "demonstration",
        "screen_text",
    }
    if not isinstance(parsed, dict) or set(parsed) != boolean_keys | {"scene", "format"}:
        return "invalid_schema", parsed
    frame_count = len(frame_seconds) if frame_seconds is not None else 4
    for key, item in parsed.items():
        if not isinstance(item, dict) or set(item) != {"value", "frames"}:
            return "invalid_schema", parsed
        value, frames = item["value"], item["frames"]
        if not isinstance(frames, list) or any(
            type(i) is not int or not 1 <= i <= frame_count for i in frames
        ):
            return "invalid_schema", parsed
        if len(set(frames)) != len(frames):
            return "invalid_schema", parsed
        if key in boolean_keys and type(value) is not bool and value != "unknown":
            return "invalid_schema", parsed
        if key == "scene" and value not in SCENES:
            return "invalid_schema", parsed
        if key == "format" and value not in FORMATS:
            return "invalid_schema", parsed
        if value != "unknown" and not frames:
            return "missing_frame_evidence", parsed
        if key == "product_visible_early" and any(
            frame_seconds[i - 1] > 3 if frame_seconds is not None else i > 3 for i in frames
        ):
            return "invalid_early_frame_evidence", parsed
    return "schema_valid_requires_perception_review", parsed

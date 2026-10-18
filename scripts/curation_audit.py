"""Narrow local visual curation; output is an automated observation, never human review."""

import json

from scripts.gguf_visual_attributes import invoke_local_vlm, model_manifest

OPTIONS = {
    "sector": ["moda", "beleza", "outside", "unknown"],
    "advertised_item": [
        "clothing",
        "fashion_accessory",
        "cosmetic",
        "cosmetic_application",
        "storage_accessory",
        "other",
        "unknown",
    ],
}


def curation_decision(parsed):
    sector = parsed["sector"]["value"]
    item = parsed["advertised_item"]["value"]
    if item == "storage_accessory":
        return "exclude_storage_accessory"
    if sector == "unknown" or item == "unknown":
        return "inconclusive"
    if sector == "outside" or item == "other":
        return "exclude_outside_content"
    if (sector == "moda" and item in ("clothing", "fashion_accessory")) or (
        sector == "beleza" and item in ("cosmetic", "cosmetic_application")
    ):
        return "content_supported"
    return "inconclusive"


def validate_curation(parsed, frame_count):
    if not isinstance(parsed, dict) or set(parsed) != set(OPTIONS):
        raise ValueError("invalid_curation_schema")
    for key, options in OPTIONS.items():
        item = parsed[key]
        if (
            not isinstance(item, dict)
            or set(item) != {"value", "frames"}
            or item["value"] not in options
        ):
            raise ValueError("invalid_curation_schema")
        frames = item["frames"]
        if not isinstance(frames, list) or any(
            type(i) is not int or not 1 <= i <= frame_count for i in frames
        ):
            raise ValueError("invalid_curation_evidence")
        if len(frames) != len(set(frames)) or (item["value"] == "unknown") != (not frames):
            raise ValueError("invalid_curation_evidence")
    return parsed


def extract_curation(frame_paths, frame_seconds, work):
    if not 1 <= len(frame_paths) == len(frame_seconds) <= 4:
        raise ValueError("invalid_curation_samples")
    schema = {
        "type": "object",
        "properties": {},
        "required": list(OPTIONS),
        "additionalProperties": False,
    }
    for key, options in OPTIONS.items():
        schema["properties"][key] = {
            "type": "object",
            "properties": {
                "value": {"enum": options},
                "frames": {
                    "type": "array",
                    "items": {"enum": list(range(1, len(frame_paths) + 1))},
                    "maxItems": len(frame_paths),
                },
            },
            "required": ["value", "frames"],
            "additionalProperties": False,
        }
    prompt = (
        "Classify only the visible advertised item in these chronological video frames. "
        "Do not use titles, hashtags, popularity, audio or assumptions about unseen content. "
        "sector: moda for clothing/fashion accessories; beleza for cosmetic products or their application; "
        "outside for other products; unknown if identity is not visible. "
        "advertised_item: clothing, fashion_accessory, cosmetic, cosmetic_application, storage_accessory, other or unknown. "
        "A makeup organizer advertises storage_accessory even with cosmetics nearby. "
        "A clothed presenter alone does not prove a clothing advertisement. "
        "Use unknown with empty frames when uncertain. Cite one-based frames for every known value. "
        "Return only the schema JSON."
    )
    output = invoke_local_vlm(frame_paths, prompt, work, schema=schema, max_tokens=192)
    decoder = json.JSONDecoder()
    for offset, char in enumerate(output["raw_response"]):
        if char != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(output["raw_response"][offset:])
            parsed = validate_curation(parsed, len(frame_paths))
        except ValueError:
            continue
        return {
            "schema_version": "automated-curation-v1",
            "status": "schema_valid_requires_perception_review",
            "human_review": False,
            "automatic_training_release_allowed": False,
            "perception_accuracy_validated": False,
            "model": model_manifest(),
            "frame_seconds": frame_seconds,
            "parsed": parsed,
            "decision": curation_decision(parsed),
            "scope": "sampled_frames_only",
            **output,
        }
    return {
        "schema_version": "automated-curation-v1",
        "status": "invalid_curation_output",
        "human_review": False,
        "automatic_training_release_allowed": False,
        "perception_accuracy_validated": False,
        "model": model_manifest(),
        "frame_seconds": frame_seconds,
        "parsed": None,
        "decision": "inconclusive",
        "scope": "sampled_frames_only",
        **output,
    }

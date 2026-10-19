"""Conservative VLM evidence canonicalization; no perceptual values are repaired."""

from __future__ import annotations

import copy
import hashlib
import json
import math

from scripts.gguf_visual_attributes import (
    QUALITY_POLICY,
    WITHHELD_ATTRIBUTES,
    apply_quality_policy,
    attribute_schema,
    invoke_local_vlm,
    model_manifest,
)
from scripts.visual_attributes import FIELDS, validate_vlm_answer

NORMALIZATION_POLICY = "deduplicate_valid_frame_indices_preserve_values_v1"
SCHEMA_VERSION = "visual-attributes-v6-qwen-gguf-cpu128-dedup"


class VLMOutputError(ValueError):
    def __init__(self, evidence):
        super().__init__("vlm_invalid_output_after_evidence_deduplication")
        self.evidence = evidence


def normalize_frame_indices(parsed, seconds):
    if not 1 <= len(seconds) <= 4 or any(
        type(s) not in (int, float) or not math.isfinite(s) or s < 0 for s in seconds
    ):
        raise ValueError("invalid_vlm_input_timestamps")
    if not isinstance(parsed, dict) or set(parsed) != set(FIELDS):
        raise ValueError("invalid_vlm_object")
    normalized = copy.deepcopy(parsed)
    for field, item in normalized.items():
        if not isinstance(item, dict) or set(item) != {"value", "frames"}:
            raise ValueError("invalid_vlm_field_structure")
        frames = item["frames"]
        allowed = [
            i for i, s in enumerate(seconds, 1) if field != "product_visible_early" or s <= 3
        ]
        if (
            not isinstance(frames, list)
            or len(frames) > len(allowed)
            or any(type(i) is not int or i not in allowed for i in frames)
        ):
            raise ValueError("invalid_vlm_frame_evidence")
        item["frames"] = list(dict.fromkeys(frames))
    status, _ = validate_vlm_answer(json.dumps(normalized), seconds)
    if status != "schema_valid_requires_perception_review":
        raise ValueError("invalid_vlm_value_or_missing_evidence")
    return normalized


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_json_key")
        result[key] = value
    return result


def parse_normalized_output(text, seconds):
    decoder = json.JSONDecoder(object_pairs_hook=_unique_object)
    for offset, character in enumerate(text):
        if character != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(text[offset:])
            normalized = normalize_frame_indices(parsed, seconds)
        except ValueError:
            continue
        return parsed, normalized
    raise ValueError("no_complete_attribute_object_with_valid_evidence")


def extract_visual_attributes(frame_paths, frame_seconds, work):
    # Keep this prompt byte-identical to the frozen v5 adapter (verified by a test).
    timeline = "; ".join(
        f"frame {i} = {seconds:.3f} seconds" for i, seconds in enumerate(frame_seconds, 1)
    )
    prompt = (
        "Inspect only these chronological video samples: " + timeline + ". "
        "Return the JSON object specified by the schema. Each value must cite the 1-based frames "
        "where it is visible. Use unknown and an empty frames array when uncertain. "
        "person_visible: visible human face or body; garments without a wearer are not people. "
        "product_visible_early: a displayed cosmetic, applicator, garment or fashion accessory in "
        "samples at or before 3 seconds. Incidental clothing worn by a speaker alone does not count. "
        "product_closeup: a product shown close enough to inspect its detail; a face alone is insufficient. "
        "demonstration: visible application or use, such as a brush touching skin; holding a package alone "
        "is not application. screen_text: presence of text, not OCR transcription. "
        "scene: indoor, outdoor, graphic, mixed or unknown. "
        "format: reaction for a split-screen reacting presenter; application for visible use; "
        "product_showcase for displayed items; talking_head for a presenter; mixed, other or unknown. "
        "When reaction and application coexist, use reaction. Do not infer audio, views, emotion or intent."
    )
    output = invoke_local_vlm(frame_paths, prompt, work, attribute_schema(frame_seconds))
    raw_sha256 = hashlib.sha256(output["raw_response"].encode()).hexdigest()
    try:
        raw_parsed, normalized = parse_normalized_output(output["raw_response"], frame_seconds)
    except ValueError as exc:
        raise VLMOutputError(
            {
                "schema_version": "vlm-rejected-output-v1",
                "normalization_policy": NORMALIZATION_POLICY,
                "model": model_manifest(),
                "input_frame_seconds": frame_seconds,
                "raw_response_sha256": raw_sha256,
                **output,
            }
        ) from exc
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "schema_valid_requires_perception_review",
        "model_parsed": raw_parsed,
        "normalized_model_parsed": normalized,
        "normalization_policy": NORMALIZATION_POLICY,
        "deduplicated_fields": [k for k in FIELDS if raw_parsed[k] != normalized[k]],
        "raw_response_sha256": raw_sha256,
        "parsed": apply_quality_policy(normalized),
        "quality_policy": QUALITY_POLICY,
        "withheld_attributes": WITHHELD_ATTRIBUTES,
        "input_frame_seconds": frame_seconds,
        "model": model_manifest(),
        "approved_for_training": False,
        "evidence_scope": "committed sampled contact-sheet cells; perception review required",
        **output,
    }

"""Strict seven-field structure, independent of transport and perception quality.

JSON Schema cannot distinguish the JSON numbers 1 and 1.0. The independent
parser additionally requires lexically integral frame indices (Python ints).
No schema/grammar or hosted response_format support is presumed by this module.
"""

from __future__ import annotations

import json
import math

from scripts.full_visual_contract_v7 import parse_json
from scripts.visual_attributes import FIELDS, FORMATS, SCENES, validate_vlm_answer

BOOLEAN_FIELDS = FIELDS[:5]
SCHEMA_VERSION = "visual-attributes-seven-v1"


def validate_timeline(frame_seconds):
    """Validate 1–4 chronological samples in the closed interval [0, 60]."""
    if type(frame_seconds) is not list or not 1 <= len(frame_seconds) <= 4:
        raise ValueError("seven_invalid_frame_timeline")
    try:
        valid = all(
            type(second) in (int, float) and math.isfinite(second) and 0 <= second <= 60
            for second in frame_seconds
        )
    except OverflowError:
        valid = False
    if not valid or frame_seconds != sorted(set(frame_seconds)):
        raise ValueError("seven_invalid_frame_timeline")


def parse_attributes(raw, frame_seconds):
    """Return the complete, unmodified seven-field object or a static ValueError.

    Compose the frozen duplicate-free JSON parser and legacy attribute validator,
    then close the unknown/evidence gap. Never repair, normalize or withhold values.
    """
    validate_timeline(frame_seconds)
    try:
        parsed = parse_json(raw)
        # allow_nan=False also rejects finite-JSON exponents overflowing to infinity.
        encoded = json.dumps(parsed, allow_nan=False)
        status, _ = validate_vlm_answer(encoded, frame_seconds)
    except (ValueError, TypeError, OverflowError, RecursionError):
        raise ValueError("seven_invalid_json_or_attributes") from None
    if status != "schema_valid_requires_perception_review":
        raise ValueError("seven_invalid_attributes")
    if any(item["value"] == "unknown" and item["frames"] != [] for item in parsed.values()):
        raise ValueError("seven_unknown_requires_empty_frames")
    return parsed


def build_schema(frame_seconds):
    """Build a schema with separate unknown and known-with-evidence branches.

    An operator may wrap this as response_format={"type": "json_schema",
    "json_schema": {"name": SCHEMA_VERSION, "schema": schema}} only after checking
    the deployment's support. This function neither contacts nor validates a provider.
    """
    validate_timeline(frame_seconds)
    properties = {}
    for field in FIELDS:
        unknown = {
            "type": "object",
            "properties": {
                "value": {"const": "unknown"},
                "frames": {"type": "array", "maxItems": 0},
            },
            "required": ["value", "frames"],
            "additionalProperties": False,
        }
        frames = [
            index
            for index, second in enumerate(frame_seconds, 1)
            if field != "product_visible_early" or second <= 3
        ]
        branches = [unknown]
        if frames:
            choices = SCENES if field == "scene" else FORMATS
            value_schema = (
                {"type": "boolean"}
                if field in BOOLEAN_FIELDS
                else {"type": "string", "enum": [v for v in choices if v != "unknown"]}
            )
            branches.append(
                {
                    "type": "object",
                    "properties": {
                        "value": value_schema,
                        "frames": {
                            "type": "array",
                            "items": {"type": "integer", "enum": frames},
                            "minItems": 1,
                            "maxItems": len(frames),
                            "uniqueItems": True,
                        },
                    },
                    "required": ["value", "frames"],
                    "additionalProperties": False,
                }
            )
        properties[field] = {"oneOf": branches}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": properties,
        "required": list(FIELDS),
        "additionalProperties": False,
    }


def build_generation_schema(frame_seconds):
    """Build a simple generation superset, independent of provider support.

    The strict parser still enforces evidence for known values, empty evidence
    for unknown, unique frame indices and the early-product time boundary.
    This profile deliberately leaves those relationships to that parser.
    """
    validate_timeline(frame_seconds)
    count = len(frame_seconds)
    properties = {}
    for field in FIELDS:
        value = (
            {"enum": [True, False, "unknown"]}
            if field in BOOLEAN_FIELDS
            else {"type": "string", "enum": list(SCENES if field == "scene" else FORMATS)}
        )
        properties[field] = {
            "type": "object",
            "properties": {
                "value": value,
                "frames": {
                    "type": "array",
                    "items": {"type": "integer", "minimum": 1, "maximum": count},
                    "maxItems": count,
                },
            },
            "required": ["value", "frames"],
            "additionalProperties": False,
        }
    return {
        "type": "object",
        "properties": properties,
        "required": list(FIELDS),
        "additionalProperties": False,
    }


def build_prompt(frame_seconds):
    """Describe the original rubrics and explicit types without reference answers."""
    validate_timeline(frame_seconds)
    timeline = "; ".join(
        f"frame {index} = {second!r} seconds" for index, second in enumerate(frame_seconds, 1)
    )
    return (
        f"Inspect only these chronological video samples: {timeline}. "
        "Return exactly one JSON object, with no prose or markdown. Its seven required fields are "
        + ", ".join(FIELDS)
        + '. Each field is an object with exactly "value" and "frames". '
        + ", ".join(BOOLEAN_FIELDS)
        + ': each value must be JSON true, JSON false, or the string "unknown". '
        "scene value must be a string in "
        + json.dumps(SCENES)
        + "; format value must be a string in "
        + json.dumps(FORMATS)
        + ". frames must be a JSON array of unique 1-based integer indices supporting the value. "
        'Known values, including false, require nonempty frames. Use "unknown" with frames=[] when uncertain. '
        "person_visible: visible human face or body; garments without a wearer are not people. "
        "product_visible_early: a displayed cosmetic, applicator, garment or fashion accessory in "
        "samples at or before 3 seconds. Incidental clothing worn by a speaker alone does not count. "
        "Cite only frames at or before 3 seconds for this field; if none exist use unknown. "
        "product_closeup: a product shown close enough to inspect its detail; a face alone is insufficient. "
        "demonstration: visible application or use, such as a brush touching skin; holding a package alone "
        "is not application. screen_text: classify presence of text; never transcribe OCR text into value. "
        "format: reaction for a split-screen reacting presenter; application for visible use; "
        "product_showcase for displayed items; talking_head for a presenter; mixed, other or unknown. "
        "When reaction and application coexist, use reaction. Do not infer audio, views, emotion or intent."
    )

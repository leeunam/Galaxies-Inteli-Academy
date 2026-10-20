"""Product-only V9: observable presentation states with deterministic evidence."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import tempfile

from PIL import Image

from scripts.gguf_visual_attributes import invoke_local_vlm, model_manifest
from scripts.private_checkpoint import digest, file_hash
from scripts.vlm_explicit_presence import specification as baseline_specification
from scripts.vlm_per_frame import BOOLEAN_FIELDS, aggregate, parse_output

VERSION = "visual-attributes-v9-product-states"
FIELD = "product_visible_early"
VARIANTS = ("enum_false_first", "examples_false_first", "neutral_key", "structured")
CATEGORIES = ("cosmetic", "applicator", "garment", "accessory")
STATES = ("no_target", "incidental_only", "presented_target", "uncertain")
PROMPT = (
    "Inspect only this single image. Classify the observable presentation of cosmetics, "
    "applicators, garments or fashion accessories. Do not infer marketing intent, audio, "
    "another frame or unseen motion. Choose exactly one state:\n"
    "no_target: no target item is visible after inspecting the image.\n"
    "incidental_only: all visible target items are clearly incidental rather than presented, "
    "such as a speaker's ordinary clothing or jewelry. Background location alone does not "
    "prove incidental status. No presented or ambiguous target item is visible.\n"
    "presented_target: at least one target item is displayed, held up, laid out, clearly "
    "showcased or visibly shown in use. Simply wearing clothing or jewelry is not enough. "
    "The identified item must be the SAME item whose presentation is visible. A confirmed "
    "presented item wins even if other items are incidental or ambiguous.\n"
    "uncertain: no presented target is confirmed and a target or its presentation is unclear.\n"
    "Return exactly a JSON object with state and presented_categories. List only witnessed "
    "presented categories: cosmetic, applicator, garment, accessory; no duplicates, at most "
    "four. Multiple presented items may contribute categories. For presented_target the "
    "list must be nonempty. For all other states the list must be empty. Examples: "
    '{"state":"no_target","presented_categories":[]}; '
    '{"state":"incidental_only","presented_categories":[]}; '
    '{"state":"presented_target","presented_categories":["cosmetic"]}; '
    '{"state":"uncertain","presented_categories":[]}. Do not write explanations.'
)


def specification(variant):
    if variant not in VARIANTS:
        raise ValueError("invalid_product_variant")
    spec = copy.deepcopy(baseline_specification()[1])
    if variant == "enum_false_first":
        spec["schema"]["properties"][FIELD]["enum"] = [False, True, "unknown"]
    elif variant == "examples_false_first":
        positive = json.dumps({FIELD: True}) + " for visible presence"
        negative = json.dumps({FIELD: False}) + " for absence"
        original = positive + ", " + negative
        if spec["prompt"].count(original) != 1:
            raise ValueError("product_baseline_instruction_changed")
        spec["prompt"] = spec["prompt"].replace(original, negative + ", " + positive)
    elif variant == "neutral_key":
        spec["fields"] = ["answer"]
        spec["schema"]["properties"] = {"answer": spec["schema"]["properties"][FIELD]}
        spec["schema"]["required"] = ["answer"]
        spec["prompt"] = spec["prompt"].replace(json.dumps(FIELD), json.dumps("answer"))
    else:
        spec = {
            "fields": ["state", "presented_categories"],
            "prompt": PROMPT,
            "schema": {
                "type": "object",
                "properties": {
                    "state": {"enum": list(STATES)},
                    "presented_categories": {
                        "type": "array",
                        "items": {"enum": list(CATEGORIES)},
                        "maxItems": 4,
                    },
                },
                "required": ["state", "presented_categories"],
                "additionalProperties": False,
            },
            "max_tokens": 64,
        }
    return spec


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_product_json_key")
        result[key] = value
    return result


def decode(raw, variant):
    if variant != "structured":
        fields = specification(variant)["fields"]
        parsed = parse_output(raw, fields)
        return parsed, parsed[fields[0]]
    parsed = json.loads(raw, object_pairs_hook=_unique)
    if type(parsed) is not dict or set(parsed) != {"state", "presented_categories"}:
        raise ValueError("invalid_product_state_object")
    state = parsed["state"]
    categories = parsed["presented_categories"]
    if (
        type(state) is not str
        or state not in STATES
        or type(categories) is not list
        or len(categories) > 4
        or any(type(v) is not str or v not in CATEGORIES for v in categories)
        or len(set(categories)) != len(categories)
        or (state == "presented_target") != bool(categories)
    ):
        raise ValueError("invalid_or_contradictory_product_state")
    return (
        parsed,
        True if state == "presented_target" else "unknown" if state == "uncertain" else False,
    )


def _save_call(path, body):
    # ASCII JSON preserves even an invalid UTF-8 string returned by a faulty adapter.
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf-8") as out:
        json.dump(body, out, ensure_ascii=True, allow_nan=False, indent=2)
        out.write("\n")
    os.replace(out.name, path)


def extract(cells, seconds, work, *, variant, evidence_dir, invoker=invoke_local_vlm):
    spec = specification(variant)
    aggregate([{f: "unknown" for f in BOOLEAN_FIELDS} for _ in cells], seconds)
    inputs = [file_hash(p) for p in cells]
    for index, cell in enumerate(cells):
        with Image.open(cell) as image:
            if image.format != "PNG" or image.mode != "RGB" or image.size != (320, 330):
                raise ValueError("product_pixels_changed")
            image.verify()
        if file_hash(cell) != inputs[index]:
            raise ValueError("product_pixels_changed")
    evidence_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    intermediate, frames, calls = [], [], []
    for index, cell in enumerate(cells, 1):
        path = evidence_dir / f"frame-{index}.json"
        call = {
            "schema_version": VERSION,
            "variant": variant,
            "frame": index,
            "input_png_sha256": inputs[index - 1],
            "specification_sha256": digest(spec),
            "status": "running",
        }
        _save_call(path, call)
        try:
            if file_hash(cell) != inputs[index - 1]:
                raise ValueError("product_pixels_changed")
            output = invoker(
                [cell], spec["prompt"], work, spec["schema"], max_tokens=spec["max_tokens"]
            )
            call.update(output, status="response_captured")
            _save_call(path, call)
            if type(output.get("raw_response")) is not str:
                raise ValueError("invalid_product_native_raw_type")
            call["raw_response_sha256"] = hashlib.sha256(
                output["raw_response"].encode()
            ).hexdigest()
            _save_call(path, call)
            if file_hash(cell) != inputs[index - 1]:
                raise ValueError("product_pixels_changed")
            parsed, value = decode(output["raw_response"], variant)
        except BaseException as exc:
            call.update(status="failed", error_type=type(exc).__name__)
            _save_call(path, call)
            raise
        call.update(status="completed", parsed=parsed)
        _save_call(path, call)
        intermediate.append(parsed)
        frames.append({f: value if f == FIELD else "unknown" for f in BOOLEAN_FIELDS})
        calls.append({"path": path.name, "sha256": file_hash(path)})
    return {
        "schema_version": VERSION,
        "variant": variant,
        "model": model_manifest(),
        "specification_sha256": digest(spec),
        "input_png_sha256": inputs,
        "input_frame_seconds": seconds,
        "intermediate": intermediate,
        "per_frame": frames,
        "parsed": aggregate(frames, seconds),
        "calls": calls,
        "approved_for_training": False,
    }


def verify(result, evidence_dir):
    spec = specification(result["variant"])
    if (
        result["schema_version"] != VERSION
        or result["model"] != model_manifest()
        or result["specification_sha256"] != digest(spec)
        or result["approved_for_training"] is not False
    ):
        raise ValueError("incompatible_product_result")
    frames, intermediate, calls = [], [], []
    for index, sha in enumerate(result["input_png_sha256"], 1):
        path = evidence_dir / f"frame-{index}.json"
        call = json.loads(path.read_bytes())
        parsed, value = decode(call["raw_response"], result["variant"])
        if (
            call["schema_version"] != VERSION
            or call["variant"] != result["variant"]
            or call["frame"] != index
            or call["status"] != "completed"
            or call["input_png_sha256"] != sha
            or call["specification_sha256"] != digest(spec)
            or call["raw_response_sha256"]
            != hashlib.sha256(call["raw_response"].encode()).hexdigest()
            or call["parsed"] != parsed
        ):
            raise ValueError("product_call_evidence_changed")
        frames.append({f: value if f == FIELD else "unknown" for f in BOOLEAN_FIELDS})
        intermediate.append(parsed)
        calls.append({"path": path.name, "sha256": file_hash(path)})
    if (
        calls != result["calls"]
        or intermediate != result["intermediate"]
        or frames != result["per_frame"]
        or aggregate(frames, result["input_frame_seconds"]) != result["parsed"]
    ):
        raise ValueError("product_derivation_changed")
    return result["parsed"]

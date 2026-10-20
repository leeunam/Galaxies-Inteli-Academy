"""Product V11: bounded visual cue, strict contradictions, unchanged temporal mapper."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile

from PIL import Image

from scripts.gguf_visual_attributes import invoke_local_vlm, model_manifest
from scripts.private_checkpoint import digest, file_hash
from scripts.vlm_per_frame import BOOLEAN_FIELDS, aggregate
from scripts.vlm_product_states import CATEGORIES, FIELD, STATES, _unique

VERSION = "visual-attributes-v11-presentation-cue"
POSITIVE_CUES = ("held_display", "isolated_display", "visible_use", "worn_detail_focus")
OTHER_CUES = {"no_target": "absent", "incidental_only": "incidental", "uncertain": "uncertain"}
PROMPT = (
    "Inspect only this image for cosmetics, applicators, garments and fashion accessories. "
    "Use visible evidence of the SAME item, not marketing intent, text meaning, audio, "
    "another frame or unseen motion. Choose a state and its presentation_cue:\n"
    "presented_target: a target item has a confirmed cue: "
    "held_display = held out to display, including fabric pulled out to show a worn garment; "
    "merely holding an object is insufficient. "
    "isolated_display = an item clearly displayed or laid out, such as a foreground garment "
    "on a hanger; a rack behind a speaker is insufficient. "
    "visible_use = an explicit visible action using the target, such as an applicator "
    "touching skin; wearing clothing or jewelry alone is insufficient. "
    "worn_detail_focus = framing clearly showcases an identifiable garment detail: cut, "
    "finish, fastening or fabric. A visible pattern, face with clothing or full-body view "
    "alone is insufficient. Select one witnessed cue and list only presented_categories "
    "whose presentation is visible. At least one listed category must contain the SAME "
    "item with the selected cue. A confirmed presented item wins over incidental or "
    "ambiguous other items.\n"
    "incidental_only with cue incidental: ALL visible targets are clearly incidental, "
    "with no presented or ambiguous target. Background location alone is insufficient.\n"
    "no_target with cue absent: no target item is visible after inspection.\n"
    "uncertain with cue uncertain: no presented item is confirmed and a target or its "
    "presentation is unclear. Ambiguous presentation is uncertain, not incidental_only.\n"
    "Return exactly JSON with state, presented_categories and presentation_cue. "
    "States: no_target, incidental_only, presented_target, uncertain. Categories: cosmetic, "
    "applicator, garment, accessory; no duplicates, at most four. For presented_target, "
    "categories are nonempty and cue is one of the four positive cues. For other states, "
    "categories are empty and cue must match that state above. No explanations."
)


def specification():
    fields = ["state", "presented_categories", "presentation_cue"]
    return {
        "fields": fields,
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
                "presentation_cue": {"enum": [*POSITIVE_CUES, *OTHER_CUES.values()]},
            },
            "required": fields,
            "additionalProperties": False,
        },
        "max_tokens": 64,
    }


def decode(raw):
    parsed = json.loads(raw, object_pairs_hook=_unique)
    if type(parsed) is not dict or set(parsed) != set(specification()["fields"]):
        raise ValueError("v11_invalid_state_object")
    state, cats, cue = (parsed[k] for k in specification()["fields"])
    if (
        type(state) is not str
        or state not in STATES
        or type(cats) is not list
        or len(cats) > 4
        or any(type(v) is not str or v not in CATEGORIES for v in cats)
        or len(set(cats)) != len(cats)
        or type(cue) is not str
        or (state == "presented_target") != bool(cats)
        or (cue == "worn_detail_focus" and "garment" not in cats)
        or (
            cue not in POSITIVE_CUES
            if state == "presented_target"
            else cue != OTHER_CUES.get(state)
        )
    ):
        raise ValueError("v11_contradictory_state_or_cue")
    return (
        parsed,
        True if state == "presented_target" else "unknown" if state == "uncertain" else False,
    )


def save(path, body):
    """ASCII-safe atomic record, fsync file and directory before any dispatch."""
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    staged = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as out:
            staged = out.name
            json.dump(body, out, ensure_ascii=True, allow_nan=False, indent=2)
            out.write("\n")
            out.flush()
            os.fsync(out.fileno())
        os.replace(staged, path)
        staged = None
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if staged is not None:
            os.unlink(staged)


def extract(cells, seconds, work, *, evidence_dir, reserve, invoker=invoke_local_vlm):
    aggregate([{f: "unknown" for f in BOOLEAN_FIELDS} for _ in cells], seconds)
    inputs = [file_hash(p) for p in cells]
    for cell in cells:
        with Image.open(cell) as image:
            if image.format != "PNG" or image.mode != "RGB" or image.size != (320, 330):
                raise ValueError("v11_pixels_changed")
            image.verify()
    evidence_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    spec = specification()
    frames, intermediate, calls = [], [], []
    for index, cell in enumerate(cells, 1):
        if file_hash(cell) != inputs[index - 1]:
            raise ValueError("v11_pixels_changed")
        reserve(index)
        path = evidence_dir / f"frame-{index}.json"
        call = {
            "schema_version": VERSION,
            "frame": index,
            "input_png_sha256": inputs[index - 1],
            "specification_sha256": digest(spec),
            "status": "running",
        }
        save(path, call)
        try:
            output = invoker([cell], spec["prompt"], work, spec["schema"], max_tokens=64)
            call.update(output, status="response_captured")
            save(path, call)
            if type(output.get("raw_response")) is not str:
                raise ValueError("v11_invalid_raw_type")
            call["raw_response_sha256"] = hashlib.sha256(
                output["raw_response"].encode()
            ).hexdigest()
            save(path, call)
            if file_hash(cell) != inputs[index - 1]:
                raise ValueError("v11_pixels_changed")
            parsed, value = decode(output["raw_response"])
        except BaseException as error:
            call.update(status="failed", error_type=type(error).__name__)
            save(path, call)
            raise
        call.update(status="completed", parsed=parsed)
        save(path, call)
        intermediate.append(parsed)
        frames.append({f: value if f == FIELD else "unknown" for f in BOOLEAN_FIELDS})
        calls.append({"path": path.name, "sha256": file_hash(path)})
    return {
        "schema_version": VERSION,
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
    if (
        result["schema_version"] != VERSION
        or result["model"] != model_manifest()
        or result["specification_sha256"] != digest(specification())
        or result["approved_for_training"] is not False
        or len(result["calls"]) != len(result["input_png_sha256"])
    ):
        raise ValueError("v11_result_configuration_changed")
    frames, intermediate, calls = [], [], []
    for index, expected in enumerate(result["input_png_sha256"], 1):
        path = evidence_dir / f"frame-{index}.json"
        call = json.loads(path.read_bytes())
        parsed, value = decode(call["raw_response"])
        if (
            call["schema_version"] != VERSION
            or call["frame"] != index
            or call["status"] != "completed"
            or call["input_png_sha256"] != expected
            or call["specification_sha256"] != digest(specification())
            or hashlib.sha256(call["raw_response"].encode()).hexdigest()
            != call["raw_response_sha256"]
            or parsed != call["parsed"]
        ):
            raise ValueError("v11_native_receipt_changed")
        frames.append({f: value if f == FIELD else "unknown" for f in BOOLEAN_FIELDS})
        intermediate.append(parsed)
        calls.append({"path": path.name, "sha256": file_hash(path)})
    if (
        calls != result["calls"]
        or intermediate != result["intermediate"]
        or frames != result["per_frame"]
        or aggregate(frames, result["input_frame_seconds"]) != result["parsed"]
    ):
        raise ValueError("v11_derivation_changed")
    return result["parsed"]

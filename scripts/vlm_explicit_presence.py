"""V8: explicit JSON and one visual presence question per attribute/frame."""

from __future__ import annotations

import hashlib
import json

from PIL import Image

from scripts.gguf_visual_attributes import invoke_local_vlm, model_manifest
from scripts.private_checkpoint import digest, file_hash, save
from scripts.vlm_per_frame import BOOLEAN_FIELDS, aggregate, parse_output

VERSION = "visual-attributes-v8-explicit-presence"
QUESTIONS = {
    "person_visible": (
        "In this single image, is any part of a real human visible? Check the face, head, "
        "hands, arms, legs and partial body before answering no. A garment without a wearer, "
        "mannequin, drawing or face printed on packaging is not a real human."
    ),
    "product_visible_early": (
        "In this single image, is a cosmetic, applicator, garment or fashion accessory visibly "
        "presented: displayed, held up, laid out, clearly showcased or shown in use? Seeing a "
        "speaker's incidental clothing or jewelry alone is not enough. Require visible "
        "presentation of the item, not an inferred marketing intention. If presentation "
        "versus incidental wearing cannot be determined, answer unknown."
    ),
    "screen_text": (
        "Does this image contain any written letters or numbers? Detect presence, even if "
        "the words cannot be read."
    ),
}


def specification():
    specs = []
    for field in BOOLEAN_FIELDS:
        if field == "screen_text":
            instruction = (
                'Return exactly one JSON object: {"screen_text": true} for visible letters or '
                'numbers, {"screen_text": false} for no text, or {"screen_text": "unknown"} '
                "if unsure. Do not transcribe the words."
            )
        else:
            instruction = (
                f"Return exactly one JSON object: {json.dumps({field: True})} for visible "
                f"presence, {json.dumps({field: False})} for absence, or "
                f"{json.dumps({field: 'unknown'})} if unsure. Do not write explanations."
            )
        specs.append(
            {
                "fields": [field],
                "prompt": QUESTIONS[field] + " " + instruction,
                "schema": {
                    "type": "object",
                    "properties": {field: {"enum": [True, False, "unknown"]}},
                    "required": [field],
                    "additionalProperties": False,
                },
                "max_tokens": 64,
            }
        )
    return specs


def extract(cells, seconds, work, *, evidence_dir, invoker=invoke_local_vlm):
    if len(cells) != len(seconds):
        raise ValueError("v8_input_count_mismatch")
    aggregate([{f: "unknown" for f in BOOLEAN_FIELDS} for _ in cells], seconds)
    inputs = [file_hash(p) for p in cells]
    for index, path in enumerate(cells):
        with Image.open(path) as picture:
            if picture.format != "PNG" or picture.mode != "RGB" or picture.size != (320, 330):
                raise ValueError("v8_input_pixels_changed")
            picture.verify()
        if file_hash(path) != inputs[index]:
            raise ValueError("v8_input_pixels_changed")
    if evidence_dir.exists():
        raise ValueError("v8_evidence_already_exists")
    evidence_dir.mkdir(parents=True, mode=0o700)
    frames, calls = [], []
    for index, cell in enumerate(cells):
        values = {}
        for group, spec in enumerate(specification()):
            path = evidence_dir / f"frame-{index + 1}-group-{group + 1}.json"
            call = {
                "schema_version": VERSION,
                "frame": index + 1,
                "input_png_sha256": inputs[index],
                "specification_sha256": digest(spec),
                "status": "running",
            }
            save(path, call)
            try:
                if file_hash(cell) != inputs[index]:
                    raise ValueError("v8_input_pixels_changed")
                output = invoker(
                    [cell], spec["prompt"], work, spec["schema"], max_tokens=spec["max_tokens"]
                )
                call.update(output)
                call["raw_response_sha256"] = hashlib.sha256(
                    output["raw_response"].encode()
                ).hexdigest()
                call["status"] = "response_captured"
                save(path, call)
                if file_hash(cell) != inputs[index]:
                    raise ValueError("v8_input_pixels_changed")
                parsed = parse_output(output["raw_response"], spec["fields"])
            except BaseException as exc:
                call.update(status="failed", error_type=type(exc).__name__)
                save(path, call)
                raise
            values.update(parsed)
            call.update(status="completed", parsed=parsed)
            save(path, call)
            calls.append({"path": path.name, "sha256": file_hash(path)})
        frames.append(values)
    return {
        "schema_version": VERSION,
        "model": model_manifest(),
        "specification_sha256": digest(specification()),
        "input_png_sha256": inputs,
        "input_frame_seconds": seconds,
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
    ):
        raise ValueError("incompatible_v8_result")
    frames, calls = [], []
    for index, image_hash in enumerate(result["input_png_sha256"]):
        values = {}
        for group, spec in enumerate(specification()):
            path = evidence_dir / f"frame-{index + 1}-group-{group + 1}.json"
            call = json.loads(path.read_bytes())
            if (
                call["schema_version"] != VERSION
                or call["status"] != "completed"
                or call["frame"] != index + 1
                or call["input_png_sha256"] != image_hash
                or call["specification_sha256"] != digest(spec)
                or call["raw_response_sha256"]
                != hashlib.sha256(call["raw_response"].encode()).hexdigest()
                or call["parsed"] != parse_output(call["raw_response"], spec["fields"])
            ):
                raise ValueError("v8_call_evidence_changed")
            values.update(call["parsed"])
            calls.append({"path": path.name, "sha256": file_hash(path)})
        frames.append(values)
    if (
        calls != result["calls"]
        or frames != result["per_frame"]
        or aggregate(frames, result["input_frame_seconds"]) != result["parsed"]
    ):
        raise ValueError("v8_derivation_changed")
    return result["parsed"]

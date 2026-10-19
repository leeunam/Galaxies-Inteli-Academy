"""Versioned frame-local boolean perception, with deterministic temporal evidence."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from PIL import Image

from scripts.gguf_visual_attributes import invoke_local_vlm, model_manifest
from scripts.private_checkpoint import digest, file_hash, save
from scripts.visual_attributes import FIELDS

VERSION = "visual-attributes-v7-frame-local-booleans"
BOOLEAN_FIELDS = ("person_visible", "product_visible_early", "screen_text")
CANDIDATES = ("A", "B")
RUBRICS = {
    "person_visible": (
        "Is an actual human face or body part visible, including a hand or arm? "
        "A garment without a wearer, mannequin, drawing or face printed on packaging is not a person."
    ),
    "product_visible_early": (
        "Is a cosmetic, applicator, garment or fashion accessory visibly presented as an item of "
        "interest? A displayed package, brush, item held up, laid out or explicitly showcased counts. "
        "Incidental clothing or jewelry worn by a speaker alone does not count."
    ),
    "screen_text": (
        "Are text characters visibly present anywhere in this image, including captions, labels "
        "or packaging? Do not transcribe or guess the words. Texture or indistinct marks alone "
        "are not evidence of text."
    ),
}
PREFIX = (
    "Inspect only this single image. Answer only what is visually observable in this image. "
    "Return the JSON object required by the schema. Use true for visible presence, false for "
    "visible absence, and the string unknown when uncertain. Do not infer another frame, audio, "
    "views or intent. Do not write explanations. "
)


def specification(candidate):
    if candidate not in CANDIDATES:
        raise ValueError("invalid_frame_local_candidate")
    groups = (BOOLEAN_FIELDS,) if candidate == "A" else tuple((f,) for f in BOOLEAN_FIELDS)
    result = []
    for group in groups:
        schema = {
            "type": "object",
            "properties": {f: {"enum": [True, False, "unknown"]} for f in group},
            "required": list(group),
            "additionalProperties": False,
        }
        prompt = PREFIX + " ".join(f"{f}: {RUBRICS[f]}" for f in group)
        result.append(
            {
                "fields": list(group),
                "prompt": prompt,
                "schema": schema,
                "max_tokens": 96 if candidate == "A" else 64,
            }
        )
    return result


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_frame_local_json_key")
        result[key] = value
    return result


def parse_output(raw, fields):
    value = json.loads(raw, object_pairs_hook=_unique)
    if (
        not isinstance(value, dict)
        or set(value) != set(fields)
        or not all(type(v) is bool or v == "unknown" for v in value.values())
    ):
        raise ValueError("invalid_or_ambiguous_frame_local_json")
    return value


def aggregate(frames, seconds):
    if (
        not 1 <= len(frames) == len(seconds) <= 4
        or any(type(s) not in (int, float) or not math.isfinite(s) or s < 0 for s in seconds)
        or seconds != sorted(set(seconds))
    ):
        raise ValueError("invalid_frame_local_timeline")
    for values in frames:
        if set(values) != set(BOOLEAN_FIELDS) or any(
            type(v) is not bool and v != "unknown" for v in values.values()
        ):
            raise ValueError("invalid_frame_local_values")
    result = {f: {"value": "unknown", "frames": []} for f in FIELDS}
    for field in BOOLEAN_FIELDS:
        eligible = [i for i, s in enumerate(seconds) if field != "product_visible_early" or s <= 3]
        positive = [i + 1 for i in eligible if frames[i][field] is True]
        if positive:
            result[field] = {"value": True, "frames": positive}
        elif eligible and all(frames[i][field] is False for i in eligible):
            result[field] = {"value": False, "frames": [i + 1 for i in eligible]}
    return result


def extract(cells, seconds, work, *, candidate, evidence_dir, invoker=invoke_local_vlm):
    if len(cells) != len(seconds):
        raise ValueError("frame_local_input_count_mismatch")
    # Check timestamps before invoking even the first model.
    aggregate([{f: "unknown" for f in BOOLEAN_FIELDS} for _ in cells], seconds)
    for cell in cells:
        with Image.open(cell) as picture:
            if picture.format != "PNG" or picture.mode != "RGB" or picture.size != (320, 330):
                raise ValueError("invalid_frame_local_input_pixels")
            picture.verify()
    if evidence_dir.exists():
        raise ValueError("frame_local_evidence_output_exists")
    evidence_dir.mkdir(parents=True, mode=0o700)
    inputs = [file_hash(p) for p in cells]
    per_frame, calls = [], []
    specs = specification(candidate)
    for index, cell in enumerate(cells):
        values = {}
        for group_index, spec in enumerate(specs):
            path = evidence_dir / f"frame-{index + 1}-group-{group_index + 1}.json"
            call = {
                "schema_version": VERSION,
                "candidate": candidate,
                "frame": index + 1,
                "input_png_sha256": inputs[index],
                "specification_sha256": digest(spec),
                "status": "running",
            }
            save(path, call)
            try:
                output = invoker(
                    [cell], spec["prompt"], work, spec["schema"], max_tokens=spec["max_tokens"]
                )
                call.update(output)
                call["raw_response_sha256"] = hashlib.sha256(
                    output["raw_response"].encode()
                ).hexdigest()
                call["status"] = "response_captured"
                save(path, call)  # Preserve the response before attempting to parse it.
                parsed = parse_output(output["raw_response"], spec["fields"])
            except BaseException as exc:
                call.update(status="failed", error_type=type(exc).__name__)
                save(path, call)
                raise
            values.update(parsed)
            call.update(status="completed", parsed=parsed)
            save(path, call)
            calls.append({"path": path.name, "sha256": file_hash(path)})
        per_frame.append(values)
    return {
        "schema_version": VERSION,
        "candidate": candidate,
        "model": model_manifest(),
        "specification_sha256": digest(specs),
        "input_frame_seconds": seconds,
        "input_png_sha256": inputs,
        "per_frame": per_frame,
        "parsed": aggregate(per_frame, seconds),
        "calls": calls,
        "approved_for_training": False,
    }


def verify(result, evidence_dir: Path):
    if (
        result["schema_version"] != VERSION
        or result["model"] != model_manifest()
        or (
            result["specification_sha256"] != digest(specification(result["candidate"]))
            or result["approved_for_training"] is not False
        )
    ):
        raise ValueError("incompatible_frame_local_result")
    specs = specification(result["candidate"])
    expected = []
    reconstructed = []
    for index, image_hash in enumerate(result["input_png_sha256"]):
        frame = {}
        for group, spec in enumerate(specs):
            name = f"frame-{index + 1}-group-{group + 1}.json"
            path = evidence_dir / name
            call = json.loads(path.read_bytes())
            if (
                call["status"] != "completed"
                or call["schema_version"] != VERSION
                or call["candidate"] != result["candidate"]
                or call["frame"] != index + 1
                or call["input_png_sha256"] != image_hash
                or call["specification_sha256"] != digest(spec)
                or call["raw_response_sha256"]
                != hashlib.sha256(call["raw_response"].encode()).hexdigest()
                or call["parsed"] != parse_output(call["raw_response"], spec["fields"])
            ):
                raise ValueError("frame_local_call_evidence_changed")
            frame.update(call["parsed"])
            expected.append({"path": name, "sha256": file_hash(path)})
        reconstructed.append(frame)
    if (
        result["calls"] != expected
        or result["per_frame"] != reconstructed
        or (result["parsed"] != aggregate(reconstructed, result["input_frame_seconds"]))
    ):
        raise ValueError("frame_local_derivation_changed")
    return result["parsed"]

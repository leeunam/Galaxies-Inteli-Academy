"""Product V10: one frozen prompt insertion; unchanged V9 decoder and mapper."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile

from PIL import Image

from scripts.gguf_visual_attributes import invoke_local_vlm, model_manifest
from scripts.private_checkpoint import digest, file_hash
from scripts.vlm_per_frame import BOOLEAN_FIELDS, aggregate
from scripts.vlm_product_states import FIELD, decode
from scripts.vlm_product_states import specification as v9_specification

VERSION = "visual-attributes-v10-worn-presentation"
INSERTION = (
    "Presentation may involve a garment that is being worn. Visible close framing "
    "of the garment's cut or details, or a hand holding the worn garment out to "
    "display it, can establish the garment itself as the item of interest. Do not "
    "require removal from the body or a hanger. A person wearing clothes, a full-body "
    "view, ordinary accessories, or clothes behind a speaker alone does not establish "
    "presentation; use uncertain if this image cannot distinguish presentation from "
    "incidental wear. "
)


def specification():
    spec = v9_specification("structured")
    marker = "Return exactly a JSON object"
    if spec["prompt"].count(marker) != 1:
        raise ValueError("v10_parent_prompt_changed")
    spec["prompt"] = spec["prompt"].replace(marker, INSERTION + marker)
    return spec


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
                raise ValueError("v10_pixels_changed")
            image.verify()
    evidence_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    spec = specification()
    frames, intermediate, calls = [], [], []
    for index, cell in enumerate(cells, 1):
        if file_hash(cell) != inputs[index - 1]:
            raise ValueError("v10_pixels_changed")
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
                raise ValueError("v10_invalid_raw_type")
            call["raw_response_sha256"] = hashlib.sha256(
                output["raw_response"].encode()
            ).hexdigest()
            save(path, call)
            if file_hash(cell) != inputs[index - 1]:
                raise ValueError("v10_pixels_changed")
            parsed, value = decode(output["raw_response"], "structured")
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
        raise ValueError("v10_result_configuration_changed")
    frames, intermediate, calls = [], [], []
    for index, expected in enumerate(result["input_png_sha256"], 1):
        path = evidence_dir / f"frame-{index}.json"
        call = json.loads(path.read_bytes())
        parsed, value = decode(call["raw_response"], "structured")
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
            raise ValueError("v10_native_receipt_changed")
        frames.append({f: value if f == FIELD else "unknown" for f in BOOLEAN_FIELDS})
        intermediate.append(parsed)
        calls.append({"path": path.name, "sha256": file_hash(path)})
    if (
        calls != result["calls"]
        or intermediate != result["intermediate"]
        or frames != result["per_frame"]
        or aggregate(frames, result["input_frame_seconds"]) != result["parsed"]
    ):
        raise ValueError("v10_derivation_changed")
    return result["parsed"]

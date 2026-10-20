"""One presented item/category per frame; additive lineage, unchanged temporal rules."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile

from PIL import Image

from scripts.gguf_visual_attributes import invoke_local_vlm, model_manifest
from scripts.private_checkpoint import digest, file_hash
from scripts.vlm_per_frame import BOOLEAN_FIELDS, aggregate
from scripts.vlm_product_v11 import FIELD
from scripts.vlm_product_v11 import decode as parent_decode
from scripts.vlm_product_v13 import specification as parent_specification

VERSION = "visual-attributes-v14-single-item"
VARIANT = "R"


def specification(variant=VARIANT):
    if variant != VARIANT:
        raise ValueError("v14_only_R_authorized")
    from scripts.vlm_product_states import CATEGORIES

    spec = parent_specification("R")
    old = (
        "Select one witnessed cue and list only presented_categories whose presentation is "
        "visible. At least one listed category must contain the SAME item with the selected cue."
    )
    new = (
        "Select ONE identifiable presented item and ONE witnessed cue for that SAME item. "
        "Set presented_categories to exactly ONE category of that item. Other clearly "
        "presented items may be omitted. Never transfer a cue from one item to a different "
        "item or category. A cosmetic must be an identifiable cosmetic product visibly "
        "presented with that cue; makeup already worn on a face does not establish a "
        "presented cosmetic product. An applicator is distinct from a cosmetic product; "
        "holding an applicator does not establish a cosmetic product or a garment as held_display."
    )
    spec["prompt"] = (
        spec["prompt"]
        .replace(old, new)
        .replace(
            "no duplicates, at most four.",
            "exactly one category for the selected presented item, otherwise empty.",
        )
        .replace(
            "categories are nonempty and cue", "categories contain exactly one category and cue"
        )
    )
    for branch in spec["schema"]["oneOf"]:
        props = branch["properties"]
        if props["state"]["const"] == "presented_target":
            props["presented_categories"] = {
                "enum": [["garment"]]
                if props["presentation_cue"]["const"] == "worn_detail_focus"
                else [[c] for c in CATEGORIES]
            }
    return spec


def decode(raw):
    parsed, value = parent_decode(raw)
    if parsed["state"] == "presented_target" and len(parsed["presented_categories"]) != 1:
        raise ValueError("v14_exactly_one_presented_category_required")
    return parsed, value


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


def extract(
    cells, seconds, work, *, variant=VARIANT, evidence_dir, reserve, invoker=invoke_local_vlm
):
    aggregate([{f: "unknown" for f in BOOLEAN_FIELDS} for _ in cells], seconds)
    inputs = [file_hash(p) for p in cells]
    for cell in cells:
        with Image.open(cell) as image:
            if image.format != "PNG" or image.mode != "RGB" or image.size != (320, 330):
                raise ValueError("v14_pixels_changed")
            image.verify()
    evidence_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    spec = specification(variant)
    frames, intermediate, calls = [], [], []
    for index, cell in enumerate(cells, 1):
        if file_hash(cell) != inputs[index - 1]:
            raise ValueError("v14_pixels_changed")
        reserve(index)
        path = evidence_dir / f"frame-{index}.json"
        call = {
            "schema_version": VERSION,
            "variant": variant,
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
                raise ValueError("v14_invalid_raw_type")
            call["raw_response_sha256"] = hashlib.sha256(
                output["raw_response"].encode()
            ).hexdigest()
            save(path, call)
            if file_hash(cell) != inputs[index - 1]:
                raise ValueError("v14_pixels_changed")
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
    variant = result["variant"]
    if (
        result["schema_version"] != VERSION
        or result["model"] != model_manifest()
        or result["specification_sha256"] != digest(specification(variant))
        or result["approved_for_training"] is not False
        or len(result["calls"]) != len(result["input_png_sha256"])
    ):
        raise ValueError("v14_result_configuration_changed")
    frames, intermediate, calls = [], [], []
    for index, expected in enumerate(result["input_png_sha256"], 1):
        path = evidence_dir / f"frame-{index}.json"
        call = json.loads(path.read_bytes())
        parsed, value = decode(call["raw_response"])
        if (
            call["schema_version"] != VERSION
            or call["variant"] != variant
            or call["frame"] != index
            or call["status"] != "completed"
            or call["input_png_sha256"] != expected
            or call["specification_sha256"] != digest(specification(variant))
            or hashlib.sha256(call["raw_response"].encode()).hexdigest()
            != call["raw_response_sha256"]
            or parsed != call["parsed"]
        ):
            raise ValueError("v14_native_receipt_changed")
        frames.append({f: value if f == FIELD else "unknown" for f in BOOLEAN_FIELDS})
        intermediate.append(parsed)
        calls.append({"path": path.name, "sha256": file_hash(path)})
    if (
        calls != result["calls"]
        or intermediate != result["intermediate"]
        or frames != result["per_frame"]
        or aggregate(frames, result["input_frame_seconds"]) != result["parsed"]
    ):
        raise ValueError("v14_derivation_changed")
    return result["parsed"]

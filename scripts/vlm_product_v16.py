"""V16: two ordered serializations of the same 22 native item objects."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy

from PIL import Image

from scripts.gguf_visual_attributes import invoke_local_vlm, model_manifest
from scripts.private_checkpoint import digest, file_hash
from scripts.vlm_per_frame import BOOLEAN_FIELDS, aggregate
from scripts.vlm_product_v11 import FIELD
from scripts.vlm_product_v15 import CUE_PROVENANCE, PROJECTION, project, save
from scripts.vlm_product_v15 import decode as semantic_decode
from scripts.vlm_product_v15 import specification as parent_specification

VERSION = "visual-attributes-v16-order-diagnostic"
VARIANTS = ("item_first", "state_first")
VARIANT = VARIANTS[0]
ORDER = {
    "item_first": ["item_configuration", "state", "presented_categories"],
    "state_first": ["state", "item_configuration", "presented_categories"],
}
OLD_RETURN = (
    "Return exactly JSON with item_configuration, state and presented_categories, in that order."
)
COMMON_RETURN = (
    "Return only the JSON object defined by the schema, with every required field exactly once."
)
# Five previously supported held crops: four hangers and one pulled hem.
POSITIVE_SELECTION = (
    ("epAKcoQrirk", 1, ("hand_holds_hanger_out", "isolated_physical_item")),
    ("epAKcoQrirk", 2, ("hand_holds_hanger_out", "isolated_physical_item")),
    ("epAKcoQrirk", 3, ("hand_holds_hanger_out", "isolated_physical_item")),
    ("toNRze0de1M", 1, ("hand_pulls_worn_fabric_out", "isolated_graphic_item")),
    ("xln8Ioqk1jU", 3, ("hand_holds_hanger_out", "isolated_physical_item")),
)


def specification(variant=VARIANT):
    if variant not in VARIANTS:
        raise ValueError("v16_unknown_order_condition")
    spec = deepcopy(parent_specification())
    assert spec["prompt"].count(OLD_RETURN) == 1
    spec["prompt"] = spec["prompt"].replace(OLD_RETURN, COMMON_RETURN)
    spec["fields"] = list(ORDER[variant])
    for branch in spec["schema"]["oneOf"]:
        old = branch["properties"]
        branch["properties"] = {k: old[k] for k in ORDER[variant]}
        # Keep even the required array unchanged: only properties serialization differs.
    return spec


def ordered_schema_hash(schema):
    return hashlib.sha256(
        json.dumps(schema, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def decode(raw, variant=VARIANT):
    native, value = semantic_decode(raw)
    if list(native) != specification(variant)["fields"]:
        raise ValueError("v16_native_serialization_order_changed")
    return native, value


def extract(
    cells, seconds, work, *, variant=VARIANT, evidence_dir, reserve, invoker=invoke_local_vlm
):
    aggregate([{f: "unknown" for f in BOOLEAN_FIELDS} for _ in cells], seconds)
    inputs = [file_hash(p) for p in cells]
    for cell in cells:
        with Image.open(cell) as image:
            if image.format != "PNG" or image.mode != "RGB" or image.size != (320, 330):
                raise ValueError("v16_pixels_changed")
            image.verify()
    evidence_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    spec = specification(variant)
    frames, intermediate, native_intermediate, calls = [], [], [], []
    for index, cell in enumerate(cells, 1):
        if file_hash(cell) != inputs[index - 1]:
            raise ValueError("v16_pixels_changed")
        reserve(index)
        path = evidence_dir / f"frame-{index}.json"
        call = {
            "schema_version": VERSION,
            "variant": variant,
            "frame": index,
            "input_png_sha256": inputs[index - 1],
            "specification_sha256": digest(spec),
            "ordered_schema_sha256": ordered_schema_hash(spec["schema"]),
            "status": "running",
        }
        save(path, call)
        try:
            output = invoker([cell], spec["prompt"], work, spec["schema"], max_tokens=64)
            call.update(output, status="response_captured")
            save(path, call)
            if type(output.get("raw_response")) is not str:
                raise ValueError("v16_invalid_raw_type")
            call["raw_response_sha256"] = hashlib.sha256(
                output["raw_response"].encode()
            ).hexdigest()
            save(path, call)
            if file_hash(cell) != inputs[index - 1]:
                raise ValueError("v16_pixels_changed")
            parsed, value = decode(output["raw_response"], variant)
        except BaseException as error:
            call.update(status="failed", error_type=type(error).__name__)
            save(path, call)
            raise
        call.update(
            status="completed",
            parsed=parsed,
            derived=project(parsed),
            presentation_cue_source=CUE_PROVENANCE,
            projection_sha256=digest(PROJECTION),
        )
        save(path, call)
        native_intermediate.append(parsed)
        intermediate.append(project(parsed))
        frames.append({f: value if f == FIELD else "unknown" for f in BOOLEAN_FIELDS})
        calls.append({"path": path.name, "sha256": file_hash(path)})
    return {
        "schema_version": VERSION,
        "variant": variant,
        "model": model_manifest(),
        "specification_sha256": digest(spec),
        "ordered_schema_sha256": ordered_schema_hash(spec["schema"]),
        "input_png_sha256": inputs,
        "input_frame_seconds": seconds,
        "intermediate": intermediate,
        "native_intermediate": native_intermediate,
        "presentation_cue_source": CUE_PROVENANCE,
        "projection_sha256": digest(PROJECTION),
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
        or result["ordered_schema_sha256"] != ordered_schema_hash(specification(variant)["schema"])
        or result["approved_for_training"] is not False
        or result["presentation_cue_source"] != CUE_PROVENANCE
        or result["projection_sha256"] != digest(PROJECTION)
        or len(result["calls"]) != len(result["input_png_sha256"])
    ):
        raise ValueError("v16_result_configuration_changed")
    frames, intermediate, native_intermediate, calls = [], [], [], []
    for index, expected in enumerate(result["input_png_sha256"], 1):
        path = evidence_dir / f"frame-{index}.json"
        call = json.loads(path.read_bytes())
        parsed, value = decode(call["raw_response"], variant)
        if (
            call["schema_version"] != VERSION
            or call["variant"] != variant
            or call["frame"] != index
            or call["status"] != "completed"
            or call["input_png_sha256"] != expected
            or call["ordered_schema_sha256"]
            != ordered_schema_hash(specification(variant)["schema"])
            or call["specification_sha256"] != digest(specification(variant))
            or hashlib.sha256(call["raw_response"].encode()).hexdigest()
            != call["raw_response_sha256"]
            or parsed != call["parsed"]
            or project(parsed) != call["derived"]
            or call["presentation_cue_source"] != CUE_PROVENANCE
            or call["projection_sha256"] != digest(PROJECTION)
        ):
            raise ValueError("v16_native_receipt_changed")
        frames.append({f: value if f == FIELD else "unknown" for f in BOOLEAN_FIELDS})
        native_intermediate.append(parsed)
        intermediate.append(project(parsed))
        calls.append({"path": path.name, "sha256": file_hash(path)})
    if (
        calls != result["calls"]
        or intermediate != result["intermediate"]
        or native_intermediate != result["native_intermediate"]
        or frames != result["per_frame"]
        or aggregate(frames, result["input_frame_seconds"]) != result["parsed"]
    ):
        raise ValueError("v16_derivation_changed")
    return result["parsed"]

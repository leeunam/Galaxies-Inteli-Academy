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
from scripts.vlm_product_states import _unique
from scripts.vlm_product_v11 import FIELD
from scripts.vlm_product_v14 import decode as semantic_decode

VERSION = "visual-attributes-v15-item-configuration"
VARIANT = "R"
CUE_PROVENANCE = "derived_from_model_declared_item_configuration_not_independent_verification"
FIELDS = ["item_configuration", "state", "presented_categories"]
PROMPT = "Inspect only this image for cosmetic products, applicators, garments and fashion accessories. Use only visible evidence of the SAME identifiable item. Do not infer marketing intent, text meaning, audio, another frame, unseen motion or real/synthetic provenance.\nSelect one confirmed presented item, if any, and report its item_configuration. Other confirmed presented items may be omitted. A nearby hand, a speaker holding another object, a body pose, or an item-only overlay does not establish a hand-to-THAT-item relationship. A relationship depicted within an image must concern the same depicted item; never borrow a hand from a different item or layer.\nConfigurations:\nabsent: no target item is visible after inspection; state no_target; categories empty.\nincidental: ALL visible targets are clearly incidental, with no presented or ambiguous target; state incidental_only; categories empty. Background location alone is insufficient.\nhand_holds_item_out: the SAME separate identifiable item is visibly in the hand AND held out to display. Merely holding or wearing an item is insufficient. The hand-to-item connection and display configuration must both be visible.\nhand_holds_hanger_out: a hand visibly holds the hanger displaying the SAME foreground garment. A background rack or a hanger without a confirmed hand connection does not establish this configuration.\nhand_pulls_worn_fabric_out: a hand visibly grips fabric of the SAME worn garment and holds it away from the body to show that fabric. Hands near clothing, at the neck or holding a different object are insufficient; do not infer unseen pulling motion.\nisolated_physical_item: the SAME item is clearly displayed or laid out as a separate foreground item. A background rack behind a speaker is insufficient.\nisolated_graphic_item: the SAME identifiable item is displayed as an isolated image cutout/overlay, without borrowing a nearby speaker's hand or another object's hand relation.\nexplicit_item_use: an explicit visible action using the SAME target, such as an applicator touching skin. Wearing clothing, jewelry or makeup alone is insufficient.\nframed_garment_detail: the framing clearly showcases an identifiable cut, finish, fastening or fabric detail of the SAME garment. A visible pattern, face with clothes or full-body view alone is insufficient.\nThe seven presentation configurations require state presented_target and exactly one category. hand_holds_hanger_out, hand_pulls_worn_fabric_out and framed_garment_detail require garment. Other presentation configurations allow cosmetic, applicator, garment or accessory. Cosmetic requires an identifiable cosmetic product; a brush is an applicator, not a cosmetic product, and makeup already worn on a face does not demonstrate a presented product.\nunclear: no presented item is confirmed and a target or its presentation is unclear; state uncertain; categories empty. Ambiguous presentation is uncertain, not incidental_only. A confirmed presented item wins over incidental or ambiguous other items.\nReturn exactly JSON with item_configuration, state and presented_categories, in that order. One configuration and at most one category; no explanations or presentation_cue field. The cue will be a code-derived projection of the declared configuration, not a separate visual observation."
PROJECTION = {
    "absent": {"state": "no_target", "presentation_cue": "absent", "categories": []},
    "incidental": {"state": "incidental_only", "presentation_cue": "incidental", "categories": []},
    "hand_holds_item_out": {
        "state": "presented_target",
        "presentation_cue": "held_display",
        "categories": ["cosmetic", "applicator", "garment", "accessory"],
    },
    "hand_holds_hanger_out": {
        "state": "presented_target",
        "presentation_cue": "held_display",
        "categories": ["garment"],
    },
    "hand_pulls_worn_fabric_out": {
        "state": "presented_target",
        "presentation_cue": "held_display",
        "categories": ["garment"],
    },
    "isolated_physical_item": {
        "state": "presented_target",
        "presentation_cue": "isolated_display",
        "categories": ["cosmetic", "applicator", "garment", "accessory"],
    },
    "isolated_graphic_item": {
        "state": "presented_target",
        "presentation_cue": "isolated_display",
        "categories": ["cosmetic", "applicator", "garment", "accessory"],
    },
    "explicit_item_use": {
        "state": "presented_target",
        "presentation_cue": "visible_use",
        "categories": ["cosmetic", "applicator", "garment", "accessory"],
    },
    "framed_garment_detail": {
        "state": "presented_target",
        "presentation_cue": "worn_detail_focus",
        "categories": ["garment"],
    },
    "unclear": {"state": "uncertain", "presentation_cue": "uncertain", "categories": []},
}


def specification(variant=VARIANT):
    if variant != VARIANT:
        raise ValueError("v15_only_R_authorized")
    branches = []
    for config, row in PROJECTION.items():
        branches.append(
            {
                "type": "object",
                "properties": {
                    "item_configuration": {"const": config},
                    "state": {"const": row["state"]},
                    "presented_categories": {"enum": [[c] for c in row["categories"]]}
                    if row["categories"]
                    else {"const": []},
                },
                "required": list(FIELDS),
                "additionalProperties": False,
            }
        )
    return {
        "fields": list(FIELDS),
        "prompt": PROMPT,
        "schema": {"oneOf": branches},
        "max_tokens": 64,
    }


def project(native):
    if type(native) is not dict or set(native) != set(FIELDS):
        raise ValueError("v15_exact_native_fields_required")
    config = native["item_configuration"]
    if type(config) is not str or config not in PROJECTION:
        raise ValueError("v15_unknown_configuration")
    row = PROJECTION[config]
    cats = native["presented_categories"]
    allowed = [[c] for c in row["categories"]] if row["categories"] else [[]]
    if native["state"] != row["state"] or type(cats) is not list or cats not in allowed:
        raise ValueError("v15_configuration_state_category_mismatch")
    return {
        "state": native["state"],
        "presented_categories": list(cats),
        "presentation_cue": row["presentation_cue"],
    }


def decode(raw):
    if type(raw) is not str:
        raise ValueError("v15_invalid_raw_type")
    native = json.loads(raw, object_pairs_hook=_unique)
    derived = project(native)
    _, value = semantic_decode(json.dumps(derived))
    return native, value


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
                raise ValueError("v15_pixels_changed")
            image.verify()
    evidence_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    spec = specification(variant)
    frames, intermediate, native_intermediate, calls = [], [], [], []
    for index, cell in enumerate(cells, 1):
        if file_hash(cell) != inputs[index - 1]:
            raise ValueError("v15_pixels_changed")
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
                raise ValueError("v15_invalid_raw_type")
            call["raw_response_sha256"] = hashlib.sha256(
                output["raw_response"].encode()
            ).hexdigest()
            save(path, call)
            if file_hash(cell) != inputs[index - 1]:
                raise ValueError("v15_pixels_changed")
            parsed, value = decode(output["raw_response"])
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
        or result["approved_for_training"] is not False
        or result["presentation_cue_source"] != CUE_PROVENANCE
        or result["projection_sha256"] != digest(PROJECTION)
        or len(result["calls"]) != len(result["input_png_sha256"])
    ):
        raise ValueError("v15_result_configuration_changed")
    frames, intermediate, native_intermediate, calls = [], [], [], []
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
            or project(parsed) != call["derived"]
            or call["presentation_cue_source"] != CUE_PROVENANCE
            or call["projection_sha256"] != digest(PROJECTION)
        ):
            raise ValueError("v15_native_receipt_changed")
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
        raise ValueError("v15_derivation_changed")
    return result["parsed"]

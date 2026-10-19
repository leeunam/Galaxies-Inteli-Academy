"""Label-blind, operational release gate for VLM columns; not a perception certification."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from scripts.channel_partitions import digest
from scripts.experiment_b_vlm_extract import POLICY, load_queue
from scripts.gguf_visual_attributes import (
    QUALITY_POLICY,
    WITHHELD_ATTRIBUTES,
    apply_quality_policy,
    model_manifest,
)
from scripts.private_checkpoint import file_hash, save
from scripts.visual_attributes import FIELDS as VLM_FIELDS
from scripts.visual_attributes import FORMATS, SCENES, validate_vlm_answer
from scripts.vlm_frame_evidence import NORMALIZATION_POLICY, SCHEMA_VERSION, parse_normalized_output

FIELDS = ("person_visible", "product_visible_early", "screen_text", "scene", "format")
BOOLEAN_FIELDS = FIELDS[:3]
GATE = "b-vlm-blind-assisted-sector-gate-v1"


def normalized(field, value):
    if field == "format" and value == "application":
        return "unknown"
    if type(value) is bool:
        return "true" if value else "false"
    return value


def validate_fields(fields, seconds):
    if not isinstance(fields, dict) or set(fields) != set(FIELDS):
        raise ValueError("invalid_blind_annotation_fields")
    for field in FIELDS:
        item = fields[field]
        options = (
            (True, False, "unknown")
            if field in BOOLEAN_FIELDS
            else (SCENES if field == "scene" else FORMATS)
        )
        value, frames = item.get("value"), item.get("frames")
        if (
            set(item) != {"value", "frames"}
            or (field in BOOLEAN_FIELDS and type(value) is not bool and value != "unknown")
            or value not in options
            or not isinstance(frames, list)
            or any(type(i) is not int or not 1 <= i <= len(seconds) for i in frames)
            or len(frames) != len(set(frames))
            or (value == "unknown") != (not frames)
            or (field == "product_visible_early" and any(seconds[i - 1] > 3 for i in frames))
        ):
            raise ValueError("invalid_blind_annotation_value_or_evidence")


def checked_sidecar(sidecar, row, config):
    """Do not permit raw answers or withheld attributes to bypass their global gate."""
    vlm = sidecar["vlm"]
    seconds = vlm["input_frame_seconds"]
    parsed = vlm["parsed"]
    raw_parsed, normalized_parsed = parse_normalized_output(vlm["raw_response"], seconds)
    status, _ = validate_vlm_answer(json.dumps(normalized_parsed), seconds)
    if (
        sidecar["schema_version"] != "experiment-b-vlm-sidecar-v1"
        or sidecar["sample_id"] != row["sample_id"]
        or sidecar["input_policy"] != POLICY
        or sidecar["config_sha256"] != digest(config)
        or sidecar["shared_features_sha256"] != row["features_sha256"]
        or sidecar["frozen_media_sha256"] != row["media_sha256"]
        or sidecar["frozen_sheet_sha256"] != row["sheet_sha256"]
        or sidecar["properties"] != row["properties"]
        or len(sidecar["input_png_sha256"]) != len(seconds)
        or any(not re.fullmatch(r"[a-f0-9]{64}", h) for h in sidecar["input_png_sha256"])
        or not re.fullmatch(r"[a-f0-9]{64}", sidecar["reacquired_media_sha256"])
        or not 1 <= len(seconds) <= 4
        or sidecar["training_approved"] is not False
        or sidecar["test_evaluated"] is not False
        or vlm["approved_for_training"] is not False
        or vlm["schema_version"] != SCHEMA_VERSION
        or vlm["normalization_policy"] != NORMALIZATION_POLICY
        or vlm["model_parsed"] != raw_parsed
        or vlm["normalized_model_parsed"] != normalized_parsed
        or vlm["deduplicated_fields"]
        != [k for k in VLM_FIELDS if raw_parsed[k] != normalized_parsed[k]]
        or vlm["raw_response_sha256"] != hashlib.sha256(vlm["raw_response"].encode()).hexdigest()
        or status != "schema_valid_requires_perception_review"
        or vlm["status"] != status
        or vlm["model"] != model_manifest()
        or vlm["quality_policy"] != QUALITY_POLICY
        or vlm["withheld_attributes"] != WITHHELD_ATTRIBUTES
        or parsed != apply_quality_policy(normalized_parsed)
        or any(
            parsed[key] != {"value": "unknown", "frames": []}
            for key in ("product_closeup", "demonstration")
        )
    ):
        raise ValueError("incompatible_or_ungated_vlm_sidecar")
    # Use the same selector without touching media to bind input ordering/timestamps.
    from scripts.pilot_licensed_media import select_vlm_samples

    properties = row["properties"]
    _, expected = select_vlm_samples(
        list(range(len(properties["sampled_frame_seconds"]))), properties
    )
    if seconds != expected:
        raise ValueError("vlm_input_timestamps_changed")
    return parsed, seconds


def evaluate_gate(observations):
    """Pure scoring after blind annotations are fixed; no predictive outcomes accepted."""
    if len(observations) != 32 or Counter(o["sector"] for o in observations) != {
        "moda": 16,
        "beleza": 16,
    }:
        raise ValueError("gate_requires_balanced_32_training_annotations")
    summary, released = {}, []
    retained_values = {}
    for field in FIELDS:
        support = Counter(normalized(field, o["predicted"][field]["value"]) for o in observations)
        allowed = (
            ("true", "false")
            if field in BOOLEAN_FIELDS
            else tuple(sorted(v for v, n in support.items() if v != "unknown" and n >= 3))
        )
        sectors = {}
        for sector in ("beleza", "moda"):
            rows = [o for o in observations if o["sector"] == sector]
            counts = Counter()
            confusion = Counter()
            correct, evidence_invalid, known = 0, 0, 0
            for observation in rows:
                prediction = observation["predicted"][field]
                annotation = observation["annotated"][field]
                predicted = normalized(field, prediction["value"])
                actual = normalized(field, annotation["value"])
                if predicted not in allowed:
                    predicted = "unknown"
                confusion[(actual, predicted)] += 1
                if predicted == "unknown":
                    continue
                known += 1
                counts[predicted] += 1
                evidence_ok = bool(prediction["frames"]) and set(prediction["frames"]) <= set(
                    annotation["frames"]
                )
                evidence_invalid += not evidence_ok
                correct += predicted == actual and evidence_ok
            sectors[sector] = {
                "samples": 16,
                "known": known,
                "abstentions_or_unsupported": 16 - known,
                "correct_value_and_evidence": correct,
                "incorrect_or_unverified": known - correct,
                "evidence_not_supported_by_blind_annotation": evidence_invalid,
                "agreement": correct / known if known else None,
                "predicted_value_support": dict(counts),
                "confusion": [
                    {"annotated": a, "predicted": p, "count": n}
                    for (a, p), n in sorted(confusion.items())
                ],
            }
        passed = all(
            s["known"] >= 12
            and s["correct_value_and_evidence"] / s["known"] >= 0.9
            and s["evidence_not_supported_by_blind_annotation"] == 0
            for s in sectors.values()
        )
        if field in BOOLEAN_FIELDS:
            passed = (
                passed
                and all(support[v] >= 3 for v in ("true", "false"))
                and all(
                    s["predicted_value_support"].get(v, 0) >= 1
                    for s in sectors.values()
                    for v in ("true", "false")
                )
            )
        else:
            passed = passed and len(allowed) >= 2
        summary[field] = {"released": passed, "retained_values": allowed, "sectors": sectors}
        if passed:
            released.append(field)
            retained_values[field] = allowed
    return {
        "gate": GATE,
        "status": "released_columns" if released else "no_columns_released",
        "released_fields": released,
        "retained_values": retained_values,
        "columns": summary,
        "human_review": False,
        "general_perception_accuracy_validated": False,
        "predictive_outcomes_used": False,
    }


def publish_gate(queue, annotations_path, output, *, parent, cohort, root):
    """Annotations must be published blind before any model answer is revealed for scoring."""
    if output.exists():
        raise ValueError("quality_release_output_already_exists")
    plan, checkpoint = load_queue(parent, cohort, queue, root)
    if checkpoint["halt_reason"]:
        raise ValueError("cannot_release_halted_extraction")
    completed = {
        entry["sample_id"]: entry
        for entry in checkpoint["entries"]
        if entry["status"] == "completed"
    }
    annotation_raw = annotations_path.read_bytes()
    annotations = json.loads(annotation_raw)
    expected = tuple(plan["audit_sample_ids"])
    if (
        set(annotations)
        != {
            "schema_version",
            "plan_sha256",
            "blind_to_vlm_outputs",
            "blind_to_outcomes",
            "human_review",
            "rows",
        }
        or annotations.get("schema_version") != "b-vlm-blind-annotations-v1"
        or annotations.get("blind_to_vlm_outputs") is not True
        or annotations.get("blind_to_outcomes") is not True
        or annotations.get("human_review") is not False
        or annotations.get("plan_sha256") != plan["plan_sha256"]
        or len(annotations["rows"]) != 32
        or tuple(r["sample_id"] for r in annotations["rows"]) != expected
        or any(set(r) != {"sample_id", "sheet_sha256", "fields"} for r in annotations["rows"])
        or not set(expected) <= set(completed)
    ):
        raise ValueError("fixed_blind_annotation_receipt_required")
    rows = {r["sample_id"]: r for r in plan["rows"]}
    observations, hashes = [], {}
    for annotation in annotations["rows"]:
        sample = annotation["sample_id"]
        row = rows[sample]
        if row["partition"] != "train" or not row["audit"]:
            raise ValueError("quality_gate_must_use_training_only")
        sheet = queue / "audit-sheets" / f"{sample}.png"
        if (
            file_hash(sheet) != row["sheet_sha256"]
            or annotation["sheet_sha256"] != row["sheet_sha256"]
        ):
            raise ValueError("blind_annotation_image_changed")
        sidecar_path = queue / "sessions" / sample / "features.json"
        raw = sidecar_path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != completed[sample]["files_sha256"]["features.json"]:
            raise ValueError("quality_audit_sidecar_changed")
        sidecar = json.loads(raw)
        predicted, seconds = checked_sidecar(sidecar, row, plan["config"])
        validate_fields(annotation["fields"], seconds)
        observations.append(
            {"sector": row["sector"], "predicted": predicted, "annotated": annotation["fields"]}
        )
        hashes[sample] = hashlib.sha256(raw).hexdigest()
    proof = evaluate_gate(observations) | {
        "plan_sha256": plan["plan_sha256"],
        "input_policy": POLICY,
        "annotations_sha256": hashlib.sha256(annotation_raw).hexdigest(),
        "audit_sidecars_sha256": hashes,
        "source_sha256": file_hash(Path(__file__)),
    }
    proof["release_sha256"] = digest(proof)
    save(output, proof)
    return proof

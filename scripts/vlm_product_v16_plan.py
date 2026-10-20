"""Frozen V16 scope and lineage: two serializations, 24 negatives, conditional 5 crops."""

from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path

from scripts.private_checkpoint import digest, file_hash, private_path
from scripts.vlm_product_limited_plan import installed_versions, no_workers
from scripts.vlm_product_v15_plan import load as load_v15
from scripts.vlm_product_v16 import (
    CUE_PROVENANCE,
    FIELD,
    POSITIVE_SELECTION,
    PROJECTION,
    VARIANTS,
    VERSION,
    decode,
    ordered_schema_hash,
    save,
    specification,
    verify,
)
from scripts.vlm_product_v16_grammar import check_receipt
from scripts.vlm_prompt_plan import FONT, controls

ROOT = Path(__file__).resolve().parent.parent
PROOF = "data/private/issue-4-vlm-v16-verificacao-v1"
PROTOCOL = "v16-response-serialization-order-diagnostic-v1"
CALL_LIMIT, SESSION_LIMIT = 34, 1200
SOURCES = (
    "scripts/vlm_product_v16.py",
    "scripts/vlm_product_v16_grammar.py",
    "scripts/vlm_product_v16_plan.py",
    "scripts/vlm_product_v16_run.py",
    "tests/test_vlm_product_v16.py",
    "tests/test_vlm_product_v16_grammar.py",
    "tests/test_vlm_product_v16_run.py",
    "docs/issue-4-vlm-v16-protocolo.md",
    "scripts/vlm_product_v13_grammar.cpp",
)


def load_base(parent, cohort, root):
    previous = root / "data/private/issue-4-vlm-v15-v1"
    old, state = load_v15(parent, cohort, previous, root)
    if (
        not state["sealed"]
        or state["halt_reason"] != "v15_controls_quality_failed"
        or state["calls_reserved"] != 12
    ):
        raise ValueError("v16_sealed_v15_required")
    before_path = root / PROOF / "before.json"
    before = json.loads(before_path.read_bytes())
    pins = before["protected_sha256"] | {str(before_path.relative_to(root)): file_hash(before_path)}
    if any(file_hash(root / n) != h for n, h in pins.items()):
        raise ValueError("v16_integration_or_earlier_pin_changed")
    review_path = root / "data/private/issue-4-vlm-v14-v1/cue-review-phase1.json"
    review = json.loads(review_path.read_bytes())["entries"]
    inspection_path = root / "data/private/issue-4-vlm-v11-verificacao-v1/preinspection.json"
    inspection = {r["sample_id"]: r for r in json.loads(inspection_path.read_bytes())["cases"]}
    rows = {r["sample_id"]: r for r in old["base"]["rows"]}
    negatives = []
    for row in controls():
        expected = old["base"]["inputs"][row["sample_id"]]
        negatives.append(
            {
                "sample_id": row["sample_id"],
                "kind": "negative",
                "source_frame": 1,
                "seconds": expected["seconds"][0],
                "png_sha256": expected["png_sha256"][0],
                "expected_value": False,
            }
        )
    positives = []
    for sample, frame, admissible in POSITIVE_SELECTION:
        original = rows[sample]
        if original["partition"] != "train":
            raise ValueError("v16_training_only_positive_required")
        expected = old["base"]["inputs"][sample]
        binding = review[f"{sample}:{frame}"]
        frozen = inspection[sample]["frames"][frame - 1]
        if (
            binding["supported"] is not True
            or binding["categories"] != ["garment"]
            or binding["cue"] != "held_display"
            or binding["input_png_sha256"] != expected["png_sha256"][frame - 1]
            or frozen["crop_sha256"] != binding["input_png_sha256"]
            or frozen["seconds"] != binding["seconds"]
        ):
            raise ValueError("v16_existing_positive_support_required")
        positives.append(
            {
                "sample_id": f"{sample}--frame-{frame}",
                "kind": "positive",
                "source_sample_id": sample,
                "source_frame": frame,
                "seconds": expected["seconds"][frame - 1],
                "png_sha256": expected["png_sha256"][frame - 1],
                "sheet_path": str(
                    Path(old["base"]["preserved_folder"]) / "images" / f"{sample}.png"
                ),
                "sheet_sha256": original["sheet_sha256"],
                "expected_value": True,
                "admissible_categories": ["garment"],
                "admissible_configurations": list(admissible),
                "frozen_cue_review": binding,
                "frozen_inspection": frozen,
                "admissible_witnesses": {
                    config: {
                        "frozen_text": frozen["items_cues_and_ambiguity"],
                        "visual_instance": "corner_graphic_dress"
                        if config == "isolated_graphic_item"
                        else "worn_dress_hem"
                        if config == "hand_pulls_worn_fabric_out"
                        else "foreground_garment_on_hanger",
                        "rule": "visible hand-to-hanger connection displaying that garment"
                        if config == "hand_holds_hanger_out"
                        else "same physical garment displayed separately in foreground; no requirement of being unheld"
                        if config == "isolated_physical_item"
                        else "visible hand grips and holds the worn hem away from body"
                        if config == "hand_pulls_worn_fabric_out"
                        else "separate dress cutout already annotated in the same crop; no borrowed hand relation",
                    }
                    for config in admissible
                },
                "annotation_source_sha256": {
                    "review": file_hash(review_path),
                    "inspection": file_hash(inspection_path),
                },
            }
        )
    return {
        "protected_sha256": pins,
        "cases": {"negative": negatives, "positive": positives},
        "prior_calls": old["base"]["prior_calls"] + state["calls_reserved"],
        "prior_acquisitions": old["base"]["prior_acquisitions"] + state["acquisitions_reserved"],
        "prior_seconds": state["elapsed_seconds"],
        "ancestor_folders": old["base"]["ancestor_folders"] + [str(previous.relative_to(root))],
    }


def configuration():
    preflights = {}
    for variant in VARIANTS:
        folder = ROOT / PROOF / ("native-" + variant)
        receipt = check_receipt(folder, variant, ROOT)
        preflights[variant] = {
            "receipt_file_sha256": file_hash(folder / "receipt.json"),
            "receipt_sha256": receipt["receipt_sha256"],
            "grammar_sha256": receipt["grammar_sha256"],
        }
    preflight_path = ROOT / PROOF / "offline-preflight.json"
    preflight = json.loads(preflight_path.read_bytes())
    if (
        preflight["status"] != "equivalent_semantics_tokenization_and_commands_passed"
        or preflight["preflight_sha256"]
        != digest({k: v for k, v in preflight.items() if k != "preflight_sha256"})
        or preflight["native_preflights"] != preflights
        or preflight["model_loaded_for_generation"] is not False
        or preflight["forward_passes"] != 0
        or preflight["semantic_objects_each"] != 22
        or preflight["opposite_order_rejected_each"] != 22
        or preflight["token_serializations"] != 88
    ):
        raise ValueError("v16_offline_preflight_changed")
    for n, h in preflight["sources_sha256"].items():
        if file_hash(ROOT / n) != h:
            raise ValueError("v16_preflight_source_changed")
    for n, h in preflight["files_sha256"].items():
        if file_hash(ROOT / PROOF / n) != h:
            raise ValueError("v16_preflight_evidence_changed")
    return {
        "sources": {n: file_hash(ROOT / n) for n in SOURCES},
        "specifications": {v: specification(v) for v in VARIANTS},
        "ordered_schema_sha256": {
            v: ordered_schema_hash(specification(v)["schema"]) for v in VARIANTS
        },
        "projection_sha256": digest(PROJECTION),
        "presentation_cue_source": CUE_PROVENANCE,
        "controls": controls(),
        "font_sha256": file_hash(FONT),
        "installed_versions": installed_versions(),
        "native_preflights": preflights,
        "offline_preflight_sha256": file_hash(preflight_path),
    }


def sequence(plan, eligible=()):
    result = []
    for kind in ("negative", "positive"):
        for i, case in enumerate(plan["base"]["cases"][kind]):
            order = VARIANTS if i % 2 == 0 else tuple(reversed(VARIANTS))
            result.extend(
                (v, kind, case["sample_id"]) for v in order if kind == "negative" or v in eligible
            )
    return result


def case_for(plan, kind, sample):
    return next(c for c in plan["base"]["cases"][kind] if c["sample_id"] == sample)


def result_path(folder, entry):
    if (
        entry["variant"] not in VARIANTS
        or entry["kind"] not in ("negative", "positive")
        or Path(entry["sample_id"]).name != entry["sample_id"]
    ):
        raise ValueError("v16_scope_forbidden")
    return (
        folder / "results" / entry["variant"] / entry["kind"] / entry["sample_id"] / "result.json"
    )


def files_for(folder, entry):
    return {
        str(p.relative_to(folder)): file_hash(p)
        for p in sorted(result_path(folder, entry).parent.rglob("*.json"))
    }


def checked_result(folder, plan, entry):
    path = result_path(folder, entry)
    body = json.loads(path.read_bytes())
    case = case_for(plan, entry["kind"], entry["sample_id"])
    r = body["vlm"]
    if (
        body["plan_sha256"] != plan["plan_sha256"]
        or body["case_sha256"] != digest(case)
        or r["variant"] != entry["variant"]
        or r["input_png_sha256"] != [case["png_sha256"]]
        or r["input_frame_seconds"] != [case["seconds"]]
    ):
        raise ValueError("v16_case_identity_changed")
    verify(r, path.parent / "calls")
    return r


def correct(case, result):
    value = result["parsed"][FIELD]["value"]
    if case["kind"] == "negative":
        return value is False
    native = result["native_intermediate"][0]
    return (
        value is True
        and native["item_configuration"] in case["admissible_configurations"]
        and native["presented_categories"] == case["admissible_categories"]
    )


def eligible_conditions(folder, plan, state):
    return [
        v
        for v in VARIANTS
        if len(
            entries := [
                e for e in state["operations"] if e["variant"] == v and e["kind"] == "negative"
            ]
        )
        == 12
        and all(
            e["status"] == "completed"
            and correct(case_for(plan, e["kind"], e["sample_id"]), checked_result(folder, plan, e))
            for e in entries
        )
    ]


def prepare(parent, cohort, folder, root):
    folder = private_path(folder, root)
    base = load_base(parent, cohort, root)
    if any(
        folder.is_relative_to(root / n) or (root / n).is_relative_to(folder)
        for n in base["ancestor_folders"]
    ):
        raise ValueError("v16_separate_queue_required")
    if folder.exists() and any(p.name != ".lock" for p in folder.iterdir()):
        raise ValueError("v16_queue_already_consumed")
    no_workers(root)
    body = {
        "protocol": PROTOCOL,
        "base": base,
        "configuration": configuration(),
        "limits": {
            "calls": 34,
            "acquisitions": 0,
            "session_seconds": 1200,
            "call_seconds": 180,
            "rss_gib": 3.3,
        },
        "authorization": "human_Sentinel_c36e04c6f9388191b2cb3380d86351ae_and_supervisor_34_call_order_diagnostic",
        "technical_review_required": True,
    }
    body["plan_sha256"] = digest(body)
    save(folder / "plan.json", body)
    save(
        folder / "checkpoint.json",
        {
            "plan_sha256": body["plan_sha256"],
            "operations": [],
            "calls_reserved": 0,
            "acquisitions_reserved": 0,
            "new_session_seconds": 0.0,
            "elapsed_seconds": base["prior_seconds"],
            "sealed": False,
            "halt_reason": None,
            "technical_clearance_sha256": None,
        },
    )
    return body


def check_clearance(folder, plan, state):
    path = folder / "technical-clearance.json"
    if state["technical_clearance_sha256"] is None:
        if path.exists() or state["operations"]:
            raise ValueError("v16_technical_review_required")
        return False
    body = json.loads(path.read_bytes())
    if (
        file_hash(path) != state["technical_clearance_sha256"]
        or body["plan_sha256"] != plan["plan_sha256"]
        or body["configuration_sha256"] != digest(plan["configuration"])
        or body["decision"] != "released_for_this_plan_only"
        or body["reviewer_thread_id"] != "01a15713-2572-7544-8329-c229ea2ff0f5"
        or not body["review_message_id"]
        or not body["message"]
        or body["message_sha256"] != hashlib.sha256(body["message"].encode()).hexdigest()
    ):
        raise ValueError("v16_technical_review_binding_changed")
    return True


def submit_clearance(folder, plan, state, body):
    if state["operations"] or state["sealed"] or state["technical_clearance_sha256"] is not None:
        raise ValueError("v16_clearance_already_consumed")
    path = folder / "technical-clearance.json"
    candidate = state | {"technical_clearance_sha256": None}
    # Validate without publishing arbitrary data or overwriting a previous receipt.
    if (
        body.get("plan_sha256") != plan["plan_sha256"]
        or body.get("configuration_sha256") != digest(plan["configuration"])
        or body.get("decision") != "released_for_this_plan_only"
        or body.get("reviewer_thread_id") != "01a15713-2572-7544-8329-c229ea2ff0f5"
        or not body.get("review_message_id")
        or type(body.get("message")) is not str
        or not body["message"]
        or body.get("message_sha256") != hashlib.sha256(body["message"].encode()).hexdigest()
    ):
        raise ValueError("v16_technical_review_binding_changed")
    exclusive(path, body)
    candidate["technical_clearance_sha256"] = file_hash(path)
    check_clearance(folder, plan, candidate)
    state.update(candidate)
    save(folder / "checkpoint.json", state)


def exclusive(path, body):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("x") as f:
        path.chmod(0o600)
        json.dump(body, f, ensure_ascii=True, allow_nan=False)
        f.flush()
        os.fsync(f.fileno())
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def load(parent, cohort, folder, root):
    if any(p.is_symlink() for p in folder.rglob("*")) or any(
        (folder / n).exists() for n in ("images", "sessions")
    ):
        raise ValueError("v16_unsafe_queue_or_acquisition")
    p = json.loads((folder / "plan.json").read_bytes())
    s = json.loads((folder / "checkpoint.json").read_bytes())
    if (
        p["protocol"] != PROTOCOL
        or p["plan_sha256"] != digest({k: v for k, v in p.items() if k != "plan_sha256"})
        or p["base"] != load_base(parent, cohort, root)
        or p["configuration"] != configuration()
        or p["limits"]
        != {
            "calls": 34,
            "acquisitions": 0,
            "session_seconds": 1200,
            "call_seconds": 180,
            "rss_gib": 3.3,
        }
        or p["authorization"]
        != "human_Sentinel_c36e04c6f9388191b2cb3380d86351ae_and_supervisor_34_call_order_diagnostic"
        or p["technical_review_required"] is not True
        or s["plan_sha256"] != p["plan_sha256"]
        or type(s["sealed"]) is not bool
    ):
        raise ValueError("v16_plan_or_sources_changed")
    entries = s["operations"]
    expected = sequence(p)
    if len(entries) > 24:
        if any(e["status"] != "completed" for e in entries[:24]):
            raise ValueError("v16_complete_negatives_required")
        expected = sequence(p, eligible_conditions(folder, p, s))
    if [(e["variant"], e["kind"], e["sample_id"]) for e in entries] != expected[
        : len(entries)
    ] or len(entries) > len(expected):
        raise ValueError("v16_order_scope_or_positive_gate_changed")
    seconds = 0.0
    wanted = set()
    number = 0
    for index, e in enumerate(entries, 1):
        if (
            e["status"] not in ("running", "completed", "failed")
            or type(e["call_count"]) is not int
            or e["call_count"] not in (0, 1)
            or (e["status"] == "completed" and e["call_count"] != 1)
            or type(e["seconds"]) not in (int, float)
            or not math.isfinite(e["seconds"])
            or e["seconds"] < 0
        ):
            raise ValueError("v16_invalid_consumption")
        seconds += e["seconds"]
        if e["call_count"]:
            number += 1
            name = f"native-{number:04d}.json"
            wanted.add(name)
            receipt = json.loads((folder / "reservations" / name).read_bytes())
            if receipt != {
                "plan_sha256": p["plan_sha256"],
                "operation": index,
                "variant": e["variant"],
                "kind": e["kind"],
                "sample_id": e["sample_id"],
                "frame": 1,
                "number": number,
            }:
                raise ValueError("v16_reservation_changed")
        if e["status"] != "running":
            if files_for(folder, e) != e["files_sha256"]:
                raise ValueError("v16_operation_evidence_changed")
            directory = result_path(folder, e).parent / "calls"
            names = {x.name for x in directory.glob("*")}
            required = {"frame-1.json"} if e["call_count"] else set()
            if names != required and not (e["status"] == "failed" and not names):
                raise ValueError("v16_native_count_changed")
            for name in names:
                call = json.loads((directory / name).read_bytes())
                variant = e["variant"]
                if (
                    call["schema_version"] != VERSION
                    or call["variant"] != variant
                    or call["frame"] != 1
                    or call["specification_sha256"] != digest(specification(variant))
                    or call["ordered_schema_sha256"]
                    != ordered_schema_hash(specification(variant)["schema"])
                    or call["input_png_sha256"]
                    != case_for(p, e["kind"], e["sample_id"])["png_sha256"]
                    or call["status"] not in ("running", "response_captured", "failed", "completed")
                ):
                    raise ValueError("v16_native_receipt_changed")
                if (
                    "raw_response_sha256" in call
                    and hashlib.sha256(call["raw_response"].encode()).hexdigest()
                    != call["raw_response_sha256"]
                ):
                    raise ValueError("v16_native_raw_changed")
                if e["seconds"] + 1e-8 < call.get("runtime_seconds", 0):
                    raise ValueError("v16_measured_time_reset")
                if (
                    call["status"] == "completed"
                    and decode(call["raw_response"], variant)[0] != call["parsed"]
                ):
                    raise ValueError("v16_native_parse_changed")
            if e["status"] == "completed":
                checked_result(folder, p, e)
    if {x.name for x in (folder / "reservations").glob("*")} != wanted:
        raise ValueError("v16_unreserved_native_or_acquisition")
    if (
        type(s["calls_reserved"]) is not int
        or number != s["calls_reserved"]
        or number > 34
        or type(s["acquisitions_reserved"]) is not int
        or s["acquisitions_reserved"] != 0
        or seconds > 1200
        or not math.isclose(seconds, s["new_session_seconds"], rel_tol=0, abs_tol=1e-8)
        or not math.isclose(
            p["base"]["prior_seconds"] + seconds, s["elapsed_seconds"], rel_tol=0, abs_tol=1e-8
        )
    ):
        raise ValueError("v16_budget_changed")
    check_clearance(folder, p, s)
    if s["sealed"]:
        report = json.loads((folder / "comparison.json").read_bytes())
        if (
            file_hash(folder / "comparison.json") != s["comparison_file_sha256"]
            or report["comparison_sha256"]
            != digest({k: v for k, v in report.items() if k != "comparison_sha256"})
            or report["plan_sha256"] != p["plan_sha256"]
            or report["new_calls_reserved"] != number
            or report["new_acquisitions_reserved"] != 0
            or report["new_session_seconds"] != seconds
            or report["cumulative_session_seconds"] != s["elapsed_seconds"]
            or report["cumulative_calls"] != p["base"]["prior_calls"] + number
            or report["cumulative_acquisitions"] != p["base"]["prior_acquisitions"]
            or report["released_fields"] != []
            or any(
                report[k] is not False
                for k in (
                    "test_evaluated",
                    "m1_replaced",
                    "new_blind_audit",
                    "predictive_training_started",
                )
            )
        ):
            raise ValueError("v16_terminal_report_changed")
        from scripts.vlm_product_v16_run import pair_scores, scores

        actual_scores = scores(folder, p, s)
        candidates = [
            v
            for v in VARIANTS
            if actual_scores[v]["negative"]["passed"] and actual_scores[v]["positive"]["passed"]
        ]
        if (
            report["condition_scores"] != actual_scores
            or report["paired"] != pair_scores(actual_scores)
            or report["candidate_for_further_development"] != candidates
            or report["positive_gate_eligible"] != eligible_conditions(folder, p, s)
            or report["unused_calls_closed"] != 34 - number
            or report["causal_scope"]
            != "serialization_order_under_the_same_neutral_prompt_not_historical_v14_to_v15_cause"
            or report["positive_sampling_unit"]
            != "five_known_crops_from_three_videos_not_five_independent_videos"
            or report["completed_result_sha256"]
            != {
                str(result_path(folder, e).relative_to(folder)): file_hash(result_path(folder, e))
                for e in entries
                if e["status"] == "completed"
            }
            or report["native_receipt_sha256"]
            != {
                str(path.relative_to(folder)): file_hash(path)
                for path in sorted((folder / "results").glob("*/*/*/calls/*.json"))
            }
        ):
            raise ValueError("v16_terminal_scientific_claim_changed")

    return p, s


def runnable(state):
    if (
        state["sealed"]
        or state["halt_reason"]
        or any(e["status"] != "completed" for e in state["operations"])
    ):
        raise ValueError("v16_consumed_or_uncertain_no_retry")
    if state["new_session_seconds"] >= 1200:
        raise ValueError("v16_session_budget_exhausted")

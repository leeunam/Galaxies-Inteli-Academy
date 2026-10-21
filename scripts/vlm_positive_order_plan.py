"""Separate ten-call positive diagnostic; sealed V16 is never resumed or approved."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from scripts.private_checkpoint import digest, file_hash, private_path
from scripts.vlm_product_v16 import (
    VARIANTS,
    VERSION,
    decode,
    ordered_schema_hash,
    specification,
)
from scripts.vlm_product_v16_plan import (
    check_clearance,
    checked_result,
    exclusive,
    files_for,
    no_workers,
    result_path,
)
from scripts.vlm_product_v16_plan import configuration as v16_configuration
from scripts.vlm_product_v16_plan import load as load_v16
from scripts.vlm_product_v16_plan import submit_clearance as parent_submit_clearance

ROOT = Path(__file__).resolve().parent.parent
QUEUE = "data/private/issue-4-vlm-pos-v16-pares-positivos-v1"
PROOF = "data/private/issue-4-vlm-pos-v16-diagnostico-v1"
PROTOCOL = "post-v16-paired-positive-diagnostic-v1"
AUTHORIZATION = "standing_human_authorization_and_supervisor_separate_10_call_400_second_diagnostic"
CALL_LIMIT, SESSION_LIMIT = 10, 400
LIMITS = {
    "calls": 10,
    "acquisitions": 0,
    "session_seconds": 400,
    "call_seconds": 180,
    "rss_gib": 3.3,
}
POSITIVE_CASES_SHA256 = "382ab73dc0d03b0b930c0c2f8de36f64e6ceb8ce949ae2b232dde256cf890aef"
SOURCES = (
    "scripts/vlm_positive_order_plan.py",
    "scripts/vlm_positive_order_run.py",
    "tests/test_vlm_positive_order.py",
    "scripts/diagnose_vlm_v16.py",
    "tests/test_diagnose_vlm_v16.py",
    "docs/issue-4-vlm-pos-v16-investigacao-e-proposta.md",
    "docs/issue-4-vlm-pos-v16-pares-positivos-protocolo.md",
    "docs/issue-5-inventario-midias-demo.md",
    "docs/evidence/issue-5-inventario-midias-demo-20261020.json",
)


def configuration():
    # Pure receipt/source/token-file identity checks: never native grammar or tokenizer execution.
    return {
        "unchanged_v16": v16_configuration(),
        "sources": {n: file_hash(ROOT / n) for n in SOURCES},
    }


def load_base(parent, cohort, root):
    previous = root / "data/private/issue-4-vlm-v16-v2"
    old, state = load_v16(parent, cohort, previous, root)
    if (
        not state["sealed"]
        or state["calls_reserved"] != 24
        or state["halt_reason"] != "v16_neither_condition_passed_negatives"
        or state["acquisitions_reserved"] != 0
        or len(state["operations"]) != 24
        or digest(old["base"]["cases"]["positive"]) != POSITIVE_CASES_SHA256
    ):
        raise ValueError("positive_probe_sealed_failed_v16_required")
    before_path = root / PROOF / "before.json"
    before = json.loads(before_path.read_bytes())
    pins = before["protected_sha256"] | {str(before_path.relative_to(root)): file_hash(before_path)}
    for n in (
        "raw-reconstruction-guarded.json",
        "control-recipe-analysis.json",
        "replay-tests.xml",
    ):
        p = root / PROOF / n
        pins[str(p.relative_to(root))] = file_hash(p)
    if any(file_hash(root / n) != h for n, h in pins.items()):
        raise ValueError("positive_probe_protected_file_changed")
    return {
        "protected_sha256": pins,
        "cases": {"positive": old["base"]["cases"]["positive"]},
        "prior_calls": old["base"]["prior_calls"] + state["calls_reserved"],
        "prior_acquisitions": old["base"]["prior_acquisitions"],
        "prior_seconds": state["elapsed_seconds"],
        "ancestor_folders": old["base"]["ancestor_folders"] + [str(previous.relative_to(root))],
        "old_plan_sha256": old["plan_sha256"],
        "old_comparison_sha256": file_hash(previous / "comparison.json"),
        "old_unused_calls_closed": 10,
        "new_separate_budget_not_old_balance": True,
    }


def sequence(plan):
    return [
        (variant, "positive", case["sample_id"])
        for i, case in enumerate(plan["base"]["cases"]["positive"])
        for variant in (VARIANTS if i % 2 == 0 else tuple(reversed(VARIANTS)))
    ]


def enforce_queue(folder, root):
    if private_path(folder, root) != root / QUEUE:
        raise ValueError("positive_probe_single_queue_required")


def submit_clearance(folder, plan, state, body):
    if plan["protocol"] != PROTOCOL:
        raise ValueError("positive_probe_review_protocol_changed")
    return parent_submit_clearance(folder, plan, state, body)


def prepare(parent, cohort, folder, root):
    enforce_queue(folder, root)
    if folder.exists() and any(p.name != ".lock" for p in folder.iterdir()):
        raise ValueError("positive_probe_queue_already_prepared_or_consumed")
    base = load_base(parent, cohort, root)
    no_workers(root)
    body = {
        "protocol": PROTOCOL,
        "base": base,
        "configuration": configuration(),
        "limits": LIMITS,
        "authorization": AUTHORIZATION,
        "technical_review_required": True,
        "diagnostic_only_never_candidate": True,
    }
    body["plan_sha256"] = digest(body)
    exclusive(folder / "plan.json", body)
    exclusive(
        folder / "checkpoint.json",
        {
            "plan_sha256": body["plan_sha256"],
            "operations": [],
            "calls_reserved": 0,
            "acquisitions_reserved": 0,
            "new_session_seconds": 0.0,
            "session_overhead_seconds": 0.0,
            "elapsed_seconds": base["prior_seconds"],
            "sealed": False,
            "halt_reason": None,
            "technical_clearance_sha256": None,
        },
    )
    return body


def load(parent, cohort, folder, root):
    enforce_queue(folder, root)
    if any(p.is_symlink() for p in folder.rglob("*")) or any(
        (folder / n).exists() for n in ("images", "sessions")
    ):
        raise ValueError("positive_probe_unsafe_queue_or_acquisition")
    p = json.loads((folder / "plan.json").read_bytes())
    s = json.loads((folder / "checkpoint.json").read_bytes())
    if (
        p["protocol"] != PROTOCOL
        or p["plan_sha256"] != digest({k: v for k, v in p.items() if k != "plan_sha256"})
        or p["base"] != load_base(parent, cohort, root)
        or p["configuration"] != configuration()
        or p["limits"] != LIMITS
        or p["authorization"] != AUTHORIZATION
        or p["technical_review_required"] is not True
        or p["diagnostic_only_never_candidate"] is not True
        or s["plan_sha256"] != p["plan_sha256"]
        or type(s["sealed"]) is not bool
    ):
        raise ValueError("positive_probe_plan_or_sources_changed")
    entries = s["operations"]
    marker_path = folder / "execution-started.json"
    if marker_path.exists():
        if json.loads(marker_path.read_bytes()) != start_marker(p, s):
            raise ValueError("positive_probe_start_marker_changed")
    elif entries or s["sealed"]:
        raise ValueError("positive_probe_start_marker_required")
    expected = sequence(p)
    if (
        [(e["variant"], e["kind"], e["sample_id"]) for e in entries] != expected[: len(entries)]
        or len(entries) > CALL_LIMIT
        or any(e["status"] != "completed" for e in entries[:-1])
    ):
        raise ValueError("positive_probe_order_or_scope_changed")
    seconds, number, wanted = 0.0, 0, set()
    for index, e in enumerate(entries, 1):
        if (
            e["status"] not in ("running", "completed", "failed")
            or type(e["call_count"]) is not int
            or e["call_count"] not in (0, 1)
            or (e["status"] == "completed" and e["call_count"] != 1)
            or type(e["seconds"]) not in (int, float)
            or not math.isfinite(e["seconds"])
            or e["seconds"] < 0
            or type(e["unmeasured_reserved_seconds"]) not in (int, float)
            or not 0 <= e["unmeasured_reserved_seconds"] <= 180
            or e["unmeasured_reserved_seconds"] > e["seconds"]
        ):
            raise ValueError("positive_probe_invalid_consumption")
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
                "kind": "positive",
                "sample_id": e["sample_id"],
                "frame": 1,
                "number": number,
            }:
                raise ValueError("positive_probe_reservation_changed")
        if e["status"] == "running":
            continue  # Crash/in-flight consumption remains charged; runnable refuses reentry.
        if files_for(folder, e) != e["files_sha256"]:
            raise ValueError("positive_probe_operation_evidence_changed")
        directory = result_path(folder, e).parent / "calls"
        names = {x.name for x in directory.glob("*")}
        required = {"frame-1.json"} if e["call_count"] else set()
        if names != required and not (e["status"] == "failed" and not names):
            raise ValueError("positive_probe_native_count_changed")
        for name in names:
            call = json.loads((directory / name).read_bytes())
            variant = e["variant"]
            case = next(
                c for c in p["base"]["cases"]["positive"] if c["sample_id"] == e["sample_id"]
            )
            if (
                call["schema_version"] != VERSION
                or call["variant"] != variant
                or call["frame"] != 1
                or call["specification_sha256"] != digest(specification(variant))
                or call["ordered_schema_sha256"]
                != ordered_schema_hash(specification(variant)["schema"])
                or call["input_png_sha256"] != case["png_sha256"]
                or call["status"] not in ("running", "response_captured", "failed", "completed")
                or (
                    e["status"] == "completed"
                    and e["seconds"] + 1e-8 < call.get("runtime_seconds", 0)
                )
            ):
                raise ValueError("positive_probe_native_receipt_changed")
            if (
                call["status"] == "completed"
                and decode(call["raw_response"], variant)[0] != call["parsed"]
            ):
                raise ValueError("positive_probe_native_parse_changed")
            if (
                "raw_response_sha256" in call
                and hashlib.sha256(call["raw_response"].encode()).hexdigest()
                != call["raw_response_sha256"]
            ):
                raise ValueError("positive_probe_native_raw_changed")
        if e["status"] == "completed":
            checked_result(folder, p, e)
            for key, maximum in (
                ("runtime_seconds", 180),
                ("runtime_peak_rss_mib", 3.3 * 1024),
                ("diagnostic_wall_seconds", call["diagnostic_deadline_seconds"]),
            ):
                value = call.get(key)
                if (
                    type(value) not in (int, float)
                    or not math.isfinite(value)
                    or not 0 <= value <= maximum
                ):
                    raise ValueError("positive_probe_completed_resource_receipt_changed")
    if {x.name for x in (folder / "reservations").glob("*")} != wanted:
        raise ValueError("positive_probe_unreserved_call_or_acquisition")
    if (
        type(s["calls_reserved"]) is not int
        or number != s["calls_reserved"]
        or number > CALL_LIMIT
        or type(s["acquisitions_reserved"]) is not int
        or s["acquisitions_reserved"] != 0
        or type(s["session_overhead_seconds"]) not in (int, float)
        or not math.isfinite(s["session_overhead_seconds"])
        or s["session_overhead_seconds"] < -1e-8
        or not math.isclose(
            seconds + s["session_overhead_seconds"],
            s["new_session_seconds"],
            rel_tol=0,
            abs_tol=1e-8,
        )
        or not math.isclose(
            p["base"]["prior_seconds"] + s["new_session_seconds"],
            s["elapsed_seconds"],
            rel_tol=0,
            abs_tol=1e-8,
        )
        or (s["new_session_seconds"] > SESSION_LIMIT and not s["halt_reason"])
    ):
        raise ValueError("positive_probe_budget_changed")
    check_clearance(folder, p, s)
    if s["sealed"]:
        from scripts.vlm_positive_order_run import comparison

        path = folder / "comparison.json"
        report = json.loads(path.read_bytes())
        if (
            file_hash(path) != s["comparison_file_sha256"]
            or report != comparison(folder, p, s)
            or not s["halt_reason"]
            or any(e["status"] == "running" for e in entries)
        ):
            raise ValueError("positive_probe_terminal_claim_changed")
    return p, s


def start_marker(plan, state):
    return {
        "plan_sha256": plan["plan_sha256"],
        "configuration_sha256": digest(plan["configuration"]),
        "technical_clearance_sha256": state["technical_clearance_sha256"],
        "attempt": 1,
        "uncertain_session_charge_upper_bound_seconds": SESSION_LIMIT,
        "no_reentry_even_before_first_reservation_or_between_completed_calls": True,
    }


def runnable(state):
    if (
        state["sealed"]
        or state["halt_reason"]
        or any(e["status"] != "completed" for e in state["operations"])
    ):
        raise ValueError("positive_probe_consumed_or_uncertain_no_retry")
    if state["new_session_seconds"] >= SESSION_LIMIT:
        raise ValueError("positive_probe_session_budget_exhausted")

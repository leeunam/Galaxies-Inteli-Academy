"""Paired positive diagnostic on five already frozen crops, never an approval gate."""

from __future__ import annotations

import argparse
import json
import math
import tempfile
import time
from contextlib import ExitStack
from pathlib import Path

from PIL import Image

from scripts.expansion_media import deadline
from scripts.gguf_visual_attributes import invoke_local_vlm
from scripts.private_checkpoint import digest, file_hash, lock, private_path
from scripts.retrain_expansion import reserved_guard
from scripts.vlm_positive_order_plan import (
    CALL_LIMIT,
    SESSION_LIMIT,
    check_clearance,
    checked_result,
    configuration,
    exclusive,
    files_for,
    load,
    no_workers,
    prepare,
    result_path,
    runnable,
    sequence,
    start_marker,
    submit_clearance,
)
from scripts.vlm_product_limited import verify_runtime
from scripts.vlm_product_v16 import FIELD, VARIANTS, extract, save
from scripts.vlm_product_v16_plan import case_for, correct


def comparison(folder, plan, state):
    measured = {}
    for variant in VARIANTS:
        rows = []
        for e in state["operations"]:
            if e["variant"] == variant and e["status"] == "completed":
                case = case_for(plan, "positive", e["sample_id"])
                r = checked_result(folder, plan, e)
                rows.append(
                    {
                        "sample_id": e["sample_id"],
                        "correct_supported_true": correct(case, r),
                        "value": r["parsed"][FIELD]["value"],
                        "native": r["native_intermediate"][0],
                        "derived": r["intermediate"][0],
                    }
                )
        measured[variant] = {
            "completed": len(rows),
            "required": 5,
            "true": sum(r["value"] is True for r in rows),
            "false": sum(r["value"] is False for r in rows),
            "unknown": sum(r["value"] == "unknown" for r in rows),
            "correct_supported_true": sum(r["correct_supported_true"] for r in rows),
            "any_raw_true": any(r["value"] is True for r in rows),
            "any_supported_true": any(r["correct_supported_true"] for r in rows),
            "observations": rows,
        }
    a, b = ({r["sample_id"]: r for r in measured[v]["observations"]} for v in VARIANTS)
    shared = sorted(a.keys() & b.keys())
    report = {
        "status": "post_v16_positive_diagnostic_sealed",
        "plan_sha256": plan["plan_sha256"],
        "condition_scores": measured,
        "paired": {
            "complete_pairs": len(shared),
            "required_pairs": 5,
            "state_first_gains": sum(
                b[n]["correct_supported_true"] and not a[n]["correct_supported_true"]
                for n in shared
            ),
            "state_first_losses": sum(
                a[n]["correct_supported_true"] and not b[n]["correct_supported_true"]
                for n in shared
            ),
        },
        "complete": len(shared) == 5,
        "stop_reason": state["halt_reason"],
        "new_calls_reserved": state["calls_reserved"],
        "new_acquisitions_reserved": 0,
        "cumulative_calls": plan["base"]["prior_calls"] + state["calls_reserved"],
        "cumulative_acquisitions": plan["base"]["prior_acquisitions"],
        "new_session_seconds": state["new_session_seconds"],
        "cumulative_session_seconds": state["elapsed_seconds"],
        "unused_calls_closed": CALL_LIMIT - state["calls_reserved"],
        "old_unused_calls_still_closed": 10,
        "candidate_for_further_development": [],
        "released_fields": [],
        "v16_still_failed": True,
        "diagnostic_only": True,
        "test_evaluated": False,
        "m1_replaced": False,
        "new_blind_audit": False,
        "predictive_training_started": False,
        "positive_sampling_unit": "five_known_crops_from_three_fashion_training_videos",
        "completed_result_sha256": {
            str(result_path(folder, e).relative_to(folder)): file_hash(result_path(folder, e))
            for e in state["operations"]
            if e["status"] == "completed"
        },
        "native_receipt_sha256": {
            str(p.relative_to(folder)): file_hash(p)
            for p in sorted((folder / "results").glob("*/*/*/calls/*.json"))
        },
    }
    report["comparison_sha256"] = digest(report)
    return report


def seal(folder, plan, state):
    report = comparison(folder, plan, state)
    exclusive(folder / "comparison.json", report)
    state.update(sealed=True, comparison_file_sha256=file_hash(folder / "comparison.json"))
    save(folder / "checkpoint.json", state)
    return report


def persist_session(folder, plan, state, session_started, clock, *, now=None, provisional=0.0):
    now = clock() if now is None else now
    state["new_session_seconds"] = now - session_started + provisional
    state["session_overhead_seconds"] = state["new_session_seconds"] - sum(
        e["seconds"] for e in state["operations"]
    )
    state["elapsed_seconds"] = plan["base"]["prior_seconds"] + state["new_session_seconds"]
    save(folder / "checkpoint.json", state)


def one(folder, plan, state, operation, root, *, invoker, session_started, clock=time.monotonic):
    expected = sequence(plan)
    if (
        len(state["operations"]) >= len(expected)
        or tuple(operation) != expected[len(state["operations"])]
    ):
        raise ValueError("positive_probe_out_of_scope_dispatch")
    variant, kind, sample = operation
    case = case_for(plan, kind, sample)
    entry = {
        "variant": variant,
        "kind": kind,
        "sample_id": sample,
        "status": "running",
        "call_count": 0,
        "seconds": 0.0,
        "unmeasured_reserved_seconds": 0.0,
    }
    state["operations"].append(entry)
    started = clock()
    allocation = None

    def persist(provisional=0.0):
        now = clock()
        entry["seconds"] = now - started + provisional
        entry["unmeasured_reserved_seconds"] = provisional
        persist_session(
            folder, plan, state, session_started, clock, now=now, provisional=provisional
        )

    def remaining():
        return SESSION_LIMIT - (clock() - session_started)

    def reserve(frame):
        nonlocal allocation
        available = remaining() - 5
        if available <= 0:
            raise TimeoutError("positive_probe_session_budget_exhausted")
        with deadline(available):
            same_configuration = configuration() == plan["configuration"]
            reviewed = check_clearance(folder, plan, state)
        if not same_configuration or not reviewed:
            raise ValueError("positive_probe_sources_or_review_changed_before_dispatch")
        if frame != 1 or entry["call_count"] or state["calls_reserved"] >= CALL_LIMIT:
            raise ValueError("positive_probe_call_budget_exhausted")
        if remaining() <= 5:
            raise TimeoutError("positive_probe_session_budget_exhausted")
        allocation = min(180, remaining() - 5)
        entry["call_count"] = 1
        state["calls_reserved"] += 1
        exclusive(
            folder / "reservations" / f"native-{state['calls_reserved']:04d}.json",
            {
                "plan_sha256": plan["plan_sha256"],
                "operation": len(state["operations"]),
                "variant": variant,
                "kind": kind,
                "sample_id": sample,
                "frame": 1,
                "number": state["calls_reserved"],
            },
        )
        persist(allocation)

    def bounded(*args, **kwargs):
        try:
            available = min(allocation, remaining() - 5)
            if available <= 0:
                raise TimeoutError("positive_probe_session_budget_exhausted")
            native_started = clock()
            with deadline(available):
                output = invoker(*args, **kwargs)
            # Retain every returned raw through the unchanged extractor before resource checks.
            return output | {
                "diagnostic_wall_seconds": clock() - native_started,
                "diagnostic_deadline_seconds": available,
            }
        finally:
            persist()

    persist()
    try:
        if json.loads((folder / "execution-started.json").read_bytes()) != start_marker(
            plan, state
        ):
            raise ValueError("positive_probe_start_marker_required")
        scratch = root / "data/private/media-temp"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="galaxies-positive-order-", dir=scratch) as temp:
            work = Path(temp)
            cell = work / "crop.png"
            sheet = root / case["sheet_path"]
            if file_hash(sheet) != case["sheet_sha256"]:
                raise ValueError("positive_probe_original_sheet_changed")
            with Image.open(sheet) as image:
                if image.mode != "RGB" or image.size != (1280, 360):
                    raise ValueError("positive_probe_original_sheet_changed")
                index = case["source_frame"] - 1
                image.crop((320 * index, 25, 320 * (index + 1), 355)).save(cell)
            if file_hash(cell) != case["png_sha256"]:
                raise ValueError("positive_probe_original_crop_changed")
            path = result_path(folder, entry)
            r = extract(
                [cell],
                [case["seconds"]],
                work,
                variant=variant,
                evidence_dir=path.parent / "calls",
                reserve=reserve,
                invoker=bounded,
            )
            save(path, {"plan_sha256": plan["plan_sha256"], "case_sha256": digest(case), "vlm": r})
            checked_result(folder, plan, entry)
            call = json.loads((path.parent / "calls/frame-1.json").read_bytes())
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
                    raise ValueError("positive_probe_native_resource_limit_or_receipt")
        if remaining() < 0:
            raise TimeoutError("positive_probe_session_budget_exhausted")
        entry["status"] = "completed"
    except BaseException as error:
        entry.update(status="failed", error_type=type(error).__name__)
        state["halt_reason"] = "positive_probe_operation_failed_" + type(error).__name__
        raise
    finally:
        entry["files_sha256"] = files_for(folder, entry)
        persist()


def execute(parent, cohort, folder, root, *, invoker=invoke_local_vlm, clock=time.monotonic):
    folder = private_path(folder, root)
    plan, _ = load(parent, cohort, folder, root)
    with ExitStack() as stack:
        for name in plan["base"]["ancestor_folders"]:
            stack.enter_context(lock(private_path(root / name, root) / ".lock"))
        stack.enter_context(lock(folder / ".lock"))
        plan, state = load(parent, cohort, folder, root)
        runnable(state)
        if state["operations"] or (folder / "execution-started.json").exists():
            raise ValueError("positive_probe_consumed_or_uncertain_no_retry")
        if not check_clearance(folder, plan, state):
            raise ValueError("positive_probe_technical_review_required")
        session_started = clock()
        exclusive(folder / "execution-started.json", start_marker(plan, state))
        error = None

        def checked_phase(check):
            available = SESSION_LIMIT - (clock() - session_started) - 5
            if available <= 0:
                raise TimeoutError("positive_probe_session_budget_exhausted")
            with deadline(available):
                check()
            persist_session(folder, plan, state, session_started, clock)
            if SESSION_LIMIT - (clock() - session_started) <= 5:
                raise TimeoutError("positive_probe_session_budget_exhausted")

        try:
            persist_session(folder, plan, state, session_started, clock)
            checked_phase(lambda: no_workers(root))
            checked_phase(verify_runtime)
            allowed = sequence(plan)
            while len(state["operations"]) < len(allowed):
                runnable(state)
                checked_phase(lambda: load(parent, cohort, folder, root))
                operation = allowed[len(state["operations"])]
                one(
                    folder,
                    plan,
                    state,
                    operation,
                    root,
                    invoker=invoker,
                    session_started=session_started,
                    clock=clock,
                )
                print(
                    json.dumps(
                        {
                            "completed_operations": len(state["operations"]),
                            "calls_reserved": state["calls_reserved"],
                            "acquisitions_reserved": 0,
                            "new_session_seconds": state["new_session_seconds"],
                        }
                    ),
                    flush=True,
                )
        except BaseException as caught:  # noqa: BLE001 - seal cancellation and consumption before rethrow
            error = caught
            state["halt_reason"] = (
                state["halt_reason"] or "positive_probe_execution_failed_" + type(caught).__name__
            )
        state["halt_reason"] = (
            state["halt_reason"] or "positive_probe_authorized_diagnostic_completed"
        )
        persist_session(folder, plan, state, session_started, clock)
        report = seal(folder, plan, state)
        if error is not None:
            raise error
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("prepare", "inspect", "clearance", "execute"))
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--cohort-dir", type=Path, required=True)
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--clearance-file", type=Path)
    args = parser.parse_args()
    root = Path.cwd()
    folder = private_path(args.folder, root)
    with reserved_guard(args.parent, root), reserved_guard(args.cohort_dir, root):
        if args.operation == "execute":
            report = execute(args.parent, args.cohort_dir, folder, root)
            output = {
                k: report[k]
                for k in (
                    "stop_reason",
                    "new_calls_reserved",
                    "new_acquisitions_reserved",
                    "candidate_for_further_development",
                    "paired",
                    "complete",
                )
            }
        else:
            with lock(folder / ".lock"):
                if args.operation == "prepare":
                    output = {
                        "plan_sha256": prepare(args.parent, args.cohort_dir, folder, root)[
                            "plan_sha256"
                        ]
                    }
                else:
                    plan, state = load(args.parent, args.cohort_dir, folder, root)
                    if args.operation == "clearance":
                        if args.clearance_file is None:
                            raise ValueError("positive_probe_clearance_file_required")
                        submit_clearance(
                            folder, plan, state, json.loads(args.clearance_file.read_bytes())
                        )
                    output = {
                        k: state[k]
                        for k in (
                            "calls_reserved",
                            "acquisitions_reserved",
                            "sealed",
                            "halt_reason",
                            "technical_clearance_sha256",
                        )
                    }
    print(json.dumps(output), flush=True)


if __name__ == "__main__":
    main()

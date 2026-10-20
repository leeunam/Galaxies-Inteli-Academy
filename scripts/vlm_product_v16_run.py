"""Single authorized V16 order diagnostic; no network, acquisition or automatic successor."""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from collections import Counter
from contextlib import ExitStack
from pathlib import Path

from PIL import Image

from scripts.expansion_media import deadline
from scripts.gguf_visual_attributes import invoke_local_vlm
from scripts.private_checkpoint import digest, file_hash, lock, private_path
from scripts.retrain_expansion import reserved_guard
from scripts.vlm_product_limited import verify_runtime
from scripts.vlm_product_v16 import FIELD, VARIANTS, extract, save
from scripts.vlm_product_v16_plan import (
    CALL_LIMIT,
    SESSION_LIMIT,
    case_for,
    check_clearance,
    checked_result,
    configuration,
    correct,
    eligible_conditions,
    exclusive,
    files_for,
    load,
    no_workers,
    prepare,
    result_path,
    runnable,
    sequence,
    submit_clearance,
)
from scripts.vlm_prompt_development import render_control
from scripts.vlm_prompt_plan import controls


def scores(folder, plan, state):
    result = {}
    for v in VARIANTS:
        result[v] = {}
        for kind, required in (("negative", 12), ("positive", 5)):
            rows = []
            for e in state["operations"]:
                if e["variant"] == v and e["kind"] == kind and e["status"] == "completed":
                    case = case_for(plan, kind, e["sample_id"])
                    r = checked_result(folder, plan, e)
                    rows.append(
                        {
                            "sample_id": e["sample_id"],
                            "correct": correct(case, r),
                            "value": r["parsed"][FIELD]["value"],
                            "native": r["native_intermediate"][0],
                            "derived": r["intermediate"][0],
                        }
                    )
            result[v][kind] = {
                "completed": len(rows),
                "correct": sum(r["correct"] for r in rows),
                "true": sum(r["value"] is True for r in rows),
                "false": sum(r["value"] is False for r in rows),
                "unknown": sum(r["value"] == "unknown" for r in rows),
                "passed": len(rows) == required and all(r["correct"] for r in rows),
                "observations": rows,
                "configurations": dict(Counter(r["native"]["item_configuration"] for r in rows)),
            }
    return result


def pair_scores(measured):
    paired = {}
    for kind in ("negative", "positive"):
        a, b = ({r["sample_id"]: r for r in measured[v][kind]["observations"]} for v in VARIANTS)
        shared = sorted(a.keys() & b.keys())
        paired[kind] = {
            "same_crops": len(shared),
            "state_first_gains": sum(b[n]["correct"] and not a[n]["correct"] for n in shared),
            "state_first_losses": sum(a[n]["correct"] and not b[n]["correct"] for n in shared),
        }
    return paired


def seal(folder, plan, state):
    if state["sealed"]:
        return json.loads((folder / "comparison.json").read_bytes())
    measured = scores(folder, plan, state)
    paired = pair_scores(measured)
    candidates = [
        v
        for v in VARIANTS
        if measured[v]["negative"]["passed"] and measured[v]["positive"]["passed"]
    ]
    report = {
        "status": "v16_order_diagnostic_sealed",
        "plan_sha256": plan["plan_sha256"],
        "condition_scores": measured,
        "paired": paired,
        "candidate_for_further_development": candidates,
        "stop_reason": state["halt_reason"] or "authorized_scope_completed",
        "positive_gate_eligible": eligible_conditions(folder, plan, state),
        "new_calls_reserved": state["calls_reserved"],
        "new_acquisitions_reserved": 0,
        "cumulative_calls": plan["base"]["prior_calls"] + state["calls_reserved"],
        "cumulative_acquisitions": plan["base"]["prior_acquisitions"],
        "new_session_seconds": state["new_session_seconds"],
        "cumulative_session_seconds": state["elapsed_seconds"],
        "unused_calls_closed": 34 - state["calls_reserved"],
        "released_fields": [],
        "test_evaluated": False,
        "m1_replaced": False,
        "new_blind_audit": False,
        "predictive_training_started": False,
        "causal_scope": "serialization_order_under_the_same_neutral_prompt_not_historical_v14_to_v15_cause",
        "positive_sampling_unit": "five_known_crops_from_three_videos_not_five_independent_videos",
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
    exclusive(folder / "comparison.json", report)
    state.update(sealed=True, comparison_file_sha256=file_hash(folder / "comparison.json"))
    save(folder / "checkpoint.json", state)
    return report


def one(folder, plan, state, operation, root, *, invoker, clock=time.monotonic):
    expected = sequence(plan, eligible_conditions(folder, plan, state))
    if (
        len(state["operations"]) >= len(expected)
        or tuple(operation) != expected[len(state["operations"])]
    ):
        raise ValueError("v16_out_of_scope_dispatch")
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
        entry["seconds"] = clock() - started + provisional
        entry["unmeasured_reserved_seconds"] = provisional
        state["new_session_seconds"] = sum(e["seconds"] for e in state["operations"])
        state["elapsed_seconds"] = plan["base"]["prior_seconds"] + state["new_session_seconds"]
        save(folder / "checkpoint.json", state)

    def remaining():
        return (
            SESSION_LIMIT
            - sum(e["seconds"] for e in state["operations"][:-1])
            - (clock() - started)
        )

    def reserve(frame):
        nonlocal allocation
        if configuration() != plan["configuration"] or not check_clearance(folder, plan, state):
            raise ValueError("v16_sources_or_review_changed_before_dispatch")
        if frame != 1 or entry["call_count"] or state["calls_reserved"] >= CALL_LIMIT:
            raise ValueError("v16_call_budget_exhausted")
        if remaining() <= 5:
            raise TimeoutError("v16_session_budget_exhausted")
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
            with deadline(min(allocation, remaining() - 5)):
                return invoker(*args, **kwargs)
        finally:
            persist()

    persist()
    try:
        scratch = root / "data/private/media-temp"
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="galaxies-inference-v16-", dir=scratch) as temp:
            work = Path(temp)
            cell = work / "crop.png"
            if kind == "negative":
                render_control(next(r for r in controls() if r["sample_id"] == sample), cell)
            else:
                sheet = root / case["sheet_path"]
                if file_hash(sheet) != case["sheet_sha256"]:
                    raise ValueError("v16_original_sheet_changed")
                with Image.open(sheet) as image:
                    if image.mode != "RGB" or image.size != (1280, 360):
                        raise ValueError("v16_original_sheet_changed")
                    index = case["source_frame"] - 1
                    image.crop((320 * index, 25, 320 * (index + 1), 355)).save(cell)
            if file_hash(cell) != case["png_sha256"]:
                raise ValueError("v16_original_crop_changed")
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
        entry["status"] = "completed"
    except BaseException as error:
        entry.update(status="failed", error_type=type(error).__name__)
        state["halt_reason"] = "v16_operation_failed_" + type(error).__name__
        raise
    finally:
        entry["files_sha256"] = files_for(folder, entry)
        persist()


def execute(parent, cohort, folder, root, *, invoker=invoke_local_vlm):
    folder = private_path(folder, root)
    plan, _ = load(parent, cohort, folder, root)
    with ExitStack() as stack:
        for name in plan["base"]["ancestor_folders"]:
            stack.enter_context(lock(private_path(root / name, root) / ".lock"))
        stack.enter_context(lock(folder / ".lock"))
        plan, state = load(parent, cohort, folder, root)
        runnable(state)
        if not check_clearance(folder, plan, state):
            raise ValueError("v16_technical_review_required")
        no_workers(root)
        verify_runtime()
        error = None
        try:
            while True:
                runnable(state)
                allowed = sequence(plan, eligible_conditions(folder, plan, state))
                if len(state["operations"]) == len(allowed):
                    break
                load(parent, cohort, folder, root)
                operation = allowed[len(state["operations"])]
                one(folder, plan, state, operation, root, invoker=invoker)
                print(
                    json.dumps(
                        {
                            "variant": operation[0],
                            "kind": operation[1],
                            "completed_operations": len(state["operations"]),
                            "calls_reserved": state["calls_reserved"],
                            "acquisitions_reserved": 0,
                            "new_session_seconds": state["new_session_seconds"],
                        }
                    ),
                    flush=True,
                )
        except BaseException as caught:  # noqa: BLE001 - preserve the one-shot ledger before rethrow
            error = caught
            state["halt_reason"] = (
                state["halt_reason"] or "v16_execution_failed_" + type(caught).__name__
            )
        if not state["halt_reason"]:
            candidates = eligible_conditions(folder, plan, state)
            state["halt_reason"] = (
                "v16_neither_condition_passed_negatives"
                if not candidates
                else "v16_authorized_scope_completed"
            )
        save(folder / "checkpoint.json", state)
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
                            raise ValueError("v16_clearance_file_required")
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

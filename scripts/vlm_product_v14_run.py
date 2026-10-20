"""Execute the authorized V14-R blocks once, then seal a development-only report."""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from contextlib import ExitStack
from pathlib import Path

from scripts.expansion_media import deadline
from scripts.gguf_visual_attributes import invoke_local_vlm
from scripts.pilot_licensed_media import run_session
from scripts.private_checkpoint import digest, file_hash, lock, private_path
from scripts.retrain_expansion import reserved_guard
from scripts.vlm_per_frame import aggregate
from scripts.vlm_product_development import cached_result
from scripts.vlm_product_limited import verify_runtime
from scripts.vlm_product_v14 import FIELD, extract, save
from scripts.vlm_product_v14_plan import (
    CALL_LIMIT,
    SESSION_LIMIT,
    checked_result,
    configuration,
    correct,
    files_for,
    load,
    no_workers,
    phase_passed,
    prepare,
    reserve_record,
    result_path,
    runnable,
    sequence,
)
from scripts.vlm_product_v14_review import check_reviews, submit_review
from scripts.vlm_prompt_development import metrics, render_control
from scripts.vlm_prompt_plan import controls
from scripts.vlm_revision import acquire_row, crops


def panel_ready(scores, count):
    if count != 20:
        return False
    return all(
        scores[s]["samples"] == 10
        and scores[s]["known"] >= 8
        and scores[s]["correct_value_and_evidence"] / scores[s]["known"] >= 0.9
        and scores[s]["unsupported_evidence"] == 0
        and all(scores[s]["predicted_value_support"].get(v, 0) >= 1 for v in ("true", "false"))
        for s in ("beleza", "moda")
    ) and all(scores["all"]["predicted_value_support"].get(v, 0) >= 3 for v in ("true", "false"))


def observation(plan, row, current, baseline):
    if (
        current["input_png_sha256"] != baseline["input_png_sha256"]
        or current["input_frame_seconds"] != baseline["input_frame_seconds"]
    ):
        raise ValueError("v14_comparison_pixels_or_times_changed")
    frames = [dict(f) for f in baseline["per_frame"]]
    for i, frame in enumerate(current["per_frame"]):
        frames[i][FIELD] = frame[FIELD]
    predicted = aggregate(frames, current["input_frame_seconds"])
    if any(predicted[f] != baseline["parsed"][f] for f in ("person_visible", "screen_text")):
        raise ValueError("v14_person_text_cache_changed")
    return {
        "sample_id": row["sample_id"],
        "sector": row["sector"],
        "annotated": plan["base"]["truth"][row["sample_id"]],
        "predicted": predicted,
        "per_frame": frames,
    }


def control_comparison(folder, plan, state, root):
    values = {"cache_v11": {}, "cache_v13_R": {}, "v14_R": {}}
    for name, key in (
        ("cache_v11", "v11_control_references"),
        ("cache_v13_R", "v13_control_references"),
    ):
        for sample, reference in plan["base"][key].items():
            path = root / reference["path"]
            if file_hash(path) != reference["sha256"]:
                raise ValueError("v14_control_reference_changed")
            result = json.loads(path.read_bytes())["vlm"]
            expected = plan["base"]["inputs"][sample]
            if (
                result["input_png_sha256"] != expected["png_sha256"]
                or result["input_frame_seconds"] != expected["seconds"]
            ):
                raise ValueError("v14_control_reference_identity_changed")
            values[name][sample] = result["parsed"][FIELD]["value"]
    for entry in state["operations"]:
        if entry["kind"] == "control" and entry["status"] == "completed":
            values["v14_R"][entry["sample_id"]] = checked_result(folder, plan, entry)["parsed"][
                FIELD
            ]["value"]
    pairs = {}
    for name in ("cache_v11", "cache_v13_R"):
        same = sorted(values[name].keys() & values["v14_R"].keys())
        pairs["paired_v14_R_vs_" + name] = {
            "same_cases": len(same),
            "gains": sum(
                values["v14_R"][n] is False and values[name][n] is not False for n in same
            ),
            "losses": sum(
                values[name][n] is False and values["v14_R"][n] is not False for n in same
            ),
        }
    return {
        "counts": {
            name: {
                "samples": len(rows),
                "false_correct": sum(v is False for v in rows.values()),
                "true": sum(v is True for v in rows.values()),
                "unknown": sum(v == "unknown" for v in rows.values()),
            }
            for name, rows in values.items()
        },
        "values": values,
        **pairs,
        "v12_accepted_results": 0,
        "unavailable_video_caches": {"v11": 0, "v12": 0},
    }


def seal(folder, plan, state, root):
    if state["sealed"]:
        return json.loads((folder / "comparison.json").read_bytes())
    observations = {name: [] for name in ("v14", "v13", "v10", "v9", "v8", "v7_A", "v7_B_old32")}
    control_scores = []
    for entry in state["operations"]:
        if entry["status"] != "completed" or entry["kind"] == "acquisition":
            continue
        current = checked_result(folder, plan, entry)
        if entry["kind"] == "control":
            control_scores.append(
                {
                    "sample_id": entry["sample_id"],
                    "correct": correct(plan, entry, current),
                    "value": current["parsed"][FIELD]["value"],
                }
            )
            continue
        row = next(r for r in plan["base"]["rows"] if r["sample_id"] == entry["sample_id"])
        baseline = cached_result(root, row)
        observations["v14"].append(observation(plan, row, current, baseline))
        if entry["sample_id"] in plan["base"]["v13_references"]:
            reference = plan["base"]["v13_references"][entry["sample_id"]]
            if file_hash(root / reference["path"]) != reference["sha256"]:
                raise ValueError("v14_v13_reference_changed")
            old_v13 = json.loads((root / reference["path"]).read_bytes())["vlm"]
            observations["v13"].append(observation(plan, row, old_v13, baseline))
        if entry["sample_id"] in plan["base"]["v10_references"]:
            reference = plan["base"]["v10_references"][entry["sample_id"]]
            if file_hash(root / reference["path"]) != reference["sha256"]:
                raise ValueError("v14_v10_reference_changed")
            old_v10 = json.loads((root / reference["path"]).read_bytes())["vlm"]
            observations["v10"].append(observation(plan, row, old_v10, baseline))
        ref = plan["base"]["v9_references"][entry["sample_id"]]
        if file_hash(root / ref["path"]) != ref["sha256"]:
            raise ValueError("v14_v9_reference_changed")
        prior = json.loads((root / ref["path"]).read_bytes())["vlm"]
        observations["v9"].append(observation(plan, row, prior, baseline))
        observations["v8"].append(observation(plan, row, baseline, baseline))
        for name, candidate in (("v7_A", "A"), ("v7_B_old32", "B")):
            if candidate == "B" and row["group"] != "development":
                continue
            old = cached_result(root, row, candidate)
            if (
                old["input_png_sha256"] != current["input_png_sha256"]
                or old["input_frame_seconds"] != current["input_frame_seconds"]
            ):
                raise ValueError("v14_legacy_comparison_identity_changed")
            observations[name].append(
                {
                    "sample_id": row["sample_id"],
                    "sector": row["sector"],
                    "annotated": plan["base"]["truth"][row["sample_id"]],
                    "predicted": old["parsed"],
                    "per_frame": old["per_frame"],
                }
            )
    scores = {
        name: {
            "all_available": metrics(rows)[FIELD],
            "phase1": metrics([r for r in rows if r["sample_id"] in plan["base"]["phase1_ids"]])[
                FIELD
            ],
            "phase2": metrics([r for r in rows if r["sample_id"] in plan["base"]["phase2_ids"]])[
                FIELD
            ],
        }
        for name, rows in observations.items()
    }
    paired = {}
    current_by_id = {r["sample_id"]: r for r in observations["v14"]}
    for name, rows in observations.items():
        if name == "v14":
            continue
        gain = loss = 0
        for row in rows:
            actual = row["annotated"][FIELD]

            def ok(o, actual=actual):
                p = o["predicted"][FIELD]
                return (
                    p["value"] == actual["value"]
                    and bool(p["frames"])
                    and set(p["frames"]) <= set(actual["frames"])
                )

            a, b = ok(current_by_id[row["sample_id"]]), ok(row)
            gain += a and not b
            loss += b and not a
        paired[name] = {"same_cases": len(rows), "gains": gain, "losses": loss}
    report = {
        "status": "v14_revealed_development_sealed",
        "plan_sha256": plan["plan_sha256"],
        "evaluated_cases": len(observations["v14"]),
        "controls": control_scores,
        "controls_correct": sum(r["correct"] for r in control_scores),
        "control_comparison": control_comparison(folder, plan, state, root),
        "phase1_passed": phase_passed(folder, plan, state, "control", 12)
        and phase_passed(folder, plan, state, "preserved", 8)
        and check_reviews(folder, plan, state).get("phase1", False),
        "phase1_value_and_frames_passed": phase_passed(folder, plan, state, "control", 12)
        and phase_passed(folder, plan, state, "preserved", 8),
        "cue_reviews": check_reviews(folder, plan, state),
        "metrics": scores,
        "paired": paired,
        "panel_descriptive_readiness": panel_ready(
            scores["v14"]["all_available"], len(observations["v14"])
        )
        and check_reviews(folder, plan, state).get("phase2", False),
        "stop_reason": state["halt_reason"] or "authorized_scope_completed",
        "new_calls_reserved": state["calls_reserved"],
        "new_acquisitions_reserved": state["acquisitions_reserved"],
        "cumulative_calls": plan["base"]["prior_calls"] + state["calls_reserved"],
        "cumulative_acquisitions": plan["base"]["prior_acquisitions"]
        + state["acquisitions_reserved"],
        "new_session_seconds": state["new_session_seconds"],
        "cumulative_session_seconds": state["elapsed_seconds"],
        "same_pixels_and_times": True,
        "person_text_cache_preserved": True,
        "released_fields": [],
        "new_blind_audit": False,
        "predictive_training_started": False,
        "test_evaluated": False,
        "m1_replaced": False,
        "completed_result_sha256": {
            str(result_path(folder, e["kind"], e["sample_id"]).relative_to(folder)): file_hash(
                result_path(folder, e["kind"], e["sample_id"])
            )
            for e in state["operations"]
            if e["status"] == "completed" and e["kind"] != "acquisition"
        },
        "native_receipt_sha256": {
            str(p.relative_to(folder)): file_hash(p)
            for p in sorted((folder / "results").glob("*/*/calls/*.json"))
        },
    }
    report["comparison_sha256"] = digest(report)
    if (folder / "comparison.json").exists():
        if json.loads((folder / "comparison.json").read_bytes()) != report:
            raise ValueError("v14_existing_report_requires_audit")
    else:
        save(folder / "comparison.json", report)
    state.update(sealed=True, comparison_file_sha256=file_hash(folder / "comparison.json"))
    save(folder / "checkpoint.json", state)
    return report


def dispose_new_images(folder, plan, state):
    if not state["sealed"]:
        raise ValueError("v14_report_required_before_cleanup")
    journal = folder / "disposal.json"
    if journal.exists():
        body = json.loads(journal.read_bytes())
        if body["plan_sha256"] != plan["plan_sha256"]:
            raise ValueError("v14_cleanup_journal_changed")
    else:
        rows = {r["sample_id"]: r for r in plan["base"]["rows"]}
        paths = sorted((folder / "images").glob("*.png"))
        if any(
            p.stem not in plan["base"]["phase2_ids"] or file_hash(p) != rows[p.stem]["sheet_sha256"]
            for p in paths
        ):
            raise ValueError("v14_unexpected_new_image_requires_audit")
        body = {
            "plan_sha256": plan["plan_sha256"],
            "images": {p.name: file_hash(p) for p in paths},
            "removed": [],
            "completed": False,
        }
        save(journal, body)
    rows = {r["sample_id"]: r for r in plan["base"]["rows"]}
    acquired = {e["sample_id"] for e in state["operations"] if e["kind"] == "acquisition"}
    allowed = {
        n + ".png": rows[n]["sheet_sha256"] for n in plan["base"]["phase2_ids"] if n in acquired
    }
    if (
        any(n not in allowed or h != allowed[n] for n, h in body["images"].items())
        or not set(body["removed"]) <= set(body["images"])
        or len(body["removed"]) != len(set(body["removed"]))
        or any(
            p.is_symlink() or p.name not in body["images"] for p in (folder / "images").glob("*")
        )
    ):
        raise ValueError("v14_cleanup_scope_changed")
    for name, expected in body["images"].items():
        path = folder / "images" / name
        if path.exists():
            if file_hash(path) != expected:
                raise ValueError("v14_cleanup_image_changed")
            path.unlink()
        if name not in body["removed"]:
            body["removed"].append(name)
            save(journal, body)
    body["completed"] = True
    save(journal, body)
    return body


def one(folder, plan, state, kind, sample, root, *, invoker, downloader, clock=time.monotonic):
    entry = {
        "kind": kind,
        "sample_id": sample,
        "status": "running",
        "call_count": 0,
        "seconds": 0.0,
        "unmeasured_reserved_seconds": 0.0,
    }
    state["operations"].append(entry)
    if kind == "acquisition":
        state["acquisitions_reserved"] += 1
    started = clock()

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

    call_deadline = None

    def reserve(index):
        nonlocal call_deadline
        if configuration() != plan["configuration"]:
            raise ValueError("v14_sources_changed_before_dispatch")
        maximum = 1 if kind == "control" else 4
        if (
            index != entry["call_count"] + 1
            or index > maximum
            or state["calls_reserved"] >= CALL_LIMIT
        ):
            raise ValueError("v14_call_budget_exhausted")
        if remaining() <= 5:
            raise TimeoutError("v14_session_budget_exhausted")
        call_deadline = min(180, remaining() - 5)
        entry["call_count"] += 1
        state["calls_reserved"] += 1
        reserve_record(
            folder,
            "native",
            state["calls_reserved"],
            {
                "plan_sha256": plan["plan_sha256"],
                "operation": len(state["operations"]),
                "kind": kind,
                "sample_id": sample,
                "frame": index,
                "number": state["calls_reserved"],
            },
        )
        persist(call_deadline)

    def bounded(*args, **kwargs):
        try:
            with deadline(min(call_deadline, remaining() - 5)):
                return invoker(*args, **kwargs)
        finally:
            persist()

    persist()
    try:
        if kind == "acquisition":
            reserve_record(
                folder,
                "acquisition",
                state["acquisitions_reserved"],
                {
                    "plan_sha256": plan["plan_sha256"],
                    "operation": len(state["operations"]),
                    "kind": kind,
                    "sample_id": sample,
                    "number": state["acquisitions_reserved"],
                },
            )
            if remaining() <= 5:
                raise TimeoutError("v14_session_budget_exhausted")
            allocation = min(180, remaining() - 5)
            persist(allocation)
            row = next(r for r in plan["base"]["rows"] if r["sample_id"] == sample)
            expected = plan["base"]["inputs"][sample]

            def measure(media, work):
                result = acquire_row(media, work, row, folder / "images" / f"{sample}.png")
                if (
                    result["input_png_sha256"] != expected["png_sha256"]
                    or result["input_frame_seconds"] != expected["seconds"]
                ):
                    raise ValueError("v14_acquired_pixels_or_times_changed")
                return result

            with deadline(allocation):
                result = run_session(
                    folder / "sessions" / sample,
                    root / "data/private/media-temp",
                    measure,
                    lambda media: downloader(media, sample),
                    source={"sample_id": sample, "purpose": "v14_fixed_revealed_panel"},
                    model_manifest={"vlm_called": False},
                )
            if result["temporary_directory_removed"] is not True:
                raise ValueError("v14_acquisition_cleanup_unconfirmed")
        else:
            expected = plan["base"]["inputs"][sample]
            scratch = root / "data/private/media-temp"
            scratch.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="galaxies-inference-v14-", dir=scratch) as name:
                work = Path(name)
                if kind == "control":
                    row = next(r for r in controls() if r["sample_id"] == sample)
                    cell = work / "control.png"
                    render_control(row, cell)
                    cells, seconds = [cell], expected["seconds"]
                else:
                    row = next(r for r in plan["base"]["rows"] if r["sample_id"] == sample)
                    sheet = (
                        root / plan["base"]["preserved_folder"] / "images" / f"{sample}.png"
                        if kind == "preserved"
                        else folder / "images" / f"{sample}.png"
                    )
                    cells, seconds = crops(sheet, work, row)
                if [file_hash(c) for c in cells] != expected["png_sha256"] or seconds != expected[
                    "seconds"
                ]:
                    raise ValueError("v14_original_pixels_or_times_changed")
                path = result_path(folder, kind, sample)
                result = extract(
                    cells,
                    seconds,
                    work,
                    evidence_dir=path.parent / "calls",
                    reserve=reserve,
                    invoker=bounded,
                )
                save(path, {"sample_id": sample, "plan_sha256": plan["plan_sha256"], "vlm": result})
                checked_result(folder, plan, entry)
        entry["status"] = "completed"
    except BaseException as error:
        entry.update(status="failed", error_type=type(error).__name__)
        state["halt_reason"] = "v14_operation_failed_" + type(error).__name__
        raise
    finally:
        entry["files_sha256"] = files_for(folder, entry)
        persist()


def execute(parent, cohort, folder, root, *, invoker=invoke_local_vlm, downloader=None):
    folder = private_path(folder, root)
    plan, _ = load(parent, cohort, folder, root)
    with ExitStack() as stack:
        for relative in plan["base"]["ancestor_folders"]:
            stack.enter_context(lock(private_path(root / relative, root) / ".lock"))
        stack.enter_context(lock(folder / ".lock"))
        plan, state = load(parent, cohort, folder, root)
        runnable(state)
        no_workers(root)
        verify_runtime()
        if downloader is None:
            from scripts.vlm_product_recovery_network import download_video

            downloader = download_video
        error = None
        try:
            for kind, sample in sequence(plan)[len(state["operations"]) :]:
                runnable(state)
                if kind == "preserved" and not phase_passed(folder, plan, state, "control", 12):
                    state["halt_reason"] = "v14_controls_quality_failed"
                    break
                if kind == "acquisition" and not phase_passed(folder, plan, state, "preserved", 8):
                    state["halt_reason"] = "v14_preserved_quality_failed"
                    break
                if kind == "acquisition":
                    reviews = check_reviews(folder, plan, state)
                    if "phase1" not in reviews:
                        return {"status": "v14_awaiting_cue_review", "phase": "phase1"}
                    if not reviews["phase1"]:
                        state["halt_reason"] = "v14_phase1_cue_quality_failed"
                        break
                load(parent, cohort, folder, root)
                one(folder, plan, state, kind, sample, root, invoker=invoker, downloader=downloader)
                print(
                    json.dumps(
                        {
                            "stage": kind,
                            "completed_operations": len(state["operations"]),
                            "calls_reserved": state["calls_reserved"],
                            "acquisitions_reserved": state["acquisitions_reserved"],
                            "new_session_seconds": state["new_session_seconds"],
                        }
                    ),
                    flush=True,
                )
        except BaseException as caught:  # noqa: BLE001 - preserve consumption before rethrow
            error = caught
            state["halt_reason"] = (
                state["halt_reason"] or "v14_execution_failed_" + type(caught).__name__
            )
        if not state["halt_reason"] and len(state["operations"]) == len(sequence(plan)):
            reviews = check_reviews(folder, plan, state)
            if "phase2" not in reviews:
                return {"status": "v14_awaiting_cue_review", "phase": "phase2"}
            if not reviews["phase2"]:
                state["halt_reason"] = "v14_phase2_cue_quality_failed"
        save(folder / "checkpoint.json", state)
        report = seal(folder, plan, state, root)
        dispose_new_images(folder, plan, state)
        if error is not None:
            raise error
        return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("prepare", "execute", "inspect", "cleanup", "review"))
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--cohort-dir", type=Path, required=True)
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--review-file", type=Path)
    parser.add_argument("--phase", choices=("phase1", "phase2"))
    args = parser.parse_args()
    root = Path.cwd()
    try:
        folder = private_path(args.folder, root)
        with reserved_guard(args.parent, root), reserved_guard(args.cohort_dir, root):
            if args.operation == "prepare":
                with lock(folder / ".lock"):
                    output = {
                        "plan_sha256": prepare(args.parent, args.cohort_dir, folder, root)[
                            "plan_sha256"
                        ]
                    }
            elif args.operation == "execute":
                report = execute(args.parent, args.cohort_dir, folder, root)
                output = (
                    report
                    if report.get("status") == "v14_awaiting_cue_review"
                    else {
                        k: report[k]
                        for k in (
                            "comparison_sha256",
                            "evaluated_cases",
                            "controls_correct",
                            "control_comparison",
                            "phase1_passed",
                            "stop_reason",
                            "new_calls_reserved",
                            "new_acquisitions_reserved",
                            "panel_descriptive_readiness",
                            "released_fields",
                        )
                    }
                )
            else:
                with lock(folder / ".lock"):
                    plan, state = load(args.parent, args.cohort_dir, folder, root)
                    if args.operation == "review":
                        if args.review_file is None or args.phase is None:
                            raise ValueError("v14_review_file_and_phase_required")
                        submit_review(
                            folder,
                            plan,
                            state,
                            args.phase,
                            json.loads(args.review_file.read_bytes()),
                        )
                        output = {"cue_reviews": check_reviews(folder, plan, state)}
                    else:
                        output = (
                            dispose_new_images(folder, plan, state)
                            if args.operation == "cleanup"
                            else {
                                k: state[k]
                                for k in (
                                    "calls_reserved",
                                    "acquisitions_reserved",
                                    "new_session_seconds",
                                    "halt_reason",
                                    "sealed",
                                )
                            }
                        )
        print(json.dumps(output), flush=True)
    except Exception as error:  # noqa: BLE001 - static error type only, no raw input
        print(json.dumps({"status": "v14_stopped", "error_type": type(error).__name__}), flush=True)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()

"""Guarded V9 product controls, revealed pilot and paired development comparison."""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from collections import Counter
from pathlib import Path

from scripts.expansion_media import deadline
from scripts.experiment_b_vlm_extract import session_with_dns_recovery
from scripts.experiment_b_vlm_network import download_video
from scripts.experiment_b_vlm_quality import evaluate_gate, validate_fields
from scripts.gguf_visual_attributes import invoke_local_vlm
from scripts.prepare_gguf_vlm import prepare as prepare_runtime
from scripts.private_checkpoint import digest, file_hash, lock, private_path, save
from scripts.retrain_expansion import reserved_guard
from scripts.vlm_explicit_presence import verify as verify_cached
from scripts.vlm_per_frame import BOOLEAN_FIELDS, aggregate
from scripts.vlm_per_frame import verify as verify_legacy
from scripts.vlm_product_plan import (
    ACQUISITION_LIMIT,
    BASE_ACQUISITIONS,
    CALL_LIMIT,
    LEGACY,
    PREVIOUS,
    TIME_LIMIT,
    annotations,
    controls,
    load,
    persist,
    prepare,
    result_path,
    runnable,
)
from scripts.vlm_product_states import FIELD, VARIANTS, extract, verify
from scripts.vlm_prompt_development import metrics, render_control
from scripts.vlm_revision import acquire_row, clean_workspace, crops, seconds_for


def cached_result(root, row, candidate=None, control=False):
    if candidate:
        path = root / LEGACY / "inferences" / candidate / row["sample_id"] / "result.json"
    else:
        path = (
            root
            / PREVIOUS
            / ("control-results" if control else "inferences")
            / row["sample_id"]
            / "result.json"
        )
    body = json.loads(path.read_bytes())
    if body["sample_id"] != row["sample_id"] or (
        not control and body["sheet_sha256"] != row["sheet_sha256"]
    ):
        raise ValueError("product_cached_identity_changed")
    (verify_legacy if candidate else verify_cached)(body["vlm"], path.parent / "calls")
    if not control and body["vlm"]["input_frame_seconds"] != seconds_for(row):
        raise ValueError("product_cached_times_changed")
    return body["vlm"]


def checked_identity(folder, row, root):
    current = json.loads((folder / "sessions" / row["sample_id"] / "features.json").read_bytes())
    previous = json.loads(
        (root / PREVIOUS / "sessions" / row["sample_id"] / "features.json").read_bytes()
    )
    run = json.loads((folder / "sessions" / row["sample_id"] / "run.json").read_bytes())
    if (
        current["sample_id"] != row["sample_id"]
        or current["properties"] != row["properties"]
        or current["sheet_sha256"] != row["sheet_sha256"]
        or current["input_frame_seconds"] != seconds_for(row)
        or current["input_png_sha256"] != previous["input_png_sha256"]
        or run["status"] != "completed"
        or run["temporary_directory_removed"] is not True
    ):
        raise ValueError("product_original_pixels_or_times_changed")
    return current


def checked_result(folder, plan, row, root, *, variant="structured", control=False):
    path = result_path(folder, row["sample_id"], variant, control)
    body = json.loads(path.read_bytes())
    previous = cached_result(root, row, control=control)
    if (
        body["sample_id"] != row["sample_id"]
        or body["plan_sha256"] != plan["plan_sha256"]
        or body["config_sha256"] != digest(plan["config"])
        or body["vlm"]["variant"] != variant
        or body["vlm"]["input_png_sha256"] != previous["input_png_sha256"]
        or body["vlm"]["input_frame_seconds"] != previous["input_frame_seconds"]
    ):
        raise ValueError("product_result_inputs_changed")
    if not control:
        identity = checked_identity(folder, row, root)
        if (
            body["sheet_sha256"] != row["sheet_sha256"]
            or identity["input_png_sha256"] != body["vlm"]["input_png_sha256"]
        ):
            raise ValueError("product_result_inputs_changed")
    verify(body["vlm"], path.parent / "calls")
    return body["vlm"]


def _one(folder, plan, state, row, root, *, variant, control, invoker):
    path = result_path(folder, row["sample_id"], variant, control)
    if path.parent.exists():
        raise ValueError("product_interrupted_output_requires_audit")
    entry = {
        "sample_id": row["sample_id"],
        "variant": variant,
        "status": "running",
        "call_count": 0,
    }
    state["controls" if control else "inferences"].append(entry)
    started = time.monotonic()
    checkpoint = lambda: persist(folder, state, entry, started, time.monotonic)
    checkpoint()

    def counted(*args, **kwargs):
        if state["calls_reserved"] >= CALL_LIMIT:
            raise ValueError("product_native_call_budget_exhausted")
        state["calls_reserved"] += 1
        entry["call_count"] += 1
        checkpoint()
        return invoker(*args, **kwargs)

    try:
        with deadline(TIME_LIMIT - state["elapsed_seconds"]):
            scratch = root / "data/private/media-temp"
            scratch.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(
                prefix="galaxies-inference-v9-", dir=scratch
            ) as temporary:
                work = Path(temporary)
                previous = cached_result(root, row, control=control)
                if control:
                    cell = work / "control.png"
                    render_control(row, cell)
                    cells, seconds = [cell], previous["input_frame_seconds"]
                else:
                    checked_identity(folder, row, root)
                    cells, seconds = crops(
                        folder / "images" / (row["sample_id"] + ".png"), work, row
                    )
                if [file_hash(c) for c in cells] != previous[
                    "input_png_sha256"
                ] or seconds != previous["input_frame_seconds"]:
                    raise ValueError("product_original_pixels_or_times_changed")
                result = extract(
                    cells,
                    seconds,
                    work,
                    variant=variant,
                    evidence_dir=path.parent / "calls",
                    invoker=counted,
                )
            body = {
                "sample_id": row["sample_id"],
                "plan_sha256": plan["plan_sha256"],
                "config_sha256": digest(plan["config"]),
                "vlm": result,
            }
            if not control:
                body["sheet_sha256"] = row["sheet_sha256"]
            save(path, body)
            checked_result(folder, plan, row, root, variant=variant, control=control)
            entry.update(status="completed", result_sha256=file_hash(path))
    except BaseException as exc:
        entry.update(status="failed", reason=type(exc).__name__)
        state["halt_reason"] = str(exc)
        raise
    finally:
        checkpoint()


def control_summary(folder, plan, state, root):
    counts = {v: Counter() for v in VARIANTS}
    for e in state["controls"]:
        if e["status"] != "completed":
            continue
        row = next(r for r in controls() if r["sample_id"] == e["sample_id"])
        body = checked_result(folder, plan, row, root, variant=e["variant"], control=True)
        value = body["parsed"][FIELD]["value"]
        counts[e["variant"]][str(value).lower()] += 1
        counts[e["variant"]]["correct"] += value is False
    return {v: dict(c) for v, c in counts.items()}


def require_controls(folder, plan, state, root):
    if len(state["controls"]) != 48 or any(e["status"] != "completed" for e in state["controls"]):
        raise ValueError("product_complete_controls_required")
    scores = control_summary(folder, plan, state, root)
    if scores["structured"].get("correct") != 12:
        raise ValueError("product_controls_absence_failed")
    return scores


def run_controls(parent, cohort, folder, root, *, limit, invoker=invoke_local_vlm):
    if not 1 <= limit <= 48:
        raise ValueError("product_invalid_batch_size")
    with lock(folder / ".lock"):
        plan, state = load(parent, cohort, folder, root)
        runnable(state)
        clean_workspace(root)
        prepare_runtime(offline=True)
        done = {(e["variant"], e["sample_id"]) for e in state["controls"]}
        used = 0
        for variant in VARIANTS:
            for row in controls():
                if (variant, row["sample_id"]) in done or used >= limit:
                    continue
                _one(folder, plan, state, row, root, variant=variant, control=True, invoker=invoker)
                used += 1
                print(
                    json.dumps(
                        {
                            "stage": "product_controls",
                            "completed": len(state["controls"]),
                            "calls_reserved": state["calls_reserved"],
                        }
                    ),
                    flush=True,
                )
        if len(state["controls"]) == 48:
            scores = control_summary(folder, plan, state, root)
            proof = {
                "plan_sha256": plan["plan_sha256"],
                "scores": scores,
                "real_inputs_allowed": scores["structured"].get("correct") == 12,
                "variants_selected_by_controls": False,
            }
            path = folder / "control-comparison.json"
            if path.exists() and json.loads(path.read_bytes()) != proof:
                raise ValueError("product_control_comparison_changed")
            save(path, proof)
            state["control_comparison_sha256"] = file_hash(path)
            if not proof["real_inputs_allowed"]:
                state["halt_reason"] = "product_controls_absence_failed"
            save(folder / "checkpoint.json", state)
    return state


def combined_observation(folder, plan, row, root):
    previous = cached_result(root, row)
    current = checked_result(folder, plan, row, root)
    frames = [
        a | {FIELD: b[FIELD]}
        for a, b in zip(previous["per_frame"], current["per_frame"], strict=True)
    ]
    prediction = aggregate(frames, current["input_frame_seconds"])
    if any(prediction[f] != previous["parsed"][f] for f in BOOLEAN_FIELDS if f != FIELD):
        raise ValueError("product_person_text_cache_changed")
    return prediction, frames


def pilot_summary(folder, plan, state, root):
    complete = {e["sample_id"] for e in state["inferences"] if e["status"] == "completed"}
    if not set(plan["pilot_ids"]) <= complete:
        return None
    truth = annotations(plan, root)
    support, correct = Counter(), Counter()
    for row in plan["rows"]:
        if row["sample_id"] not in plan["pilot_ids"]:
            continue
        a = truth[row["sample_id"]][FIELD]
        p = checked_result(folder, plan, row, root)["parsed"][FIELD]
        key = row["sector"] + "/" + str(a["value"]).lower()
        support[key] += 1
        correct[key] += (
            p["value"] == a["value"] and bool(p["frames"]) and set(p["frames"]) <= set(a["frames"])
        )
    return {
        "support": dict(support),
        "correct_value_and_evidence": dict(correct),
        "continue": all(
            correct[s + "/" + v] >= 1 for s in ("beleza", "moda") for v in ("true", "false")
        ),
        "independent_validation": False,
    }


def evaluation_rows(plan, allow_remaining):
    by_id = {r["sample_id"]: r for r in plan["rows"]}
    result = [by_id[s] for s in plan["pilot_ids"]]
    if allow_remaining:
        result += [r for r in plan["rows"] if r["sample_id"] not in plan["pilot_ids"]]
    return result


def acquire(parent, cohort, folder, root, *, limit, downloader=None):
    if not 1 <= limit <= 64:
        raise ValueError("product_invalid_batch_size")
    with lock(folder / ".lock"):
        plan, state = load(parent, cohort, folder, root)
        runnable(state)
        clean_workspace(root)
        require_controls(folder, plan, state, root)
        pilot = pilot_summary(folder, plan, state, root)
        if pilot and not pilot["continue"]:
            raise ValueError("product_pilot_failed")
        if downloader is None:
            import imageio_ffmpeg

            ffmpeg = Path(imageio_ffmpeg.get_ffmpeg_exe())
            downloader = lambda media, sample: download_video(media, sample, ffmpeg)
        done = {e["sample_id"] for e in state["entries"]}
        used = 0
        for row in evaluation_rows(plan, bool(pilot and pilot["continue"])):
            if row["sample_id"] in done or used >= limit:
                continue
            if (
                BASE_ACQUISITIONS + sum(len(e["attempts"]) for e in state["entries"])
                >= ACQUISITION_LIMIT
            ):
                raise ValueError("product_acquisition_budget_exhausted")
            destination = folder / "sessions" / row["sample_id"]
            if destination.exists():
                raise ValueError("product_interrupted_acquisition_requires_audit")
            entry = {
                "sample_id": row["sample_id"],
                "status": "running",
                "attempts": [{"status": "running"}],
            }
            state["entries"].append(entry)
            started = time.monotonic()
            checkpoint = lambda entry=entry, started=started: persist(
                folder, state, entry, started, time.monotonic
            )
            checkpoint()
            try:
                with deadline(TIME_LIMIT - state["elapsed_seconds"]):
                    result = session_with_dns_recovery(
                        destination,
                        root / "data/private/media-temp",
                        lambda media, scratch, current=row: acquire_row(
                            media,
                            scratch,
                            current,
                            folder / "images" / (current["sample_id"] + ".png"),
                        ),
                        lambda media, sample=row["sample_id"]: downloader(media, sample),
                        source={
                            "sample_id": row["sample_id"],
                            "purpose": "product_v9_identity_only",
                        },
                        model={"vlm_called": False},
                        entry=entry,
                        state=state,
                        folder=folder,
                        persist=checkpoint,
                    )
                if result["temporary_directory_removed"] is not True:
                    raise ValueError("product_cleanup_unconfirmed")
                checked_identity(folder, row, root)
                entry.update(
                    status="completed",
                    files_sha256={
                        n: file_hash(destination / n) for n in ("features.json", "run.json")
                    },
                )
            except BaseException as exc:
                entry.update(status="failed", reason=type(exc).__name__)
                entry["attempts"][-1]["status"] = "failed"
                entry["attempts"][-1].setdefault("seconds", 0.0)
                state["halt_reason"] = str(exc)
                raise
            finally:
                record = destination / "run.json"
                if record.is_file():
                    entry["attempts"][-1]["run_sha256"] = file_hash(record)
                else:
                    entry["attempts"][-1]["run_receipt_missing"] = True
                checkpoint()
            used += 1
            print(
                json.dumps({"stage": "product_acquisition", "completed": len(state["entries"])}),
                flush=True,
            )
    return state


def infer(parent, cohort, folder, root, *, limit, invoker=invoke_local_vlm):
    if not 1 <= limit <= 64:
        raise ValueError("product_invalid_batch_size")
    with lock(folder / ".lock"):
        plan, state = load(parent, cohort, folder, root)
        runnable(state)
        clean_workspace(root)
        require_controls(folder, plan, state, root)
        prepare_runtime(offline=True)
        done = {e["sample_id"] for e in state["inferences"]}
        acquired = {e["sample_id"] for e in state["entries"] if e["status"] == "completed"}
        used = 0
        for row in evaluation_rows(plan, True):
            if row["sample_id"] in done or used >= limit:
                continue
            if row["sample_id"] not in plan["pilot_ids"]:
                pilot = pilot_summary(folder, plan, state, root)
                if not pilot or not pilot["continue"]:
                    break
            if row["sample_id"] not in acquired:
                break
            _one(
                folder, plan, state, row, root, variant="structured", control=False, invoker=invoker
            )
            used += 1
            print(
                json.dumps(
                    {
                        "stage": "product_inference",
                        "completed": len(state["inferences"]),
                        "calls_reserved": state["calls_reserved"],
                    }
                ),
                flush=True,
            )
        pilot = pilot_summary(folder, plan, state, root)
        if pilot:
            path = folder / "pilot-comparison.json"
            if path.exists() and json.loads(path.read_bytes()) != pilot:
                raise ValueError("product_pilot_comparison_changed")
            save(path, pilot)
            state["pilot_comparison_sha256"] = file_hash(path)
            if not pilot["continue"]:
                state["halt_reason"] = "product_pilot_failed"
            save(folder / "checkpoint.json", state)
    return state


def compare(parent, cohort, folder, root):
    with lock(folder / ".lock"):
        plan, state = load(parent, cohort, folder, root)
        if state["halt_reason"] == "product_report_sealed":
            return json.loads((folder / "comparison.json").read_bytes())
        if any(
            e["status"] == "running"
            for e in [*state["entries"], *state["controls"], *state["inferences"]]
        ):
            raise ValueError("product_interrupted_requires_audit")
        clean_workspace(root)
        completed = {e["sample_id"] for e in state["inferences"] if e["status"] == "completed"}
        if not state["halt_reason"] and len(completed) != 64:
            raise ValueError("product_complete_64_or_recorded_stop_required")
        truth = annotations(plan, root)
        observations = {v: [] for v in ("v9", "v8", "v7_A", "v7_B_old32")}
        hashes = {}
        for row in plan["rows"]:
            if row["sample_id"] not in completed:
                continue
            validate_fields(truth[row["sample_id"]], seconds_for(row))
            predicted, frames = combined_observation(folder, plan, row, root)
            base = {
                "sample_id": row["sample_id"],
                "origin": row["group"],
                "sector": row["sector"],
                "annotated": truth[row["sample_id"]],
            }
            observations["v9"].append(base | {"predicted": predicted, "per_frame": frames})
            current = checked_result(folder, plan, row, root)
            for version, candidate in (("v8", None), ("v7_A", "A"), ("v7_B_old32", "B")):
                if candidate == "B" and row["group"] != "development":
                    continue
                cached = cached_result(root, row, candidate)
                if (
                    cached["input_png_sha256"] != current["input_png_sha256"]
                    or cached["input_frame_seconds"] != current["input_frame_seconds"]
                ):
                    raise ValueError("product_comparison_inputs_changed")
                observations[version].append(
                    base | {"predicted": cached["parsed"], "per_frame": cached["per_frame"]}
                )
            hashes[row["sample_id"]] = file_hash(result_path(folder, row["sample_id"]))
        scores, gates = {}, {}
        for version, rows in observations.items():
            scores[version] = {"all_available": metrics(rows)}
            for group in ("development", "audit", "pilot", "remaining"):
                part = [
                    r
                    for r in rows
                    if (
                        r["origin"] == group
                        if group in ("development", "audit")
                        else (r["sample_id"] in plan["pilot_ids"]) == (group == "pilot")
                    )
                ]
                scores[version][group] = metrics(part)
            gates[version] = {}
            if len(completed) == 64:
                for group in ("development", "audit"):
                    part = [r for r in rows if r["origin"] == group]
                    if len(part) == 32:
                        gates[version][group] = evaluate_gate(part)
        ready = (
            [FIELD]
            if len(completed) == 64
            and all(FIELD in gates["v9"][g]["released_fields"] for g in ("development", "audit"))
            else []
        )
        proof = {
            "status": "product_development_report",
            "plan_sha256": plan["plan_sha256"],
            "stop_reason": state["halt_reason"] or "completed_64",
            "evaluated_cases": len(completed),
            "acquired_cases": len([e for e in state["entries"] if e["status"] == "completed"]),
            "controls": control_summary(folder, plan, state, root),
            "pilot": pilot_summary(folder, plan, state, root),
            "metrics": scores,
            "original_gate_by_origin": gates,
            "fields_ready_for_future_blind_audit": ready,
            "released_fields": [],
            "same_pixels_and_times": True,
            "person_text_cache_preserved": True,
            "new_blind_audit": False,
            "predictive_training_started": False,
            "test_evaluated": False,
            "m1_replaced": False,
            "result_sha256": hashes,
            "native_receipt_sha256": {
                str(p.relative_to(folder)): file_hash(p)
                for area in ("control-results", "inferences")
                for p in sorted((folder / area).glob("*/**/calls/*.json"))
            },
        }
        proof["comparison_sha256"] = digest(proof)
        path = folder / "comparison.json"
        if path.exists() and json.loads(path.read_bytes()) != proof:
            raise ValueError("product_interrupted_comparison_changed")
        save(path, proof)
        state["comparison_file_sha256"] = file_hash(path)
        state["halt_reason"] = "product_report_sealed"
        save(folder / "checkpoint.json", state)
        return proof


def dispose(parent, cohort, folder, root):
    with lock(folder / ".lock"):
        plan, state = load(parent, cohort, folder, root)
        if state["halt_reason"] != "product_report_sealed":
            raise ValueError("product_sealed_report_required")
        images = {
            e["sample_id"]: next(
                r["sheet_sha256"] for r in plan["rows"] if r["sample_id"] == e["sample_id"]
            )
            for e in state["entries"]
            if e["status"] == "completed"
            or (folder / "images" / (e["sample_id"] + ".png")).exists()
        }
        if "cleanup_pending" in state:
            images = json.loads((folder / "image-disposal.json").read_bytes())["images"]
        if state["images_disposed"]:
            return {"images_removed": len(images), "temporary_media_retained": False}
        if "cleanup_pending" not in state:
            for sample, sha in images.items():
                if file_hash(folder / "images" / (sample + ".png")) != sha:
                    raise ValueError("product_disposal_image_changed")
            receipt = {
                "images": images,
                "plan_sha256": plan["plan_sha256"],
                "comparison_file_sha256": state["comparison_file_sha256"],
            }
            path = folder / "image-disposal.json"
            if path.exists() and json.loads(path.read_bytes()) != receipt:
                raise ValueError("product_disposal_evidence_changed")
            save(path, receipt)
            state.update(cleanup_pending=list(images), disposal_sha256=file_hash(path))
            save(folder / "checkpoint.json", state)
        for sample in list(state["cleanup_pending"]):
            path = folder / "images" / (sample + ".png")
            if path.exists() and file_hash(path) != images[sample]:
                raise ValueError("product_disposal_image_changed")
            path.unlink(missing_ok=True)
            state["cleanup_pending"].remove(sample)
            save(folder / "checkpoint.json", state)
        if list((folder / "images").glob("*.png")):
            raise ValueError("product_unexpected_images_require_audit")
        state["images_disposed"] = True
        save(folder / "checkpoint.json", state)
        return {"images_removed": len(images), "temporary_media_retained": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation",
        choices=("prepare", "controls", "acquire", "infer", "compare", "dispose", "inspect"),
    )
    parser.add_argument("--parent", required=True, type=Path)
    parser.add_argument("--cohort-dir", required=True, type=Path)
    parser.add_argument("--folder", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=1)
    args = parser.parse_args()
    root = Path.cwd()
    folder = private_path(args.folder, root)
    with reserved_guard(args.parent, root):
        common = (args.parent, args.cohort_dir, folder, root)
        if args.operation == "prepare":
            report = {"plan_sha256": prepare(*common)["plan_sha256"], "revealed_cases": 64}
        elif args.operation in ("controls", "acquire", "infer"):
            state = {"controls": run_controls, "acquire": acquire, "infer": infer}[args.operation](
                *common, limit=args.limit
            )
            report = {
                "calls_reserved": state["calls_reserved"],
                "acquisitions": len(state["entries"]),
                "halt_reason": state["halt_reason"],
            }
        elif args.operation == "compare":
            proof = compare(*common)
            report = {
                k: proof[k]
                for k in ("comparison_sha256", "evaluated_cases", "stop_reason", "released_fields")
            }
        elif args.operation == "dispose":
            report = dispose(*common)
        else:
            _, state = load(*common)
            report = {
                "acquisitions": len(state["entries"]),
                "controls": len(state["controls"]),
                "inferences": len(state["inferences"]),
                "calls_reserved": state["calls_reserved"],
                "halt_reason": state["halt_reason"],
            }
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()

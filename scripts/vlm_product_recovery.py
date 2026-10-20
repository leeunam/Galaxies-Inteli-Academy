"""Execute only explicitly authorized V9 missing work in a separate queue."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import time
from functools import partial
from pathlib import Path

from scripts.expansion_media import deadline
from scripts.gguf_visual_attributes import invoke_local_vlm, model_manifest
from scripts.pilot_licensed_media import run_session
from scripts.prepare_gguf_vlm import prepare as prepare_runtime
from scripts.private_checkpoint import digest, file_hash, lock, private_path, save
from scripts.retrain_expansion import reserved_guard
from scripts.vlm_per_frame import BOOLEAN_FIELDS, aggregate
from scripts.vlm_product_development import cached_result, checked_identity
from scripts.vlm_product_recovery_plan import (
    ACQUISITION_LIMIT,
    CALL_LIMIT,
    TIME_LIMIT,
    checked_result,
    load,
    persist,
    prepare,
    result_path,
    runnable,
)
from scripts.vlm_product_states import FIELD, VERSION, decode, extract, specification, verify
from scripts.vlm_revision import acquire_row, clean_workspace, crops


class UnreservedBudgetStop(ValueError):
    """A receipt header exists, but no native operation was reserved or run."""


def recover_partial(cells, seconds, work, *, sealed_calls, evidence_dir, invoker):
    """Three byte-exact inherited receipts plus one new, separately reserved call."""
    spec = specification("structured")
    evidence_dir.mkdir(parents=True, mode=0o700, exist_ok=False)
    for index in (1, 2, 3):
        src, dst = sealed_calls / f"frame-{index}.json", evidence_dir / f"frame-{index}.json"
        with dst.open("xb") as output:
            dst.chmod(0o600)
            output.write(src.read_bytes())
    hashes = [file_hash(c) for c in cells]
    lost = json.loads((sealed_calls / "frame-4.json").read_bytes())
    if lost["input_png_sha256"] != hashes[3] or "raw_response" in lost:
        raise ValueError("recovery_missing_frame_identity_changed")
    path = evidence_dir / "frame-4.json"
    call = {
        "schema_version": VERSION,
        "variant": "structured",
        "frame": 4,
        "input_png_sha256": hashes[3],
        "specification_sha256": digest(spec),
        "recovery_of_sealed_reservation_sha256": file_hash(sealed_calls / "frame-4.json"),
        "status": "running",
    }
    save(path, call)
    try:
        output = invoker(
            [cells[3]], spec["prompt"], work, spec["schema"], max_tokens=spec["max_tokens"]
        )
        call.update(output, status="response_captured")
        save(path, call)
        if type(output.get("raw_response")) is not str:
            raise ValueError("invalid_product_native_raw_type")
        call["raw_response_sha256"] = hashlib.sha256(output["raw_response"].encode()).hexdigest()
        save(path, call)
        parsed, _ = decode(output["raw_response"], "structured")
        call.update(parsed=parsed, status="completed")
        save(path, call)
    except BaseException as exc:
        call.update(status="failed", error_type=type(exc).__name__)
        save(path, call)
        raise
    if hashes != [file_hash(c) for c in cells]:
        raise ValueError("recovery_pixels_changed_during_call")
    intermediate, frames, calls = [], [], []
    for i in (1, 2, 3, 4):
        path = evidence_dir / f"frame-{i}.json"
        body = json.loads(path.read_bytes())
        parsed, value = decode(body["raw_response"], "structured")
        intermediate.append(parsed)
        frames.append({f: value if f == FIELD else "unknown" for f in BOOLEAN_FIELDS})
        calls.append({"path": path.name, "sha256": file_hash(path)})
    result = {
        "schema_version": VERSION,
        "variant": "structured",
        "model": model_manifest(),
        "specification_sha256": digest(spec),
        "input_png_sha256": hashes,
        "input_frame_seconds": seconds,
        "intermediate": intermediate,
        "per_frame": frames,
        "parsed": aggregate(frames, seconds),
        "calls": calls,
        "approved_for_training": False,
    }
    verify(result, evidence_dir)
    return result


def acquire(parent, cohort, folder, root, *, limit, downloader=None):
    if not 1 <= limit <= 31:
        raise ValueError("recovery_invalid_batch")
    plan = json.loads((folder / "plan.json").read_bytes())
    with lock(root / plan["sealed_folder"] / ".lock"), lock(folder / ".lock"):
        plan, state = load(parent, cohort, folder, root)
        runnable(state)
        clean_workspace(root)
        if downloader is None:
            from scripts.vlm_product_recovery_network import download_video

            downloader = download_video
        rows = {r["sample_id"]: r for r in plan["rows"]}
        for sample in plan["pending_ids"][len(state["entries"]) :][:limit]:
            if len(state["entries"]) >= ACQUISITION_LIMIT:
                raise ValueError("recovery_acquisition_budget_exhausted")
            destination = folder / "sessions" / sample
            if destination.exists():
                raise ValueError("recovery_existing_acquisition_requires_audit")
            row = rows[sample]
            entry = {"sample_id": sample, "status": "running", "seconds": 0.0}
            state["entries"].append(entry)
            started = time.monotonic()
            checkpoint = partial(persist, folder, state, entry, started, time.monotonic)
            checkpoint()
            try:
                with deadline(min(180, TIME_LIMIT - state["elapsed_seconds"])):
                    result = run_session(
                        destination,
                        root / "data/private/media-temp",
                        lambda media, work, current=row, key=sample: acquire_row(
                            media, work, current, folder / "images" / (key + ".png")
                        ),
                        lambda media, key=sample: downloader(media, key),
                        source={
                            "sample_id": sample,
                            "purpose": "product_v9_authorized_recovery_identity_only",
                        },
                        model_manifest={"vlm_called": False},
                    )
                    if not result["temporary_directory_removed"]:
                        raise ValueError("recovery_cleanup_unconfirmed")
                    checked_identity(folder, row, root)
                    entry.update(
                        status="completed",
                        files_sha256={
                            n: file_hash(destination / n) for n in ("features.json", "run.json")
                        },
                    )
            except BaseException as exc:
                entry.update(status="failed", reason=type(exc).__name__)
                state["halt_reason"] = "recovery_acquisition_failed_" + type(exc).__name__
                raise
            finally:
                run = destination / "run.json"
                if run.is_file():
                    entry["run_sha256"] = file_hash(run)
                else:
                    entry["run_receipt_missing"] = True
                checkpoint()
            print(
                json.dumps({"stage": "recovery_acquisition", "completed": len(state["entries"])}),
                flush=True,
            )
            if state["elapsed_seconds"] >= TIME_LIMIT:
                state["halt_reason"] = "recovery_time_budget_exhausted"
                save(folder / "checkpoint.json", state)
                break
        return state


def infer(parent, cohort, folder, root, *, limit, invoker=invoke_local_vlm):
    if not 1 <= limit <= 31:
        raise ValueError("recovery_invalid_batch")
    plan = json.loads((folder / "plan.json").read_bytes())
    sealed = root / plan["sealed_folder"]
    with lock(sealed / ".lock"), lock(folder / ".lock"):
        plan, state = load(parent, cohort, folder, root)
        runnable(state)
        clean_workspace(root)
        prepare_runtime(offline=True)
        rows = {r["sample_id"]: r for r in plan["rows"]}
        acquired = {e["sample_id"] for e in state["entries"] if e["status"] == "completed"}
        for sample in plan["pending_ids"][len(state["inferences"]) :][:limit]:
            if sample not in acquired:
                break
            row, path = rows[sample], result_path(folder, sample)
            if path.parent.exists():
                raise ValueError("recovery_existing_inference_requires_audit")
            entry = {"sample_id": sample, "status": "running", "call_count": 0, "seconds": 0.0}
            state["inferences"].append(entry)
            started = time.monotonic()
            checkpoint = partial(persist, folder, state, entry, started, time.monotonic)
            checkpoint()

            def counted(*args, checkpoint=checkpoint, entry=entry, **kwargs):
                checkpoint()
                if state["elapsed_seconds"] >= TIME_LIMIT:
                    raise UnreservedBudgetStop("recovery_time_budget_exhausted")
                expected = 1 if entry["sample_id"] == plan["pending_ids"][0] else 4
                if state["calls_reserved"] >= CALL_LIMIT or entry["call_count"] >= expected:
                    raise UnreservedBudgetStop("recovery_native_call_budget_exhausted")
                state["calls_reserved"] += 1
                entry["call_count"] += 1
                checkpoint()
                with deadline(min(180, TIME_LIMIT - state["elapsed_seconds"])):
                    result = invoker(*args, **kwargs)
                print(
                    json.dumps({"stage": "recovery_call", "reservations": state["calls_reserved"]}),
                    flush=True,
                )
                return result

            try:
                checked_identity(folder, row, root)
                scratch = root / "data/private/media-temp"
                scratch.mkdir(parents=True, exist_ok=True)
                with tempfile.TemporaryDirectory(
                    prefix="galaxies-inference-recovery-", dir=scratch
                ) as name:
                    work = Path(name)
                    cells, seconds = crops(folder / "images" / (sample + ".png"), work, row)
                    cached = cached_result(root, row)
                    if [file_hash(c) for c in cells] != cached[
                        "input_png_sha256"
                    ] or seconds != cached["input_frame_seconds"]:
                        raise ValueError("recovery_original_pixels_or_times_changed")
                    if sample == plan["pending_ids"][0]:
                        result = recover_partial(
                            cells,
                            seconds,
                            work,
                            sealed_calls=sealed / "inferences/structured" / sample / "calls",
                            evidence_dir=path.parent / "calls",
                            invoker=counted,
                        )
                    else:
                        result = extract(
                            cells,
                            seconds,
                            work,
                            variant="structured",
                            evidence_dir=path.parent / "calls",
                            invoker=counted,
                        )
                save(
                    path,
                    {
                        "sample_id": sample,
                        "sheet_sha256": row["sheet_sha256"],
                        "recovery_plan_sha256": plan["plan_sha256"],
                        "sealed_plan_sha256": plan["sealed_plan_sha256"],
                        "config_sha256": plan["old_config_sha256"],
                        "vlm": result,
                    },
                )
                checked_result(folder, plan, row, root)
                entry.update(status="completed", result_sha256=file_hash(path))
            except BaseException as exc:
                entry.update(status="failed", reason=type(exc).__name__)
                state["halt_reason"] = "recovery_inference_failed_" + type(exc).__name__
                raise
            finally:
                checkpoint()
            print(
                json.dumps(
                    {
                        "stage": "recovery_inference",
                        "completed_new": len(state["inferences"]),
                        "completed_total": 33 + len(state["inferences"]),
                    }
                ),
                flush=True,
            )
            if state["elapsed_seconds"] >= TIME_LIMIT:
                state["halt_reason"] = "recovery_time_budget_exhausted"
                save(folder / "checkpoint.json", state)
                break
        return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation", choices=("prepare", "acquire", "infer", "compare", "dispose", "inspect")
    )
    parser.add_argument("--parent", required=True, type=Path)
    parser.add_argument("--cohort-dir", required=True, type=Path)
    parser.add_argument(
        "--sealed-folder",
        type=Path,
        default=Path("data/private/issue-4-vlm-produto-v9-desenvolvimento"),
    )
    parser.add_argument("--folder", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=1)
    args = parser.parse_args()
    root = Path.cwd()
    folder, sealed = private_path(args.folder, root), private_path(args.sealed_folder, root)
    with reserved_guard(args.parent, root):
        common = (args.parent, args.cohort_dir, folder, root)
        if args.operation == "prepare":
            output = {
                "plan_sha256": prepare(args.parent, args.cohort_dir, sealed, folder, root)[
                    "plan_sha256"
                ]
            }
        elif args.operation in ("acquire", "infer"):
            state = {"acquire": acquire, "infer": infer}[args.operation](*common, limit=args.limit)
            output = {
                "new_acquisitions": len(state["entries"]),
                "calls_reserved": state["calls_reserved"],
                "halt_reason": state["halt_reason"],
                "elapsed_seconds": state["elapsed_seconds"],
            }
        elif args.operation in ("compare", "dispose"):
            from scripts.vlm_product_recovery_compare import compare, dispose

            output = {"compare": compare, "dispose": dispose}[args.operation](*common)
            if args.operation == "compare":
                output = {
                    k: output[k]
                    for k in (
                        "comparison_sha256",
                        "evaluated_cases",
                        "stop_reason",
                        "released_fields",
                        "new_native_reservations",
                        "cumulative_native_reservations",
                    )
                }
        else:
            with lock(sealed / ".lock"), lock(folder / ".lock"):
                _, state = load(*common)
            output = {
                k: state[k]
                for k in ("calls_reserved", "elapsed_seconds", "halt_reason", "images_disposed")
            }
            output.update(
                new_acquisitions=len(state["entries"]),
                completed_new=sum(e["status"] == "completed" for e in state["inferences"]),
            )
    print(json.dumps(output), flush=True)


if __name__ == "__main__":
    main()

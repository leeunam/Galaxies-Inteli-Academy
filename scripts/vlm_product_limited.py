"""One authorized diagnostic download, then V9 inference on seven preserved sheets."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tarfile
import tempfile
import time
from functools import partial
from pathlib import Path

import av

from scripts.expansion_media import deadline
from scripts.gguf_visual_attributes import HASHES, MODEL_DIR, RUNTIME, invoke_local_vlm
from scripts.pilot_licensed_media import frames_and_properties, run_session
from scripts.prepare_gguf_vlm import ARCHIVE_SHA256
from scripts.private_checkpoint import file_hash, private_path, save
from scripts.retrain_expansion import reserved_guard
from scripts.vlm_product_development import cached_result, checked_identity
from scripts.vlm_product_limited_plan import (
    TIME_LIMIT,
    checked_result,
    load,
    locks,
    no_workers,
    persist,
    prepare,
    result_path,
    runnable,
)
from scripts.vlm_product_states import extract
from scripts.vlm_revision import crops


def verify_runtime():
    """Verify installed files against the official cached archive without extracting it."""
    cache = RUNTIME.parent.parent
    archive = cache / "runtime.tar.gz"
    if file_hash(archive) != ARCHIVE_SHA256:
        raise ValueError("limited_runtime_archive_changed")
    with tarfile.open(archive) as bundle:
        members = bundle.getmembers()
        if sum(m.size for m in members) > 128 * 1024 * 1024:
            raise ValueError("limited_runtime_archive_size_changed")
        for member in members:
            target = cache / member.name
            if not target.resolve().is_relative_to(cache.resolve()):
                raise ValueError("limited_runtime_path_changed")
            if member.issym():
                if not target.is_symlink() or os.readlink(target) != member.linkname:
                    raise ValueError("limited_runtime_link_changed")
            elif member.isfile():
                with bundle.extractfile(member) as content:
                    expected = hashlib.file_digest(content, "sha256").hexdigest()
                if target.is_symlink() or file_hash(target) != expected:
                    raise ValueError("limited_installed_runtime_changed")
            elif not member.isdir() or not target.is_dir():
                raise ValueError("limited_runtime_member_changed")
    for name, expected in HASHES.items():
        if file_hash(MODEL_DIR / name) != expected:
            raise ValueError("limited_installed_weight_changed")


def property_differences(frozen, observed, path=()):
    if frozen == observed:
        return []
    if isinstance(frozen, dict) and isinstance(observed, dict):
        result = []
        for key in sorted(frozen.keys() | observed.keys()):
            if key in frozen and key in observed:
                result.extend(property_differences(frozen[key], observed[key], (*path, key)))
            else:
                result.append(
                    {
                        "path": [*path, key],
                        "frozen_present": key in frozen,
                        "observed_present": key in observed,
                        "frozen": frozen.get(key),
                        "observed": observed.get(key),
                    }
                )
        return result
    if isinstance(frozen, list) and isinstance(observed, list) and len(frozen) == len(observed):
        return [
            d
            for i, (a, b) in enumerate(zip(frozen, observed, strict=True))
            for d in property_differences(a, b, (*path, i))
        ]
    return [
        {
            "path": list(path),
            "frozen_present": True,
            "observed_present": True,
            "frozen": frozen,
            "observed": observed,
        }
    ]


def diagnose(parent, cohort, folder, root, *, downloader=None):
    preliminary = json.loads((folder / "plan.json").read_bytes())
    recovery = root / preliminary["recovery_folder"]
    with locks(recovery, folder, root):
        plan, state = load(parent, cohort, folder, root)
        runnable(state)
        no_workers(root)
        if state["diagnostic"] is not None or (folder / "diagnostic").exists():
            raise ValueError("limited_diagnostic_already_consumed")
        if downloader is None:
            from scripts.vlm_product_recovery_network import download_video

            downloader = download_video
        row = next(r for r in plan["rows"] if r["sample_id"] == plan["diagnostic_id"])
        failed = json.loads((recovery / "sessions" / row["sample_id"] / "run.json").read_bytes())
        original_run = root / plan["sealed_folder"] / "sessions" / row["sample_id"] / "run.json"
        original_v9 = json.loads(original_run.read_bytes())
        entry = {"sample_id": row["sample_id"], "status": "running", "seconds": 0.0}
        state["diagnostic"] = entry
        started = time.monotonic()
        checkpoint = partial(persist, folder, state, entry, started, time.monotonic)
        checkpoint()

        def measure(media, work):
            properties, _ = frames_and_properties(media, work)
            observed = {
                "sample_id": row["sample_id"],
                "properties": properties,
                "media_sha256": file_hash(media),
                "frozen_media_sha256": row["media_sha256"],
                "original_v9_media_sha256": original_v9["media_fingerprint"]["sha256"],
                "original_v9_run_sha256": file_hash(original_run),
                "failed_recovery_media_sha256": failed["media_fingerprint"]["sha256"],
                "failed_recovery_run_sha256": file_hash(
                    recovery / "sessions" / row["sample_id"] / "run.json"
                ),
                "decoder_versions": {"pyav": av.__version__, "libraries": av.library_versions},
                "limited_plan_sha256": plan["plan_sha256"],
            }
            # Persist actual decoded values before any equality/difference calculation.
            save(folder / "diagnostic/observed-properties.json", observed)
            differences = property_differences(row["properties"], properties)
            same_failed = observed["media_sha256"] == observed["failed_recovery_media_sha256"]
            return observed | {
                "frozen_properties": row["properties"],
                "differences": differences,
                "properties_equal": properties == row["properties"],
                "identity_approved": False,
                "same_bytes_as_original_v9": observed["media_sha256"]
                == observed["original_v9_media_sha256"],
                "same_bytes_as_failed_recovery": same_failed,
                "retrospective_limit": "same_failed_download_bytes_with_recorded_decoder"
                if same_failed
                else "current_download_only_prior_properties_not_reconstructed",
                "vlm_called": False,
                "test_evaluated": False,
            }

        try:
            with deadline(min(180, TIME_LIMIT - state["elapsed_seconds"])):
                result = run_session(
                    folder / "diagnostic",
                    root / "data/private/media-temp",
                    measure,
                    lambda media: downloader(media, row["sample_id"]),
                    source={
                        "sample_id": row["sample_id"],
                        "purpose": "limited_properties_diagnostic_only",
                    },
                    model_manifest={"vlm_called": False},
                )
                if not result["temporary_directory_removed"]:
                    raise ValueError("limited_cleanup_unconfirmed")
                entry.update(
                    status="completed",
                    files_sha256={
                        n: file_hash(folder / "diagnostic" / n)
                        for n in ("run.json", "features.json", "observed-properties.json")
                    },
                )
        except BaseException as exc:
            entry.update(status="failed", reason=type(exc).__name__)
            state["halt_reason"] = "limited_diagnostic_failed_" + type(exc).__name__
            raise
        finally:
            if (folder / "diagnostic/run.json").is_file():
                entry["run_sha256"] = file_hash(folder / "diagnostic/run.json")
            checkpoint()
        if state["elapsed_seconds"] >= TIME_LIMIT:
            state["halt_reason"] = "limited_time_budget_exhausted"
            save(folder / "checkpoint.json", state)
        return state


def infer(parent, cohort, folder, root, *, invoker=invoke_local_vlm):
    preliminary = json.loads((folder / "plan.json").read_bytes())
    recovery = root / preliminary["recovery_folder"]
    with locks(recovery, folder, root):
        plan, state = load(parent, cohort, folder, root)
        runnable(state)
        if state["diagnostic"] is None:
            raise ValueError("limited_diagnostic_required")
        no_workers(root)
        verify_runtime()
        rows = {r["sample_id"]: r for r in plan["rows"]}
        for sample in plan["inference_ids"][len(state["inferences"]) :]:
            runnable(state)
            path = result_path(folder, sample)
            if path.parent.exists():
                raise ValueError("limited_existing_inference_requires_audit")
            row = rows[sample]
            entry = {"sample_id": sample, "status": "running", "call_count": 0, "seconds": 0.0}
            state["inferences"].append(entry)
            started = time.monotonic()
            checkpoint = partial(persist, folder, state, entry, started, time.monotonic)
            checkpoint()

            def counted(*args, entry=entry, checkpoint=checkpoint, **kwargs):
                if state["calls_reserved"] >= 28 or entry["call_count"] >= 4:
                    raise ValueError("limited_native_budget_exhausted")
                state["calls_reserved"] += 1
                entry["call_count"] += 1
                checkpoint()
                remaining = TIME_LIMIT - state["elapsed_seconds"]
                if remaining <= 0:
                    raise TimeoutError("limited_time_budget_exhausted")
                with deadline(min(180, remaining)):
                    result = invoker(*args, **kwargs)
                print(
                    json.dumps(
                        {"stage": "limited_native", "reservations": state["calls_reserved"]}
                    ),
                    flush=True,
                )
                return result

            try:
                checked_identity(recovery, row, root)
                scratch = root / "data/private/media-temp"
                scratch.mkdir(parents=True, exist_ok=True)
                with tempfile.TemporaryDirectory(
                    prefix="galaxies-inference-limited-", dir=scratch
                ) as name:
                    work = Path(name)
                    cells, seconds = crops(recovery / "images" / (sample + ".png"), work, row)
                    prior = cached_result(root, row)
                    if [file_hash(c) for c in cells] != prior[
                        "input_png_sha256"
                    ] or seconds != prior["input_frame_seconds"]:
                        raise ValueError("limited_original_pixels_or_times_changed")
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
                        "limited_plan_sha256": plan["plan_sha256"],
                        "recovery_plan_sha256": plan["recovery_plan_sha256"],
                        "config_sha256": plan["old_config_sha256"],
                        "vlm": result,
                    },
                )
                checked_result(folder, plan, row, root)
                entry.update(status="completed", result_sha256=file_hash(path))
            except BaseException as exc:
                entry.update(status="failed", reason=type(exc).__name__)
                state["halt_reason"] = "limited_inference_failed_" + type(exc).__name__
                raise
            finally:
                checkpoint()
            if state["elapsed_seconds"] >= TIME_LIMIT:
                state["halt_reason"] = "limited_time_budget_exhausted"
                save(folder / "checkpoint.json", state)
                break
        return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("prepare", "diagnose", "infer", "compare", "inspect"))
    parser.add_argument("--parent", required=True, type=Path)
    parser.add_argument("--cohort-dir", required=True, type=Path)
    parser.add_argument(
        "--recovery-folder",
        type=Path,
        default=Path("data/private/issue-4-vlm-produto-v9-recuperacao-v1"),
    )
    parser.add_argument("--folder", required=True, type=Path)
    args = parser.parse_args()
    root = Path.cwd()
    folder = private_path(args.folder, root)
    with reserved_guard(args.parent, root):
        common = (args.parent, args.cohort_dir, folder, root)
        if args.operation == "prepare":
            output = {
                "plan_sha256": prepare(
                    args.parent,
                    args.cohort_dir,
                    private_path(args.recovery_folder, root),
                    folder,
                    root,
                )["plan_sha256"]
            }
        elif args.operation == "compare":
            from scripts.vlm_product_limited_compare import compare

            report = compare(*common)
            output = {
                k: report[k]
                for k in (
                    "evaluated_cases",
                    "cumulative_acquisitions",
                    "cumulative_native_reservations",
                    "comparison_sha256",
                )
            }
        else:
            state = {"diagnose": diagnose, "infer": infer}.get(
                args.operation, lambda *a: load(*a)[1]
            )(*common)
            output = {k: state[k] for k in ("calls_reserved", "elapsed_seconds", "halt_reason")}
            output["completed_new"] = sum(e["status"] == "completed" for e in state["inferences"])
    print(json.dumps(output), flush=True)


if __name__ == "__main__":
    main()

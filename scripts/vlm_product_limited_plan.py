"""Immutable scope for one diagnostic acquisition and seven cached V9 cases."""

from __future__ import annotations

import json
import math
import os
from contextlib import contextmanager
from importlib.metadata import distributions
from pathlib import Path

import psutil

from scripts.private_checkpoint import digest, file_hash, lock, private_path, save
from scripts.vlm_product_development import cached_result, checked_identity
from scripts.vlm_product_recovery_plan import load as load_recovery
from scripts.vlm_product_states import VERSION, decode, specification, verify
from scripts.vlm_revision import clean_workspace

ROOT = Path(__file__).resolve().parent.parent
BASE_SECONDS = 34491.61625775001
BASE_ACQUISITIONS = 255
BASE_CALLS = 1638
TIME_LIMIT = 27 * 3600
RECOVERY_CHECKPOINT_SHA = "bff118743b9f2135dae6b9402f7a70b53f9baef9e0741a610bb6de4d2193f7bc"
SOURCES = (
    "scripts/vlm_product_limited_plan.py",
    "scripts/vlm_product_limited.py",
    "scripts/vlm_product_limited_compare.py",
    "tests/test_vlm_product_limited.py",
    "docs/issue-4-vlm-produto-v9-adendo-limitado-protocolo.md",
)


def configuration():
    return {name: file_hash(ROOT / name) for name in SOURCES}


def installed_versions():
    return dict(sorted((d.metadata["Name"], d.version) for d in distributions()))


def no_workers(root):
    clean_workspace(root)
    own_processes = {os.getpid(), *(p.pid for p in psutil.Process().parents())}
    for process in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            if process.pid in own_processes:
                continue
            name, args = process.info["name"] or "", process.info["cmdline"] or []
            if name.startswith("llama-") or any(
                a == "yt_dlp" or a.startswith(("scripts.vlm_", "scripts.experiment_b_vlm_"))
                for a in args
            ):
                raise ValueError("limited_concurrent_worker_requires_audit")
        except psutil.NoSuchProcess:
            continue


@contextmanager
def locks(recovery, folder, root):
    recovery, folder = private_path(recovery, root), private_path(folder, root)
    base = json.loads((recovery / "plan.json").read_bytes())
    sealed = private_path(root / base["sealed_folder"], root)
    with (
        lock(sealed / ".lock"),
        lock(recovery / ".lock"),
        lock(folder / ".lock"),
    ):
        yield


def base_state(parent, cohort, recovery, root):
    if file_hash(recovery / "checkpoint.json") != RECOVERY_CHECKPOINT_SHA:
        raise ValueError("limited_sealed_checkpoint_changed")
    plan, state = load_recovery(parent, cohort, recovery, root)
    entries, inferred = state["entries"], state["inferences"]
    if (
        state["halt_reason"] != "recovery_report_sealed"
        or state["images_disposed"]
        or len(entries) != 9
        or [e["sample_id"] for e in entries] != plan["pending_ids"][:9]
        or [e["status"] for e in entries] != ["completed"] * 8 + ["failed"]
        or len(inferred) != 1
        or inferred[0]["status"] != "completed"
        or state["calls_reserved"] != 1
        or state["elapsed_seconds"] != BASE_SECONDS
        or 246 + len(entries) != BASE_ACQUISITIONS
        or 1637 + state["calls_reserved"] != BASE_CALLS
    ):
        raise ValueError("limited_base_scope_or_consumption_changed")
    rows = {r["sample_id"]: r for r in plan["rows"]}
    images = list((recovery / "images").glob("*.png"))
    if {p.stem for p in images} != set(plan["pending_ids"][:8]):
        raise ValueError("limited_requires_eight_preserved_sheets")
    for sample in plan["pending_ids"][:8]:
        checked_identity(recovery, rows[sample], root)
        prior = cached_result(root, rows[sample])
        if len(prior["input_png_sha256"]) != 4 or len(prior["input_frame_seconds"]) != 4:
            raise ValueError("limited_requires_four_original_frames")
    return plan, state


def snapshot(recovery, original, root):
    protected = dict(original["protected_sha256"])
    for path in sorted(recovery.rglob("*")):
        if path.is_symlink():
            raise ValueError("limited_symlink_forbidden")
        if path.is_file() and path.name != ".lock":
            protected[str(path.relative_to(root))] = file_hash(path)
    return protected


def prepare(parent, cohort, recovery, folder, root):
    recovery, folder = private_path(recovery, root), private_path(folder, root)
    sealed = root / json.loads((recovery / "plan.json").read_bytes())["sealed_folder"]
    if any(folder.is_relative_to(old) or old.is_relative_to(folder) for old in (recovery, sealed)):
        raise ValueError("limited_output_must_be_separate")
    with locks(recovery, folder, root):
        if any(
            p.name not in (".lock", "preflight.json", "implementation-verification.json")
            for p in folder.iterdir()
        ):
            raise ValueError("limited_output_already_exists")
        no_workers(root)
        old, _ = base_state(parent, cohort, recovery, root)
        body = {
            "protocol": "product-v9-limited-diagnostic-and-cached-inference-v1",
            "recovery_folder": str(recovery.relative_to(root)),
            "recovery_plan_sha256": old["plan_sha256"],
            "sealed_folder": old["sealed_folder"],
            "rows": old["rows"],
            "pilot_ids": old["pilot_ids"],
            "inference_ids": old["pending_ids"][1:8],
            "diagnostic_id": old["pending_ids"][8],
            "old_config_sha256": old["old_config_sha256"],
            "configuration": configuration(),
            "installed_versions": installed_versions(),
            "protected_sha256": snapshot(recovery, old, root),
            "prior_acquisitions": BASE_ACQUISITIONS,
            "prior_calls": BASE_CALLS,
            "prior_seconds": BASE_SECONDS,
            "acquisition_limit": 1,
            "call_limit": 28,
            "time_limit": TIME_LIMIT,
            "preparation_sha256": {
                n: file_hash(folder / n)
                for n in ("preflight.json", "implementation-verification.json")
                if (folder / n).is_file()
            },
        }
        body["plan_sha256"] = digest(body)
        save(folder / "plan.json", body)
        save(
            folder / "checkpoint.json",
            {
                "plan_sha256": body["plan_sha256"],
                "diagnostic": None,
                "inferences": [],
                "calls_reserved": 0,
                "elapsed_seconds": BASE_SECONDS,
                "halt_reason": None,
            },
        )
        return body


def result_path(folder, sample):
    return folder / "inferences/structured" / sample / "result.json"


def checked_result(folder, plan, row, root):
    path = result_path(folder, row["sample_id"])
    body = json.loads(path.read_bytes())
    current, prior = body["vlm"], cached_result(root, row)
    if (
        body["sample_id"] != row["sample_id"]
        or body["limited_plan_sha256"] != plan["plan_sha256"]
        or body["recovery_plan_sha256"] != plan["recovery_plan_sha256"]
        or body["sheet_sha256"] != row["sheet_sha256"]
        or body["config_sha256"] != plan["old_config_sha256"]
        or current["variant"] != "structured"
        or len(current["input_png_sha256"]) != 4
        or current["input_png_sha256"] != prior["input_png_sha256"]
        or current["input_frame_seconds"] != prior["input_frame_seconds"]
    ):
        raise ValueError("limited_result_identity_changed")
    verify(current, path.parent / "calls")
    return current


def load(parent, cohort, folder, root):
    plan = json.loads((folder / "plan.json").read_bytes())
    state = json.loads((folder / "checkpoint.json").read_bytes())
    recovery = private_path(root / plan["recovery_folder"], root)
    old, _ = base_state(parent, cohort, recovery, root)
    if (
        plan["plan_sha256"] != digest({k: v for k, v in plan.items() if k != "plan_sha256"})
        or plan["configuration"] != configuration()
        or plan["installed_versions"] != installed_versions()
        or plan["protocol"] != "product-v9-limited-diagnostic-and-cached-inference-v1"
        or plan["protected_sha256"] != snapshot(recovery, old, root)
        or any(file_hash(root / p) != h for p, h in plan["protected_sha256"].items())
        or plan["recovery_plan_sha256"] != old["plan_sha256"]
        or plan["rows"] != old["rows"]
        or plan["pilot_ids"] != old["pilot_ids"]
        or plan["inference_ids"] != old["pending_ids"][1:8]
        or plan["diagnostic_id"] != old["pending_ids"][8]
        or plan["sealed_folder"] != old["sealed_folder"]
        or plan["old_config_sha256"] != old["old_config_sha256"]
        or (
            plan["prior_acquisitions"],
            plan["prior_calls"],
            plan["prior_seconds"],
            plan["acquisition_limit"],
            plan["call_limit"],
            plan["time_limit"],
        )
        != (BASE_ACQUISITIONS, BASE_CALLS, BASE_SECONDS, 1, 28, TIME_LIMIT)
        or plan["preparation_sha256"]
        != {
            n: file_hash(folder / n)
            for n in ("preflight.json", "implementation-verification.json")
            if (folder / n).is_file()
        }
        or state["plan_sha256"] != plan["plan_sha256"]
    ):
        raise ValueError("limited_scope_source_or_pin_changed")
    entries = state["inferences"]
    if [e["sample_id"] for e in entries] != plan["inference_ids"][: len(entries)] or len(
        entries
    ) > 7:
        raise ValueError("limited_order_or_duplicate_changed")
    diagnostic = state["diagnostic"]
    if entries and (not diagnostic or diagnostic["status"] != "completed"):
        raise ValueError("limited_diagnostic_required_before_inference")
    elapsed, calls = BASE_SECONDS, 0
    rows = {r["sample_id"]: r for r in plan["rows"]}
    for entry in ([diagnostic] if diagnostic else []) + entries:
        seconds = entry["seconds"]
        if (
            entry["status"] not in ("running", "failed", "completed")
            or type(seconds) not in (float, int)
            or not math.isfinite(seconds)
            or seconds < 0
        ):
            raise ValueError("limited_invalid_ledger")
        elapsed += seconds
        if entry is diagnostic:
            if entry["sample_id"] != plan["diagnostic_id"]:
                raise ValueError("limited_diagnostic_scope_changed")
            directory = folder / "diagnostic"
            if entry["status"] == "completed":
                for name in ("run.json", "features.json", "observed-properties.json"):
                    if file_hash(directory / name) != entry["files_sha256"][name]:
                        raise ValueError("limited_diagnostic_receipt_changed")
                run = json.loads((directory / "run.json").read_bytes())
                if run["status"] != "completed" or not run["temporary_directory_removed"]:
                    raise ValueError("limited_diagnostic_cleanup_unconfirmed")
            elif "run_sha256" in entry and file_hash(directory / "run.json") != entry["run_sha256"]:
                raise ValueError("limited_diagnostic_receipt_changed")
            continue
        count = entry["call_count"]
        if (
            type(count) is not int
            or not 0 <= count <= 4
            or (entry["status"] == "completed" and count != 4)
        ):
            raise ValueError("limited_call_count_changed")
        calls += count
        directory = result_path(folder, entry["sample_id"]).parent / "calls"
        paths = {p.name: p for p in directory.glob("*.json")}
        if set(paths) != {f"frame-{i}.json" for i in range(1, count + 1)}:
            raise ValueError("limited_call_ledger_changed")
        prior = cached_result(root, rows[entry["sample_id"]])
        for i in range(1, count + 1):
            call = json.loads(paths[f"frame-{i}.json"].read_bytes())
            if (
                call["frame"] != i
                or call["schema_version"] != VERSION
                or call["variant"] != "structured"
                or call["input_png_sha256"] != prior["input_png_sha256"][i - 1]
                or call["specification_sha256"] != digest(specification("structured"))
                or call["status"] not in ("running", "failed", "response_captured", "completed")
            ):
                raise ValueError("limited_native_receipt_changed")
            if (
                "raw_response_sha256" in call
                and digest_raw(call["raw_response"]) != call["raw_response_sha256"]
            ):
                raise ValueError("limited_native_raw_changed")
            if (
                call["status"] == "completed"
                and decode(call["raw_response"], "structured")[0] != call["parsed"]
            ):
                raise ValueError("limited_native_parse_changed")
        if entry["status"] == "completed":
            if file_hash(result_path(folder, entry["sample_id"])) != entry["result_sha256"]:
                raise ValueError("limited_result_changed")
            checked_result(folder, plan, rows[entry["sample_id"]], root)
    if (
        type(state["calls_reserved"]) is not int
        or calls != state["calls_reserved"]
        or calls > 28
        or not math.isclose(elapsed, state["elapsed_seconds"], rel_tol=0, abs_tol=1e-8)
    ):
        raise ValueError("limited_cumulative_budget_changed")
    if "comparison_file_sha256" in state:
        if (
            state["halt_reason"] != "limited_report_sealed"
            or file_hash(folder / "comparison.json") != state["comparison_file_sha256"]
        ):
            raise ValueError("limited_terminal_receipt_changed")
        report = json.loads((folder / "comparison.json").read_bytes())
        completed = [e for e in entries if e["status"] == "completed"]
        if (
            report["comparison_sha256"]
            != digest({k: v for k, v in report.items() if k != "comparison_sha256"})
            or report["limited_plan_sha256"] != plan["plan_sha256"]
            or report["evaluated_cases"] != 34 + len(completed)
            or report["new_native_reservations"] != calls
            or report["cumulative_acquisitions"] != BASE_ACQUISITIONS + 1
            or report["cumulative_native_reservations"] != BASE_CALLS + calls
            or report["elapsed_seconds"] != state["elapsed_seconds"]
            or report["released_fields"] != []
            or report["fields_ready_for_future_blind_audit"] != []
            or any(
                report[k] is not False
                for k in (
                    "new_blind_audit",
                    "predictive_training_started",
                    "test_evaluated",
                    "m1_replaced",
                )
            )
        ):
            raise ValueError("limited_terminal_scope_changed")
    elif state["halt_reason"] == "limited_report_sealed":
        raise ValueError("limited_missing_terminal_receipt")
    return plan, state


def digest_raw(raw):
    import hashlib

    return hashlib.sha256(raw.encode()).hexdigest()


def runnable(state):
    if state["halt_reason"]:
        raise ValueError("limited_halted_no_automatic_retry")
    if any(
        e["status"] != "completed"
        for e in ([state["diagnostic"]] if state["diagnostic"] else []) + state["inferences"]
    ):
        raise ValueError("limited_interrupted_requires_audit")
    if state["elapsed_seconds"] >= TIME_LIMIT:
        raise ValueError("limited_time_budget_exhausted")


def persist(folder, state, entry, started, clock):
    entry["seconds"] = clock() - started
    state["elapsed_seconds"] = BASE_SECONDS + sum(
        e["seconds"]
        for e in ([state["diagnostic"]] if state["diagnostic"] else []) + state["inferences"]
    )
    save(folder / "checkpoint.json", state)

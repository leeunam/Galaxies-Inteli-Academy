"""Immutable V8 development cohort and cumulative accounting, without new sampling."""

from __future__ import annotations

import json
import math
from pathlib import Path

from scripts.private_checkpoint import digest, file_hash, lock, save
from scripts.vlm_explicit_presence import specification, verify
from scripts.vlm_revision import seconds_for
from scripts.vlm_revision_plan import OLD
from scripts.vlm_revision_plan import load as load_previous

PREVIOUS = Path("data/private/issue-4-vlm-revisao-1")
DIAGNOSTIC = Path("data/private/issue-4-vlm-diagnostico-20261019")
FINAL_SHA = "7633185e7db37d82ac7773da84bcb7d160ecb904a46ebcf6191e4b9d84a211ba"
DIAGNOSTIC_SHA = "8067bdc5fb918a474d23a578a9e1d475640bb7148425fc982a364ca7c21a7993"
BASE_SECONDS = 8306.90845013706
BASE_ACQUISITIONS = 118
BASE_CALLS = 649
ACQUISITION_LIMIT = 192
CALL_LIMIT = 804
TIME_LIMIT = 27 * 3600
PROTOCOL = "vlm-v8-revealed-development-64-v1"
SOURCES = (
    "scripts/vlm_explicit_presence.py",
    "scripts/vlm_prompt_plan.py",
    "scripts/vlm_prompt_development.py",
    "docs/issue-4-vlm-v8-desenvolvimento-protocolo.md",
)
FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
ANNOTATIONS = {
    "development": str(OLD / "blind-annotations-v3.json"),
    "audit": str(PREVIOUS / "blind-annotations.json"),
}


def controls():
    rows = []
    for size in (14, 48):
        for gray in (0, 160):
            for y in (8, 250):
                rows.append(
                    {
                        "sample_id": f"text-{size}-{gray}-{y}",
                        "size": size,
                        "gray": gray,
                        "y": y,
                        "text": True,
                    }
                )
    rows.extend(
        {"sample_id": name, "text": False} for name in ("white", "black", "lines", "shapes")
    )
    return rows


def prior(parent, cohort, root):
    plan, state = load_previous(parent, cohort, root / PREVIOUS, root)
    if file_hash(root / PREVIOUS / "final-verification.json") != FINAL_SHA or (
        file_hash(root / DIAGNOSTIC / "final-verification.json") != DIAGNOSTIC_SHA
    ):
        raise ValueError("v8_previous_receipts_changed")
    final = json.loads((root / PREVIOUS / "final-verification.json").read_bytes())
    diagnostic = json.loads((root / DIAGNOSTIC / "final-verification.json").read_bytes())
    protected = dict(final["frozen_file_sha256"])
    for folder, names in (
        (PREVIOUS, final["receipt_file_sha256"]),
        (DIAGNOSTIC, diagnostic["diagnostic_receipt_sha256"]),
    ):
        protected.update({str(folder / name): sha for name, sha in names.items()})
    protected[str(PREVIOUS / "final-verification.json")] = FINAL_SHA
    protected[str(DIAGNOSTIC / "final-verification.json")] = DIAGNOSTIC_SHA
    for path, sha in protected.items():
        if file_hash(root / path) != sha:
            raise ValueError("v8_protected_evidence_changed")
    checkpoint = json.loads((root / DIAGNOSTIC / "checkpoint.json").read_bytes())
    if (
        state["halt_reason"] != "quality_gate_no_columns_released"
        or not state["images_disposed"]
        or checkpoint["status"] != "completed"
        or checkpoint["cumulative_elapsed_seconds"] != BASE_SECONDS
        or checkpoint["cumulative_native_calls"] != BASE_CALLS
        or state["prior_acquisitions"] + sum(len(e["attempts"]) for e in state["entries"])
        != BASE_ACQUISITIONS
    ):
        raise ValueError("v8_prior_budget_changed")
    return plan, protected


def configuration(root):
    return {
        "sources_sha256": {name: file_hash(root / name) for name in SOURCES},
        "font_sha256": file_hash(FONT),
        "specification": specification(),
        "controls": controls(),
    }


def prepare(parent, cohort, folder, root):
    previous, protected = prior(parent, cohort, root)
    body = {
        "protocol": PROTOCOL,
        "previous_plan_sha256": previous["plan_sha256"],
        "cohort_sha256": previous["cohort_sha256"],
        "partition_sha256": previous["partition_sha256"],
        "rows": previous["rows"],
        "config": configuration(root),
        "protected_sha256": protected,
        "annotations": ANNOTATIONS,
        "new_blind_audit": False,
        "labels_used": False,
        "test_evaluated": False,
    }
    body["plan_sha256"] = digest(body)
    with lock(folder / ".lock"):
        if any(p.name != ".lock" for p in folder.iterdir()):
            raise ValueError("v8_output_already_exists")
        save(folder / "plan.json", body)
        save(
            folder / "checkpoint.json",
            {
                "plan_sha256": body["plan_sha256"],
                "prior_acquisitions": BASE_ACQUISITIONS,
                "prior_native_calls": BASE_CALLS,
                "acquisition_limit": ACQUISITION_LIMIT,
                "elapsed_seconds": BASE_SECONDS,
                "dns_retries_used": 0,
                "calls_reserved": 0,
                "entries": [],
                "controls": [],
                "inferences": [],
                "halt_reason": None,
                "images_disposed": False,
            },
        )
    return body


def load(parent, cohort, folder, root):
    previous, protected = prior(parent, cohort, root)
    plan = json.loads((folder / "plan.json").read_bytes())
    state = json.loads((folder / "checkpoint.json").read_bytes())
    if (
        plan["protocol"] != PROTOCOL
        or plan["plan_sha256"] != digest({k: v for k, v in plan.items() if k != "plan_sha256"})
        or state["plan_sha256"] != plan["plan_sha256"]
        or plan["previous_plan_sha256"] != previous["plan_sha256"]
        or plan["rows"] != previous["rows"]
        or len(plan["rows"]) != 64
        or any(r["partition"] != "train" for r in plan["rows"])
        or plan["cohort_sha256"] != previous["cohort_sha256"]
        or plan["partition_sha256"] != previous["partition_sha256"]
        or plan["config"] != configuration(root)
        or plan["protected_sha256"] != protected
        or plan["new_blind_audit"] is not False
        or plan["annotations"] != ANNOTATIONS
        or plan["labels_used"] is not False
        or plan["test_evaluated"] is not False
    ):
        raise ValueError("v8_plan_or_frozen_inputs_changed")
    validate_state(plan, state, folder)
    return plan, state


def result_path(folder, sample, control=False):
    return folder / ("control-results" if control else "inferences") / sample / "result.json"


def validate_state(plan, state, folder):
    rows = {r["sample_id"]: r for r in plan["rows"]}
    control_ids = {r["sample_id"] for r in controls()}
    pending = None
    if "cleanup_pending" in state or state["images_disposed"]:
        path = folder / "image-disposal.json"
        disposal = json.loads(path.read_bytes())
        pending_list = state.get("cleanup_pending", [])
        if (
            type(pending_list) is not list
            or len(set(pending_list)) != len(pending_list)
            or not set(pending_list) <= set(rows)
            or state["images_disposed"]
            and pending_list
            or file_hash(path) != state["disposal_sha256"]
            or disposal
            != {
                "images": {r["sample_id"]: r["sheet_sha256"] for r in plan["rows"]},
                "plan_sha256": plan["plan_sha256"],
                "comparison_file_sha256": state["comparison_file_sha256"],
            }
            or state["halt_reason"] != "development_comparison_completed"
        ):
            raise ValueError("v8_disposal_evidence_changed")
        pending = set(pending_list)
    for key, allowed in (
        ("entries", set(rows)),
        ("inferences", set(rows)),
        ("controls", control_ids),
    ):
        ids = [e["sample_id"] for e in state[key]]
        if len(ids) != len(set(ids)) or not set(ids) <= allowed:
            raise ValueError("v8_invalid_ledger_keys")
    accounted, calls, attempts, retries = BASE_SECONDS, 0, 0, 0
    for entry in [*state["entries"], *state["controls"], *state["inferences"]]:
        seconds = entry.get("seconds", 0.0)
        if entry["status"] not in ("running", "completed", "failed") or (
            type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0
        ):
            raise ValueError("v8_invalid_ledger_entry")
        accounted += seconds
    for entry in state["entries"]:
        tries = entry.get("attempts", [])
        if (
            not 1 <= len(tries) <= 2
            or entry["status"] != "running"
            and tries[-1]["status"] != entry["status"]
        ):
            raise ValueError("v8_invalid_acquisition_attempts")
        attempts += len(tries)
        retries += len(tries) - 1
        for attempt in tries:
            if (
                attempt["status"] not in ("running", "completed", "failed")
                or attempt["status"] != "running"
                and (
                    type(attempt["seconds"]) not in (int, float)
                    or not math.isfinite(attempt["seconds"])
                    or attempt["seconds"] < 0
                )
            ):
                raise ValueError("v8_invalid_attempt_time")
        if len(tries) == 2:
            first = tries[0]
            archived = folder / "failed-attempts" / entry["sample_id"] / "1/run.json"
            if (
                first["reason"] != "temporary_network_dns_failure"
                or first["cleanup"] is not True
                or first["dns_preflight_positive"] is not True
                or file_hash(archived) != first["run_sha256"]
            ):
                raise ValueError("v8_dns_recovery_changed")
        if entry["status"] == "completed":
            if set(entry["files_sha256"]) != {"features.json", "run.json"}:
                raise ValueError("v8_acquisition_hashes_incomplete")
            for name, sha in entry["files_sha256"].items():
                if file_hash(folder / "sessions" / entry["sample_id"] / name) != sha:
                    raise ValueError("v8_acquisition_evidence_changed")
            image = folder / "images" / (entry["sample_id"] + ".png")
            if pending is None:
                if file_hash(image) != rows[entry["sample_id"]]["sheet_sha256"]:
                    raise ValueError("v8_sheet_changed")
            elif image.exists() and (
                entry["sample_id"] not in pending
                or file_hash(image) != rows[entry["sample_id"]]["sheet_sha256"]
            ):
                raise ValueError("v8_disposal_evidence_changed")
    for control, entries in ((True, state["controls"]), (False, state["inferences"])):
        for entry in entries:
            expected = 3 if control else 3 * len(seconds_for(rows[entry["sample_id"]]))
            if type(entry["call_count"]) is not int or not 0 <= entry["call_count"] <= expected:
                raise ValueError("v8_invalid_call_counter")
            calls += entry["call_count"]
            if entry["status"] == "completed":
                path = result_path(folder, entry["sample_id"], control)
                if file_hash(path) != entry["result_sha256"] or entry["call_count"] != expected:
                    raise ValueError("v8_inference_receipt_changed")
                verify(json.loads(path.read_bytes())["vlm"], path.parent / "calls")
    if (
        state["prior_acquisitions"] != BASE_ACQUISITIONS
        or state["prior_native_calls"] != BASE_CALLS
        or state["acquisition_limit"] != ACQUISITION_LIMIT
        or attempts + BASE_ACQUISITIONS > ACQUISITION_LIMIT
        or state["dns_retries_used"] != retries
        or type(state["dns_retries_used"]) is not int
        or not 0 <= retries <= 10
        or type(state["calls_reserved"]) is not int
        or state["calls_reserved"] != calls
        or calls > CALL_LIMIT
        or not math.isfinite(state["elapsed_seconds"])
        or not math.isclose(state["elapsed_seconds"], accounted, rel_tol=0, abs_tol=1e-8)
    ):
        raise ValueError("v8_cumulative_budget_changed")
    if state["images_disposed"] and list((folder / "images").glob("*.png")):
        raise ValueError("v8_disposal_evidence_changed")


def runnable(state):
    if state["halt_reason"] or state["images_disposed"]:
        raise ValueError("v8_halted_no_automatic_retry")
    if any(
        e["status"] == "running"
        for e in [*state["entries"], *state["controls"], *state["inferences"]]
    ):
        raise ValueError("v8_interrupted_session_requires_audit")
    if state["elapsed_seconds"] >= TIME_LIMIT:
        raise ValueError("v8_total_time_budget_exhausted")


def persist(folder, state, entry, started, clock):
    entry["seconds"] = clock() - started
    state["elapsed_seconds"] = BASE_SECONDS + sum(
        e.get("seconds", 0.0) for e in [*state["entries"], *state["controls"], *state["inferences"]]
    )
    save(folder / "checkpoint.json", state)

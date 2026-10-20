"""Fixed V14-R lineage, phase gates and conservative one-shot accounting."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

from scripts.private_checkpoint import digest, file_hash, private_path
from scripts.vlm_product_limited_plan import installed_versions, no_workers
from scripts.vlm_product_v13_plan import load as load_v13
from scripts.vlm_product_v14 import FIELD, VERSION, decode, save, specification, verify
from scripts.vlm_product_v14_grammar import check_receipt
from scripts.vlm_prompt_plan import FONT, controls

ROOT = Path(__file__).resolve().parent.parent
SOURCES = (
    "scripts/vlm_product_v14.py",
    "scripts/vlm_product_v14_plan.py",
    "scripts/vlm_product_v14_run.py",
    "tests/test_vlm_product_v14.py",
    "tests/test_vlm_product_v14_run.py",
    "docs/issue-4-vlm-v14-protocolo.md",
    "scripts/vlm_product_v14_review.py",
    "scripts/vlm_product_v14_grammar.py",
    "scripts/vlm_product_v13_grammar.cpp",
    "tests/test_vlm_product_v14_grammar.py",
)
CALL_LIMIT, ACQUISITION_LIMIT, SESSION_LIMIT = 92, 12, 2400
PROTOCOL = "product-v14-single-item-revealed-development-v1"


def reserve_record(folder, category, number, body):
    directory = folder / "reservations"
    directory.mkdir(exist_ok=True, mode=0o700)
    path = directory / f"{category}-{number:04d}.json"
    with path.open("x") as output:
        path.chmod(0o600)
        json.dump(body, output, ensure_ascii=True, allow_nan=False)
        output.flush()
        os.fsync(output.fileno())
    handle = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(handle)
    finally:
        os.close(handle)


def check_reservations(folder, plan, state):
    expected = {"native": [], "acquisition": []}
    for operation, entry in enumerate(state["operations"], 1):
        common = {
            "plan_sha256": plan["plan_sha256"],
            "operation": operation,
            "kind": entry["kind"],
            "sample_id": entry["sample_id"],
        }
        if entry["kind"] == "acquisition":
            expected["acquisition"].append(common)
        else:
            for frame in range(1, entry["call_count"] + 1):
                expected["native"].append(common | {"frame": frame})
    wanted = set()
    for category, entries in expected.items():
        for number, common in enumerate(entries, 1):
            name = f"{category}-{number:04d}.json"
            wanted.add(name)
            receipt = json.loads((folder / "reservations" / name).read_bytes())
            if receipt != common | {"number": number}:
                raise ValueError("v14_reservation_changed")
    if {p.name for p in (folder / "reservations").glob("*")} != wanted:
        raise ValueError("v14_reservation_count_changed")


def check_native_files(folder, plan, entry):
    directory = result_path(folder, entry["kind"], entry["sample_id"]).parent / "calls"
    names = {p.name for p in directory.glob("*")}
    count = entry["call_count"]
    complete = {f"frame-{i}.json" for i in range(1, count + 1)}
    missing_tail = {f"frame-{i}.json" for i in range(1, count)}
    if names != complete and not (entry["status"] != "completed" and names == missing_tail):
        raise ValueError("v14_native_count_changed")
    native_seconds = 0.0
    for name in names:
        call = json.loads((directory / name).read_bytes())
        frame = int(name.removeprefix("frame-").removesuffix(".json"))
        if (
            call["schema_version"] != VERSION
            or call["frame"] != frame
            or call["specification_sha256"] != digest(specification())
            or call["input_png_sha256"]
            != plan["base"]["inputs"][entry["sample_id"]]["png_sha256"][frame - 1]
            or call["status"] not in ("running", "response_captured", "failed", "completed")
        ):
            raise ValueError("v14_native_receipt_changed")
        if "raw_response_sha256" in call:
            import hashlib

            if (
                hashlib.sha256(call["raw_response"].encode()).hexdigest()
                != call["raw_response_sha256"]
            ):
                raise ValueError("v14_native_raw_changed")
        if call["status"] == "completed" and decode(call["raw_response"])[0] != call["parsed"]:
            raise ValueError("v14_native_parse_changed")
        native_seconds += call.get("runtime_seconds", 0.0)
    if entry["seconds"] + 1e-8 < native_seconds:
        raise ValueError("v14_measured_time_reset")


def configuration():
    return {
        "sources": {n: file_hash(ROOT / n) for n in SOURCES},
        "specification": specification(),
        "controls": controls(),
        "font_sha256": file_hash(FONT),
        "installed_versions": installed_versions(),
        "native_preflight": native_preflight(),
    }


def native_preflight():
    folder = ROOT / "data/private/issue-4-vlm-v14-verificacao-v1/native-preflight-final-v2"
    receipt = check_receipt(folder, ROOT)
    return {
        "path": str(folder.relative_to(ROOT)),
        "receipt_file_sha256": file_hash(folder / "receipt.json"),
        "receipt_sha256": receipt["receipt_sha256"],
        "grammar_sha256": receipt["grammar_sha256"],
    }


def load_base(parent, cohort, root):
    previous = root / "data/private/issue-4-vlm-v13-v1"
    old, state = load_v13(parent, cohort, previous, root)
    if (
        not state["sealed"]
        or state["halt_reason"] != "v13_external_termination_exit_143_no_retry"
        or state["calls_reserved"] != 32
        or state["acquisitions_reserved"] != 0
    ):
        raise ValueError("v14_sealed_v13_required")
    diagnostic = root / "data/private/issue-4-vlm-v14-verificacao-v1"
    before = json.loads((diagnostic / "before.json").read_bytes())
    protected = dict(before["protected_sha256"])
    protected[str((diagnostic / "before.json").relative_to(root))] = file_hash(
        diagnostic / "before.json"
    )
    if any(file_hash(root / n) != h for n, h in protected.items()):
        raise ValueError("v14_protected_evidence_changed")
    drafts = root / "data/private/issue-4-vlm-v13-cosmetic-diagnostico-v1/proposal-drafts.json"
    proposal = json.loads(drafts.read_bytes())["specification"]
    if specification() != proposal:
        raise ValueError("v14_approved_proposal_changed")
    controls_old, videos_old = {}, {}
    for entry in state["operations"]:
        if entry["status"] != "completed":
            continue  # Partial fifth video is never a complete comparison baseline.
        path = previous / "results" / entry["kind"] / entry["sample_id"] / "result.json"
        references = controls_old if entry["kind"] == "control" else videos_old
        references[entry["sample_id"]] = {
            "path": str(path.relative_to(root)),
            "sha256": file_hash(path),
        }
    return old["base"] | {
        "ancestor_folders": old["base"]["ancestor_folders"] + [str(previous.relative_to(root))],
        "prior_calls": old["base"]["prior_calls"] + state["calls_reserved"],
        "prior_acquisitions": old["base"]["prior_acquisitions"] + state["acquisitions_reserved"],
        "prior_seconds": state["elapsed_seconds"],
        "protected_sha256": protected,
        "proposal_drafts_sha256": file_hash(drafts),
        "v13_control_references": controls_old,
        "v13_references": videos_old,
    }


def prepare(parent, cohort, folder, root):
    folder = private_path(folder, root)
    base = load_base(parent, cohort, root)
    if any(
        folder.is_relative_to(root / n) or (root / n).is_relative_to(folder)
        for n in base["ancestor_folders"]
    ):
        raise ValueError("v14_output_must_be_separate")
    if folder.exists() and any(p.name != ".lock" for p in folder.iterdir()):
        raise ValueError("v14_output_already_consumed")
    no_workers(root)
    body = {
        "protocol": PROTOCOL,
        "base": base,
        "configuration": configuration(),
        "limits": {
            "calls": CALL_LIMIT,
            "acquisitions": ACQUISITION_LIMIT,
            "session_seconds": SESSION_LIMIT,
        },
        "authorization": "explicit_user_implement_v14_native_grammar_and_conditional_revealed_evaluation_2026-10-20",
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
            "halt_reason": None,
            "sealed": False,
            "cue_reviews": {},
        },
    )
    return body


def sequence(plan):
    base = plan["base"]
    return (
        [("control", r["sample_id"]) for r in controls()]
        + [("preserved", n) for n in base["phase1_ids"]]
        + [(kind, n) for n in base["phase2_ids"] for kind in ("acquisition", "additional")]
    )


def result_path(folder, kind, sample):
    return folder / "results" / kind / sample / "result.json"


def files_for(folder, entry):
    directory = (
        folder / "sessions" / entry["sample_id"]
        if entry["kind"] == "acquisition"
        else result_path(folder, entry["kind"], entry["sample_id"]).parent
    )
    return {str(p.relative_to(folder)): file_hash(p) for p in sorted(directory.rglob("*.json"))}


def checked_result(folder, plan, entry):
    body = json.loads(result_path(folder, entry["kind"], entry["sample_id"]).read_bytes())
    expected = plan["base"]["inputs"][entry["sample_id"]]
    result = body["vlm"]
    if (
        body["plan_sha256"] != plan["plan_sha256"]
        or body["sample_id"] != entry["sample_id"]
        or result["input_png_sha256"] != expected["png_sha256"]
        or result["input_frame_seconds"] != expected["seconds"]
    ):
        raise ValueError("v14_result_inputs_changed")
    verify(result, result_path(folder, entry["kind"], entry["sample_id"]).parent / "calls")
    return result


def correct(plan, entry, result):
    predicted = result["parsed"][FIELD]
    if entry["kind"] == "control":
        return predicted["value"] is False
    truth = plan["base"]["truth"][entry["sample_id"]][FIELD]
    return (
        predicted["value"] == truth["value"]
        and bool(predicted["frames"])
        and set(predicted["frames"]) <= set(truth["frames"])
    )


def phase_passed(folder, plan, state, kind, count):
    entries = [e for e in state["operations"] if e["kind"] == kind]
    return len(entries) == count and all(
        e["status"] == "completed" and correct(plan, e, checked_result(folder, plan, e))
        for e in entries
    )


def load(parent, cohort, folder, root):
    if any(p.is_symlink() for p in folder.rglob("*")):
        raise ValueError("v14_queue_symlink_forbidden")
    plan = json.loads((folder / "plan.json").read_bytes())
    state = json.loads((folder / "checkpoint.json").read_bytes())
    if type(state["sealed"]) is not bool:
        raise ValueError("v14_invalid_terminal_state")
    if (
        plan["protocol"] != PROTOCOL
        or plan["plan_sha256"] != digest({k: v for k, v in plan.items() if k != "plan_sha256"})
        or plan["configuration"] != configuration()
        or plan["base"] != load_base(parent, cohort, root)
        or plan["limits"] != {"calls": 92, "acquisitions": 12, "session_seconds": 2400}
        or plan["authorization"]
        != "explicit_user_implement_v14_native_grammar_and_conditional_revealed_evaluation_2026-10-20"
        or state["plan_sha256"] != plan["plan_sha256"]
    ):
        raise ValueError("v14_plan_source_or_lineage_changed")
    operations = state["operations"]
    if [(e["kind"], e["sample_id"]) for e in operations] != sequence(plan)[
        : len(operations)
    ] or len(operations) > 44:
        raise ValueError("v14_operation_order_changed")
    seconds = 0.0
    for entry in operations:
        maximum = 0 if entry["kind"] == "acquisition" else 1 if entry["kind"] == "control" else 4
        if (
            entry["status"] not in ("running", "failed", "completed")
            or type(entry["call_count"]) is not int
            or not 0 <= entry["call_count"] <= maximum
            or (entry["status"] == "completed" and entry["call_count"] != maximum)
            or type(entry["seconds"]) not in (int, float)
            or not math.isfinite(entry["seconds"])
            or entry["seconds"] < 0
        ):
            raise ValueError("v14_invalid_consumption")
        seconds += entry["seconds"]
        if entry["status"] != "running":
            if entry["kind"] != "acquisition":
                check_native_files(folder, plan, entry)
            if files_for(folder, entry) != entry["files_sha256"]:
                raise ValueError("v14_operation_receipt_changed")
            if entry["status"] == "completed" and entry["kind"] != "acquisition":
                checked_result(folder, plan, entry)
            if entry["status"] == "completed" and entry["kind"] == "acquisition":
                run = json.loads(
                    (folder / "sessions" / entry["sample_id"] / "run.json").read_bytes()
                )
                features = json.loads(
                    (folder / "sessions" / entry["sample_id"] / "features.json").read_bytes()
                )
                row = next(r for r in plan["base"]["rows"] if r["sample_id"] == entry["sample_id"])
                expected = plan["base"]["inputs"][entry["sample_id"]]
                if (
                    run["status"] != "completed"
                    or run["temporary_directory_removed"] is not True
                    or features["sample_id"] != entry["sample_id"]
                    or features["properties"] != row["properties"]
                    or features["sheet_sha256"] != row["sheet_sha256"]
                    or features["input_png_sha256"] != expected["png_sha256"]
                    or features["input_frame_seconds"] != expected["seconds"]
                ):
                    raise ValueError("v14_acquired_identity_changed")
    if (
        type(state["calls_reserved"]) is not int
        or state["calls_reserved"] != sum(e["call_count"] for e in operations)
        or type(state["acquisitions_reserved"]) is not int
        or state["acquisitions_reserved"] != sum(e["kind"] == "acquisition" for e in operations)
        or state["calls_reserved"] > CALL_LIMIT
        or state["acquisitions_reserved"] > ACQUISITION_LIMIT
        or seconds > SESSION_LIMIT
        or not math.isclose(seconds, state["new_session_seconds"], rel_tol=0, abs_tol=1e-8)
        or not math.isclose(
            plan["base"]["prior_seconds"] + seconds,
            state["elapsed_seconds"],
            rel_tol=0,
            abs_tol=1e-8,
        )
        or state["elapsed_seconds"] > 27 * 3600
    ):
        raise ValueError("v14_cumulative_budget_changed")
    check_reservations(folder, plan, state)
    if len(operations) > 12 and not phase_passed(folder, plan, state, "control", 12):
        raise ValueError("v14_controls_required")
    if len(operations) > 20 and not phase_passed(folder, plan, state, "preserved", 8):
        raise ValueError("v14_preserved_success_required")
    if state["sealed"]:
        report = json.loads((folder / "comparison.json").read_bytes())
        if (
            file_hash(folder / "comparison.json") != state["comparison_file_sha256"]
            or report["plan_sha256"] != plan["plan_sha256"]
            or report["comparison_sha256"]
            != digest({k: v for k, v in report.items() if k != "comparison_sha256"})
        ):
            raise ValueError("v14_terminal_report_changed")
        if (
            report["new_calls_reserved"] != state["calls_reserved"]
            or report["new_acquisitions_reserved"] != state["acquisitions_reserved"]
            or report["new_session_seconds"] != state["new_session_seconds"]
            or report["cumulative_session_seconds"] != state["elapsed_seconds"]
            or report["cumulative_calls"] != plan["base"]["prior_calls"] + state["calls_reserved"]
            or report["cumulative_acquisitions"]
            != plan["base"]["prior_acquisitions"] + state["acquisitions_reserved"]
            or report["evaluated_cases"]
            != sum(
                e["kind"] in ("preserved", "additional") and e["status"] == "completed"
                for e in operations
            )
            or report["released_fields"] != []
            or any(
                report[n] is not False
                for n in (
                    "new_blind_audit",
                    "predictive_training_started",
                    "test_evaluated",
                    "m1_replaced",
                )
            )
        ):
            raise ValueError("v14_terminal_scope_changed")
    from scripts.vlm_product_v14_review import check_reviews

    reviews = check_reviews(folder, plan, state)
    if state["sealed"] and report["cue_reviews"] != reviews:
        raise ValueError("v14_terminal_cue_review_changed")
    return plan, state


def runnable(state):
    if (
        state["sealed"]
        or state["halt_reason"]
        or any(e["status"] != "completed" for e in state["operations"])
    ):
        raise ValueError("v14_consumed_or_uncertain_no_retry")
    if state["new_session_seconds"] >= SESSION_LIMIT:
        raise ValueError("v14_session_budget_exhausted")

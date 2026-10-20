"""Separate recovery lineage for a sealed V9 queue; no media or inference."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

from scripts.private_checkpoint import digest, file_hash, lock, save
from scripts.vlm_product_development import cached_result, checked_identity, evaluation_rows
from scripts.vlm_product_plan import load as load_original
from scripts.vlm_product_states import VERSION, decode, specification, verify

SEALED_FINAL_SHA = "6b5f5e078e530b2ce41a7b30607532f8e1c8df83897bd4b9c541f697c28572a9"
BASE_SECONDS = 34439.12766741601
BASE_ACQUISITIONS = 246
BASE_CALLS = 1637
ACQUISITION_LIMIT = 31
CALL_LIMIT = 121
TIME_LIMIT = 27 * 3600
SOURCE_ROOT = Path(__file__).resolve().parent.parent
SOURCES = (
    "scripts/vlm_product_recovery_plan.py",
    "scripts/vlm_product_recovery.py",
    "scripts/vlm_product_recovery_network.py",
    "scripts/vlm_product_recovery_compare.py",
    "tests/test_vlm_product_recovery.py",
    "docs/issue-4-vlm-produto-v9-recuperacao-protocolo.md",
)
PREPARATION_RECEIPTS = (
    "preflight.json",
    "viability-before-preparation.json",
    "implementation-verification.json",
)


def configuration():
    return {name: file_hash(SOURCE_ROOT / name) for name in SOURCES}


def sealed_pins(sealed, root):
    if file_hash(sealed / "final-verification.json") != SEALED_FINAL_SHA:
        raise ValueError("recovery_sealed_final_changed")
    final = json.loads((sealed / "final-verification.json").read_bytes())
    protected = dict(final["protected_sha256"])
    protected.update(
        {
            str((sealed / name).relative_to(root)): sha
            for name, sha in final.get("receipt_file_sha256", {}).items()
        }
    )
    for name, sha in protected.items():
        if file_hash(root / name) != sha:
            raise ValueError("recovery_protected_file_changed")
    for path in sorted(sealed.rglob("*")):
        if path.is_symlink():
            raise ValueError("recovery_sealed_symlink_forbidden")
        if path.is_file() and path.name != ".lock":
            protected[str(path.relative_to(root))] = file_hash(path)
    return protected


def partial_calls(sealed, sample, expected):
    folder = sealed / "inferences/structured" / sample
    if (folder / "result.json").exists():
        raise ValueError("recovery_response_already_exists")
    hashes = {}
    for i, sha in enumerate(expected, 1):
        path = folder / "calls" / f"frame-{i}.json"
        call = json.loads(path.read_bytes())
        if (
            call["schema_version"] != VERSION
            or call["frame"] != i
            or call["variant"] != "structured"
            or call["input_png_sha256"] != sha
            or call["specification_sha256"] != digest(specification("structured"))
        ):
            raise ValueError("recovery_partial_input_changed")
        if i == 4:
            if call["status"] != "running" or "raw_response" in call:
                raise ValueError("recovery_lost_response_not_missing")
        else:
            parsed, _ = decode(call["raw_response"], "structured")
            if (
                call["status"] != "completed"
                or call["parsed"] != parsed
                or call["raw_response_sha256"]
                != hashlib.sha256(call["raw_response"].encode()).hexdigest()
            ):
                raise ValueError("recovery_partial_raw_changed")
        hashes[str(path.relative_to(sealed))] = file_hash(path)
    if len(list((folder / "calls").glob("*.json"))) != 4:
        raise ValueError("recovery_unexpected_partial_call")
    return hashes


def prepare(parent, cohort, sealed, folder, root):
    with lock(sealed / ".lock"), lock(folder / ".lock"):
        if any(p.name not in (".lock", *PREPARATION_RECEIPTS) for p in folder.iterdir()):
            raise ValueError("recovery_output_already_exists")
        if file_hash(sealed / "final-verification.json") != SEALED_FINAL_SHA:
            raise ValueError("recovery_sealed_final_changed")
        old, state = load_original(parent, cohort, sealed, root)
        order = evaluation_rows(old, True)
        done, failed = state["inferences"][:33], state["inferences"][33:]
        if (
            len(done) != 33
            or any(e["status"] != "completed" for e in done)
            or [e["sample_id"] for e in done] != [r["sample_id"] for r in order[:33]]
            or len(failed) != 1
            or failed[0]["sample_id"] != order[33]["sample_id"]
            or failed[0]["status"] != "failed"
            or failed[0]["call_count"] != 4
            or state["halt_reason"] != "product_report_sealed"
            or not state["images_disposed"]
            or state["calls_reserved"] + state["prior_native_calls"] != BASE_CALLS
            or state["prior_acquisitions"] + sum(len(e["attempts"]) for e in state["entries"])
            != BASE_ACQUISITIONS
            or state["elapsed_seconds"] != BASE_SECONDS
        ):
            raise ValueError("recovery_sealed_scope_or_budget_changed")
        sample = order[33]["sample_id"]
        prior = cached_result(root, order[33])
        if len(prior["input_png_sha256"]) != 4:
            raise ValueError("recovery_requires_four_original_frames")
        partial = partial_calls(sealed, sample, prior["input_png_sha256"])
        protected = sealed_pins(sealed, root)
        body = {
            "protocol": "product-v9-explicit-recovery-v1",
            "sealed_folder": str(sealed.relative_to(root)),
            "sealed_plan_sha256": old["plan_sha256"],
            "rows": old["rows"],
            "annotations": old["annotations"],
            "pilot_ids": old["pilot_ids"],
            "pending_ids": [r["sample_id"] for r in order[33:]],
            "inherited_result_sha256": {e["sample_id"]: e["result_sha256"] for e in done},
            "partial_call_sha256": partial,
            "old_config_sha256": digest(old["config"]),
            "configuration": configuration(),
            "preparation_sha256": {
                name: file_hash(folder / name)
                for name in PREPARATION_RECEIPTS
                if (folder / name).is_file()
            },
            "protected_sha256": protected,
            "prior_seconds": BASE_SECONDS,
            "prior_acquisitions": BASE_ACQUISITIONS,
            "prior_calls": BASE_CALLS,
            "acquisition_limit": ACQUISITION_LIMIT,
            "call_limit": CALL_LIMIT,
            "time_limit": TIME_LIMIT,
            "new_blind_audit": False,
            "test_evaluated": False,
        }
        body["plan_sha256"] = digest(body)
        save(folder / "plan.json", body)
        save(
            folder / "checkpoint.json",
            {
                "plan_sha256": body["plan_sha256"],
                "entries": [],
                "inferences": [],
                "calls_reserved": 0,
                "elapsed_seconds": BASE_SECONDS,
                "halt_reason": None,
                "images_disposed": False,
            },
        )
        return body


def result_path(folder, sample):
    return folder / "inferences/structured" / sample / "result.json"


def checked_result(folder, plan, row, root):
    path = result_path(folder, row["sample_id"])
    body = json.loads(path.read_bytes())
    cached = cached_result(root, row)
    result = body["vlm"]
    if (
        body["sample_id"] != row["sample_id"]
        or body["recovery_plan_sha256"] != plan["plan_sha256"]
        or body["sealed_plan_sha256"] != plan["sealed_plan_sha256"]
        or body["config_sha256"] != plan["old_config_sha256"]
        or body["sheet_sha256"] != row["sheet_sha256"]
        or result["input_png_sha256"] != cached["input_png_sha256"]
        or result["input_frame_seconds"] != cached["input_frame_seconds"]
    ):
        raise ValueError("recovery_result_identity_changed")
    verify(result, path.parent / "calls")
    if row["sample_id"] == plan["pending_ids"][0]:
        for i in (1, 2, 3):
            relative = f"inferences/structured/{row['sample_id']}/calls/frame-{i}.json"
            if (
                file_hash(path.parent / "calls" / f"frame-{i}.json")
                != plan["partial_call_sha256"][relative]
            ):
                raise ValueError("recovery_inherited_raw_changed")
        call = json.loads((path.parent / "calls/frame-4.json").read_bytes())
        if (
            call.get("recovery_of_sealed_reservation_sha256")
            != plan["partial_call_sha256"][
                f"inferences/structured/{row['sample_id']}/calls/frame-4.json"
            ]
        ):
            raise ValueError("recovery_lost_reservation_link_changed")
    return result


def check_call_ledger(folder, plan, entry, row, root):
    directory = result_path(folder, row["sample_id"]).parent / "calls"
    paths = {p.name: p for p in directory.glob("*.json")}
    first = row["sample_id"] == plan["pending_ids"][0]
    n = entry["call_count"]
    expected_native = {4} if first and n else set() if first else set(range(1, n + 1))
    inherited = {1, 2, 3} if first and n else set()
    allowed = expected_native | inherited
    pending_native = 4 if first else n + 1
    if (
        entry["status"] == "failed"
        and n < (1 if first else 4)
        and f"frame-{pending_native}.json" in paths
    ):
        body = json.loads(paths[f"frame-{pending_native}.json"].read_bytes())
        if (
            body.get("status") == "failed"
            and body.get("error_type") == "UnreservedBudgetStop"
            and "raw_response" not in body
        ):
            allowed.add(pending_native)
    if first and not n:
        # A local copy can itself fail; no native reservation is inferred from it.
        inherited = {i for i in (1, 2, 3) if f"frame-{i}.json" in paths}
        if inherited != set(range(1, len(inherited) + 1)):
            raise ValueError("recovery_inherited_call_prefix_changed")
        allowed |= inherited
    if entry["status"] == "running":
        # An interrupted header before reservation must be audited, never resumed.
        allowed |= {pending_native} if pending_native <= 4 else set()
    if set(paths) != {f"frame-{i}.json" for i in allowed} and not (
        entry["status"] == "running" and set(paths) <= {f"frame-{i}.json" for i in allowed}
    ):
        raise ValueError("recovery_call_receipt_count_changed")
    expected = cached_result(root, row)["input_png_sha256"]
    for name, path in paths.items():
        if path.is_symlink():
            raise ValueError("recovery_call_symlink_forbidden")
        call = json.loads(path.read_bytes())
        i = call["frame"]
        if (
            name != f"frame-{i}.json"
            or type(i) is not int
            or not 1 <= i <= 4
            or call.get("schema_version") != VERSION
            or call.get("variant") != "structured"
            or call.get("input_png_sha256") != expected[i - 1]
            or call.get("specification_sha256") != digest(specification("structured"))
        ):
            raise ValueError("recovery_call_metadata_changed")
        if i in inherited:
            relative = f"inferences/structured/{row['sample_id']}/calls/{name}"
            if file_hash(path) != plan["partial_call_sha256"][relative]:
                raise ValueError("recovery_inherited_raw_changed")
        if (
            first
            and i == 4
            and call.get("recovery_of_sealed_reservation_sha256")
            != plan["partial_call_sha256"][
                f"inferences/structured/{row['sample_id']}/calls/frame-4.json"
            ]
        ):
            raise ValueError("recovery_lost_reservation_link_changed")
        if (
            "raw_response" in call
            and type(call["raw_response"]) is str
            and (
                call.get("raw_response_sha256")
                != hashlib.sha256(call["raw_response"].encode()).hexdigest()
            )
        ):
            raise ValueError("recovery_call_raw_hash_changed")
        if call.get("status") == "completed":
            parsed, _ = decode(call["raw_response"], "structured")
            if call.get("parsed") != parsed:
                raise ValueError("recovery_call_parse_changed")
        elif entry["status"] == "completed" or call.get("status") not in (
            "running",
            "failed",
            "response_captured",
        ):
            raise ValueError("recovery_call_status_changed")


def load(parent, cohort, folder, root):
    plan = json.loads((folder / "plan.json").read_bytes())
    state = json.loads((folder / "checkpoint.json").read_bytes())
    if (
        plan["plan_sha256"] != digest({k: v for k, v in plan.items() if k != "plan_sha256"})
        or (plan["configuration"] != configuration())
        or plan["preparation_sha256"]
        != {
            name: file_hash(folder / name)
            for name in PREPARATION_RECEIPTS
            if (folder / name).is_file()
        }
    ):
        raise ValueError("recovery_plan_or_source_changed")
    for path, sha in plan["protected_sha256"].items():
        if file_hash(root / path) != sha:
            raise ValueError("recovery_protected_file_changed")
    sealed = root / plan["sealed_folder"]
    old, old_state = load_original(parent, cohort, sealed, root)
    if (
        plan["protocol"] != "product-v9-explicit-recovery-v1"
        or plan["new_blind_audit"] is not False
        or plan["test_evaluated"] is not False
        or plan["protected_sha256"] != sealed_pins(sealed, root)
        or plan["pilot_ids"] != old["pilot_ids"]
        or plan["old_config_sha256"] != digest(old["config"])
        or plan["inherited_result_sha256"]
        != {
            e["sample_id"]: e["result_sha256"]
            for e in old_state["inferences"]
            if e["status"] == "completed"
        }
        or plan["partial_call_sha256"]
        != partial_calls(
            sealed,
            plan["pending_ids"][0],
            cached_result(root, evaluation_rows(old, True)[33])["input_png_sha256"],
        )
        or plan["rows"] != old["rows"]
        or plan["annotations"] != old["annotations"]
        or plan["sealed_plan_sha256"] != old["plan_sha256"]
        or plan["pending_ids"] != [r["sample_id"] for r in evaluation_rows(old, True)[33:]]
        or old_state["halt_reason"] != "product_report_sealed"
        or (
            plan["prior_seconds"],
            plan["prior_acquisitions"],
            plan["prior_calls"],
            plan["acquisition_limit"],
            plan["call_limit"],
            plan["time_limit"],
        )
        != (BASE_SECONDS, BASE_ACQUISITIONS, BASE_CALLS, ACQUISITION_LIMIT, CALL_LIMIT, TIME_LIMIT)
        or state["plan_sha256"] != plan["plan_sha256"]
    ):
        raise ValueError("recovery_scope_or_budget_changed")
    calls, elapsed = 0, BASE_SECONDS
    by_id = {r["sample_id"]: r for r in plan["rows"]}
    acquired = {e["sample_id"] for e in state["entries"] if e["status"] == "completed"}
    if any(e["sample_id"] not in acquired for e in state["inferences"]):
        raise ValueError("recovery_inference_without_completed_acquisition")
    for field in ("entries", "inferences"):
        entries = state[field]
        if [e["sample_id"] for e in entries] != plan["pending_ids"][: len(entries)]:
            raise ValueError("recovery_order_or_duplicate_changed")
        if len(entries) > 31:
            raise ValueError("recovery_budget_exhausted")
        for e in entries:
            if e["status"] not in ("running", "completed", "failed") or (
                type(e["seconds"]) not in (int, float)
                or not math.isfinite(e["seconds"])
                or e["seconds"] < 0
            ):
                raise ValueError("recovery_invalid_ledger")
            elapsed += e["seconds"]
            if field == "entries" and e["status"] in ("completed", "failed"):
                run = folder / "sessions" / e["sample_id"] / "run.json"
                if e.get("run_receipt_missing") is True:
                    if run.exists() or e["status"] == "completed":
                        raise ValueError("recovery_terminal_run_changed")
                elif not run.is_file() or file_hash(run) != e.get("run_sha256"):
                    raise ValueError("recovery_terminal_run_changed")
            if field == "entries" and e["status"] == "completed":
                session = folder / "sessions" / e["sample_id"]
                if {n: file_hash(session / n) for n in ("features.json", "run.json")} != e[
                    "files_sha256"
                ]:
                    raise ValueError("recovery_acquisition_changed")
                checked_identity(folder, by_id[e["sample_id"]], root)
            if field == "inferences":
                expected = 1 if e["sample_id"] == plan["pending_ids"][0] else 4
                if (
                    type(e["call_count"]) is not int
                    or not 0 <= e["call_count"] <= expected
                    or (e["status"] == "completed" and e["call_count"] != expected)
                ):
                    raise ValueError("recovery_call_count_changed")
                calls += e["call_count"]
                check_call_ledger(folder, plan, e, by_id[e["sample_id"]], root)
                if e["status"] == "completed":
                    path = result_path(folder, e["sample_id"])
                    if file_hash(path) != e["result_sha256"]:
                        raise ValueError("recovery_result_changed")
                    checked_result(folder, plan, by_id[e["sample_id"]], root)
    if (
        type(state["calls_reserved"]) is not int
        or calls != state["calls_reserved"]
        or calls > CALL_LIMIT
        or not math.isclose(elapsed, state["elapsed_seconds"], rel_tol=0, abs_tol=1e-8)
    ):
        raise ValueError("recovery_cumulative_budget_changed")
    for key, name in (
        ("comparison_file_sha256", "comparison.json"),
        ("disposal_sha256", "image-disposal.json"),
    ):
        if key in state and file_hash(folder / name) != state[key]:
            raise ValueError("recovery_terminal_receipt_changed")
    validate_terminal(plan, state, folder, root)
    return plan, state


def validate_terminal(plan, state, folder, root):
    if (state["halt_reason"] == "recovery_report_sealed" or state["images_disposed"]) and (
        "comparison_file_sha256" not in state or state["halt_reason"] != "recovery_report_sealed"
    ):
        raise ValueError("recovery_terminal_receipt_changed")
    if "comparison_file_sha256" in state:
        report = json.loads((folder / "comparison.json").read_bytes())
        expected = {
            s: {
                "path": str(result_path(root / plan["sealed_folder"], s).relative_to(root)),
                "sha256": h,
            }
            for s, h in plan["inherited_result_sha256"].items()
        }
        expected.update(
            {
                e["sample_id"]: {
                    "path": str(result_path(folder, e["sample_id"]).relative_to(root)),
                    "sha256": e["result_sha256"],
                }
                for e in state["inferences"]
                if e["status"] == "completed"
            }
        )
        if (
            report.get("comparison_sha256")
            != digest({k: v for k, v in report.items() if k != "comparison_sha256"})
            or report.get("recovery_plan_sha256") != plan["plan_sha256"]
            or report.get("sealed_plan_sha256") != plan["sealed_plan_sha256"]
            or report.get("result_sha256") != expected
            or report.get("evaluated_cases") != len(expected)
            or report.get("new_acquisitions") != len(state["entries"])
            or report.get("new_native_reservations") != state["calls_reserved"]
            or report.get("released_fields") != []
            or any(
                report.get(k) is not False
                for k in (
                    "new_blind_audit",
                    "predictive_training_started",
                    "test_evaluated",
                    "m1_replaced",
                )
            )
        ):
            raise ValueError("recovery_comparison_evidence_changed")
    rows = {r["sample_id"]: r for r in plan["rows"]}
    attempted = {e["sample_id"] for e in state["entries"]}
    completed = {e["sample_id"] for e in state["entries"] if e["status"] == "completed"}
    pending = state.get("cleanup_pending")
    if "disposal_sha256" in state:
        receipt = json.loads((folder / "image-disposal.json").read_bytes())
        images = receipt.get("images", {})
        if (
            type(images) is not dict
            or not completed <= set(images) <= attempted
            or any(sha != rows[s]["sheet_sha256"] for s, sha in images.items())
            or receipt
            != {
                "plan_sha256": plan["plan_sha256"],
                "comparison_file_sha256": state["comparison_file_sha256"],
                "images": images,
            }
            or type(pending) is not list
            or len(pending) != len(set(pending))
            or not set(pending) <= set(images)
            or (state["images_disposed"] and pending)
            or state["halt_reason"] != "recovery_report_sealed"
        ):
            raise ValueError("recovery_disposal_evidence_changed")
    elif pending is not None or state["images_disposed"]:
        raise ValueError("recovery_disposal_evidence_changed")
    else:
        images = {s: rows[s]["sheet_sha256"] for s in completed}
    for sample, sha in images.items():
        path = folder / "images" / (sample + ".png")
        if pending is None:
            if file_hash(path) != sha:
                raise ValueError("recovery_sheet_changed")
        elif path.exists() and (sample not in pending or file_hash(path) != sha):
            raise ValueError("recovery_disposal_evidence_changed")
    actual = {p.stem for p in (folder / "images").glob("*.png")}
    if not actual <= attempted or state["images_disposed"] and actual:
        raise ValueError("recovery_unexpected_images_require_audit")


def runnable(state):
    if state["halt_reason"] or state["images_disposed"]:
        raise ValueError("recovery_halted_no_automatic_retry")
    if any(e["status"] != "completed" for e in [*state["entries"], *state["inferences"]]):
        raise ValueError("recovery_interrupted_requires_audit")
    if state["elapsed_seconds"] >= TIME_LIMIT:
        raise ValueError("recovery_time_budget_exhausted")


def persist(folder, state, entry, started, clock):
    entry["seconds"] = clock() - started
    state["elapsed_seconds"] = BASE_SECONDS + sum(
        e["seconds"] for e in [*state["entries"], *state["inferences"]]
    )
    save(folder / "checkpoint.json", state)

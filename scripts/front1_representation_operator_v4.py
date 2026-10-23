"""Finite representation candidate; fresh authority, original development gates, no release."""

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/home/inteli/Documents/projetos/Galaxies-Inteli-Academy")
NAMESPACE = "fechamento-20261023/frente-1/representation-product-panel-v4-r2"
FOLDER = ROOT / "data/private" / NAMESPACE
sys.path.insert(0, str(ROOT))
from scripts import visual_validation_batch_v1 as batch
from scripts import visual_validation_capture_v1 as capture
from scripts import vlm_native225_probe_v2 as native
from scripts import vlm_product_v16 as product
from scripts.visual_validation_contract_v1 import digest, read_json, require, write_new
from scripts.vlm_native_contrast_v2 import _DeadlineProcess

batch.NAMESPACE = capture.NAMESPACE = NAMESPACE
EXECUTION_ENVELOPE = {
    "tool": "exec_command",
    "sandbox_permissions": "require_escalated",
    "inner_capsule": "reviewed_bwrap_unchanged",
    "fallback_allowed": False,
    "system_security_changes_allowed": False,
}
MODULE = FOLDER / "control_worker.py"
OLD = ROOT / "data/private/issue-4-visual-validation-run-v2/control_operator.py"
spec = importlib.util.spec_from_file_location("reviewed_process_owner", OLD)
owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner)
owner.FOLDER = FOLDER
panel_spec = importlib.util.spec_from_file_location(
    "front1_frozen_representation_panel", Path(__file__).with_name("front1_representation_v4.py")
)
panel = importlib.util.module_from_spec(panel_spec)
panel_spec.loader.exec_module(panel)
batch.NAMESPACE = capture.NAMESPACE = NAMESPACE


def sha(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def verify(*, external_attempt=True):
    plan = read_json(FOLDER / "plan.json")
    require(
        digest({k: v for k, v in plan.items() if k != "plan_sha256"}) == plan["plan_sha256"],
        "plan_changed",
    )
    grant = read_json(FOLDER / "authorization.json")
    review = read_json(FOLDER / "review.json")
    slot = read_json(FOLDER / "resource-slot.json")
    require(
        grant["decision"] == "authorize_exact_representation_v4_panel_once"
        and grant["plan_sha256"]
        == review["plan_sha256"]
        == slot["plan_sha256"]
        == plan["plan_sha256"]
        and grant["proposal_sha256"] == plan["proposal_sha256"]
        and grant["calls_max"] == panel.CALLS_MAX
        and grant["retry_allowed"] is False
        and grant["cost_brl_max"] == 0
        and grant["renewed_panel_sha256"] == plan["panel_sha256"]
        and grant["issued_epoch"] > plan["prepared_epoch"]
        and hashlib.sha256(grant["human_message"].encode()).hexdigest()
        == grant["human_message_sha256"]
        and grant["authorization_id"] not in plan["consumed_authorization_ids"],
        "new_exact_one_call_human_authorization_required",
    )
    require(
        review["decision"] == "reviewed_exact_representation_v4_operator_and_authorization"
        and review["authorization_file_sha256"] == sha(FOLDER / "authorization.json")
        and review["operator_sha256"] == sha(MODULE)
        and review["human_origin_independently_checked"] is True
        and review["source_message_id"] != grant["authorization_id"],
        "independent_review_required",
    )
    require(
        slot["decision"] == "exclusive_visual_cpu4_slot"
        and slot["source_thread_id"] == "01a1467e-5da5-7a41-8b43-bfa0da1917f8",
        "coordinator_resource_slot_required",
    )
    require(
        plan["execution_envelope"]
        == grant["execution_envelope"]
        == review["execution_envelope"]
        == slot["execution_envelope"]
        == EXECUTION_ENVELOPE,
        "exact_external_envelope_authority_required",
    )
    require(capsule() == plan["capsule_argv"], "reviewed_inner_capsule_changed")
    deadline = min(grant["expires_epoch"], slot["expires_epoch"])
    require(
        time.time() < deadline and grant["issued_epoch"] <= time.time(), "new_authority_expired"
    )
    require(
        plan["calls_max"] == panel.CALLS_MAX
        and plan["run_seconds_max"] == panel.RUN_SECONDS
        and plan["call_seconds_max"] == panel.CALL_SECONDS
        and plan["panel_sha256"] == digest(plan["cases"]),
        "fixed_development_panel_limits",
    )
    panel.validate_panel(plan["cases"])
    require(
        all(row["expected_tokens"] == panel.EXPECTED_TOKENS for row in plan["cases"]),
        "fixed_spatial_tokens",
    )
    for name, wanted in plan["source_sha256"].items():
        require(sha(ROOT / name) == wanted, "source_changed")
    for name, wanted in plan["predecessor_sha256"].items():
        require(sha(ROOT / name) == wanted, "sealed_predecessor_changed")
    for name, reference in plan["asset_references"].items():
        require(native._asset_reference(name) == reference, "asset_reference_changed")
    for name, fingerprint in plan["asset_fingerprints"].items():
        require(list(native._fingerprint(name)) == fingerprint, "asset_changed")
    for name, wanted in plan["protected_sheet_sha256"].items():
        require(sha(name) == wanted, "protected_sheet_changed")
    if external_attempt:
        attempt = read_json(FOLDER / "external-attempt.json")
        require(
            attempt["plan_sha256"] == plan["plan_sha256"]
            and attempt["authorization_file_sha256"] == sha(FOLDER / "authorization.json")
            and attempt["resource_slot_file_sha256"] == sha(FOLDER / "resource-slot.json")
            and attempt["tool_requests_sha256"] == digest(plan["external_tool_requests"])
            and attempt["execution_envelope"] == EXECUTION_ENVELOPE,
            "fresh_external_attempt_binding_required",
        )
    return plan | {
        "global_deadline_epoch": deadline,
        "authorization_id": grant["authorization_id"],
        "authorization_file_sha256": sha(FOLDER / "authorization.json"),
        "resource_slot_file_sha256": sha(FOLDER / "resource-slot.json"),
    }


def reserve_external_attempt():
    """Caller latch before asking the tool to execute; denial consumes this round too."""
    plan = verify(external_attempt=False)
    require(
        time.time() + panel.RUN_SECONDS <= plan["global_deadline_epoch"],
        "full_panel_authority_window_required",
    )
    write_new(
        FOLDER / "external-attempt.json",
        {
            "schema": "front1-external-attempt-v4",
            "plan_sha256": plan["plan_sha256"],
            "authorization_file_sha256": plan["authorization_file_sha256"],
            "resource_slot_file_sha256": plan["resource_slot_file_sha256"],
            "tool_requests_sha256": digest(plan["external_tool_requests"]),
            "execution_envelope": EXECUTION_ENVELOPE,
            "reserved_epoch": time.time(),
            "preflight_max": 1,
            "model_calls_max": panel.CALLS_MAX,
            "retry_allowed": False,
        },
    )


def capsule():
    return owner.capsule()


def actual_argv():
    return [a.decode() for a in Path("/proc/self/cmdline").read_bytes().split(b"\0") if a]


def reserve_preflight(plan):
    """Exclusive durable latch before any child; failures cannot reset its clock."""
    started = time.time()
    deadline = min(started + panel.RUN_SECONDS, plan["global_deadline_epoch"])
    require(started + 88 <= deadline, "insufficient_preflight_and_dispatch_budget")
    value = {
        "schema": "front1-representation-preflight-reservation-v4",
        "plan_sha256": plan["plan_sha256"],
        "authorization_file_sha256": plan["authorization_file_sha256"],
        "resource_slot_file_sha256": plan["resource_slot_file_sha256"],
        "started_epoch": started,
        "deadline_epoch": deadline,
        "operator_identity": owner.supervisor.proc_identity(os.getpid()),
        "model_calls_reserved": 0,
        "preflight_attempts_reserved": 1,
    }
    write_new(FOLDER / "preflight-reservation.json", value)
    return value


def configuration(plan, row, scratch):
    query = product.specification("state_first")
    require(
        hashlib.sha256(query["prompt"].encode()).hexdigest() == plan["prompt_sha256"],
        "candidate_prompt",
    )
    require(product.ordered_schema_hash(query["schema"]) == plan["schema_sha256"], "schema_order")
    argv = list(plan["runtime_template"])
    for flag in ("--image-min-tokens", "--image-max-tokens"):
        require(
            argv.count(flag) == 1 and argv[argv.index(flag) + 1] == "1024",
            "fixed_spatial_budget",
        )
    for flag, value in [
        ("--image", row["path"]),
        ("--json-schema-file", str(scratch / "schema.json")),
        ("--prompt", query["prompt"]),
    ]:
        require(argv.count(flag) == 1, "single_flag")
        argv[argv.index(flag) + 1] = value
    require(argv == plan["effective_model_argvs"][row["call_id"] - 1], "fixed_model_argv")
    return query, argv


def worker(index):
    plan = verify()
    require(type(index) is int and 1 <= index <= panel.CALLS_MAX, "fixed_call_index")
    native.capsule_preflight()
    state = read_json(FOLDER / "ledger.json")
    require(
        not state["sealed"] and state["pending"] == index and state["calls_reserved"] == index,
        "reserved_next_call_only",
    )
    identity = owner.supervisor.proc_identity(state["operator_identity"]["pid"])
    require(
        identity is not None
        and identity["start_ticks"] == state["operator_identity"]["start_ticks"]
        and identity["pid"] != os.getpid(),
        "watchdog_required",
    )
    args = [
        a.decode()
        for a in (Path("/proc") / str(identity["pid"]) / "cmdline").read_bytes().split(b"\0")
        if a
    ]
    require(args == plan["launch_argv"], "absolute_live_operator")
    deadline = min(
        state["dispatch_deadline_epoch"],
        state["run_deadline_epoch"],
        plan["global_deadline_epoch"],
    )
    require(time.time() < deadline, "dispatch_deadline")
    row = plan["cases"][index - 1]
    reserved = read_json(FOLDER / f"call-reservation-{index:04d}.json")
    require(
        reserved["call_id"] == index
        and reserved["plan_sha256"] == plan["plan_sha256"]
        and reserved["png_sha256"] == row["png_sha256"],
        "durable_call_reservation_required",
    )
    scratch = FOLDER / "scratch" / f"call-{index:04d}"
    query, argv = configuration(plan, row, scratch)
    scratch.mkdir(mode=0o700, parents=True, exist_ok=False)
    batch.write_runtime_schema(scratch / "schema.json", query["schema"])
    require(row["path"] == str(scratch / "input.png"), "owned_input_path")
    with Path(row["path"]).open("xb") as handle:
        handle.write(panel.input_bytes(row))
    Path(row["path"]).chmod(0o600)

    def bind():
        verify()
        require(
            native.available_memory() >= 6 * 1024**3 and time.time() < deadline - 5,
            "memory_or_deadline",
        )
        require(sha(row["path"]) == row["png_sha256"], "input_changed_before_spawn")
        for name, reference in plan["asset_references"].items():
            require(native._asset_reference(name) == reference, "asset_reference_changed")
        for name, fingerprint in plan["asset_fingerprints"].items():
            require(list(native._fingerprint(name)) == fingerprint, "asset_changed")
        current = read_json(FOLDER / "ledger.json")
        require(current["pending"] == index and not current["sealed"], "consumed_or_stopped")

    def reserve():
        bind()
        write_new(
            FOLDER / f"dispatch-{index:04d}.json",
            {
                "call_id": index,
                "epoch": time.time(),
                "plan_sha256": plan["plan_sha256"],
                "png_sha256": row["png_sha256"],
            },
        )

    def launch(*args, **kwargs):
        bind()
        require(
            args == (argv,) and (FOLDER / f"dispatch-{index:04d}.json").is_file(),
            "reserved_exact_argv",
        )
        return _DeadlineProcess(
            subprocess.Popen(*args, **kwargs),
            time.monotonic() + max(0, deadline - time.time() - 5),
        )

    result = capture._capture_invented(
        argv,
        root=ROOT,
        call_id=index,
        kind="product_visible_early",
        png_sha256=row["png_sha256"],
        expected_tokens=panel.EXPECTED_TOKENS,
        reserve=reserve,
        launcher=launch,
        seconds=min(75, deadline - time.time() - 5),
    )
    bound = capture.read_capture(
        ROOT,
        index,
        kind="product_visible_early",
        png_sha256=row["png_sha256"],
        expected_tokens=panel.EXPECTED_TOKENS,
    )
    parsed = result["parsed_response"]
    accepted = panel.accepted_case(row, parsed, result["technical_success"])
    receipt = {
        "call_id": index,
        "accepted": bool(accepted),
        "expected_value": row["expected_value"],
        "value": None if parsed is None else parsed["value"],
        "native": None if parsed is None else parsed["native"],
        "technical_success": result["technical_success"],
        "cleanup_confirmed": result["cleanup_confirmed"],
        "image_tokens_observed": result["image_tokens_observed"],
        "runtime_seconds": result["runtime_seconds"],
        "peak_rss_mib": result["peak_rss_mib"],
        "stop_code": result["stop_code"],
        "capture_result_sha256": bound["result_sha256"],
        "plan_sha256": plan["plan_sha256"],
    }
    write_new(FOLDER / f"receipt-{index:04d}.json", receipt)
    if result["cleanup_confirmed"]:
        shutil.rmtree(scratch)
    print(json.dumps(receipt), flush=True)
    return 0 if result["technical_success"] and result["cleanup_confirmed"] else 2


def operator(preflight=False):
    plan = verify()
    actual = actual_argv()
    require(
        actual == plan["launch_argv"] + (["--preflight-only"] if preflight else []),
        "exact_absolute_launch",
    )
    require(not (FOLDER / "started.json").exists(), "one_call_round_already_consumed")
    if preflight:
        require(not (FOLDER / "preflight.json").exists(), "preflight_already_attempted")
        require(
            native.available_memory() >= 6 * 1024**3 and not capture.owner.workers(),
            "memory_or_other_worker",
        )
        require(shutil.disk_usage(FOLDER).free >= 1024**3, "disk_minimum")
        reserve_preflight(plan)
        code = "import json;from scripts.vlm_native225_probe_v2 import capsule_preflight;capsule_preflight();print(json.dumps({'model_calls':0,'network_isolated':True,'devnull':True}))"
        result = owner.owned_run(
            capsule() + ["-c", code], cwd=ROOT, env={"PATH": "/usr/bin:/bin"}, seconds=8
        )
        write_new(
            FOLDER / "preflight.json",
            result | {"preflight_reservation_sha256": sha(FOLDER / "preflight-reservation.json")},
        )
        require(
            result["code"] == "completed"
            and result["returncode"] == 0
            and result["cleanup_confirmed"],
            "no_model_preflight_failed",
        )
        return 0
    preflight = read_json(FOLDER / "preflight.json")
    reservation = read_json(FOLDER / "preflight-reservation.json")
    require(
        preflight["code"] == "completed"
        and preflight["returncode"] == 0
        and preflight["cleanup_confirmed"],
        "no_model_preflight_required",
    )
    require(
        preflight["preflight_reservation_sha256"] == sha(FOLDER / "preflight-reservation.json")
        and reservation["plan_sha256"] == plan["plan_sha256"]
        and reservation["authorization_file_sha256"] == plan["authorization_file_sha256"]
        and reservation["resource_slot_file_sha256"] == plan["resource_slot_file_sha256"]
        and reservation["preflight_attempts_reserved"] == 1,
        "first_preflight_reservation_binding_required",
    )
    require(
        native.available_memory() >= 6 * 1024**3 and not capture.owner.workers(),
        "memory_or_other_worker",
    )
    require(shutil.disk_usage(FOLDER).free >= 1024**3, "disk_minimum")
    start = time.time()
    require(reservation["started_epoch"] <= start, "preflight_clock_invalid")
    deadline = min(reservation["deadline_epoch"], plan["global_deadline_epoch"])
    require(time.time() + 80 <= deadline, "insufficient_global_budget")
    write_new(
        FOLDER / "started.json",
        {
            "started_epoch": start,
            "deadline_epoch": deadline,
            "authorization_id": plan["authorization_id"],
            "plan_sha256": plan["plan_sha256"],
        },
    )
    state = {
        "calls_reserved": 0,
        "pending": None,
        "sealed": False,
        "run_deadline_epoch": deadline,
        "dispatch_deadline_epoch": None,
        "operator_identity": owner.supervisor.proc_identity(os.getpid()),
    }
    write_new(FOLDER / "ledger.json", state)
    status = "technical_or_uncertain_failure"
    receipts = []
    try:
        for index, row in enumerate(plan["cases"], 1):
            status = "technical_or_uncertain_failure"
            verify()
            require(
                native.available_memory() >= 6 * 1024**3 and not capture.owner.workers(),
                "memory_or_other_worker",
            )
            require(shutil.disk_usage(FOLDER).free >= 1024**3, "disk_minimum")
            if time.time() + panel.CALL_SECONDS > deadline:
                status = "global_budget_exhausted"
                break
            write_new(
                FOLDER / f"call-reservation-{index:04d}.json",
                {
                    "call_id": index,
                    "plan_sha256": plan["plan_sha256"],
                    "png_sha256": row["png_sha256"],
                    "epoch": time.time(),
                },
            )
            state.update(
                calls_reserved=index,
                pending=index,
                dispatch_deadline_epoch=min(time.time() + panel.CALL_SECONDS, deadline),
            )
            capture.owner.write(FOLDER / "ledger.json", state)
            result = owner.owned_run(
                capsule() + [str(MODULE), "--call", str(index)],
                cwd=ROOT,
                env={"PATH": "/usr/bin:/bin"},
                seconds=panel.CALL_SECONDS,
            )
            write_new(FOLDER / f"operator-result-{index:04d}.json", result)
            require(
                result["code"] == "completed"
                and result["returncode"] == 0
                and result["cleanup_confirmed"]
                and result["seconds"] <= panel.CALL_SECONDS,
                "owned_call_failed",
            )
            receipt = read_json(FOLDER / f"receipt-{index:04d}.json")
            require(
                receipt["technical_success"] and receipt["cleanup_confirmed"],
                "capture_or_cleanup_failed",
            )
            require(json.loads(result["stdout"]) == receipt, "owned_receipt_binding")
            receipts.append(receipt)
            state["pending"] = None
            capture.owner.write(FOLDER / "ledger.json", state)
            status = panel.classify_case(row, receipt)
            if status != "accepted_development_case":
                break
        if len(receipts) == panel.CALLS_MAX:
            status = panel.panel_outcome(plan["cases"], receipts)["status"]
    finally:
        pending = state["pending"]
        if pending is not None:
            receipt_path = FOLDER / f"receipt-{pending:04d}.json"
            owned_path = FOLDER / f"operator-result-{pending:04d}.json"
            if (
                receipt_path.is_file()
                and owned_path.is_file()
                and read_json(receipt_path).get("cleanup_confirmed") is True
                and read_json(owned_path).get("cleanup_confirmed") is True
            ):
                state["pending"] = None
        state.update(sealed=True, status=status)
        capture.owner.write(FOLDER / "ledger.json", state)
        if state["pending"] is None:
            scratch = FOLDER / "scratch"
            if scratch.is_dir() and not any(scratch.iterdir()):
                scratch.rmdir()
        write_new(
            FOLDER / "terminal.json",
            {
                "status": status,
                "calls_reserved": state["calls_reserved"],
                "completed_receipts": len(receipts),
                "pending": state["pending"],
                "seconds_since_preflight_reservation": time.time() - reservation["started_epoch"],
                "retry_allowed": False,
                "quality_release": False,
                "audit_released": False,
                "B_C_released": False,
                "cost_brl": 0,
            },
        )
    return 0 if status == "development_panel_passed_only" else 2


if __name__ == "__main__":
    if sys.argv[1:] == ["--preflight-only"]:
        raise SystemExit(operator(True))
    if len(sys.argv) == 3 and sys.argv[1] == "--call" and sys.argv[2].isdigit():
        raise SystemExit(worker(int(sys.argv[2])))
    require(not sys.argv[1:], "fixed_arguments_only")
    raise SystemExit(operator())

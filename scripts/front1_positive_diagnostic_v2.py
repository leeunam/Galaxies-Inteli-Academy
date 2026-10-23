"""One missing positive cell; no dispatch without new authority and resource receipts."""

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
NAMESPACE = "fechamento-20261023/frente-1/diagnostic-old-prompt-positive-v2"
FOLDER = ROOT / "data/private" / NAMESPACE
sys.path.insert(0, str(ROOT))
from scripts import visual_validation_batch_v1 as batch
from scripts import visual_validation_capture_v1 as capture
from scripts import vlm_native225_probe_v2 as native
from scripts import vlm_product_v16 as product
from scripts.visual_validation_contract_v1 import digest, read_json, require, write_new
from scripts.vlm_native_contrast_v2 import _DeadlineProcess

batch.NAMESPACE = capture.NAMESPACE = NAMESPACE
MODULE = FOLDER / "control_worker.py"
OLD = ROOT / "data/private/issue-4-visual-validation-run-v2/control_operator.py"
spec = importlib.util.spec_from_file_location("reviewed_process_owner", OLD)
owner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(owner)
owner.FOLDER = FOLDER
batch.NAMESPACE = capture.NAMESPACE = NAMESPACE


def sha(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def verify():
    plan = read_json(FOLDER / "plan.json")
    require(
        digest({k: v for k, v in plan.items() if k != "plan_sha256"}) == plan["plan_sha256"],
        "plan_changed",
    )
    grant = read_json(FOLDER / "authorization.json")
    review = read_json(FOLDER / "review.json")
    slot = read_json(FOLDER / "resource-slot.json")
    require(
        grant["decision"] == "authorize_exact_old_prompt_positive_v2_once"
        and grant["plan_sha256"]
        == review["plan_sha256"]
        == slot["plan_sha256"]
        == plan["plan_sha256"]
        and grant["proposal_sha256"] == plan["proposal_sha256"]
        and grant["calls_max"] == 1
        and grant["retry_allowed"] is False
        and grant["cost_brl_max"] == 0
        and grant["renewed_png_sha256"] == plan["cases"][0]["png_sha256"]
        and grant["issued_epoch"] > plan["prepared_epoch"]
        and hashlib.sha256(grant["human_message"].encode()).hexdigest()
        == grant["human_message_sha256"]
        and grant["authorization_id"] not in plan["consumed_authorization_ids"],
        "new_exact_one_call_human_authorization_required",
    )
    require(
        review["decision"] == "reviewed_exact_old_prompt_positive_v2_operator_and_authorization"
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
    deadline = min(grant["expires_epoch"], slot["expires_epoch"])
    require(
        time.time() < deadline and grant["issued_epoch"] <= time.time(), "new_authority_expired"
    )
    require(
        plan["calls_max"] == 1
        and plan["run_seconds_max"] == 120
        and plan["call_seconds_max"] == 80
        and len(plan["cases"]) == 1,
        "fixed_one_cell_limits",
    )
    for name, wanted in plan["source_sha256"].items():
        require(sha(ROOT / name) == wanted, "source_changed")
    for name, wanted in plan["predecessor_sha256"].items():
        require(sha(ROOT / name) == wanted, "sealed_predecessor_changed")
    for name, reference in plan["asset_references"].items():
        require(native._asset_reference(name) == reference, "asset_reference_changed")
    for name, fingerprint in plan["asset_fingerprints"].items():
        require(list(native._fingerprint(name)) == fingerprint, "asset_changed")
    require(sha(plan["cases"][0]["path"]) == plan["cases"][0]["png_sha256"], "image_changed")
    require(
        sha(plan["positive_sheet_path"]) == plan["positive_sheet_sha256"], "protected_sheet_changed"
    )
    return plan | {
        "global_deadline_epoch": deadline,
        "authorization_id": grant["authorization_id"],
        "authorization_file_sha256": sha(FOLDER / "authorization.json"),
        "resource_slot_file_sha256": sha(FOLDER / "resource-slot.json"),
    }


def capsule():
    return owner.capsule()


def actual_argv():
    return [a.decode() for a in Path("/proc/self/cmdline").read_bytes().split(b"\0") if a]


def reserve_preflight(plan):
    """Exclusive durable latch before any child; failures cannot reset its clock."""
    started = time.time()
    deadline = min(started + 120, plan["global_deadline_epoch"])
    require(started + 88 <= deadline, "insufficient_preflight_and_dispatch_budget")
    value = {
        "schema": "front1-one-positive-preflight-reservation-v2",
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
    for flag, value in [
        ("--image", row["path"]),
        ("--json-schema-file", str(scratch / "schema.json")),
        ("--prompt", query["prompt"]),
    ]:
        require(argv.count(flag) == 1, "single_flag")
        argv[argv.index(flag) + 1] = value
    require(argv == plan["effective_model_argv"], "fixed_model_argv")
    return query, argv


def worker(index):
    plan = verify()
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
    scratch = FOLDER / "scratch" / f"call-{index:04d}"
    query, argv = configuration(plan, row, scratch)
    scratch.mkdir(mode=0o700, parents=True, exist_ok=False)
    batch.write_runtime_schema(scratch / "schema.json", query["schema"])

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
        expected_tokens=240,
        reserve=reserve,
        launcher=launch,
        seconds=min(75, deadline - time.time() - 5),
    )
    bound = capture.read_capture(
        ROOT,
        index,
        kind="product_visible_early",
        png_sha256=row["png_sha256"],
        expected_tokens=240,
    )
    parsed = result["parsed_response"]
    accepted = result["technical_success"] and parsed["value"] is row["expected_value"]
    if index == 1:
        accepted = (
            accepted
            and parsed["native"]["presented_categories"] == ["garment"]
            and parsed["native"]["item_configuration"] in row["admissible_configurations"]
        )
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
    return 0 if accepted else 2


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
        "calls_reserved": 1,
        "pending": 1,
        "sealed": False,
        "run_deadline_epoch": deadline,
        "dispatch_deadline_epoch": min(start + 80, deadline),
        "operator_identity": owner.supervisor.proc_identity(os.getpid()),
    }
    write_new(FOLDER / "ledger.json", state)
    status = "technical_or_uncertain_failure"
    try:
        result = owner.owned_run(
            capsule() + [str(MODULE), "--call", "1"],
            cwd=ROOT,
            env={"PATH": "/usr/bin:/bin"},
            seconds=80,
        )
        write_new(FOLDER / "operator-result-0001.json", result)
        require(
            result["code"] == "completed"
            and result["cleanup_confirmed"]
            and result["seconds"] <= 80,
            "owned_call_failed",
        )
        receipt = read_json(FOLDER / "receipt-0001.json")
        require(
            receipt["technical_success"] and receipt["cleanup_confirmed"],
            "capture_or_cleanup_failed",
        )
        status = (
            "supported_true_diagnostic_only"
            if receipt["accepted"]
            else (
                "abstention_diagnostic_only"
                if receipt["value"] == "unknown"
                else (
                    "unsupported_true_diagnostic_only"
                    if receipt["value"] is True
                    else "false_negative_diagnostic_only"
                )
            )
        )
    finally:
        receipt_path = FOLDER / "receipt-0001.json"
        if receipt_path.is_file() and read_json(receipt_path).get("cleanup_confirmed") is True:
            state["pending"] = None
        state.update(sealed=True, status=status)
        capture.owner.write(FOLDER / "ledger.json", state)
        write_new(
            FOLDER / "terminal.json",
            {
                "status": status,
                "calls_reserved": 1,
                "pending": state["pending"],
                "seconds": time.time() - start,
                "retry_allowed": False,
                "audit_released": False,
                "B_C_released": False,
                "cost_brl": 0,
            },
        )
    return 0 if status == "supported_true_diagnostic_only" else 2


if __name__ == "__main__":
    if sys.argv[1:] == ["--preflight-only"]:
        raise SystemExit(operator(True))
    if sys.argv[1:] == ["--call", "1"]:
        raise SystemExit(worker(1))
    require(not sys.argv[1:], "fixed_arguments_only")
    raise SystemExit(operator())

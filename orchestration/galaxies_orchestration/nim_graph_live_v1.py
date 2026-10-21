"""One reviewed live call IN the existing compiled select node; no replay route."""

import argparse
import asyncio
import json
import os
import time
import uuid
from pathlib import Path

from . import nim_graph_live_contract_v1 as contract
from .integrated_graph_v2 import build_graph
from .nim_graph_contract_v1 import CASES, ROOT, canonical, digest, fixture
from .nim_graph_v1 import ProbeWorker, RootSelector

TRANSPORT_CODES = {
    "selection_accepted",
    "selection_rejected",
    "request_failed_outcome_uncertain",
    "protocol_rejected",
    "invalid_http_status",
    "http_error",
    "response_read_failed",
    "invalid_wire_type",
    "wire_byte_limit",
    "invalid_wire_unicode",
    "envelope_duplicate_key",
    "envelope_depth_limit",
    "envelope_json_syntax",
    "envelope_schema_invalid",
    "invalid_unicode",
    "response_byte_limit",
}


def provider_proof(proof, result, bound, folder, nonce, *, offline, calls):
    if not offline and (folder / "graph-result-live-v1.json").exists():
        raise ValueError("live_graph_receipt_already_finalized")
    expected = {
        "origin",
        "run_id",
        "packet_sha256",
        "real_http_requests",
        "live_dispatch",
        "root_selection_accepted",
        "root_render_accepted",
        "transport",
        "events",
    }
    public = fixture()
    if (
        type(proof) is not dict
        or set(proof) != expected
        or (
            proof["origin"] != ("offline_fake" if offline else "live_nim")
            or proof["run_id"] != bound["run_id"]
            or calls != 1
            or proof["packet_sha256"] != public["request"]["packet_sha256"]
            or proof["events"]
            != ["analyze", "shap", "comparables", "context", "select", "render", "proof"]
            or canonical(result["analysis"]) != canonical(public["data"]["report"])
            or canonical(result["evidence_packet"]) != canonical(public["request"]["packet"])
            or result["orchestration"]["native_feature_handoff"] is not False
            or result["orchestration"]["real_provider_verified"] is not False
        )
    ):
        raise ValueError("live_graph_proof_binding_failed")
    expected_dispatch = (
        None
        if offline
        else {
            "run_id": bound["run_id"],
            "plan_sha256": contract.PLAN_SHA256,
            "configuration_sha256": bound["configuration_sha256"],
            "specific_remote_authorization_id": contract.AUTHORIZATION_ID,
            "technical_review_sha256": bound["technical_review_sha256"],
            "state": "consumed_before_transport",
        }
    )
    if canonical(proof["live_dispatch"]) != canonical(expected_dispatch):
        raise ValueError("live_graph_dispatch_proof_invalid")
    reservation, _ = contract.read_json(folder / "reservation-v3.json", 2048)
    expected_reservation = {
        "protocol": "nim-fixed-public-dispatch-v3",
        "state": "consumed_before_child_start",
        "plan_sha256": contract.PLAN_SHA256,
        "parent_pid": os.getpid(),
        "nonce_sha256": digest(nonce),
        "offline_simulation_only": offline,
        "retry_allowed": False,
    }
    dispatch, _ = contract.read_json(folder / "dispatch-v3.json", 2048)
    if canonical(reservation) != canonical(expected_reservation) or canonical(
        dispatch
    ) != canonical({"state": "consumed_before_transport", "offline_simulation_only": offline}):
        raise ValueError("live_graph_durable_dispatch_missing")
    accepted = result["explanation"]["status"] == "validated_catalogue_selection"
    if any(
        type(proof[k]) is not bool or proof[k] != accepted
        for k in ("root_selection_accepted", "root_render_accepted")
    ):
        raise ValueError("live_graph_authority_proof_invalid")
    count = proof["real_http_requests"]
    if (offline and (type(count) is not int or count != 0)) or (
        not offline and count is not None and (type(count) is not int or count not in (0, 1))
    ):
        raise ValueError("live_graph_request_count_invalid")
    transport = proof["transport"]
    if (
        type(transport) is not dict
        or set(transport) != {"code", "http_status", "wire_bytes", "completion_tokens"}
        or (transport["code"] not in TRANSPORT_CODES)
    ):
        raise ValueError("live_graph_transport_proof_invalid")
    for name, lower, upper in (
        ("http_status", 100, 599),
        ("wire_bytes", 0, 16384),
        ("completion_tokens", 0, 2048),
    ):
        value = transport[name]
        if value is not None and (type(value) is not int or not lower <= value <= upper):
            raise ValueError("live_graph_transport_proof_invalid")
    if accepted and (
        transport["code"] != "selection_accepted"
        or transport["http_status"] != 200
        or not transport["wire_bytes"]
        or transport["completion_tokens"] is None
    ):
        raise ValueError("live_graph_accepted_transport_invalid")
    verified = not offline and expected_dispatch is not None and count == 1 and accepted
    return proof | {
        "real_provider_verified": verified,
        "verification_status": "offline_only"
        if offline
        else "live_validated"
        if verified
        else "live_not_validated",
        "selector_invocations": calls,
        "numerical_origin": "entirely_invented",
        "legacy_status_field": "legacy_result.orchestration.real_provider_verified",
    }


def checked_python(worker_python):
    value = Path(worker_python)
    if not value.is_absolute() or not value.is_file():
        raise ValueError("live_graph_existing_absolute_root_python_required")
    return value


async def execute_once(worker_python):
    started = time.monotonic()
    worker_python = checked_python(worker_python)
    plan = contract.verify_plan()
    review_hash = contract.check_review(plan)
    return await _consume(contract.LEDGER, None, plan, review_hash, started, 45, worker_python)


async def simulate(case, folder, *, worker_python, timeout=45):
    started = time.monotonic()
    worker_python = checked_python(worker_python)
    if case not in CASES or type(timeout) not in (float, int) or not 0 < timeout <= 45:
        raise ValueError("live_graph_invalid_simulation")
    return await _consume(
        contract.simulation_folder(folder),
        case,
        contract.verify_plan(),
        None,
        started,
        timeout,
        worker_python,
    )


async def _consume(folder, case, plan, review_hash, started, timeout, worker_python):
    offline = case is not None
    if time.monotonic() >= started + timeout:
        raise TimeoutError
    folder, nonce = contract.reserve(folder, offline=offline)
    run_id = uuid.uuid4().hex
    bound = contract.binding(
        plan, review_hash, run_id, started, timeout, offline=offline, owner_pid=os.getpid()
    )
    outcome = "startup_failed_consumed"
    result = None
    try:
        contract.create(folder / "live-graph-binding.json", bound)
        # Exact root interpreter is an operator option of main(), never payload.
        remaining = started + timeout - time.monotonic()
        if remaining <= 0:
            raise TimeoutError
        arguments = ("--run-id", run_id) + (
            ("--offline-case", case, "--simulation-ledger", str(folder))
            if offline
            else ("--released",)
        )
        worker = ProbeWorker(
            worker_python,
            ROOT,
            arguments,
            module="scripts.nim_graph_live_worker_v1",
            timeout=remaining,
        )
        # HTTP stays in this ONLY child. Parent cancellation kills/reaps it,
        # closing its sockets; there is no separately-sessioned HTTP grandchild.
        deadline = asyncio.get_running_loop().time() + max(0, started + timeout - time.monotonic())
        async with asyncio.timeout_at(deadline), worker:
            authorized = await worker.request({"op": "authorize", "nonce": nonce.hex()})
            if authorized != {"authorization": "bound_before_context"}:
                raise ValueError("live_graph_initial_authorization_failed")
            selector = RootSelector(worker)
            legacy = (await build_graph(worker, selector).ainvoke({"payload": {}}))["result"]
            proof = await worker.request({"op": "proof"})
            contract.check_binding(
                folder, plan, review_hash, run_id, offline=offline, owner_pid=os.getpid()
            )
            current = provider_proof(
                proof, legacy, bound, folder, nonce, offline=offline, calls=selector.calls
            )
            result = {
                "schema_version": "creative-nim-graph-live-v1",
                "legacy_result": legacy,
                "current_provider": current,
            }
            outcome = "observed"
    except TimeoutError:
        outcome = "timeout_outcome_uncertain"
        result = None
    except asyncio.CancelledError:
        outcome = "cancelled_outcome_uncertain"
        result = None
        raise
    except Exception:  # noqa: BLE001 - never include provider/credential/path/error data
        outcome = "failed_outcome_uncertain"
        result = None
    finally:
        receipt = {
            "protocol": contract.PROTOCOL,
            "state": "consumed",
            "outcome": outcome,
            "result": result,
            "run_id": run_id,
            "plan_sha256": contract.PLAN_SHA256,
            "configuration_sha256": plan["configuration_sha256"],
            "specific_remote_authorization_id": contract.AUTHORIZATION_ID,
            "technical_review_sha256": review_hash,
            "offline_simulation_only": offline,
            "real_http_requests": 0
            if offline
            else None
            if result is None
            else result["current_provider"]["real_http_requests"],
            "retry_allowed": False,
            "max_spend_brl": 0,
            "measured_cost_brl": None,
            "elapsed_seconds_including_cleanup": time.monotonic() - started,
        }
        contract.create(folder / "graph-result-live-v1.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--execute-reviewed-once", action="store_true")
    mode.add_argument("--offline-case", choices=sorted(CASES))
    parser.add_argument("--simulation-ledger")
    parser.add_argument("--worker-python", type=Path, required=True)
    args = parser.parse_args()
    try:
        if not args.worker_python.is_absolute():
            raise ValueError("live_graph_absolute_root_python_required")
        if args.execute_reviewed_once and args.simulation_ledger is None:
            receipt = asyncio.run(execute_once(args.worker_python))
        elif args.offline_case and args.simulation_ledger:
            receipt = asyncio.run(
                simulate(
                    args.offline_case, args.simulation_ledger, worker_python=args.worker_python
                )
            )
        else:
            raise ValueError("live_graph_invalid_mode")
    except Exception:  # noqa: BLE001 - no raw error/path/key; inspect durable consumed receipt
        receipt = {"outcome": "stopped_do_not_repeat_if_reserved"}
    print(json.dumps(receipt, allow_nan=False))


if __name__ == "__main__":
    main()

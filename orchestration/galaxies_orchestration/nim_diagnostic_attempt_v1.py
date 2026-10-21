"""Fresh one-shot diagnostic wrapper; real execution requires a NEW authorization."""

import argparse
import asyncio
import json
import os
import time
import uuid
from pathlib import Path

from . import nim_diagnostic_attempt_contract_v1 as c
from .integrated_graph_v2 import build_graph
from .nim_diagnostic_contract_v1 import validate_diagnostic
from .nim_diagnostic_graph_v1 import DiagnosticSelector
from .nim_graph_contract_v1 import ROOT, canonical, digest, fixture
from .nim_graph_live_v1 import TRANSPORT_CODES
from .nim_graph_v1 import ProbeWorker

CASES = c.FAKE_CASES


def verify_dispatch(folder, nonce, *, offline):
    reservation, _ = c.read_json(folder / "reservation-v3.json", 2048)
    marker, _ = c.read_json(folder / "dispatch-v3.json", 2048)
    if canonical(reservation) != canonical(
        {
            "protocol": "nim-fixed-public-dispatch-v3",
            "state": "consumed_before_child_start",
            "plan_sha256": c.PLAN_SHA256,
            "parent_pid": os.getpid(),
            "nonce_sha256": digest(nonce),
            "offline_simulation_only": offline,
            "retry_allowed": False,
        }
    ) or canonical(marker) != canonical(
        {"state": "consumed_before_transport", "offline_simulation_only": offline}
    ):
        raise ValueError("diagnostic_attempt_dispatch_binding_invalid")


def provider(proof, legacy, bound, *, offline, calls):
    if not offline:
        c.require_new_authorization()
    expected_dispatch = (
        None
        if offline
        else {
            key: bound[key]
            for key in (
                "protocol",
                "plan_sha256",
                "configuration_sha256",
                "specific_remote_authorization_id",
                "technical_review_sha256",
                "run_id",
            )
        }
        | {"state": "consumed_before_transport"}
    )
    public = fixture()
    if (
        type(proof) is not dict
        or set(proof)
        != {
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
        or proof["origin"] != ("offline_fake" if offline else "live_nim")
        or proof["run_id"] != bound["run_id"]
        or calls != 1
        or (
            canonical(proof["live_dispatch"]) != canonical(expected_dispatch)
            or proof["packet_sha256"] != public["request"]["packet_sha256"]
            or proof["events"]
            != ["analyze", "shap", "comparables", "context", "select", "render", "proof"]
            or canonical(legacy["analysis"]) != canonical(public["data"]["report"])
            or canonical(legacy["evidence_packet"]) != canonical(public["request"]["packet"])
            or legacy["orchestration"]["native_feature_handoff"] is not False
            or legacy["orchestration"]["real_provider_verified"] is not False
        )
    ):
        raise ValueError("diagnostic_attempt_live_proof_invalid")
    accepted = legacy["explanation"]["status"] == "validated_catalogue_selection"
    if any(
        type(proof[k]) is not bool or proof[k] != accepted
        for k in ("root_selection_accepted", "root_render_accepted")
    ):
        raise ValueError("diagnostic_attempt_authority_proof_invalid")
    count, transport = proof["real_http_requests"], proof["transport"]
    if (offline and (type(count) is not int or count != 0)) or (
        not offline and count is not None and (type(count) is not int or count not in (0, 1))
    ):
        raise ValueError("diagnostic_attempt_count_invalid")
    if (
        type(transport) is not dict
        or set(transport) != {"code", "http_status", "wire_bytes", "completion_tokens"}
        or transport["code"] not in TRANSPORT_CODES
    ):
        raise ValueError("diagnostic_attempt_transport_invalid")
    for key, lower, upper in (
        ("http_status", 100, 599),
        ("wire_bytes", 0, 16384),
        ("completion_tokens", 0, 2048),
    ):
        value = transport[key]
        if value is not None and (type(value) is not int or not lower <= value <= upper):
            raise ValueError("diagnostic_attempt_transport_invalid")
    if (transport["code"] == "selection_accepted") != accepted:
        raise ValueError("diagnostic_attempt_transport_authority_mismatch")
    if accepted and (
        transport["code"] != "selection_accepted"
        or transport["http_status"] != 200
        or not transport["wire_bytes"]
        or transport["completion_tokens"] is None
        or (not offline and count != 1)
    ):
        raise ValueError("diagnostic_attempt_accepted_transport_invalid")
    return proof | {
        "real_provider_verified": not offline and accepted and count == 1,
        "verification_status": "offline_only"
        if offline
        else "live_validated"
        if accepted
        else "live_not_validated",
        "selector_invocations": calls,
        "numerical_origin": "entirely_invented",
        "legacy_status_field": "legacy_result.orchestration.real_provider_verified",
    }


async def execute_remote(worker_python):
    c.require_new_authorization()  # FIRST: no plan/review read, spawn, nonce, ledger or key
    started = time.monotonic()
    plan = c.verify_plan()
    return await run(worker_python, c.LEDGER, None, plan, c.check_review(plan), started, 45)


async def simulate(worker_python, case, folder, *, timeout=45):
    started = time.monotonic()
    if case not in CASES or type(timeout) not in (int, float) or not 0 < timeout <= 45:
        raise ValueError("diagnostic_attempt_invalid_simulation")
    return await run(
        worker_python, c.simulation_folder(folder), case, c.verify_plan(), None, started, timeout
    )


async def run(worker_python, folder, case, plan, review_hash, started, timeout):
    offline = case is not None
    if not offline:
        c.require_new_authorization()
    if not Path(worker_python).is_absolute() or not Path(worker_python).is_file():
        raise ValueError("diagnostic_attempt_absolute_existing_python_required")
    if time.monotonic() >= started + timeout:
        raise TimeoutError
    folder, nonce = c.reserve(folder, offline=offline)
    run_id = uuid.uuid4().hex
    bound = c.binding(
        plan, review_hash, run_id, started, timeout, offline=offline, owner_pid=os.getpid()
    )
    outcome, result = "startup_failed_consumed", None
    try:
        c.create(folder / "diagnostic-attempt-binding.json", bound)
        arguments = ("--run-id", run_id) + (
            ("--offline-case", case, "--simulation-ledger", str(folder))
            if offline
            else ("--released",)
        )
        remaining = started + timeout - time.monotonic()
        if remaining <= 0:
            raise TimeoutError
        worker = ProbeWorker(
            worker_python,
            ROOT,
            arguments,
            module="scripts.nim_diagnostic_attempt_worker_v1",
            timeout=remaining,
        )
        deadline = asyncio.get_running_loop().time() + max(0, started + timeout - time.monotonic())
        async with asyncio.timeout_at(deadline), worker:
            if await worker.request({"op": "authorize", "nonce": nonce.hex()}) != {
                "authorization": "bound_before_context"
            }:
                raise ValueError("diagnostic_attempt_handshake_invalid")
            selector = DiagnosticSelector(worker)
            legacy = (await build_graph(worker, selector).ainvoke({"payload": {}}))["result"]
            proof = await worker.request({"op": "proof"})
            c.check_binding(
                folder, plan, review_hash, run_id, offline=offline, owner_pid=os.getpid()
            )
            verify_dispatch(folder, nonce, offline=offline)
            current = provider(proof, legacy, bound, offline=offline, calls=selector.calls)
            diagnostic = validate_diagnostic(selector.diagnostic)
            if (diagnostic["authority_status"] == "accepted") != proof["root_selection_accepted"]:
                raise ValueError("diagnostic_attempt_diagnostic_binding_invalid")
            result = {
                "legacy_result": legacy,
                "current_provider": current,
                "selection_diagnostic": diagnostic,
            }
            outcome = "observed"
    except asyncio.CancelledError:
        outcome, result = "cancelled_outcome_uncertain", None
        raise
    except TimeoutError:
        outcome, result = "timeout_outcome_uncertain", None
    except Exception:  # noqa: BLE001 - only fixed outcomes, never arbitrary errors
        outcome, result = "failed_outcome_uncertain", None
    finally:
        receipt = {
            "protocol": c.PROTOCOL,
            "state": "consumed",
            "outcome": outcome,
            "result": result,
            "run_id": run_id,
            "plan_sha256": c.PLAN_SHA256,
            "configuration_sha256": plan["configuration_sha256"],
            "specific_remote_authorization_id": c.AUTHORIZATION_ID,
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
        c.create(folder / "diagnostic-attempt-result.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--execute-reviewed-once", action="store_true")
    mode.add_argument("--offline-case", choices=sorted(CASES))
    parser.add_argument("--simulation-ledger")
    parser.add_argument("--worker-python", required=True)
    args = parser.parse_args()
    try:
        if args.execute_reviewed_once and args.simulation_ledger is None:
            result = asyncio.run(execute_remote(args.worker_python))
        elif args.offline_case and args.simulation_ledger:
            result = asyncio.run(
                simulate(args.worker_python, args.offline_case, args.simulation_ledger)
            )
        else:
            raise ValueError("diagnostic_attempt_invalid_mode")
    except Exception:  # noqa: BLE001 - no error/key/body/path projection
        result = {"outcome": "stopped_do_not_repeat_if_reserved"}
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()

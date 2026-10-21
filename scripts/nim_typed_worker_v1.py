"""Fixed typed request; gated key access and safe post-authority sidecar only."""

from __future__ import annotations

import argparse
import http.client
import json
import re
import ssl
import sys
import time

from scripts.nim_dispatch_fakes_v3 import INVENTED_KEY, connection_factory
from scripts.nim_dispatch_ledger_v3 import authorize, create
from scripts.nim_dispatch_plan_v3 import HOST, PATH
from scripts.nim_dispatch_summary_v3 import transport_failure
from scripts.nim_observed_http_worker_v3 import protocol_ok
from scripts.nim_release_worker_v1 import simulated_connection
from scripts.nim_type_observer_v1 import observe_open_response, type_audit, validate_observation
from scripts.nim_typed_request_v1 import (
    CASES,
    LEDGER,
    PLAN_SHA256,
    check_binding,
    check_review,
    payload_bytes,
    simulation_folder,
    verify_plan,
)


def exchange(key, *, factory, timeout=45):
    """Mandatory transport seam; no proxy, redirect, SDK, retry or error logging."""
    connection = None
    summary = transport_failure("request_failed_outcome_uncertain")
    try:
        if type(key) is not str or not re.fullmatch(r"[A-Za-z0-9_-]{20,512}", key):
            return validate_observation({"summary": summary, "type_audit": type_audit(None)})
        body = payload_bytes()
        connection = factory(HOST, port=443, timeout=timeout, context=ssl.create_default_context())
        connection.set_debuglevel(0)
        connection.request(
            "POST",
            PATH,
            body=body,
            headers={
                "Authorization": "Bearer " + key,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        response = connection.getresponse()
        if response.status == 200 and not protocol_ok(response):
            summary = transport_failure("protocol_rejected")
        else:
            return observe_open_response(response)
    except Exception:  # noqa: BLE001, S110 - no body, header, exception or hashes escape
        pass
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:  # noqa: BLE001, S110
                pass
    return validate_observation({"summary": summary, "type_audit": type_audit(None)})


def released(nonce, *, remaining):
    plan = verify_plan()
    review_hash = check_review(plan)
    check_binding(LEDGER, plan, review_hash, offline=False)
    authorize(LEDGER, nonce, PLAN_SHA256, offline=False)
    # The existing secret is read only AFTER the durable exclusive dispatch.
    from orchestration.galaxies_orchestration.nim_http import existing_key

    return exchange(existing_key(), factory=http.client.HTTPSConnection, timeout=remaining)


def fake_connection(case):
    if case not in {"scalar_ids", "object_item", "double_encoded"}:
        return simulated_connection(case)

    class TypeConnection(connection_factory("valid")):
        def getresponse(self):
            response = super().getresponse()
            envelope = json.loads(response.read(16385))
            message = envelope["choices"][0]["message"]
            selection = json.loads(message["content"])
            if case == "scalar_ids":
                selection["evidence_ids"] = "c1_prediction"
            elif case == "object_item":
                selection["evidence_ids"] = [{"evidence_id": "c1_prediction"}]
            else:
                selection = json.dumps(selection)
            message["content"] = json.dumps(selection)
            wire = json.dumps(envelope).encode()
            response.read = lambda size: wire[:size]
            return response

    return TypeConnection


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--released", action="store_true")
    mode.add_argument("--offline-case", choices=sorted(CASES))
    parser.add_argument("--simulation-ledger")
    args = parser.parse_args()
    result = {"worker_status": "worker_failed_outcome_uncertain"}
    try:
        started = time.monotonic()
        plan = verify_plan()
        nonce = sys.stdin.buffer.read(33)
        remaining = 45 - (time.monotonic() - started)
        if remaining <= 0:
            raise TimeoutError
        if args.released:
            if args.simulation_ledger is not None:
                raise ValueError("typed_fixed_ledger_required")
            folder = LEDGER
            observation = released(nonce, remaining=remaining)
        else:
            folder = simulation_folder(args.simulation_ledger)
            check_binding(folder, plan, None, offline=True)
            authorize(folder, nonce, PLAN_SHA256, offline=True)
            observation = exchange(
                INVENTED_KEY, factory=fake_connection(args.offline_case), timeout=remaining
            )
        # Existing bounded IPC remains unchanged. This sidecar is allowlisted,
        # durable, private, and must match the independently validated IPC summary.
        create(folder / "typed-observation.json", validate_observation(observation))
        result = {"worker_status": "observed", "summary": observation["summary"]}
    except Exception:  # noqa: BLE001, S110 - stdout never contains raw diagnostics
        pass
    sys.stdout.write(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()

"""The only new component allowed to read the existing key, after all gates."""

from __future__ import annotations

import argparse
import http.client
import json
import sys
import time
from pathlib import Path

from scripts.nim_dispatch_fakes_v3 import INVENTED_KEY, connection_factory
from scripts.nim_dispatch_ledger_v3 import authorize
from scripts.nim_observed_http_worker_v3 import exchange
from scripts.nim_release_contract_v1 import (
    LEDGER,
    SIMULATION_CASES,
    check_binding,
    check_review,
    simulation_folder,
    verify_plan,
)
from scripts.nim_release_seal_v1 import PLAN_SHA256


def released(nonce, *, remaining):
    plan = verify_plan()
    review_hash = check_review(plan)
    check_binding(LEDGER, plan, review_hash, offline=False)
    # O_EXCL+fsync dispatch marker precedes reading the existing key and HTTP.
    authorize(LEDGER, nonce, PLAN_SHA256, offline=False)
    from orchestration.galaxies_orchestration.nim_http import existing_key

    return exchange(existing_key(), factory=http.client.HTTPSConnection, timeout=remaining)


def simulated_connection(case):
    if case not in {"http_429", "http_503"}:
        return connection_factory(case)

    class StatusConnection(connection_factory("http_error")):
        def getresponse(self):
            response = super().getresponse()
            response.status = 429 if case == "http_429" else 503
            return response

    return StatusConnection


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--released", action="store_true")
    mode.add_argument("--offline-case", choices=sorted(SIMULATION_CASES))
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
                raise ValueError("release_fixed_ledger_required")
            summary = released(nonce, remaining=remaining)
        else:
            folder = simulation_folder(Path(args.simulation_ledger))
            check_binding(folder, plan, None, offline=True)
            authorize(folder, nonce, PLAN_SHA256, offline=True)
            summary = exchange(
                INVENTED_KEY, factory=simulated_connection(args.offline_case), timeout=remaining
            )
        result = {"worker_status": "observed", "summary": summary}
    except Exception:  # noqa: BLE001, S110 - no secret, traceback or unknown metadata leaves stdout
        pass
    sys.stdout.write(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()

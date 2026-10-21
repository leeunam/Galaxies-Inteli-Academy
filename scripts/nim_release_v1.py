"""Fixed single-attempt release. No HTTP is performed by this parent."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from scripts.nim_dispatch_ledger_v3 import create, reserve
from scripts.nim_dispatch_v3 import bounded_child, validate_outcome
from scripts.nim_release_contract_v1 import (
    EVIDENCE_ID,
    LEDGER,
    PROTOCOL,
    SIMULATION_CASES,
    check_review,
    simulation_folder,
    verify_plan,
)
from scripts.nim_release_seal_v1 import PLAN_SHA256


async def execute_once():
    started = time.monotonic()
    plan = verify_plan()
    review_hash = check_review(plan)
    return await _consume(LEDGER, None, plan, review_hash, started, 45, bounded_child)


async def simulate(case, folder, *, timeout=45, runner=bounded_child):
    started = time.monotonic()
    if case not in SIMULATION_CASES or not 0 < timeout <= 45:
        raise ValueError("release_invalid_simulation")
    folder = simulation_folder(Path(folder))
    plan = verify_plan()
    return await _consume(folder, case, plan, None, started, timeout, runner)


async def _consume(folder, case, plan, review_hash, started, timeout, runner):
    offline = case is not None
    # Shared v3 on-disk consumption codec, but NEW fixed release ledger+plan hash.
    # Existence consumes the attempt, even before a receipt can be completed.
    folder, nonce = reserve(folder, PLAN_SHA256, offline=offline)
    result = {"outcome": "startup_failed_consumed"}
    try:
        create(
            folder / "release-binding.json",
            {
                "protocol": PROTOCOL,
                "plan_sha256": PLAN_SHA256,
                "configuration_sha256": plan["configuration_sha256"],
                "financial_evidence_id": EVIDENCE_ID,
                "technical_review_sha256": review_hash,
                "offline_simulation_only": offline,
            },
        )
        command = [sys.executable, "-s", "-m", "scripts.nim_release_worker_v1"]
        command += (
            ["--offline-case", case, "--simulation-ledger", str(folder)]
            if offline
            else ["--released"]
        )
        remaining = timeout - (time.monotonic() - started)
        if remaining <= 0:
            result = {"outcome": "timeout_outcome_uncertain"}
        else:
            result = validate_outcome(await runner(command, nonce, timeout=remaining))
    except asyncio.CancelledError:
        result = {"outcome": "cancelled_outcome_uncertain"}
        raise
    except Exception:  # noqa: BLE001 - receipt is an allowlist, never an exception projection
        result = {"outcome": "invalid_child_protocol"}
    finally:
        receipt = validate_outcome(result) | {
            "protocol": PROTOCOL,
            "state": "consumed",
            "plan_sha256": PLAN_SHA256,
            "configuration_sha256": plan["configuration_sha256"],
            "financial_evidence_id": EVIDENCE_ID,
            "technical_review_sha256": review_hash,
            "offline_simulation_only": offline,
            "real_requests": 0 if offline else None,
            "max_spend_brl": 0,
            "measured_cost_brl": None,
            "retry_allowed": False,
            "elapsed_seconds": time.monotonic() - started,
        }
        create(folder / "result-v3.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--execute-reviewed-once", action="store_true")
    mode.add_argument("--offline-case", choices=sorted(SIMULATION_CASES))
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    try:
        if args.execute_reviewed_once and args.output_dir is None:
            result = asyncio.run(execute_once())
        elif args.offline_case and args.output_dir:
            result = asyncio.run(simulate(args.offline_case, args.output_dir))
        else:
            result = {"outcome": "not_executed"}
    except Exception:  # noqa: BLE001 - never print credential, filesystem path or raw error
        result = {"outcome": "stopped_do_not_repeat_if_reserved"}
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()

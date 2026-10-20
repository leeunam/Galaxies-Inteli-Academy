"""One fixed public NIM dispatch, prepared and runnable only as an offline simulation."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import sys
import time
from pathlib import Path

from scripts.nim_dispatch_fakes_v3 import CASES
from scripts.nim_dispatch_ledger_v3 import create, reserve
from scripts.nim_dispatch_plan_v3 import LEDGER, ROOT, verify_plan
from scripts.nim_dispatch_seal_v3 import PLAN_SHA256
from scripts.nim_dispatch_summary_v3 import validate_summary
from scripts.selection_observation_v2 import _unique

MAX_IPC_BYTES = 8192
OUTCOMES = {
    "observed",
    "timeout_outcome_uncertain",
    "child_failed_outcome_uncertain",
    "invalid_child_protocol",
    "cancelled_outcome_uncertain",
    "startup_failed_consumed",
}


def child_environment():
    # Literal environment: no credential, proxy, tracing, PYTHONPATH, user site,
    # alternate CA, loader variables, shell hooks or inherited debug configuration.
    return {
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "LANGSMITH_TRACING": "false",
        "LANGCHAIN_TRACING_V2": "false",
        "CUDA_VISIBLE_DEVICES": "",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
    }


def inspect_child(raw):
    value = json.loads(raw, object_pairs_hook=_unique)
    if (
        type(value) is not dict
        or set(value) != {"worker_status", "summary"}
        or value["worker_status"] != "observed"
    ):
        raise ValueError("v3_invalid_child_protocol")
    return {"outcome": "observed", "summary": validate_summary(value["summary"])}


async def bounded_child(command, nonce, *, timeout):
    """Deadline covers startup, HTTP, authority, IPC and child exit; always reap."""
    process = None
    spawning = None
    try:
        async with asyncio.timeout(timeout):
            spawning = asyncio.create_task(
                asyncio.create_subprocess_exec(
                    *command,
                    cwd=ROOT,
                    env=child_environment(),
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.DEVNULL,
                    start_new_session=True,
                )
            )
            # Cancellation cannot lose ownership between OS spawn and assignment.
            # Recovery below obtains only the handle: it never releases the nonce.
            process = await asyncio.shield(spawning)
            process.stdin.write(nonce)
            await process.stdin.drain()
            process.stdin.close()
            raw = bytearray()
            while True:
                chunk = await process.stdout.read(min(4096, MAX_IPC_BYTES + 1 - len(raw)))
                if not chunk:
                    break
                raw.extend(chunk)
                if len(raw) > MAX_IPC_BYTES:
                    return {"outcome": "invalid_child_protocol"}
            await process.wait()
            if process.returncode != 0:
                return {"outcome": "child_failed_outcome_uncertain"}
            return inspect_child(raw)
    except TimeoutError:
        return {"outcome": "timeout_outcome_uncertain"}
    except asyncio.CancelledError:
        raise
    except Exception:  # noqa: BLE001 - no child input, output or exception retained
        return {"outcome": "invalid_child_protocol"}
    finally:
        cleanup = asyncio.create_task(_reap_spawn(spawning, process))
        interrupted = False
        while True:
            try:
                await asyncio.shield(cleanup)
                break
            except asyncio.CancelledError:
                # Also collect on repeated cancellation during spawn recovery.
                if cleanup.cancelled():
                    raise RuntimeError("v3_cleanup_unconfirmed") from None
                interrupted = True
        if interrupted:
            raise asyncio.CancelledError


async def _reap_spawn(spawning, process):
    if process is None and spawning is not None:
        try:
            process = await spawning
        except Exception:  # noqa: BLE001 - spawn failed without a process handle
            return
    if process is not None:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        await process.wait()


def validate_outcome(result):
    if type(result) is not dict or result.get("outcome") not in OUTCOMES:
        raise ValueError("v3_invalid_outcome")
    if result["outcome"] == "observed":
        if set(result) != {"outcome", "summary"}:
            raise ValueError("v3_invalid_outcome")
        validate_summary(result["summary"])
    elif set(result) != {"outcome"}:
        raise ValueError("v3_invalid_outcome")
    return result


async def execute_offline(case, folder, *, timeout=45, runner=bounded_child):
    """Test seam uses namespaces that can never be used by the remote entrypoint.

    A fresh directory represents a new identified simulation, not another remote
    authorization. Remote execution is absent from this CLI and remains sealed.
    """
    started = time.monotonic()
    if case not in CASES or not 0 < timeout <= 45:
        raise ValueError("v3_invalid_simulation")
    if Path(folder).resolve() == LEDGER.resolve() or Path(folder).resolve().is_relative_to(
        LEDGER.resolve()
    ):
        raise ValueError("v3_remote_ledger_forbidden_in_simulation")
    verify_plan()  # before creating a directory, nonce or child
    return await _consume_attempt(folder, case, started, timeout, runner, offline=True)


async def execute_released():
    """Prepared fixed-ledger path; current seal refuses it before reservation.

    Absent from CLI. A future release must replace the offline seal/plan contract
    with applicable account evidence. No endpoint/model/payload/ledger arguments.
    """
    started = time.monotonic()
    verify_plan(remote=True)
    return await _consume_attempt(LEDGER, None, started, 45, bounded_child, offline=False)


async def _consume_attempt(folder, case, started, timeout, runner, *, offline):
    folder, nonce = reserve(folder, PLAN_SHA256, offline=offline)
    command = [sys.executable, "-s", "-m", "scripts.nim_observed_http_worker_v3"]
    command += ["--offline-case", case] if offline else ["--released-remote"]
    command += ["--ledger", str(folder)]
    result = {"outcome": "startup_failed_consumed"}
    try:
        remaining = timeout - (time.monotonic() - started)
        if remaining <= 0:
            result = {"outcome": "timeout_outcome_uncertain"}
        else:
            result = validate_outcome(
                await runner(
                    command,
                    nonce,
                    timeout=remaining,
                )
            )
    except asyncio.CancelledError:
        result = {"outcome": "cancelled_outcome_uncertain"}
        raise
    except Exception:  # noqa: BLE001 - injected test runners also fail closed
        result = {"outcome": "invalid_child_protocol"}
    finally:
        result = validate_outcome(result)
        receipt = result | {
            "protocol": "nim-fixed-public-dispatch-v3",
            "state": "consumed",
            "plan_sha256": PLAN_SHA256,
            "offline_simulation_only": offline,
            "real_requests": 0 if offline else None,
            "retry_allowed": False,
            "case": case,
            "elapsed_seconds": time.monotonic() - started,
        }
        create(folder / "result-v3.json", receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline-case", required=True, choices=sorted(CASES))
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    try:
        result = asyncio.run(execute_offline(args.offline_case, args.output_dir))
    except Exception:  # noqa: BLE001 - never print a path, input or exception
        result = {"outcome": "stopped_do_not_repeat"}
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()

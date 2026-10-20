"""One authorized synthetic NIM attempt, durably consumed before child startup."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import signal
import sys
import time
from datetime import UTC, datetime

from galaxies_orchestration.nim_http import (
    FIXTURE,
    HOST,
    LEDGER,
    MODEL,
    PATH,
    ROOT,
    durable_create,
    payload,
)
from galaxies_orchestration.nim_seal import APPROVED_PLAN_SHA256


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_plan(folder=LEDGER):
    if not APPROVED_PLAN_SHA256 or sha(folder / "plan.json") != APPROVED_PLAN_SHA256:
        raise ValueError("probe_plan_seal_mismatch")
    plan = json.loads((folder / "plan.json").read_bytes())
    if (
        plan["max_calls"] != 1
        or plan["max_output_tokens"] != 2048
        or plan["timeout_seconds"] != 45
        or plan["max_response_bytes"] != 16384
        or plan["max_spend_brl"] != 0
        or plan["endpoint"] != "https://" + HOST + PATH
        or plan["model"] != MODEL
        or not plan["text_only_entirely_invented"]
        or plan["fixture_sha256"] != sha(FIXTURE)
        or plan["http_payload_sha256"]
        != hashlib.sha256(json.dumps(payload(), ensure_ascii=True).encode()).hexdigest()
    ):
        raise ValueError("probe_plan_mismatch")
    for name, expected in plan["protected_sha256"].items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT) or sha(path) != expected:
            raise ValueError("probe_protected_file_changed")
    return plan


async def bounded_child(command, *, environment, timeout=45, input_bytes=None):
    """Wall deadline includes process startup, request and response consumption."""
    process = None
    try:
        async with asyncio.timeout(timeout):
            process = await asyncio.create_subprocess_exec(
                *command,
                cwd=ROOT / "orchestration",
                env=environment,
                stdin=asyncio.subprocess.PIPE
                if input_bytes is not None
                else asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                start_new_session=True,
            )
            if input_bytes is not None:
                process.stdin.write(input_bytes)
                await process.stdin.drain()
                process.stdin.close()
            raw = b""
            while True:
                chunk = await process.stdout.read(min(4096, 32769 - len(raw)))
                if not chunk:
                    break
                raw += chunk
                if len(raw) > 32768:
                    return {"status": "child_output_limit_exceeded"}
            await process.wait()
            if process.returncode != 0:
                return {"status": "child_failed_outcome_uncertain"}
            return json.loads(raw)
    except TimeoutError:
        return {"status": "timeout_outcome_uncertain"}
    except asyncio.CancelledError:
        raise
    except Exception:  # noqa: BLE001 - sanitized result only
        return {"status": "child_failed_outcome_uncertain"}
    finally:
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            await process.wait()


class OneShotNim:
    def __init__(self, folder=LEDGER, *, runner=bounded_child):
        self.folder = folder
        self.runner = runner  # test-only local injection; production CLI uses fixed child
        self.status = None

    async def __call__(self, request):
        if request != FIXTURE.read_text().strip():
            raise ValueError("only_fixed_synthetic_fixture_authorized")
        plan = verify_plan(self.folder)
        token = os.urandom(32)
        reservation = {
            "status": "reserved_attempt_consumed",
            "reserved_at_utc": datetime.now(UTC).isoformat(),
            "plan_sha256": sha(self.folder / "plan.json"),
            "fixture_sha256": sha(FIXTURE),
            "endpoint": plan["endpoint"],
            "model": MODEL,
            "max_calls": 1,
            "max_output_tokens": 2048,
            "timeout_seconds": 45,
            "max_response_bytes": 16384,
            "max_spend_brl": 0,
            "private_data_sent": False,
            "parent_pid": os.getpid(),
            "dispatch_token_sha256": hashlib.sha256(token).hexdigest(),
        }
        # O_EXCL + fsync; even cancellation/startup failure consumes the attempt.
        durable_create(self.folder / "reservation.json", reservation)
        started = time.monotonic()
        environment = {
            k: v
            for k, v in os.environ.items()
            if k in {"PATH", "LANG", "LC_ALL", "TMPDIR", "NVIDIA_API_KEY"}
        }
        environment.update(LANGSMITH_TRACING="false", LANGCHAIN_TRACING_V2="false")
        result = {"status": "cancelled_outcome_uncertain"}
        try:
            result = await self.runner(
                [sys.executable, "-m", "galaxies_orchestration.nim_http"],
                environment=environment,
                timeout=45,
                input_bytes=token,
            )
        finally:
            self.status = result.get("status", "invalid_child_reply")
            # No raw body/content, key, headers, exception or account data on disk.
            receipt = {
                k: result[k]
                for k in ("status", "http_status", "response_bytes", "completion_tokens")
                if k in result
            }
            receipt.update(
                elapsed_seconds=time.monotonic() - started,
                ended_at_utc=datetime.now(UTC).isoformat(),
                retry_allowed=False,
                reservation_sha256=sha(self.folder / "reservation.json"),
            )
            durable_create(self.folder / "result.json", receipt)
        if result.get("status") != "reply_received":
            raise ValueError("synthetic_nim_attempt_failed")
        return result["content"]


async def execute():
    from galaxies_orchestration.graph import build_graph
    from galaxies_orchestration.worker import RootWorker

    # Check sealed predecessors externally before authorizing this command. This
    # local check never resets reservation/dispatch/result or an uncertain outcome.
    verify_plan()
    if any(
        (LEDGER / name).exists() for name in ("reservation.json", "dispatch.json", "result.json")
    ):
        raise ValueError("synthetic_attempt_already_consumed_or_uncertain")
    selector = OneShotNim()
    async with RootWorker(synthetic_probe=True) as worker:
        result = (await build_graph(worker, selector).ainvoke({"payload": {}}))["result"]
    summary = {
        "stategraph_executed": result["orchestration"]["stategraph_executed"],
        "fixture_entirely_invented": result["fixture_entirely_invented"],
        "provider_status": selector.status,
        "selection_validated": result["explanation"]["status"] == "validated_catalogue_selection",
        "adherence_status": result["explanation"]["adherence_status"],
        "private_data_sent": False,
        "new_vlm_inferences": 0,
        "test_evaluated": False,
    }
    durable_create(LEDGER / "graph-result.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute-authorized-once", action="store_true")
    args = parser.parse_args()
    if not args.execute_authorized_once:
        print('{"status":"not_executed"}')
        return
    try:
        result = asyncio.run(execute())
    except Exception:  # noqa: BLE001 - inspect durable receipts; never echo input/secret
        result = {"status": "stopped_inspect_durable_receipts_do_not_repeat"}
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()

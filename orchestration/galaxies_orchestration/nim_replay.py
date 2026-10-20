"""Offline diagnostic of the sealed path; HTTP and credentials are simulated.

Never calls nim_probe.execute or nim_http.main. Original plan/fixture/sources
and the real consumed ledger remain read-only. Only temporary test ledgers vary.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import sys
import tempfile
from pathlib import Path

from galaxies_orchestration import nim_http
from galaxies_orchestration.graph import build_graph
from galaxies_orchestration.nim_probe import OneShotNim, bounded_child
from galaxies_orchestration.worker import RootWorker

CASES = ("valid", "invalid_json", "wrong_hash", "unknown_id", "duplicate_key", "invalid_unicode")


def invented_content(case):
    if case not in CASES:
        raise ValueError("unknown_offline_case")
    packet = json.loads(nim_http.FIXTURE.read_bytes())
    selected = {
        "packet_sha256": packet["packet_sha256"],
        "evidence_ids": ["c1_prediction", "c1_interval"],
    }
    if case == "invalid_json":
        return "ENTIRELY_INVENTED_NOT_JSON"
    if case == "invalid_unicode":
        return "\ud800"
    if case == "duplicate_key":
        return '{"packet_sha256":"' + packet["packet_sha256"] + '",' + json.dumps(selected)[1:]
    if case == "wrong_hash":
        selected["packet_sha256"] = "0" * 64
    if case == "unknown_id":
        selected["evidence_ids"] = ["invented_but_not_in_catalogue"]
    return json.dumps(selected)


def simulated_http(case):
    """Use the sealed envelope parser with a fake connection, in a real child."""
    raw = json.dumps(
        {
            "choices": [
                {
                    "message": {"role": "assistant", "content": invented_content(case)},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"completion_tokens": 10},
        }
    ).encode()

    class Response:
        status = 200

        def read(self, size):
            assert size == 16385
            return raw[:size]

    class FakeConnection:
        def __init__(self, host, **kwargs):
            assert host == nim_http.HOST and kwargs["port"] == 443
            self.called = False

        def request(self, method, path, *, body, headers):
            assert not self.called and method == "POST" and path == nim_http.PATH
            assert headers["Authorization"] == "Bearer ENTIRELY_INVENTED_OFFLINE_KEY"
            assert json.loads(body) == nim_http.payload()
            self.called = True

        def getresponse(self):
            assert self.called
            return Response()

        def close(self):
            pass

    return nim_http.perform_http("ENTIRELY_INVENTED_OFFLINE_KEY", connection_factory=FakeConnection)


async def replay(case, *, plan_bytes=None):
    """Exercise actual graph, adapter, child IPC and root validation; no network.

    The CLI uses a byte-for-byte copy of the already approved private plan;
    pytest supplies an invented plan under its own temporary test trust anchor.
    No real reservation/dispatch/result file is created or modified.
    """
    if case not in CASES:
        raise ValueError("unknown_offline_case")
    original = (nim_http.LEDGER / "plan.json").read_bytes() if plan_bytes is None else plan_bytes
    calls = []

    async def offline_runner(command, *, environment, timeout, input_bytes):
        calls.append(True)
        # The NIM child is substituted by an offline envelope simulator, but the
        # same real process/deadline/pipe implementation is used. No key enters it.
        safe_environment = {k: v for k, v in environment.items() if k in {"PATH", "LANG", "LC_ALL"}}
        return await bounded_child(
            [sys.executable, "-m", "galaxies_orchestration.nim_replay", "--child-case", case],
            environment=safe_environment,
            timeout=timeout,
            input_bytes=input_bytes,
        )

    with tempfile.TemporaryDirectory(prefix="galaxies-offline-nim-replay-") as scratch:
        folder = Path(scratch)
        (folder / "plan.json").write_bytes(original)
        selector = OneShotNim(folder, runner=offline_runner)
        async with RootWorker(synthetic_probe=True) as worker:
            result = (await build_graph(worker, selector).ainvoke({"payload": {}}))["result"]
        receipt = json.loads((folder / "result.json").read_bytes())
        return {
            "case": case,
            "offline_http_simulation": True,
            "actual_network_calls": 0,
            "real_credentials_loaded": False,
            "simulated_adapter_attempts": len(calls),
            "real_child_process_reaped": True,
            "real_root_worker_reaped": True,
            "stategraph_executed": result["orchestration"]["stategraph_executed"],
            "fixture_entirely_invented": result["fixture_entirely_invented"],
            "provider_status": selector.status,
            "adapter_status": receipt["status"],
            "selection_validated": result["explanation"]["status"]
            == "validated_catalogue_selection",
            "explanation_reason_code": result["explanation"].get("reason_code"),
            "analysis": result["analysis"],
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--case", choices=CASES)
    modes.add_argument("--child-case", choices=CASES)
    args = parser.parse_args()

    def forbidden(*args, **kwargs):
        raise RuntimeError("network_and_credential_lookup_forbidden_in_offline_replay")

    socket.socket.connect = forbidden
    socket.socket.connect_ex = forbidden
    socket.getaddrinfo = forbidden
    nim_http.existing_key = forbidden
    if args.child_case and "NVIDIA_API_KEY" in os.environ:
        raise RuntimeError("credential_must_not_enter_offline_child")
    os.environ.pop("NVIDIA_API_KEY", None)
    result = simulated_http(args.child_case) if args.child_case else asyncio.run(replay(args.case))
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()

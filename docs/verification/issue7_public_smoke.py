"""Acceptance receipt: real shared service/StateGraph/MCP; invented inputs only."""

import argparse
import asyncio
import json
import os
import select
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

from scripts.explanation_graph_service_v2 import GraphSettings, analyze_via_graph
from tests.native_v2_fixture import public_data

ROOT = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output-dir", type=Path, required=True)
args = parser.parse_args()
E = args.output_dir.resolve()
if not E.is_relative_to(ROOT / "data/private"):
    parser.error("output-dir must be a fresh directory under this clone data/private")
E.mkdir(parents=True)
data = public_data(3)
fixture = E / "invented.json"
fixture.write_text(json.dumps(data))
settings = GraphSettings(
    ROOT / "orchestration/.venv/bin/python",
    Path(sys.executable),
    E / "uploads",
    E / "registry.json",
    E / "scratch",
    worker_module="tests.native_v2_fixture",
    worker_arguments_extra=("--fixture-json", str(fixture)),
)
payload = {
    "campaign_id": "invented",
    "creative_ids": [c["creative_id"] for c in data["report"]["candidates"]],
    "sector": "moda",
    "objective": "divulgacao",
    "brief": "PUBLIC_INVENTED_BRIEF_SENTINEL",
}
direct = asyncio.run(analyze_via_graph(payload, settings))
assert direct["analysis"] == data["report"]
assert direct["orchestration"]["stategraph_executed"]
assert direct["orchestration"]["explainer_subgraph_executed"]
assert not direct["orchestration"]["native_feature_handoff"]
assert not direct["orchestration"]["real_provider_verified"]
assert direct["orchestration"]["selector_kind"] == "absent"
assert direct["explanation"]["adherence_status"] == "not_evaluated"
assert direct["explanation"]["reason_code"] == "transport_not_configured"
source = E / "settings.json"
source.write_text(json.dumps(asdict(settings), default=str))
messages = []
buffered = b""
with (E / "stderr.log").open("wb") as stderr:
    process = subprocess.Popen(
        [sys.executable, "-B", "-m", "tests.native_v2_mcp_fixture", str(source)],
        cwd=ROOT,
        env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1", "OPENBLAS_NUM_THREADS": "1"},
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=stderr,
        bufsize=0,
    )

    def send(body):
        process.stdin.write((json.dumps(body) + "\n").encode())

    def receive(expected_id):
        global buffered
        while True:
            while b"\n" not in buffered:
                assert select.select([process.stdout], [], [], 30)[0], "protocol_timeout"
                chunk = os.read(process.stdout.fileno(), 65536)
                assert chunk, "protocol_eof"
                buffered += chunk
            line, buffered = buffered.split(b"\n", 1)
            message = json.loads(line)
            assert message["jsonrpc"] == "2.0"
            messages.append(message)
            if message.get("id") == expected_id:
                return message

    try:
        send(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "issue7-invented-public", "version": "1"},
                },
            }
        )
        assert "result" in receive(1)
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        tools = receive(2)["result"]["tools"]
        assert {t["name"] for t in tools} == {
            "analyze_creatives",
            "analyze_creatives_with_explanation",
        }
        send(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "analyze_creatives_with_explanation",
                    "arguments": {"payload": payload},
                },
            }
        )
        reply = receive(3)
        assert reply["result"]["structuredContent"] == direct
    finally:
        process.stdin.close()
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        remaining = buffered + process.stdout.read()
        process.stdout.close()
    assert process.returncode == 0
for line in remaining.splitlines():
    message = json.loads(line)
    assert message["jsonrpc"] == "2.0"
    messages.append(message)
assert not list(settings.scratch_root.iterdir())
assert "PUBLIC_INVENTED_BRIEF_SENTINEL" not in json.dumps(messages)
assert "PUBLIC_INVENTED_BRIEF_SENTINEL" not in (E / "stderr.log").read_text()
receipt = {
    "input_kind": "public_invented_fixture_not_real_m1",
    "valid_request_contract": True,
    "candidates": 3,
    "python_mcp_exact_parity": True,
    "raw_stdout_jsonrpc_only": True,
    "jsonrpc_messages": len(messages),
    "server_exitcode": process.returncode,
    "scratch_empty": True,
    "sentinel_absent_in_result_and_stderr": True,
    "stategraph_executed": True,
    "explainer_subgraph_executed": True,
    "native_feature_handoff": False,
    "real_provider_verified": False,
    "selector_kind": "absent",
    "explanation_reason": direct["explanation"]["reason_code"],
    "adherence_status": direct["explanation"]["adherence_status"],
    "extraction_executed": False,
    "trained_model_loaded": False,
    "external_requests": 0,
}
(E / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
print(json.dumps(receipt, indent=2))

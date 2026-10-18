"""Inspect raw stdout as well as exercising the real SDK client in other tests."""

import json
import os
import select
import subprocess
import sys

from scripts.creative_analysis import analyze_creatives
from scripts.creative_mcp import ROOT


def test_stdout_contains_only_json_rpc_protocol_messages(registry, registered, tmp_path):
    payload = {
        "campaign_id": "demo",
        "creative_ids": [registered["creative_id"]],
        "sector": "moda",
        "objective": "divulgacao",
        "brief": "DADO_PRIVADO",
    }
    expected = analyze_creatives(payload, registry)
    with (tmp_path / "stderr").open("wb") as stderr:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "scripts.creative_mcp",
                "--uploads-root",
                str(registry.uploads_root),
                "--registry",
                str(registry.registry_file),
            ],
            cwd=ROOT,
            env={"PATH": os.defpath},
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr,
            bufsize=0,
        )
        buffered = b""

        def send(message):
            process.stdin.write((json.dumps(message) + "\n").encode())

        def receive(expected_id):
            nonlocal buffered
            while True:
                while b"\n" not in buffered:
                    assert select.select([process.stdout], [], [], 15)[0], "STDIO response timeout"
                    chunk = os.read(process.stdout.fileno(), 65536)
                    assert chunk, "Unexpected STDIO EOF"
                    buffered += chunk
                line, buffered = buffered.split(b"\n", 1)
                message = json.loads(line)
                assert message["jsonrpc"] == "2.0"
                if message.get("id") == expected_id:
                    return message
                assert "method" in message

        try:
            send(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-11-25",
                        "capabilities": {},
                        "clientInfo": {"name": "protocol-test", "version": "1"},
                    },
                }
            )
            assert "result" in receive(1)
            send({"jsonrpc": "2.0", "method": "notifications/initialized"})
            send(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "name": "analyze_creatives",
                        "arguments": {"payload": payload},
                    },
                }
            )
            assert receive(2)["result"]["structuredContent"] == expected
        finally:
            process.stdin.close()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            remaining = buffered + process.stdout.read()
            process.stdout.close()
        for line in remaining.splitlines():
            assert json.loads(line)["jsonrpc"] == "2.0"
        assert process.returncode == 0

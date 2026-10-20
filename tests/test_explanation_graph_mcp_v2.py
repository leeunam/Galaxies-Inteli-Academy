"""Real MCP stdio parity; all M1-looking numbers/evidence here are invented."""

# ruff: noqa: F811

import asyncio
import json
import os
import sys
from dataclasses import asdict, replace

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from scripts.explanation_graph_service_v2 import ROOT, analyze_via_graph
from tests.native_v2_fixture import public_data
from tests.test_explanation_evidence import evidence_inputs  # noqa: F401
from tests.test_explanation_graph_service_v2 import graph_settings  # noqa: F401
from tests.test_explanation_session_v2 import invented_data  # noqa: F401
from tests.test_m1_service import serving  # noqa: F401


def transport(settings, tmp_path):
    source = tmp_path / "fixture-settings.json"
    source.write_text(json.dumps(asdict(settings), default=str))
    return StdioTransport(
        command=sys.executable,
        args=["-B", "-m", "tests.native_v2_mcp_fixture", str(source)],
        cwd=str(ROOT),
        env={"PYTHONDONTWRITEBYTECODE": "1"},
        keep_alive=False,
        log_file=tmp_path / "stdio.log",
    )


@pytest.mark.parametrize("count", [1, 3, 5])
def test_real_stdio_and_python_share_graph_service(graph_settings, tmp_path, monkeypatch, count):
    fixture = tmp_path / "public-fixture.json"
    fixture.write_text(json.dumps(public_data(count)))
    graph_settings = replace(
        graph_settings, worker_arguments_extra=("--fixture-json", str(fixture))
    )
    monkeypatch.setenv("NVIDIA_API_KEY", "PRIVATE_CREDENTIAL")
    request = {"brief": "PRIVATE_BRIEF"}

    async def scenario():
        direct = await analyze_via_graph(request, graph_settings)
        async with Client(transport(graph_settings, tmp_path)) as client:
            tools = await client.list_tools()
            assert {t.name for t in tools} == {
                "analyze_creatives",
                "analyze_creatives_with_explanation",
            }
            tool = next(t for t in tools if t.name.endswith("with_explanation"))
            fields = tool.input_schema["properties"]["payload"]["properties"]
            assert "worker_module" not in fields and "graph_python" not in fields
            reply = await client.call_tool(
                "analyze_creatives_with_explanation", {"payload": request}
            )
            assert reply.structured_content == direct

    asyncio.run(scenario())
    assert "PRIVATE" not in (tmp_path / "stdio.log").read_text()
    assert not list(graph_settings.scratch_root.iterdir())


def test_stdio_cancellation_propagates_to_external_supervisor(graph_settings, tmp_path):
    pids = tmp_path / "pids.json"
    settings = replace(
        graph_settings,
        worker_arguments_extra=graph_settings.worker_arguments_extra
        + ("--mode", "block", "--pid-file", str(pids)),
    )

    async def scenario():
        async with Client(transport(settings, tmp_path)) as client:
            task = asyncio.create_task(
                client.call_tool("analyze_creatives_with_explanation", {"payload": {}})
            )
            for _ in range(1000):
                if pids.exists():
                    break
                await asyncio.sleep(0.01)
            assert pids.exists()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            for _ in range(500):
                if not list(settings.scratch_root.iterdir()):
                    break
                await asyncio.sleep(0.01)
            assert not list(settings.scratch_root.iterdir())
            ids = json.loads(pids.read_bytes())
            for pid in (ids["worker"], ids["child"]):
                with pytest.raises(ProcessLookupError):
                    os.kill(pid, 0)

    asyncio.run(scenario())

"""Invented numerical service only, exercising complete graph/stdio boundaries."""

import asyncio
import json
import os
import random
import sys
from dataclasses import asdict
from pathlib import Path

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from scripts.explanation_graph_service_v2 import GraphSettings, analyze_via_graph
from scripts.independent_parity_observer import semantic
from tests.native_v2_fixture import public_data


async def scenario(folder):
    root = Path(__file__).resolve().parents[1]
    data = public_data(3)
    source = folder / "invented.json"
    source.write_text(json.dumps(data))
    settings = GraphSettings(
        root / "orchestration/.venv/bin/python",
        root / ".venv/bin/python",
        folder / "uploads",
        folder / "registry.json",
        folder / "native-scratch",
        worker_module="tests.native_v2_fixture",
        worker_arguments_extra=("--fixture-json", str(source)),
        timeout_seconds=30,
    )
    request = {
        "campaign_id": "invented",
        "sector": "moda",
        "objective": "divulgacao",
        "brief": "Entirely invented observer preflight",
        "creative_ids": [c["creative_id"] for c in data["report"]["candidates"]],
    }
    python = await analyze_via_graph(request, settings)
    config = folder / "settings.json"
    config.write_text(json.dumps(asdict(settings), default=str))
    transport = StdioTransport(
        command=sys.executable,
        args=["-B", "-m", "tests.native_v2_mcp_fixture", str(config)],
        cwd=str(root),
        env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1"},
        keep_alive=False,
        log_file=Path(os.devnull),
    )
    async with Client(transport) as client:
        reply = await client.call_tool("analyze_creatives_with_explanation", {"payload": request})
    assert python == reply.structured_content
    assert python["analysis"] == data["report"] and python["evidence_packet"] is not None
    assert not list(settings.scratch_root.iterdir())
    # A read-only snapshot must preserve already initialized generator state.
    import numpy as np

    from scripts.independent_parity_observer import state_snapshot

    before = (random.getstate(), semantic(np.random.get_state()))
    state_snapshot()
    assert (random.getstate(), semantic(np.random.get_state())) == before
    (folder / "response.json").write_text(json.dumps(python, allow_nan=False))
    print('{"invented_routes_equal":true,"rng_unchanged":true,"real_model_calls":0}')


if __name__ == "__main__":
    if "--observer-required" in sys.argv[2:]:
        assert sys.getprofile() is not None, "invented_target_startup_observer_required"
    asyncio.run(scenario(Path(sys.argv[1])))

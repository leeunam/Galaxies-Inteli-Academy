import asyncio
import json
import os
import sys

import pytest

from galaxies_orchestration.graph import build_graph
from galaxies_orchestration.worker import ROOT, RootWorker, WorkerError


def test_real_two_environment_stdio_graph_and_invalid_request():
    async def scenario():
        async with RootWorker() as worker:
            result = (await build_graph(worker).ainvoke({"payload": {}}))["result"]
            assert result["analysis"]["error"]["code"] == "invalid_request"
            assert result["explanation"]["reason_code"] == "m1_prediction_required"
        assert worker.process.returncode is not None

    assert sys.prefix != str(ROOT / ".venv")
    assert "catboost" not in sys.modules
    asyncio.run(scenario())


def test_worker_timeout_kills_and_reaps_process():
    async def scenario():
        async with RootWorker(timeout_seconds=0.0001) as worker:
            pid = worker.process.pid
            with pytest.raises(WorkerError, match="worker_failed"):
                await worker.request({"op": "prepare", "payload": {}})
            assert worker.process.returncode is not None
            with pytest.raises(ProcessLookupError):
                os.kill(pid, 0)

    asyncio.run(scenario())


def test_child_environment_drops_credentials_and_proxy(monkeypatch):
    from unittest.mock import AsyncMock

    seen = []

    async def spawn(*args, **kwargs):
        seen.append(kwargs["env"])
        return AsyncMock(returncode=0)

    monkeypatch.setenv("NVIDIA_API_KEY", "PRIVATE_SENTINEL")
    monkeypatch.setenv("HTTPS_PROXY", "PRIVATE_PROXY")
    monkeypatch.setenv("LANGSMITH_API_KEY", "PRIVATE_SENTINEL")
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)

    async def scenario():
        async with RootWorker():
            pass

    asyncio.run(scenario())
    assert "PRIVATE" not in json.dumps(seen)
    assert seen[0]["LANGSMITH_TRACING"] == "false"

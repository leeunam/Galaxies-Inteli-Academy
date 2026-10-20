"""Actual graph/subgraph; real stdio root validator with public invented evidence."""

import asyncio
import json
import os
import subprocess
from pathlib import Path

import pytest

from galaxies_orchestration.integrated_graph_v2 import build_graph
from galaxies_orchestration.integrated_worker_v2 import IntegratedWorker

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def root_python():
    value = os.environ.get("GALAXIES_ROOT_PYTHON")
    if not value:
        pytest.skip("Explicit root interpreter required")
    return Path(value)


@pytest.mark.parametrize("count", [1, 3, 5])
@pytest.mark.parametrize("selection", ["valid", "wrong_hash", "failure", "unicode"])
def test_real_graph_and_root_session_validate_closed_selection(
    root_python, tmp_path, count, selection
):
    fixture = tmp_path / "invented.json"
    create = subprocess.run(
        [
            str(root_python),
            "-B",
            "-c",
            f"import json; from tests.native_v2_fixture import public_data; print(json.dumps(public_data({count})))",
        ],
        cwd=ROOT,
        capture_output=True,
        check=True,
        timeout=15,
        env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    fixture.write_bytes(create.stdout)
    expected = json.loads(create.stdout)["report"]
    checkpoints, calls = [], []

    async def select(request):
        calls.append(request)
        body = json.loads(request)
        assert "PRIVATE_BRIEF" not in request
        if selection == "failure":
            raise RuntimeError("PRIVATE_ERROR")
        if selection == "unicode":
            return "\ud800"
        return json.dumps(
            {
                "packet_sha256": body["packet_sha256"] if selection == "valid" else "0" * 64,
                "evidence_ids": ["c1_shap_speech_embedding"],
            }
        )

    async def scenario():
        from langgraph.graph.state import CompiledStateGraph

        async with IntegratedWorker(
            root_python, ROOT, ("--fixture-json", str(fixture)), module="tests.native_v2_fixture"
        ) as worker:
            graph = build_graph(worker, select, checkpoint=checkpoints.append)
            assert isinstance(graph, CompiledStateGraph)
            assert [n for n, _ in graph.get_subgraphs()] == ["explain"]
            assert set(graph.get_graph().nodes) >= {
                "extract_predict_and_rank",
                "native_shap",
                "training_comparables",
                "bind_context",
            }
            return (await graph.ainvoke({"payload": {"brief": "PRIVATE_BRIEF"}}))["result"]

    result = asyncio.run(scenario())
    assert checkpoints == [expected]
    assert result["analysis"] == expected
    assert len(calls) == 1
    assert result["explanation"]["status"] == (
        "validated_catalogue_selection" if selection == "valid" else "incomplete"
    )
    assert result["explanation"]["adherence_status"] == "not_evaluated"
    assert not result["orchestration"]["real_provider_verified"]
    assert "PRIVATE_ERROR" not in json.dumps(result)


def test_subgraph_cancellation_does_not_render_or_repeat():
    class Worker:
        def __init__(self):
            self.calls = []

        async def request(self, message):
            self.calls.append(message["op"])
            if message["op"] == "analyze":
                return {"analysis": {"invented": True}, "native_feature_handoff": False}
            if message["op"] == "context":
                return {"packet": {"invented": True}, "packet_sha256": "a" * 64, "reason": None}
            return {}

    async def scenario():
        entered = asyncio.Event()

        async def select(_):
            entered.set()
            await asyncio.Event().wait()

        worker = Worker()
        task = asyncio.create_task(build_graph(worker, select).ainvoke({"payload": {}}))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert worker.calls == ["analyze", "shap", "comparables", "context"]

    asyncio.run(scenario())

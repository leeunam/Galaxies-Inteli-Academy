import asyncio
import json
import socket

import pytest


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("network_forbidden")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)


class Worker:
    def __init__(self, ready=True):
        self.calls = []
        self.ready = ready

    async def request(self, message):
        self.calls.append(message)
        if message["op"] == "prepare":
            return {
                "packet": {"evidence": [{"evidence_id": "invented"}]} if self.ready else None,
                "packet_sha256": "a" * 64 if self.ready else None,
                "reason": None if self.ready else "m1_prediction_required",
            }
        return {"analysis": {"invented_q50": 123}, "selection": message["selection"]}


def test_actual_compiled_graph_executes_explainer_subgraph_once():
    from langgraph.graph.state import CompiledStateGraph

    from galaxies_orchestration.graph import build_graph

    worker, calls = Worker(), []

    async def select(request):
        calls.append(request)
        body = json.loads(request)
        assert body["packet_sha256"] == "a" * 64
        return json.dumps({"packet_sha256": "a" * 64, "evidence_ids": ["invented"]})

    graph = build_graph(worker, select)
    assert isinstance(graph, CompiledStateGraph)
    assert [name for name, _ in graph.get_subgraphs()] == ["explain"]
    result = asyncio.run(graph.ainvoke({"payload": {"brief": "PRIVATE_BRIEF"}}))
    assert list(result) == ["result"]
    assert result["result"]["analysis"] == {"invented_q50": 123}
    assert result["result"]["orchestration"]["stategraph_executed"] is True
    assert len(calls) == 1 and "PRIVATE_BRIEF" not in calls[0]
    assert [m["op"] for m in worker.calls] == ["prepare", "render"]


@pytest.mark.parametrize("ready", [True, False])
def test_missing_transport_or_non_m1_does_not_select(ready):
    from galaxies_orchestration.graph import build_graph

    worker = Worker(ready)
    result = asyncio.run(build_graph(worker).ainvoke({"payload": {}}))["result"]
    assert worker.calls[-1]["selection"] is None
    assert worker.calls[-1]["reason"] == (
        "transport_not_configured" if ready else "m1_prediction_required"
    )
    assert result["orchestration"]["kind"] == "isolated_stategraph"


@pytest.mark.parametrize("fault", ["failure", "oversize", "wrong_type"])
def test_selection_failure_is_sanitized_and_never_retried(fault):
    from galaxies_orchestration.graph import build_graph

    worker, calls = Worker(), []

    async def select(request):
        calls.append(request)
        if fault == "failure":
            raise RuntimeError("PRIVATE_PROVIDER_BODY")
        return "x" * 16385 if fault == "oversize" else {}

    result = asyncio.run(build_graph(worker, select).ainvoke({"payload": {}}))
    assert len(calls) == 1
    assert worker.calls[-1]["selection"] is None
    assert worker.calls[-1]["reason"] == "transport_failed"
    assert "PRIVATE_PROVIDER_BODY" not in json.dumps(result)


def test_cancellation_propagates_without_render_or_retry():
    from galaxies_orchestration.graph import build_graph

    async def scenario():
        worker, entered = Worker(), asyncio.Event()

        async def select(request):
            entered.set()
            await asyncio.Event().wait()

        task = asyncio.create_task(build_graph(worker, select).ainvoke({"payload": {}}))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert len(worker.calls) == 1

    asyncio.run(scenario())

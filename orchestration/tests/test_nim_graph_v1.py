"""Compiled integrated graph/subgraph, real ROOT IPC, fake provider only."""

import asyncio
import copy
import os
from pathlib import Path

import pytest
from langgraph.graph.state import CompiledStateGraph

from galaxies_orchestration import nim_graph_v1 as probe
from galaxies_orchestration.nim_graph_contract_v1 import fixture


@pytest.fixture
def root_python():
    value = os.environ.get("GALAXIES_ROOT_PYTHON")
    if not value:
        pytest.skip("Explicit existing root interpreter required")
    return Path(value)


@pytest.mark.parametrize("case", ["valid", "wrong_hash", "secret_id", "http_error", "invalid_wire"])
def test_compiled_graph_calls_root_selector_once_between_context_and_render(
    root_python, monkeypatch, case
):
    original = probe.build_graph
    graphs = []

    def build(worker, selector):
        graph = original(worker, selector)
        graphs.append(graph)
        assert isinstance(graph, CompiledStateGraph)
        assert [name for name, _ in graph.get_subgraphs()] == ["explain"]
        assert set(graph.get_graph().nodes) >= {
            "extract_predict_and_rank",
            "native_shap",
            "training_comparables",
            "bind_context",
        }
        return graph

    monkeypatch.setattr(probe, "build_graph", build)
    output = asyncio.run(probe.run_offline(root_python, case))
    assert len(graphs) == 1
    result, proof = output["legacy_result"], output["current_provider"]
    assert result["analysis"] == fixture()["data"]["report"]
    assert result["evidence_packet"] == fixture()["request"]["packet"]
    assert proof["events"] == [
        "analyze",
        "shap",
        "comparables",
        "context",
        "select",
        "render",
        "proof",
    ]
    assert proof["selector_invocations"] == 1
    assert result["orchestration"]["explainer_subgraph_executed"] is True
    assert result["orchestration"]["native_feature_handoff"] is False
    assert result["orchestration"]["real_provider_verified"] is False
    assert proof["real_provider_verified"] is False
    assert proof["origin"] == "offline_fake" and proof["real_http_requests"] == 0
    assert proof["root_render_accepted"] is (case == "valid")
    if case == "valid":
        allowed = {fact["evidence_id"]: fact for fact in fixture()["request"]["packet"]["evidence"]}
        for claim in result["explanation"]["claims"]:
            assert claim == allowed[claim["evidence_id"]]
        assert result["explanation"]["adherence_status"] == "not_evaluated"


@pytest.mark.parametrize(
    "field,value",
    [
        ("run_id", "b" * 32),
        ("packet_sha256", "0" * 64),
        ("origin", "live_nim"),
        ("live_dispatch", {"cached": True}),
        ("real_http_requests", 1),
        ("root_render_accepted", False),
    ],
)
def test_cached_or_forged_receipt_cannot_become_current_real_proof(root_python, field, value):
    output = asyncio.run(probe.run_offline(root_python))
    original = output["current_provider"]
    fields = {
        "origin",
        "run_id",
        "packet_sha256",
        "real_http_requests",
        "live_dispatch",
        "root_selection_accepted",
        "root_render_accepted",
        "transport",
        "events",
    }
    proof = {key: copy.deepcopy(original[key]) for key in fields}
    proof[field] = value
    with pytest.raises(ValueError):
        probe.current_provider(proof, output["legacy_result"], original["run_id"], selector_calls=1)


def track_processes(monkeypatch):
    original = asyncio.create_subprocess_exec
    processes = []

    async def spawn(*args, **kwargs):
        process = await original(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    return processes


def test_deadline_kills_and_reaps_without_retry(root_python, monkeypatch):
    processes = track_processes(monkeypatch)
    with pytest.raises(TimeoutError):
        asyncio.run(probe.run_offline(root_python, "hang", timeout=1.5))
    assert len(processes) == 1 and processes[0].returncode is not None
    assert not Path(f"/proc/{processes[0].pid}").exists()


def test_cancel_during_selector_reaps_and_propagates(root_python, monkeypatch):
    processes = track_processes(monkeypatch)
    original = probe.RootSelector.__call__

    async def scenario():
        entered = asyncio.Event()

        async def select(self, request):
            entered.set()
            return await original(self, request)

        monkeypatch.setattr(probe.RootSelector, "__call__", select)
        task = asyncio.create_task(probe.run_offline(root_python, "hang"))
        await asyncio.wait_for(entered.wait(), 5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    assert len(processes) == 1 and processes[0].returncode is not None


def test_cancel_during_spawn_never_releases_graph_work(root_python, monkeypatch):
    original = asyncio.create_subprocess_exec
    processes, requests = [], []

    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()

        async def spawn(*args, **kwargs):
            process = await original(*args, **kwargs)
            processes.append(process)
            entered.set()
            await release.wait()
            return process

        async def request(*args):
            requests.append(True)
            raise AssertionError("cancelled_spawn_must_not_release_work")

        monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
        monkeypatch.setattr(probe.ProbeWorker, "request", request)
        task = asyncio.create_task(probe.run_offline(root_python))
        await asyncio.wait_for(entered.wait(), 5)
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    assert requests == []
    assert len(processes) == 1 and processes[0].returncode is not None

"""Actual graph/subgraph and root IPC with invented responses and false provider proof."""

import asyncio
import os
from pathlib import Path

import pytest
from langgraph.graph.state import CompiledStateGraph

from galaxies_orchestration import nim_diagnostic_graph_v1 as new
from galaxies_orchestration.nim_graph_contract_v1 import fixture
from galaxies_orchestration.nim_graph_v1 import run_offline as baseline


@pytest.fixture
def root_python():
    value = os.environ.get("GALAXIES_ROOT_PYTHON")
    if not value:
        pytest.skip("Explicit existing root interpreter required")
    return Path(value)


@pytest.mark.parametrize(
    "case,code",
    [
        ("valid", "accepted"),
        ("wrong_hash", "packet_hash_mismatch"),
        ("secret_id", "unknown_evidence_id"),
        ("too_many_ids", "schema_constraint"),
        ("duplicate_ids", "duplicate_evidence_id"),
        ("scalar_ids", "schema_invalid_type"),
        ("extra_field", "schema_extra_field"),
        ("deep_json", "json_depth_limit"),
        ("http_error", "http_error"),
        ("invalid_wire", "envelope_json_syntax"),
    ],
)
def test_compiled_select_preserves_authority_and_returns_safe_diagnostic(
    root_python, monkeypatch, case, code
):
    original = new.build_graph

    def build(worker, selector):
        graph = original(worker, selector)
        assert isinstance(graph, CompiledStateGraph)
        assert [name for name, _ in graph.get_subgraphs()] == ["explain"]
        return graph

    monkeypatch.setattr(new, "build_graph", build)
    output = asyncio.run(new.run_offline(root_python, case))
    assert output["selection_diagnostic"]["code"] == code
    assert output["legacy_result"]["analysis"] == fixture()["data"]["report"]
    assert output["current_provider"]["real_provider_verified"] is False
    assert output["current_provider"]["real_http_requests"] == 0
    assert output["legacy_result"]["orchestration"]["native_feature_handoff"] is False
    assert output["legacy_result"]["orchestration"]["real_provider_verified"] is False
    if case in {"valid", "wrong_hash", "secret_id", "http_error", "invalid_wire"}:
        before = asyncio.run(baseline(root_python, case))
        assert output["legacy_result"] == before["legacy_result"]
        assert {k: v for k, v in output["current_provider"].items() if k != "run_id"} == {
            k: v for k, v in before["current_provider"].items() if k != "run_id"
        }


def test_timeout_reaps_only_root_worker(root_python, monkeypatch):
    original = asyncio.create_subprocess_exec
    processes = []

    async def spawn(*args, **kwargs):
        process = await original(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    with pytest.raises(TimeoutError):
        asyncio.run(new.run_offline(root_python, "hang", timeout=1.5))
    assert len(processes) == 1 and processes[0].returncode is not None
    assert not Path(f"/proc/{processes[0].pid}").exists()


def test_cancelled_spawn_never_releases_work_and_reaps(root_python, monkeypatch):
    original = asyncio.create_subprocess_exec
    processes = []

    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()

        async def spawn(*args, **kwargs):
            process = await original(*args, **kwargs)
            processes.append(process)
            entered.set()
            await release.wait()
            return process

        monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
        task = asyncio.create_task(new.run_offline(root_python))
        await asyncio.wait_for(entered.wait(), 5)
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    assert len(processes) == 1 and processes[0].returncode is not None

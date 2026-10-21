"""Existing compiled graph and actual direct ROOT child; every network is fake."""

import asyncio
import copy
import json
import os
from pathlib import Path

import pytest
from langgraph.graph.state import CompiledStateGraph

from galaxies_orchestration import nim_graph_live_contract_v1 as c
from galaxies_orchestration import nim_graph_live_v1 as live
from galaxies_orchestration.nim_graph_contract_v1 import fixture


@pytest.fixture
def root_python():
    value = os.environ.get("GALAXIES_ROOT_PYTHON")
    if not value:
        pytest.skip("Explicit existing root interpreter required")
    return Path(value)


def test_review_missing_stops_before_reservation_or_worker(root_python, tmp_path, monkeypatch):
    monkeypatch.setattr(c, "REVIEW", tmp_path / "missing.json")

    def forbidden(*a, **kw):
        raise AssertionError("review_must_fail_before_reservation")

    monkeypatch.setattr(c, "reserve", forbidden)
    with pytest.raises(FileNotFoundError):
        asyncio.run(live.execute_once(root_python))
    assert not c.LEDGER.exists()


@pytest.mark.parametrize("case", ["valid", "wrong_hash", "secret_id", "http_error", "invalid_wire"])
def test_fresh_compiled_select_dispatches_once_with_real_parent_binding(
    root_python, tmp_path, monkeypatch, case
):
    original = live.build_graph
    graphs = []

    def build(worker, selector):
        graph = original(worker, selector)
        assert isinstance(graph, CompiledStateGraph)
        assert [name for name, _ in graph.get_subgraphs()] == ["explain"]
        graphs.append(graph)
        return graph

    monkeypatch.setattr(live, "build_graph", build)
    folder = tmp_path / case
    receipt = asyncio.run(live.simulate(case, folder, worker_python=root_python))
    assert receipt["outcome"] == "observed"
    assert len(graphs) == 1
    result, proof = receipt["result"]["legacy_result"], receipt["result"]["current_provider"]
    assert result["analysis"] == fixture()["data"]["report"]
    assert result["evidence_packet"] == fixture()["request"]["packet"]
    assert result["orchestration"]["real_provider_verified"] is False
    assert result["orchestration"]["native_feature_handoff"] is False
    assert proof["real_provider_verified"] is False and proof["live_dispatch"] is None
    assert proof["root_render_accepted"] is (case == "valid")
    assert proof["events"] == [
        "analyze",
        "shap",
        "comparables",
        "context",
        "select",
        "render",
        "proof",
    ]
    assert proof["selector_invocations"] == 1 and proof["real_http_requests"] == 0
    # Old authorize() accepted the actual graph PID/child PPID without overrides.
    assert (folder / "dispatch-v3.json").exists()
    assert json.loads((folder / "reservation-v3.json").read_bytes())["parent_pid"] == os.getpid()
    assert (folder.stat().st_mode & 0o777) == 0o700
    assert all((path.stat().st_mode & 0o777) == 0o600 for path in folder.iterdir())
    with pytest.raises(FileExistsError):
        asyncio.run(live.simulate(case, folder, worker_python=root_python))
    retained = b"".join(path.read_bytes() for path in folder.iterdir())
    assert b"ENTIRELY_INVENTED_SECRET" not in retained


def test_simulations_reject_all_old_and_new_real_namespaces(root_python):
    for name in (
        "issue-5-nim-sintetico-unico-v1",
        "issue-5-nim-dispatch-v3",
        "issue-5-nim-release-v1",
        "issue-5-nim-release-v1-review",
        "issue-5-nim-typed-request-v1",
        "issue-5-nim-typed-request-v1-review",
        "issue-5-nim-graph-live-v1",
        "issue-5-nim-graph-live-v1-review",
    ):
        for folder in (
            c.ROOT / "data/private" / name,
            c.ROOT / "data/private" / name / "invented-child",
        ):
            with pytest.raises(ValueError):
                asyncio.run(live.simulate("valid", folder, worker_python=root_python))


def track(monkeypatch):
    original = asyncio.create_subprocess_exec
    processes = []

    async def spawn(*args, **kwargs):
        process = await original(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    return processes


def test_timeout_closes_sole_root_worker_and_consumes_without_orphan(
    root_python, tmp_path, monkeypatch
):
    processes = track(monkeypatch)
    folder = tmp_path / "timeout"
    receipt = asyncio.run(live.simulate("hang", folder, worker_python=root_python, timeout=1.5))
    assert receipt["outcome"] == "timeout_outcome_uncertain"
    assert len(processes) == 1 and processes[0].returncode is not None
    assert not Path(f"/proc/{processes[0].pid}").exists()
    assert (folder / "dispatch-v3.json").exists()
    with pytest.raises(FileExistsError):
        asyncio.run(live.simulate("valid", folder, worker_python=root_python))


def test_cancel_after_durable_dispatch_reaps_and_never_retries(root_python, tmp_path, monkeypatch):
    processes = track(monkeypatch)
    folder = tmp_path / "cancel"

    async def scenario():
        task = asyncio.create_task(live.simulate("hang", folder, worker_python=root_python))
        async with asyncio.timeout(5):
            while not (folder / "dispatch-v3.json").exists():
                await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    assert len(processes) == 1 and processes[0].returncode is not None
    assert not Path(f"/proc/{processes[0].pid}").exists()
    receipt = json.loads((folder / "graph-result-live-v1.json").read_bytes())
    assert receipt["outcome"] == "cancelled_outcome_uncertain"
    with pytest.raises(FileExistsError):
        asyncio.run(live.simulate("valid", folder, worker_python=root_python))


def test_cancel_during_spawn_does_not_release_nonce_or_select(root_python, tmp_path, monkeypatch):
    original = asyncio.create_subprocess_exec
    processes = []
    folder = tmp_path / "cancel-spawn"

    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()

        async def spawn(*args, **kwargs):
            process = await original(*args, **kwargs)
            processes.append(process)
            entered.set()
            await release.wait()
            return process

        monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
        task = asyncio.create_task(live.simulate("valid", folder, worker_python=root_python))
        await asyncio.wait_for(entered.wait(), 5)
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    assert len(processes) == 1 and processes[0].returncode is not None
    assert not (folder / "dispatch-v3.json").exists()
    assert (
        json.loads((folder / "graph-result-live-v1.json").read_bytes())["outcome"]
        == "cancelled_outcome_uncertain"
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("run_id", "b" * 32),
        ("origin", "live_nim"),
        ("real_http_requests", 1),
        ("live_dispatch", {"cached": True}),
    ],
)
def test_cached_or_fake_proof_never_verifies_live(root_python, tmp_path, monkeypatch, field, value):
    folder = tmp_path / "proof"
    reserve = c.reserve
    nonces = []

    def capture_nonce(*args, **kwargs):
        directory, nonce = reserve(*args, **kwargs)
        nonces.append(nonce)
        return directory, nonce

    monkeypatch.setattr(c, "reserve", capture_nonce)
    receipt = asyncio.run(live.simulate("valid", folder, worker_python=root_python))
    original = receipt["result"]["current_provider"]
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
    bound = json.loads((folder / "live-graph-binding.json").read_bytes())
    assert (
        live.provider_proof(
            proof,
            receipt["result"]["legacy_result"],
            bound,
            folder,
            nonces[0],
            offline=True,
            calls=1,
        )["real_provider_verified"]
        is False
    )
    proof[field] = value
    with pytest.raises(ValueError):
        live.provider_proof(
            proof,
            receipt["result"]["legacy_result"],
            bound,
            folder,
            nonces[0],
            offline=True,
            calls=1,
        )

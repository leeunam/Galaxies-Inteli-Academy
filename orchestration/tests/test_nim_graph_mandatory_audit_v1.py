"""One new fake graph execution: omitted mandatory limits are appended by root."""

import asyncio
import http.client
import os
import socket
from pathlib import Path

import pytest
from langgraph.graph.state import CompiledStateGraph

from galaxies_orchestration import nim_graph_live_v1 as live
from galaxies_orchestration.nim_graph_contract_v1 import fixture


@pytest.mark.parametrize("case", ["valid", "wrong_hash"])
def test_existing_compiled_three_graph_mandatories_and_rejection_notice(
    tmp_path, monkeypatch, case
):
    value = os.environ.get("GALAXIES_ROOT_PYTHON")
    if not value:
        pytest.skip("Explicit existing root interpreter required")

    def forbidden(*args, **kwargs):
        raise AssertionError("offline_audit_forbids_parent_network")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(http.client.HTTPSConnection, "request", forbidden)
    original = live.build_graph

    def build(worker, selector):
        graph = original(worker, selector)
        assert isinstance(graph, CompiledStateGraph)
        assert [name for name, _ in graph.get_subgraphs()] == ["explain"]
        return graph

    monkeypatch.setattr(live, "build_graph", build)
    original_select = live.RootSelector.__call__
    selector_events = []

    async def select(self, request):
        selector_events.append("called")
        try:
            return await original_select(self, request)
        except ValueError:
            selector_events.append("none_selection_refused")
            raise

    monkeypatch.setattr(live.RootSelector, "__call__", select)
    # Sealed offline-case valid sends nine IDs, omitting all three limit_* IDs.
    # The unchanged root worker has explicit offline mode and no credential path.
    receipt = asyncio.run(
        live.simulate(case, tmp_path / "invented-audit", worker_python=Path(value))
    )
    assert receipt["outcome"] == "observed"
    result, proof = receipt["result"]["legacy_result"], receipt["result"]["current_provider"]
    assert result["analysis"] == fixture()["data"]["report"]
    claims = {claim["evidence_id"] for claim in result["explanation"]["claims"]}
    if case == "valid":
        assert {
            "limit_target",
            "limit_quality",
            "limit_interpretation",
            "c1_prediction",
            "c2_prediction",
            "c3_prediction",
        } <= claims
        assert len(claims) == 12 and proof["root_render_accepted"] is True
        assert selector_events == ["called"]
    else:
        assert not claims and proof["root_render_accepted"] is False
        assert proof["transport"]["http_status"] == 200
        assert proof["transport"]["code"] == "selection_rejected"
        assert result["explanation"]["reason_code"] == "transport_failed"
        assert selector_events == ["called", "none_selection_refused"]
    assert result["orchestration"]["real_provider_verified"] is False
    assert result["orchestration"]["native_feature_handoff"] is False
    assert proof["real_provider_verified"] is False and proof["real_http_requests"] == 0

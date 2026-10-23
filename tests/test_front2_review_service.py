"""Shared Python/MCP contracts with explicitly invented analysis/evidence."""

import asyncio
import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from scripts import explanation_review_service_v1 as service
from scripts.campaign_evidence_v1 import CampaignCase, brief_digest
from scripts.explanation_evidence import build_explanation_context, validate_selection
from scripts.explanation_graph_service_v2 import GraphSettings
from scripts.explanation_review_mcp_v1 import create_server, public_example
from scripts.explanation_review_service_v1 import ReviewSettings, analyze_reviewed
from scripts.m1_evidence import M1Evidence
from scripts.training_comparables import ComparableResult
from tests.native_v2_fixture import public_data

ROOT = Path(__file__).resolve().parents[1]


def payload(count):
    data = public_data(count)
    return {
        "campaign_id": "invented",
        "creative_ids": [c["creative_id"] for c in data["report"]["candidates"]],
        "sector": "moda",
        "objective": "divulgacao",
        "brief": "PRIVATE_SENTINEL",
    }


def graph_result(count):
    data = public_data(count)
    context = build_explanation_context(
        data["report"],
        shap={k: M1Evidence.model_validate_json(json.dumps(v)) for k, v in data["shap"].items()},
        comparables={
            k: ComparableResult.model_validate_json(json.dumps(v))
            for k, v in data["comparables"].items()
        },
    )
    # One zero group and the explicit no-reference reason per candidate suffice.
    ids = [
        f"c{i}_{suffix}"
        for i in range(1, count + 1)
        for suffix in ("shap_sector", "references_missing")
    ]
    selected = validate_selection(
        context, json.dumps({"packet_sha256": context.packet_sha256, "evidence_ids": ids})
    )
    return selected | {
        "schema_version": "creative-explanation-integrated-v2",
        "evidence_packet": context.packet.model_dump(mode="json"),
        "orchestration": {
            "kind": "integrated_stategraph_v2",
            "stategraph_executed": False,
            "explainer_subgraph_executed": False,
            "native_feature_handoff": False,
            "real_provider_verified": False,
            "selector_kind": "trusted_local_callback",
        },
    }


async def fake_graph(request, settings):
    return graph_result(len(request["creative_ids"]))


@pytest.fixture
def settings(tmp_path):
    return ReviewSettings(
        GraphSettings(
            Path(sys.executable),
            Path(sys.executable),
            tmp_path / "uploads",
            tmp_path / "registry.json",
            tmp_path / "scratch",
        ),
        data_origin="invented",
    )


@pytest.mark.parametrize("count", [1, 3, 5])
def test_python_and_mcp_share_exact_numeric_objects_and_review(settings, monkeypatch, count):
    calls = []

    async def observed(request, graph):
        calls.append(request)
        return await fake_graph(request, graph)

    monkeypatch.setattr(service, "analyze_via_graph", observed)
    request = payload(count)

    async def scenario():
        direct = await analyze_reviewed(request, settings)
        async with Client(create_server(settings)) as client:
            tools = await client.list_tools()
            tool = next(t for t in tools if t.name == "analyze_creatives_reviewed")
            assert set(tool.input_schema["properties"]) == {"payload"}
            properties = tool.input_schema["properties"]["payload"]["properties"]
            assert set(properties) == set(request)
            response = await client.call_tool(tool.name, {"payload": request})
            assert response.structured_content == direct
        assert direct["source_result"] == graph_result(count)
        assert direct["quality_review"]["status"] == "sufficient_for_exploratory_comparison"
        assert direct["campaign_adherence"]["status"] == "not_evaluated"
        assert not direct["integration_receipt"]["final_configuration_validated"]
        assert not direct["integration_receipt"]["fresh_media_extraction_proven_by_this_receipt"]
        assert direct["integration_receipt"]["training_reference_matches"] == 0
        assert direct["integration_receipt"]["training_reference_absence_notices"] == count
        assert direct["integration_receipt"]["cleanup"] == "not_observed_in_simulated_source"
        assert "PRIVATE_SENTINEL" not in json.dumps(direct)
        assert direct["source_result"]["orchestration"]["stategraph_executed"] is False
        # All zero is explicit, without pretending the zero group explains ordering.
        assert "todos os grupos SHAP do catálogo vinculado são zero" in direct["display_text"]

    asyncio.run(scenario())
    assert len(calls) == 2


@pytest.mark.parametrize(
    "bad",
    [
        {},
        payload(5) | {"creative_ids": payload(5)["creative_ids"] * 2},
        payload(1) | {"path": "PRIVATE_PATH"},
        payload(1) | {"brief": None},
    ],
)
def test_invalid_inputs_do_not_launch_graph_or_echo_private_values(settings, monkeypatch, bad):
    async def forbidden(*args):
        raise AssertionError("should_not_start")

    monkeypatch.setattr(service, "analyze_via_graph", forbidden)
    result = asyncio.run(analyze_reviewed(bad, settings))
    assert result["reason_code"] == "invalid_request"
    assert result["integration_receipt"]["invocation"] == "not_started"
    assert result["source_result"]["error"]["code"] == "invalid_request"
    assert "PRIVATE" not in json.dumps(result)


@pytest.mark.parametrize("reason", ["no_packet", "bad_claim", "graph_error"])
def test_failed_review_preserves_checkpoint_and_does_not_invent_support(
    settings, monkeypatch, reason
):
    source = graph_result(3)
    if reason == "no_packet":
        source["evidence_packet"] = None
    if reason == "bad_claim":
        source["explanation"]["claims"][0]["statement_pt"] = "invented wrong claim"
    if reason == "graph_error":
        source = {"orchestration_error": "local_graph_failed"}
    before = copy.deepcopy(source)

    async def failed(*args):
        return source

    monkeypatch.setattr(service, "analyze_via_graph", failed)
    result = asyncio.run(analyze_reviewed(payload(3), settings))
    assert result["review_status"] == "unavailable"
    assert result["source_result"] == source == before
    assert result["quality_review"] is None
    if reason == "graph_error":
        assert result["integration_receipt"]["cleanup"] == "not_inferred_for_error"


def test_registry_change_invalidates_adherence_but_not_numeric_result(settings, monkeypatch):
    request = payload(1)
    case = CampaignCase(
        case_id="invented",
        brief_id="invented",
        campaign_id="invented",
        sector="moda",
        purpose="campaign",
        data_origin="invented",
        brief_sha256=brief_digest(request["brief"]),
        requirements=({"requirement_id": "r1", "attribute": "portrait", "expected": True},),
        media=({"creative_id": request["creative_ids"][0], "media_sha256": "a" * 64},),
        observations=(),
    )
    settings = ReviewSettings(settings.graph, cases=(case,), data_origin="invented")
    values = iter([{request["creative_ids"][0]: "a" * 64}, {request["creative_ids"][0]: "b" * 64}])
    monkeypatch.setattr(service, "registry_bindings", lambda *a: next(values))
    monkeypatch.setattr(service, "analyze_via_graph", fake_graph)
    result = asyncio.run(analyze_reviewed(request, settings))
    assert result["reason_code"] == "campaign_binding_failed"
    assert result["source_result"] == graph_result(1)


def test_cancel_and_timeout_propagate_without_restarting_or_creating_a_fallback(
    settings, monkeypatch
):
    calls = []

    async def delayed(*args):
        calls.append(True)
        await asyncio.sleep(60)

    monkeypatch.setattr(service, "analyze_via_graph", delayed)

    async def scenario():
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(analyze_reviewed(payload(1), settings), 0.02)

    asyncio.run(scenario())
    assert len(calls) == 1


@pytest.mark.parametrize("count", [1, 3, 5])
def test_real_stdio_with_fake_graph_equals_python(settings, monkeypatch, tmp_path, count):
    monkeypatch.setattr(service, "analyze_via_graph", fake_graph)
    transport = StdioTransport(
        command=sys.executable,
        args=["-B", "-m", "tests.front2_mcp_fixture"],
        cwd=str(ROOT),
        env={
            "PATH": os.defpath,
            "PYTHONDONTWRITEBYTECODE": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
        },
        keep_alive=False,
        log_file=tmp_path / "stdio.log",
    )

    async def scenario():
        expected = await analyze_reviewed(payload(count), settings)
        async with Client(transport) as client:
            result = await client.call_tool(
                "analyze_creatives_reviewed", {"payload": payload(count)}
            )
            assert result.structured_content == expected

    asyncio.run(asyncio.wait_for(scenario(), 30))
    assert "PRIVATE_SENTINEL" not in (tmp_path / "stdio.log").read_text()
    assert not settings.graph.scratch_root.exists()


def test_public_cli_is_reproducible_and_explicitly_invented():
    result = public_example()
    assert result["quality_review"]["status"] == "sufficient_for_exploratory_comparison"
    assert result["campaign_adherence"]["status"] == "partial"
    assert result["review_provenance"]["input_origin_declared_by_operator"] == "invented"
    assert (
        result["review_provenance"]["selection_origin"] == "authored_local_public_example_not_nim"
    )
    run = subprocess.run(
        [sys.executable, "-B", "-m", "scripts.explanation_review_mcp_v1", "--public-example"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=20,
        check=True,
    )
    assert json.loads(run.stdout) == result
    assert not run.stderr


def test_graph_launch_exception_is_fixed_and_does_not_echo_private_path(settings, monkeypatch):
    async def failed(*args):
        raise OSError("PRIVATE_PATH PRIVATE_BRIEF")

    monkeypatch.setattr(service, "analyze_via_graph", failed)
    result = asyncio.run(analyze_reviewed(payload(1), settings))
    assert result["source_result"] == {"orchestration_error": "local_graph_failed"}
    assert result["review_status"] == "unavailable"
    assert "PRIVATE" not in json.dumps(result)

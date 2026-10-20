"""Additive MCP contract tests; all media, M1 outputs and transports are synthetic."""

import asyncio
import json
import sys
from pathlib import Path

import pytest
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from scripts.creative_contracts import AnalysisRequest
from scripts.explanation_transport import TransportReply
from tests.test_explanation_composition import local_service, synthetic_evidence  # noqa: F401
from tests.test_explanation_transport import deny_network  # noqa: F401
from tests.test_m1_service import payload, serving  # noqa: F401


@pytest.mark.parametrize("count", [1, 3, 5])
def test_mcp_composition_parity(local_service, registry, count):  # noqa: F811
    from scripts.explanation_composition import analyze_with_explanation
    from scripts.explanation_mcp import create_server

    settings, ids, _ = local_service

    async def transport(request):
        body = json.loads(request.payload_json)
        return TransportReply(
            content=json.dumps(
                {
                    "packet_sha256": body["packet_sha256"],
                    "evidence_ids": ["c1_shap_speech_embedding", "c1_reference_1"],
                }
            )
        )

    server = create_server(
        registry, m1=settings, evidence_provider=synthetic_evidence, transport=transport
    )

    async def exercise():
        request = payload(ids[:count])
        direct = await analyze_with_explanation(
            request,
            registry,
            m1=settings,
            evidence_provider=synthetic_evidence,
            transport=transport,
        )
        async with Client(server) as client:
            legacy = (
                await client.call_tool("analyze_creatives", {"payload": request})
            ).structured_content
            response = await client.call_tool(
                "analyze_creatives_with_explanation", {"payload": request}
            )
            assert not response.is_error
            composed = response.structured_content
            assert composed["analysis"] == legacy == direct["analysis"]
            assert composed["explanation"] == direct["explanation"]
            assert composed["orchestration"] == direct["orchestration"]
            for result in (direct, composed):
                assert result["explanation_transport"]["attempts"] == 1
                assert result["explanation_transport"]["real_provider_verified"] is False
            assert "PRIVATE_BRIEF" not in json.dumps(composed)

    asyncio.run(exercise())


@pytest.mark.parametrize("mode", ["default", "synthetic", "observed"])
def test_stdio_extension_parity(local_service, registry, tmp_path, mode):  # noqa: F811
    from scripts.explanation_composition import analyze_with_explanation

    settings, ids, _ = local_service
    args = []
    kwargs = {}
    if mode == "synthetic":
        args = ["--synthetic-baseline"]
        kwargs = {"synthetic_baseline": True}
    if mode == "observed":
        args = ["--observed-baseline-dir", str(settings.cohort_dir)]
        kwargs = {"observed_baseline_dir": settings.cohort_dir}
    log = tmp_path / "extension-stderr.txt"
    transport = StdioTransport(
        command=sys.executable,
        args=[
            "-m",
            "scripts.explanation_mcp",
            "--uploads-root",
            str(registry.uploads_root),
            "--registry",
            str(registry.registry_file),
            *args,
        ],
        cwd=str(Path(__file__).resolve().parents[1]),
        env={},
        keep_alive=False,
        log_file=log,
    )

    async def exercise():
        async with Client(transport) as client:
            tools = {t.name: t for t in await client.list_tools()}
            assert set(tools) == {"analyze_creatives", "analyze_creatives_with_explanation"}
            published = tools["analyze_creatives_with_explanation"].input_schema["properties"][
                "payload"
            ]
            assert set(published["properties"]) == set(
                AnalysisRequest.model_json_schema()["properties"]
            )
            assert published["additionalProperties"] is False
            assert tools["analyze_creatives_with_explanation"].output_schema is not None
            requests = [payload(ids[:n]) for n in (1, 3, 5)] + [
                payload(ids[:1]) | {"transport": "PRIVATE_ENDPOINT"},
                payload([ids[0]] * 2),
                "PRIVATE_BAD_PAYLOAD",
            ]
            for request in requests:
                direct = await analyze_with_explanation(request, registry, **kwargs)
                old = (
                    await client.call_tool("analyze_creatives", {"payload": request})
                ).structured_content
                result = await client.call_tool(
                    "analyze_creatives_with_explanation", {"payload": request}
                )
                assert not result.is_error
                assert result.structured_content == direct
                assert result.structured_content["analysis"] == old
                assert result.structured_content["explanation_transport"]["attempts"] == 0
                assert "PRIVATE" not in json.dumps(result.structured_content)

    asyncio.run(exercise())
    assert "PRIVATE" not in log.read_text()

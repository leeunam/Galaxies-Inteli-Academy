"""One independent complete production route; private offline operator only."""

import argparse
import asyncio
import json
import os
import sys
from dataclasses import replace
from pathlib import Path

from scripts.demo_recovery_mcp_only import transport_arguments
from scripts.demo_recovery_native import graph_settings
from scripts.demo_recovery_policy import exclusive_json, read_json


async def run(config, route, output):
    from scripts.explanation_graph_service_v2 import IntegratedResponse, analyze_via_graph

    if sys.getprofile() is None:
        raise RuntimeError("observer_required")
    original = Path(config["run_dir"])
    request = read_json(original / "request.json")
    settings = graph_settings(config)
    scratch = output.parent / "scratch" / route / "graph"
    settings = replace(
        settings, scratch_root=scratch, m1=replace(settings.m1, scratch_root=scratch.parent)
    )
    exclusive_json(
        output.with_suffix(".invocation.json"),
        {
            "route": route,
            "request": request,
            "registry": read_json(original / "registry.json"),
            "configuration": config,
            "effective_worker_arguments_without_run_suffix": settings.arguments(scratch),
            "timeout_seconds": settings.timeout_seconds,
            "worker_module": settings.worker_module,
            "worker_python": str(settings.worker_python),
            "graph_python": str(settings.graph_python),
            "application_cache_used_as_acceptance": False,
            "one_call_reserved_before_invocation": True,
        },
    )
    if route == "python":
        result = await analyze_via_graph(request, settings)
    else:
        from fastmcp import Client
        from fastmcp.client.transports import StdioTransport

        transport = StdioTransport(
            command=sys.executable,
            args=transport_arguments(settings),
            cwd=str(Path(__file__).resolve().parents[1]),
            env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1", "OPENBLAS_NUM_THREADS": "1"},
            keep_alive=False,
            log_file=Path(os.devnull),
        )
        async with Client(transport) as client:
            catalogue = await client.list_tools()
            if {tool.name for tool in catalogue} != {
                "analyze_creatives",
                "analyze_creatives_with_explanation",
            }:
                raise RuntimeError("tool_catalogue_changed")
            response = await client.call_tool(
                "analyze_creatives_with_explanation",
                {"payload": request},
                timeout=config["analysis_seconds"],
            )
            result = response.structured_content
    # Persist the ENTIRE original response, before any acceptance/projection.
    exclusive_json(output, result)
    validated = IntegratedResponse.model_validate_json(json.dumps(result, allow_nan=False))
    if validated.model_dump(mode="json") != result:
        raise RuntimeError("response_roundtrip_changed")
    if (
        not result["orchestration"]["stategraph_executed"]
        or not result["orchestration"]["explainer_subgraph_executed"]
        or not result["orchestration"]["native_feature_handoff"]
        or result["evidence_packet"] is None
        or not result["analysis"]["learned_prediction_available"]
        or any(c["prediction"]["status"] != "estimated" for c in result["analysis"]["candidates"])
    ):
        raise RuntimeError("incomplete_native_route_preserved")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("route", choices=("python", "mcp"))
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        asyncio.run(run(read_json(args.config), args.route, args.output))
    except Exception:  # noqa: BLE001 - never expose raw private exceptions
        print('{"route_completed":false}')
        raise SystemExit(1) from None
    print('{"route_completed":true}')


if __name__ == "__main__":
    main()

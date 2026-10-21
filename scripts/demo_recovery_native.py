"""Late-imported native stage; no fixture, VLM invocation, training or provider.

The frozen shared extractor also calculates CLIP and uses four CPU threads.
Its include_vlm=False path is preserved, not replaced or patched here.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import sys
from pathlib import Path

from scripts.demo_recovery_policy import RecoveryError, exclusive_json, read_json


def prepare(config):
    from scripts.creative_registry import CreativeRegistry

    root = Path(config["run_dir"])
    registry = CreativeRegistry(root / "inputs", root / "registry.json")
    ids = []
    for row in config["inputs"]:
        result = registry.register(
            {
                "campaign_id": config["campaign_id"],
                "sector": "beleza",
                "relative_path": row["relative_path"],
            }
        )
        if result.get("status") != "registered":
            raise RecoveryError("native_registration_failed")
        current = read_json(root / "registry.json")["creatives"][result["creative_id"]]["media"]
        # Compare measured container duration, not yt-dlp's possibly rounded
        # metadata duration. A new acquisition is not historical byte identity.
        expected_duration = config["previous_duration_seconds"][row["alias"]]
        if abs(current["duration_seconds"] - expected_duration) > 0.15:
            raise RecoveryError("registered_duration_changed")
        ids.append(result["creative_id"])
    request = {
        "campaign_id": config["campaign_id"],
        "sector": "beleza",
        "objective": "divulgacao",
        "brief": "Demonstração técnica local: comparar três referências históricas de beleza; não é avaliação prospectiva ou campanha original das publicações.",
        "creative_ids": ids,
    }
    exclusive_json(root / "request.json", request)
    return {"status": "registered", "creative_count": len(ids)}


def graph_settings(config):
    from scripts.explanation_graph_service_v2 import GraphSettings
    from scripts.m1_service import M1Settings

    root = Path(config["run_dir"])
    return GraphSettings(
        graph_python=Path(config["graph_python"]),
        worker_python=Path(sys.executable),
        uploads_root=root / "inputs",
        registry_file=root / "registry.json",
        scratch_root=root / "scratch/native-runs",
        m1=M1Settings(Path(config["model_dir"]), Path(config["cohort_dir"]), root / "scratch"),
        evidence_root=Path(config["evidence_root"]),
        minimum_similarity=0.5,
        # The production worker/default selector remain unchanged.
        timeout_seconds=config["analysis_seconds"],
    )


async def analyze(config, route):
    from scripts.explanation_graph_service_v2 import analyze_via_graph

    request = read_json(Path(config["run_dir"]) / "request.json")
    settings = graph_settings(config)
    task = asyncio.current_task()
    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGTERM, task.cancel)
    if route == "python":
        return await analyze_via_graph(request, settings)

    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    args = [
        "-B",
        "-m",
        "scripts.explanation_graph_mcp_v2",
        "--graph-python",
        str(settings.graph_python),
        "--worker-python",
        str(settings.worker_python),
        "--uploads-root",
        str(settings.uploads_root),
        "--registry",
        str(settings.registry_file),
        "--scratch-root",
        str(settings.scratch_root),
        "--m1-model-dir",
        str(settings.m1.model_dir),
        "--m1-cohort-dir",
        str(settings.m1.cohort_dir),
        "--evidence-root",
        str(settings.evidence_root),
        "--minimum-similarity",
        "0.5",
    ]
    transport = StdioTransport(
        command=sys.executable,
        args=args,
        cwd=str(Path(__file__).resolve().parents[1]),
        env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1", "OPENBLAS_NUM_THREADS": "1"},
        keep_alive=False,
        log_file=os.devnull,
    )
    async with Client(transport) as client:
        tools = await client.list_tools()
        if {tool.name for tool in tools} != {
            "analyze_creatives",
            "analyze_creatives_with_explanation",
        }:
            raise RecoveryError("unexpected_native_tools")
        result = await client.call_tool(
            "analyze_creatives_with_explanation",
            {"payload": request},
            timeout=config["analysis_seconds"],
        )
    return result.structured_content


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("route", choices=["prepare", "python", "mcp"])
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    try:
        config = read_json(args.config)
        result = (
            prepare(config) if args.route == "prepare" else asyncio.run(analyze(config, args.route))
        )
        encoded = json.dumps(result, allow_nan=False).encode()
        if len(encoded) > 65536:
            raise RecoveryError("native_result_limit")
    except Exception:  # noqa: BLE001 - private inputs and native exception suppressed
        # No exception/raw input/path is emitted.
        encoded = b'{"recovery_error":"native_stage_failed"}'
    sys.stdout.buffer.write(encoded + b"\n")


if __name__ == "__main__":
    main()

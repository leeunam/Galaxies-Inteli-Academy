"""One corrected MCP route; private supplemental operator/supervisor required.

Reuses the original request/configuration. No acquisition or direct Python
analysis route is available. The only transport fix is Path(os.devnull).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import sys
from pathlib import Path

from scripts.demo_recovery_native import graph_settings
from scripts.demo_recovery_policy import RecoveryError, exclusive_json, read_json


def transport_arguments(settings):
    return [
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


async def analyze(config, progress):
    from fastmcp import Client
    from fastmcp.client.transports import StdioTransport

    request = read_json(Path(config["run_dir"]) / "request.json")
    settings = graph_settings(config)
    task = asyncio.current_task()
    asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, task.cancel)
    transport = StdioTransport(
        command=sys.executable,
        args=transport_arguments(settings),
        cwd=str(Path(__file__).resolve().parents[1]),
        env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1", "OPENBLAS_NUM_THREADS": "1"},
        keep_alive=False,
        log_file=Path(os.devnull),
    )
    async with Client(transport) as client:
        tools = await client.list_tools()
        if {tool.name for tool in tools} != {
            "analyze_creatives",
            "analyze_creatives_with_explanation",
        }:
            raise RecoveryError("unexpected_native_tools")
        exclusive_json(progress / "tools-listed.json", {"expected_tools": True})
        exclusive_json(progress / "call-reserved.json", {"single_analysis_call": True})
        result = await client.call_tool(
            "analyze_creatives_with_explanation",
            {"payload": request},
            timeout=config["analysis_seconds"],
        )
    return result.structured_content


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--progress", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = asyncio.run(analyze(read_json(args.config), args.progress))
        encoded = json.dumps(result, allow_nan=False).encode()
        if len(encoded) > 65536:
            raise RecoveryError("native_result_limit")
    except Exception:  # noqa: BLE001 - no raw media or exception forwarded
        encoded = b'{"recovery_error":"native_stage_failed"}'
    sys.stdout.buffer.write(encoded + b"\n")


if __name__ == "__main__":
    main()

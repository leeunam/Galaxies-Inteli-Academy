"""Opt-in stdio MCP server for the shared isolated StateGraph service."""

import argparse
import logging
import sys
from pathlib import Path

from pydantic import TypeAdapter

from scripts.creative_mcp import AnalysisPayload
from scripts.creative_mcp import create_server as create_base_server
from scripts.creative_registry import CreativeRegistry
from scripts.explanation_graph_service_v2 import (
    ROOT,
    GraphError,
    GraphSettings,
    IntegratedResponse,
    analyze_via_graph,
)
from scripts.m1_service import M1Settings


def create_server(settings):
    registry = CreativeRegistry(settings.uploads_root, settings.registry_file)
    server = create_base_server(
        registry,
        m1=settings.m1,
        synthetic_baseline=settings.synthetic_baseline,
        observed_baseline_dir=settings.observed_baseline_dir,
    )

    @server.tool(
        name="analyze_creatives_with_explanation",
        timeout=510,
        output_schema={
            "type": "object",
            **TypeAdapter(IntegratedResponse | GraphError).json_schema(),
        },
        annotations={"readOnlyHint": True, "idempotentHint": False, "openWorldHint": False},
    )
    async def analyze(payload: AnalysisPayload) -> dict:
        """Executa StateGraph local, SHAP e referências; sem provedor externo configurado."""
        return await analyze_via_graph(payload, settings)

    return server


def parse_settings():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph-python", type=Path, required=True)
    parser.add_argument("--worker-python", type=Path, default=Path(sys.executable))
    parser.add_argument("--uploads-root", type=Path, default=ROOT / "uploads")
    parser.add_argument(
        "--registry", type=Path, default=ROOT / "data/private/creative-registry.json"
    )
    parser.add_argument(
        "--scratch-root", type=Path, default=ROOT / "data/private/integrated-v2-runs"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--m1-model-dir", type=Path)
    mode.add_argument("--synthetic-baseline", action="store_true")
    mode.add_argument("--observed-baseline-dir", type=Path)
    parser.add_argument("--m1-cohort-dir", type=Path)
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--minimum-similarity", type=float)
    parser.add_argument("--request-file", type=Path, help="Run Python service once instead of MCP")
    args = parser.parse_args()
    if bool(args.m1_model_dir) != bool(args.m1_cohort_dir):
        parser.error("M1 requires model and cohort")
    settings = GraphSettings(
        args.graph_python,
        args.worker_python,
        args.uploads_root,
        args.registry,
        args.scratch_root,
        m1=M1Settings(args.m1_model_dir, args.m1_cohort_dir, args.scratch_root)
        if args.m1_model_dir
        else None,
        evidence_root=args.evidence_root,
        minimum_similarity=args.minimum_similarity,
        synthetic_baseline=args.synthetic_baseline,
        observed_baseline_dir=args.observed_baseline_dir,
    )
    return settings, args.request_file


def main():
    settings, request_file = parse_settings()
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr, force=True)
    if request_file:
        import asyncio
        import json

        try:
            raw = request_file.read_bytes()
            if len(raw) > 262144:
                raise ValueError("input_limit")
            print(
                json.dumps(
                    asyncio.run(analyze_via_graph(json.loads(raw), settings)), allow_nan=False
                )
            )
        except Exception:  # noqa: BLE001 - private input/path/exception suppressed
            print('{"orchestration_error":"local_graph_failed"}')
    else:
        create_server(settings).run(transport="stdio", show_banner=False, log_level="WARNING")


if __name__ == "__main__":
    main()

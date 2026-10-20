"""Opt-in additive MCP adapter for the local composition; no NIM or StateGraph."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from scripts.creative_mcp import AnalysisPayload
from scripts.creative_mcp import create_server as create_base_server
from scripts.creative_registry import CreativeRegistry
from scripts.explanation_composition import ExplainedAnalysis, analyze_with_explanation
from scripts.explanation_transport import TransportLimits

ROOT = Path(__file__).resolve().parents[1]


def create_server(
    registry,
    *,
    synthetic_baseline=False,
    observed_baseline_dir=None,
    m1=None,
    evidence_provider=None,
    transport=None,
    limits: TransportLimits | None = None,
):
    """Retain the existing tool and add a composition using operator-only callbacks."""
    limits = TransportLimits() if limits is None else TransportLimits.model_validate(limits)
    server = create_base_server(
        registry,
        synthetic_baseline=synthetic_baseline,
        observed_baseline_dir=observed_baseline_dir,
        m1=m1,
    )

    @server.tool(
        name="analyze_creatives_with_explanation",
        output_schema=ExplainedAnalysis.model_json_schema(),
        timeout=480,
        annotations={"readOnlyHint": True, "idempotentHint": False, "openWorldHint": False},
    )
    async def analyze(payload: AnalysisPayload) -> dict:
        """Compõe análise e catálogo local; sem StateGraph, NIM real ou aderência validada."""
        return await analyze_with_explanation(
            payload,
            registry,
            synthetic_baseline=synthetic_baseline,
            observed_baseline_dir=observed_baseline_dir,
            m1=m1,
            evidence_provider=evidence_provider,
            transport=transport,
            limits=limits,
        )

    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uploads-root", type=Path, default=ROOT / "uploads")
    parser.add_argument(
        "--registry", type=Path, default=ROOT / "data/private/creative-registry.json"
    )
    baseline = parser.add_mutually_exclusive_group()
    baseline.add_argument("--synthetic-baseline", action="store_true")
    baseline.add_argument("--observed-baseline-dir", type=Path)
    parser.add_argument("--m1-model-dir", type=Path)
    parser.add_argument("--m1-cohort-dir", type=Path)
    args = parser.parse_args()
    if bool(args.m1_model_dir) != bool(args.m1_cohort_dir):
        parser.error("--m1-model-dir and --m1-cohort-dir must be provided together")
    if args.m1_model_dir and (args.synthetic_baseline or args.observed_baseline_dir):
        parser.error("Choose a single model or baseline source")
    m1 = None
    if args.m1_model_dir:
        from scripts.m1_service import M1Settings

        m1 = M1Settings(args.m1_model_dir, args.m1_cohort_dir)
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr, force=True)
    server = create_server(
        CreativeRegistry(args.uploads_root, args.registry),
        synthetic_baseline=args.synthetic_baseline,
        observed_baseline_dir=args.observed_baseline_dir,
        m1=m1,
    )
    server.run(transport="stdio", show_banner=False, log_level="WARNING")


if __name__ == "__main__":
    main()

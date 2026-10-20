"""Operator-only native verification with generated media and invented features."""

import argparse
import asyncio
import json
import os
import sys
from dataclasses import asdict, replace
from pathlib import Path
from tempfile import TemporaryDirectory

from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from scripts.creative_registry import CreativeRegistry
from scripts.demo_creatives import make_synthetic_video
from scripts.explanation_graph_service_v2 import ROOT, GraphSettings, analyze_via_graph
from scripts.m1_handoff_v2 import M1_A200_SHA256
from scripts.m1_service import M1Settings


async def verify(args):
    args.output_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    with TemporaryDirectory(dir=args.output_dir, prefix="generated-media-") as folder:
        work = Path(folder)
        registry = CreativeRegistry(work / "uploads", work / "registry.json")
        ids = []
        for i in range(3):
            make_synthetic_video(registry.uploads_root / f"blank-{i}.mp4")
            row = registry.register(
                {
                    "campaign_id": "native-synthetic-verification",
                    "sector": "moda",
                    "relative_path": f"blank-{i}.mp4",
                }
            )
            ids.append(row["creative_id"])
        payload = {
            "campaign_id": "native-synthetic-verification",
            "creative_ids": ids,
            "sector": "moda",
            "objective": "divulgacao",
            "brief": "Invented verification only",
        }
        settings = GraphSettings(
            args.graph_python,
            Path(sys.executable),
            registry.uploads_root,
            registry.registry_file,
            work / "scratch",
            m1=M1Settings(args.model_dir, args.cohort_dir),
            evidence_root=args.evidence_root,
            minimum_similarity=0.5,
            worker_module="tests.native_v2_native_worker",
        )
        direct = await analyze_via_graph(payload, settings)
        assert direct["analysis"]["model_artifact_sha256"] == M1_A200_SHA256
        assert direct["analysis"]["status"] == "m1_prediction_available"
        assert direct["orchestration"]["native_feature_handoff"]
        assert direct["explanation"]["reason_code"] == "transport_not_configured"
        facts = direct["evidence_packet"]["evidence"]
        assert sum("_shap_" in row["evidence_id"] for row in facts) == 12
        assert sum("_reference" in row["evidence_id"] for row in facts) >= 3
        source = work / "operator-settings.json"
        source.write_text(json.dumps(asdict(settings), default=str))
        log = args.output_dir / "mcp-stderr.txt"
        transport = StdioTransport(
            command=sys.executable,
            args=["-B", "-m", "tests.native_v2_mcp_fixture", str(source)],
            cwd=str(ROOT),
            env={"PYTHONDONTWRITEBYTECODE": "1"},
            keep_alive=False,
            log_file=log,
        )
        async with Client(transport) as client:
            reply = await client.call_tool(
                "analyze_creatives_with_explanation", {"payload": payload}
            )
            assert not reply.is_error
            assert reply.structured_content == direct
        assert not list(settings.scratch_root.iterdir())
        assert "Invented verification only" not in log.read_text()
        # Default production launcher really runs the unchanged extractor. In
        # this isolated checkout its encoders were deliberately not copied.
        missing_weights_checked = False
        if args.verify_missing_extractor_weights:
            production = await analyze_via_graph(
                payload, replace(settings, worker_module="scripts.explanation_worker_v2")
            )
            assert production["analysis"]["status"] == "m1_prediction_incomplete"
            assert {
                c["prediction"]["reason_code"] for c in production["analysis"]["candidates"]
            } == {"model_weights_unavailable"}
            assert not list(settings.scratch_root.iterdir())
            missing_weights_checked = True
        receipt = {
            "verification_kind": "native_predictor_synthetic_feature_queries",
            "media_extraction": "invented_fixture_for_positive_path",
            "predictor": "native_m1_a200",
            "shap": "native_catboost_q50_log1p",
            "training_index": "served_a200_124_only",
            "python_mcp_stdio_equal": True,
            "stategraph_executed": True,
            "candidates": 3,
            "shap_facts": 12,
            "comparable_matches": sum("_reference_" in row["evidence_id"] for row in facts),
            "queries_without_matches": sum(
                "_references_missing" in row["evidence_id"] for row in facts
            ),
            "real_provider_verified": False,
            "adherence_status": "not_evaluated",
            "default_extractor_missing_weights_explicit": missing_weights_checked,
            "analysis": direct["analysis"],
            "evidence_packet": direct["evidence_packet"],
        }
        (args.output_dir / "native-verification.json").write_text(json.dumps(receipt, indent=2))
        os.chmod(args.output_dir / "native-verification.json", 0o600)
    print(
        json.dumps(
            {
                "native_bundle": "M1/A200",
                "synthetic_queries": 3,
                "native_shap_facts": 12,
                "python_mcp_stdio_equal": True,
                "real_media_demo": False,
                "provider_calls": 0,
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("model-dir", "cohort-dir", "evidence-root", "graph-python", "output-dir"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument(
        "--verify-missing-extractor-weights",
        action="store_true",
        help="Only for an isolated checkout known to lack encoder weights; never assume this after integration",
    )
    asyncio.run(verify(parser.parse_args()))

"""Opt-in real-model parity demo on operator-provided local media, never the holdout."""

import argparse
import asyncio
import json
import os
import shutil
import tempfile
import time
from pathlib import Path

from fastmcp import Client

from scripts.creative_analysis import analyze_creatives
from scripts.creative_contracts import M1AnalysisResponse
from scripts.creative_registry import CreativeRegistry
from scripts.demo_creatives import stdio_transport
from scripts.m1_service import M1Settings


async def demonstrate(media: Path, settings: M1Settings, sector: str, scratch_parent: Path):
    """Repeat one fixture as distinct registrations; no claim of independent creatives."""
    Path(scratch_parent).mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.TemporaryDirectory(prefix="m1-parity-", dir=scratch_parent) as folder:
        root = Path(folder)
        uploads = root / "uploads"
        uploads.mkdir()
        shutil.copyfile(media, uploads / "fixture.mp4")
        registry = CreativeRegistry(uploads, root / "registry.json")
        ids = []
        for _ in range(5):
            registration = registry.register(
                {"campaign_id": "m1demo", "sector": sector, "relative_path": "fixture.mp4"}
            )
            if registration["status"] != "registered":
                raise RuntimeError("demo_media_registration_failed")
            ids.append(registration["creative_id"])
        results = []
        stderr = root / "server-stderr.log"
        async with Client(stdio_transport(registry, m1=settings, log_file=stderr)) as client:
            for count in (1, 2, 5):
                print(
                    json.dumps({"stage": "parity_pair", "sector": sector, "count": count}),
                    flush=True,
                )
                request = {
                    "campaign_id": "m1demo",
                    "creative_ids": ids[:count],
                    "sector": sector,
                    "objective": "divulgacao",
                    "brief": "Demonstração técnica, não avaliação de qualidade.",
                }
                started = time.monotonic()
                direct = await asyncio.to_thread(analyze_creatives, request, registry, m1=settings)
                python_seconds = time.monotonic() - started
                M1AnalysisResponse.model_validate(direct)
                if direct["status"] != "m1_prediction_available":
                    raise RuntimeError("demo_learned_prediction_unavailable")
                started = time.monotonic()
                remote = await client.call_tool(
                    "analyze_creatives", {"payload": request}, timeout=480
                )
                mcp_seconds = time.monotonic() - started
                if remote.is_error or remote.structured_content != direct:
                    raise RuntimeError("demo_python_mcp_mismatch")
                if count > 1 and [e["rank"] for e in direct["ranking"]["entries"]] != [1] * count:
                    raise RuntimeError("demo_duplicate_fixture_must_tie")
                results.append(
                    {
                        "count": count,
                        "sector": sector,
                        "python_stdio_equal": True,
                        "python_seconds": python_seconds,
                        "mcp_seconds": mcp_seconds,
                        "response": direct,
                    }
                )
        # The extractor's own logs are discarded in its worker. Only fixed app states
        # should be in server stderr, without local paths or fixture contents.
        logs = stderr.read_text()
        if str(uploads) in logs or request["brief"] in logs:
            raise RuntimeError("demo_private_data_in_server_logs")
    return {
        "purpose": "technical_parity_not_predictive_evaluation",
        "counts": [1, 2, 5],
        "fixture_reused_across_ids": True,
        "independent_creatives": 1,
        "real_asr_embeddings_and_catboost": True,
        "feature_result_cache_used": False,
        "evaluation_labels_used": False,
        "evaluation_metrics_computed": False,
        "media_cohort_membership": "not_checked_operator_responsibility",
        "temporary_demo_directory_removed": not root.exists(),
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--media", required=True, type=Path)
    parser.add_argument("--sector", required=True, choices=("moda", "beleza"))
    parser.add_argument("--m1-model-dir", required=True, type=Path)
    parser.add_argument("--m1-cohort-dir", required=True, type=Path)
    parser.add_argument("--report-file", required=True, type=Path)
    args = parser.parse_args()
    if args.report_file.exists():
        parser.error("use a fresh report path")
    args.report_file.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    settings = M1Settings(args.m1_model_dir, args.m1_cohort_dir)
    result = asyncio.run(demonstrate(args.media, settings, args.sector, args.report_file.parent))
    with args.report_file.open("x") as output:
        os.chmod(args.report_file, 0o600)
        json.dump(result, output, indent=2, allow_nan=False)
    print(
        json.dumps(
            {
                "python_mcp_parities": len(result["results"]),
                "temporary_demo_directory_removed": result["temporary_demo_directory_removed"],
            }
        )
    )


if __name__ == "__main__":
    main()

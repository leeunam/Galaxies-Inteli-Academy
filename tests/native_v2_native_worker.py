"""EXPLICIT SYNTHETIC FEATURES; original extraction validation, native M1/SHAP/index.

Operator-only verification worker. Never the production default. No encoder,
media acquisition, training, tuning, holdout evidence or provider call.
"""

import argparse
import json
import sys
from pathlib import Path

from scripts.channel_partitions import digest
from scripts.creative_registry import CreativeRegistry
from scripts.explanation_session_v2 import create_session
from scripts.explanation_worker_v2 import serve
from scripts.m1_service import M1Settings


def invented_extractor(folder, count):
    request = json.loads((folder / "request.json").read_bytes())
    assert len(request["items"]) == count
    rows = []
    for i, item in enumerate(request["items"]):
        media = item["media"]
        rows.append(
            {
                "status": "completed",
                "reason_code": None,
                "extractor_config_sha256": digest(request["config"]),
                "inputs": {
                    "sector": item["sector"],
                    "duration_seconds": media["duration_seconds"],
                    "aspect_ratio_height_over_width": media["height"] / media["width"],
                    "text_status": "extracted",
                    "text_embedding": [1.0 if j == i else 0.0 for j in range(384)],
                },
            }
        )
    # The unchanged extractor checks count/configuration/properties and owns
    # media-copy validation and cleanup; the feature values are invented.
    with (folder / "result.json").open("x") as output:
        json.dump(rows, output, allow_nan=False)
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in (
        "uploads-root",
        "registry",
        "scratch-root",
        "m1-model-dir",
        "m1-cohort-dir",
        "evidence-root",
    ):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--minimum-similarity", type=float, required=True)
    args = parser.parse_args()
    session = create_session(
        CreativeRegistry(args.uploads_root, args.registry),
        m1=M1Settings(args.m1_model_dir, args.m1_cohort_dir, args.scratch_root),
        evidence_root=args.evidence_root,
        minimum_similarity=args.minimum_similarity,
        launcher=invented_extractor,
    )
    serve(session, sys.stdin.buffer, sys.stdout.buffer)


if __name__ == "__main__":
    main()

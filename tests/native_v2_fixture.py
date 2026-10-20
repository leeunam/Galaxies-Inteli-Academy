"""EXPLICIT OFFLINE SIMULATION. Fake model/features/SHAP/index, real session/IPC.

Never used by default production entrypoints. Contains no model/provider call.
"""

import argparse
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

from scripts.creative_contracts import M1AnalysisResponse
from scripts.explanation_session_v2 import Session
from scripts.explanation_worker_v2 import serve
from scripts.m1_evidence import GROUPS, GroupedDriver, M1Evidence
from scripts.training_comparables import ComparableResult
from scripts.training_manifest import PredictorInputs


def public_data(count=3):
    """Entirely invented values, with no private file or trained model dependency."""
    values = [200.0, 400.0, 400.0, 100.0, 300.0][:count]
    ids = ["cr_" + str(i + 1).zfill(32) for i in range(count)]
    candidates = [
        {
            "creative_id": cid,
            "extraction": {"status": "completed", "text_status": "extracted"},
            "prediction": {"value": v},
            "interval": {"lower_views": 10.0, "upper_views": 1000.0},
        }
        for cid, v in zip(ids, values, strict=True)
    ]
    baseline = {
        "sector": "moda",
        "central_views": 100.0,
        "sector_range": {"lower_views": 10.0, "sector_median_views": 100.0, "upper_views": 1000.0},
        "reference_samples": 124,
        "reference_channels": 50,
        "artifact_sha256": "b" * 64,
        "partition_manifest_sha256": "c" * 64,
        "cohort_release_sha256": "d" * 64,
    }
    ranking = (
        {"reason_code": "individual_analysis"}
        if count == 1
        else {
            "entries": [
                {
                    "creative_id": ids[i],
                    "value": values[i],
                    "rank": 1 + sum(v > values[i] for v in values),
                }
                for i in sorted(range(count), key=lambda i: -values[i])
            ]
        }
    )
    report = M1AnalysisResponse.model_validate(
        {
            "status": "m1_prediction_available",
            "campaign_id": "invented",
            "sector": "moda",
            "mode": "individual" if count == 1 else "comparative",
            "learned_prediction_available": True,
            "model_artifact_sha256": "a" * 64,
            "extractor_config_sha256": "e" * 64,
            "extraction_status": "completed",
            "baseline": baseline,
            "candidates": candidates,
            "ranking": ranking,
            "warnings": ["offline_invented_fixture_not_real_m1"],
        }
    ).model_dump(mode="json")
    shap = {
        cid: M1Evidence(
            model_artifact_sha256="a" * 64,
            prediction_log=math.log1p(v),
            base_value_log=math.log1p(v),
            drivers=tuple(GroupedDriver(group=g, contribution_log=0.0) for g, _ in GROUPS),
        ).model_dump(mode="json")
        for cid, v in zip(ids, values, strict=True)
    }
    empty = ComparableResult(
        model_artifact_sha256="a" * 64,
        cohort_sha256="d" * 64,
        partition_sha256="c" * 64,
        minimum_similarity=0.5,
        references=(),
        reason_code="no_matching_training_reference",
    )
    return {
        "report": report,
        "shap": shap,
        "comparables": {cid: empty.model_dump(mode="json") for cid in ids},
    }


def fixture_session(data):
    report = data["report"]
    ids = [
        c["creative_id"] for c in report["candidates"] if c["prediction"]["status"] == "estimated"
    ]
    queries = tuple(
        (
            cid,
            PredictorInputs(
                sector=report["sector"],
                duration_seconds=0.2,
                aspect_ratio_height_over_width=1.5,
                text_status="extracted",
                text_embedding=tuple([float(i + 1)] * 384),
            ),
            "f" * 64,
        )
        for i, cid in enumerate(ids)
    )
    handoff = SimpleNamespace(
        _features=None, ready_inputs=lambda _: queries, context=(None, None, None), settings=None
    )
    refs = iter(
        [ComparableResult.model_validate_json(json.dumps(data["comparables"][cid])) for cid in ids]
    )
    index = SimpleNamespace(
        training_samples=124,
        model_artifact_sha256=report["model_artifact_sha256"],
        search=lambda p, **kw: next(refs),
    )
    return Session(
        lambda _: (report, handoff),
        evidence_root=Path("invented"),
        minimum_similarity=0.5,
        shap_explainer=lambda *a: tuple(
            M1Evidence.model_validate_json(json.dumps(data["shap"][cid])) for cid in ids
        ),
        index_loader=lambda *a, **kw: index,
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-json", type=Path, required=True)
    parser.add_argument(
        "--mode", default="normal", choices=["normal", "crash", "block", "launch_failure"]
    )
    parser.add_argument("--pid-file", type=Path)
    args, _ = parser.parse_known_args()
    session = fixture_session(json.loads(args.fixture_json.read_bytes()))
    handle = session.handle

    def controlled(message):
        if message["op"] == "shap" and args.mode != "normal":
            if args.mode == "launch_failure":
                subprocess.Popen(["/definitely-absent-galaxies-test-executable"])
            # A real grandchild remains in the owned group even if this worker
            # exits abruptly. The external subreaper must collect it.
            child = subprocess.Popen([sys.executable, "-B", "-c", "import time; time.sleep(90)"])
            args.pid_file.write_text(
                json.dumps({"worker": os.getpid(), "child": child.pid, "pgid": os.getpgrp()})
            )
            if args.mode == "crash":
                os._exit(12)
            time.sleep(90)
        return handle(message)

    session.handle = controlled
    serve(session, sys.stdin.buffer, sys.stdout.buffer)


if __name__ == "__main__":
    main()

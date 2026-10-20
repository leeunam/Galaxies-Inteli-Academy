"""Two-message local stdio boundary, using only the unchanged root runtime."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scripts.creative_analysis import analyze_creatives
from scripts.creative_registry import CreativeRegistry
from scripts.explanation_composition import ExplanationNotice
from scripts.explanation_evidence import build_explanation_context, validate_selection

ROOT = Path(__file__).resolve().parents[1]
MAX_LINE_BYTES = 262144
REASONS = {"transport_not_configured", "transport_failed"}


class Session:
    def __init__(self, analyzer):
        self.analyzer = analyzer
        self.report = None
        self.context = None
        self.prepared = False
        self.finished = False
        self.reason = None

    def handle(self, message):
        if not self.prepared:
            if set(message) != {"op", "payload"} or message["op"] != "prepare":
                raise ValueError("invalid_worker_message")
            # Mark consumed before analysis; failures never allow a second extraction.
            self.prepared = True
            report = self.analyzer(message["payload"])
            self.report = json.dumps(report, allow_nan=False)
            if report.get("schema_version") != "creative-m1-v1":
                self.reason = "m1_prediction_required"
            elif not report["learned_prediction_available"]:
                self.reason = "learned_prediction_unavailable"
            else:
                try:
                    self.context = build_explanation_context(report)
                except Exception:  # noqa: BLE001 - preserve analysis on evidence failure
                    self.reason = "evidence_binding_failed"
            return {
                "packet": self.context.packet.model_dump(mode="json") if self.context else None,
                "packet_sha256": self.context.packet_sha256 if self.context else None,
                "reason": self.reason,
            }
        if (
            self.finished
            or set(message) != {"op", "selection", "reason"}
            or message["op"] != "render"
        ):
            raise ValueError("invalid_worker_message")
        self.finished = True
        reason = self.reason or message["reason"]
        if self.context and message["selection"] is not None:
            try:
                result = validate_selection(self.context, message["selection"])
                result["schema_version"] = "creative-explanation-stategraph-v1"
                return result
            except ValueError:
                reason = "invalid_selection"
        elif self.context and reason not in REASONS:
            raise ValueError("invalid_worker_message")
        return {
            "schema_version": "creative-explanation-stategraph-v1",
            "analysis": json.loads(self.report),
            "explanation": ExplanationNotice(
                reason_code=reason,
                packet_sha256=self.context.packet_sha256 if self.context else None,
            ).model_dump(mode="json"),
        }


def serve(session, source, target):
    for _ in range(2):
        raw = source.readline(MAX_LINE_BYTES + 1)
        if not raw:
            return
        try:
            if len(raw) > MAX_LINE_BYTES or not raw.endswith(b"\n"):
                raise ValueError("worker_input_limit")
            message = json.loads(raw)
            if type(message) is not dict:
                raise ValueError("invalid_worker_message")
            result = session.handle(message)
            encoded = json.dumps(result, allow_nan=False).encode() + b"\n"
            if len(encoded) > MAX_LINE_BYTES:
                raise ValueError("worker_output_limit")
        except Exception:  # noqa: BLE001 - no paths, raw input or traceback on stdio
            target.write(b'{"worker_error":"worker_failed"}\n')
            target.flush()
            return
        target.write(encoded)
        target.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uploads-root", type=Path, default=ROOT / "uploads")
    parser.add_argument(
        "--registry", type=Path, default=ROOT / "data/private/creative-registry.json"
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--synthetic-baseline", action="store_true")
    mode.add_argument("--observed-baseline-dir", type=Path)
    mode.add_argument("--m1-model-dir", type=Path)
    parser.add_argument("--m1-cohort-dir", type=Path)
    args = parser.parse_args()
    if bool(args.m1_model_dir) != bool(args.m1_cohort_dir):
        parser.error("M1 requires both model and cohort directories")
    m1 = None
    if args.m1_model_dir:
        from scripts.m1_service import M1Settings

        m1 = M1Settings(args.m1_model_dir, args.m1_cohort_dir)
    registry = CreativeRegistry(args.uploads_root, args.registry)
    session = Session(
        lambda payload: analyze_creatives(
            payload,
            registry,
            synthetic_baseline=args.synthetic_baseline,
            observed_baseline_dir=args.observed_baseline_dir,
            m1=m1,
        )
    )
    serve(session, sys.stdin.buffer, sys.stdout.buffer)


if __name__ == "__main__":
    main()

"""Request-private bindings around the unchanged M1 numerical authority.

Only load_model_context/extract_candidates are rebound in a private function
namespace. Both delegate at the original call site; nothing is pre-extracted.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import FunctionType

from pydantic import ValidationError

from scripts import candidate_features, m1_service
from scripts.channel_partitions import digest
from scripts.creative_analysis import analyze_creatives, determine_mode
from scripts.creative_contracts import AnalysisRequest, error_response
from scripts.creative_media import CreativeError

SOURCE_PINS = {
    "m1_service.py": "0f7254c88a396901bdef76777c68f59c891cbcf797e7195aecec0870521ce7bc",
    "creative_analysis.py": "61d4bef14dd9b63e818d8daa5261443384bbda26c5d7673b73d3f4c987841329",
    "candidate_features.py": "09f2993939d519a07795d5ca70fcd1d772740ea67a185962783edff138a0a70c",
}
M1_A200_SHA256 = "9dd1c7a2e35e32cf3068395ed8bf2e0561aa4fecded5c31754f981cc13d70d59"


def verify_sources():
    root = Path(__file__).resolve().parent
    if any(
        hashlib.sha256((root / n).read_bytes()).hexdigest() != h for n, h in SOURCE_PINS.items()
    ):
        raise ValueError("handoff_source_contract_changed")


def bind_private(function, bindings):
    """Copy a namespace, never mutate the original function/module globals."""
    allowed = (
        {"load_model_context", "extract_candidates"}
        if function is m1_service.serve_m1
        else {"_run_worker"}
        if function is candidate_features.extract_candidates
        else None
    )
    if allowed is None or set(bindings) != allowed:
        raise ValueError("unsupported_private_binding")
    namespace = function.__globals__.copy()
    namespace.update(bindings)
    bound = FunctionType(function.__code__, namespace, function.__name__, function.__defaults__)
    bound.__kwdefaults__ = function.__kwdefaults__.copy() if function.__kwdefaults__ else None
    return bound


class M1Handoff:
    """One-shot state owned by a trusted local session, never serialized to a host."""

    def __init__(self, registry, settings, *, launcher=None, expected_artifact=None):
        verify_sources()
        self.registry, self.settings = registry, settings
        self._launcher = launcher
        self._expected_artifact = expected_artifact
        self.consumed = False
        self.context = None
        self._request = self._records = self._features = self._binding = None
        self._context_used = self._extraction_used = False
        self._report_sha256 = None
        self._feature_sha256 = None

    def _load(self, settings):
        if self._context_used or settings is not self.settings:
            raise ValueError("handoff_context_mismatch")
        self._context_used = True
        # Delegate at the original call site, including all bundle/runtime guards.
        self.context = m1_service.load_model_context(settings)
        artifact = self.context[2].artifact
        if self._expected_artifact is not None and (
            artifact.artifact_sha256 != self._expected_artifact
            or len(artifact.training_sample_ids) != 124
        ):
            raise ValueError("integrated_m1_a200_required")
        return self.context

    def _snapshot(self, records, config):
        return digest(
            {
                "request": self._request.model_dump(mode="json"),
                "records": [(key, row.model_dump(mode="json")) for key, row in records.items()],
                "config": config,
                "artifact": self.context[2].artifact.artifact_sha256,
            }
        )

    def _extract(self, registry, records, config, scratch):
        if (
            self._extraction_used
            or registry is not self.registry
            or records is not self._records
            or scratch != self.settings.scratch_root
            or tuple(records) != tuple(self._request.creative_ids)
            or self.context is None
            or digest(config) != self.context[2].artifact.extractor_config_sha256
        ):
            raise ValueError("handoff_extraction_mismatch")
        self._extraction_used = True  # consumed before even attempting extraction
        before = self._snapshot(records, config)
        extractor = candidate_features.extract_candidates
        if self._launcher is not None:
            extractor = bind_private(extractor, {"_run_worker": self._launcher})
        results = tuple(extractor(registry, records, config, scratch))
        if self._snapshot(records, config) != before or len(results) != len(records):
            raise ValueError("handoff_extraction_mismatch")
        # Roundtrip freezes nested predictor inputs; no live list is shared.
        self._features = tuple(
            candidate_features.CandidateFeatures.model_validate_json(result.model_dump_json())
            for result in results
        )
        if any(r.extractor_config_sha256 != digest(config) for r in self._features):
            raise ValueError("handoff_extraction_mismatch")
        self._binding = before
        self._feature_sha256 = digest([r.model_dump(mode="json") for r in self._features])
        return self._features

    def analyze(self, payload):
        if self.consumed:
            raise ValueError("handoff_already_consumed")
        self.consumed = True
        report = self._analyze(payload)
        self._report_sha256 = digest(report)
        return report

    def _analyze(self, payload):
        try:
            self._request = AnalysisRequest.model_validate(payload)
        except ValidationError:
            return error_response("invalid_request")
        try:
            self._records = self.registry.validate_creatives(self._request)
        except CreativeError as error:
            return error_response(error.code)
        determine_mode(self._request.creative_ids)
        authority = bind_private(
            m1_service.serve_m1,
            {
                "load_model_context": self._load,
                "extract_candidates": self._extract,
            },
        )
        return authority(self._request, self.registry, self._records, self.settings)

    def ready_inputs(self, report):
        """Return bound inputs only for predictions actually returned by M1."""
        if self._report_sha256 is None or digest(report) != self._report_sha256:
            raise ValueError("handoff_report_mismatch")
        if self._features is None:
            return ()
        artifact = self.context[2].artifact
        if (
            digest([r.model_dump(mode="json") for r in self._features]) != self._feature_sha256
            or self._snapshot(self._records, artifact.extractor_config) != self._binding
            or report["model_artifact_sha256"] != artifact.artifact_sha256
            or report["extractor_config_sha256"] != artifact.extractor_config_sha256
            or tuple(c["creative_id"] for c in report["candidates"]) != tuple(self._records)
        ):
            raise ValueError("handoff_binding_mismatch")
        return tuple(
            (cid, result.inputs, record.media.sha256)
            for (cid, record), result, candidate in zip(
                self._records.items(), self._features, report["candidates"], strict=True
            )
            if candidate["prediction"]["status"] == "estimated" and result.status == "completed"
        )


def analyze_once(payload, registry, *, m1=None, launcher=None, expected_artifact=None, **baseline):
    """Baseline modes retain the original entry; M1 preserves the same validation."""
    if type(baseline.get("synthetic_baseline", False)) is not bool:
        raise TypeError("synthetic_baseline must be a boolean operator setting")
    if m1 is None:
        return analyze_creatives(payload, registry, **baseline), None
    if baseline.get("synthetic_baseline") or baseline.get("observed_baseline_dir") is not None:
        raise ValueError("Choose a single model or baseline source")
    handoff = M1Handoff(registry, m1, launcher=launcher, expected_artifact=expected_artifact)
    report = handoff.analyze(payload)
    # Snapshot numerics before evidence preparation can fail.
    return json.loads(json.dumps(report, allow_nan=False)), handoff

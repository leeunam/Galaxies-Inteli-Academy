"""Additive Python composition of the existing analyzer and local evidence boundary.

Operator callbacks are trusted local code, not tool inputs. This does not collect
SHAP/features automatically, execute StateGraph, or implement a real NIM client.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Literal

from pydantic import Field

from scripts.channel_partitions import Digest, FrozenContract
from scripts.creative_analysis import analyze_creatives
from scripts.creative_contracts import AnalysisResult
from scripts.explanation_evidence import EvidenceFact, build_explanation_context
from scripts.explanation_transport import TransportLimits, run_explanation
from scripts.m1_evidence import M1Evidence
from scripts.training_comparables import ComparableResult


@dataclass(frozen=True)
class LocalEvidence:
    shap: Mapping[str, M1Evidence] = field(default_factory=dict)
    comparables: Mapping[str, ComparableResult] = field(default_factory=dict)


class ExplanationNotice(FrozenContract):
    status: Literal["incomplete"] = "incomplete"
    kind: Literal["deterministic_notice"] = "deterministic_notice"
    reason_code: str = Field(pattern=r"^[a-z0-9_]{1,64}$")
    packet_sha256: Digest | None = None
    adherence_status: Literal["not_evaluated"] = "not_evaluated"
    claims: tuple[EvidenceFact, ...] = Field(default=(), max_length=0)


class CatalogueExplanation(FrozenContract):
    status: Literal["validated_catalogue_selection"]
    kind: Literal["deterministic_rendering_of_selected_evidence"]
    packet_sha256: Digest
    adherence_status: Literal["not_evaluated"]
    claims: tuple[EvidenceFact, ...] = Field(min_length=1)


class ExplanationTransportStatus(FrozenContract):
    kind: Literal["injected_transport"] = "injected_transport"
    attempts: int = Field(ge=0, le=2)
    elapsed_seconds: float = Field(ge=0)
    real_provider_verified: Literal[False] = False


class LocalOrchestration(FrozenContract):
    kind: Literal["plain_python_composition"] = "plain_python_composition"
    stategraph_executed: Literal[False] = False


class ExplainedAnalysis(FrozenContract):
    schema_version: Literal["creative-explanation-local-v1"] = "creative-explanation-local-v1"
    analysis: AnalysisResult
    explanation: ExplanationNotice | CatalogueExplanation
    explanation_transport: ExplanationTransportStatus
    orchestration: LocalOrchestration = Field(default_factory=LocalOrchestration)


async def analyze_with_explanation(
    payload,
    registry,
    *,
    synthetic_baseline=False,
    observed_baseline_dir=None,
    m1=None,
    evidence_provider: Callable[[dict], LocalEvidence] | None = None,
    transport=None,
    limits: TransportLimits | None = None,
) -> dict:
    """Analyze once, then enrich a copied report with bound local evidence.

    The optional synchronous provider receives only a disposable numeric report.
    It must use verified local outputs; this is not authentication of arbitrary JSON
    or a hard deadline/sandbox for operator callbacks. The existing transport owns
    its separate cooperative deadline and repair limit. Caller cancellation propagates.
    """
    limits = TransportLimits() if limits is None else TransportLimits.model_validate(limits)
    report = analyze_creatives(
        payload,
        registry,
        synthetic_baseline=synthetic_baseline,
        observed_baseline_dir=observed_baseline_dir,
        m1=m1,
    )
    snapshot = json.dumps(report, allow_nan=False)

    def finish(result=None, reason=None):
        if result is None:
            result = {
                "analysis": json.loads(snapshot),
                "explanation": ExplanationNotice(reason_code=reason).model_dump(mode="json"),
                "explanation_transport": ExplanationTransportStatus(
                    attempts=0, elapsed_seconds=0
                ).model_dump(mode="json"),
            }
        return ExplainedAnalysis.model_validate_json(
            json.dumps(result, allow_nan=False)
        ).model_dump(mode="json")

    if report.get("schema_version") != "creative-m1-v1":
        return finish(reason="m1_prediction_required")
    if not report["learned_prediction_available"]:
        return finish(reason="learned_prediction_unavailable")
    evidence = LocalEvidence()
    if evidence_provider is not None:
        try:
            evidence = evidence_provider(json.loads(snapshot))
            if type(evidence) is not LocalEvidence:
                raise TypeError("invalid_local_evidence_provider_result")
        except Exception:  # noqa: BLE001 - sanitize trusted local callback errors
            return finish(reason="evidence_preparation_failed")
    try:
        context = build_explanation_context(
            json.loads(snapshot), shap=evidence.shap, comparables=evidence.comparables
        )
    except Exception:  # noqa: BLE001 - preserve the report when local evidence cannot be bound
        return finish(reason="evidence_binding_failed")
    return finish(await run_explanation(context, transport, limits=limits))

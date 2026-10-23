"""Shared Python/MCP review around the unchanged, supervised M1 graph.

No provider is configured here. Final model selection is intentionally gated on
the still-missing approved Front 1 handoff; this adapter serves the historical M1
contract only. Operator campaign files never arrive through the MCP payload.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Literal

from pydantic import Field, ValidationError

from scripts.campaign_evidence_v1 import AdherenceReview, CampaignCase, brief_digest
from scripts.channel_partitions import Digest, FrozenContract, digest
from scripts.creative_contracts import AnalysisRequest, ErrorResponse, error_response
from scripts.creative_registry import CreativeRegistry
from scripts.explanation_graph_service_v2 import (
    GraphError,
    GraphSettings,
    IntegratedResponse,
    analyze_via_graph,
)
from scripts.explanation_review_v1 import SufficiencyReview, hashlib_text, review_recorded


class ReviewProvenance(FrozenContract):
    kind: Literal["local_review_of_bound_report"] = "local_review_of_bound_report"
    new_extractions: Literal[0] = 0
    new_predictions: Literal[0] = 0
    new_external_calls: Literal[0] = 0
    input_origin_declared_by_operator: Literal["unverified", "invented", "cached_features", "media"]
    configuration_status: Literal["final_front1_handoff_pending"] = "final_front1_handoff_pending"


class PhaseReceipt(FrozenContract):
    phase: Literal[
        "entry",
        "extraction_features",
        "prediction_interval_ranking",
        "shap",
        "training_comparables",
        "selection_rendering",
        "qualitative_review",
    ]
    status: Literal["completed", "incomplete", "not_started"]
    basis: Literal[
        "validated_request",
        "native_handoff",
        "numeric_report",
        "bound_packet",
        "selection_status",
        "local_review",
        "no_receipt",
    ]


class IntegrationReceipt(FrozenContract):
    kind: Literal["shared_python_mcp_graph_review_v1"] = "shared_python_mcp_graph_review_v1"
    invocation: Literal["live_graph", "not_started"]
    data_origin: Literal["unverified", "invented", "media"]
    phases: tuple[PhaseReceipt, ...]
    cleanup: Literal[
        "confirmed_by_graph_supervisor",
        "not_inferred_for_error",
        "not_started",
        "not_observed_in_simulated_source",
    ]
    external_provider_configured: Literal[False] = False
    final_configuration_validated: Literal[False] = False
    fresh_media_extraction_proven_by_this_receipt: Literal[False] = False
    phase_status_basis: Literal["derived_from_returned_source_not_independent_trace"] = (
        "derived_from_returned_source_not_independent_trace"
    )
    training_reference_matches: int = Field(ge=0)
    training_reference_absence_notices: int = Field(ge=0)


class ReviewedResponse(FrozenContract):
    schema_version: Literal["creative-explanation-reviewed-v1"] = "creative-explanation-reviewed-v1"
    review_status: Literal["reviewed", "unavailable"]
    reason_code: Literal[
        "review_completed",
        "invalid_request",
        "source_unavailable",
        "campaign_binding_failed",
        "evidence_review_failed",
    ]
    source_result: IntegratedResponse | GraphError | ErrorResponse
    source_sha256: Digest
    display_text: str = Field(max_length=131072)
    display_sha256: Digest
    quality_review: SufficiencyReview | None
    campaign_adherence: AdherenceReview | None
    review_provenance: ReviewProvenance
    integration_receipt: IntegrationReceipt


@dataclass(frozen=True)
class ReviewSettings:
    graph: GraphSettings
    cases: tuple[CampaignCase, ...] = ()
    show_local_evidence: bool = False
    data_origin: Literal["unverified", "invented", "media"] = "unverified"

    def __post_init__(self):
        keys = [(c.campaign_id, c.brief_sha256) for c in self.cases]
        if len(set(keys)) != len(keys) or self.data_origin not in {
            "unverified",
            "invented",
            "media",
        }:
            raise ValueError("invalid_review_operator_configuration")
        if type(self.show_local_evidence) is not bool:
            raise ValueError("invalid_review_presentation_scope")
        for case in self.cases:
            CampaignCase.model_validate_json(case.model_dump_json())


def registry_bindings(settings, request):
    """Metadata snapshot only. The existing graph owns media validation/extraction.

    Before/after snapshots reject registry substitutions. Private paths and media
    digests stay local. This does not claim protection from a hostile local admin.
    """
    registry = CreativeRegistry(settings.uploads_root, settings.registry_file)
    with registry._locked():
        state = registry._load()
    records = [state.creatives[cid] for cid in request.creative_ids]
    if any(r.campaign_id != request.campaign_id or r.sector != request.sector for r in records):
        raise ValueError("campaign_registry_mismatch")
    return {cid: r.media.sha256 for cid, r in zip(request.creative_ids, records, strict=True)}


def _receipt(settings, source, *, started, reviewed):
    valid = "analysis" in source
    facts = (source.get("evidence_packet") or {}).get("evidence", [])
    phases = [
        PhaseReceipt(
            phase="entry",
            status="completed" if started else "not_started",
            basis="validated_request" if started else "no_receipt",
        )
    ]
    if valid:
        analysis = source["analysis"]
        flags = [
            (
                "extraction_features",
                source["orchestration"]["native_feature_handoff"],
                "native_handoff",
            ),
            (
                "prediction_interval_ranking",
                analysis.get("status") == "m1_prediction_available",
                "numeric_report",
            ),
            (
                "shap",
                reviewed and any("_shap_" in f["evidence_id"] for f in facts),
                "bound_packet" if reviewed else "no_receipt",
            ),
            (
                "training_comparables",
                reviewed and any("_reference" in f["evidence_id"] for f in facts),
                "bound_packet" if reviewed else "no_receipt",
            ),
            (
                "selection_rendering",
                reviewed and source["explanation"]["status"] == "validated_catalogue_selection",
                "selection_status",
            ),
        ]
        phases.extend(
            PhaseReceipt(phase=p, status="completed" if flag else "incomplete", basis=b)
            for p, flag, b in flags
        )
    phases.append(
        PhaseReceipt(
            phase="qualitative_review",
            status="completed" if reviewed else "incomplete",
            basis="local_review",
        )
    )
    return IntegrationReceipt(
        invocation="live_graph" if started else "not_started",
        data_origin=settings.data_origin,
        phases=tuple(phases),
        training_reference_matches=sum(
            bool(re.fullmatch(r"c[1-5]_reference_[1-3]", f["evidence_id"])) for f in facts
        )
        if reviewed
        else 0,
        training_reference_absence_notices=sum(
            bool(re.fullmatch(r"c[1-5]_references_missing", f["evidence_id"])) for f in facts
        )
        if reviewed
        else 0,
        cleanup=(
            "confirmed_by_graph_supervisor"
            if source["orchestration"]["stategraph_executed"]
            else "not_observed_in_simulated_source"
        )
        if valid
        else "not_inferred_for_error"
        if started
        else "not_started",
    )


async def analyze_reviewed(payload, settings: ReviewSettings):
    """Single graph invocation; failures preserve validated numerical checkpoints."""
    started = False
    case = bindings = None
    case_failed = False
    try:
        request = AnalysisRequest.model_validate(payload)
    except ValidationError:
        source, reason = error_response("invalid_request"), "invalid_request"
    else:
        case = next(
            (
                c
                for c in settings.cases
                if c.campaign_id == request.campaign_id
                and c.brief_sha256 == brief_digest(request.brief)
            ),
            None,
        )
        if case:
            try:
                bindings = registry_bindings(settings.graph, request)
            except Exception:  # noqa: BLE001 - fixed code, never emit private registry errors
                case_failed = True
        started = True
        try:
            source = await analyze_via_graph(request.model_dump(mode="json"), settings.graph)
            model = IntegratedResponse if "analysis" in source else GraphError
            source = model.model_validate_json(json.dumps(source)).model_dump(mode="json")
        except Exception:  # noqa: BLE001 - preserve cancellation; suppress private launch/schema failures
            source = GraphError(orchestration_error="local_graph_failed").model_dump(mode="json")
        reason = "source_unavailable"
        if "analysis" in source:
            # Only the shared graph's strict reduced response may be returned.
            if case:
                try:
                    case_failed |= bindings != registry_bindings(settings.graph, request)
                except Exception:  # noqa: BLE001 - numeric checkpoint survives
                    case_failed = True
            if case_failed:
                reason = "campaign_binding_failed"
            elif source.get("evidence_packet") is not None:
                try:
                    result = review_recorded(
                        source,
                        request,
                        case=case,
                        media_bindings=bindings,
                        show_local_evidence=settings.show_local_evidence,
                        input_origin=settings.data_origin,
                    )
                    result.update(
                        review_status="reviewed",
                        reason_code="review_completed",
                        integration_receipt=_receipt(
                            settings, source, started=True, reviewed=True
                        ).model_dump(mode="json"),
                    )
                    return ReviewedResponse.model_validate_json(json.dumps(result)).model_dump(
                        mode="json"
                    )
                except Exception:  # noqa: BLE001 - fixed failure, preserve numbers/ranking
                    reason = "evidence_review_failed"
        else:
            source = GraphError.model_validate(source).model_dump(mode="json")
    text = "Revisão indisponível: " + reason + ". Os números disponíveis permanecem na fonte.\n"
    # JSON roundtrip is required by the historical strict tuple contracts.
    # Constructing this model from JSON-mode dicts would reject lists in a
    # preserved numerical checkpoint precisely on the unavailable-review path.
    result = {
        "schema_version": "creative-explanation-reviewed-v1",
        "review_status": "unavailable",
        "reason_code": reason,
        "source_result": source,
        "source_sha256": digest(source),
        "display_text": text,
        "display_sha256": hashlib_text(text),
        "quality_review": None,
        "campaign_adherence": None,
        "review_provenance": ReviewProvenance(
            input_origin_declared_by_operator=settings.data_origin
        ).model_dump(mode="json"),
        "integration_receipt": _receipt(
            settings, source, started=started, reviewed=False
        ).model_dump(mode="json"),
    }
    return ReviewedResponse.model_validate_json(json.dumps(result)).model_dump(mode="json")

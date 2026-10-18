"""Shared application use case for direct Python and MCP calls."""

from pydantic import ValidationError

from scripts.creative_contracts import (
    AnalysisRequest,
    AnalysisResponse,
    CandidateResult,
    Unavailable,
    error_response,
)
from scripts.creative_media import CreativeError
from scripts.creative_registry import CreativeRegistry


def determine_mode(creative_ids: list[str]) -> str:
    """Choose the analysis mode for one to five distinct creative IDs."""
    if not 1 <= len(creative_ids) <= 5:
        raise ValueError("Informe de um a cinco IDs de criativos")

    if len(set(creative_ids)) != len(creative_ids):
        raise ValueError("Os IDs de criativos devem ser distintos")

    return "individual" if len(creative_ids) == 1 else "comparative"


def analyze_creatives(payload: object, registry: CreativeRegistry) -> dict:
    """Validate registered candidates and explicitly report missing predictive capability."""
    try:
        request = AnalysisRequest.model_validate(payload)
    except ValidationError:
        return error_response("invalid_request")
    try:
        registry.validate_creatives(request)
    except CreativeError as exc:
        return error_response(exc.code)
    mode = determine_mode(request.creative_ids)
    return AnalysisResponse(
        campaign_id=request.campaign_id,
        sector=request.sector,
        mode=mode,
        baseline=Unavailable(reason_code="eligible_training_data_missing"),
        candidates=[
            CandidateResult(
                creative_id=creative_id,
                prediction=Unavailable(reason_code="usable_model_artifact_missing"),
                interval=Unavailable(reason_code="prediction_unavailable"),
            )
            for creative_id in request.creative_ids
        ],
        ranking=Unavailable(
            reason_code=(
                "individual_analysis" if mode == "individual" else "prediction_unavailable"
            )
        ),
    ).model_dump(mode="json")

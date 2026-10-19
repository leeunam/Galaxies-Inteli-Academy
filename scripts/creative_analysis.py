"""Shared application use case for direct Python and MCP calls."""

from pathlib import Path
from typing import TYPE_CHECKING

from pydantic import ValidationError

from scripts.creative_contracts import (
    AnalysisRequest,
    AnalysisResponse,
    BaselinePoint,
    BaselineRank,
    BaselineRanking,
    CandidateResult,
    ObservedAnalysisResponse,
    ObservedBaseline,
    ObservedCandidate,
    SyntheticAnalysisResponse,
    SyntheticBaseline,
    Unavailable,
    error_response,
)
from scripts.creative_media import CreativeError
from scripts.creative_registry import CreativeRegistry
from scripts.empirical_baseline import estimate_baseline
from scripts.observed_baseline import load_observed_baseline
from scripts.synthetic_baseline import build_synthetic_baseline

if TYPE_CHECKING:
    from scripts.m1_service import M1Settings


def determine_mode(creative_ids: list[str]) -> str:
    """Choose the analysis mode for one to five distinct creative IDs."""
    if not 1 <= len(creative_ids) <= 5:
        raise ValueError("Informe de um a cinco IDs de criativos")

    if len(set(creative_ids)) != len(creative_ids):
        raise ValueError("Os IDs de criativos devem ser distintos")

    return "individual" if len(creative_ids) == 1 else "comparative"


def analyze_creatives(
    payload: object,
    registry: CreativeRegistry,
    *,
    synthetic_baseline: bool = False,
    observed_baseline_dir: Path | None = None,
    m1: "M1Settings | None" = None,
) -> dict:
    """Validate media and serve the mode explicitly enabled by the operator."""
    if type(synthetic_baseline) is not bool:
        raise TypeError("synthetic_baseline must be a boolean operator setting")
    if synthetic_baseline and observed_baseline_dir is not None:
        raise ValueError("Choose a single baseline source")
    if m1 is not None and (synthetic_baseline or observed_baseline_dir is not None):
        raise ValueError("Choose a single model or baseline source")
    try:
        request = AnalysisRequest.model_validate(payload)
    except ValidationError:
        return error_response("invalid_request")
    try:
        records = registry.validate_creatives(request)
    except CreativeError as exc:
        return error_response(exc.code)
    mode = determine_mode(request.creative_ids)
    if m1 is not None:
        from scripts.m1_service import serve_m1

        return serve_m1(request, registry, records, m1)
    response = AnalysisResponse(
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
    )
    if observed_baseline_dir is not None:
        try:
            release, artifact = load_observed_baseline(observed_baseline_dir)
            estimate = estimate_baseline(artifact, request.sector)
            if estimate.status != "observed_baseline":
                raise ValueError("Missing sector support")
        except (OSError, ValueError):
            return error_response("baseline_artifact_unavailable")
        reference = ObservedBaseline(
            sector=request.sector,
            central_views=estimate.central_views,
            sector_range=estimate.sector_range,
            reference_samples=estimate.reference_samples,
            reference_channels=estimate.reference_channels,
            artifact_sha256=artifact.artifact_sha256,
            partition_manifest_sha256=artifact.partition_manifest_sha256,
            cohort_release_sha256=release.release_sha256,
        )
        return ObservedAnalysisResponse(
            campaign_id=request.campaign_id,
            sector=request.sector,
            mode=mode,
            baseline=reference,
            candidates=[
                ObservedCandidate(
                    creative_id=creative_id,
                    prediction=BaselinePoint(value=estimate.central_views),
                    interval=Unavailable(reason_code="predictive_interval_not_validated"),
                )
                for creative_id in request.creative_ids
            ],
            ranking=Unavailable(reason_code="individual_analysis")
            if mode == "individual"
            else BaselineRanking(
                entries=[
                    BaselineRank(creative_id=creative_id, value=estimate.central_views)
                    for creative_id in request.creative_ids
                ]
            ),
        ).model_dump(mode="json")
    if not synthetic_baseline:
        return response.model_dump(mode="json")
    artifact = build_synthetic_baseline()
    estimate = estimate_baseline(artifact, request.sector)
    reference = SyntheticBaseline(
        sector=request.sector,
        central_views=estimate.central_views,
        sector_range=estimate.sector_range,
        reference_samples=estimate.reference_samples,
        reference_channels=estimate.reference_channels,
        artifact_sha256=artifact.artifact_sha256,
        partition_manifest_sha256=artifact.partition_manifest_sha256,
    )
    return SyntheticAnalysisResponse(
        campaign_id=request.campaign_id,
        sector=request.sector,
        mode=mode,
        baseline=reference,
        candidates=response.candidates,
        ranking=response.ranking,
    ).model_dump(mode="json")

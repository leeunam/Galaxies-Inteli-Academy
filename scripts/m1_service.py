"""Operator-enabled M1 inference; no training, holdout labels or external services."""

import json
from dataclasses import dataclass
from pathlib import Path

from catboost import CatBoostError

from scripts.candidate_features import extract_candidates
from scripts.channel_partitions import ExperimentError, load_partitions
from scripts.creative_contracts import (
    M1AnalysisResponse,
    M1Candidate,
    M1Extraction,
    M1Interval,
    M1Point,
    M1Rank,
    M1Ranking,
    ObservedBaseline,
    Unavailable,
    error_response,
)
from scripts.creative_media import ROOT, CreativeError
from scripts.empirical_baseline import estimate_baseline
from scripts.experiment_a_artifact import load_bundle
from scripts.experiment_a_data import check_extractor_runtime
from scripts.observed_baseline import load_observed_baseline, read_json


@dataclass(frozen=True)
class M1Settings:
    model_dir: Path
    cohort_dir: Path
    scratch_root: Path = ROOT / "data/private/m1-temp"


def load_model_context(settings):
    release, baseline = load_observed_baseline(settings.cohort_dir)
    manifest = load_partitions(settings.cohort_dir / "partitions.json")
    config = json.loads(read_json(settings.cohort_dir / "extractor-config.json"))
    check_extractor_runtime(config, Path(__file__).parent)
    bundle = load_bundle(
        settings.model_dir,
        expected_extractor_config=config,
        expected_partition_sha256=manifest.manifest_sha256,
        expected_cohort_sha256=release.release_sha256,
    )
    artifact = bundle.artifact
    if (
        artifact.data_kind != "observed_pilot"
        or artifact.baseline_sha256 != baseline.artifact_sha256
        or artifact.training_sample_ids != baseline.training_sample_ids
        or artifact.validation_sample_ids
        != tuple(r.sample_id for r in manifest.assignments if r.partition == "validation")
    ):
        raise ExperimentError("incompatible_serving_cohort")
    return release, baseline, bundle


def serve_m1(request, registry, records, settings):
    try:
        release, baseline, bundle = load_model_context(settings)
        estimate = estimate_baseline(baseline, request.sector)
        if estimate.status != "observed_baseline":
            raise ExperimentError("missing_sector_support")
    except (OSError, ValueError, KeyError, CatBoostError):
        return error_response("model_artifact_unavailable")
    artifact = bundle.artifact
    reference = ObservedBaseline(
        sector=request.sector,
        central_views=estimate.central_views,
        sector_range=estimate.sector_range,
        reference_samples=estimate.reference_samples,
        reference_channels=estimate.reference_channels,
        artifact_sha256=baseline.artifact_sha256,
        partition_manifest_sha256=baseline.partition_manifest_sha256,
        cohort_release_sha256=release.release_sha256,
    )
    try:
        extracted = extract_candidates(
            registry, records, artifact.extractor_config, settings.scratch_root
        )
    except CreativeError as exc:
        return error_response(exc.code)
    except (OSError, ValueError, RuntimeError):
        from scripts.candidate_features import CandidateFeatures

        extracted = [
            CandidateFeatures(
                status="unavailable",
                reason_code="extraction_failed",
                extractor_config_sha256=artifact.extractor_config_sha256,
            )
            for _ in records
        ]
    candidates = []
    for creative_id, result in zip(request.creative_ids, extracted, strict=True):
        inputs, reason = result.inputs, result.reason_code
        if (
            result.status == "completed"
            and inputs.text_status not in artifact.supported_text_statuses
        ):
            reason = "unsupported_text_status"
        prediction, interval = None, None
        if reason is None:
            try:
                lower, central, upper = bundle.predict_views([inputs])[0]
                if not 0 <= lower <= central <= upper:
                    raise ExperimentError("invalid_quantile_order")
                prediction = M1Point(value=float(central))
                interval = M1Interval(lower_views=float(lower), upper_views=float(upper))
            except (ValueError, CatBoostError):
                reason = "invalid_model_prediction"
                prediction, interval = None, None
        candidates.append(
            M1Candidate(
                creative_id=creative_id,
                extraction=M1Extraction(
                    status=result.status, text_status=inputs.text_status if inputs else None
                ),
                prediction=prediction
                if prediction is not None
                else Unavailable(reason_code=reason),
                interval=interval if interval is not None else Unavailable(reason_code=reason),
            )
        )
    ready = sum(isinstance(c.prediction, M1Point) for c in candidates)
    mode = "individual" if len(candidates) == 1 else "comparative"
    if mode == "individual":
        ranking = Unavailable(reason_code="individual_analysis")
    elif ready != len(candidates):
        ranking = Unavailable(reason_code="incomplete_predictions")
    else:
        ordered = sorted(candidates, key=lambda c: -c.prediction.value)
        ranking = M1Ranking(
            entries=[
                M1Rank(
                    creative_id=c.creative_id,
                    value=c.prediction.value,
                    rank=1
                    + sum(other.prediction.value > c.prediction.value for other in candidates),
                )
                for c in ordered
            ]
        )
    completed = sum(r.status == "completed" for r in extracted)
    return M1AnalysisResponse(
        status="m1_prediction_available"
        if ready == len(candidates)
        else "m1_prediction_incomplete",
        campaign_id=request.campaign_id,
        sector=request.sector,
        mode=mode,
        learned_prediction_available=ready > 0,
        model_artifact_sha256=artifact.artifact_sha256,
        extractor_config_sha256=artifact.extractor_config_sha256,
        extraction_status="completed"
        if completed == len(candidates)
        else "partial"
        if completed
        else "unavailable",
        baseline=reference,
        candidates=candidates,
        ranking=ranking,
    ).model_dump(mode="json")

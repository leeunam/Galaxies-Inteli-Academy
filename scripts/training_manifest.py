"""Strict local import and readiness report; neither acquisition nor schema releases training."""

import hashlib
import json
from collections import Counter
from typing import Literal

from pydantic import Field, TypeAdapter, model_validator

from scripts.channel_partitions import (
    Digest,
    ExperimentError,
    FrozenContract,
    PartitionManifest,
    Reference,
    digest,
)
from scripts.observed_baseline import CuratedReference, observation_digest
from scripts.pilot_licensed_media import EXTRACTOR_VERSION, FRAME_POLICY, MODELS


class TrainingReference(CuratedReference):
    youtube_license: Literal["youtube", "creativeCommon"]
    permission_basis: Literal["explicit_operator_instruction"]
    permission_evidence_sha256: Digest
    use_scope: Literal["local_extraction_and_training"]
    platform_approval_verified: Literal[False] = False
    curation_method: Literal["automated_assisted_review", "human_review"]
    view_count_observed: int = Field(ge=0, le=2**63 - 1)
    features_sha256: Digest
    run_sha256: Digest
    extractor_config_sha256: Digest
    acquired_media_sha256: Digest

    @model_validator(mode="after")
    def frozen_target(self):
        if self.frozen_observation_sha256 != observation_digest(
            self.model_dump(), self.view_count_observed
        ):
            raise ExperimentError("frozen_observation_mismatch")
        return self


class PredictorInputs(FrozenContract):
    """Only properties of the creative; grouping, outcomes and titles cannot enter."""

    sector: Literal["moda", "beleza"]
    duration_seconds: float = Field(gt=0, le=60)
    aspect_ratio_height_over_width: float = Field(gt=1)
    text_status: Literal["extracted", "no_audio_stream", "no_speech_detected_by_asr"]
    text_embedding: tuple[float, ...] | None

    @model_validator(mode="after")
    def text_consistency(self):
        if (self.text_status == "extracted") != (self.text_embedding is not None):
            raise ExperimentError("inconsistent_text_features")
        if self.text_embedding is not None and len(self.text_embedding) != 384:
            raise ExperimentError("invalid_text_embedding")
        return self


def validate_feature_evidence(
    reference: TrainingReference, features_raw: bytes, run_raw: bytes, config: dict
) -> PredictorInputs:
    reference = TrainingReference.model_validate(reference)
    if (
        hashlib.sha256(features_raw).hexdigest() != reference.features_sha256
        or hashlib.sha256(run_raw).hexdigest() != reference.run_sha256
        or digest(config) != reference.extractor_config_sha256
    ):
        raise ExperimentError("feature_evidence_mismatch")
    if len(features_raw) > 16 * 1024 * 1024 or len(run_raw) > 16 * 1024 * 1024:
        raise ExperimentError("feature_evidence_too_large")
    features, run = json.loads(features_raw), json.loads(run_raw)
    expected_models = {k: {"repo": v[0], "revision": v[1]} for k, v in MODELS.items()}
    if any(config.get("models", {}).get(k) != model for k, model in expected_models.items()):
        raise ExperimentError("incompatible_model_revisions")
    if run.get("models") != config.get("models"):
        raise ExperimentError("incompatible_run_models")
    if run.get("media_fingerprint", {}).get("sha256") != reference.acquired_media_sha256:
        raise ExperimentError("media_fingerprint_mismatch")
    policy = features.get("feature_policy", {})
    if (
        run.get("status") != "completed"
        or run.get("temporary_directory_removed") is not True
        or features.get("schema_version") != EXTRACTOR_VERSION
        or policy.get("version") != EXTRACTOR_VERSION
        or policy.get("frame_policy") != FRAME_POLICY
        or policy.get("asr_beam_size") != 1
        or policy.get("language_requested", "missing") is not None
        or policy.get("asr_temperature") != 0
        or policy.get("asr_vad") is not True
        or policy.get("asr_condition_on_previous_text") is not False
    ):
        raise ExperimentError("incompatible_extractor_policy")
    audit = run.get("source", {}).get("audit", {})
    expected_audit = {
        "video_id": reference.sample_id,
        "channel_id": reference.channel_id,
        "source_url": reference.source_url,
        "published_at_utc": reference.published_at_utc,
        "observed_at_utc": reference.observed_at_utc,
    }
    if (
        audit != expected_audit
        or run.get("source", {}).get("target", {}).get("view_count_observed")
        != reference.view_count_observed
    ):
        raise ExperimentError("source_observation_mismatch")
    props = features.get("properties", {})
    if any(props.get(k) != getattr(reference, k) for k in ("duration_seconds", "width", "height")):
        raise ExperimentError("media_properties_mismatch")
    vector = features.get("text_embedding")
    return PredictorInputs(
        sector=reference.sector,
        duration_seconds=reference.duration_seconds,
        aspect_ratio_height_over_width=reference.height / reference.width,
        text_status=features["text_features_status"],
        text_embedding=tuple(vector) if isinstance(vector, list) else vector,
    )


def _readiness(records: list, *, features_verified: bool, partitions_verified: bool) -> dict:
    rows = TypeAdapter(list[TrainingReference]).validate_python(records)
    ids = [r.sample_id for r in rows]
    if len(set(ids)) != len(ids):
        raise ExperimentError("duplicate_sample_id")
    channels = {r.channel_id for r in rows}
    sectors = Counter(r.sector for r in rows)
    hashes = Counter(r.media_sha256 for r in rows)
    blockers = []
    if len(rows) < 200:
        blockers.append("below_agreed_200_references")
    if len(channels) < 50:
        blockers.append("below_agreed_50_channels")
    if set(sectors) != {"moda", "beleza"}:
        blockers.append("missing_sector")
    if not features_verified:
        blockers.append("extractor_evidence_not_verified")
    if not partitions_verified:
        blockers.append("channel_partitions_not_verified")
    return {
        "schema_version": "training-readiness-v1",
        "references": len(rows),
        "channels": len(channels),
        "sector_support": dict(sectors),
        "exact_duplicate_groups": sum(n > 1 for n in hashes.values()),
        "training_release_available": not blockers,
        "blockers": blockers,
        "warnings": [
            "platform_approval_not_verified",
            "automated_curation_is_not_human_accuracy_validation",
            "development_pilot_not_independent_evaluation",
            "edited_reposts_not_automatically_detected",
        ],
        "extractor_evidence_required": True,
        "predictive_quality_validated": False,
    }


def readiness(records: list) -> dict:
    """Metadata alone can never release training, even at the agreed sample size."""
    return _readiness(records, features_verified=False, partitions_verified=False)


def import_training_manifest(
    records: list,
    evidence_by_id: dict,
    config: dict,
    *,
    partitions: PartitionManifest | None = None,
) -> tuple[dict, dict]:
    rows = TypeAdapter(list[TrainingReference]).validate_python(records)
    if set(evidence_by_id) != {r.sample_id for r in rows}:
        raise ExperimentError("feature_evidence_ids_mismatch")
    predictors = {}
    for row in rows:
        features_raw, run_raw = evidence_by_id[row.sample_id]
        predictors[row.sample_id] = validate_feature_evidence(row, features_raw, run_raw, config)
    if partitions is not None:
        partitions = PartitionManifest.model_validate(partitions)
        metadata = [
            r.model_dump(include=set(Reference.model_fields))
            for r in sorted(rows, key=lambda r: r.sample_id)
        ]
        if (
            partitions.data_kind != "observed_pilot"
            or digest(metadata) != partitions.metadata_sha256
        ):
            raise ExperimentError("partition_metadata_mismatch")
        assignments = {r.sample_id: r.partition for r in partitions.assignments}
        acquisition_groups = {}
        for row in rows:
            allocation = assignments[row.sample_id]
            previous = acquisition_groups.setdefault(row.acquired_media_sha256, allocation)
            if previous != allocation:
                raise ExperimentError("new_duplicate_crosses_partitions")
    return _readiness(
        records, features_verified=True, partitions_verified=partitions is not None
    ), predictors

"""Train-only reference statistics; artifacts never assert real scientific readiness."""

from __future__ import annotations

import math
from collections import defaultdict
from pathlib import Path
from typing import Literal

from pydantic import Field, TypeAdapter, model_validator

from scripts.channel_partitions import (
    SECTORS,
    DataKind,
    Digest,
    ExperimentError,
    FrozenContract,
    Identifier,
    PartitionManifest,
    digest,
    save_new_json,
)

MAX_LOG_VIEWS = math.log1p(2**63 - 1)


class TrainingTarget(FrozenContract):
    sample_id: Identifier
    view_count: int = Field(ge=0, le=2**63 - 1)


class SectorStatistics(FrozenContract):
    sector: Literal["moda", "beleza"]
    samples: int = Field(gt=0)
    channels: int = Field(gt=0)
    q10_log1p: float = Field(ge=0, le=MAX_LOG_VIEWS)
    q50_log1p: float = Field(ge=0, le=MAX_LOG_VIEWS)
    q90_log1p: float = Field(ge=0, le=MAX_LOG_VIEWS)

    @model_validator(mode="after")
    def ordered(self):
        if not self.q10_log1p <= self.q50_log1p <= self.q90_log1p:
            raise ExperimentError("unordered_sector_quantiles")
        return self


class ChannelMedian(FrozenContract):
    channel_id: Identifier
    samples: int = Field(gt=0)
    q50_log1p: float = Field(ge=0, le=MAX_LOG_VIEWS)


class BaselineArtifact(FrozenContract):
    schema_version: Literal["empirical-baseline-v1"] = "empirical-baseline-v1"
    data_kind: DataKind
    scientific_status: Literal["pending_issue_1", "pilot_not_evaluated"] = "pending_issue_1"
    real_results_available: bool = False
    target_transform: Literal["log1p"] = "log1p"
    range_method: Literal["linear_quantiles_in_log1p"] = "linear_quantiles_in_log1p"
    partition_manifest_sha256: Digest
    training_targets_sha256: Digest
    training_sample_ids: tuple[Identifier, ...] = Field(min_length=1)
    sectors: tuple[SectorStatistics, ...] = Field(min_length=1, max_length=2)
    channels: tuple[ChannelMedian, ...] = Field(min_length=1)
    warnings: tuple[str, ...]
    artifact_sha256: Digest

    @model_validator(mode="after")
    def integrity(self):
        sectors = [row.sector for row in self.sectors]
        channels = [row.channel_id for row in self.channels]
        if (
            self.real_results_available != (self.data_kind == "observed_pilot")
            or self.scientific_status
            != ("pilot_not_evaluated" if self.data_kind == "observed_pilot" else "pending_issue_1")
            or tuple(sorted(set(self.training_sample_ids))) != self.training_sample_ids
            or sectors != sorted(set(sectors))
            or channels != sorted(set(channels))
            or sum(row.samples for row in self.sectors) != len(self.training_sample_ids)
            or sum(row.samples for row in self.channels) != len(self.training_sample_ids)
            or self.artifact_sha256 != digest(self.model_dump(exclude={"artifact_sha256"}))
        ):
            raise ExperimentError("baseline_artifact_mismatch")
        return self


class EmpiricalSectorRange(FrozenContract):
    kind: Literal["empirical_training_sector_range"] = "empirical_training_sector_range"
    lower_views: float = Field(ge=0)
    sector_median_views: float = Field(ge=0)
    upper_views: float = Field(ge=0)
    lower_quantile: Literal[0.1] = 0.1
    upper_quantile: Literal[0.9] = 0.9
    coverage_status: Literal["not_evaluated"] = "not_evaluated"


class BaselineEstimate(FrozenContract):
    schema_version: Literal["baseline-estimate-v1"] = "baseline-estimate-v1"
    status: Literal[
        "synthetic_baseline", "unvalidated_baseline", "observed_baseline", "unavailable"
    ]
    data_kind: DataKind
    scientific_status: Literal["pending_issue_1", "pilot_not_evaluated"] = "pending_issue_1"
    real_results_available: bool = False
    sector: Literal["moda", "beleza"]
    variant: Literal["B0", "Bcanal"]
    artifact_sha256: Digest
    reason_code: Literal["sector_training_support_missing"] | None = None
    central_views: float | None = Field(default=None, ge=0)
    central_log1p_views: float | None = Field(default=None, ge=0)
    reference_scope: Literal["sector", "channel"] | None = None
    reference_samples: int = Field(default=0, ge=0)
    reference_channels: int = Field(default=0, ge=0)
    channel_fallback: bool = False
    sector_range: EmpiricalSectorRange | None = None
    central_outside_sector_range: bool | None = None


def _quantile(values, probability):
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower, upper = math.floor(position), math.ceil(position)
    weight = position - lower
    return ordered[lower] + weight * (ordered[upper] - ordered[lower])


def fit_baseline(manifest: PartitionManifest, training_targets: list) -> BaselineArtifact:
    """Require exactly the train labels; validation/test labels are rejected."""
    manifest = PartitionManifest.model_validate(manifest)
    targets = TypeAdapter(list[TrainingTarget]).validate_python(training_targets)
    rows = {row.sample_id: row for row in manifest.assignments if row.partition == "train"}
    if len({target.sample_id for target in targets}) != len(targets):
        raise ExperimentError("duplicate_training_target")
    if {target.sample_id for target in targets} != set(rows):
        raise ExperimentError("training_targets_mismatch")
    targets.sort(key=lambda target: target.sample_id)
    sector_values, channel_values = defaultdict(list), defaultdict(list)
    for target in targets:
        row = rows[target.sample_id]
        value = math.log1p(target.view_count)
        sector_values[row.sector].append(value)
        channel_values[row.channel_id].append(value)
    sectors = tuple(
        SectorStatistics(
            sector=sector,
            samples=len(values),
            channels=len({row.channel_id for row in rows.values() if row.sector == sector}),
            q10_log1p=_quantile(values, 0.1),
            q50_log1p=_quantile(values, 0.5),
            q90_log1p=_quantile(values, 0.9),
        )
        for sector, values in sorted(sector_values.items())
    )
    channels = tuple(
        ChannelMedian(
            channel_id=channel,
            samples=len(values),
            q50_log1p=_quantile(values, 0.5),
        )
        for channel, values in sorted(channel_values.items())
    )
    observed = manifest.data_kind == "observed_pilot"
    warnings = [
        "empirical_range_not_calibrated",
        "development_pilot_not_independent_evaluation"
        if observed
        else "real_results_pending_issue_1",
    ]
    for sector in SECTORS:
        if sector not in sector_values:
            warnings.append(f"sector_without_training_support:{sector}")
        elif len(sector_values[sector]) < 5:
            warnings.append(f"few_training_samples:{sector}")
    body = {
        "schema_version": "empirical-baseline-v1",
        "data_kind": manifest.data_kind,
        "scientific_status": "pilot_not_evaluated" if observed else "pending_issue_1",
        "real_results_available": observed,
        "target_transform": "log1p",
        "range_method": "linear_quantiles_in_log1p",
        "partition_manifest_sha256": manifest.manifest_sha256,
        "training_targets_sha256": digest([target.model_dump() for target in targets]),
        "training_sample_ids": tuple(target.sample_id for target in targets),
        "sectors": sectors,
        "channels": channels,
        "warnings": tuple(sorted(warnings)),
    }
    serialized = {
        **body,
        "sectors": [row.model_dump() for row in sectors],
        "channels": [row.model_dump() for row in channels],
    }
    return BaselineArtifact(**body, artifact_sha256=digest(serialized))


def estimate_baseline(
    artifact: BaselineArtifact,
    sector: str,
    *,
    variant="B0",
    channel_id=None,
) -> BaselineEstimate:
    artifact = BaselineArtifact.model_validate(artifact)
    if sector not in SECTORS or variant not in ("B0", "Bcanal"):
        raise ExperimentError("unsupported_baseline_request")
    if channel_id is not None:
        channel_id = TypeAdapter(Identifier).validate_python(channel_id)
    shared = {
        "data_kind": artifact.data_kind,
        "scientific_status": artifact.scientific_status,
        "real_results_available": artifact.real_results_available,
        "sector": sector,
        "variant": variant,
        "artifact_sha256": artifact.artifact_sha256,
    }
    statistics = next((row for row in artifact.sectors if row.sector == sector), None)
    if statistics is None:
        return BaselineEstimate(
            status="unavailable", reason_code="sector_training_support_missing", **shared
        )
    channel = next((row for row in artifact.channels if row.channel_id == channel_id), None)
    use_channel = variant == "Bcanal" and channel is not None
    central = channel.q50_log1p if use_channel else statistics.q50_log1p
    central_views = math.expm1(central)
    interval = EmpiricalSectorRange(
        lower_views=math.expm1(statistics.q10_log1p),
        sector_median_views=math.expm1(statistics.q50_log1p),
        upper_views=math.expm1(statistics.q90_log1p),
    )
    return BaselineEstimate(
        status="synthetic_baseline"
        if artifact.data_kind == "synthetic"
        else "observed_baseline"
        if artifact.data_kind == "observed_pilot"
        else "unvalidated_baseline",
        central_log1p_views=central,
        central_views=central_views,
        reference_scope="channel" if use_channel else "sector",
        reference_samples=channel.samples if use_channel else statistics.samples,
        reference_channels=1 if use_channel else statistics.channels,
        channel_fallback=variant == "Bcanal" and not use_channel,
        sector_range=interval,
        central_outside_sector_range=not interval.lower_views
        <= central_views
        <= interval.upper_views,
        **shared,
    )


def save_baseline(path: Path, artifact: BaselineArtifact):
    save_new_json(path, BaselineArtifact.model_validate(artifact))


def load_baseline(
    path: Path, manifest: PartitionManifest, training_targets: list
) -> BaselineArtifact:
    """Validate against the frozen manifest AND train labels; reject stale statistics."""
    with Path(path).open("rb") as handle:
        raw = handle.read(16 * 1024 * 1024 + 1)
    if len(raw) > 16 * 1024 * 1024:
        raise ExperimentError("artifact_too_large")
    artifact = BaselineArtifact.model_validate_json(raw)
    if artifact != fit_baseline(manifest, training_targets):
        raise ExperimentError("baseline_artifact_mismatch")
    return artifact

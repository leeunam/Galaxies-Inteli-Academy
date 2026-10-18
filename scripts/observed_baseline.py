"""Explicit operator release of a curated observational pilot, never model evaluation.

The fixed bundle layout contains no caller-controlled paths. Freeze metadata first;
publish only train labels afterwards. Hashes check consistency, not legal approval.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from scripts.channel_partitions import (
    Digest,
    ExperimentError,
    FrozenContract,
    Reference,
    digest,
    freeze_partitions,
    load_partitions,
    save_new_json,
)
from scripts.empirical_baseline import (
    BaselineArtifact,
    TrainingTarget,
    fit_baseline,
    load_baseline,
    save_baseline,
)


class CuratedReference(Reference):
    source_url: str
    published_at_utc: str
    observed_at_utc: str
    duration_seconds: float = Field(gt=0, le=60)
    width: int = Field(gt=0, le=1920)
    height: int = Field(gt=0, le=1920)
    spoken_language: Literal["pt-BR"]
    language_evidence: Literal["existing_human_review", "asr_and_agent_transcript_review"]
    content_review: Literal["included"]
    curation_evidence_sha256: Digest
    frozen_observation_sha256: Digest

    @model_validator(mode="after")
    def cohort_compatible(self):
        if (
            not re.fullmatch(r"[A-Za-z0-9_-]{11}", self.sample_id)
            or self.source_url != f"https://www.youtube.com/watch?v={self.sample_id}"
        ):
            raise ExperimentError("source_identity_mismatch")
        try:
            published = datetime.fromisoformat(self.published_at_utc)
            observed = datetime.fromisoformat(self.observed_at_utc)
            if published.utcoffset() is None or observed.utcoffset() is None:
                raise ValueError
            age = (observed - published).total_seconds() / 86400
        except ValueError:
            raise ExperimentError("invalid_observation_dates") from None
        if not 30 <= age < 37 or self.height <= self.width:
            raise ExperimentError("outside_pilot_cohort")
        return self


class CohortRelease(FrozenContract):
    schema_version: Literal["observed-cohort-v1"] = "observed-cohort-v1"
    scope: Literal["observational_development_pilot"] = "observational_development_pilot"
    operator_authorized: Literal[True]
    platform_approval_verified: Literal[False] = False
    human_sample_audit_completed: Literal[False] = False
    scientific_evaluation: Literal["not_performed"] = "not_performed"
    source_snapshot_sha256: Digest
    records: tuple[CuratedReference, ...] = Field(min_length=6)
    release_sha256: Digest

    @model_validator(mode="after")
    def integrity(self):
        ids = [r.sample_id for r in self.records]
        if ids != sorted(set(ids)) or self.release_sha256 != digest(
            self.model_dump(exclude={"release_sha256"})
        ):
            raise ExperimentError("cohort_release_mismatch")
        for sector in ("moda", "beleza"):
            if len({r.channel_id for r in self.records if r.sector == sector}) < 3:
                raise ExperimentError("insufficient_sector_channels")
        return self


class TrainLabels(FrozenContract):
    targets: tuple[TrainingTarget, ...] = Field(min_length=1)


def observation_digest(record: dict, view_count: int) -> str:
    """Bind train counts to the frozen identity/dates without loading holdout labels."""
    return digest(
        {
            key: record[key]
            for key in ("sample_id", "channel_id", "published_at_utc", "observed_at_utc")
        }
        | {"view_count": view_count}
    )


def _verify_targets(release, targets):
    records = {r.sample_id: r for r in release.records}
    for target in targets:
        row = records.get(target.sample_id)
        if row is None or row.frozen_observation_sha256 != observation_digest(
            row.model_dump(), target.view_count
        ):
            raise ExperimentError("frozen_observation_mismatch")


def _metadata(release):
    return [r.model_dump(include=set(Reference.model_fields)) for r in release.records]


def freeze_cohort(records: list, directory: Path, *, source_snapshot_sha256: str) -> CohortRelease:
    """The input deliberately has no outcome field. No existing evidence is replaced."""
    rows = tuple(
        sorted((CuratedReference.model_validate(r) for r in records), key=lambda r: r.sample_id)
    )
    body = {
        "schema_version": "observed-cohort-v1",
        "scope": "observational_development_pilot",
        "operator_authorized": True,
        "platform_approval_verified": False,
        "human_sample_audit_completed": False,
        "scientific_evaluation": "not_performed",
        "source_snapshot_sha256": source_snapshot_sha256,
        "records": [r.model_dump() for r in rows],
    }
    release = CohortRelease.model_validate_json(json.dumps(body | {"release_sha256": digest(body)}))
    directory = Path(directory)
    # Exclusive directory creation also prevents partial overwrites on reruns.
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    save_new_json(directory / "cohort.json", release)
    freeze_partitions(_metadata(release), directory / "partitions.json", data_kind="observed_pilot")
    return release


def read_json(path: Path):
    with path.open("rb") as handle:
        raw = handle.read(16 * 1024 * 1024 + 1)
    if len(raw) > 16 * 1024 * 1024:
        raise ExperimentError("artifact_too_large")
    return raw


def _load_metadata(directory: Path):
    release = CohortRelease.model_validate_json(read_json(directory / "cohort.json"))
    manifest = load_partitions(directory / "partitions.json")
    if manifest.data_kind != "observed_pilot" or manifest.metadata_sha256 != digest(
        _metadata(release)
    ):
        raise ExperimentError("cohort_partition_mismatch")
    return release, manifest


def publish_baseline(directory: Path, training_targets: list) -> BaselineArtifact:
    """Require previously frozen metadata, accept exactly the train IDs, never holdout."""
    directory = Path(directory)
    release, manifest = _load_metadata(directory)
    labels = TrainLabels(targets=tuple(TrainingTarget.model_validate(t) for t in training_targets))
    _verify_targets(release, labels.targets)
    artifact = fit_baseline(manifest, list(labels.targets))
    save_new_json(directory / "train-targets.json", labels)
    save_baseline(directory / "baseline.json", artifact)
    return artifact


def load_observed_baseline(directory: Path) -> tuple[CohortRelease, BaselineArtifact]:
    """Recompute statistics from train labels and verify the complete frozen bundle."""
    directory = Path(directory)
    release, manifest = _load_metadata(directory)
    labels = TrainLabels.model_validate_json(read_json(directory / "train-targets.json"))
    _verify_targets(release, labels.targets)
    artifact = load_baseline(directory / "baseline.json", manifest, list(labels.targets))
    return release, artifact

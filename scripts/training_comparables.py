"""Train-only descriptive MiniLM references; no outcomes in selection or results."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import numpy as np
from pydantic import Field, TypeAdapter, ValidationError

from scripts.channel_partitions import (
    Digest,
    ExperimentError,
    FrozenContract,
    Identifier,
    digest,
    load_partitions,
)
from scripts.empirical_baseline import TrainingTarget
from scripts.experiment_a_data import DevelopmentSplit, split_digest
from scripts.m1_service import load_model_context
from scripts.observed_baseline import CuratedReference, observation_digest, read_json
from scripts.training_manifest import PredictorInputs

TECHNICAL_FORMAT = "portrait_short_le60"


class ComparableMatch(FrozenContract):
    sample_id: Identifier
    sector: Literal["moda", "beleza"]
    technical_format: Literal["portrait_short_le60"] = TECHNICAL_FORMAT
    source_url: str
    published_at_utc: str
    observed_at_utc: str
    similarity: float = Field(ge=-1, le=1)
    partition: Literal["train"] = "train"


class ComparableResult(FrozenContract):
    schema_version: Literal["training-comparables-v1"] = "training-comparables-v1"
    criterion: Literal["cosine_minilm_speech_same_sector_technical_format"] = (
        "cosine_minilm_speech_same_sector_technical_format"
    )
    model_artifact_sha256: Digest
    cohort_sha256: Digest
    partition_sha256: Digest
    minimum_similarity: float = Field(ge=0, le=1)
    references: tuple[ComparableMatch, ...] = Field(max_length=3)
    reason_code: (
        Literal[
            "speech_embedding_unavailable",
            "zero_query_embedding",
            "semantic_format_not_available",
            "no_matching_training_reference",
        ]
        | None
    ) = None
    causal: Literal[False] = False


@dataclass(frozen=True)
class _Entry:
    metadata: CuratedReference
    vector: tuple[float, ...] = field(repr=False)


@dataclass(frozen=True)
class TrainingIndex:
    model_artifact_sha256: str
    cohort_sha256: str
    partition_sha256: str
    training_samples: int
    minimum_similarity: float
    _entries: tuple[_Entry, ...] = field(repr=False)
    _copy_groups: tuple[tuple[str, str | None], ...] = field(repr=False)

    def search(self, query, *, media_sha256, semantic_format=None) -> ComparableResult:
        try:
            query = PredictorInputs.model_validate(query)
            media_sha256 = TypeAdapter(Digest).validate_python(media_sha256)
        except ValidationError:
            raise ExperimentError("invalid_comparable_query") from None

        def response(matches=(), reason=None):
            return ComparableResult(
                model_artifact_sha256=self.model_artifact_sha256,
                cohort_sha256=self.cohort_sha256,
                partition_sha256=self.partition_sha256,
                minimum_similarity=self.minimum_similarity,
                references=matches,
                reason_code=reason,
            )

        if semantic_format is not None:
            return response(reason="semantic_format_not_available")
        if query.text_status != "extracted":
            return response(reason="speech_embedding_unavailable")
        vector = _normal(query.text_embedding)
        if vector is None:
            return response(reason="zero_query_embedding")
        duplicate_groups = {
            group
            for media, group in self._copy_groups
            if media == media_sha256 and group is not None
        }
        matches = []
        for entry in self._entries:
            r = entry.metadata
            if (
                r.sector != query.sector
                or not _technical_format(r)
                or r.media_sha256 == media_sha256
                or r.duplicate_group is not None
                and r.duplicate_group in duplicate_groups
            ):
                continue
            score = float(np.clip(np.dot(vector, entry.vector), -1.0, 1.0))
            if score >= self.minimum_similarity:
                matches.append(
                    ComparableMatch(
                        sample_id=r.sample_id,
                        sector=r.sector,
                        source_url=r.source_url,
                        published_at_utc=r.published_at_utc,
                        observed_at_utc=r.observed_at_utc,
                        similarity=score,
                    )
                )
        selected = tuple(sorted(matches, key=lambda r: (-r.similarity, r.sample_id))[:3])
        return response(selected, None if selected else "no_matching_training_reference")


def _normal(values):
    vector = np.asarray(values, dtype=float)
    if vector.shape != (384,) or not np.isfinite(vector).all():
        raise ExperimentError("invalid_comparable_embedding")
    norm = float(np.linalg.norm(vector))
    if not math.isfinite(norm):
        raise ExperimentError("invalid_comparable_embedding")
    return tuple(float(v) for v in vector / norm) if norm else None


def _technical_format(record):
    # This is technical portrait/short-video compatibility, never editorial genre.
    return 0 < record.duration_seconds <= 60 and record.height > record.width


def _evidence_path(root, reference, forbidden):
    relative = Path(reference)
    path = (root / relative).resolve()
    if (
        relative.is_absolute()
        or not path.is_relative_to(root)
        or path in forbidden
        or path.name in ("records.json", "predictor-inputs.json")
    ):
        raise ExperimentError("nontrain_comparable_evidence_forbidden")
    return path


def load_training_index(settings, evidence_root, *, minimum_similarity) -> TrainingIndex:
    """Select the served bundle's training IDs before dereferencing evidence.

    The context loader validates the native artifact/cohort/baseline/runtime.
    This loader verifies only train raw receipts and reconstructs its frozen
    split digest. Train outcomes are discarded before building the index.
    A similarity threshold is explicit operator configuration, not calibrated.
    """
    if (
        type(minimum_similarity) not in (int, float)
        or not math.isfinite(minimum_similarity)
        or not 0 <= minimum_similarity <= 1
    ):
        raise ExperimentError("invalid_comparable_threshold")
    root = Path(evidence_root).resolve()
    release, baseline, bundle = load_model_context(settings)
    artifact = bundle.artifact
    manifest = load_partitions(settings.cohort_dir / "partitions.json")
    rows = tuple(r for r in manifest.assignments if r.partition == "train")
    ids = tuple(r.sample_id for r in rows)
    if (
        ids != artifact.training_sample_ids
        or ids != baseline.training_sample_ids
        or release.release_sha256 != artifact.cohort_sha256
        or manifest.manifest_sha256 != artifact.partition_manifest_sha256
        or baseline.artifact_sha256 != artifact.baseline_sha256
    ):
        raise ExperimentError("comparable_training_lineage_mismatch")
    metadata = {r.sample_id: r for r in release.records}
    index = json.loads(read_json(settings.cohort_dir / "evidence-index.json"))
    # These are path metadata, not evidence contents. Deny redirects before open.
    forbidden = {
        (root / index[r.sample_id][key]).resolve()
        for r in manifest.assignments
        if r.partition != "train"
        for key in ("features_ref", "run_ref")
    }
    inputs, targets, entries = [], [], []
    for row in rows:
        record, entry = metadata[row.sample_id], index[row.sample_id]
        curation = entry["curation"]
        if digest(curation) != record.curation_evidence_sha256:
            raise ExperimentError("comparable_curation_mismatch")
        payload = []
        for ref, checksum in (("features_ref", "features_sha256"), ("run_ref", "run_sha256")):
            path = _evidence_path(root, entry[ref], forbidden)
            raw = read_json(path)
            if hashlib.sha256(raw).hexdigest() != curation[checksum]:
                raise ExperimentError("comparable_evidence_mismatch")
            payload.append(json.loads(raw))
        features, run = payload
        count = run["source"]["target"]["view_count_observed"]
        expected_audit = {
            "video_id": record.sample_id,
            "channel_id": record.channel_id,
            "source_url": record.source_url,
            "published_at_utc": record.published_at_utc,
            "observed_at_utc": record.observed_at_utc,
        }
        if (
            observation_digest(record.model_dump(), count) != record.frozen_observation_sha256
            or run["source"]["audit"] != expected_audit
            or run["status"] != "completed"
            or run["temporary_directory_removed"] is not True
            or run["media_fingerprint"]["sha256"] != record.media_sha256
            or any(
                features["properties"][key] != getattr(record, key)
                for key in ("duration_seconds", "width", "height")
            )
        ):
            raise ExperimentError("comparable_observation_mismatch")
        p = PredictorInputs(
            sector=record.sector,
            duration_seconds=record.duration_seconds,
            aspect_ratio_height_over_width=record.height / record.width,
            text_status=features["text_features_status"],
            text_embedding=tuple(features["text_embedding"])
            if features["text_embedding"] is not None
            else None,
        )
        inputs.append(p)
        targets.append(TrainingTarget(sample_id=record.sample_id, view_count=count))
        if p.text_status == "extracted" and _technical_format(record):
            normalized = _normal(p.text_embedding)
            if normalized is not None:
                entries.append(_Entry(record, normalized))
    split = DevelopmentSplit(
        partition="train",
        sample_ids=ids,
        channel_ids=tuple(r.channel_id for r in rows),
        inputs=tuple(inputs),
        targets=tuple(targets),
    )
    if split_digest(split) != artifact.train_split_sha256:
        raise ExperimentError("comparable_training_split_changed")
    return TrainingIndex(
        artifact.artifact_sha256,
        release.release_sha256,
        manifest.manifest_sha256,
        len(ids),
        float(minimum_similarity),
        tuple(entries),
        tuple((metadata[r.sample_id].media_sha256, r.duplicate_group) for r in rows),
    )

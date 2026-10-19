"""Revalidate the released corpus, then expose only train/validation to experiment A.

The importer reads all evidence for integrity. Test labels/features never cross the
training boundary: no test matrix, target vector, prediction or metric is built.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Literal

from pydantic import TypeAdapter, model_validator

from scripts.channel_partitions import (
    ExperimentError,
    FrozenContract,
    Identifier,
    PartitionManifest,
    digest,
    load_partitions,
)
from scripts.empirical_baseline import BaselineArtifact, TrainingTarget
from scripts.observed_baseline import CuratedReference, load_observed_baseline, read_json
from scripts.training_manifest import PredictorInputs, TrainingReference, import_training_manifest

FEATURE_NAMES = (
    "sector",
    "duration_seconds",
    "aspect_ratio_height_over_width",
    "text_status",
    *(f"speech_minilm_{i:03d}" for i in range(384)),
)
CATEGORICAL_INDICES = (0, 3)
MISSING_POLICY = "zero_embedding_for_train_supported_text_status_v1"


class DevelopmentSplit(FrozenContract):
    partition: Literal["train", "validation"]
    sample_ids: tuple[Identifier, ...]
    channel_ids: tuple[Identifier, ...]
    inputs: tuple[PredictorInputs, ...]
    targets: tuple[TrainingTarget, ...]

    @model_validator(mode="after")
    def aligned(self):
        if (
            not self.sample_ids
            or self.sample_ids != tuple(sorted(set(self.sample_ids)))
            or not len(self.sample_ids)
            == len(self.channel_ids)
            == len(self.inputs)
            == len(self.targets)
            or self.sample_ids != tuple(t.sample_id for t in self.targets)
        ):
            raise ExperimentError("development_split_mismatch")
        return self


@dataclass(frozen=True)
class DevelopmentData:
    manifest: PartitionManifest
    cohort_sha256: str
    extractor_config: dict
    baseline: BaselineArtifact
    train: DevelopmentSplit
    validation: DevelopmentSplit


def check_extractor_runtime(config: dict, scripts_root: Path):
    """Check frozen source files and installed packages without loading any weights."""
    files = config.get("extractor_files_sha256", {})
    packages = config.get("packages", {})
    required = {"pilot_licensed_media.py", "audio_features.py", "visual_attributes.py"}
    if not required <= set(files) or not {"faster-whisper", "sentence-transformers"} <= set(
        packages
    ):
        raise ExperimentError("incomplete_extractor_config")
    for name, expected in files.items():
        if (
            Path(name).name != name
            or hashlib.sha256(read_json(scripts_root / name)).hexdigest() != expected
        ):
            raise ExperimentError("incompatible_extractor_files")
    if any(version(name) != expected for name, expected in packages.items()):
        raise ExperimentError("incompatible_extractor_packages")


def load_development_data(directory: Path, *, evidence_root: Path) -> DevelopmentData:
    """Trust local operator paths; never regenerate partitions or refresh observations."""
    directory, evidence_root = Path(directory), Path(evidence_root).resolve()
    release, baseline = load_observed_baseline(directory)
    manifest = load_partitions(directory / "partitions.json")
    records = TypeAdapter(list[TrainingReference]).validate_json(
        read_json(directory / "records.json")
    )
    metadata = [
        r.model_dump(include=set(CuratedReference.model_fields))
        for r in sorted(records, key=lambda r: r.sample_id)
    ]
    if metadata != [r.model_dump() for r in release.records]:
        raise ExperimentError("training_cohort_mismatch")
    config = json.loads(read_json(directory / "extractor-config.json"))
    check_extractor_runtime(config, Path(__file__).parent)
    index = json.loads(read_json(directory / "evidence-index.json"))
    evidence = {}
    for sample_id, entry in index.items():
        pair = []
        for key in ("features_ref", "run_ref"):
            relative = Path(entry[key])
            resolved = (evidence_root / relative).resolve()
            if relative.is_absolute() or not resolved.is_relative_to(evidence_root):
                raise ExperimentError("unsafe_evidence_path")
            pair.append(read_json(resolved))
        evidence[sample_id] = tuple(pair)
    readiness, predictors = import_training_manifest(
        [r.model_dump() for r in records], evidence, config, partitions=manifest
    )
    if not readiness["training_release_available"]:
        raise ExperimentError("training_not_released")
    persisted = TypeAdapter(dict[str, PredictorInputs]).validate_json(
        read_json(directory / "predictor-inputs.json")
    )
    if persisted != predictors:
        raise ExperimentError("persisted_predictors_mismatch")
    by_id = {r.sample_id: r for r in records}

    def split(partition):
        rows = [r for r in manifest.assignments if r.partition == partition]
        return DevelopmentSplit(
            partition=partition,
            sample_ids=tuple(r.sample_id for r in rows),
            channel_ids=tuple(r.channel_id for r in rows),
            inputs=tuple(predictors[r.sample_id] for r in rows),
            targets=tuple(
                TrainingTarget(
                    sample_id=r.sample_id, view_count=by_id[r.sample_id].view_count_observed
                )
                for r in rows
            ),
        )

    data = DevelopmentData(
        manifest, release.release_sha256, config, baseline, split("train"), split("validation")
    )
    validate_development_data(data)
    return data


def validate_development_data(data: DevelopmentData):
    """Defend the fit API too, including callers constructing synthetic fixtures."""
    manifest = PartitionManifest.model_validate(data.manifest)
    for name in ("train", "validation"):
        split = DevelopmentSplit.model_validate(getattr(data, name))
        rows = [r for r in manifest.assignments if r.partition == name]
        if (
            split.partition != name
            or split.sample_ids != tuple(r.sample_id for r in rows)
            or split.channel_ids != tuple(r.channel_id for r in rows)
            or tuple(p.sector for p in split.inputs) != tuple(r.sector for r in rows)
        ):
            raise ExperimentError("development_partition_mismatch")
    from scripts.empirical_baseline import fit_baseline

    if data.baseline != fit_baseline(manifest, list(data.train.targets)):
        raise ExperimentError("development_baseline_mismatch")
    if {p.sector for p in data.train.inputs} != {"moda", "beleza"}:
        raise ExperimentError("missing_sector_training_support")


def split_digest(split: DevelopmentSplit) -> str:
    return digest(split.model_dump())


def feature_matrix(inputs, *, supported_text_statuses: tuple[str, ...]) -> list[list]:
    """Fixed representation: no fitted scaler/imputer/PCA; labels and IDs have no slot."""
    rows = []
    for value in inputs:
        value = PredictorInputs.model_validate(value)
        if value.text_status not in supported_text_statuses:
            raise ExperimentError("unsupported_text_status")
        rows.append(
            [
                value.sector,
                value.duration_seconds,
                value.aspect_ratio_height_over_width,
                value.text_status,
                *(value.text_embedding if value.text_embedding is not None else (0.0,) * 384),
            ]
        )
    return rows

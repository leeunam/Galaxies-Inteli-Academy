"""B-cache: the unchanged A inputs plus verified cached CLIP/image/audio signals."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from scripts.channel_partitions import ExperimentError, FrozenContract, digest
from scripts.diagnose_m1 import load_diagnostic_data
from scripts.experiment_a_data import (
    FEATURE_NAMES as A_FEATURE_NAMES,
)
from scripts.experiment_a_data import (
    DevelopmentData,
    validate_development_data,
)
from scripts.experiment_a_data import (
    feature_matrix as a_matrix,
)
from scripts.training_manifest import PredictorInputs

FEATURE_NAMES = (
    *A_FEATURE_NAMES,
    *(f"image_clip_{i:03d}" for i in range(512)),
    "brightness_mean_0_1",
    "saturation_mean_0_1",
    "audio_rms",
    "audio_duration_seconds",
    "audio_status",
)
CATEGORICAL_INDICES = (0, 3, 904)
REPRESENTATION = "b_cached_clip_audio_905_v1_no_vlm_no_imputation"


class BInputs(FrozenContract):
    a: PredictorInputs
    image_embedding: tuple[float, ...] = Field(min_length=512, max_length=512)
    brightness_mean_0_1: float = Field(ge=0, le=1)
    saturation_mean_0_1: float = Field(ge=0, le=1)
    audio_rms: float = Field(ge=0, le=1)
    audio_duration_seconds: float = Field(gt=0, le=61)
    audio_status: Literal["transcribed"]

    @model_validator(mode="after")
    def complete_modalities(self):
        if self.a.text_status != "extracted":
            raise ExperimentError("b_requires_supported_transcribed_audio")
        return self


@dataclass(frozen=True)
class BDevelopmentData:
    base: DevelopmentData
    train: tuple[BInputs, ...]
    validation: tuple[BInputs, ...]


def validate_data(data):
    validate_development_data(data.base)
    for part in ("train", "validation"):
        extras, original = getattr(data, part), getattr(data.base, part)
        checked = tuple(BInputs.model_validate(v) for v in extras)
        if tuple(v.a for v in checked) != original.inputs:
            raise ExperimentError("b_development_alignment_mismatch")


def feature_matrix(inputs):
    values = tuple(BInputs.model_validate(v) for v in inputs)
    prefix = a_matrix(tuple(v.a for v in values), supported_text_statuses=("extracted",))
    return [
        a
        + list(v.image_embedding)
        + [
            v.brightness_mean_0_1,
            v.saturation_mean_0_1,
            v.audio_rms,
            v.audio_duration_seconds,
            v.audio_status,
        ]
        for a, v in zip(prefix, values, strict=True)
    ]


def split_digest(data, part):
    return digest(
        {
            "base": getattr(data.base, part).model_dump(),
            "inputs": [v.model_dump() for v in getattr(data, part)],
        }
    )


def load_data(cohort, root):
    """Select development first; never walk the unrestricted evidence index."""
    index_raw = (cohort / "evidence-index.json").read_bytes()
    base, opened = load_diagnostic_data(cohort, root)
    if index_raw != (cohort / "evidence-index.json").read_bytes():
        raise ExperimentError("b_index_changed")
    index = json.loads(index_raw)

    def load(part):
        split = getattr(base, part)
        values = []
        for sample, a in zip(split.sample_ids, split.inputs, strict=True):
            entry = index[sample]
            relative = Path(entry["features_ref"])
            path = (root / relative).resolve()
            if relative.is_absolute() or not path.is_relative_to(root.resolve()):
                raise ExperimentError("unsafe_b_evidence_path")
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != entry["curation"]["features_sha256"]:
                raise ExperimentError("b_evidence_changed")
            f = json.loads(raw)
            if (
                f["schema_version"] != "creative-features-v1"
                or f["feature_policy"]["clip_pooling"] != "mean_of_deduplicated_sample_frames"
                or f["vlm"]["status"] != "not_requested"
            ):
                raise ExperimentError("incompatible_b_cached_policy")
            values.append(
                BInputs(
                    a=a,
                    image_embedding=tuple(f["image_embedding"]),
                    brightness_mean_0_1=f["properties"]["brightness_mean_0_1"],
                    saturation_mean_0_1=f["properties"]["saturation_mean_0_1"],
                    audio_rms=f["audio_rms"],
                    audio_duration_seconds=f["audio_duration_seconds"],
                    audio_status=f["audio_status"],
                )
            )
        return tuple(values)

    data = BDevelopmentData(base, load("train"), load("validation"))
    validate_data(data)
    return data, opened

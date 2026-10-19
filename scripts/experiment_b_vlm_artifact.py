"""Isolated B-VLM native bundle with a frozen perception release and exact B-cache prefix."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Literal

import numpy as np
from catboost import CatBoostRegressor, Pool
from pydantic import model_validator

from scripts.channel_partitions import (
    Digest,
    ExperimentError,
    FrozenContract,
    Identifier,
    digest,
    save_new_json,
)
from scripts.experiment_a_artifact import SearchProtocol, Trial
from scripts.experiment_a_metrics import (
    QUANTILES,
    REPAIR_POLICY,
    checked_logs,
    repair_quantiles,
    views_from_logs,
)
from scripts.experiment_b_vlm_data import (
    REPRESENTATION,
    QualityRelease,
    categorical_indices,
    feature_matrix,
    feature_names,
)
from scripts.observed_baseline import read_json

MISSING_POLICY = "require_complete_released_vlm_and_cached_modalities_v1"
MODEL_FILES = ("q10.cbm", "q50.cbm", "q90.cbm")
SOURCE_FILES = (
    "experiment_a_data.py",
    "experiment_a_metrics.py",
    "experiment_a_artifact.py",
    "train_experiment_a.py",
    "experiment_b_data.py",
    "experiment_b_artifact.py",
    "train_experiment_b.py",
    "diagnose_m1.py",
    "channel_partitions.py",
    "training_manifest.py",
    "observed_baseline.py",
    "empirical_baseline.py",
    "retrain_expansion.py",
    "private_checkpoint.py",
    "experiment_b_vlm_extract.py",
    "experiment_b_vlm_quality.py",
    "experiment_b_vlm_data.py",
    "experiment_b_vlm_artifact.py",
    "train_experiment_b_vlm.py",
    "vlm_frame_evidence.py",
)


def source_hashes():
    return {
        name: hashlib.sha256(read_json(Path(__file__).parent / name)).hexdigest()
        for name in SOURCE_FILES
    }


class ExperimentArtifact(FrozenContract):
    schema_version: Literal["experiment-b-vlm-catboost-v1"] = "experiment-b-vlm-catboost-v1"
    experiment: Literal["B_FULL_VLM"] = "B_FULL_VLM"
    representation: Literal["b_cached_905_plus_released_vlm_cells_v1"] = REPRESENTATION
    vlm_used: Literal[True] = True
    data_kind: Literal["synthetic", "observed_pilot"]
    target_transform: Literal["log1p"] = "log1p"
    target_definition: Literal["public_views_observed_age_30_le_days_lt_37"] = (
        "public_views_observed_age_30_le_days_lt_37"
    )
    predictive_quality_validated: Literal[False] = False
    coverage_status: Literal["not_validated"] = "not_validated"
    final_test_evaluated: Literal[False] = False
    quality_release: QualityRelease
    vlm_config: dict
    vlm_config_sha256: Digest
    feature_names: tuple[str, ...]
    categorical_indices: tuple[int, ...]
    missing_policy: Literal["require_complete_released_vlm_and_cached_modalities_v1"] = (
        MISSING_POLICY
    )
    repair_policy: Literal["lower_min_raw_upper_max_raw_preserve_q50_v1"] = REPAIR_POLICY
    supported_text_statuses: tuple[
        Literal["extracted", "no_audio_stream", "no_speech_detected_by_asr"], ...
    ]
    extractor_config: dict
    extractor_config_sha256: Digest
    cohort_sha256: Digest
    partition_manifest_sha256: Digest
    baseline_sha256: Digest
    train_split_sha256: Digest
    validation_split_sha256: Digest
    training_sample_ids: tuple[Identifier, ...]
    validation_sample_ids: tuple[Identifier, ...]
    runtime_versions: dict[str, str]
    source_files_sha256: dict[str, Digest]
    uv_lock_sha256: Digest
    protocol: SearchProtocol = SearchProtocol()
    trials: tuple[Trial, ...]
    selected: tuple[Trial, ...]
    model_sha256: dict[str, Digest]
    validation_report_sha256: Digest
    artifact_sha256: Digest

    @model_validator(mode="after")
    def integrity(self):
        expected = {(q, d, l2) for q in QUANTILES for d in (4, 6) for l2 in (3, 10)}
        if (
            self.feature_names != feature_names(self.quality_release)
            or self.categorical_indices != categorical_indices(self.quality_release)
            or self.vlm_config_sha256 != digest(self.vlm_config)
            or self.supported_text_statuses != ("extracted",)
            or not self.supported_text_statuses
            or self.supported_text_statuses != tuple(sorted(set(self.supported_text_statuses)))
            or self.extractor_config_sha256 != digest(self.extractor_config)
            or len(self.trials) != 12
            or {(t.quantile, t.depth, t.l2_leaf_reg) for t in self.trials} != expected
            or tuple(t.quantile for t in self.selected) != QUANTILES
            or set(self.model_sha256) != set(MODEL_FILES)
            or set(self.source_files_sha256) != set(SOURCE_FILES)
            or self.artifact_sha256 != digest(self.model_dump(exclude={"artifact_sha256"}))
        ):
            raise ExperimentError("experiment_artifact_mismatch")
        for ids in (self.training_sample_ids, self.validation_sample_ids):
            if not ids or ids != tuple(sorted(set(ids))):
                raise ExperimentError("artifact_sample_ids_mismatch")
        if set(self.training_sample_ids) & set(self.validation_sample_ids):
            raise ExperimentError("artifact_sample_ids_mismatch")
        for selected in self.selected:
            best = min(
                (t for t in self.trials if t.quantile == selected.quantile),
                key=lambda t: (t.validation_score, t.depth, t.l2_leaf_reg),
            )
            if selected != best:
                raise ExperimentError("artifact_selection_mismatch")
        return self


@dataclass(frozen=True)
class ExperimentBundle:
    artifact: ExperimentArtifact
    models: tuple[CatBoostRegressor, ...]

    def predict_logs(self, inputs, *, repaired=True):
        matrix = feature_matrix(inputs, self.artifact.quality_release)
        pool = Pool(
            matrix,
            cat_features=list(self.artifact.categorical_indices),
            feature_names=list(self.artifact.feature_names),
        )
        raw = checked_logs(np.column_stack([model.predict(pool) for model in self.models]))
        return repair_quantiles(raw) if repaired else raw

    def predict_views(self, inputs):
        return views_from_logs(self.predict_logs(inputs))


def save_bundle(directory: Path, body: dict, models, report: dict) -> ExperimentBundle:
    """Exclusive directory, private files, manifest published last; never overwrite."""
    directory = Path(directory)
    directory.mkdir(parents=True, mode=0o700, exist_ok=False)
    hashes = {}
    for name, model in zip(MODEL_FILES, models, strict=True):
        path = directory / name
        model.save_model(str(path), format="cbm")
        os.chmod(path, 0o600)
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    raw = (json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    path = directory / "validation-report.json"
    with path.open("xb") as handle:
        os.chmod(path, 0o600)
        handle.write(raw)
    body = body | {
        "quality_release": QualityRelease.model_validate_json(json.dumps(body["quality_release"])),
        "model_sha256": hashes,
        "validation_report_sha256": hashlib.sha256(raw).hexdigest(),
        "protocol": SearchProtocol.model_validate_json(json.dumps(body["protocol"])),
        "trials": tuple(Trial.model_validate(t) for t in body["trials"]),
        "selected": tuple(Trial.model_validate(t) for t in body["selected"]),
    }
    # Defaults participate in the content checksum as well.
    body = ExperimentArtifact.model_construct(**body, artifact_sha256="0" * 64).model_dump(
        exclude={"artifact_sha256"}
    )
    artifact = ExperimentArtifact.model_validate_json(
        json.dumps(body | {"artifact_sha256": digest(body)})
    )
    save_new_json(directory / "artifact.json", artifact)
    return ExperimentBundle(artifact, tuple(models))


def load_bundle(
    directory: Path,
    *,
    expected_extractor_config: dict,
    expected_vlm_config: dict,
    expected_quality_release_sha256: str,
    expected_partition_sha256: str | None = None,
    expected_cohort_sha256: str | None = None,
) -> ExperimentBundle:
    directory = Path(directory)
    artifact = ExperimentArtifact.model_validate_json(read_json(directory / "artifact.json"))
    if (
        artifact.runtime_versions != {"catboost": version("catboost"), "numpy": version("numpy")}
        or artifact.extractor_config != expected_extractor_config
        or artifact.vlm_config != expected_vlm_config
        or artifact.quality_release.release_sha256 != expected_quality_release_sha256
        or artifact.quality_release.source_sha256
        != artifact.source_files_sha256["experiment_b_vlm_quality.py"]
        or artifact.source_files_sha256 != source_hashes()
        or artifact.uv_lock_sha256
        != hashlib.sha256(read_json(Path(__file__).parent.parent / "uv.lock")).hexdigest()
        or (
            expected_partition_sha256 is not None
            and artifact.partition_manifest_sha256 != expected_partition_sha256
        )
        or (expected_cohort_sha256 is not None and artifact.cohort_sha256 != expected_cohort_sha256)
    ):
        raise ExperimentError("incompatible_experiment_artifact")
    raw = read_json(directory / "validation-report.json")
    if hashlib.sha256(raw).hexdigest() != artifact.validation_report_sha256:
        raise ExperimentError("validation_report_mismatch")
    models = []
    for name, trial in zip(MODEL_FILES, artifact.selected, strict=True):
        path = directory / name
        if (
            path.stat().st_size > 128 * 1024 * 1024
            or hashlib.sha256(path.read_bytes()).hexdigest() != artifact.model_sha256[name]
        ):
            raise ExperimentError("model_checksum_mismatch")
        model = CatBoostRegressor()
        model.load_model(str(path), format="cbm")
        params = model.get_all_params()
        if (
            tuple(model.feature_names_) != artifact.feature_names
            or tuple(model.get_cat_feature_indices()) != artifact.categorical_indices
            or model.tree_count_ != trial.tree_count
            or params["depth"] != trial.depth
            or params["l2_leaf_reg"] != trial.l2_leaf_reg
            or params["loss_function"] != f"Quantile:alpha={trial.quantile}"
            or not np.isclose(params["learning_rate"], 0.05)
            or params["random_seed"] != 42
            or params["task_type"] != "CPU"
        ):
            raise ExperimentError("model_contract_mismatch")
        models.append(model)
    return ExperimentBundle(artifact, tuple(models))

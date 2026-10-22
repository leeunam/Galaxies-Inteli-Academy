"""Offline C representation: the exact B-VLM rows, with train-only category codes."""

from __future__ import annotations

import numpy as np
from pydantic import model_validator

from scripts.channel_partitions import ExperimentError, FrozenContract, digest
from scripts.experiment_b_vlm_data import (
    QualityRelease,
    VLMDevelopmentData,
    categorical_indices,
    feature_matrix,
    feature_names,
    split_digest,
    validate_data,
)


def validate_offline_data(data):
    # No file loader or approval flag: this delivery cannot fit/evaluate real data.
    if not isinstance(data, VLMDevelopmentData):
        raise ExperimentError("c_requires_full_b_vlm_data")
    if data.base.manifest.data_kind != "synthetic":
        raise ExperimentError("c_offline_real_data_blocked")
    if data.vlm_config.get("synthetic") is not True:
        raise ExperimentError("c_offline_requires_invented_extraction")
    validate_data(data)


class CategoryEncoding(FrozenContract):
    feature_names: tuple[str, ...]
    categorical_indices: tuple[int, ...]
    categories: dict[str, tuple[str, ...]]

    @model_validator(mode="after")
    def integrity(self):
        if (
            len(set(self.feature_names)) != len(self.feature_names)
            or self.categorical_indices != tuple(sorted(set(self.categorical_indices)))
            or any(i < 0 or i >= len(self.feature_names) for i in self.categorical_indices)
            or set(self.categories) != {self.feature_names[i] for i in self.categorical_indices}
            or any(not v or v != tuple(sorted(set(v))) for v in self.categories.values())
        ):
            raise ExperimentError("invalid_c_category_encoding")
        return self

    def transform(self, inputs, release):
        encoding = CategoryEncoding.model_validate(self)
        if encoding.feature_names != feature_names(
            release
        ) or encoding.categorical_indices != categorical_indices(release):
            raise ExperimentError("c_feature_contract_mismatch")
        rows = feature_matrix(inputs, release)
        if not rows:
            raise ExperimentError("c_empty_matrix")
        maps = {
            i: {value: code for code, value in enumerate(self.categories[self.feature_names[i]])}
            for i in self.categorical_indices
        }
        for row in rows:
            for index, mapping in maps.items():
                if row[index] not in mapping:
                    raise ExperimentError("c_category_without_training_support")
                row[index] = mapping[row[index]]
        matrix = np.asarray(rows, dtype=np.float64)
        if matrix.shape != (len(rows), len(self.feature_names)) or not np.isfinite(matrix).all():
            raise ExperimentError("c_invalid_feature_matrix")
        return matrix


def fit_encoding(data):
    validate_offline_data(data)
    # Validation, targets and audit identifiers have no place in this vocabulary.
    rows = feature_matrix(data.train, data.release)
    names, indices = feature_names(data.release), categorical_indices(data.release)
    return CategoryEncoding(
        feature_names=names,
        categorical_indices=indices,
        categories={names[i]: tuple(sorted({row[i] for row in rows})) for i in indices},
    )


def pairing(data):
    """Content identity shared with B, including ordered rows, labels and partitions."""
    validate_offline_data(data)
    return {
        "cohort_sha256": data.base.cohort_sha256,
        "partition_manifest_sha256": data.base.manifest.manifest_sha256,
        "baseline_sha256": data.base.baseline.artifact_sha256,
        "train_split_sha256": split_digest(data, "train"),
        "validation_split_sha256": split_digest(data, "validation"),
        "training_sample_ids": data.base.train.sample_ids,
        "validation_sample_ids": data.base.validation.sample_ids,
        "extractor_config": data.base.extractor_config,
        "vlm_config": data.vlm_config,
        "quality_release": data.release.model_dump(),
    }


def assert_pairing(data, artifact):
    expected = pairing(data)
    actual = {name: getattr(artifact, name) for name in expected}
    actual["quality_release"] = QualityRelease.model_validate(
        actual["quality_release"]
    ).model_dump()
    if (
        artifact.data_kind != "synthetic"
        or artifact.final_test_evaluated is not False
        or artifact.feature_names != feature_names(data.release)
        or artifact.categorical_indices != categorical_indices(data.release)
        or digest(actual) != digest(expected)
    ):
        raise ExperimentError("bc_pairing_mismatch")

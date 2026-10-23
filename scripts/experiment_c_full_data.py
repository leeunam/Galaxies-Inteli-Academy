"""Full C boundary, separate from the sealed synthetic-only and cache-only paths."""

from scripts.channel_partitions import ExperimentError, digest
from scripts.experiment_b_vlm_data import (
    QualityRelease,
    VLMDevelopmentData,
    categorical_indices,
    feature_matrix,
    feature_names,
    split_digest,
    validate_data,
)
from scripts.experiment_c_data import CategoryEncoding


def validate_full_data(data):
    # Reject missing/failed perception before the cached validator reads targets.
    if not isinstance(data, VLMDevelopmentData):
        raise ExperimentError("c_full_requires_released_b_vlm_data")
    release = QualityRelease.model_validate(data.release)
    kind = data.base.manifest.data_kind
    if kind == "observed_pilot":
        if data.vlm_config.get("synthetic") is not False:
            raise ExperimentError("c_full_observed_extraction_provenance_required")
        if (
            len(data.train) != 203
            or len(data.validation) != 66
            or not set(release.released_fields)
            <= {"person_visible", "product_visible_early", "screen_text"}
        ):
            raise ExperimentError("c_full_requires_269_rows_and_current_release_scope")
    elif kind != "synthetic" or data.vlm_config.get("synthetic") is not True:
        raise ExperimentError("c_full_data_kind_mismatch")
    validate_data(data)


def fit_encoding(data):
    validate_full_data(data)
    rows = feature_matrix(data.train, data.release)
    names, indices = feature_names(data.release), categorical_indices(data.release)
    return CategoryEncoding(
        feature_names=names,
        categorical_indices=indices,
        categories={names[i]: tuple(sorted({row[i] for row in rows})) for i in indices},
    )


def pairing(data):
    validate_full_data(data)
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
        artifact.data_kind != data.base.manifest.data_kind
        or artifact.final_test_evaluated is not False
        or artifact.feature_names != feature_names(data.release)
        or artifact.categorical_indices != categorical_indices(data.release)
        or digest(actual) != digest(expected)
    ):
        raise ExperimentError("bc_full_pairing_mismatch")

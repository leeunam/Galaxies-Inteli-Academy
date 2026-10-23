"""Native signed q50 contributions for the versioned full B/C bundles."""

from math import fsum, isclose

import numpy as np
from catboost import Pool

from scripts.channel_partitions import ExperimentError, digest
from scripts.experiment_b_vlm_artifact import ExperimentArtifact as BArtifact
from scripts.experiment_b_vlm_data import feature_matrix
from scripts.train_experiment_c_full import ExperimentArtifact as CArtifact
from scripts.train_experiment_c_full import reload_observed_bundle


def feature_groups(release):
    return (
        ("sector", (0,)),
        ("file_properties", (1, 2)),
        ("text_status", (3,)),
        ("speech_embedding", tuple(range(4, 388))),
        ("image_embedding", tuple(range(388, 900))),
        ("image_measures", (900, 901)),
        ("audio_measures_and_status", (902, 903, 904)),
        *((f"vlm_{field}", (905 + i,)) for i, field in enumerate(release.released_fields)),
    )


def explain_full(bundle, inputs, *, data=None):
    """Caller loads the checked native bundle; labels and comparables are not read."""
    inputs = tuple(inputs)
    if bundle.artifact.data_kind == "observed_pilot":
        if data is None:
            raise ExperimentError("full_shap_observed_requires_verified_development")
        bundle = reload_observed_bundle(bundle, data=data)
    if not 1 <= len(inputs) <= 5 or len(bundle.models) != 3:
        raise ExperimentError("full_shap_requires_one_to_five_inputs_and_three_models")
    artifact = bundle.artifact
    if isinstance(artifact, BArtifact):
        artifact = BArtifact.model_validate(artifact)
        matrix = Pool(
            feature_matrix(inputs, artifact.quality_release),
            cat_features=list(artifact.categorical_indices),
            feature_names=list(artifact.feature_names),
        )
        contributions = bundle.models[1].get_feature_importance(
            matrix, type="ShapValues", thread_count=1, verbose=False
        )
        method = "native_catboost_shap"
    elif isinstance(artifact, CArtifact):
        artifact = CArtifact.model_validate(artifact)
        matrix = artifact.encoding.transform(inputs, artifact.quality_release)
        contributions = bundle.models[1].predict(matrix, pred_contrib=True, num_threads=1)
        method = "native_lightgbm_pred_contrib"
    else:
        raise ExperimentError("full_shap_requires_full_b_or_c_artifact")
    contributions = np.asarray(contributions, dtype=float)
    prediction = bundle.predict_logs(inputs, repaired=False)
    groups = feature_groups(artifact.quality_release)
    indices = [i for _, members in groups for i in members]
    if (
        sorted(indices) != list(range(len(artifact.feature_names)))
        or contributions.shape != (len(inputs), len(artifact.feature_names) + 1)
        or not np.isfinite(contributions).all()
    ):
        raise ExperimentError("full_shap_shape_or_coverage_mismatch")
    evidence = []
    for row, predicted in zip(contributions, prediction, strict=True):
        drivers = [
            {"group": name, "contribution_log": fsum(float(row[i]) for i in members)}
            for name, members in groups
        ]
        reconstructed = float(row[-1]) + fsum(d["contribution_log"] for d in drivers)
        if not isclose(reconstructed, predicted[1], rel_tol=1e-9, abs_tol=1e-7):
            raise ExperimentError("full_shap_reconstruction_failed")
        value = {
            "schema_version": "full-model-q50-evidence-v1",
            "method": method,
            "model_artifact_sha256": artifact.artifact_sha256,
            "quality_release_sha256": artifact.quality_release.release_sha256,
            "quantile": 0.5,
            "scale": "log1p_views",
            "prediction_log": float(predicted[1]),
            "base_value_log": float(row[-1]),
            "drivers": drivers,
            "absolute_reconstruction_error": abs(reconstructed - predicted[1]),
            "causal": False,
        }
        evidence.append(value | {"evidence_sha256": digest(value)})
    return tuple(evidence)

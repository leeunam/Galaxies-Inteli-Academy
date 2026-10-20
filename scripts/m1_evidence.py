"""Local q50 SHAP evidence from an already verified M1 bundle; no service changes."""

from __future__ import annotations

from math import fsum, isclose
from typing import Literal

import numpy as np
from catboost import CatBoostError, Pool
from pydantic import Field, ValidationError, model_validator

from scripts.channel_partitions import Digest, ExperimentError, FrozenContract
from scripts.empirical_baseline import MAX_LOG_VIEWS
from scripts.experiment_a_data import CATEGORICAL_INDICES, FEATURE_NAMES, feature_matrix
from scripts.experiment_a_metrics import checked_logs

GROUPS = (
    ("sector", (0,)),
    ("file_properties", (1, 2)),
    ("text_status", (3,)),
    ("speech_embedding", tuple(range(4, len(FEATURE_NAMES)))),
)


class GroupedDriver(FrozenContract):
    group: Literal["sector", "file_properties", "text_status", "speech_embedding"]
    contribution_log: float


class M1Evidence(FrozenContract):
    schema_version: Literal["m1-shap-evidence-v1"] = "m1-shap-evidence-v1"
    method: Literal["native_catboost_shap"] = "native_catboost_shap"
    model_artifact_sha256: Digest
    quantile: Literal[0.5] = 0.5
    scale: Literal["log1p_views"] = "log1p_views"
    prediction_log: float = Field(ge=0, le=MAX_LOG_VIEWS)
    base_value_log: float
    drivers: tuple[GroupedDriver, ...]
    causal: Literal[False] = False

    @model_validator(mode="after")
    def reconstructs_q50(self):
        if tuple(d.group for d in self.drivers) != tuple(g for g, _ in GROUPS) or not isclose(
            self.base_value_log + fsum(d.contribution_log for d in self.drivers),
            self.prediction_log,
            rel_tol=1e-9,
            abs_tol=1e-7,
        ):
            raise ExperimentError("m1_shap_reconstruction_failed")
        return self


def explain_m1(bundle, inputs) -> tuple[M1Evidence, ...]:
    """Explain 1–5 supported inputs; caller loads/verifies the native bundle first.

    No reference dataset or label is supplied to SHAP. The final SHAP column is
    its base value, not another feature. Signed embedding contributions are
    summed once; exponentiating individual terms would destroy additivity.
    """
    inputs = tuple(inputs)
    artifact = bundle.artifact
    if (
        not 1 <= len(inputs) <= 5
        or artifact.experiment != "A_M1"
        or artifact.feature_names != FEATURE_NAMES
        or artifact.categorical_indices != CATEGORICAL_INDICES
        or len(bundle.models) != 3
    ):
        raise ExperimentError("incompatible_m1_evidence_contract")
    matrix = feature_matrix(inputs, supported_text_statuses=artifact.supported_text_statuses)
    try:
        pool = Pool(
            matrix, cat_features=list(CATEGORICAL_INDICES), feature_names=list(FEATURE_NAMES)
        )
        predictions = checked_logs(bundle.predict_logs(inputs, repaired=False))
        values = np.asarray(
            bundle.models[1].get_feature_importance(
                pool, type="ShapValues", thread_count=2, verbose=False
            ),
            dtype=float,
        )
    except (CatBoostError, ValueError, TypeError):
        raise ExperimentError("m1_shap_unavailable") from None
    if (
        len(predictions) != len(inputs)
        or values.shape != (len(inputs), len(FEATURE_NAMES) + 1)
        or not np.isfinite(values).all()
    ):
        raise ExperimentError("invalid_m1_shap_values")
    try:
        return tuple(
            M1Evidence(
                model_artifact_sha256=artifact.artifact_sha256,
                prediction_log=float(prediction[1]),
                base_value_log=float(row[-1]),
                drivers=tuple(
                    GroupedDriver(
                        group=group, contribution_log=fsum(float(row[i]) for i in indices)
                    )
                    for group, indices in GROUPS
                ),
            )
            for row, prediction in zip(values, predictions, strict=True)
        )
    except (ValidationError, OverflowError):
        raise ExperimentError("invalid_m1_shap_evidence") from None

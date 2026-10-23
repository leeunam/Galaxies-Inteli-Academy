"""Non-causal synthetic q50 contributions for V7 bundles."""

from __future__ import annotations

from math import fsum

import numpy as np

from scripts.channel_partitions import ExperimentError, digest
from scripts.full_visual_data_v7 import feature_names
from scripts.full_visual_models_v7 import _fresh


def feature_groups():
    names = feature_names()
    groups = (
        ("sector", (0,)),
        ("file_properties", (1, 2)),
        ("text_status", (3,)),
        ("speech_embedding", tuple(range(4, 388))),
        ("image_embedding", tuple(range(388, 900))),
        ("image_measures", (900, 901)),
        ("audio_measures_and_status", (902, 903, 904)),
        *((f"vlm_{name[4:]}", (905 + i,)) for i, name in enumerate(names[905:])),
    )
    return groups


def explain_full(bundle, inputs, *, data):
    data = _fresh(data)
    inputs = tuple(inputs)
    if not 1 <= len(inputs) <= 5 or bundle.artifact.get("data_kind") != "synthetic":
        raise ExperimentError("v7_shap_requires_one_to_five_synthetic_inputs")
    # Reload through the public verifier so in-memory model mutation is not trusted.
    from scripts.full_visual_models_v7 import load_bundle

    verified = load_bundle(bundle.directory, data=data, backend=bundle.backend)
    if verified.artifact["validation_split_sha256"] != bundle.artifact["validation_split_sha256"]:
        raise ExperimentError("v7_shap_artifact_mismatch")
    algo = verified.artifact["algorithm"]
    matrix = verified._matrix(inputs)
    q50 = verified.models[1]
    contributions = np.asarray(
        verified.backend.contributions(algorithm=algo, model=q50, matrix=matrix), dtype=float
    )
    raw = verified.predict_logs(inputs, repaired=False)
    groups = feature_groups()
    indices = [i for _, ix in groups for i in ix]
    names = feature_names()
    if (
        sorted(indices) != list(range(912))
        or len(names) != 912
        or contributions.shape != (len(inputs), 913)
        or not np.isfinite(contributions).all()
    ):
        raise ExperimentError("v7_shap_shape_or_coverage_mismatch")
    results = []
    for row, pred in zip(contributions, raw[:, 1], strict=True):
        drivers = [
            {
                "group": name,
                "feature_indices": list(ix),
                "contribution_log": fsum(float(row[i]) for i in ix),
            }
            for name, ix in groups
        ]
        reconstructed = float(row[-1]) + fsum(d["contribution_log"] for d in drivers)
        if abs(reconstructed - float(pred)) > 1e-7:
            raise ExperimentError("v7_shap_reconstruction_failed")
        body = {
            "schema_version": "front1-v7-q50-evidence-v1",
            "algorithm": algo,
            "backend_kind": verified.artifact["backend_kind"],
            "model_artifact_sha256": verified.artifact["content_sha256"],
            "model_sha256": verified.artifact["model_sha256"]["q50.model"],
            "data_manifest_sha256": data.manifest_sha256,
            "input_sha256": digest(matrix[len(results)]),
            "feature_contract_sha256": verified.artifact["feature_contract_sha256"],
            "quantile": 0.5,
            "scale": "log1p_views",
            "prediction_log": float(pred),
            "base_value_log": float(row[-1]),
            "drivers": drivers,
            "absolute_reconstruction_error": abs(reconstructed - float(pred)),
            "causal": False,
            "quality_accepted": False,
            "release_emitted": False,
        }
        results.append(body | {"evidence_sha256": digest(body)})
    return tuple(results)

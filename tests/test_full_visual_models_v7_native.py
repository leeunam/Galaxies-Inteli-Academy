"""Real C adapter regression on invented inputs; no data or served bundle is opened."""

from __future__ import annotations

import json

import lightgbm as lgb
import numpy as np
import pytest

from scripts.experiment_a_metrics import channel_weights, selection_score
from scripts.full_visual_models_v7 import (
    CATEGORICAL_INDICES,
    FEATURE_NAMES,
    NativeBackend,
    _encode_c,
    _fit_c_encoding,
    _trial_params,
)


def test_native_c_encoded_lists_fit_and_roundtrip(tmp_path):
    categories = {
        0: ("invented_a", "invented_b"),
        3: ("extracted",),
        904: ("transcribed",),
        **{i: ("false", "true", "unknown") for i in range(905, 910)},
        910: ("indoor", "outdoor", "unknown"),
        911: ("talking_head", "product_showcase", "unknown"),
    }
    assert len(FEATURE_NAMES) == 912
    assert set(categories) == set(CATEGORICAL_INDICES)

    def matrix(offset, count):
        rows = []
        for row in range(offset, offset + count):
            values = [float(((row + 1) * (col + 3)) % 23) / 23 for col in range(912)]
            for col, levels in categories.items():
                values[col] = levels[row % len(levels)]
            rows.append(values)
        return rows

    train, valid = matrix(0, 8), matrix(8, 4)
    vocabulary = _fit_c_encoding(train)
    train_x, valid_x = _encode_c(train, vocabulary), _encode_c(valid, vocabulary)
    original_train, original_valid = [row[:] for row in train_x], [row[:] for row in valid_x]
    assert isinstance(train_x, list) and all(isinstance(row, list) for row in train_x)
    assert isinstance(valid_x, list) and all(isinstance(row, list) for row in valid_x)
    train_y = np.asarray([2 + (i % 3) / 10 for i in range(8)])
    valid_y = np.asarray([2 + (i % 3) / 10 for i in range(4)])
    channels = ("invented_a", "invented_a", "invented_a", "invented_b")
    weights = channel_weights(channels)
    params = _trial_params("C", 0.5, 7, 5)
    original_params = dict(params)
    assert (params["iterations"], params["early_stopping_rounds"]) == (500, 50)
    assert (params["num_leaves"], params["min_data_in_leaf"], params["num_threads"]) == (7, 5, 1)

    backend = NativeBackend("C")
    fitted = backend.fit_trial(
        algorithm="C",
        quantile=0.5,
        params=params,
        train_x=train_x,
        train_y=train_y,
        validation_x=valid_x,
        validation_y=valid_y,
        validation_weights=weights,
        validation_channel_ids=channels,
        feature_names=FEATURE_NAMES,
        categorical_indices=CATEGORICAL_INDICES,
    )
    assert isinstance(fitted.model, lgb.Booster)
    assert fitted.predictions.shape == (4,)
    assert np.isfinite(fitted.predictions).all()
    assert 1 <= fitted.tree_count <= fitted.best_iteration < fitted.evaluated_iterations <= 500
    assert fitted.evaluated_iterations == fitted.best_iteration + 50
    assert fitted.native_validation_metric == pytest.approx(
        selection_score(valid_y, fitted.predictions, channels, 0.5), abs=1e-12
    )
    assert fitted.model.feature_name() == list(FEATURE_NAMES)
    assert fitted.model.params["categorical_column"] == list(CATEGORICAL_INDICES)
    assert fitted.model.params["num_iterations"] == 500
    for key, value in params.items():
        if key not in ("iterations", "early_stopping_rounds"):
            assert fitted.model.params[key] == value
    assert params == original_params
    assert train_x == original_train and valid_x == original_valid
    assert _fit_c_encoding(train) == vocabulary
    assert np.array_equal(
        fitted.predictions,
        backend.predict(algorithm="C", model=fitted.model, matrix=valid_x),
    )

    model_path = tmp_path / "invented-c-q50.model"
    backend.save_model(algorithm="C", model=fitted.model, path=model_path)
    loaded = backend.load_model(algorithm="C", path=model_path)
    prediction = backend.predict(algorithm="C", model=loaded, matrix=valid_x)
    assert isinstance(loaded, lgb.Booster)
    assert prediction.shape == (4,) and np.isfinite(prediction).all()
    assert np.array_equal(fitted.predictions, prediction)
    assert fitted.model.dump_model() == loaded.dump_model()
    assert model_path.stat().st_mode & 0o777 == 0o600
    assert set(tmp_path.iterdir()) == {model_path}
    print(
        json.dumps(
            {
                "backend_kind": backend.backend_kind,
                "lightgbm_version": lgb.__version__,
                "data_kind": "invented",
                "train_shape": [8, 912],
                "validation_shape": [4, 912],
                "best_iteration": fitted.best_iteration,
                "tree_count": fitted.tree_count,
                "evaluated_iterations": fitted.evaluated_iterations,
                "predictions": prediction.tolist(),
                "roundtrip_exact": True,
            },
            sort_keys=True,
        )
    )

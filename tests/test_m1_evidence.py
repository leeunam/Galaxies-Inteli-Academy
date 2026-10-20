"""M1 explanation must reconstruct q50 without inventing embedding semantics."""

from types import SimpleNamespace

import numpy as np
import pytest

from scripts.channel_partitions import ExperimentError
from scripts.experiment_a_artifact import ExperimentBundle
from scripts.experiment_a_data import CATEGORICAL_INDICES, FEATURE_NAMES
from scripts.m1_evidence import explain_m1
from scripts.training_manifest import PredictorInputs


def candidate():
    return PredictorInputs(
        sector="beleza",
        duration_seconds=12.0,
        aspect_ratio_height_over_width=16 / 9,
        text_status="extracted",
        text_embedding=tuple([0.1] * 384),
    )


def bundle(values=None):
    row = np.zeros(len(FEATURE_NAMES) + 1)
    row[-1], row[1], row[4], row[5] = 6, 0.5, 2, -0.5
    calls = []

    def shap(data, *, type, thread_count, verbose):
        calls.append((data, type, thread_count, verbose))
        return np.tile(row, (data.num_row(), 1)) if values is None else values

    return SimpleNamespace(
        artifact=SimpleNamespace(
            experiment="A_M1",
            artifact_sha256="a" * 64,
            feature_names=FEATURE_NAMES,
            categorical_indices=CATEGORICAL_INDICES,
            supported_text_statuses=("extracted",),
        ),
        models=(object(), SimpleNamespace(get_feature_importance=shap), object()),
        predict_logs=lambda inputs, repaired: np.tile([9.0, 8.0, 7.0], (len(inputs), 1)),
        calls=calls,
    )


def test_signed_speech_group_and_frozen_pool_reconstruct_raw_q50():
    b = bundle()
    result = explain_m1(b, [candidate(), candidate()])
    assert len(result) == 2
    first = result[0].model_dump(mode="json")
    assert first["scale"] == "log1p_views"
    assert first["quantile"] == 0.5
    assert first["prediction_log"] == 8.0
    assert first["base_value_log"] == 6.0
    assert {d["group"]: d["contribution_log"] for d in first["drivers"]} == {
        "sector": 0.0,
        "file_properties": 0.5,
        "text_status": 0.0,
        "speech_embedding": 1.5,
    }
    assert sum(d["contribution_log"] for d in first["drivers"]) == 2
    assert first["model_artifact_sha256"] == "a" * 64
    assert first["causal"] is False
    data, method, threads, verbose = b.calls[0]
    assert data.get_feature_names() == list(FEATURE_NAMES)
    assert data.get_cat_feature_indices() == list(CATEGORICAL_INDICES)
    assert method == "ShapValues" and threads == 2 and verbose is False
    assert "speech_minilm_" not in str(first)


@pytest.mark.parametrize(
    "values", [np.zeros((1, 388)), np.full((1, 389), np.nan), np.zeros((1, 389))]
)
def test_bad_shape_nonfinite_or_nonadditive_shap_is_rejected(values):
    with pytest.raises(ExperimentError):
        explain_m1(bundle(values), [candidate()])


def test_changed_feature_contract_is_rejected_before_native_shap():
    b = bundle()
    b.artifact.feature_names = tuple(reversed(FEATURE_NAMES))
    with pytest.raises(ExperimentError):
        explain_m1(b, [candidate()])
    assert not b.calls


@pytest.mark.parametrize("count", [0, 6])
def test_analysis_boundaries_are_checked_before_native_call(count):
    b = bundle()
    with pytest.raises(ExperimentError):
        explain_m1(b, [candidate()] * count)
    assert not b.calls


def test_unsupported_speech_is_not_explained():
    b = bundle()
    silent = PredictorInputs(
        sector="beleza",
        duration_seconds=12.0,
        aspect_ratio_height_over_width=16 / 9,
        text_status="no_audio_stream",
        text_embedding=None,
    )
    with pytest.raises(ExperimentError):
        explain_m1(b, [silent])
    assert not b.calls


def test_native_catboost_shap_matches_frozen_representation_on_synthetic_inputs():
    from catboost import CatBoostRegressor, Pool

    from scripts.experiment_a_data import feature_matrix

    values = [candidate().model_copy(update={"duration_seconds": float(i + 1)}) for i in range(20)]
    data = Pool(
        feature_matrix(values, supported_text_statuses=("extracted",)),
        label=np.log1p(np.arange(20) * 20 + 100),
        cat_features=list(CATEGORICAL_INDICES),
        feature_names=list(FEATURE_NAMES),
    )
    model = CatBoostRegressor(
        iterations=8,
        depth=2,
        loss_function="Quantile:alpha=0.5",
        thread_count=1,
        random_seed=42,
        verbose=False,
        allow_writing_files=False,
    )
    model.fit(data)
    toy = ExperimentBundle(artifact=bundle().artifact, models=(model, model, model))
    explanation = explain_m1(toy, values[:3])
    expected = toy.predict_logs(values[:3], repaired=False)[:, 1]
    assert np.allclose([e.prediction_log for e in explanation], expected)
    assert np.allclose(
        [e.base_value_log + sum(d.contribution_log for d in e.drivers) for e in explanation],
        expected,
    )
    assert all(len(e.drivers) == 4 for e in explanation)

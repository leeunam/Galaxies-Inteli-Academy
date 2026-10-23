"""Native C-cache tests on invented development inputs; no reserved data or API."""

from dataclasses import replace

import numpy as np
import pytest

from scripts.channel_partitions import ExperimentError
from scripts.experiment_b_data import CATEGORICAL_INDICES, FEATURE_NAMES
from scripts.train_experiment_c_cache import (
    encoded_matrix,
    fit_encoding,
    load_bundle,
    pairing,
    train_experiment,
)
from tests.test_experiment_b_data import b_fixture


@pytest.fixture(scope="module")
def trained(tmp_path_factory):
    data = b_fixture()
    directory = tmp_path_factory.mktemp("cache-model-parent") / "model"
    bundle, report = train_experiment(data, directory)
    return data, directory, bundle, report


def test_native_cache_training_reload_and_predictions_are_reproducible(trained):
    data, directory, bundle, report = trained
    loaded = load_bundle(directory, data=data)
    assert bundle.artifact.experiment == "C_CACHE_CLIP_AUDIO"
    assert bundle.artifact.vlm_used is False
    assert bundle.artifact.feature_names == FEATURE_NAMES
    assert bundle.artifact.categorical_indices == CATEGORICAL_INDICES
    assert len(bundle.artifact.trials) == 12 and len(bundle.models) == 3
    assert len(FEATURE_NAMES) == 905
    assert report["partition"] == "validation" and not report["final_test_evaluated"]
    assert report["data_kind"] == "synthetic" and not report["real_results_available"]
    actual = loaded.predict_logs(data.validation, repaired=False)
    assert np.array_equal(actual, bundle.predict_logs(data.validation, repaired=False))
    assert np.array_equal(actual, [r["raw_log_quantiles"] for r in report["validation_rows"]])
    assert bundle.artifact.training_sample_ids == data.base.train.sample_ids
    assert bundle.artifact.validation_sample_ids == data.base.validation.sample_ids


def test_changed_cached_input_is_rejected_before_native_model_load(trained, monkeypatch):
    data, directory, _, _ = trained
    changed = data.validation[0].model_copy(update={"brightness_mean_0_1": 0.7})
    altered = replace(data, validation=(changed, *data.validation[1:]))
    assert pairing(altered) != pairing(data)

    def forbidden(*args, **kwargs):
        pytest.fail("native model must not load with mismatched input content")

    monkeypatch.setattr("scripts.train_experiment_c_cache.lgb.Booster", forbidden)
    with pytest.raises(ExperimentError, match="c_cache_pairing_mismatch"):
        load_bundle(directory, data=altered)


def test_encoding_uses_training_categories_and_refuses_unsupported_values():
    data = b_fixture()
    encoding = fit_encoding(data)
    assert encoding.categories["sector"] == tuple(sorted({v.a.sector for v in data.train}))
    assert encoding.categories["audio_status"] == ("transcribed",)
    raw = encoding.model_dump()
    omitted = raw["categories"]["sector"][-1]
    raw["categories"]["sector"] = raw["categories"]["sector"][:-1]
    value = next(v for v in (*data.train, *data.validation) if v.a.sector == omitted)
    with pytest.raises(ExperimentError, match="c_cache_category_without_training_support"):
        encoded_matrix([value], raw)


def test_cache_variant_does_not_unlock_original_full_vlm_training(tmp_path, monkeypatch):
    from scripts.train_experiment_c_offline import train_experiment as full_train

    def forbidden(*args, **kwargs):
        pytest.fail("full VLM preparation must reject cache inputs before training")

    monkeypatch.setattr("scripts.train_experiment_c_offline.lgb.train", forbidden)
    with pytest.raises(ExperimentError, match="c_requires_full_b_vlm_data"):
        full_train(b_fixture(), tmp_path / "forbidden")

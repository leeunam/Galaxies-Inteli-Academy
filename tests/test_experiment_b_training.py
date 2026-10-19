import json
import shutil
from dataclasses import replace

import numpy as np
import pytest
from pydantic import ValidationError

from scripts.channel_partitions import ExperimentError, digest
from scripts.experiment_a_metrics import channel_weights
from scripts.experiment_b_artifact import load_bundle
from scripts.experiment_b_data import feature_matrix
from scripts.train_experiment_a import train_experiment as train_a
from scripts.train_experiment_b import compare, train_experiment
from tests.test_experiment_b_data import b_fixture


@pytest.fixture(scope="module")
def fitted(tmp_path_factory):
    data = b_fixture()
    folder = tmp_path_factory.mktemp("b-fit")
    trials = []
    b, report = train_experiment(data, folder / "b", progress=trials.append)
    a, _ = train_a(data.base, folder / "a")
    assert len(trials) == 12
    return data, folder / "b", b, a, report


def test_native_b_fit_reload_and_batch_parity(fitted):
    data, directory, b, _, report = fitted
    assert len(b.artifact.feature_names) == 905
    assert len(b.artifact.trials) == 12
    assert b.artifact.training_sample_ids == data.base.train.sample_ids
    assert b.artifact.validation_sample_ids == data.base.validation.sample_ids
    assert b.artifact.vlm_used is False and report["vlm_used"] is False
    assert b.artifact.final_test_evaluated is False
    loaded = load_bundle(directory, expected_extractor_config=data.base.extractor_config)
    raw = np.asarray([r["raw_log_quantiles"] for r in report["validation_rows"]])
    np.testing.assert_array_equal(raw, loaded.predict_logs(data.validation, repaired=False))
    np.testing.assert_array_equal(
        loaded.predict_views(data.validation[:1])[0], loaded.predict_views(data.validation)[0]
    )
    for name in ["artifact.json", "q10.cbm", "q50.cbm", "q90.cbm", "validation-report.json"]:
        assert (directory / name).stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize(
    "corruption", ["weights", "report", "features", "selection", "runtime", "source", "vlm"]
)
def test_b_incompatible_or_corrupt_bundles_are_refused(fitted, tmp_path, corruption):
    data, original, _, _, _ = fitted
    directory = tmp_path / "b"
    shutil.copytree(original, directory)
    if corruption in {"weights", "report"}:
        path = directory / ("q50.cbm" if corruption == "weights" else "validation-report.json")
        path.write_bytes(path.read_bytes() + b" ")
    else:
        path = directory / "artifact.json"
        body = json.loads(path.read_bytes())
        if corruption == "features":
            body["feature_names"][4] = "view_count"
        elif corruption == "selection":
            chosen = body["selected"][0]
            body["selected"][0] = next(
                t for t in body["trials"] if t["quantile"] == 0.1 and t != chosen
            )
        elif corruption == "runtime":
            body["runtime_versions"]["catboost"] = "0.0.0"
        elif corruption == "source":
            body["source_files_sha256"]["experiment_b_data.py"] = "0" * 64
        else:
            body["vlm_used"] = True
        body["artifact_sha256"] = digest({k: v for k, v in body.items() if k != "artifact_sha256"})
        path.write_text(json.dumps(body))
    with pytest.raises((ValidationError, ExperimentError)):
        load_bundle(directory, expected_extractor_config=data.base.extractor_config)


def test_expected_cohort_and_partition_are_enforced(fitted):
    data, directory, _, _, _ = fitted
    for change in [
        {"expected_cohort_sha256": "0" * 64},
        {"expected_partition_sha256": "0" * 64},
        {"expected_extractor_config": {}},
    ]:
        with pytest.raises(ExperimentError):
            load_bundle(
                directory, **({"expected_extractor_config": data.base.extractor_config} | change)
            )


def test_comparison_is_paired_and_refuses_changed_training_targets(fitted):
    data, _, b, a, _ = fitted
    report = compare(data, data.base, b, a, a)
    assert report["test_evaluated"] is False
    assert report["vlm_used"] is False
    assert report["groups"]["new_validation"]["status"] == "not_estimable"
    all_rows = report["groups"]["all_validation"]
    assert set(all_rows["models"]) == {"A200", "A300", "B_cache_300", "B0_300"}
    assert all_rows["models"]["B_cache_300"]["metrics"]["samples"] == len(data.validation)
    altered = replace(data.base, cohort_sha256="b" * 64)
    with pytest.raises(ExperimentError, match="comparison_a_split_mismatch"):
        compare(replace(data, base=altered), data.base, b, a, a)


def test_no_overwrite_and_a_inputs_cannot_be_used_in_b(fitted):
    data, directory, b, _, _ = fitted
    with pytest.raises(ExperimentError, match="output_already_exists"):
        train_experiment(data, directory)
    with pytest.raises(ValidationError):
        b.predict_logs(data.base.validation.inputs)


def test_every_fit_gets_only_train_labels_and_macro_channel_validation(tmp_path, monkeypatch):
    import scripts.train_experiment_b as module

    data = b_fixture()
    original = module.CatBoostRegressor
    calls = []

    class Recorder(original):
        def fit(self, train, **kwargs):
            calls.append((train.get_label(), kwargs["eval_set"].get_weight(), self.get_params()))
            assert train.num_col() == len(feature_matrix(data.train)[0]) == 905
            return super().fit(train, **kwargs)

    monkeypatch.setattr(module, "CatBoostRegressor", Recorder)
    train_experiment(data, tmp_path / "recorded")
    assert len(calls) == 12
    for labels, weights, params in calls:
        np.testing.assert_allclose(
            labels, np.log1p([t.view_count for t in data.base.train.targets])
        )
        np.testing.assert_allclose(weights, channel_weights(data.base.validation.channel_ids))
        assert params["thread_count"] == 2 and params["random_seed"] == 42

import json
import shutil
from dataclasses import replace

import numpy as np
import pytest
from pydantic import ValidationError

from scripts.channel_partitions import ExperimentError, digest
from scripts.experiment_a_metrics import channel_weights
from scripts.experiment_b_vlm_artifact import load_bundle
from scripts.train_experiment_a import train_experiment as train_a
from scripts.train_experiment_b import compare as compare_cached
from scripts.train_experiment_b import train_experiment as train_cached
from scripts.train_experiment_b_vlm import compare, train_experiment
from tests.test_experiment_b_vlm_data import vlm_fixture


@pytest.fixture(scope="module")
def fitted(tmp_path_factory):
    import scripts.train_experiment_b_vlm as module

    data = vlm_fixture()
    folder = tmp_path_factory.mktemp("b-vlm-fit")
    original = module.CatBoostRegressor
    calls = []

    class Recorder(original):
        def fit(self, train, **kwargs):
            assert train.num_col() == 910
            calls.append((train.get_label(), kwargs["eval_set"].get_weight(), self.get_params()))
            return super().fit(train, **kwargs)

    module.CatBoostRegressor = Recorder
    try:
        full, report = train_experiment(data, folder / "full")
    finally:
        module.CatBoostRegressor = original
    cached, _ = train_cached(data.cached, folder / "cached")
    a, _ = train_a(data.base, folder / "a")
    return data, folder, full, cached, a, report, calls


def load(directory, data, **changes):
    args = {
        "expected_extractor_config": data.base.extractor_config,
        "expected_vlm_config": data.vlm_config,
        "expected_quality_release_sha256": data.release.release_sha256,
        "expected_cohort_sha256": data.base.cohort_sha256,
        "expected_partition_sha256": data.base.manifest.manifest_sha256,
    } | changes
    return load_bundle(directory, **args)


def test_native_full_fit_reload_real_parity_and_training_boundary(fitted):
    data, folder, full, _, _, report, calls = fitted
    assert len(calls) == len(full.artifact.trials) == 12
    assert full.artifact.vlm_used is True
    assert full.artifact.final_test_evaluated is False
    assert full.artifact.quality_release == data.release
    assert full.artifact.training_sample_ids == data.base.train.sample_ids
    for labels, weights, params in calls:
        np.testing.assert_allclose(
            labels, np.log1p([t.view_count for t in data.base.train.targets])
        )
        np.testing.assert_allclose(weights, channel_weights(data.base.validation.channel_ids))
        assert params["thread_count"] == 2 and params["random_seed"] == 42
    raw = np.asarray([row["raw_log_quantiles"] for row in report["validation_rows"]])
    reloaded = load(folder / "full", data)
    np.testing.assert_array_equal(raw, reloaded.predict_logs(data.validation, repaired=False))
    np.testing.assert_array_equal(
        reloaded.predict_views(data.validation[:1])[0], reloaded.predict_views(data.validation)[0]
    )
    for path in (folder / "full").iterdir():
        assert path.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize(
    "corruption", ["weights", "report", "quality", "fields", "runtime", "source", "vlm"]
)
def test_incompatible_or_corrupted_full_bundle_is_refused(fitted, tmp_path, corruption):
    data, folder, *_ = fitted
    directory = tmp_path / "full"
    shutil.copytree(folder / "full", directory)
    if corruption in {"weights", "report"}:
        path = directory / ("q50.cbm" if corruption == "weights" else "validation-report.json")
        path.write_bytes(path.read_bytes() + b" ")
    else:
        path = directory / "artifact.json"
        body = json.loads(path.read_bytes())
        if corruption == "quality":
            body["quality_release"]["released_fields"] = ["demonstration"]
        elif corruption == "fields":
            body["feature_names"][905] = "views"
        elif corruption == "runtime":
            body["runtime_versions"]["catboost"] = "0.0"
        elif corruption == "source":
            body["source_files_sha256"]["experiment_b_vlm_quality.py"] = "0" * 64
        else:
            body["vlm_used"] = False
        body["artifact_sha256"] = digest({k: v for k, v in body.items() if k != "artifact_sha256"})
        path.write_text(json.dumps(body))
    with pytest.raises((ValidationError, ExperimentError)):
        load(directory, data)


def test_expected_vlm_configuration_and_quality_release_are_required(fitted):
    data, folder, *_ = fitted
    for change in (
        {"expected_vlm_config": {}},
        {"expected_quality_release_sha256": "0" * 64},
        {"expected_partition_sha256": "0" * 64},
        {"expected_cohort_sha256": "0" * 64},
    ):
        with pytest.raises(ExperimentError):
            load(folder / "full", data, **change)


def test_comparison_preserves_all_frozen_comparator_metrics(fitted):
    data, _, full, cached, a, _, _ = fitted
    previous = compare_cached(data.cached, data.base, cached, a, a)
    report = compare(data, data.base, full, cached, a, a)
    assert report["test_evaluated"] is False and report["vlm_used"] is True
    assert report["unchanged_b_cache_prefix_columns"] == 905
    for name, group in previous["groups"].items():
        if group.get("status") == "not_estimable":
            assert report["groups"][name] == group
        else:
            for model, value in group["models"].items():
                assert report["groups"][name]["models"][model] == value
    assert report["groups"]["all_validation"]["models"]["B_VLM_300"]["metrics"]["samples"] == len(
        data.validation
    )


def test_no_overwrite_no_a_or_cached_inputs_and_changed_release_cannot_be_compared(fitted):
    data, folder, full, cached, a, _, _ = fitted
    with pytest.raises(ExperimentError, match="output_already_exists"):
        train_experiment(data, folder / "full")
    with pytest.raises(ValidationError):
        full.predict_logs(data.cached.validation)
    changed = replace(data, vlm_config={"different": True})
    with pytest.raises(ExperimentError, match="comparison_vlm"):
        compare(changed, data.base, full, cached, a, a)

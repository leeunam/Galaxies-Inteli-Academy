import hashlib
import json
from dataclasses import replace

import numpy as np
import pytest
from pydantic import ValidationError

from scripts.channel_partitions import ExperimentError, digest
from scripts.experiment_a_artifact import ExperimentArtifact, load_bundle
from scripts.experiment_a_metrics import (
    channel_weights,
    evaluate_development,
    repair_quantiles,
    selection_score,
    views_from_logs,
)
from scripts.train_experiment_a import learning_example, train_experiment
from tests.test_experiment_a_data import development_fixture


def test_crossing_repair_preserves_q50_and_uses_all_three_raw_values():
    raw = np.array([[8.0, 3.0, 1.0], [2.0, 4.0, 3.0], [1.0, 2.0, 3.0]])
    repaired = repair_quantiles(raw)
    np.testing.assert_array_equal(repaired, [[1, 3, 8], [2, 4, 4], [1, 2, 3]])
    np.testing.assert_array_equal(repaired[:, 1], raw[:, 1])
    np.testing.assert_allclose(views_from_logs(np.log1p([[0, 999, 9999]])), [[0, 999, 9999]])


@pytest.mark.parametrize(
    "raw",
    [[[1, float("nan"), 3]], [[1, float("inf"), 3]], [[1, -1, 3]], [[1, 1000, 3]], [], [[1, 2]]],
)
def test_nonphysical_or_nonfinite_predictions_are_not_served(raw):
    with pytest.raises(ExperimentError):
        repair_quantiles(raw)


def test_selection_gives_each_channel_equal_weight_not_each_video():
    labels, predictions, channels = (
        np.array([10, 10, 10, 0]),
        np.array([9, 9, 9, 10]),
        ("a", "a", "a", "b"),
    )
    assert selection_score(labels, predictions, channels, 0.5) == pytest.approx(5.5)
    assert selection_score(labels, predictions, channels, 0.1) == pytest.approx(4.55)
    np.testing.assert_allclose(channel_weights(channels), [1 / 3, 1 / 3, 1 / 3, 1])


def test_metrics_evaluate_the_repaired_interval_and_handle_zero_and_ranking_support():
    split = development_fixture().validation
    targets = tuple(
        t.model_copy(update={"view_count": 0 if i == 0 else 100})
        for i, t in enumerate(split.targets)
    )
    split = split.model_copy(update={"targets": targets})
    raw = np.array([[8.0, 4.0, 0.0]] * len(split.targets))
    result = evaluate_development(split, raw)
    assert result["coverage_micro"] == 1
    assert result["crossing_rows_raw"] == len(split.targets)
    assert result["mape_excluded_zero_views"] == 1
    assert result["spearman_macro_channel"] is None
    assert result["pair_accuracy_macro_channel"] == 0.5
    assert result["mean_width_views"] == pytest.approx(np.expm1(8))


@pytest.fixture(scope="module")
def fitted(tmp_path_factory):
    data = development_fixture()
    directory = tmp_path_factory.mktemp("experiment-a") / "bundle"
    progress = []
    bundle, report = train_experiment(data, directory, progress=progress.append)
    assert len(progress) == 12
    return data, directory, bundle, report


def test_actual_cpu_search_persists_exact_grid_and_reload_parity(fitted):
    data, directory, bundle, report = fitted
    artifact = bundle.artifact
    assert len(artifact.trials) == 12
    assert {(t.depth, t.l2_leaf_reg) for t in artifact.trials} == {(4, 3), (4, 10), (6, 3), (6, 10)}
    assert not artifact.final_test_evaluated
    assert not artifact.predictive_quality_validated
    assert artifact.training_sample_ids == data.train.sample_ids
    assert artifact.validation_sample_ids == data.validation.sample_ids
    assert artifact.train_split_sha256 != artifact.validation_split_sha256
    assert artifact.supported_text_statuses == ("extracted",)
    assert report["metrics"]["B0"] == report["metrics"]["Bcanal"]
    assert set(report["metrics"]) == {"A_M1", "B0", "Bcanal"}
    assert (directory / "artifact.json").stat().st_mode & 0o777 == 0o600
    for name in artifact.model_sha256:
        assert (directory / name).stat().st_mode & 0o777 == 0o600
    reloaded = load_bundle(
        directory,
        expected_extractor_config=data.extractor_config,
        expected_partition_sha256=data.manifest.manifest_sha256,
    )
    np.testing.assert_array_equal(
        bundle.predict_views(data.validation.inputs), reloaded.predict_views(data.validation.inputs)
    )
    # Individual predictions do not depend on other candidates in the batch.
    np.testing.assert_array_equal(
        bundle.predict_views(data.validation.inputs[:1])[0],
        bundle.predict_views(data.validation.inputs)[0],
    )


def test_model_reload_rejects_wrong_extractor_partition_or_cohort(fitted):
    data, directory, _, _ = fitted
    for changes in (
        {"expected_extractor_config": {}},
        {"expected_partition_sha256": "0" * 64},
        {"expected_cohort_sha256": "0" * 64},
    ):
        with pytest.raises(ExperimentError, match="incompatible_experiment_artifact"):
            load_bundle(
                directory, **({"expected_extractor_config": data.extractor_config} | changes)
            )


@pytest.mark.parametrize(
    "failure", ["model", "report", "feature_names", "selected", "runtime", "source"]
)
def test_corrupt_or_incompatible_bundle_is_rejected(fitted, tmp_path, failure):
    import shutil

    data, original, _, _ = fitted
    directory = tmp_path / "bundle"
    shutil.copytree(original, directory)
    if failure in ("model", "report"):
        path = directory / ("q50.cbm" if failure == "model" else "validation-report.json")
        path.write_bytes(path.read_bytes() + b" ")
    else:
        path = directory / "artifact.json"
        payload = json.loads(path.read_bytes())
        if failure == "feature_names":
            payload["feature_names"][0] = "channel_id"
        elif failure == "selected":
            q = payload["selected"][0]["quantile"]
            payload["selected"][0] = next(
                t for t in payload["trials"] if t["quantile"] == q and t != payload["selected"][0]
            )
        elif failure == "runtime":
            payload["runtime_versions"]["catboost"] = "0.0.0"
        else:
            payload["source_files_sha256"]["experiment_a_data.py"] = "0" * 64
        payload["artifact_sha256"] = digest(
            {k: v for k, v in payload.items() if k != "artifact_sha256"}
        )
        path.write_text(json.dumps(payload))
    with pytest.raises((ExperimentError, ValidationError)):
        load_bundle(directory, expected_extractor_config=data.extractor_config)


def test_cannot_silently_accept_unseen_missing_text_or_overwrite_bundle(fitted):
    data, directory, bundle, _ = fitted
    missing = data.validation.inputs[0].model_copy(
        update={"text_status": "no_audio_stream", "text_embedding": None}
    )
    with pytest.raises(ExperimentError, match="unsupported_text_status"):
        bundle.predict_views([missing])
    with pytest.raises(ExperimentError, match="output_already_exists"):
        train_experiment(data, directory)


def test_all_fits_use_only_training_labels_and_weighted_validation(tmp_path, monkeypatch):
    import scripts.train_experiment_a as module

    original = module.CatBoostRegressor
    data = development_fixture()
    fits = []

    class RecordingRegressor(original):
        def fit(self, train, **kwargs):
            validation = kwargs["eval_set"]
            fits.append(
                (
                    train.get_label(),
                    validation.get_label(),
                    validation.get_weight(),
                    self.get_params(),
                )
            )
            return super().fit(train, **kwargs)

    monkeypatch.setattr(module, "CatBoostRegressor", RecordingRegressor)
    # Arbitrarily large validation counts cannot become training targets or baseline statistics.
    data = replace(
        data,
        validation=data.validation.model_copy(
            update={
                "targets": tuple(
                    t.model_copy(update={"view_count": 10**8 + i})
                    for i, t in enumerate(data.validation.targets)
                )
            }
        ),
    )
    train_experiment(data, tmp_path / "fit-boundary")
    assert len(fits) == 12
    for labels, validation, weights, params in fits:
        np.testing.assert_allclose(labels, np.log1p([t.view_count for t in data.train.targets]))
        np.testing.assert_allclose(
            validation, np.log1p([t.view_count for t in data.validation.targets])
        )
        np.testing.assert_allclose(weights, channel_weights(data.validation.channel_ids))
        assert params["iterations"] == 500
        assert params["task_type"] == "CPU"
        assert params["random_seed"] == 42


def test_learning_example_never_exposes_test_rows():
    result = learning_example(development_fixture())
    assert set(result["examples"]) == {"train", "validation"}
    assert not result["test_matrix_created"]
    assert result["columns"] == 388


def test_artifact_hash_detects_changed_protocol(fitted):
    _, _, bundle, _ = fitted
    payload = bundle.artifact.model_dump(mode="json")
    payload["protocol"]["iterations"] = 501
    payload["artifact_sha256"] = digest(
        {k: v for k, v in payload.items() if k != "artifact_sha256"}
    )
    with pytest.raises(ValidationError):
        ExperimentArtifact.model_validate_json(json.dumps(payload))
    assert hashlib.sha256(b"model").hexdigest() != bundle.artifact.model_sha256["q50.cbm"]


def test_cli_suppresses_native_exceptions_and_private_paths(monkeypatch, capsys, tmp_path):
    import scripts.train_experiment_a as module

    monkeypatch.setattr(
        "sys.argv",
        ["train_experiment_a", "--cohort-dir", "private", "--output-dir", str(tmp_path / "output")],
    )
    monkeypatch.setattr(module, "load_development_data", lambda *a, **k: development_fixture())

    def fail(*args, **kwargs):
        raise module.CatBoostError("private-path-and-transcript")

    monkeypatch.setattr(module, "train_experiment", fail)
    assert module.main() == 1
    captured = capsys.readouterr()
    assert not captured.out
    assert json.loads(captured.err) == {"status": "error", "code": "experiment_a_failed"}

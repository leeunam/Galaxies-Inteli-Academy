"""Invented inputs only; no corpus/model paths, media, network or VLM calls."""

import hashlib
import json
import shutil
from dataclasses import replace
from importlib.metadata import version
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from pydantic import ValidationError

from scripts.channel_partitions import ExperimentError, digest
from scripts.experiment_a_metrics import channel_weights, selection_score
from scripts.experiment_b_vlm_artifact import ExperimentArtifact as BArtifact
from scripts.experiment_b_vlm_artifact import SearchProtocol as BProtocol
from scripts.experiment_b_vlm_artifact import Trial as BTrial
from scripts.experiment_b_vlm_artifact import source_hashes as b_source_hashes
from scripts.experiment_b_vlm_data import categorical_indices, feature_matrix, feature_names
from scripts.experiment_c_full_data import assert_pairing, fit_encoding, pairing, validate_full_data
from scripts.train_experiment_c_full import (
    compare,
    load_bundle,
    model_params,
    train_experiment,
)
from tests.test_experiment_b_vlm_data import vlm_fixture


def observed_marker(data):
    # An invalid manifest is sufficient: the offline boundary must stop before
    # it parses or inspects anything inside a would-be real dataset.
    manifest = data.base.manifest.model_copy(update={"data_kind": "observed_pilot"})
    return replace(data, cached=replace(data.cached, base=replace(data.base, manifest=manifest)))


def test_c_uses_the_exact_b_columns_and_train_only_lossless_category_codes():
    data = vlm_fixture()
    encoder = fit_encoding(data)
    assert encoder.feature_names == feature_names(data.release)
    assert encoder.categorical_indices == categorical_indices(data.release)
    original = feature_matrix(data.validation, data.release)
    numeric = encoder.transform(data.validation, data.release)
    assert numeric.shape == (len(data.validation), 910)
    for i, row in enumerate(original):
        for j, value in enumerate(row):
            if j in encoder.categorical_indices:
                assert encoder.categories[encoder.feature_names[j]][int(numeric[i, j])] == value
            else:
                assert numeric[i, j] == value
    assert "unknown" in encoder.categories["vlm_screen_text"]
    assert not {"view_count", "sample_id", "channel_id"} & set(encoder.feature_names)


def test_validation_only_categories_cannot_expand_the_training_vocabulary():
    data = vlm_fixture()
    training = tuple(
        v.model_copy(update={"attributes": v.attributes | {"screen_text": "false"}})
        for v in data.train
    )
    changed = replace(data, train=training)
    encoder = fit_encoding(changed)
    assert encoder.categories["vlm_screen_text"] == ("false",)
    with pytest.raises(ExperimentError, match="without_training_support"):
        encoder.transform(data.validation, data.release)
    assert encoder == fit_encoding(changed)


def test_cache_only_and_unproven_observed_data_stop_before_targets_or_output(tmp_path, monkeypatch):
    import scripts.experiment_c_full_data as module

    data = vlm_fixture()
    real = observed_marker(data)
    monkeypatch.setattr(module, "validate_data", lambda *_: pytest.fail("read beyond boundary"))
    with pytest.raises(ExperimentError, match="requires_released_b"):
        validate_full_data(data.cached)
    for call in (
        lambda: fit_encoding(real),
        lambda: train_experiment(real, tmp_path / "new-model"),
        lambda: load_bundle(tmp_path / "does-not-exist", data=real),
        lambda: compare(real, None, None),
    ):
        with pytest.raises(ExperimentError, match="observed_extraction_provenance"):
            call()
    with pytest.raises(ExperimentError, match="269_rows"):
        validate_full_data(replace(real, vlm_config={"synthetic": False}))
    assert not list(tmp_path.iterdir())


def test_no_fake_extraction_no_failed_release_no_reordered_rows():
    data = vlm_fixture()
    with pytest.raises(ExperimentError, match="data_kind_mismatch"):
        validate_full_data(replace(data, vlm_config={}))
    with pytest.raises(ExperimentError, match="alignment"):
        fit_encoding(replace(data, train=data.train[::-1]))
    raw = data.release.model_dump()
    raw["columns"]["screen_text"]["sectors"]["moda"]["correct_value_and_evidence"] = 0
    raw["release_sha256"] = digest({k: v for k, v in raw.items() if k != "release_sha256"})
    with pytest.raises((ExperimentError, ValidationError)):
        fit_encoding(replace(data, release=data.release.model_copy(update=raw)))


def test_b_training_refuses_failed_visual_release_before_constructing_a_pool(tmp_path, monkeypatch):
    import scripts.train_experiment_b_vlm as module

    data = vlm_fixture()
    invalid = data.release.model_copy(update={"release_sha256": "0" * 64})
    monkeypatch.setattr(module, "Pool", lambda *_a, **_kw: pytest.fail("a pool was constructed"))
    with pytest.raises((ExperimentError, ValidationError)):
        module.train_experiment(replace(data, release=invalid), tmp_path / "never-created")
    assert not list(tmp_path.iterdir())


@pytest.fixture(scope="module")
def fitted(tmp_path_factory):
    import scripts.train_experiment_c_full as module

    data = vlm_fixture()
    directory = tmp_path_factory.mktemp("c-invented") / "model"
    original = module.lgb.train
    calls = []

    def recorder(params, train, **kwargs):
        # Observe the exact split and callback contract, then run native LightGBM.
        np.testing.assert_array_equal(
            train.data, fit_encoding(data).transform(data.train, data.release)
        )
        expected_labels = np.log1p([t.view_count for t in data.base.train.targets])
        # Reused Dataset labels are converted in place to float32 by LightGBM.
        np.testing.assert_array_equal(train.label, expected_labels.astype(train.label.dtype))
        assert train.weight is None
        validation = kwargs["valid_sets"][0]
        np.testing.assert_array_equal(
            validation.data, fit_encoding(data).transform(data.validation, data.release)
        )
        np.testing.assert_allclose(
            validation.weight, channel_weights(data.base.validation.channel_ids), atol=1e-7
        )
        assert params["num_threads"] == 1
        assert params["metric"] == "None" and callable(kwargs["feval"])
        predictions = np.linspace(1, 3, len(data.validation))
        name, score, maximize = kwargs["feval"](predictions, validation)
        expected = selection_score(
            np.log1p([t.view_count for t in data.base.validation.targets]),
            predictions,
            data.base.validation.channel_ids,
            params["alpha"],
        )
        assert name == "macro_channel_selection" and maximize is False
        assert score == expected
        calls.append(params.copy())
        return original(params, train, **kwargs)

    module.lgb.train = recorder
    try:
        bundle, report = train_experiment(data, directory)
    finally:
        module.lgb.train = original
    return data, directory, bundle, report, calls


def test_twelve_native_fits_use_approved_recipe_reload_exactly_and_preserve_q50(fitted):
    data, directory, c, report, calls = fitted
    assert len(calls) == len(c.artifact.trials) == 12
    assert {(p["alpha"], p["num_leaves"], p["min_data_in_leaf"]) for p in calls} == {
        (q, n, m) for q in (0.1, 0.5, 0.9) for n in (7, 15) for m in (5, 20)
    }
    assert all(p == model_params(p["alpha"], p["num_leaves"], p["min_data_in_leaf"]) for p in calls)
    assert c.artifact.final_test_evaluated is False
    assert report["real_results_available"] is False
    assert c.artifact.run_scope == "development_train_validation_only"
    raw = np.asarray([r["raw_log_quantiles"] for r in report["validation_rows"]])
    reloaded = load_bundle(directory, data=data)
    np.testing.assert_array_equal(raw, reloaded.predict_logs(data.validation, repaired=False))
    np.testing.assert_array_equal(raw[:, 1], reloaded.predict_logs(data.validation)[:, 1])
    np.testing.assert_array_equal(
        c.predict_views(data.validation[:1])[0], c.predict_views(data.validation)[0]
    )
    assert directory.stat().st_mode & 0o777 == 0o700
    assert all(p.stat().st_mode & 0o777 == 0o600 for p in directory.iterdir())
    with pytest.raises(ExperimentError, match="output_already_exists"):
        train_experiment(data, directory)


@pytest.mark.parametrize(
    "corruption", ["weights", "report", "encoding", "runtime", "source", "native_params"]
)
def test_native_artifacts_refuse_corruption_before_predicting(fitted, tmp_path, corruption):
    data, original, *_ = fitted
    directory = tmp_path / "bad"
    shutil.copytree(original, directory)
    if corruption in {"weights", "report"}:
        path = directory / ("q50.txt" if corruption == "weights" else "validation-report.json")
        path.write_bytes(path.read_bytes() + b" ")
    else:
        path = directory / "artifact.json"
        body = json.loads(path.read_bytes())
        if corruption == "native_params":
            model_path = directory / "q50.txt"
            raw_model = model_path.read_text()
            assert "[lambda_l2: 3]" in raw_model
            model_path.write_text(raw_model.replace("[lambda_l2: 3]", "[lambda_l2: 4]"))
            body["model_sha256"]["q50.txt"] = hashlib.sha256(model_path.read_bytes()).hexdigest()
        elif corruption == "encoding":
            body["encoding"]["categories"]["vlm_screen_text"] = ["false", "true", "unknown"]
        elif corruption == "runtime":
            body["runtime_versions"]["lightgbm"] = "0.0"
        else:
            body["source_files_sha256"]["experiment_c_data.py"] = "0" * 64
        body["artifact_sha256"] = digest({k: v for k, v in body.items() if k != "artifact_sha256"})
        path.write_text(json.dumps(body))
    with pytest.raises((ExperimentError, ValidationError)):
        load_bundle(directory, data=data)


def synthetic_b_contract(data):
    """A mock B contract, explicitly invented; never persisted as a trained model."""
    trials = tuple(
        BTrial(
            quantile=q,
            depth=d,
            l2_leaf_reg=l2,
            best_iteration=0,
            tree_count=1,
            evaluated_iterations=1,
            validation_score=1.0,
            elapsed_seconds=0.0,
        )
        for q in (0.1, 0.5, 0.9)
        for d in (4, 6)
        for l2 in (3, 10)
    )
    body = pairing(data) | {
        "quality_release": data.release,
        "feature_names": feature_names(data.release),
        "categorical_indices": categorical_indices(data.release),
        "data_kind": "synthetic",
        "supported_text_statuses": ("extracted",),
        "extractor_config_sha256": digest(data.base.extractor_config),
        "vlm_config_sha256": digest(data.vlm_config),
        "runtime_versions": {name: version(name) for name in ("catboost", "numpy")},
        "source_files_sha256": b_source_hashes(),
        "uv_lock_sha256": hashlib.sha256(Path("uv.lock").read_bytes()).hexdigest(),
        "protocol": BProtocol(),
        "trials": trials,
        "selected": tuple(t for t in trials if t.depth == 4 and t.l2_leaf_reg == 3),
        "model_sha256": {name: "b" * 64 for name in ("q10.cbm", "q50.cbm", "q90.cbm")},
        "validation_report_sha256": "c" * 64,
    }
    body = BArtifact.model_construct(**body, artifact_sha256="0" * 64).model_dump(
        exclude={"artifact_sha256"}
    )
    return BArtifact.model_validate_json(json.dumps(body | {"artifact_sha256": digest(body)}))


def test_paired_comparison_requires_full_b_same_features_labels_and_partitions(fitted):
    data, _, c, *_ = fitted
    b = SimpleNamespace(
        artifact=synthetic_b_contract(data),
        predict_logs=lambda inputs, **kw: c.predict_logs(inputs, **kw),
    )
    report = compare(data, b, c)
    assert report["data_kind"] == "synthetic" and report["real_results_available"] is False
    assert report["final_test_evaluated"] is False
    assert report["models"]["B_FULL_VLM"] == report["models"]["C_FULL_VLM"]
    assert report["pairing_sha256"] == digest(pairing(data))
    original = data.base.validation.sample_ids[:6]
    grouped = compare(data, b, c, original_validation_ids=original)
    assert grouped["groups"]["original_validation"]["samples"] == 6
    assert grouped["groups"]["new_validation"]["samples"] == len(data.validation) - 6
    assert (
        grouped["groups"]["all_validation"]["models"]["B_FULL_VLM"]["metrics"]
        == report["models"]["B_FULL_VLM"]
    )
    with pytest.raises(ExperimentError, match="original_validation_ids"):
        compare(data, b, c, original_validation_ids={"not-a-validation-id"})
    for change in (
        {"train_split_sha256": "0" * 64},
        {"validation_split_sha256": "0" * 64},
        {"cohort_sha256": "0" * 64},
        {"partition_manifest_sha256": "0" * 64},
        {"quality_release": data.release.model_copy(update={"plan_sha256": "0" * 64})},
    ):
        with pytest.raises((ExperimentError, ValidationError)):
            assert_pairing(data, b.artifact.model_copy(update=change))
    with pytest.raises(ExperimentError, match="bc_full_pairing"):
        compare(
            data,
            b,
            replace(
                c,
                artifact=c.artifact.model_copy(
                    update={
                        "cohort_sha256": "0" * 64,
                        "artifact_sha256": digest(
                            c.artifact.model_dump(exclude={"artifact_sha256"})
                            | {
                                "cohort_sha256": "0" * 64,
                            }
                        ),
                    }
                ),
            ),
        )


def test_changed_inputs_and_labels_break_pairing_before_prediction(fitted):
    data, _, c, *_ = fitted
    changed = replace(data, vlm_config={"synthetic": True, "different": True})
    with pytest.raises(ExperimentError, match="pairing"):
        assert_pairing(changed, c.artifact)
    first = data.validation[0]
    inputs = (
        first.model_copy(
            update={
                "attributes": first.attributes | {"screen_text": "false"},
            }
        ),
        *data.validation[1:],
    )
    with pytest.raises(ExperimentError, match="pairing"):
        assert_pairing(replace(data, validation=inputs), c.artifact)
    target = data.base.validation.targets[0]
    split = data.base.validation.model_copy(
        update={
            "targets": (
                target.model_copy(update={"view_count": target.view_count + 1}),
                *data.base.validation.targets[1:],
            )
        }
    )
    cached = replace(data.cached, base=replace(data.base, validation=split))
    with pytest.raises(ExperimentError, match="pairing"):
        assert_pairing(replace(data, cached=cached), c.artifact)


def test_cache_schema_and_changed_source_stop_comparison_before_prediction(fitted):
    data, _, c, *_ = fitted
    calls = []
    contract = synthetic_b_contract(data)

    def never_predict(*args, **kwargs):
        calls.append(True)
        pytest.fail("prediction preceded artifact validation")

    raw = contract.model_dump()
    raw["source_files_sha256"]["train_experiment_b_vlm.py"] = "0" * 64
    raw["artifact_sha256"] = digest({k: v for k, v in raw.items() if k != "artifact_sha256"})
    with pytest.raises(ExperimentError, match="incompatible_bc"):
        compare(
            data,
            SimpleNamespace(
                artifact=BArtifact.model_validate_json(json.dumps(raw)),
                predict_logs=never_predict,
            ),
            c,
        )
    cache = contract.model_copy(update={"experiment": "B_CACHE", "vlm_used": False})
    with pytest.raises((ExperimentError, ValidationError)):
        compare(data, SimpleNamespace(artifact=cache, predict_logs=never_predict), c)
    assert not calls


def test_native_full_b_c_shap_pairing_and_reload_on_invented_inputs(fitted, tmp_path):
    from scripts.full_model_evidence import explain_full, feature_groups
    from scripts.train_experiment_b_vlm import train_experiment as train_b

    data, _, c, *_ = fitted
    b, _ = train_b(data, tmp_path / "b-invented")
    report = compare(data, b, c)
    assert set(report["models"]) == {"B_FULL_VLM", "C_FULL_VLM"}
    assert not report["real_results_available"]
    indices = [i for _, members in feature_groups(data.release) for i in members]
    assert sorted(indices) == list(range(len(feature_names(data.release))))
    for bundle in (b, c):
        explained = explain_full(bundle, data.validation[:3])
        assert len(explained) == 3
        assert max(row["absolute_reconstruction_error"] for row in explained) < 1e-7
        assert all(
            row["quality_release_sha256"] == data.release.release_sha256 for row in explained
        )
        assert all(row["causal"] is False for row in explained)
        assert explain_full(bundle, data.validation[:1])[0] == explained[0]
        with pytest.raises(ExperimentError, match="one_to_five"):
            explain_full(bundle, data.validation[:6])

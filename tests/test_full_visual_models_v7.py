from __future__ import annotations

import numpy as np
import pytest

from scripts.channel_partitions import ExperimentError
from scripts.full_visual_artifact_v7 import sha
from scripts.full_visual_models_v7 import (
    CATEGORICAL_INDICES,
    FEATURE_NAMES,
    RecordingBackend,
    _encode_c,
    _fit_c_encoding,
    compare,
    load_bundle,
    train_experiment,
)
from tests.test_full_visual_data_v7 import _fixture, _load


@pytest.fixture(autouse=True)
def trap_native_construction(monkeypatch):
    import catboost
    import lightgbm

    def fail(*_a, **_kw):
        raise AssertionError("native model use forbidden in light tests")

    monkeypatch.setattr(catboost, "Pool", fail)
    monkeypatch.setattr(catboost, "CatBoostRegressor", fail)
    monkeypatch.setattr(lightgbm, "Dataset", fail)
    monkeypatch.setattr(lightgbm, "train", fail)
    monkeypatch.setattr(lightgbm, "Booster", fail)


@pytest.mark.parametrize(
    "algorithm,grid_keys",
    [("B", ("depth", "l2_leaf_reg")), ("C", ("num_leaves", "min_data_in_leaf"))],
)
def test_exact_frozen_grid_and_recording_roundtrip(tmp_path, algorithm, grid_keys):
    fixture = _fixture(tmp_path / "source")
    data, _ = _load(fixture)
    out = tmp_path / "model"
    backend = RecordingBackend()
    bundle, report = train_experiment(data, out, algorithm=algorithm, backend=backend)
    assert len(report["trials"]) == 12
    assert len(report["selected"]) == 3
    assert {r["quantile"] for r in report["trials"]} == {0.1, 0.5, 0.9}
    assert len({(r["quantile"], r[grid_keys[0]], r[grid_keys[1]]) for r in report["trials"]}) == 12
    assert len(backend.calls) == 12
    assert all(call["training_weights"] is None for call in backend.calls)
    assert all(
        call["validation_weights"]
        == pytest.approx(
            [
                1.0 / data.cached.base.validation.channel_ids.count(ch)
                for ch in data.cached.base.validation.channel_ids
            ]
        )
        for call in backend.calls
    )
    if algorithm == "B":
        assert {call["params"]["thread_count"] for call in backend.calls} == {2}
        assert all(
            call["params"]["allow_writing_files"] is False
            and call["params"]["nan_mode"] == "Forbidden"
            for call in backend.calls
        )
        assert all(
            call["params"]["fit_use_best_model"] is True
            and call["params"]["early_stopping_rounds"] == 50
            for call in backend.calls
        )
    else:
        assert {call["params"]["num_threads"] for call in backend.calls} == {1}
        assert all(
            call["params"]["deterministic"] is True
            and call["params"]["force_col_wise"] is True
            and call["params"]["feature_pre_filter"] is False
            for call in backend.calls
        )
    assert bundle.artifact["feature_names"] == list(FEATURE_NAMES) and len(FEATURE_NAMES) == 912
    assert bundle.artifact["categorical_indices"] == list(CATEGORICAL_INDICES)
    assert (
        bundle.artifact["quality_accepted"] is False
        and bundle.artifact["quality_release_sha256"] is None
    )
    loaded = load_bundle(out, data=data, backend=RecordingBackend())
    assert np.array_equal(
        bundle.predict_logs(data.validation, repaired=False),
        loaded.predict_logs(data.validation, repaired=False),
    )
    assert (out / "artifact.json").stat().st_mode & 0o777 == 0o600
    assert out.stat().st_mode & 0o777 == 0o700
    unused = RecordingBackend()
    with pytest.raises(ExperimentError, match="already_exists"):
        train_experiment(data, out, algorithm=algorithm, backend=unused)
    assert unused.calls == []


def test_integrated_pair_compare_reload_and_q50_contributions(tmp_path):
    from scripts.full_visual_evidence_v7 import explain_full

    fixture = _fixture(tmp_path / "source")
    data, _ = _load(fixture)
    b, _ = train_experiment(data, tmp_path / "b", algorithm="B", backend=RecordingBackend())
    c, _ = train_experiment(data, tmp_path / "c", algorithm="C", backend=RecordingBackend())
    comparison = compare(data, b, c)
    assert comparison["paired"] is True
    assert set(comparison) >= {"B", "C", "B0"}
    assert comparison["holdout_opened"] is False and comparison["selection_or_promotion"] is False
    for n in (1, 3, 5):
        for bundle in (b, c):
            evidence = explain_full(bundle, data.validation[:n], data=data)
            assert len(evidence) == n and all(len(row["drivers"]) == 14 for row in evidence)
            covered = [i for driver in evidence[0]["drivers"] for i in driver["feature_indices"]]
            assert sorted(covered) == list(range(912))
            assert len(set(covered)) == 912
            assert all(
                row["absolute_reconstruction_error"] <= 1e-7
                and row["causal"] is False
                and row["quality_accepted"] is False
                for row in evidence
            )
    assert (b.report["selected"][0]["depth"], b.report["selected"][0]["l2_leaf_reg"]) == (4, 3)
    assert (c.report["selected"][0]["num_leaves"], c.report["selected"][0]["min_data_in_leaf"]) == (
        7,
        5,
    )
    for report in (b.report, c.report):
        for q in (0.1, 0.5, 0.9):
            scores = [
                trial["validation_score"] for trial in report["trials"] if trial["quantile"] == q
            ]
            assert len(set(scores)) == 1

    assert comparison["partition"] == "validation"
    assert comparison["final_test_evaluated"] is False
    assert comparison["provenance"]["train_split_sha256"] == b.artifact["train_split_sha256"]
    from scripts.channel_partitions import digest

    assert comparison["result_sha256"] == digest(
        {key: value for key, value in comparison.items() if key != "result_sha256"}
    )
    for report in (b.report, c.report):
        for q in (0.1, 0.5, 0.9):
            scores = [
                trial["validation_score"] for trial in report["trials"] if trial["quantile"] == q
            ]
            assert len(set(scores)) == 1


def test_c_encoding_learns_only_train_and_rejects_new_or_unknown_category():
    train = [[0] * 912 for _ in range(2)]
    train[0][905] = "false"
    train[1][905] = "true"
    vocab = _fit_c_encoding(train)
    with pytest.raises(ExperimentError, match="unseen_category"):
        _encode_c([[0] * 905 + ["unknown"] + [0] * 6], vocab)


def test_recording_bundle_cannot_be_loaded_as_native_and_tampering_is_refused(tmp_path):
    fixture = _fixture(tmp_path / "source")
    data, _ = _load(fixture)
    out = tmp_path / "model"
    train_experiment(data, out, algorithm="B", backend=RecordingBackend())
    from scripts.full_visual_models_v7 import NativeBackend

    with pytest.raises(ExperimentError, match="recording_backend_injection_required"):
        load_bundle(out, data=data)
    with pytest.raises(ExperimentError, match="recording_artifact_rejected"):
        load_bundle(out, data=data, backend=NativeBackend("B"))
    path = out / "q50.model"
    path.write_bytes(path.read_bytes() + b"tamper")
    with pytest.raises(ExperimentError):
        load_bundle(out, data=data, backend=RecordingBackend())


def test_compare_reloads_bundles_against_exact_input_dataset_before_predict(tmp_path, monkeypatch):
    from dataclasses import replace

    fixture_a = _fixture(tmp_path / "source-a")
    data_a, _ = _load(fixture_a)
    b, _ = train_experiment(data_a, tmp_path / "b", algorithm="B", backend=RecordingBackend())
    c, _ = train_experiment(data_a, tmp_path / "c", algorithm="C", backend=RecordingBackend())

    cached = fixture_a["cached"]
    changed_input = cached.train[0].model_copy(
        update={"brightness_mean_0_1": cached.train[0].brightness_mean_0_1 + 0.125}
    )
    changed_cached = replace(cached, train=(changed_input, *cached.train[1:]))
    fixture_b = _fixture(tmp_path / "source-b", cached=changed_cached)
    data_b, _ = _load(fixture_b)
    assert data_a.cached.base.train.targets == data_b.cached.base.train.targets
    assert data_a.manifest.identities == data_b.manifest.identities
    from scripts.full_visual_data_v7 import split_digest

    assert split_digest(data_a, "train") != split_digest(data_b, "train")

    def forbidden_predict(**_kwargs):
        raise AssertionError("pairing must fail before any prediction")

    monkeypatch.setattr(b.backend, "predict", forbidden_predict)
    monkeypatch.setattr(c.backend, "predict", forbidden_predict)
    with pytest.raises(ExperimentError, match="pairing_mismatch"):
        compare(data_b, b, c)


def test_compare_ignores_mutated_in_memory_bundle_metadata(tmp_path):
    fixture = _fixture(tmp_path / "source")
    data, _ = _load(fixture)
    b, _ = train_experiment(data, tmp_path / "b", algorithm="B", backend=RecordingBackend())
    c, _ = train_experiment(data, tmp_path / "c", algorithm="C", backend=RecordingBackend())
    b.artifact["algorithm"] = "C"
    c.artifact["algorithm"] = "B"
    comparison = compare(data, b, c)
    assert comparison["paired"] is True
    assert comparison["provenance"]["B_artifact_sha256"] == sha(
        (b.directory / "artifact.json").read_bytes()
    )
    assert comparison["provenance"]["C_artifact_sha256"] == sha(
        (c.directory / "artifact.json").read_bytes()
    )


def test_observed_boundary_and_non_boolean_flags_fail_before_backend(tmp_path):
    from dataclasses import replace

    from scripts.channel_partitions import ExperimentError

    fixture = _fixture(tmp_path / "source")
    data, _ = _load(fixture)
    backend = RecordingBackend()
    with pytest.raises(ExperimentError):
        train_experiment(
            replace(data, data_kind="observed_unreleased"),
            tmp_path / "observed",
            algorithm="B",
            backend=backend,
        )
    with pytest.raises(ExperimentError):
        train_experiment(
            replace(data, quality_accepted=0), tmp_path / "badflag", algorithm="B", backend=backend
        )
    assert (
        backend.calls == []
        and not (tmp_path / "observed").exists()
        and not (tmp_path / "badflag").exists()
    )

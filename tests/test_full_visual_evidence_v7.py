from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import replace

import numpy as np
import pytest

from scripts.channel_partitions import ExperimentError, digest
from scripts.empirical_baseline import MAX_LOG_VIEWS
from scripts.full_visual_artifact_v7 import canonical
from scripts.full_visual_models_v7 import (
    FitResult,
    RecordingBackend,
    load_bundle,
    train_experiment,
)
from tests.test_full_visual_data_v7 import _fixture, _load


@pytest.fixture(autouse=True)
def trap_native_calls(monkeypatch):
    import catboost
    import lightgbm

    def fail(*_args, **_kwargs):
        pytest.fail("native call forbidden in recording evidence tests")

    monkeypatch.setattr(catboost, "Pool", fail)
    monkeypatch.setattr(catboost, "CatBoostRegressor", fail)
    monkeypatch.setattr(lightgbm, "Dataset", fail)
    monkeypatch.setattr(lightgbm, "train", fail)
    monkeypatch.setattr(lightgbm, "Booster", fail)


def _trained(tmp_path, algorithm="B", backend=None):
    fixture = _fixture(tmp_path / "source")
    data, _ = _load(fixture)
    actual = backend or RecordingBackend()
    bundle, _ = train_experiment(data, tmp_path / "model", algorithm=algorithm, backend=actual)
    return data, bundle, actual


def test_unverified_manual_data_stops_before_targets_or_backend(tmp_path, monkeypatch):
    data, _bundle, _ = _trained(tmp_path)
    manual = replace(data, loader_verified=False)
    backend = RecordingBackend()

    def target_sentinel(*_args, **_kwargs):
        pytest.fail("target accessed before verified source boundary")

    monkeypatch.setattr("scripts.full_visual_models_v7._targets", target_sentinel)
    with pytest.raises(ExperimentError, match="loader_verified_data_required"):
        train_experiment(manual, tmp_path / "manual-model", backend=backend)
    assert backend.calls == []


class _OutOfRangeBackend(RecordingBackend):
    def fit_trial(self, **kwargs):
        fit = super().fit_trial(**kwargs)
        invalid = np.full_like(fit.predictions, MAX_LOG_VIEWS + 1.0)
        return FitResult(
            fit.model,
            invalid,
            fit.best_iteration,
            fit.tree_count,
            fit.evaluated_iterations,
            fit.native_validation_metric,
            fit.elapsed_seconds,
        )


def test_every_trial_is_checked_against_physical_prediction_limit(tmp_path):
    fixture = _fixture(tmp_path / "source")
    data, _ = _load(fixture)
    with pytest.raises(ExperimentError, match="invalid_quantile_predictions"):
        train_experiment(data, tmp_path / "model", backend=_OutOfRangeBackend())


class _BadContributionBackend(RecordingBackend):
    def __init__(self, failure):
        super().__init__()
        self.failure = failure

    def contributions(self, *, algorithm, model, matrix):
        values = super().contributions(algorithm=algorithm, model=model, matrix=matrix)
        if self.failure == "shape":
            return values[:, :-1]
        if self.failure == "nonfinite":
            values[0, 0] = np.nan
        if self.failure == "absolute_tolerance":
            values[:, -1] += 1.03e-7
        return values


@pytest.mark.parametrize(
    "failure,error",
    [
        ("shape", "shape_or_coverage"),
        ("nonfinite", "shape_or_coverage"),
        ("absolute_tolerance", "reconstruction_failed"),
    ],
)
def test_q50_evidence_rejects_malformed_or_inaccurate_drivers(tmp_path, failure, error):
    from scripts.full_visual_evidence_v7 import explain_full

    data, bundle, _ = _trained(tmp_path, "C", _BadContributionBackend(failure))
    with pytest.raises(ExperimentError, match=error):
        explain_full(bundle, data.validation[:1], data=data)


def test_sources_are_reloaded_before_prediction_and_memory_mutation_is_ignored(tmp_path):
    data, bundle, _ = _trained(tmp_path)
    expected = bundle.predict_logs(data.validation[:2], repaired=False)
    bundle.models[1]["level"] += 1.0
    assert np.array_equal(bundle.predict_logs(data.validation[:2], repaired=False), expected)
    source_record = data.source_records[0]
    sidecar = data.sidecar_root / f"features/{source_record.sample_id}.json"
    sidecar.write_bytes(sidecar.read_bytes() + b" ")
    with pytest.raises(ExperimentError, match="features_hash_mismatch"):
        bundle.predict_logs(data.validation[:1], repaired=False)


def test_protocol_runtime_source_and_descriptor_corruption_are_refused(tmp_path, monkeypatch):
    from scripts import full_visual_models_v7 as models

    data, bundle, _ = _trained(tmp_path)
    with (
        pytest.raises(ExperimentError, match="pairing_mismatch"),
        monkeypatch.context() as patcher,
    ):
        patcher.setattr(models, "_runtime", lambda: {"different": "runtime"})
        load_bundle(bundle.directory, data=data, backend=RecordingBackend())
    with (
        pytest.raises(ExperimentError, match="pairing_mismatch"),
        monkeypatch.context() as patcher,
    ):
        patcher.setattr(models, "_source_hashes", lambda: {"changed": "0" * 64})
        load_bundle(bundle.directory, data=data, backend=RecordingBackend())

    artifact_path = bundle.directory / "artifact.json"
    artifact = json.loads(artifact_path.read_bytes())
    original_artifact = copy.deepcopy(artifact)
    artifact["protocol"]["thread_count"] = 99
    artifact["content_sha256"] = digest(
        {k: v for k, v in artifact.items() if k != "content_sha256"}
    )
    artifact_path.write_bytes(canonical(artifact))
    with pytest.raises(ExperimentError, match="protocol_mismatch"):
        load_bundle(bundle.directory, data=data, backend=RecordingBackend())

    for malformed in ("false", 0, 1, None, True):
        candidate = copy.deepcopy(original_artifact)
        candidate["quality_accepted"] = malformed
        candidate["content_sha256"] = digest(
            {k: v for k, v in candidate.items() if k != "content_sha256"}
        )
        artifact_path.write_bytes(canonical(candidate))
        with pytest.raises(ExperimentError, match="artifact_pairing_mismatch"):
            load_bundle(bundle.directory, data=data, backend=RecordingBackend())

    artifact_path.write_bytes(canonical(original_artifact))
    report_path = bundle.directory / "validation-report.json"
    original_report_raw = report_path.read_bytes()
    report = json.loads(original_report_raw)
    report["quality_accepted"] = True
    report_path.write_bytes(canonical(report))
    artifact = json.loads(artifact_path.read_bytes())
    artifact["validation_report_sha256"] = hashlib.sha256(report_path.read_bytes()).hexdigest()
    artifact["content_sha256"] = digest(
        {k: v for k, v in artifact.items() if k != "content_sha256"}
    )
    artifact_path.write_bytes(canonical(artifact))
    with pytest.raises(ExperimentError, match="report_contract_mismatch"):
        load_bundle(bundle.directory, data=data, backend=RecordingBackend())
    report_path.write_bytes(original_report_raw)

    class BadDescriptor(RecordingBackend):
        def describe(self, *, algorithm, model):
            result = super().describe(algorithm=algorithm, model=model)
            result["feature_names"] = result["feature_names"][:-1]
            return result

    artifact_path.write_bytes(canonical(original_artifact))
    with pytest.raises(ExperimentError, match="model_descriptor_mismatch"):
        load_bundle(bundle.directory, data=data, backend=BadDescriptor())

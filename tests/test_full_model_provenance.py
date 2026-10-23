from dataclasses import replace
from types import SimpleNamespace

import pytest

from scripts import experiment_c_full_data as data_module
from scripts import train_experiment_c_full as training
from scripts.channel_partitions import ExperimentError
from tests.test_experiment_b_vlm_data import vlm_fixture


def test_verified_data_reloads_evidence_and_rejects_changed_sidecars(tmp_path, monkeypatch):
    data = vlm_fixture()
    calls = []

    def reload(source):
        calls.append(source)
        return data, []

    monkeypatch.setattr(data_module.FullDataSource, "reload", reload)
    source = data_module.FullDataSource(
        *(tmp_path / name for name in ("parent", "cohort", "queue", "release", "root"))
    )
    verified = data_module.VerifiedFullData(data, source)
    data_module.validate_full_data(verified)
    assert calls == [source]
    changed = replace(data, vlm_config={"synthetic": True, "changed": True})
    with pytest.raises(ExperimentError, match="sources_changed"):
        data_module.validate_full_data(data_module.VerifiedFullData(changed, source))


def test_a_self_declared_loader_or_boolean_is_not_provenance():
    data = vlm_fixture()
    fake = data_module.VerifiedFullData(data, SimpleNamespace(reload=lambda: (data, [])))
    with pytest.raises(ExperimentError, match="source_paths_required"):
        data_module.validate_full_data(fake)


def test_observed_group_ids_are_derived_from_frozen_parent(tmp_path, monkeypatch):
    original = {"v1", "v2"}
    parent = SimpleNamespace(
        assignments=[SimpleNamespace(sample_id=s, partition="validation") for s in original],
        manifest_sha256="a" * 64,
    )
    monkeypatch.setattr(training, "load_partitions", lambda path: parent)
    data = SimpleNamespace(
        base=SimpleNamespace(
            manifest=SimpleNamespace(data_kind="observed_pilot"),
            validation=SimpleNamespace(sample_ids=("v1", "v2", "v3")),
        ),
        source=SimpleNamespace(parent=tmp_path),
    )
    assert training.validation_groups(data) == (original, "a" * 64)
    with pytest.raises(ExperimentError, match="not_bound_to_parent"):
        training.validation_groups(data, {"v3"})


def test_observed_comparison_rejects_in_memory_models_before_prediction(monkeypatch):
    monkeypatch.setattr(training, "validate_full_data", lambda *_: None)
    monkeypatch.setattr(training, "validation_groups", lambda *_: (set(), "a" * 64))
    data = SimpleNamespace(
        base=SimpleNamespace(manifest=SimpleNamespace(data_kind="observed_pilot"))
    )
    with pytest.raises(ExperimentError, match="verified_native_loads"):
        training.compare(data, SimpleNamespace(), SimpleNamespace())


def test_observed_shap_requires_source_data_before_native_model_access():
    from scripts.full_model_evidence import explain_full

    bundle = SimpleNamespace(artifact=SimpleNamespace(data_kind="observed_pilot"))
    with pytest.raises(ExperimentError, match="verified_development"):
        explain_full(bundle, [object()])


def test_observed_shap_reloads_instead_of_using_mutated_memory_bundle(monkeypatch):
    from scripts import full_model_evidence as evidence

    called = []
    mutated = SimpleNamespace(artifact=SimpleNamespace(data_kind="observed_pilot"))

    def reload(bundle, *, data):
        assert bundle is mutated and data == "invented_source_marker"
        called.append(True)
        raise ExperimentError("changed_native_model_checksum")

    monkeypatch.setattr(evidence, "reload_observed_bundle", reload)
    with pytest.raises(ExperimentError, match="changed_native_model_checksum"):
        evidence.explain_full(mutated, [object()], data="invented_source_marker")
    assert called == [True]

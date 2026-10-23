"""Fixture-only integration tests for the synthetic V7 data loader."""

from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from scripts.channel_partitions import ExperimentError
from scripts.full_visual_contract_v7 import FIELDS, check_sidecar_v7, make_synthetic_sidecar
from scripts.full_visual_data_v7 import (
    B_REPRESENTATION,
    INDEX_SCHEMA_VERSION,
    RUN_SCHEMA_VERSION,
    SCHEMA_VERSION,
    V7PredictorInputs,
    V7SourceRecord,
    _b_contract,
    _expected_identities,
    _split_digest,
    categorical_indices,
    feature_matrix,
    feature_names,
    load_data,
    reload_data,
    source_versions,
    validate_data,
)
from tests.test_experiment_b_data import b_fixture

_forbidden_native_calls: list[str] = []


def _forbidden(name: str):
    def fail(*_args, **_kwargs):
        _forbidden_native_calls.append(name)
        pytest.fail(f"forbidden native training/model call: {name}")

    return fail


@pytest.fixture(autouse=True)
def forbid_model_construction_and_pool_use(monkeypatch):
    """Imports are allowed; native model/pool use is trapped before fixtures run."""
    import catboost

    import scripts.diagnose_m1 as diagnose
    import scripts.experiment_a_artifact as artifact

    for module, name in (
        (catboost, "Pool"),
        (catboost, "CatBoostRegressor"),
        (diagnose, "Pool"),
        (artifact, "Pool"),
        (artifact, "CatBoostRegressor"),
    ):
        monkeypatch.setattr(module, name, _forbidden(name))


def _sha(raw: bytes | str) -> str:
    if type(raw) is str:
        raw = raw.encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        + b"\n"
    )


def _attribute_values(index: int) -> dict:
    result = {}
    values = {
        "person_visible": bool(index % 2),
        "product_visible_early": bool((index + 1) % 2),
        "product_closeup": "unknown" if index % 3 == 0 else bool(index % 2),
        "demonstration": bool(index % 2),
        "screen_text": "unknown" if index % 4 == 0 else bool((index + 1) % 2),
        "scene": ("indoor", "outdoor", "graphic", "mixed", "unknown")[index % 5],
        "format": (
            "talking_head",
            "product_showcase",
            "application",
            "reaction",
            "mixed",
            "other",
            "unknown",
        )[index % 7],
    }
    for field in FIELDS:
        value = values[field]
        result[field] = {"value": value, "frames": [] if value == "unknown" else [1]}
    return result


def _fixture(tmp_path: Path, cached=None) -> dict:
    cached = b_fixture() if cached is None else cached
    identities = _expected_identities(cached)
    versions = source_versions()
    sidecar_root = tmp_path / "sidecars"
    (sidecar_root / "features").mkdir(parents=True)
    (sidecar_root / "runs").mkdir()
    opened_sidecar = []
    inputs_by_partition = {"train": [], "validation": []}
    records = []
    entries = []
    expected_rows = []
    for partition in ("train", "validation"):
        split = getattr(cached.base, partition)
        b_inputs = getattr(cached, partition)
        expected_rows.extend(
            (sample_id, partition, channel_id, b_input)
            for sample_id, channel_id, b_input in zip(
                split.sample_ids, split.channel_ids, b_inputs, strict=True
            )
        )
    for index, (sample_id, partition, channel_id, b_input) in enumerate(expected_rows):
        feature_value = make_synthetic_sidecar(
            sample_id=sample_id,
            partition=partition,
            channel_id=channel_id,
            identities=identities,
            frame_seconds=[0.0, 3.0, 8.5],
            frame_sha256=[_sha(f"frame:{sample_id}:{frame}") for frame in range(3)],
            attributes=_attribute_values(index),
        )
        feature_raw = _json_bytes(feature_value)
        feature_hash = _sha(feature_raw)
        run_value = {
            "schema_version": RUN_SCHEMA_VERSION,
            "data_kind": "synthetic",
            "sample_id": sample_id,
            "partition": partition,
            "channel_id": channel_id,
            "identities": identities,
            "status": "completed",
            "temporary_directory_removed": True,
            "features_sha256": feature_hash,
            "quality_accepted": False,
            "release_emitted": False,
        }
        run_raw = _json_bytes(run_value)
        run_hash = _sha(run_raw)
        features_ref = f"features/{sample_id}.json"
        run_ref = f"runs/{sample_id}.json"
        (sidecar_root / features_ref).write_bytes(feature_raw)
        (sidecar_root / run_ref).write_bytes(run_raw)
        opened_sidecar.extend((features_ref, run_ref))
        entries.append(
            {
                "sample_id": sample_id,
                "partition": partition,
                "channel_id": channel_id,
                "features_ref": features_ref,
                "run_ref": run_ref,
                "features_sha256": feature_hash,
                "run_sha256": run_hash,
            }
        )
        checked = check_sidecar_v7(feature_value)
        inputs_by_partition[partition].append(
            V7PredictorInputs(
                b=b_input,
                attributes=checked.attributes,
                data_kind="synthetic",
                quality_accepted=False,
                release_emitted=False,
            )
        )
        records.append(
            V7SourceRecord(
                sample_id=sample_id,
                partition=partition,
                channel_id=channel_id,
                features_sha256=feature_hash,
                run_sha256=run_hash,
                identities=identities,
                frame_seconds=checked.frame_seconds,
                frame_sha256=checked.frame_sha256,
                quality_accepted=False,
                release_emitted=False,
            )
        )
    index_value = {
        "schema_version": INDEX_SCHEMA_VERSION,
        "data_kind": "synthetic",
        "entries": entries,
        "quality_accepted": False,
        "release_emitted": False,
    }
    index_raw = _json_bytes(index_value)
    (sidecar_root / "index.json").write_bytes(index_raw)
    source_records = tuple(records)
    split_hashes = {
        part: _split_digest(
            cached,
            part,
            tuple(inputs_by_partition[part]),
            source_records,
            identities,
            versions,
        )
        for part in ("train", "validation")
    }
    manifest_value = {
        "schema_version": SCHEMA_VERSION,
        "data_kind": "synthetic",
        "identities": identities,
        "source_versions": versions,
        "index_ref": "index.json",
        "index_sha256": _sha(index_raw),
        "split_sha256": split_hashes,
        "quality_accepted": False,
        "release_emitted": False,
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_bytes(_json_bytes(manifest_value))
    return {
        "cached": cached,
        "manifest_path": manifest_path,
        "sidecar_root": sidecar_root,
        "expected_sidecar_relpaths": tuple(opened_sidecar),
        "manifest_value": manifest_value,
        "index_value": index_value,
        "entries": entries,
    }


def _load(fixture: dict):
    return load_data(
        fixture["cached"],
        fixture["manifest_path"],
        sidecar_root=fixture["sidecar_root"],
    )


def test_load_manifest_sidecars_rehash_sources_and_build_912_column_matrix(tmp_path):
    fixture = _fixture(tmp_path)
    data, opened = _load(fixture)
    validate_data(data)
    b = _b_contract()
    matrix = feature_matrix(data.train)
    prefix = b.feature_matrix(fixture["cached"].train)
    names = feature_names()
    assert len(names) == len(matrix[0]) == 912
    assert names[:905] == b.FEATURE_NAMES
    assert names[905:] == tuple(f"vlm_{field}" for field in FIELDS)
    assert [row[:905] for row in matrix] == prefix
    assert (
        matrix[0][905 + FIELDS.index("product_closeup")]
        == data.train[0].attributes["product_closeup"]
    )
    assert "unknown" in {row[-3] for row in matrix}
    assert categorical_indices() == (*b.CATEGORICAL_INDICES, *range(905, 912))
    assert data.loader_verified is True
    assert data.quality_accepted is False and data.release_emitted is False
    assert data.manifest_sha256 == _sha(fixture["manifest_path"].read_bytes())
    assert tuple(path.name for path in opened[:2]) == ("manifest.json", "index.json")
    assert len(opened) == 2 + 2 * len(fixture["entries"])
    assert not any(
        path.name in {"records.json", "predictor-inputs.json", "test.json"} for path in opened
    )
    assert "catboost" in sys.modules
    assert _forbidden_native_calls == []
    assert {
        "channel_partitions.py_sha256",
        "experiment_a_data.py_sha256",
        "experiment_b_data.py_sha256",
        "training_manifest.py_sha256",
        "empirical_baseline.py_sha256",
        "visual_attributes.py_sha256",
        "full_visual_contract_v7.py_sha256",
        "full_visual_data_v7.py_sha256",
    } <= set(data.manifest.source_versions)


def test_reload_reopens_and_rehashes_manifest_index_features_and_runs(tmp_path):
    fixture = _fixture(tmp_path)
    data, _ = _load(fixture)
    reloaded = reload_data(data)
    assert reloaded.loader_verified is True
    assert reloaded.manifest_sha256 == data.manifest_sha256
    assert reloaded.source_records == data.source_records


def test_changed_source_after_load_fails_reload(tmp_path):
    fixture = _fixture(tmp_path)
    data, _ = _load(fixture)
    entry = fixture["entries"][0]
    target = fixture["sidecar_root"] / entry["features_ref"]
    target.write_bytes(target.read_bytes() + b" ")
    with pytest.raises(ExperimentError, match="v7_features_hash_mismatch"):
        reload_data(data)


@pytest.mark.parametrize(
    ("kind", "error"),
    [
        ("features_hash", "v7_features_hash_mismatch"),
        ("run_hash", "v7_run_hash_mismatch"),
        ("path", "v7_path_rejected"),
        ("extra_index", "v7_index_count_mismatch"),
        ("split", "v7_split_digest_mismatch"),
        ("config_identity", "v7_cached_identity_mismatch"),
    ],
)
def test_hash_path_index_split_and_identity_corruption_are_rejected(tmp_path, kind, error):
    fixture = _fixture(tmp_path)
    if kind == "features_hash":
        path = fixture["sidecar_root"] / fixture["entries"][0]["features_ref"]
        path.write_bytes(path.read_bytes() + b"tamper")
    elif kind == "run_hash":
        path = fixture["sidecar_root"] / fixture["entries"][0]["run_ref"]
        path.write_bytes(path.read_bytes() + b"tamper")
    elif kind in {"path", "extra_index"}:
        index = fixture["index_value"]
        if kind == "path":
            index["entries"][0]["features_ref"] = "../outside.json"
        else:
            index["entries"].append(dict(index["entries"][-1]))
        index_raw = _json_bytes(index)
        (fixture["sidecar_root"] / "index.json").write_bytes(index_raw)
        manifest = fixture["manifest_value"]
        manifest["index_sha256"] = _sha(index_raw)
        fixture["manifest_path"].write_bytes(_json_bytes(manifest))
    elif kind == "split":
        manifest = fixture["manifest_value"]
        manifest["split_sha256"]["train"] = "0" * 64
        fixture["manifest_path"].write_bytes(_json_bytes(manifest))
    else:
        manifest = fixture["manifest_value"]
        manifest["identities"]["configuration_sha256"] = "0" * 64
        fixture["manifest_path"].write_bytes(_json_bytes(manifest))
    with pytest.raises(ExperimentError, match=error):
        _load(fixture)


@pytest.mark.parametrize(
    ("reference", "error"),
    [
        ("index_ref", "v7_manifest_invalid"),
        ("features_ref", "v7_path_rejected"),
        ("run_ref", "v7_path_rejected"),
    ],
)
def test_nul_in_manifest_or_index_references_is_rejected_statically(tmp_path, reference, error):
    fixture = _fixture(tmp_path)
    if reference == "index_ref":
        fixture["manifest_value"]["index_ref"] = "index\x00.json"
    else:
        fixture["index_value"]["entries"][0][reference] = f"bad\x00{reference}.json"
        index_raw = _json_bytes(fixture["index_value"])
        (fixture["sidecar_root"] / "index.json").write_bytes(index_raw)
        fixture["manifest_value"]["index_sha256"] = _sha(index_raw)
    fixture["manifest_path"].write_bytes(_json_bytes(fixture["manifest_value"]))
    with pytest.raises(ExperimentError, match=error) as caught:
        _load(fixture)
    assert "\x00" not in str(caught.value)


def test_nul_in_explicit_manifest_path_is_rejected_before_filesystem_access(tmp_path):
    fixture = _fixture(tmp_path)
    nul_manifest = tmp_path / "manifest\x00.json"
    with pytest.raises(ExperimentError, match="v7_explicit_path_required") as caught:
        load_data(fixture["cached"], nul_manifest, sidecar_root=fixture["sidecar_root"])
    assert "\x00" not in str(caught.value)


def test_nul_in_explicit_sidecar_root_stops_after_manifest(monkeypatch, tmp_path):
    fixture = _fixture(tmp_path)
    opened = []
    module = __import__("scripts.full_visual_data_v7", fromlist=["x"])
    original = module._read_bounded

    def track(path, opened_paths, **kwargs):
        opened.append(Path(path))
        return original(path, opened_paths, **kwargs)

    monkeypatch.setattr("scripts.full_visual_data_v7._read_bounded", track)
    nul_root = Path(f"{tmp_path}/bad\x00root")
    with pytest.raises(ExperimentError, match="v7_path_rejected") as caught:
        load_data(fixture["cached"], fixture["manifest_path"], sidecar_root=nul_root)
    assert "\x00" not in str(caught.value)
    assert opened == [fixture["manifest_path"]]


def test_index_partition_must_match_cached_split(tmp_path):
    fixture = _fixture(tmp_path)
    fixture["index_value"]["entries"][0]["partition"] = "validation"
    raw = _json_bytes(fixture["index_value"])
    (fixture["sidecar_root"] / "index.json").write_bytes(raw)
    fixture["manifest_value"]["index_sha256"] = _sha(raw)
    fixture["manifest_path"].write_bytes(_json_bytes(fixture["manifest_value"]))
    with pytest.raises(ExperimentError, match="v7_index_membership_or_order_mismatch"):
        _load(fixture)


def test_observed_cached_data_rejects_before_manifest_or_cached_validator(monkeypatch, tmp_path):
    observed_cache = SimpleNamespace(
        base=SimpleNamespace(manifest=SimpleNamespace(data_kind="observed_pilot"))
    )

    def fail(*_args, **_kwargs):
        pytest.fail("observed cache crossed the V7 boundary")

    monkeypatch.setattr("scripts.full_visual_data_v7._read_bounded", fail)
    monkeypatch.setattr("scripts.full_visual_data_v7._b_contract", fail)
    with pytest.raises(ExperimentError, match="seven_field_observed_quality_boundary_unavailable"):
        load_data(observed_cache, tmp_path / "must-not-open.json", sidecar_root=tmp_path)


def test_observed_manifest_reads_only_manifest_then_stops(monkeypatch, tmp_path):
    fixture = _fixture(tmp_path)
    observed_manifest = {"data_kind": "observed_unreleased"}
    fixture["manifest_path"].write_bytes(_json_bytes(observed_manifest))
    opened = []
    original = __import__("scripts.full_visual_data_v7", fromlist=["x"])._read_bounded

    def track(path, opened_paths, **kwargs):
        opened.append(Path(path))
        return original(path, opened_paths, **kwargs)

    monkeypatch.setattr("scripts.full_visual_data_v7._read_bounded", track)
    monkeypatch.setattr(
        "scripts.full_visual_data_v7._b_contract", lambda: pytest.fail("B validator opened")
    )
    with pytest.raises(ExperimentError, match="seven_field_observed_quality_boundary_unavailable"):
        _load(fixture)
    assert opened == [fixture["manifest_path"]]


def test_validate_data_rejects_observed_cached_object_before_cached_validator(
    monkeypatch, tmp_path
):
    fixture = _fixture(tmp_path)
    data, _ = _load(fixture)
    fake_cache = SimpleNamespace(
        base=SimpleNamespace(manifest=SimpleNamespace(data_kind="observed_pilot"))
    )
    data = replace(data, cached=fake_cache)
    monkeypatch.setattr(
        "scripts.full_visual_data_v7._b_contract",
        lambda: pytest.fail("cached validator was called"),
    )
    with pytest.raises(ExperimentError, match="seven_field_observed_quality_boundary_unavailable"):
        validate_data(data)


def test_observed_sidecar_is_only_structural_and_never_predictor_data(tmp_path):
    fixture = _fixture(tmp_path)
    feature_path = fixture["sidecar_root"] / fixture["entries"][0]["features_ref"]
    feature = json.loads(feature_path.read_bytes())
    feature["data_kind"] = "observed_unreleased"
    feature_raw = _json_bytes(feature)
    feature_path.write_bytes(feature_raw)
    entry = fixture["entries"][0]
    entry["features_sha256"] = _sha(feature_raw)
    run_path = fixture["sidecar_root"] / entry["run_ref"]
    run = json.loads(run_path.read_bytes())
    run["features_sha256"] = entry["features_sha256"]
    run_raw = _json_bytes(run)
    run_path.write_bytes(run_raw)
    entry["run_sha256"] = _sha(run_raw)
    index_raw = _json_bytes(fixture["index_value"])
    (fixture["sidecar_root"] / "index.json").write_bytes(index_raw)
    fixture["manifest_value"]["index_sha256"] = _sha(index_raw)
    fixture["manifest_path"].write_bytes(_json_bytes(fixture["manifest_value"]))
    with pytest.raises(ExperimentError, match="seven_field_observed_quality_boundary_unavailable"):
        _load(fixture)


def test_observed_sidecar_header_is_rejected_before_attribute_validation(tmp_path):
    fixture = _fixture(tmp_path)
    feature_path = fixture["sidecar_root"] / fixture["entries"][0]["features_ref"]
    feature = json.loads(feature_path.read_bytes())
    feature["data_kind"] = "observed_unreleased"
    feature["attributes"] = {"malformed": True}
    feature_raw = _json_bytes(feature)
    feature_path.write_bytes(feature_raw)
    entry = fixture["entries"][0]
    entry["features_sha256"] = _sha(feature_raw)
    run_path = fixture["sidecar_root"] / entry["run_ref"]
    run = json.loads(run_path.read_bytes())
    run["features_sha256"] = entry["features_sha256"]
    run_raw = _json_bytes(run)
    run_path.write_bytes(run_raw)
    entry["run_sha256"] = _sha(run_raw)
    index_raw = _json_bytes(fixture["index_value"])
    (fixture["sidecar_root"] / "index.json").write_bytes(index_raw)
    fixture["manifest_value"]["index_sha256"] = _sha(index_raw)
    fixture["manifest_path"].write_bytes(_json_bytes(fixture["manifest_value"]))
    with pytest.raises(ExperimentError, match="seven_field_observed_quality_boundary_unavailable"):
        _load(fixture)


def test_observed_manifest_is_not_read_as_v7(tmp_path):
    fixture = _fixture(tmp_path)
    fixture["manifest_value"]["data_kind"] = "observed_unreleased"
    fixture["manifest_path"].write_bytes(_json_bytes(fixture["manifest_value"]))
    with pytest.raises(ExperimentError, match="seven_field_observed_quality_boundary_unavailable"):
        _load(fixture)


@pytest.mark.parametrize("flag", [0, "false", None])
def test_non_boolean_or_truthy_release_flags_are_rejected(flag):
    cached = b_fixture()
    raw = {
        "schema_version": SCHEMA_VERSION,
        "data_kind": "synthetic",
        "identities": _expected_identities(cached),
        "source_versions": source_versions(),
        "index_ref": "index.json",
        "index_sha256": "a" * 64,
        "split_sha256": {"train": "b" * 64, "validation": "c" * 64},
        "quality_accepted": flag,
        "release_emitted": False,
    }
    from scripts.full_visual_data_v7 import V7Manifest

    with pytest.raises((ExperimentError, ValidationError)):
        V7Manifest.model_validate(raw)


def test_predictor_input_rejects_coerced_release_flags():
    cached = b_fixture()
    raw = {
        "b": cached.train[0],
        "attributes": {field: "unknown" for field in FIELDS},
        "data_kind": "synthetic",
        "quality_accepted": 0,
        "release_emitted": False,
    }
    with pytest.raises(
        (ExperimentError, ValidationError), match="v7_quality_must_remain_unreleased"
    ):
        V7PredictorInputs.model_validate(raw)


def test_manual_dataset_rejects_coerced_release_flags_before_validation(tmp_path):
    fixture = _fixture(tmp_path)
    data, _ = _load(fixture)
    with pytest.raises(ExperimentError, match="v7_quality_must_remain_unreleased"):
        validate_data(replace(data, quality_accepted=0))


def test_source_record_rechecks_timeline_and_creative_duration(tmp_path):
    fixture = _fixture(tmp_path)
    data, _ = _load(fixture)
    invalid_record = data.source_records[0].model_copy(update={"frame_seconds": (0.0, 3.0, 10.5)})
    manual = replace(
        data, source_records=(invalid_record, *data.source_records[1:]), loader_verified=False
    )
    with pytest.raises((ExperimentError, ValidationError)):
        validate_data(manual)


def test_verified_data_reopens_sources_even_if_manifest_digest_is_recomputed_in_memory(tmp_path):
    fixture = _fixture(tmp_path)
    data, _ = _load(fixture)
    first = data.train[0]
    changed = first.model_copy(update={"attributes": first.attributes | {"scene": "outdoor"}})
    changed_train = (changed, *data.train[1:])
    from scripts.full_visual_data_v7 import V7Manifest, _split_digest

    split_sha256 = dict(data.manifest.split_sha256)
    split_sha256["train"] = _split_digest(
        data.cached,
        "train",
        changed_train,
        data.source_records,
        data.manifest.identities,
        data.manifest.source_versions,
    )
    manifest = V7Manifest.model_validate(
        data.manifest.model_dump() | {"split_sha256": split_sha256}
    )
    changed_data = replace(data, train=changed_train, manifest=manifest)
    with pytest.raises(ExperimentError, match="v7_reloaded_dataset_mismatch"):
        validate_data(changed_data)


def test_captured_import_closure_contains_catboost_but_no_native_calls():
    assert "catboost" in sys.modules
    assert _forbidden_native_calls == []
    assert B_REPRESENTATION == "b_cached_clip_audio_905_v1_no_vlm_no_imputation"

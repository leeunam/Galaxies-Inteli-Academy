import json
from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.channel_partitions import ExperimentError, create_partitions, digest
from scripts.empirical_baseline import TrainingTarget, fit_baseline
from scripts.experiment_a_data import (
    FEATURE_NAMES,
    DevelopmentData,
    DevelopmentSplit,
    feature_matrix,
    load_development_data,
    validate_development_data,
)
from scripts.observed_baseline import CuratedReference
from scripts.training_manifest import PredictorInputs
from tests.test_training_manifest import encode, fixture


def development_fixture():
    records = [
        {
            "sample_id": f"sample_{i:03}",
            "channel_id": f"channel_{i // 3}",
            "sector": "moda" if i // 3 % 2 else "beleza",
            "media_sha256": digest(i),
        }
        for i in range(60)
    ]
    manifest = create_partitions(records, data_kind="synthetic")

    def split(name):
        rows = [r for r in manifest.assignments if r.partition == name]
        return DevelopmentSplit(
            partition=name,
            sample_ids=tuple(r.sample_id for r in rows),
            channel_ids=tuple(r.channel_id for r in rows),
            inputs=tuple(
                PredictorInputs(
                    sector=r.sector,
                    duration_seconds=float(10 + i),
                    aspect_ratio_height_over_width=1.8,
                    text_status="extracted",
                    text_embedding=tuple([0.01 * i] * 384),
                )
                for i, r in enumerate(rows)
            ),
            targets=tuple(
                TrainingTarget(sample_id=r.sample_id, view_count=100 + i * 100)
                for i, r in enumerate(rows)
            ),
        )

    train, validation = split("train"), split("validation")
    return DevelopmentData(
        manifest,
        "a" * 64,
        {"synthetic": True},
        fit_baseline(manifest, list(train.targets)),
        train,
        validation,
    )


def test_predictor_boundary_has_exactly_388_outcome_free_columns():
    data = development_fixture()
    validate_development_data(data)
    matrix = feature_matrix(data.train.inputs, supported_text_statuses=("extracted",))
    assert len(FEATURE_NAMES) == len(matrix[0]) == 388
    assert matrix[0][:4] == [data.train.inputs[0].sector, 10.0, 1.8, "extracted"]
    assert not {"view_count", "channel_id", "sample_id", "published_at_utc", "title"} & set(
        FEATURE_NAMES
    )
    test_ids = {r.sample_id for r in data.manifest.assignments if r.partition == "test"}
    assert not test_ids & set(data.train.sample_ids + data.validation.sample_ids)


def test_fit_boundary_rejects_validation_as_train_and_wrong_baseline():
    data = development_fixture()
    with pytest.raises(ExperimentError, match="development_partition_mismatch"):
        validate_development_data(replace(data, train=data.validation))
    wrong = development_fixture()
    changed = [t.model_copy(update={"view_count": t.view_count + 1}) for t in wrong.train.targets]
    with pytest.raises(ExperimentError, match="development_baseline_mismatch"):
        validate_development_data(replace(data, baseline=fit_baseline(data.manifest, changed)))


def test_test_cannot_be_a_development_split():
    with pytest.raises(ValidationError):
        DevelopmentSplit.model_validate(
            development_fixture().validation.model_dump() | {"partition": "test"}
        )


@pytest.mark.parametrize("status", ["no_audio_stream", "no_speech_detected_by_asr"])
def test_absence_requires_train_support_and_is_not_fabricated_speech(status):
    missing = PredictorInputs(
        sector="moda",
        duration_seconds=10.0,
        aspect_ratio_height_over_width=1.8,
        text_status=status,
        text_embedding=None,
    )
    with pytest.raises(ExperimentError, match="unsupported_text_status"):
        feature_matrix([missing], supported_text_statuses=("extracted",))
    matrix = feature_matrix([missing], supported_text_statuses=("extracted", status))
    assert matrix[0][3] == status
    assert matrix[0][4:] == [0.0] * 384


@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_nonfinite_embedding_is_rejected(value):
    raw = development_fixture().train.inputs[0].model_dump()
    raw["text_embedding"] = tuple([value] * 384)
    with pytest.raises(ValidationError):
        feature_matrix([raw], supported_text_statuses=("extracted",))


@pytest.fixture
def released_bundle(tmp_path, monkeypatch):
    from scripts.observed_baseline import freeze_cohort, publish_baseline
    from scripts.training_manifest import TrainingReference, import_training_manifest

    records, evidence, index = [], {}, {}
    for i in range(200):
        row, features, run, config = fixture(i)
        row, pair = encode(row, features, run)
        records.append(row)
        evidence.update(pair)
        paths = []
        for kind, raw in zip(("features", "run"), pair[row["sample_id"]], strict=True):
            path = tmp_path / f"{i}-{kind}.json"
            path.write_bytes(raw)
            paths.append(path.name)
        index[row["sample_id"]] = dict(zip(("features_ref", "run_ref"), paths, strict=True))
    directory = tmp_path / "released"
    freeze_cohort(
        [
            TrainingReference.model_validate(r).model_dump(
                include=set(CuratedReference.model_fields)
            )
            for r in records
        ],
        directory,
        source_snapshot_sha256="a" * 64,
    )
    from scripts.channel_partitions import load_partitions

    manifest = load_partitions(directory / "partitions.json")
    by_id = {r["sample_id"]: r for r in records}
    publish_baseline(
        directory,
        [
            TrainingTarget(
                sample_id=r.sample_id, view_count=by_id[r.sample_id]["view_count_observed"]
            )
            for r in manifest.assignments
            if r.partition == "train"
        ],
    )
    _, predictors = import_training_manifest(records, evidence, config, partitions=manifest)
    for name, value in {
        "records.json": records,
        "evidence-index.json": index,
        "extractor-config.json": config,
        "predictor-inputs.json": {k: v.model_dump() for k, v in predictors.items()},
    }.items():
        (directory / name).write_text(json.dumps(value))
    monkeypatch.setattr("scripts.experiment_a_data.check_extractor_runtime", lambda *_: None)
    return directory, tmp_path


def test_loader_revalidates_release_and_exposes_only_development(released_bundle):
    directory, root = released_bundle
    data = load_development_data(directory, evidence_root=root)
    assert len(data.train.sample_ids) + len(data.validation.sample_ids) < 200
    assert not hasattr(data, "test")


@pytest.mark.parametrize("failure", ["evidence", "predictors", "cohort", "unsafe_path"])
def test_loader_rejects_stale_or_incompatible_evidence(released_bundle, failure):
    directory, root = released_bundle
    if failure == "evidence":
        (root / "0-features.json").write_text("{}")
    elif failure == "predictors":
        (directory / "predictor-inputs.json").write_text("{}")
    elif failure == "cohort":
        path = directory / "records.json"
        rows = json.loads(path.read_bytes())
        rows[0]["curation_evidence_sha256"] = "c" * 64
        path.write_text(json.dumps(rows))
    else:
        path = directory / "evidence-index.json"
        index = json.loads(path.read_bytes())
        next(iter(index.values()))["features_ref"] = str(Path("/tmp/outside.json"))
        path.write_text(json.dumps(index))
    with pytest.raises(ExperimentError):
        load_development_data(directory, evidence_root=root)

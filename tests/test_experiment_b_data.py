import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.channel_partitions import ExperimentError
from scripts.experiment_a_data import feature_matrix as a_matrix
from scripts.experiment_b_data import (
    CATEGORICAL_INDICES,
    FEATURE_NAMES,
    BDevelopmentData,
    BInputs,
    feature_matrix,
    load_data,
    validate_cohort_boundary,
    validate_data,
)
from tests.test_experiment_a_data import development_fixture


def b_fixture():
    base = development_fixture()

    def extras(part):
        return tuple(
            BInputs(
                a=a,
                image_embedding=tuple([0.02 * (i + 1)] * 512),
                brightness_mean_0_1=0.5,
                saturation_mean_0_1=0.3,
                audio_rms=0.2,
                audio_duration_seconds=a.duration_seconds,
                audio_status="transcribed",
            )
            for i, a in enumerate(getattr(base, part).inputs)
        )

    return BDevelopmentData(base, extras("train"), extras("validation"))


def test_b_preserves_the_exact_a_prefix_and_has_no_outcome_or_audit_fields():
    data = b_fixture()
    validate_data(data)
    rows = feature_matrix(data.train)
    assert len(FEATURE_NAMES) == len(rows[0]) == 905
    assert [r[:388] for r in rows] == a_matrix(
        data.base.train.inputs, supported_text_statuses=("extracted",)
    )
    assert CATEGORICAL_INDICES == (0, 3, 904)
    assert rows[0][-5:] == [0.5, 0.3, 0.2, 10.0, "transcribed"]
    assert not any(
        forbidden in field
        for field in FEATURE_NAMES
        for forbidden in ("view_count", "channel_id", "sample_id", "title", "date", "vlm")
    )


@pytest.mark.parametrize(
    "update",
    [
        {"image_embedding": tuple([0.0] * 511)},
        {"image_embedding": tuple([float("nan")] * 512)},
        {"audio_rms": None},
        {"audio_rms": float("inf")},
        {"audio_duration_seconds": -1.0},
        {"brightness_mean_0_1": 1.1},
        {"saturation_mean_0_1": -0.1},
        {"audio_status": "no_speech_detected_by_asr"},
        {"view_count": 999},
    ],
)
def test_missing_corrupt_or_leaking_modalities_are_refused(update):
    raw = b_fixture().train[0].model_dump() | update
    with pytest.raises(ValidationError):
        BInputs.model_validate(raw)


def test_alignment_refuses_reordered_or_validation_rows_as_training():
    data = b_fixture()
    for change in (data.validation, data.train[::-1], data.train[:-1]):
        with pytest.raises(ExperimentError, match="b_development_alignment"):
            validate_data(replace(data, train=change))


def test_no_audio_cannot_be_disguised_as_transcribed_audio():
    value = b_fixture().train[0]
    raw = value.model_dump()
    raw["a"].update(text_status="no_audio_stream", text_embedding=None)
    with pytest.raises(ValidationError, match="b_requires_supported"):
        BInputs.model_validate(raw)


@pytest.mark.parametrize("corruption", [None, "hash", "clip", "policy"])
def test_loader_only_opens_selected_development_and_revalidates_extras(
    tmp_path, monkeypatch, corruption
):
    data = b_fixture()
    monkeypatch.setattr("scripts.experiment_b_data.validate_cohort_boundary", lambda *a, **kw: None)
    monkeypatch.setattr(
        "scripts.experiment_b_data.load_diagnostic_data", lambda *a: (data.base, [])
    )
    index = {"reserved_id": {"features_ref": "reserved.json"}}
    for part in ("train", "validation"):
        for sample, value in zip(getattr(data.base, part).sample_ids, getattr(data, part)):
            f = {
                "schema_version": "creative-features-v1",
                "feature_policy": {"clip_pooling": "mean_of_deduplicated_sample_frames"},
                "vlm": {"status": "not_requested"},
                "image_embedding": list(value.image_embedding),
                "properties": {"brightness_mean_0_1": 0.5, "saturation_mean_0_1": 0.3},
                "audio_status": "transcribed",
                "audio_rms": 0.2,
                "audio_duration_seconds": value.audio_duration_seconds,
            }
            if sample == data.base.train.sample_ids[0]:
                if corruption == "clip":
                    f["image_embedding"] = [0.0]
                elif corruption == "policy":
                    f["feature_policy"]["clip_pooling"] = "other"
            raw = json.dumps(f).encode()
            path = tmp_path / f"{sample}.json"
            path.write_bytes(raw)
            index[sample] = {
                "features_ref": path.name,
                "curation": {"features_sha256": hashlib.sha256(raw).hexdigest()},
            }
    if corruption == "hash":
        index[data.base.train.sample_ids[0]]["curation"]["features_sha256"] = "0" * 64
    (tmp_path / "evidence-index.json").write_text(json.dumps(index))
    original = Path.open

    def guarded(path, *args, **kwargs):
        assert path.name not in {"reserved.json", "records.json", "predictor-inputs.json"}
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded)
    if corruption:
        with pytest.raises((ExperimentError, ValidationError)):
            load_data(tmp_path, tmp_path, parent=tmp_path)
    else:
        result, _ = load_data(tmp_path, tmp_path, parent=tmp_path)
        assert result == data


@pytest.mark.parametrize("change", [None, "new_test", "old_test_to_validation", "lineage"])
def test_metadata_boundary_refuses_partition_changes_before_evidence(tmp_path, monkeypatch, change):
    from scripts.channel_partitions import (
        append_development_partitions,
        create_partitions,
        digest,
        load_partitions,
    )
    from scripts.observed_baseline import CuratedReference, freeze_cohort
    from scripts.private_checkpoint import save
    from tests.test_training_manifest import fixture

    records = []
    for i in range(300):
        row, *_ = fixture(i)
        records.append(
            CuratedReference.model_validate(
                {k: row[k] for k in CuratedReference.model_fields if k in row}
            ).model_dump()
        )
    parent, cohort = tmp_path / "parent", tmp_path / "cohort"
    release = freeze_cohort(records[:200], parent, source_snapshot_sha256="a" * 64)
    old = load_partitions(parent / "partitions.json")
    reference_fields = {"sample_id", "channel_id", "sector", "media_sha256", "duplicate_group"}
    extras = [{k: v for k, v in row.items() if k in reference_fields} for row in records[200:]]
    manifest = append_development_partitions(old, extras)
    body = release.model_dump(exclude={"release_sha256", "records"}) | {"records": records}
    save(cohort / "cohort.json", body | {"release_sha256": digest(body)})
    raw = manifest.model_dump()
    if change == "lineage":
        rows = [r.model_dump(include=reference_fields) for r in release.records]
        different = create_partitions(rows, seed=43, data_kind="observed_pilot")
        raw = append_development_partitions(different, extras).model_dump()
    elif change:
        if change == "new_test":
            fresh_ids = {v["sample_id"] for v in extras}
            target = next(r for r in raw["assignments"] if r["sample_id"] in fresh_ids)
        else:
            target = next(r for r in raw["assignments"] if r["partition"] == "test")
        target["partition"] = "test" if change == "new_test" else "validation"
        raw["manifest_sha256"] = digest({k: v for k, v in raw.items() if k != "manifest_sha256"})
    save(cohort / "partitions.json", raw)
    monkeypatch.setattr(
        "scripts.experiment_b_data.load_diagnostic_data",
        lambda *a: (_ for _ in ()).throw(AssertionError("evidence loader must not run")),
    )
    original = Path.open

    def metadata_only(path, *a, **kw):
        assert path.name in {"cohort.json", "partitions.json"}
        return original(path, *a, **kw)

    monkeypatch.setattr(Path, "open", metadata_only)
    if change:
        with pytest.raises((ExperimentError, ValidationError)):
            load_data(cohort, tmp_path, parent=parent)
    else:
        validate_cohort_boundary(parent, cohort)
        for wrong in (
            {"expected_cohort_sha256": "0" * 64},
            {"expected_partition_sha256": "0" * 64},
        ):
            with pytest.raises(ExperimentError, match="b_requires_same_cohort"):
                validate_cohort_boundary(parent, cohort, **wrong)

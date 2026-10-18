import hashlib
import json

import pytest
from pydantic import ValidationError

from scripts.channel_partitions import ExperimentError, Reference, create_partitions, digest
from scripts.observed_baseline import observation_digest
from scripts.pilot_licensed_media import EXTRACTOR_VERSION, FRAME_POLICY, MODELS
from scripts.training_manifest import TrainingReference, import_training_manifest, readiness


def fixture(index=0, *, text_status="extracted"):
    """Invented evidence, never a real training corpus."""
    sample = f"f{index:010d}"
    sector = "moda" if index % 2 else "beleza"
    row = {
        "sample_id": sample,
        "channel_id": f"channel_{index // 4}",
        "sector": sector,
        "media_sha256": digest(sample),
        "acquired_media_sha256": digest(sample),
        "source_url": f"https://www.youtube.com/watch?v={sample}",
        "published_at_utc": "2026-09-15T12:00:00Z",
        "observed_at_utc": "2026-10-17T12:00:00Z",
        "duration_seconds": 12.0,
        "width": 360,
        "height": 640,
        "spoken_language": "pt-BR",
        "language_evidence": "asr_and_agent_transcript_review",
        "content_review": "included",
        "curation_evidence_sha256": "a" * 64,
        "youtube_license": "youtube",
        "permission_basis": "explicit_operator_instruction",
        "permission_evidence_sha256": "b" * 64,
        "use_scope": "local_extraction_and_training",
        "curation_method": "automated_assisted_review",
        "view_count_observed": index,
    }
    row["frozen_observation_sha256"] = observation_digest(row, index)
    features = {
        "schema_version": EXTRACTOR_VERSION,
        "properties": {"duration_seconds": 12.0, "width": 360, "height": 640},
        "feature_policy": {
            "version": EXTRACTOR_VERSION,
            "frame_policy": FRAME_POLICY,
            "asr_beam_size": 1,
            "language_requested": None,
            "asr_temperature": 0,
            "asr_vad": True,
            "asr_condition_on_previous_text": False,
        },
        "text_features_status": text_status,
        "text_embedding": [0.1] * 384 if text_status == "extracted" else None,
    }
    run = {
        "status": "completed",
        "temporary_directory_removed": True,
        "source": {
            "audit": {
                "video_id": sample,
                "channel_id": row["channel_id"],
                "source_url": row["source_url"],
                "published_at_utc": row["published_at_utc"],
                "observed_at_utc": row["observed_at_utc"],
            },
            "target": {"view_count_observed": index},
        },
    }
    config = {
        "version": "entirely_synthetic_test",
        "models": {k: {"repo": v[0], "revision": v[1]} for k, v in MODELS.items()},
    }
    run["models"] = config["models"]
    run["media_fingerprint"] = {"sha256": row["media_sha256"]}
    row["extractor_config_sha256"] = digest(config)
    return row, features, run, config


def encode(row, features, run):
    raw_f = json.dumps(features).encode()
    raw_r = json.dumps(run).encode()
    row["features_sha256"] = hashlib.sha256(raw_f).hexdigest()
    row["run_sha256"] = hashlib.sha256(raw_r).hexdigest()
    return row, {row["sample_id"]: (raw_f, raw_r)}


def test_valid_features_stay_outcome_and_identity_free_but_small_corpus_stays_blocked():
    row, features, run, config = fixture()
    row, evidence = encode(row, features, run)
    report, inputs = import_training_manifest([row], evidence, config)
    assert not report["training_release_available"]
    assert "below_agreed_200_references" in report["blockers"]
    assert "extractor_evidence_not_verified" not in report["blockers"]
    values = inputs[row["sample_id"]].model_dump()
    assert not set(values) & {
        "view_count",
        "view_count_observed",
        "channel_id",
        "published_at_utc",
        "title",
        "like_count",
    }
    assert values["text_embedding"] == tuple([0.1] * 384)
    assert values["aspect_ratio_height_over_width"] == pytest.approx(640 / 360)
    assert not set(values) & {"width", "height"}


def test_metadata_size_alone_cannot_release_training():
    rows = []
    evidence = {}
    for i in range(200):
        row, features, run, config = fixture(i)
        row, pair = encode(row, features, run)
        rows.append(row)
        evidence.update(pair)
    assert readiness(rows)["blockers"] == [
        "extractor_evidence_not_verified",
        "channel_partitions_not_verified",
    ]
    assert not import_training_manifest(rows, evidence, config)[0]["training_release_available"]
    metadata = [
        TrainingReference.model_validate(r).model_dump(include=set(Reference.model_fields))
        for r in rows
    ]
    partitions = create_partitions(metadata, data_kind="observed_pilot")
    report, _ = import_training_manifest(rows, evidence, config, partitions=partitions)
    assert report["training_release_available"]
    assert not report["predictive_quality_validated"]
    assert "platform_approval_not_verified" in report["warnings"]


@pytest.mark.parametrize(
    "change",
    [
        {"spoken_language": "unknown"},
        {"youtube_license": None},
        {"permission_basis": "public_url"},
        {"view_count_observed": True},
        {"view_count_observed": 1},
        {"height": 300},
    ],
)
def test_incomplete_incompatible_or_relabeled_reference_rejected(change):
    row, features, run, _ = fixture()
    row, _ = encode(row, features, run)
    with pytest.raises(ValidationError):
        TrainingReference.model_validate(row | change)


@pytest.mark.parametrize(
    "failure",
    ["forced_language", "old_extractor", "wrong_identity", "changed_bytes", "invalid_vector"],
)
def test_regressions_cannot_be_promoted_by_new_checksums(failure):
    row, features, run, config = fixture()
    if failure == "forced_language":
        features["feature_policy"]["language_requested"] = "pt"
    elif failure == "old_extractor":
        features["schema_version"] = "pilot-features-v3"
    elif failure == "wrong_identity":
        run["source"]["audit"]["video_id"] = "wrong"
    elif failure == "invalid_vector":
        features["text_embedding"] = [float("nan")] * 384
    row, evidence = encode(row, features, run)
    if failure == "changed_bytes":
        a, b = evidence[row["sample_id"]]
        evidence[row["sample_id"]] = (a + b" ", b)
    with pytest.raises((ExperimentError, ValidationError)):
        import_training_manifest([row], evidence, config)


@pytest.mark.parametrize("status", ["no_audio_stream", "no_speech_detected_by_asr"])
def test_missing_text_is_preserved_as_missing(status):
    row, features, run, config = fixture(text_status=status)
    row, evidence = encode(row, features, run)
    _, inputs = import_training_manifest([row], evidence, config)
    assert inputs[row["sample_id"]].text_embedding is None


def test_download_resolution_is_audit_only_and_does_not_change_m1_input():
    results = []
    for width, height in ((720, 1280), (1080, 1920)):
        row, features, run, config = fixture()
        row.update(width=width, height=height)
        features["properties"].update(width=width, height=height)
        row, evidence = encode(row, features, run)
        _, inputs = import_training_manifest([row], evidence, config)
        results.append(inputs[row["sample_id"]])
    assert results[0] == results[1]


def test_a_new_acquisition_duplicate_cannot_cross_frozen_partitions():
    prepared = [fixture(i) for i in range(12)]
    metadata = [
        {key: row[key] for key in Reference.model_fields if key in row} for row, _, _, _ in prepared
    ]
    partitions = create_partitions(metadata, data_kind="observed_pilot")
    first = partitions.assignments[0]
    other = next(a for a in partitions.assignments if a.partition != first.partition)
    duplicated = {first.sample_id, other.sample_id}
    rows, evidence = [], {}
    for row, features, run, config in prepared:
        if row["sample_id"] in duplicated:
            row["acquired_media_sha256"] = "c" * 64
            run["media_fingerprint"]["sha256"] = "c" * 64
        row, pair = encode(row, features, run)
        rows.append(row)
        evidence.update(pair)
    with pytest.raises(ExperimentError, match="new_duplicate_crosses_partitions"):
        import_training_manifest(rows, evidence, config, partitions=partitions)


def test_changed_partition_metadata_is_rejected_even_with_valid_feature_evidence():
    prepared = [fixture(i) for i in range(12)]
    metadata = [
        {key: row[key] for key in Reference.model_fields if key in row} for row, _, _, _ in prepared
    ]
    metadata[0]["sector"] = "moda"
    partitions = create_partitions(metadata, data_kind="observed_pilot")
    rows, evidence = [], {}
    for row, features, run, config in prepared:
        row, pair = encode(row, features, run)
        rows.append(row)
        evidence.update(pair)
    with pytest.raises(ExperimentError, match="partition_metadata_mismatch"):
        import_training_manifest(rows, evidence, config, partitions=partitions)


def test_different_model_revision_is_not_approved_by_updating_checksums():
    row, features, run, config = fixture()
    config["models"]["asr"]["revision"] = "changed"
    row["extractor_config_sha256"] = digest(config)
    row, evidence = encode(row, features, run)
    with pytest.raises(ExperimentError, match="incompatible_model_revisions"):
        import_training_manifest([row], evidence, config)


def test_extra_evidence_ids_are_rejected():
    row, features, run, config = fixture()
    row, evidence = encode(row, features, run)
    evidence["extra"] = evidence[row["sample_id"]]
    with pytest.raises(ExperimentError, match="feature_evidence_ids_mismatch"):
        import_training_manifest([row], evidence, config)

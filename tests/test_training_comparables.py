"""Public synthetic evidence only; non-train files are guarded by canaries."""

import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from scripts.channel_partitions import ExperimentError
from scripts.diagnose_m1 import load_diagnostic_data
from scripts.experiment_a_data import split_digest
from scripts.m1_service import M1Settings
from scripts.observed_baseline import load_observed_baseline
from scripts.training_comparables import load_training_index

pytest_plugins = ["tests.test_experiment_a_data", "tests.test_diagnose_m1"]


@pytest.fixture
def context(diagnostic_bundle, monkeypatch):
    directory, root, index = diagnostic_bundle
    data, _ = load_diagnostic_data(directory, root)
    release, baseline = load_observed_baseline(directory)
    artifact = SimpleNamespace(
        training_sample_ids=data.train.sample_ids,
        train_split_sha256=split_digest(data.train),
        cohort_sha256=data.cohort_sha256,
        partition_manifest_sha256=data.manifest.manifest_sha256,
        baseline_sha256=baseline.artifact_sha256,
        artifact_sha256="a" * 64,
        supported_text_statuses=("extracted",),
    )
    monkeypatch.setattr(
        "scripts.training_comparables.load_model_context",
        lambda _: (release, baseline, SimpleNamespace(artifact=artifact)),
    )
    return M1Settings(root / "unused-model", directory), root, index, data, artifact


def guard_nontrain(context, monkeypatch):
    settings, root, index, data, _ = context
    forbidden = {
        (settings.cohort_dir / name).resolve() for name in ("records.json", "predictor-inputs.json")
    }
    permitted = set()
    for row in data.manifest.assignments:
        paths = {
            (root / index[row.sample_id][key]).resolve() for key in ("features_ref", "run_ref")
        }
        (permitted if row.partition == "train" else forbidden).update(paths)
    opened = set()
    original = Path.open

    def guarded(path, *args, **kwargs):
        resolved = path.resolve()
        assert resolved not in forbidden, "non-train or mixed evidence was opened"
        if resolved in permitted:
            opened.add(resolved)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded)
    return opened, permitted


def test_loader_opens_exactly_train_evidence_and_returns_no_outcomes(context, monkeypatch):
    settings, root, _, data, _ = context
    opened, permitted = guard_nontrain(context, monkeypatch)
    index = load_training_index(settings, root, minimum_similarity=0.5)
    assert opened == permitted
    assert index.training_samples == len(data.train.sample_ids)
    query = data.train.inputs[0]
    result = index.search(query, media_sha256="f" * 64)
    assert 1 <= len(result.references) <= 3
    assert all(r.sector == query.sector for r in result.references)
    assert all(r.technical_format == "portrait_short_le60" for r in result.references)
    assert result.criterion == "cosine_minilm_speech_same_sector_technical_format"
    assert result.model_artifact_sha256 == "a" * 64
    serialized = json.dumps(result.model_dump(mode="json"))
    assert not any(term in serialized for term in ("view_count", "text_embedding", "transcript"))


def test_wrong_training_ids_fail_before_any_evidence_is_opened(context, monkeypatch):
    settings, root, _, data, artifact = context
    opened, _ = guard_nontrain(context, monkeypatch)
    artifact.training_sample_ids += (data.validation.sample_ids[0],)
    with pytest.raises(ExperimentError):
        load_training_index(settings, root, minimum_similarity=0.5)
    assert not opened


@pytest.mark.parametrize("partition", ["validation", "test"])
def test_redirected_train_entry_is_rejected_before_read(context, monkeypatch, partition):
    settings, root, entries, data, _ = context
    train_id = data.train.sample_ids[0]
    other = next(r.sample_id for r in data.manifest.assignments if r.partition == partition)
    entries[train_id]["features_ref"] = entries[other]["features_ref"]
    (settings.cohort_dir / "evidence-index.json").write_text(json.dumps(entries))
    guard_nontrain(context, monkeypatch)
    with pytest.raises(ExperimentError):
        load_training_index(settings, root, minimum_similarity=0.5)


def test_split_digest_binds_inputs_even_with_local_metadata_rehashed(context):
    settings, root, _, _, artifact = context
    artifact.train_split_sha256 = "b" * 64
    with pytest.raises(ExperimentError):
        load_training_index(settings, root, minimum_similarity=0.5)


def test_no_speech_or_zero_embedding_produces_empty_references(context):
    settings, root, _, data, _ = context
    index = load_training_index(settings, root, minimum_similarity=0.5)
    missing = data.train.inputs[0].model_copy(
        update={"text_status": "no_audio_stream", "text_embedding": None}
    )
    assert (
        index.search(missing, media_sha256="f" * 64).reason_code == "speech_embedding_unavailable"
    )
    zero = data.train.inputs[0].model_copy(update={"text_embedding": (0.0,) * 384})
    assert index.search(zero, media_sha256="f" * 64).reason_code == "zero_query_embedding"


def test_recognized_exact_copy_is_excluded_and_ties_are_stable(context):
    settings, root, _, data, _ = context
    index = load_training_index(settings, root, minimum_similarity=0.5)
    sample = data.train.sample_ids[0]
    reference = next(r for r in data.manifest.assignments if r.sample_id == sample)
    query = data.train.inputs[0]
    first = index.search(query, media_sha256=reference.media_sha256)
    second = index.search(query, media_sha256=reference.media_sha256)
    assert first == second
    assert sample not in [r.sample_id for r in first.references]
    # The public fixture gives all eligible vectors the same direction.
    ids = [r.sample_id for r in first.references]
    assert ids == sorted(ids)
    assert all(np.isclose(r.similarity, 1.0) for r in first.references)


def test_semantic_format_has_no_fallback_to_technical_format(context):
    settings, root, _, data, _ = context
    index = load_training_index(settings, root, minimum_similarity=0.5)
    result = index.search(data.train.inputs[0], media_sha256="f" * 64, semantic_format="tutorial")
    assert result.references == ()
    assert result.reason_code == "semantic_format_not_available"


def test_known_duplicate_group_is_excluded_even_if_exact_copy_has_no_embedding(context):
    settings, root, _, data, _ = context
    index = load_training_index(settings, root, minimum_similarity=0.5)
    a = index._entries[0]
    b = next(e for e in index._entries[1:] if e.metadata.sector == a.metadata.sector)
    recognized = replace(b, metadata=b.metadata.model_copy(update={"duplicate_group": "copy"}))
    # A is known in train metadata, but absent from the eligible embedding index.
    narrowed = replace(
        index,
        _entries=(recognized,),
        _copy_groups=((a.metadata.media_sha256, "copy"), (b.metadata.media_sha256, "copy")),
    )
    query = data.train.inputs[data.train.sample_ids.index(a.metadata.sample_id)]
    result = narrowed.search(query, media_sha256=a.metadata.media_sha256)
    assert result.references == ()
    assert result.reason_code == "no_matching_training_reference"


def test_cosine_ranking_and_threshold_do_not_fallback_across_sectors(context):
    settings, root, _, data, _ = context
    index = load_training_index(settings, root, minimum_similarity=0.5)
    a = index._entries[0]
    peers = [e for e in index._entries if e.metadata.sector == a.metadata.sector][:3]
    other = next(e for e in index._entries if e.metadata.sector != a.metadata.sector)
    first = (1.0,) + (0.0,) * 383
    second = (0.6, 0.8) + (0.0,) * 382
    negative = (-1.0,) + (0.0,) * 383
    narrowed = replace(
        index,
        _entries=tuple(replace(e, vector=v) for e, v in zip(peers, (first, second, negative)))
        + (replace(other, vector=first),),
    )
    query = data.train.inputs[data.train.sample_ids.index(a.metadata.sample_id)].model_copy(
        update={"text_embedding": first}
    )
    result = narrowed.search(query, media_sha256="f" * 64)
    assert [r.sample_id for r in result.references] == [e.metadata.sample_id for e in peers[:2]]
    assert [r.similarity for r in result.references] == pytest.approx([1.0, 0.6])
    assert other.metadata.sample_id not in [r.sample_id for r in result.references]


def test_below_threshold_returns_empty_without_weak_matches(context):
    settings, root, _, data, _ = context
    index = load_training_index(settings, root, minimum_similarity=0.5)
    query = data.train.inputs[0].model_copy(update={"text_embedding": (1.0,) + (0.0,) * 383})
    result = index.search(query, media_sha256="f" * 64)
    assert result.references == ()
    assert result.reason_code == "no_matching_training_reference"


@pytest.mark.parametrize("kind", ["absolute", "escape", "symlink_to_test"])
def test_unsafe_or_aliased_train_path_is_rejected_before_read(context, monkeypatch, kind):
    settings, root, entries, data, _ = context
    train_id = data.train.sample_ids[0]
    if kind == "absolute":
        entries[train_id]["features_ref"] = str(root / entries[train_id]["features_ref"])
    elif kind == "escape":
        entries[train_id]["features_ref"] = "../outside-canary.json"
    else:
        sample = next(r.sample_id for r in data.manifest.assignments if r.partition == "test")
        alias = root / "training-alias.json"
        alias.symlink_to(root / entries[sample]["features_ref"])
        entries[train_id]["features_ref"] = str(alias.relative_to(root))
    (settings.cohort_dir / "evidence-index.json").write_text(json.dumps(entries))
    guard_nontrain(context, monkeypatch)
    with pytest.raises(ExperimentError):
        load_training_index(settings, root, minimum_similarity=0.5)


@pytest.mark.parametrize("threshold", [-0.1, 1.1, float("nan"), True])
def test_similarity_threshold_must_be_explicit_and_valid(context, threshold):
    settings, root, *_ = context
    with pytest.raises(ExperimentError):
        load_training_index(settings, root, minimum_similarity=threshold)

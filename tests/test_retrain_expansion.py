from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from scripts.empirical_baseline import TrainingTarget
from scripts.experiment_a_data import DevelopmentSplit
from scripts.retrain_expansion import FIXED_TAIL, compare, publish, subset
from tests.test_experiment_a_data import development_fixture


def test_recognized_variants_group_transitively_and_refuse_unknown_relations():
    from scripts.retrain_expansion import recognized_variant_groups

    def entry(vid, target=None):
        ann = {"decision": "included"}
        if target is not None:
            ann["possible_variant_of"] = target
        return {"video_id": vid, "review": ann}

    videos = [entry("a"), entry("b", "a"), entry("c", "b"), entry("other")]
    groups = recognized_variant_groups(videos)
    assert set(groups) == {"a", "b", "c"} and len(set(groups.values())) == 1
    assert recognized_variant_groups(list(reversed(videos))) == groups
    with pytest.raises(ValueError, match="invalid_assisted_variant_relation"):
        recognized_variant_groups([entry("a", "reserved_or_unknown")])


def test_recognized_variant_crossing_new_hash_partitions_is_rejected():
    import hashlib

    from scripts.channel_partitions import (
        append_development_partitions,
        create_partitions,
        new_channel_partition,
    )
    from scripts.retrain_expansion import recognized_variant_groups
    from tests.test_channel_partitions import references

    channels = {}
    for i in range(100):
        ch = f"fresh_channel_{i}"
        channels.setdefault(new_channel_partition(ch), ch)
    videos = [
        {"video_id": "fresh_a", "review": {"decision": "included"}},
        {
            "video_id": "fresh_b",
            "review": {"decision": "included", "possible_variant_of": "fresh_a"},
        },
    ]
    groups = recognized_variant_groups(videos)
    rows = [
        {
            "sample_id": vid,
            "channel_id": channels[part],
            "sector": "moda",
            "media_sha256": hashlib.sha256(vid.encode()).hexdigest(),
            "duplicate_group": groups[vid],
        }
        for vid, part in (("fresh_a", "train"), ("fresh_b", "validation"))
    ]
    with pytest.raises(ValueError, match="duplicate_crosses_frozen_partition"):
        append_development_partitions(create_partitions(references()), rows)


def test_comparison_uses_identical_original_rows_and_reports_new_validation_separately():
    old = development_fixture()
    extra = DevelopmentSplit(
        partition="validation",
        sample_ids=("zz_new",),
        channel_ids=("new_channel",),
        inputs=(old.validation.inputs[0],),
        targets=(TrainingTarget(sample_id="zz_new", view_count=1_000_000),),
    )
    val = DevelopmentSplit(
        partition="validation",
        sample_ids=old.validation.sample_ids + extra.sample_ids,
        channel_ids=old.validation.channel_ids + extra.channel_ids,
        inputs=old.validation.inputs + extra.inputs,
        targets=old.validation.targets + extra.targets,
    )
    expanded = replace(old, validation=val)
    bundle = SimpleNamespace(
        predict_logs=lambda rows, **kw: np.tile(np.log1p([[10.0, 1000.0, 10000.0]]), (len(rows), 1))
    )
    report = compare(old, expanded, bundle, bundle)
    assert report["groups"]["original_validation"]["samples"] == len(old.validation.inputs)
    assert report["groups"]["new_validation"]["samples"] == 1
    assert report["groups"]["all_validation"]["samples"] == len(val.inputs)
    assert report["fixed_original_train_tail_thresholds"] == FIXED_TAIL
    assert not report["test_evaluated"] and report["validation_used_for_selection"]
    for group in report["groups"].values():
        assert set(group["models"]) == {"A_original", "B0_original", "A_expanded", "B0_expanded"}
    assert subset(old.train, set(old.train.sample_ids)) == old.train
    assert subset(old.validation, {"absent"}) is None


def test_changed_original_training_outcome_is_rejected_by_comparison():
    old = development_fixture()
    targets = (old.train.targets[0].model_copy(update={"view_count": 999}),) + old.train.targets[1:]
    changed = replace(old, train=old.train.model_copy(update={"targets": targets}))
    with pytest.raises(ValueError, match="original_development_changed"):
        compare(old, changed, None, None)


def test_release_refuses_incomplete_expansion_without_creating_directory(tmp_path, monkeypatch):
    videos = [
        {
            "video_id": f"new{i}",
            "channel_id": f"new_channel{i}",
            "review": {"decision": "included", "sector": "moda" if i % 2 else "beleza"},
        }
        for i in range(98)
    ]
    monkeypatch.setattr(
        "scripts.retrain_expansion.load_state",
        lambda *a: (SimpleNamespace(records=range(200)), {}, {}, {"videos": videos}),
    )
    out = tmp_path / "not-created"
    with pytest.raises(ValueError, match="expansion_requires_200_plus_50_per_sector"):
        publish(Path("synthetic"), Path("synthetic"), out)
    assert not out.exists()


def test_runtime_guard_blocks_test_files_and_mixed_parent_files(tmp_path):
    import json

    from scripts.channel_partitions import create_partitions, save_new_json
    from scripts.private_checkpoint import save
    from scripts.retrain_expansion import reserved_guard
    from tests.test_channel_partitions import references

    parent = tmp_path / "parent"
    parent.mkdir()
    manifest = create_partitions(references())
    save_new_json(parent / "partitions.json", manifest)
    index = {
        r.sample_id: {
            "features_ref": f"evidence/{r.sample_id}/features.json",
            "run_ref": f"evidence/{r.sample_id}/run.json",
        }
        for r in manifest.assignments
    }
    save(parent / "evidence-index.json", index)
    test = next(r for r in manifest.assignments if r.partition == "test")
    with reserved_guard(parent, tmp_path):
        for path in (
            parent / "records.json",
            parent / "predictor-inputs.json",
            tmp_path / index[test.sample_id]["features_ref"],
            tmp_path / index[test.sample_id]["run_ref"],
        ):
            with pytest.raises(ValueError, match="reserved_evidence_access_forbidden"):
                path.read_bytes()
        assert (
            json.loads((parent / "partitions.json").read_bytes())["manifest_sha256"]
            == manifest.manifest_sha256
        )


def test_staging_removes_partial_bundle_and_supports_clean_retry(tmp_path):
    from scripts.retrain_expansion import staged_publication

    out = tmp_path / "cohort"
    with pytest.raises(RuntimeError, match="synthetic failure"), staged_publication(out) as stage:
        (stage / "cohort.json").write_text("synthetic")
        raise RuntimeError("synthetic failure")
    assert not out.exists() and list(tmp_path.iterdir()) == []
    with staged_publication(out) as stage:
        (stage / "cohort.json").write_text("complete")
    assert (out / "cohort.json").read_text() == "complete"
    with pytest.raises(ValueError, match="output_already_exists"), staged_publication(out) as stage:
        (stage / "cohort.json").write_text("replacement")
    assert (out / "cohort.json").read_text() == "complete"


def test_annotation_uses_strict_confirmations_and_bound_receipt():
    from scripts.channel_partitions import digest
    from scripts.retrain_expansion import check_annotation

    ann = {
        "video_id": "synthetic",
        "image_review_performed": True,
        "transcript_review_performed": True,
        "human_review": False,
        "contact_sheet_sha256": "a" * 64,
    }
    check_annotation({"video_id": "synthetic", "review": ann, "review_receipt_sha256": digest(ann)})
    for change in (
        {"image_review_performed": "yes"},
        {"transcript_review_performed": 1},
        {"contact_sheet_sha256": "invalid"},
        {"video_id": "different"},
    ):
        altered = ann | change
        with pytest.raises(ValueError, match="assisted_review_provenance_missing"):
            check_annotation(
                {
                    "video_id": "synthetic",
                    "review": altered,
                    "review_receipt_sha256": digest(altered),
                }
            )
    with pytest.raises(ValueError, match="assisted_review_provenance_missing"):
        check_annotation(
            {"video_id": "synthetic", "review": ann, "review_receipt_sha256": "f" * 64}
        )


def test_synthetic_300_publication_is_complete_and_never_opens_old_test(tmp_path, monkeypatch):
    from scripts.channel_partitions import digest, load_partitions
    from scripts.observed_baseline import CuratedReference, freeze_cohort, publish_baseline
    from scripts.private_checkpoint import file_hash, save
    from scripts.retrain_expansion import publish, reserved_guard
    from scripts.training_manifest import TrainingReference
    from tests.test_training_manifest import fixture

    monkeypatch.chdir(tmp_path)
    parent = tmp_path / "data/private/parent"
    pool = tmp_path / "data/private/pool"
    pool.mkdir(parents=True)
    records = []
    outcomes = {}
    index = {}
    videos = []
    sources = []
    core = None
    for i in range(300):
        row, features, run, core = fixture(i)
        features.update(asr_language="pt", image_embedding=[0.2] * 512)
        folder = tmp_path / "data/private/evidence" / row["sample_id"]
        folder.mkdir(parents=True)
        fp, rp = folder / "features.json", folder / "run.json"
        save(fp, features)
        save(rp, run)
        ann = {
            "decision": "included",
            "sector": row["sector"],
            "video_id": row["sample_id"],
            "reason": "entirely synthetic fixture, no real perception claim",
            "image_review_performed": True,
            "transcript_review_performed": True,
            "human_review": False,
            "contact_sheet_sha256": "c" * 64,
            "features_sha256": file_hash(fp),
            "run_sha256": file_hash(rp),
        }
        row.update(
            features_sha256=file_hash(fp),
            run_sha256=file_hash(rp),
            curation_evidence_sha256=digest(ann),
        )
        reference = TrainingReference.model_validate(row)
        entry = {
            "video_id": row["sample_id"],
            "channel_id": row["channel_id"],
            "status": "completed",
            "cleanup": True,
            "media_sha256": row["media_sha256"],
            "features_sha256": file_hash(fp),
            "run_sha256": file_hash(rp),
            "features_ref": str(fp.relative_to(tmp_path)),
            "run_ref": str(rp.relative_to(tmp_path)),
            "review": ann,
            "review_receipt_sha256": digest(ann),
        }
        if i < 200:
            records.append(reference.model_dump(include=set(CuratedReference.model_fields)))
            outcomes[row["sample_id"]] = i
            index[row["sample_id"]] = {
                "features_ref": entry["features_ref"],
                "run_ref": entry["run_ref"],
                "curation": ann,
            }
        else:
            videos.append(entry)
            sources.append(
                {
                    "audit": run["source"]["audit"],
                    "target": run["source"]["target"],
                    "curation": {"youtube_license": "youtube"},
                }
            )
    freeze_cohort(records, parent, source_snapshot_sha256="a" * 64)
    original = load_partitions(parent / "partitions.json")
    publish_baseline(
        parent,
        [
            {"sample_id": r.sample_id, "view_count": outcomes[r.sample_id]}
            for r in original.assignments
            if r.partition == "train"
        ],
    )
    save(parent / "evidence-index.json", index)
    save(parent / "extractor-config.json", core)
    from scripts.channel_partitions import new_channel_partition

    save(
        pool / "candidates.json",
        {
            "records": sources,
            "channel_allocation": {
                r["audit"]["channel_id"]: new_channel_partition(r["audit"]["channel_id"])
                for r in sources
            },
        },
    )
    (pool / "extraction").mkdir()
    from scripts.observed_baseline import CohortRelease

    release = CohortRelease.model_validate_json((parent / "cohort.json").read_bytes())
    save(
        pool / "extraction/checkpoint.json",
        {
            "selection_sha256": file_hash(pool / "candidates.json"),
            "parent_sha256": release.release_sha256,
            "config": core,
            "videos": videos,
            "halt_reason": None,
            "elapsed_seconds": 1.0,
        },
    )
    monkeypatch.setattr("scripts.expansion_media.configuration", lambda *a: core)
    monkeypatch.setattr("scripts.diagnose_m1.check_extractor_runtime", lambda *a: None)
    out = pool / "released"
    with reserved_guard(parent, tmp_path):
        data, provenance = publish(parent, pool, out)
    assert provenance["new_references"] == 100 and not provenance["test_evidence_opened"]
    assert len(data.manifest.assignments) == 300
    assert [r for r in data.manifest.assignments if r.partition == "test"] == [
        r for r in original.assignments if r.partition == "test"
    ]
    assert not (out / "records.json").exists() and not (out / "predictor-inputs.json").exists()
    assert not list(pool.glob(".expansion-stage-*"))

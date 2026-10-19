from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from scripts.empirical_baseline import TrainingTarget
from scripts.experiment_a_data import DevelopmentSplit
from scripts.retrain_expansion import FIXED_TAIL, compare, publish, subset
from tests.test_experiment_a_data import development_fixture


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

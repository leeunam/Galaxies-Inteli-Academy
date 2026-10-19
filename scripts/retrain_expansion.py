"""Publish the append-only cohort and compare B0/A using development evidence only."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import math
import os
import re
import tempfile
from pathlib import Path
from unittest.mock import patch

import numpy as np

from scripts.channel_partitions import (
    Reference,
    append_development_partitions,
    digest,
    load_partitions,
    save_new_json,
)
from scripts.diagnose_m1 import error_slice, load_diagnostic_data
from scripts.expansion_media import load_state, validate_reviews
from scripts.experiment_a_artifact import load_bundle
from scripts.experiment_a_data import DevelopmentSplit
from scripts.experiment_a_metrics import evaluate_development
from scripts.observed_baseline import (
    CohortRelease,
    CuratedReference,
    TrainLabels,
    load_observed_baseline,
    observation_digest,
    publish_baseline,
)
from scripts.private_checkpoint import file_hash, private_path, save
from scripts.train_experiment_a import train_experiment
from scripts.training_manifest import TrainingReference, validate_feature_evidence

FIXED_TAIL = {"moda": 6403.5, "beleza": 33835.30000000001}


def check_annotation(entry):
    ann = entry["review"]
    if (
        ann.get("image_review_performed") is not True
        or ann.get("transcript_review_performed") is not True
        or ann.get("human_review") is not False
        or not re.fullmatch(r"[0-9a-f]{64}", ann.get("contact_sheet_sha256", ""))
        or ann.get("video_id") != entry["video_id"]
        or entry.get("review_receipt_sha256") != digest(ann)
    ):
        raise ValueError("assisted_review_provenance_missing")


@contextlib.contextmanager
def staged_publication(output):
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".expansion-stage-", dir=output.parent) as temporary:
        stage = Path(temporary)
        yield stage
        if output.exists():
            raise ValueError("output_already_exists")
        os.rename(stage, output)


@contextlib.contextmanager
def reserved_guard(parent, root):
    manifest = load_partitions(parent / "partitions.json")
    index = json.loads((parent / "evidence-index.json").read_bytes())
    forbidden = {(parent / name).resolve() for name in ("records.json", "predictor-inputs.json")}
    for row in manifest.assignments:
        if row.partition == "test":
            forbidden.update(
                (root / index[row.sample_id][key]).resolve() for key in ("features_ref", "run_ref")
            )
    original = Path.open

    def guarded(path, *a, **kw):
        if path.resolve() in forbidden:
            raise ValueError("reserved_evidence_access_forbidden")
        return original(path, *a, **kw)

    with patch.object(Path, "open", guarded):
        yield


def publish(parent, pool, output):
    root = Path.cwd()
    release, plan, core, state = load_state(pool, parent)
    sectors, _ = validate_reviews(state["videos"])
    if len(release.records) != 200 or dict(sectors) != {"moda": 50, "beleza": 50}:
        raise ValueError("expansion_requires_200_plus_50_per_sector")
    if (
        state["halt_reason"]
        or state.get("cleanup_pending")
        or any("review" not in v for v in state["videos"])
    ):
        raise ValueError("finish_curation_and_cleanup_before_release")
    if list((root / "data/private/media-temp").glob("galaxies-media-*")) or list(
        (pool / "extraction/temporary-review").glob("*.png")
    ):
        raise ValueError("temporary_media_remaining")
    if output.exists():
        raise ValueError("output_already_exists")
    source = {r["audit"]["video_id"]: r for r in plan["records"]}
    instruction = {
        "source": "explicit_user_instruction_in_this_chat",
        "instruction": "Amplie ate 300, preserve particoes e teste, retreine B0/A e compare antes de B.",
        "scope": "local_extraction_and_training",
        "platform_approval_verified": False,
        "human_review_claimed": False,
    }
    instruction_path = pool / "expansion-operator-instruction.json"
    save(instruction_path, instruction)
    new_records, pointers = [], {}
    for entry in state["videos"]:
        ann = entry["review"]
        if ann["decision"] != "included":
            continue
        vid = entry["video_id"]
        row = source[vid]
        check_annotation(entry)
        fp, rp = (root / entry[k] for k in ("features_ref", "run_ref"))
        fr, rr = fp.read_bytes(), rp.read_bytes()
        if (
            hashlib.sha256(fr).hexdigest() != entry["features_sha256"]
            or hashlib.sha256(rr).hexdigest() != entry["run_sha256"]
        ):
            raise ValueError("new_evidence_changed")
        features, run = json.loads(fr), json.loads(rr)
        if (
            ann["features_sha256"] != entry["features_sha256"]
            or ann["run_sha256"] != entry["run_sha256"]
        ):
            raise ValueError("review_evidence_changed")
        image = features["image_embedding"]
        if len(image) != 512 or not all(math.isfinite(v) for v in image):
            raise ValueError("invalid_image_embedding")
        record = {
            k: row["audit"][k]
            for k in ("channel_id", "source_url", "published_at_utc", "observed_at_utc")
        }
        record.update(
            sample_id=vid,
            sector=ann["sector"],
            media_sha256=entry["media_sha256"],
            acquired_media_sha256=entry["media_sha256"],
            duplicate_group=None,
            **{k: features["properties"][k] for k in ("duration_seconds", "width", "height")},
            spoken_language="pt-BR",
            language_evidence="asr_and_agent_transcript_review",
            content_review="included",
            curation_evidence_sha256=digest(ann),
            youtube_license=row["curation"]["youtube_license"],
            permission_basis="explicit_operator_instruction",
            permission_evidence_sha256=file_hash(instruction_path),
            use_scope="local_extraction_and_training",
            curation_method="automated_assisted_review",
            view_count_observed=row["target"]["view_count_observed"],
            features_sha256=entry["features_sha256"],
            run_sha256=entry["run_sha256"],
            extractor_config_sha256=digest(core),
        )
        record["frozen_observation_sha256"] = observation_digest(
            record, record["view_count_observed"]
        )
        reference = TrainingReference.model_validate(record)
        validate_feature_evidence(reference, fr, rr, core)
        if features["asr_language"] != "pt" or run["source"]["audit"] != row["audit"]:
            raise ValueError("unsupported_curation_evidence")
        new_records.append(reference)
        pointers[vid] = {
            "features_ref": entry["features_ref"],
            "run_ref": entry["run_ref"],
            "curation": ann,
        }
    parent_manifest = load_partitions(parent / "partitions.json")
    manifest = append_development_partitions(
        parent_manifest, [r.model_dump(include=set(Reference.model_fields)) for r in new_records]
    )
    metadata = sorted(
        [r.model_dump() for r in release.records]
        + [r.model_dump(include=set(CuratedReference.model_fields)) for r in new_records],
        key=lambda r: r["sample_id"],
    )
    body = release.model_dump(exclude={"records", "release_sha256"}) | {
        "records": metadata,
        "source_snapshot_sha256": file_hash(pool / "candidates.json"),
    }
    expanded_release = CohortRelease.model_validate_json(
        json.dumps(body | {"release_sha256": digest(body)})
    )
    old_index = json.loads((parent / "evidence-index.json").read_bytes())
    load_observed_baseline(parent)
    if set(old_index) != {r.sample_id for r in release.records}:
        raise ValueError("parent_evidence_index_mismatch")
    labels = TrainLabels.model_validate_json((parent / "train-targets.json").read_bytes())
    train_ids = {r.sample_id for r in manifest.assignments if r.partition == "train"}
    targets = [t.model_dump() for t in labels.targets] + [
        {"sample_id": r.sample_id, "view_count": r.view_count_observed}
        for r in new_records
        if r.sample_id in train_ids
    ]
    with staged_publication(output) as staging:
        output = staging
        save_new_json(output / "cohort.json", expanded_release)
        save_new_json(output / "partitions.json", manifest)
        save(output / "evidence-index.json", old_index | pointers)
        save(output / "extractor-config.json", core)
        baseline = publish_baseline(output, targets)
        data, opened = load_diagnostic_data(output, root)
        provenance = {
            "parent_cohort_sha256": release.release_sha256,
            "parent_partition_sha256": parent_manifest.manifest_sha256,
            "new_cohort_sha256": expanded_release.release_sha256,
            "new_partition_sha256": manifest.manifest_sha256,
            "baseline_sha256": baseline.artifact_sha256,
            "new_references": len(new_records),
            "partition_support": [s.model_dump() for s in manifest.support],
            "development_evidence_files_opened": len(opened),
            "test_evidence_opened": False,
            "test_predicted": False,
            "producer_sha256": file_hash(Path(__file__)),
        }
        save(output / "expansion-provenance.json", provenance)
    return data, provenance


def subset(split, selected):
    indices = [i for i, sample in enumerate(split.sample_ids) if sample in selected]
    if not indices:
        return None
    return DevelopmentSplit(
        partition=split.partition,
        sample_ids=tuple(split.sample_ids[i] for i in indices),
        channel_ids=tuple(split.channel_ids[i] for i in indices),
        inputs=tuple(split.inputs[i] for i in indices),
        targets=tuple(split.targets[i] for i in indices),
    )


def baseline_logs(baseline, inputs):
    stats = {s.sector: s for s in baseline.sectors}
    return np.asarray(
        [
            [stats[p.sector].q10_log1p, stats[p.sector].q50_log1p, stats[p.sector].q90_log1p]
            for p in inputs
        ]
    )


def compare(old_data, new_data, old_bundle, new_bundle):
    old_ids = set(old_data.validation.sample_ids)
    original = subset(new_data.validation, old_ids)
    if (
        original != old_data.validation
        or subset(new_data.train, set(old_data.train.sample_ids)) != old_data.train
    ):
        raise ValueError("original_development_changed")
    new_ids = set(new_data.validation.sample_ids) - old_ids
    result = {
        "schema_version": "expansion300-comparison-v1",
        "test_evaluated": False,
        "validation_used_for_selection": True,
        "causal_effect_of_data_isolated": False,
        "fixed_original_train_tail_thresholds": FIXED_TAIL,
        "groups": {},
    }
    for name, split in [
        ("original_validation", original),
        ("new_validation", subset(new_data.validation, new_ids)),
        ("all_validation", new_data.validation),
    ]:
        if split is None:
            result["groups"][name] = {"status": "not_estimable", "samples": 0}
            continue
        actual = np.asarray([t.view_count for t in split.targets], dtype=float)
        channels = np.asarray(split.channel_ids)
        high = np.asarray(
            [value >= FIXED_TAIL[p.sector] for value, p in zip(actual, split.inputs, strict=True)]
        )
        entries = {}
        for model, raw, predictive in (
            ("B0_original", baseline_logs(old_data.baseline, split.inputs), False),
            ("A_original", old_bundle.predict_logs(split.inputs, repaired=False), True),
            ("B0_expanded", baseline_logs(new_data.baseline, split.inputs), False),
            ("A_expanded", new_bundle.predict_logs(split.inputs, repaired=False), True),
        ):
            served = raw.copy()
            if predictive:
                served[:, 0], served[:, 2] = raw.min(axis=1), raw.max(axis=1)
            entries[model] = {
                "metrics": evaluate_development(split, raw, repair=predictive),
                "range_kind": "estimated_predictive_not_calibrated"
                if predictive
                else "descriptive_training_sector_range",
                "fixed_high_reach": error_slice(actual[high], served[high], channels[high]),
                "other_rows": error_slice(actual[~high], served[~high], channels[~high]),
            }
        result["groups"][name] = {
            "samples": len(split.inputs),
            "channels": len(set(split.channel_ids)),
            "models": entries,
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["publish", "train", "compare"])
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--pool", type=Path, required=True)
    parser.add_argument("--cohort-dir", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument(
        "--old-model-dir", type=Path, default=Path("artifacts/issue-3-experimento-a-v1")
    )
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.operation in ("train", "compare") and args.model_dir is None:
        parser.error("--model-dir is required for train/compare")
    if args.operation == "compare" and args.report is None:
        parser.error("--report is required for compare")
    with reserved_guard(args.parent, Path.cwd()):
        execute(args)


def execute(args):
    root = Path.cwd()
    pool = private_path(args.pool, root)
    cohort = private_path(args.cohort_dir, root)
    if args.operation == "publish":
        _, provenance = publish(args.parent, pool, cohort)
        print(json.dumps(provenance))
        return
    data, opened = load_diagnostic_data(cohort, root)
    if args.operation == "train":
        bundle, report = train_experiment(
            data, args.model_dir, progress=lambda t: print(json.dumps(t), flush=True)
        )
        print(
            json.dumps(
                {
                    "artifact_sha256": bundle.artifact.artifact_sha256,
                    "validation_mae": report["metrics"]["A_M1"]["mae_log_macro_channel"],
                    "test_opened": False,
                }
            )
        )
        return
    if args.report.exists():
        raise ValueError("comparison_output_already_exists")
    old_data, _ = load_diagnostic_data(args.parent, root)
    old = load_bundle(
        args.old_model_dir,
        expected_extractor_config=old_data.extractor_config,
        expected_partition_sha256=old_data.manifest.manifest_sha256,
        expected_cohort_sha256=old_data.cohort_sha256,
    )
    new = load_bundle(
        args.model_dir,
        expected_extractor_config=data.extractor_config,
        expected_partition_sha256=data.manifest.manifest_sha256,
        expected_cohort_sha256=data.cohort_sha256,
    )
    report = compare(old_data, data, old, new)
    report["development_evidence_files_opened"] = opened
    save(private_path(args.report, root), report)
    print(
        json.dumps(
            {
                name: {
                    m: v["metrics"]["mae_log_macro_channel"]
                    for m, v in group.get("models", {}).items()
                }
                for name, group in report["groups"].items()
            }
        )
    )


if __name__ == "__main__":
    main()

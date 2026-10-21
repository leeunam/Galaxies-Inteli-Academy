"""B with released local VLM: the same twelve fits, isolated bundle and paired validation."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
from catboost import CatBoostRegressor, Pool

from scripts.channel_partitions import ExperimentError, digest
from scripts.diagnose_m1 import error_slice, load_diagnostic_data
from scripts.experiment_a_artifact import load_bundle as load_a
from scripts.experiment_a_metrics import (
    QUANTILES,
    channel_weights,
    checked_logs,
    evaluate_development,
    repair_quantiles,
    selection_score,
)
from scripts.experiment_b_artifact import load_bundle as load_cached
from scripts.experiment_b_vlm_artifact import (
    SearchProtocol,
    Trial,
    load_bundle,
    save_bundle,
    source_hashes,
)
from scripts.experiment_b_vlm_data import (
    categorical_indices,
    feature_matrix,
    feature_names,
    load_data,
    split_digest,
    validate_data,
)
from scripts.private_checkpoint import private_path, save
from scripts.retrain_expansion import FIXED_TAIL, reserved_guard, subset
from scripts.train_experiment_b import compare as compare_cached


def train_experiment(data, directory, *, progress=None):
    validate_data(data)
    if Path(directory).exists():
        raise ExperimentError("output_already_exists")
    protocol = SearchProtocol()
    base = data.base
    train = Pool(
        feature_matrix(data.train, data.release),
        label=np.log1p([t.view_count for t in base.train.targets]),
        cat_features=list(categorical_indices(data.release)),
        feature_names=list(feature_names(data.release)),
    )
    y = np.log1p([t.view_count for t in base.validation.targets])
    validation = Pool(
        feature_matrix(data.validation, data.release),
        label=y,
        weight=channel_weights(base.validation.channel_ids),
        cat_features=list(categorical_indices(data.release)),
        feature_names=list(feature_names(data.release)),
    )
    trials, candidates = [], {}
    for q in QUANTILES:
        for depth in protocol.depths:
            for l2 in protocol.l2_values:
                started = time.monotonic()
                metric = "MAE" if q == 0.5 else f"Quantile:alpha={q}"
                model = CatBoostRegressor(
                    loss_function=f"Quantile:alpha={q}",
                    eval_metric=metric,
                    depth=depth,
                    l2_leaf_reg=l2,
                    learning_rate=protocol.learning_rate,
                    iterations=protocol.iterations,
                    random_seed=protocol.random_seed,
                    task_type=protocol.task_type,
                    thread_count=protocol.thread_count,
                    allow_writing_files=False,
                    nan_mode="Forbidden",
                    verbose=False,
                )
                model.fit(
                    train,
                    eval_set=validation,
                    use_best_model=True,
                    early_stopping_rounds=protocol.early_stopping_rounds,
                )
                prediction = np.asarray(model.predict(validation))
                checked_logs(np.repeat(prediction[:, None], 3, axis=1))
                score = selection_score(y, prediction, base.validation.channel_ids, q)
                if not np.isclose(
                    model.get_best_score()["validation"][metric], score, atol=3e-6, rtol=0
                ):
                    raise ExperimentError("early_stopping_metric_mismatch")
                trial = Trial(
                    quantile=q,
                    depth=depth,
                    l2_leaf_reg=l2,
                    best_iteration=model.get_best_iteration(),
                    tree_count=model.tree_count_,
                    evaluated_iterations=len(
                        next(iter(model.get_evals_result()["validation"].values()))
                    ),
                    validation_score=score,
                    elapsed_seconds=time.monotonic() - started,
                )
                trials.append(trial)
                candidates[(q, depth, l2)] = model
                if progress:
                    progress(trial.model_dump())
    selected = tuple(
        min(
            (t for t in trials if t.quantile == q),
            key=lambda t: (t.validation_score, t.depth, t.l2_leaf_reg),
        )
        for q in QUANTILES
    )
    models = tuple(candidates[(t.quantile, t.depth, t.l2_leaf_reg)] for t in selected)
    raw = np.column_stack([m.predict(validation) for m in models])
    report = {
        "schema_version": "experiment-b-vlm-validation-v1",
        "partition": "validation",
        "final_test_evaluated": False,
        "predictive_quality_validated": False,
        "vlm_used": True,
        "released_vlm_fields": data.release.released_fields,
        "quality_release_sha256": data.release.release_sha256,
        "audio_status_variation_in_training": False,
        "metrics": evaluate_development(base.validation, raw),
        "selected": [t.model_dump() for t in selected],
        "validation_rows": [
            {"sample_id": sample, "raw_log_quantiles": row.tolist()}
            for sample, row in zip(base.validation.sample_ids, raw, strict=True)
        ],
    }
    body = {
        "feature_names": feature_names(data.release),
        "categorical_indices": categorical_indices(data.release),
        "quality_release": data.release.model_dump(),
        "vlm_config": data.vlm_config,
        "vlm_config_sha256": digest(data.vlm_config),
        "data_kind": base.manifest.data_kind,
        "supported_text_statuses": ("extracted",),
        "extractor_config": base.extractor_config,
        "extractor_config_sha256": digest(base.extractor_config),
        "cohort_sha256": base.cohort_sha256,
        "partition_manifest_sha256": base.manifest.manifest_sha256,
        "baseline_sha256": base.baseline.artifact_sha256,
        "train_split_sha256": split_digest(data, "train"),
        "validation_split_sha256": split_digest(data, "validation"),
        "training_sample_ids": base.train.sample_ids,
        "validation_sample_ids": base.validation.sample_ids,
        "runtime_versions": {"catboost": version("catboost"), "numpy": version("numpy")},
        "source_files_sha256": source_hashes(),
        "uv_lock_sha256": hashlib.sha256(Path("uv.lock").read_bytes()).hexdigest(),
        "protocol": protocol.model_dump(),
        "trials": [t.model_dump() for t in trials],
        "selected": [t.model_dump() for t in selected],
    }
    save_bundle(directory, body, models, report)
    reloaded = load_bundle(
        directory,
        expected_extractor_config=base.extractor_config,
        expected_vlm_config=data.vlm_config,
        expected_quality_release_sha256=data.release.release_sha256,
        expected_partition_sha256=base.manifest.manifest_sha256,
        expected_cohort_sha256=base.cohort_sha256,
    )
    if not np.array_equal(raw, reloaded.predict_logs(data.validation, repaired=False)):
        raise ExperimentError("reload_prediction_mismatch")
    return reloaded, report


def compare(data, old_data, full, cached, a300, a200):
    validate_data(data)
    # Reuse the frozen comparator and its exact split/lineage checks.
    report = compare_cached(data.cached, old_data, cached, a300, a200)
    if (
        full.artifact.train_split_sha256 != split_digest(data, "train")
        or full.artifact.validation_split_sha256 != split_digest(data, "validation")
        or full.artifact.quality_release != data.release
        or full.artifact.vlm_config != data.vlm_config
        or full.artifact.cohort_sha256 != data.base.cohort_sha256
        or full.artifact.partition_manifest_sha256 != data.base.manifest.manifest_sha256
        or full.artifact.training_sample_ids != data.base.train.sample_ids
        or full.artifact.validation_sample_ids != data.base.validation.sample_ids
    ):
        raise ExperimentError("comparison_vlm_split_or_release_mismatch")
    report.update(
        schema_version="experiment-b-vlm-comparison-v1",
        vlm_used=True,
        released_vlm_fields=data.release.released_fields,
        quality_release_sha256=data.release.release_sha256,
        input_policy=data.release.input_policy,
        unchanged_b_cache_prefix_columns=905,
    )
    old_ids = set(old_data.validation.sample_ids)
    for name, ids in (
        ("original_validation", old_ids),
        ("new_validation", set(data.base.validation.sample_ids) - old_ids),
        ("all_validation", set(data.base.validation.sample_ids)),
    ):
        split = subset(data.base.validation, ids)
        if split is None:
            continue
        inputs = tuple(
            value
            for sample, value in zip(data.base.validation.sample_ids, data.validation, strict=True)
            if sample in ids
        )
        raw = full.predict_logs(inputs, repaired=False)
        served = repair_quantiles(raw)
        actual = np.asarray([t.view_count for t in split.targets])
        channels = np.asarray(split.channel_ids)
        high = np.asarray(
            [value >= FIXED_TAIL[a.sector] for value, a in zip(actual, split.inputs, strict=True)]
        )
        report["groups"][name]["models"]["B_VLM_300"] = {
            "metrics": evaluate_development(split, raw),
            "range_kind": "estimated_not_calibrated",
            "fixed_high_reach": error_slice(actual[high], served[high], channels[high]),
            "other_rows": error_slice(actual[~high], served[~high], channels[~high]),
        }
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("inspect", "train", "compare"))
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--cohort-dir", type=Path, required=True)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--quality-release", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.operation == "compare" and args.report is None:
        parser.error("--report is required for compare")
    root = Path.cwd()
    with reserved_guard(args.parent, root):
        data, opened = load_data(
            args.parent, args.cohort_dir, args.queue, args.quality_release, root
        )
        if args.operation == "inspect":
            print(
                json.dumps(
                    {
                        "train": len(data.train),
                        "validation": len(data.validation),
                        "columns": len(feature_names(data.release)),
                        "released_vlm_fields": data.release.released_fields,
                        "test_opened": False,
                    }
                )
            )
        elif args.operation == "train":
            bundle, report = train_experiment(
                data, args.model_dir, progress=lambda trial: print(json.dumps(trial), flush=True)
            )
            print(
                json.dumps(
                    {
                        "artifact_sha256": bundle.artifact.artifact_sha256,
                        "validation_mae": report["metrics"]["mae_log_macro_channel"],
                    }
                )
            )
        else:
            if args.report.exists():
                raise ExperimentError("comparison_output_already_exists")
            old, _ = load_diagnostic_data(args.parent, root)

            def a_bundle(path, base):
                return load_a(
                    path,
                    expected_extractor_config=base.extractor_config,
                    expected_partition_sha256=base.manifest.manifest_sha256,
                    expected_cohort_sha256=base.cohort_sha256,
                )

            full = load_bundle(
                args.model_dir,
                expected_extractor_config=data.base.extractor_config,
                expected_vlm_config=data.vlm_config,
                expected_quality_release_sha256=data.release.release_sha256,
                expected_partition_sha256=data.base.manifest.manifest_sha256,
                expected_cohort_sha256=data.base.cohort_sha256,
            )
            cached = load_cached(
                root / "artifacts/issue-4-experimento-b-300-v1",
                expected_extractor_config=data.base.extractor_config,
                expected_partition_sha256=data.base.manifest.manifest_sha256,
                expected_cohort_sha256=data.base.cohort_sha256,
            )
            report = compare(
                data,
                old,
                full,
                cached,
                a_bundle(root / "artifacts/issue-3-experimento-a-300-v1", data.base),
                a_bundle(root / "artifacts/issue-3-experimento-a-v1", old),
            )
            report["development_evidence_unique_paths"] = len(set(opened))
            save(private_path(args.report, root), report)
            print(
                json.dumps(
                    {
                        name: {
                            model: value["metrics"]["mae_log_macro_channel"]
                            for model, value in group.get("models", {}).items()
                        }
                        for name, group in report["groups"].items()
                    }
                )
            )


if __name__ == "__main__":
    main()

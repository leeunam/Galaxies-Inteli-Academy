"""Twelve B-cache fits and a paired development-only comparison; no media or service."""

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
from scripts.experiment_a_artifact import ExperimentArtifact as AArtifact
from scripts.experiment_a_artifact import load_bundle as load_a
from scripts.experiment_a_data import split_digest as a_split_digest
from scripts.experiment_a_metrics import (
    QUANTILES,
    channel_weights,
    checked_logs,
    evaluate_development,
    repair_quantiles,
    selection_score,
)
from scripts.experiment_b_artifact import (
    SearchProtocol,
    Trial,
    load_bundle,
    save_bundle,
    source_hashes,
)
from scripts.experiment_b_data import (
    CATEGORICAL_INDICES,
    FEATURE_NAMES,
    feature_matrix,
    load_data,
    split_digest,
    validate_data,
)
from scripts.private_checkpoint import private_path, save
from scripts.retrain_expansion import FIXED_TAIL, baseline_logs, reserved_guard, subset


def train_experiment(data, directory, *, progress=None):
    validate_data(data)
    if Path(directory).exists():
        raise ExperimentError("output_already_exists")
    protocol = SearchProtocol()
    base = data.base
    train = Pool(
        feature_matrix(data.train),
        label=np.log1p([t.view_count for t in base.train.targets]),
        cat_features=list(CATEGORICAL_INDICES),
        feature_names=list(FEATURE_NAMES),
    )
    y = np.log1p([t.view_count for t in base.validation.targets])
    validation = Pool(
        feature_matrix(data.validation),
        label=y,
        weight=channel_weights(base.validation.channel_ids),
        cat_features=list(CATEGORICAL_INDICES),
        feature_names=list(FEATURE_NAMES),
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
        "schema_version": "experiment-b-cache-validation-v1",
        "partition": "validation",
        "final_test_evaluated": False,
        "predictive_quality_validated": False,
        "vlm_used": False,
        "audio_status_variation_in_training": False,
        "metrics": evaluate_development(base.validation, raw),
        "selected": [t.model_dump() for t in selected],
        "validation_rows": [
            {"sample_id": sample, "raw_log_quantiles": row.tolist()}
            for sample, row in zip(base.validation.sample_ids, raw, strict=True)
        ],
    }
    body = {
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
        expected_partition_sha256=base.manifest.manifest_sha256,
        expected_cohort_sha256=base.cohort_sha256,
    )
    if not np.array_equal(raw, reloaded.predict_logs(data.validation, repaired=False)):
        raise ExperimentError("reload_prediction_mismatch")
    return reloaded, report


def compare(data, old_data, b, a300, a200):
    base = data.base
    if (
        subset(base.train, set(old_data.train.sample_ids)) != old_data.train
        or subset(base.validation, set(old_data.validation.sample_ids)) != old_data.validation
    ):
        raise ExperimentError("original_development_changed")
    for a, expected in ((a300, base), (a200, old_data)):
        if (
            a.artifact.training_sample_ids != expected.train.sample_ids
            or a.artifact.validation_sample_ids != expected.validation.sample_ids
            or a.artifact.train_split_sha256 != a_split_digest(expected.train)
            or a.artifact.validation_split_sha256 != a_split_digest(expected.validation)
            or a.artifact.cohort_sha256 != expected.cohort_sha256
            or a.artifact.partition_manifest_sha256 != expected.manifest.manifest_sha256
        ):
            raise ExperimentError("comparison_a_split_mismatch")
    if b.artifact.train_split_sha256 != split_digest(
        data, "train"
    ) or b.artifact.validation_split_sha256 != split_digest(data, "validation"):
        raise ExperimentError("comparison_b_split_mismatch")
    old_ids = set(old_data.validation.sample_ids)
    new_ids = set(base.validation.sample_ids) - old_ids
    result = {
        "schema_version": "experiment-b-cache-comparison-v1",
        "test_evaluated": False,
        "validation_used_for_selection": True,
        "causal_effect_of_single_modality_isolated": False,
        "vlm_used": False,
        "fixed_high_reach_thresholds": FIXED_TAIL,
        "groups": {},
    }
    for name, ids in (
        ("original_validation", old_ids),
        ("new_validation", new_ids),
        ("all_validation", set(base.validation.sample_ids)),
    ):
        split = subset(base.validation, ids)
        if split is None:
            result["groups"][name] = {"status": "not_estimable", "samples": 0}
            continue
        extras = tuple(
            v for sample, v in zip(base.validation.sample_ids, data.validation) if sample in ids
        )
        actual = np.asarray([t.view_count for t in split.targets])
        channels = np.asarray(split.channel_ids)
        high = np.asarray(
            [v >= FIXED_TAIL[p.sector] for v, p in zip(actual, split.inputs, strict=True)]
        )
        entries = {}
        for model, raw, repair in (
            ("B0_300", baseline_logs(base.baseline, split.inputs), False),
            ("A200", a200.predict_logs(split.inputs, repaired=False), True),
            ("A300", a300.predict_logs(split.inputs, repaired=False), True),
            ("B_cache_300", b.predict_logs(extras, repaired=False), True),
        ):
            served = repair_quantiles(raw) if repair else raw
            entries[model] = {
                "metrics": evaluate_development(split, raw, repair=repair),
                "range_kind": "estimated_not_calibrated" if repair else "descriptive_training",
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
    parser.add_argument("operation", choices=("train", "compare", "inspect"))
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--cohort-dir", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    if args.operation == "compare" and args.report is None:
        parser.error("--report is required for compare")
    with reserved_guard(args.parent, Path.cwd()):
        anchor = AArtifact.model_validate_json(
            Path("artifacts/issue-3-experimento-a-300-v1/artifact.json").read_bytes()
        )
        data, opened = load_data(
            args.cohort_dir,
            Path.cwd(),
            parent=args.parent,
            expected_cohort_sha256=anchor.cohort_sha256,
            expected_partition_sha256=anchor.partition_manifest_sha256,
        )
        if args.operation == "inspect":
            print(
                json.dumps(
                    {
                        "train": len(data.train),
                        "validation": len(data.validation),
                        "columns": len(FEATURE_NAMES),
                        "test_opened": False,
                    }
                )
            )
        elif args.operation == "train":
            bundle, report = train_experiment(
                data, args.model_dir, progress=lambda t: print(json.dumps(t), flush=True)
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
            old, _ = load_diagnostic_data(args.parent, Path.cwd())

            def a_bundle(directory, d):
                return load_a(
                    directory,
                    expected_extractor_config=d.extractor_config,
                    expected_cohort_sha256=d.cohort_sha256,
                    expected_partition_sha256=d.manifest.manifest_sha256,
                )

            b = load_bundle(
                args.model_dir,
                expected_extractor_config=data.base.extractor_config,
                expected_cohort_sha256=data.base.cohort_sha256,
                expected_partition_sha256=data.base.manifest.manifest_sha256,
            )
            report = compare(
                data,
                old,
                b,
                a_bundle(Path("artifacts/issue-3-experimento-a-300-v1"), data.base),
                a_bundle(Path("artifacts/issue-3-experimento-a-v1"), old),
            )
            report["development_evidence_unique_paths"] = len(set(opened))
            save(private_path(args.report, Path.cwd()), report)
            print(
                json.dumps(
                    {
                        g: {
                            m: v["metrics"]["mae_log_macro_channel"]
                            for m, v in row.get("models", {}).items()
                        }
                        for g, row in report["groups"].items()
                    }
                )
            )


if __name__ == "__main__":
    main()

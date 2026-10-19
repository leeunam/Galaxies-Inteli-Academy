"""Bounded, CPU-only experiment A. No test evaluation and no extraction/network calls."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
from catboost import CatBoostError, CatBoostRegressor, Pool
from pydantic import ValidationError

from scripts.channel_partitions import ExperimentError, digest
from scripts.empirical_baseline import estimate_baseline
from scripts.experiment_a_artifact import (
    SearchProtocol,
    Trial,
    load_bundle,
    save_bundle,
    source_hashes,
)
from scripts.experiment_a_data import (
    CATEGORICAL_INDICES,
    FEATURE_NAMES,
    DevelopmentData,
    feature_matrix,
    load_development_data,
    split_digest,
    validate_development_data,
)
from scripts.experiment_a_metrics import (
    QUANTILES,
    channel_weights,
    checked_logs,
    evaluate_development,
    selection_score,
)
from scripts.observed_baseline import read_json


def _baseline_predictions(data, variant):
    rows = []
    for inputs, channel in zip(data.validation.inputs, data.validation.channel_ids, strict=True):
        estimate = estimate_baseline(
            data.baseline, inputs.sector, variant=variant, channel_id=channel
        )
        sector = next(s for s in data.baseline.sectors if s.sector == inputs.sector)
        rows.append([sector.q10_log1p, estimate.central_log1p_views, sector.q90_log1p])
    return rows


def train_experiment(data: DevelopmentData, directory: Path, *, progress=None):
    """Fit only train rows. Validation labels control stopping/choice, never refitting."""
    validate_development_data(data)
    if Path(directory).exists():
        raise ExperimentError("output_already_exists")
    protocol = SearchProtocol()
    supported = tuple(sorted({p.text_status for p in data.train.inputs}))
    train = Pool(
        feature_matrix(data.train.inputs, supported_text_statuses=supported),
        label=[np.log1p(t.view_count) for t in data.train.targets],
        cat_features=list(CATEGORICAL_INDICES),
        feature_names=list(FEATURE_NAMES),
    )
    validation_targets = np.array([np.log1p(t.view_count) for t in data.validation.targets])
    validation = Pool(
        feature_matrix(data.validation.inputs, supported_text_statuses=supported),
        label=validation_targets,
        weight=channel_weights(data.validation.channel_ids),
        cat_features=list(CATEGORICAL_INDICES),
        feature_names=list(FEATURE_NAMES),
    )
    trials, candidates = [], {}
    for quantile in QUANTILES:
        for depth in protocol.depths:
            for l2 in protocol.l2_values:
                started = time.monotonic()
                model = CatBoostRegressor(
                    loss_function=f"Quantile:alpha={quantile}",
                    eval_metric="MAE" if quantile == 0.5 else f"Quantile:alpha={quantile}",
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
                predictions = np.asarray(model.predict(validation), dtype=float)
                checked_logs(np.repeat(predictions[:, None], 3, axis=1))
                score = selection_score(
                    validation_targets, predictions, data.validation.channel_ids, quantile
                )
                metric = "MAE" if quantile == 0.5 else f"Quantile:alpha={quantile}"
                # CatBoost uses float32 labels and a small epsilon in these metrics.
                # Verify that native stopping actually used the macro-channel weights.
                if not np.isclose(
                    model.get_best_score()["validation"][metric], score, atol=3e-6, rtol=0
                ):
                    raise ExperimentError("early_stopping_metric_mismatch")
                trial = Trial(
                    quantile=quantile,
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
                candidates[(quantile, depth, l2)] = model
                if progress is not None:
                    progress(trial.model_dump())
    selected = tuple(
        min(
            (t for t in trials if t.quantile == q),
            key=lambda t: (t.validation_score, t.depth, t.l2_leaf_reg),
        )
        for q in QUANTILES
    )
    models = tuple(candidates[(t.quantile, t.depth, t.l2_leaf_reg)] for t in selected)
    raw = np.column_stack([model.predict(validation) for model in models])
    metrics = {"A_M1": evaluate_development(data.validation, raw)}
    for variant in ("B0", "Bcanal"):
        metrics[variant] = evaluate_development(
            data.validation, _baseline_predictions(data, variant), repair=False
        )
        metrics[variant]["range_kind"] = "descriptive_training_sector_range_not_predictive"
    report = {
        "schema_version": "experiment-a-validation-v1",
        "partition": "validation",
        "data_kind": data.manifest.data_kind,
        "final_test_evaluated": False,
        "predictive_quality_validated": False,
        "coverage_status": "validation_diagnostic_not_calibration_guarantee",
        "selection_before_joint_crossing_repair": True,
        "selected": [t.model_dump() for t in selected],
        "metrics": metrics,
        "validation_rows": [
            {"sample_id": sample_id, "raw_log_quantiles": predictions.tolist()}
            for sample_id, predictions in zip(data.validation.sample_ids, raw, strict=True)
        ],
        "warnings": [
            "convenience_sample",
            "assisted_curation_not_independent_accuracy_audit",
            "platform_approval_not_verified",
            "public_views_not_paid_return",
            "validation_used_for_selection_not_final_evaluation",
            "interval_coverage_not_validated",
        ],
    }
    body = {
        "data_kind": data.manifest.data_kind,
        "supported_text_statuses": supported,
        "extractor_config": data.extractor_config,
        "extractor_config_sha256": digest(data.extractor_config),
        "cohort_sha256": data.cohort_sha256,
        "partition_manifest_sha256": data.manifest.manifest_sha256,
        "baseline_sha256": data.baseline.artifact_sha256,
        "train_split_sha256": split_digest(data.train),
        "validation_split_sha256": split_digest(data.validation),
        "training_sample_ids": data.train.sample_ids,
        "validation_sample_ids": data.validation.sample_ids,
        "runtime_versions": {"catboost": version("catboost"), "numpy": version("numpy")},
        "source_files_sha256": source_hashes(),
        "uv_lock_sha256": hashlib.sha256(
            read_json(Path(__file__).parent.parent / "uv.lock")
        ).hexdigest(),
        "protocol": protocol.model_dump(),
        "trials": [t.model_dump() for t in trials],
        "selected": [t.model_dump() for t in selected],
    }
    bundle = save_bundle(directory, body, models, report)
    reloaded = load_bundle(
        directory,
        expected_extractor_config=data.extractor_config,
        expected_partition_sha256=data.manifest.manifest_sha256,
        expected_cohort_sha256=data.cohort_sha256,
    )
    # Exact parity on the same validation inputs; no predictions on the reserved test.
    if not np.array_equal(
        bundle.predict_logs(data.validation.inputs), reloaded.predict_logs(data.validation.inputs)
    ):
        raise ExperimentError("reload_prediction_mismatch")
    return reloaded, report


def learning_example(data: DevelopmentData):
    examples = {}
    for name in ("train", "validation"):
        split = getattr(data, name)
        value, target = split.inputs[0], split.targets[0]
        label = float(np.log1p(target.view_count))
        examples[name] = {
            "first_four_features": [
                value.sector,
                value.duration_seconds,
                value.aspect_ratio_height_over_width,
                value.text_status,
            ],
            "embedding_dimensions": len(value.text_embedding)
            if value.text_embedding is not None
            else 0,
            "label_in_separate_vector": target.view_count,
            "label_log1p": label,
            "inverse_label_views": float(np.expm1(label)),
        }
    return {
        "columns": len(FEATURE_NAMES),
        "train_rows": len(data.train.inputs),
        "validation_rows": len(data.validation.inputs),
        "examples": examples,
        "test_matrix_created": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort-dir", required=True, type=Path)
    parser.add_argument("--evidence-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--inspect", action="store_true", help="Show one train/validation row, without fitting"
    )
    args = parser.parse_args()
    if not args.inspect and args.output_dir is None:
        parser.error("--output-dir is required unless --inspect")
    try:
        data = load_development_data(args.cohort_dir, evidence_root=args.evidence_root)
        if args.inspect:
            result = learning_example(data)
        else:
            bundle, report = train_experiment(
                data,
                args.output_dir,
                progress=lambda trial: print(json.dumps(trial), file=sys.stderr, flush=True),
            )
            result = {
                "artifact_sha256": bundle.artifact.artifact_sha256,
                "selected": report["selected"],
                "final_test_evaluated": False,
                "validation_mae_log_macro_channel": {
                    name: values["mae_log_macro_channel"]
                    for name, values in report["metrics"].items()
                },
            }
        print(json.dumps(result, indent=2, allow_nan=False))
    except (ExperimentError, ValidationError, CatBoostError, OSError, KeyError, ValueError):
        # Avoid leaking paths, transcriptions, record contents or native library exceptions.
        print(json.dumps({"status": "error", "code": "experiment_a_failed"}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

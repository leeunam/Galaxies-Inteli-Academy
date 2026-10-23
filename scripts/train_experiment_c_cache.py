"""C-cache LightGBM on the exact 905 B-cache inputs; no VLM or final-test access.

The full-VLM synthetic preparation keeps its original guards. This separate
ablation reuses its predefined search recipe without claiming complete C.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Literal

import lightgbm as lgb
import numpy as np
from pydantic import Field, model_validator

from scripts.channel_partitions import (
    Digest,
    ExperimentError,
    FrozenContract,
    Identifier,
    digest,
    load_partitions,
)
from scripts.diagnose_m1 import error_slice
from scripts.experiment_a_artifact import load_bundle as load_a
from scripts.experiment_a_data import split_digest as a_split_digest
from scripts.experiment_a_metrics import (
    QUANTILES,
    channel_weights,
    checked_logs,
    evaluate_development,
    repair_quantiles,
    selection_score,
    views_from_logs,
)
from scripts.experiment_b_artifact import SOURCE_FILES as B_SOURCE_FILES
from scripts.experiment_b_artifact import ExperimentArtifact as BArtifact
from scripts.experiment_b_artifact import load_bundle as load_b
from scripts.experiment_b_artifact import source_hashes as b_source_hashes
from scripts.experiment_b_data import (
    CATEGORICAL_INDICES,
    FEATURE_NAMES,
    feature_matrix,
    load_data,
    split_digest,
    validate_data,
)
from scripts.experiment_c_data import CategoryEncoding
from scripts.retrain_expansion import FIXED_TAIL, reserved_guard, subset

ROOT = Path(__file__).resolve().parents[1]
MODEL_FILES = ("q10.txt", "q50.txt", "q90.txt")
SOURCE_FILES = tuple(
    dict.fromkeys(
        (
            *B_SOURCE_FILES,
            "experiment_c_data.py",
            "train_experiment_c_offline.py",
            "train_experiment_c_cache.py",
        )
    )
)


def source_hashes():
    root = Path(__file__).parent
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in SOURCE_FILES}


def runtime_versions():
    return {name: version(name) for name in ("lightgbm", "numpy")}


class SearchProtocol(FrozenContract):
    num_leaves: tuple[Literal[7], Literal[15]] = (7, 15)
    min_data_in_leaf: tuple[Literal[5], Literal[20]] = (5, 20)
    max_depth: Literal[6] = 6
    lambda_l2: Literal[3] = 3
    learning_rate: Literal[0.05] = 0.05
    iterations: Literal[500] = 500
    early_stopping_rounds: Literal[50] = 50
    seed: Literal[42] = 42
    num_threads: Literal[1] = 1
    selection: Literal["q50_macro_channel_mae_extremes_macro_channel_pinball"] = (
        "q50_macro_channel_mae_extremes_macro_channel_pinball"
    )
    tie_break: Literal["lower_num_leaves_then_lower_min_data_in_leaf"] = (
        "lower_num_leaves_then_lower_min_data_in_leaf"
    )


class Trial(FrozenContract):
    quantile: Literal[0.1, 0.5, 0.9]
    num_leaves: Literal[7, 15]
    min_data_in_leaf: Literal[5, 20]
    best_iteration: int = Field(ge=1, le=500)
    tree_count: int = Field(ge=1, le=500)
    evaluated_iterations: int = Field(ge=1, le=500)
    validation_score: float = Field(ge=0)
    elapsed_seconds: float = Field(ge=0)

    @model_validator(mode="after")
    def integrity(self):
        if not self.tree_count <= self.best_iteration <= self.evaluated_iterations:
            raise ExperimentError("c_trial_iterations_mismatch")
        return self


def trial_key(trial):
    return trial.validation_score, trial.num_leaves, trial.min_data_in_leaf


def model_params(q, leaves, minimum):
    return {
        "objective": "quantile",
        "alpha": q,
        "metric": "None",
        "num_leaves": leaves,
        "min_data_in_leaf": minimum,
        "max_depth": 6,
        "lambda_l2": 3,
        "learning_rate": 0.05,
        "seed": 42,
        "num_threads": 1,
        "device_type": "cpu",
        "deterministic": True,
        "force_col_wise": True,
        "feature_pre_filter": False,
        "verbosity": -1,
    }


def fit_encoding(data):
    validate_data(data)
    rows = feature_matrix(data.train)
    return CategoryEncoding(
        feature_names=FEATURE_NAMES,
        categorical_indices=CATEGORICAL_INDICES,
        categories={
            FEATURE_NAMES[i]: tuple(sorted({row[i] for row in rows})) for i in CATEGORICAL_INDICES
        },
    )


def encoded_matrix(inputs, encoding):
    encoding = CategoryEncoding.model_validate(encoding)
    if (
        encoding.feature_names != FEATURE_NAMES
        or encoding.categorical_indices != CATEGORICAL_INDICES
    ):
        raise ExperimentError("c_cache_encoding_contract_mismatch")
    rows = feature_matrix(inputs)
    if not rows:
        raise ExperimentError("c_cache_empty_matrix")
    for row in rows:
        for index in CATEGORICAL_INDICES:
            vocabulary = encoding.categories[FEATURE_NAMES[index]]
            if row[index] not in vocabulary:
                raise ExperimentError("c_cache_category_without_training_support")
            row[index] = vocabulary.index(row[index])
    matrix = np.asarray(rows, dtype=np.float64)
    if matrix.shape != (len(rows), len(FEATURE_NAMES)) or not np.isfinite(matrix).all():
        raise ExperimentError("c_cache_invalid_matrix")
    return matrix


def pairing(data):
    validate_data(data)
    return {
        "data_kind": data.base.manifest.data_kind,
        "cohort_sha256": data.base.cohort_sha256,
        "partition_manifest_sha256": data.base.manifest.manifest_sha256,
        "baseline_sha256": data.base.baseline.artifact_sha256,
        "train_split_sha256": split_digest(data, "train"),
        "validation_split_sha256": split_digest(data, "validation"),
        "training_sample_ids": data.base.train.sample_ids,
        "validation_sample_ids": data.base.validation.sample_ids,
        "extractor_config": data.base.extractor_config,
    }


def assert_pairing(data, artifact):
    expected = pairing(data)
    actual = {key: getattr(artifact, key) for key in expected}
    if (
        digest(actual) != digest(expected)
        or artifact.final_test_evaluated is not False
        or artifact.vlm_used is not False
        or artifact.feature_names != FEATURE_NAMES
        or artifact.categorical_indices != CATEGORICAL_INDICES
    ):
        raise ExperimentError("c_cache_pairing_mismatch")


class ExperimentArtifact(FrozenContract):
    schema_version: Literal["experiment-c-cache-lightgbm-v1"] = "experiment-c-cache-lightgbm-v1"
    experiment: Literal["C_CACHE_CLIP_AUDIO"] = "C_CACHE_CLIP_AUDIO"
    data_kind: Literal["synthetic", "observed_pilot"]
    run_scope: Literal["cached_non_vlm_development"] = "cached_non_vlm_development"
    final_test_evaluated: Literal[False] = False
    predictive_quality_validated: Literal[False] = False
    vlm_used: Literal[False] = False
    coverage_status: Literal["not_validated"] = "not_validated"
    target_transform: Literal["log1p"] = "log1p"
    target_definition: Literal["public_views_observed_age_30_le_days_lt_37"] = (
        "public_views_observed_age_30_le_days_lt_37"
    )
    repair_policy: Literal["lower_min_raw_upper_max_raw_preserve_q50_v1"] = (
        "lower_min_raw_upper_max_raw_preserve_q50_v1"
    )
    feature_names: tuple[str, ...]
    categorical_indices: tuple[int, ...]
    encoding: CategoryEncoding
    cohort_sha256: Digest
    partition_manifest_sha256: Digest
    baseline_sha256: Digest
    train_split_sha256: Digest
    validation_split_sha256: Digest
    training_sample_ids: tuple[Identifier, ...]
    validation_sample_ids: tuple[Identifier, ...]
    extractor_config: dict
    protocol: SearchProtocol = SearchProtocol()
    trials: tuple[Trial, ...]
    selected: tuple[Trial, ...]
    model_sha256: dict[str, Digest]
    validation_report_sha256: Digest
    runtime_versions: dict[str, str]
    source_files_sha256: dict[str, Digest]
    uv_lock_sha256: Digest
    artifact_sha256: Digest

    @model_validator(mode="after")
    def integrity(self):
        expected = {(q, n, m) for q in QUANTILES for n in (7, 15) for m in (5, 20)}
        if (
            self.feature_names != FEATURE_NAMES
            or self.categorical_indices != CATEGORICAL_INDICES
            or self.encoding.feature_names != self.feature_names
            or self.encoding.categorical_indices != self.categorical_indices
            or len(self.trials) != 12
            or {(t.quantile, t.num_leaves, t.min_data_in_leaf) for t in self.trials} != expected
            or tuple(t.quantile for t in self.selected) != QUANTILES
            or any(
                selected != min((t for t in self.trials if t.quantile == q), key=trial_key)
                for q, selected in zip(QUANTILES, self.selected, strict=True)
            )
            or set(self.model_sha256) != set(MODEL_FILES)
            or set(self.source_files_sha256) != set(SOURCE_FILES)
            or self.artifact_sha256 != digest(self.model_dump(exclude={"artifact_sha256"}))
        ):
            raise ExperimentError("c_artifact_contract_mismatch")
        for ids in (self.training_sample_ids, self.validation_sample_ids):
            if not ids or ids != tuple(sorted(set(ids))):
                raise ExperimentError("c_artifact_sample_ids_mismatch")
        if set(self.training_sample_ids) & set(self.validation_sample_ids):
            raise ExperimentError("c_artifact_sample_ids_mismatch")
        return self


@dataclass(frozen=True)
class ExperimentBundle:
    artifact: ExperimentArtifact
    models: tuple[lgb.Booster, ...]

    def predict_logs(self, inputs, *, repaired=True):
        matrix = encoded_matrix(inputs, self.artifact.encoding)
        raw = checked_logs(np.column_stack([m.predict(matrix, num_threads=1) for m in self.models]))
        return repair_quantiles(raw) if repaired else raw

    def predict_views(self, inputs):
        return views_from_logs(self.predict_logs(inputs))


def load_bundle(directory, *, data):
    validate_data(data)
    directory = Path(directory)
    artifact = ExperimentArtifact.model_validate_json((directory / "artifact.json").read_bytes())
    assert_pairing(data, artifact)
    if (
        artifact.runtime_versions != runtime_versions()
        or artifact.source_files_sha256 != source_hashes()
        or artifact.encoding != fit_encoding(data)
        or artifact.uv_lock_sha256
        != hashlib.sha256(Path(__file__).parent.parent.joinpath("uv.lock").read_bytes()).hexdigest()
    ):
        raise ExperimentError("incompatible_c_artifact")
    if (
        hashlib.sha256((directory / "validation-report.json").read_bytes()).hexdigest()
        != artifact.validation_report_sha256
    ):
        raise ExperimentError("c_validation_report_mismatch")
    models = []
    for name, trial in zip(MODEL_FILES, artifact.selected, strict=True):
        path = directory / name
        if (
            path.stat().st_size > 128 * 1024 * 1024
            or hashlib.sha256(path.read_bytes()).hexdigest() != artifact.model_sha256[name]
        ):
            raise ExperimentError("c_model_checksum_mismatch")
        model = lgb.Booster(model_file=str(path))
        expected = model_params(trial.quantile, trial.num_leaves, trial.min_data_in_leaf)
        if (
            tuple(model.feature_name()) != artifact.feature_names
            or tuple(model.params.get("categorical_feature", ())) != artifact.categorical_indices
            or model.current_iteration() != trial.tree_count
            or any(model.params.get(k) != v for k, v in expected.items() if k != "metric")
        ):
            raise ExperimentError("c_native_model_contract_mismatch")
        models.append(model)
    return ExperimentBundle(artifact, tuple(models))


def _write_new(path, raw):
    with path.open("xb") as handle:
        os.chmod(path, 0o600)
        handle.write(raw)


def train_experiment(data, directory, *, progress=None):
    validate_data(data)
    directory = Path(directory)
    if directory.exists():
        raise ExperimentError("output_already_exists")
    encoding, protocol = fit_encoding(data), SearchProtocol()
    x_train = encoded_matrix(data.train, encoding)
    x_validation = encoded_matrix(data.validation, encoding)
    y_train = np.log1p([t.view_count for t in data.base.train.targets])
    y_validation = np.log1p([t.view_count for t in data.base.validation.targets])
    train = lgb.Dataset(
        x_train,
        label=y_train,
        feature_name=list(encoding.feature_names),
        categorical_feature=list(encoding.categorical_indices),
        free_raw_data=False,
    )
    validation = lgb.Dataset(
        x_validation,
        label=y_validation,
        weight=channel_weights(data.base.validation.channel_ids),
        reference=train,
        free_raw_data=False,
    )
    trials, candidates = [], {}
    for q in QUANTILES:
        # Reuse the shared score on float64 labels. LightGBM internally stores
        # labels/weights as float32; that must not change the selection recipe.
        def metric(predicted, dataset, quantile=q):
            if dataset is not validation:
                raise ExperimentError("c_metric_requires_validation")
            return (
                "macro_channel_selection",
                selection_score(
                    y_validation, predicted, data.base.validation.channel_ids, quantile
                ),
                False,
            )

        for leaves in protocol.num_leaves:
            for minimum in protocol.min_data_in_leaf:
                started, history = time.monotonic(), {}
                model = lgb.train(
                    model_params(q, leaves, minimum),
                    train,
                    num_boost_round=protocol.iterations,
                    valid_sets=[validation],
                    valid_names=["validation"],
                    feval=metric,
                    callbacks=[
                        lgb.early_stopping(protocol.early_stopping_rounds, verbose=False),
                        lgb.record_evaluation(history),
                    ],
                )
                predicted = model.predict(x_validation, num_threads=1)
                checked_logs(np.repeat(predicted[:, None], 3, axis=1))
                score = selection_score(
                    y_validation, predicted, data.base.validation.channel_ids, q
                )
                if not np.isclose(
                    score,
                    model.best_score["validation"]["macro_channel_selection"],
                    atol=1e-12,
                    rtol=0,
                ):
                    raise ExperimentError("c_early_stopping_metric_mismatch")
                trial = Trial(
                    quantile=q,
                    num_leaves=leaves,
                    min_data_in_leaf=minimum,
                    best_iteration=model.best_iteration,
                    tree_count=model.current_iteration(),
                    evaluated_iterations=len(history["validation"]["macro_channel_selection"]),
                    validation_score=score,
                    elapsed_seconds=time.monotonic() - started,
                )
                trials.append(trial)
                candidates[(q, leaves, minimum)] = model
                if progress:
                    progress(trial.model_dump())
    selected = tuple(min((t for t in trials if t.quantile == q), key=trial_key) for q in QUANTILES)
    models = tuple(candidates[(t.quantile, t.num_leaves, t.min_data_in_leaf)] for t in selected)
    raw = np.column_stack([model.predict(x_validation, num_threads=1) for model in models])
    report = {
        "schema_version": "experiment-c-cache-validation-v1",
        "data_kind": data.base.manifest.data_kind,
        "real_results_available": data.base.manifest.data_kind == "observed_pilot",
        "final_test_evaluated": False,
        "partition": "validation",
        "vlm_used": False,
        "validation_used_for_selection": True,
        "range_kind": "estimated_not_calibrated",
        "metrics": evaluate_development(data.base.validation, raw),
        "selected": [t.model_dump() for t in selected],
        "validation_rows": [
            {"sample_id": sample, "raw_log_quantiles": row.tolist()}
            for sample, row in zip(data.base.validation.sample_ids, raw, strict=True)
        ],
    }
    directory.mkdir(parents=True, mode=0o700, exist_ok=False)
    hashes = {}
    for name, model in zip(MODEL_FILES, models, strict=True):
        path = directory / name
        model.save_model(str(path))
        os.chmod(path, 0o600)
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    report_raw = (json.dumps(report, sort_keys=True, allow_nan=False) + "\n").encode()
    _write_new(directory / "validation-report.json", report_raw)
    body = pairing(data) | {
        "feature_names": encoding.feature_names,
        "categorical_indices": encoding.categorical_indices,
        "encoding": encoding,
        "protocol": protocol,
        "trials": tuple(trials),
        "selected": selected,
        "model_sha256": hashes,
        "validation_report_sha256": hashlib.sha256(report_raw).hexdigest(),
        "runtime_versions": runtime_versions(),
        "source_files_sha256": source_hashes(),
        "uv_lock_sha256": hashlib.sha256(
            Path(__file__).parent.parent.joinpath("uv.lock").read_bytes()
        ).hexdigest(),
    }
    body = ExperimentArtifact.model_construct(**body, artifact_sha256="0" * 64).model_dump(
        exclude={"artifact_sha256"}
    )
    artifact = ExperimentArtifact.model_validate_json(
        json.dumps(body | {"artifact_sha256": digest(body)})
    )
    _write_new(directory / "artifact.json", artifact.model_dump_json(indent=2).encode())
    reloaded = load_bundle(directory, data=data)
    if not np.array_equal(raw, reloaded.predict_logs(data.validation, repaired=False)):
        raise ExperimentError("c_reload_prediction_mismatch")
    return reloaded, report


def compare(data, b, c, *, original_validation_ids=None):
    validate_data(data)
    # Require the same cached representation and content before any prediction.
    BArtifact.model_validate(b.artifact)
    ExperimentArtifact.model_validate(c.artifact)
    assert_pairing(data, b.artifact)
    assert_pairing(data, c.artifact)
    lock_hash = hashlib.sha256(
        Path(__file__).parent.parent.joinpath("uv.lock").read_bytes()
    ).hexdigest()
    if (
        b.artifact.source_files_sha256 != b_source_hashes()
        or b.artifact.runtime_versions != {name: version(name) for name in ("catboost", "numpy")}
        or b.artifact.uv_lock_sha256 != lock_hash
        or c.artifact.source_files_sha256 != source_hashes()
        or c.artifact.runtime_versions != runtime_versions()
        or c.artifact.uv_lock_sha256 != lock_hash
        or c.artifact.encoding != fit_encoding(data)
    ):
        raise ExperimentError("incompatible_bc_artifact")
    all_ids = set(data.base.validation.sample_ids)
    old_ids = all_ids if original_validation_ids is None else set(original_validation_ids)
    if not old_ids <= all_ids:
        raise ExperimentError("bc_original_validation_ids_mismatch")
    raw = {
        name: bundle.predict_logs(data.validation, repaired=False)
        for name, bundle in (("B_cache_300", b), ("C_cache_300", c))
    }
    # Validate full row counts/ranges before slicing into comparison groups.
    all_metrics = {
        name: evaluate_development(data.base.validation, values) for name, values in raw.items()
    }
    report = {
        "schema_version": "experiment-bc-cache-comparison-v1",
        "data_kind": data.base.manifest.data_kind,
        "real_results_available": data.base.manifest.data_kind == "observed_pilot",
        "final_test_evaluated": False,
        "validation_used_for_selection": True,
        "causal_effect_of_single_modality_isolated": False,
        "pairing_sha256": digest(pairing(data)),
        "model_artifact_sha256": {
            "B_cache_300": b.artifact.artifact_sha256,
            "C_cache_300": c.artifact.artifact_sha256,
        },
        "fixed_high_reach_thresholds": FIXED_TAIL,
        "models": all_metrics,
        "groups": {},
    }
    for group, ids in (
        ("original_validation", old_ids),
        ("new_validation", all_ids - old_ids),
        ("all_validation", all_ids),
    ):
        split = subset(data.base.validation, ids)
        if split is None:
            report["groups"][group] = {"status": "not_estimable", "samples": 0}
            continue
        mask = np.array([sample in ids for sample in data.base.validation.sample_ids])
        actual = np.asarray([target.view_count for target in split.targets])
        channels = np.asarray(split.channel_ids)
        high = np.asarray(
            [value >= FIXED_TAIL[p.sector] for value, p in zip(actual, split.inputs, strict=True)]
        )
        entries = {}
        for name, values in raw.items():
            selected = values[mask]
            served = repair_quantiles(selected)
            entries[name] = {
                "metrics": evaluate_development(split, selected),
                "range_kind": "estimated_not_calibrated",
                "fixed_high_reach": error_slice(actual[high], served[high], channels[high]),
                "other_rows": error_slice(actual[~high], served[~high], channels[~high]),
            }
        report["groups"][group] = {
            "samples": len(split.inputs),
            "channels": len(set(split.channel_ids)),
            "models": entries,
        }
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--cohort-dir", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--comparison", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.model_dir.exists() or args.comparison.exists():
        raise ExperimentError("c_cache_output_already_exists")
    a_dir = ROOT / "artifacts/issue-3-experimento-a-300-v1"
    b_dir = ROOT / "artifacts/issue-4-experimento-b-300-v1"
    a_metadata = json.loads((a_dir / "artifact.json").read_bytes())
    with reserved_guard(args.parent, ROOT):
        data, opened = load_data(
            args.cohort_dir,
            ROOT,
            parent=args.parent,
            expected_cohort_sha256=a_metadata["cohort_sha256"],
            expected_partition_sha256=a_metadata["partition_manifest_sha256"],
        )
        context = {
            "expected_extractor_config": data.base.extractor_config,
            "expected_cohort_sha256": data.base.cohort_sha256,
            "expected_partition_sha256": data.base.manifest.manifest_sha256,
        }
        a, b = load_a(a_dir, **context), load_b(b_dir, **context)
        assert_pairing(data, b.artifact)
        if a.artifact.train_split_sha256 != a_split_digest(
            data.base.train
        ) or a.artifact.validation_split_sha256 != a_split_digest(data.base.validation):
            raise ExperimentError("c_cache_a300_pairing_mismatch")
        a_raw = a.predict_logs(data.base.validation.inputs, repaired=False)
        b_raw = b.predict_logs(data.validation, repaired=False)
        for directory, values in ((a_dir, a_raw), (b_dir, b_raw)):
            saved = json.loads((directory / "validation-report.json").read_bytes())[
                "validation_rows"
            ]
            if [r["sample_id"] for r in saved] != list(
                data.base.validation.sample_ids
            ) or not np.array_equal(values, [r["raw_log_quantiles"] for r in saved]):
                raise ExperimentError("c_cache_existing_validation_prediction_mismatch")
        print(
            json.dumps(
                {
                    "phase": "verified_existing_A300_B_cache",
                    "train": len(data.train),
                    "validation": len(data.validation),
                    "columns": len(FEATURE_NAMES),
                    "holdout_opened": False,
                }
            ),
            flush=True,
        )
        started = time.monotonic()
        c, _ = train_experiment(
            data,
            args.model_dir,
            progress=lambda value: print(
                json.dumps({"phase": "trial_completed", **value}), flush=True
            ),
        )
        original = {
            r.sample_id
            for r in load_partitions(args.parent / "partitions.json").assignments
            if r.partition == "validation"
        }
        result = compare(data, b, c, original_validation_ids=original)
        result["models"]["A300"] = evaluate_development(data.base.validation, a_raw)
        for name, ids in (
            ("original_validation", original),
            ("new_validation", set(data.base.validation.sample_ids) - original),
            ("all_validation", set(data.base.validation.sample_ids)),
        ):
            split = subset(data.base.validation, ids)
            if split is None:
                continue
            mask = [sample in ids for sample in data.base.validation.sample_ids]
            result["groups"][name]["models"]["A300"] = {
                "metrics": evaluate_development(split, a_raw[mask]),
                "range_kind": "estimated_not_calibrated",
            }
        result.update(
            seconds_including_C_training_reload_comparison=time.monotonic() - started,
            development_evidence_unique_paths=len(set(opened)),
            A300_and_B_cache_saved_predictions_exact=True,
            full_B_C_completed=False,
            served_model_replaced=False,
            holdout_opened=False,
            new_external_requests=0,
        )
        _write_new(
            args.comparison, (json.dumps(result, sort_keys=True, allow_nan=False) + "\n").encode()
        )
        print(
            json.dumps(
                {
                    "phase": "completed",
                    "mae_log_macro_channel": {
                        name: m["mae_log_macro_channel"] for name, m in result["models"].items()
                    },
                    "seconds": result["seconds_including_C_training_reload_comparison"],
                    "full_B_C_completed": False,
                    "holdout_opened": False,
                }
            ),
            flush=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

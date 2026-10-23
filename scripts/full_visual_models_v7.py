"""Synthetic-only B/C V7 trainer with injected backends and verified artifacts.

Native fitting is deliberately lazy: the default adapter is not created until a
separate, explicitly scheduled native run. Tests inject the JSON recording backend.
"""

from __future__ import annotations

import itertools
import math
import os
import time
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import numpy as np

from scripts.channel_partitions import ExperimentError, digest
from scripts.experiment_a_metrics import (
    QUANTILES,
    channel_weights,
    checked_logs,
    evaluate_development,
    repair_quantiles,
    selection_score,
    views_from_logs,
)
from scripts.full_visual_artifact_v7 import (
    ARTIFACT_SCHEMA,
    MODEL_FILES,
    REPORT_SCHEMA,
    read_bundle,
    save_bundle,
    sha,
)
from scripts.full_visual_contract_v7 import FIELDS
from scripts.full_visual_data_v7 import (
    V7DevelopmentData,
    categorical_indices,
    feature_matrix,
    feature_names,
    reload_data,
    source_versions,
    split_digest,
)

FEATURE_NAMES = feature_names()
CATEGORICAL_INDICES = categorical_indices()
FEATURE_CONTRACT_SHA256 = digest(
    {"feature_names": FEATURE_NAMES, "categorical_indices": CATEGORICAL_INDICES}
)


@dataclass(frozen=True)
class FitResult:
    model: Any
    predictions: np.ndarray
    best_iteration: int
    tree_count: int
    evaluated_iterations: int
    native_validation_metric: float
    elapsed_seconds: float


class RecordingBackend:
    """A deterministic, explicitly non-native backend for contract tests only."""

    backend_kind = "recording"

    def __init__(self):
        self.calls = []

    def fit_trial(
        self,
        *,
        algorithm,
        quantile,
        params,
        train_x,
        train_y,
        validation_x,
        validation_y,
        validation_weights,
        validation_channel_ids,
        feature_names,
        categorical_indices,
    ):
        start = time.monotonic()
        self.calls.append(
            {
                "algorithm": algorithm,
                "quantile": quantile,
                "params": dict(params),
                "train_rows": len(train_y),
                "validation_rows": len(validation_y),
                "training_weights": None,
                "validation_weights": np.asarray(validation_weights).tolist(),
                "feature_names": tuple(feature_names),
                "categorical_indices": tuple(categorical_indices),
            }
        )
        # A stable tiny linear statistic lets the integrated tests exercise actual
        # serialization and pairing without importing or fitting a native model.
        matrix = np.asarray(validation_x, dtype=object)
        numeric = np.zeros(len(matrix), dtype=float)
        for j in range(matrix.shape[1]):
            col = matrix[:, j]
            if np.issubdtype(np.asarray(col).dtype, np.number):
                numeric += np.asarray(col, dtype=float) * ((j % 7) + 1) * 1e-7
            else:
                numeric += np.array([sum(map(ord, str(v))) % 17 for v in col]) * 1e-5
        level = float(np.quantile(np.asarray(train_y, dtype=float), quantile))
        pred = np.maximum(0.0, level + numeric)
        score = selection_score(validation_y, pred, validation_channel_ids, quantile)
        model = {
            "kind": self.backend_kind,
            "algorithm": algorithm,
            "quantile": quantile,
            "level": level,
            "params": params,
            "features": list(feature_names),
            "categories": list(categorical_indices),
            "best_iteration": 1,
        }
        best = 0 if algorithm == "B" else 1
        model["best_iteration"] = best
        return FitResult(model, pred, best, 1, 1, score, time.monotonic() - start)

    def predict(self, *, algorithm, model, matrix):
        # Same formula used at fit; train-derived intercept only.
        matrix = np.asarray(matrix, dtype=object)
        numeric = np.zeros(len(matrix), dtype=float)
        for j in range(matrix.shape[1]):
            col = matrix[:, j]
            if np.issubdtype(np.asarray(col).dtype, np.number):
                numeric += np.asarray(col, dtype=float) * ((j % 7) + 1) * 1e-7
            else:
                numeric += np.array([sum(map(ord, str(v))) % 17 for v in col]) * 1e-5
        return np.maximum(0.0, float(model["level"]) + numeric)

    def save_model(self, *, algorithm, model, path):
        from scripts.full_visual_artifact_v7 import canonical

        Path(path).write_bytes(canonical(model))
        os.chmod(path, 0o600)

    def load_model(self, *, algorithm, path):
        import json

        model = json.loads(Path(path).read_bytes())
        if model.get("kind") != self.backend_kind or model.get("algorithm") != algorithm:
            raise ExperimentError("v7_recording_model_kind_mismatch")
        return model

    def describe(self, *, algorithm, model):
        return {
            "algorithm": algorithm,
            "quantile": model["quantile"],
            "feature_names": model["features"],
            "categorical_indices": model["categories"],
            "best_iteration": model["best_iteration"],
            "tree_count": 1,
            "params": model["params"],
            "backend_kind": self.backend_kind,
        }

    def contributions(self, *, algorithm, model, matrix):
        # Additive decomposition that reconstructs this backend's q50 prediction.
        prediction = self.predict(algorithm=algorithm, model=model, matrix=matrix)
        result = np.zeros((len(prediction), len(FEATURE_NAMES) + 1), dtype=float)
        result[:, -1] = prediction
        return result


def _protocol(algorithm):
    if algorithm == "B":
        return {
            "quantiles": list(QUANTILES),
            "depths": [4, 6],
            "l2_leaf_reg": [3, 10],
            "iterations": 500,
            "learning_rate": 0.05,
            "early_stopping_rounds": 50,
            "seed": 42,
            "task_type": "CPU",
            "thread_count": 2,
            "allow_writing_files": False,
            "nan_mode": "Forbidden",
            "use_best_model": True,
            "selection": "q50_macro_channel_mae_extremes_macro_channel_pinball",
            "tie_break": ["score", "depth", "l2_leaf_reg"],
        }
    if algorithm == "C":
        return {
            "quantiles": list(QUANTILES),
            "num_leaves": [7, 15],
            "min_data_in_leaf": [5, 20],
            "iterations": 500,
            "learning_rate": 0.05,
            "early_stopping_rounds": 50,
            "seed": 42,
            "device_type": "cpu",
            "num_threads": 1,
            "deterministic": True,
            "force_col_wise": True,
            "max_depth": 6,
            "lambda_l2": 3,
            "feature_pre_filter": False,
            "verbosity": -1,
            "selection": "q50_macro_channel_mae_extremes_macro_channel_pinball",
            "tie_break": ["score", "num_leaves", "min_data_in_leaf"],
        }
    raise ExperimentError("v7_algorithm_invalid")


def _trial_params(algorithm, q, first, second):
    if algorithm == "B":
        return {
            "loss_function": f"Quantile:alpha={q}",
            "eval_metric": "MAE" if q == 0.5 else f"Quantile:alpha={q}",
            "depth": first,
            "l2_leaf_reg": second,
            "learning_rate": 0.05,
            "iterations": 500,
            "random_seed": 42,
            "task_type": "CPU",
            "thread_count": 2,
            "allow_writing_files": False,
            "nan_mode": "Forbidden",
            "verbose": False,
            "fit_use_best_model": True,
            "early_stopping_rounds": 50,
        }
    return {
        "objective": "quantile",
        "alpha": q,
        "metric": "None",
        "num_leaves": first,
        "min_data_in_leaf": second,
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
        "iterations": 500,
        "early_stopping_rounds": 50,
    }


def _fresh(data):
    if not isinstance(data, V7DevelopmentData):
        raise ExperimentError("v7_loader_verified_data_required")
    if type(data.loader_verified) is not bool or data.loader_verified is not True:
        raise ExperimentError("v7_loader_verified_data_required")
    if data.source_manifest_path is None or data.sidecar_root is None:
        raise ExperimentError("v7_reloadable_source_paths_required")
    if (
        data.data_kind != "synthetic"
        or type(data.quality_accepted) is not bool
        or data.quality_accepted is not False
        or type(data.release_emitted) is not bool
        or data.release_emitted is not False
    ):
        raise ExperimentError("v7_synthetic_unreleased_only")
    return reload_data(data)


def _targets(data, part):
    split = getattr(data.cached.base, part)
    return np.log1p(np.asarray([t.view_count for t in split.targets], dtype=np.float64))


def _fit_c_encoding(train_x):
    return {str(i): sorted({str(row[i]) for row in train_x}) for i in CATEGORICAL_INDICES}


def _encode_c(matrix, vocab):
    result = [list(row) for row in matrix]
    for index in CATEGORICAL_INDICES:
        categories = vocab[str(index)]
        mapping = {value: position for position, value in enumerate(categories)}
        for row in result:
            value = str(row[index])
            if value not in mapping:
                raise ExperimentError("v7_c_unseen_category")
            row[index] = mapping[value]
    return result


def _check_new_destination(path):
    absolute = Path(os.path.abspath(path))
    if absolute.exists() or absolute.is_symlink():
        raise ExperimentError("v7_model_output_already_exists")
    for ancestor in (absolute, *absolute.parents):
        if ancestor.is_symlink():
            raise ExperimentError("v7_artifact_symlink_rejected")
    try:
        absolute.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    except OSError:
        raise ExperimentError("v7_artifact_parent_invalid") from None
    return absolute


def _source_hashes():
    root = Path(__file__).resolve().parent
    names = (
        "experiment_a_metrics.py",
        "experiment_a_artifact.py",
        "train_experiment_b_vlm.py",
        "train_experiment_c_full.py",
        "experiment_b_vlm_artifact.py",
        "full_visual_contract_v7.py",
        "full_visual_data_v7.py",
        "full_visual_artifact_v7.py",
        "full_visual_models_v7.py",
    )
    return {name: sha((root / name).read_bytes()) for name in names}


def _runtime():
    result = {}
    for name in ("numpy", "catboost", "lightgbm", "pydantic"):
        try:
            result[name] = version(name)
        except PackageNotFoundError:
            result[name] = "not-installed"
    return result


def _fit(backend, algorithm, data, directory, progress=None):
    data = _fresh(data)
    directory = Path(directory)
    _check_new_destination(directory)
    protocol = _protocol(algorithm)
    train_x = feature_matrix(data.train)
    val_x = feature_matrix(data.validation)
    c_categories = _fit_c_encoding(train_x) if algorithm == "C" else None
    if algorithm == "C":
        train_x, val_x = _encode_c(train_x, c_categories), _encode_c(val_x, c_categories)
    train_y = _targets(data, "train")
    val_y = _targets(data, "validation")
    val_split = data.cached.base.validation
    weights = channel_weights(val_split.channel_ids)
    fields = ("depths", "l2_leaf_reg") if algorithm == "B" else ("num_leaves", "min_data_in_leaf")
    values = (protocol[fields[0]], protocol[fields[1]])
    trials, candidates = [], {}
    for q in QUANTILES:
        for first, second in itertools.product(*values):
            params = _trial_params(algorithm, q, first, second)
            result = backend.fit_trial(
                algorithm=algorithm,
                quantile=q,
                params=params,
                train_x=train_x,
                train_y=train_y,
                validation_x=val_x,
                validation_y=val_y,
                validation_weights=weights,
                validation_channel_ids=val_split.channel_ids,
                feature_names=FEATURE_NAMES,
                categorical_indices=CATEGORICAL_INDICES,
            )
            prediction = np.asarray(result.predictions, dtype=np.float64)
            if prediction.shape != (len(val_y),):
                raise ExperimentError("v7_trial_predictions_invalid")
            checked_logs(np.repeat(prediction[:, None], 3, axis=1))
            score = selection_score(val_y, prediction, val_split.channel_ids, q)
            tolerance = 3e-6 if algorithm == "B" else 1e-12
            if not math.isclose(
                result.native_validation_metric, score, rel_tol=0, abs_tol=tolerance
            ):
                raise ExperimentError("v7_early_stopping_metric_mismatch")
            best = int(result.best_iteration)
            trees = int(result.tree_count)
            evaluated = int(result.evaluated_iterations)
            valid_iterations = (
                (0 <= best < 500 and trees == best + 1 and evaluated >= trees)
                if algorithm == "B"
                else (1 <= trees <= best <= evaluated <= 500)
            )
            if not valid_iterations:
                raise ExperimentError("v7_trial_iterations_invalid")
            elapsed = float(result.elapsed_seconds)
            if not math.isfinite(elapsed) or elapsed < 0 or not math.isfinite(score) or score < 0:
                raise ExperimentError("v7_trial_metadata_invalid")
            row = {
                "quantile": q,
                fields[0][:-1] if algorithm == "B" else fields[0]: first,
                fields[1]: second,
                "best_iteration": best,
                "tree_count": trees,
                "evaluated_iterations": evaluated,
                "validation_score": score,
                "elapsed_seconds": elapsed,
                "params": params,
            }
            trials.append(row)
            candidates[(q, first, second)] = result.model
            if progress:
                progress(dict(row))
    selected = []
    models = []
    for q in QUANTILES:
        rows = [r for r in trials if r["quantile"] == q]
        key_names = (
            ("depth", "l2_leaf_reg") if algorithm == "B" else ("num_leaves", "min_data_in_leaf")
        )
        chosen = min(rows, key=lambda r: (r["validation_score"], r[key_names[0]], r[key_names[1]]))
        selected.append(chosen)
        models.append(candidates[(q, chosen[key_names[0]], chosen[key_names[1]])])
    raw = np.column_stack(
        [backend.predict(algorithm=algorithm, model=m, matrix=val_x) for m in models]
    )
    raw = checked_logs(raw)
    report = {
        "schema_version": REPORT_SCHEMA,
        "algorithm": algorithm,
        "backend_kind": backend.backend_kind,
        "data_kind": "synthetic",
        "partition": "validation",
        "metrics": evaluate_development(data.cached.base.validation, raw),
        "selected": selected,
        "trials": trials,
        "validation_rows": [
            {"sample_id": sid, "raw_log_quantiles": row.tolist()}
            for sid, row in zip(val_split.sample_ids, raw, strict=True)
        ],
        "quality_accepted": False,
        "release_emitted": False,
        "final_test_evaluated": False,
    }
    report["baseline_B0"] = {
        "artifact_sha256": data.cached.base.baseline.artifact_sha256,
        "scope": "train_only_sector_quantiles",
        "coverage_status": "not_calibrated",
        "metrics": evaluate_development(data.cached.base.validation, _baseline_predictions(data)),
    }
    try:
        lock_hash = sha(Path(__file__).resolve().parents[1].joinpath("uv.lock").read_bytes())
    except OSError:
        raise ExperimentError("v7_lockfile_unavailable") from None
    artifact = {
        "schema_version": ARTIFACT_SCHEMA,
        "algorithm": algorithm,
        "backend_kind": backend.backend_kind,
        "data_kind": "synthetic",
        "backend_identity": (
            "front1-deterministic-recording-v1"
            if backend.backend_kind == "recording"
            else ("catboost" if algorithm == "B" else "lightgbm")
        ),
        "quality_accepted": False,
        "release_emitted": False,
        "final_test_evaluated": False,
        "served_model_replaced": False,
        "quality_release_sha256": None,
        "feature_names": list(FEATURE_NAMES),
        "categorical_indices": list(CATEGORICAL_INDICES),
        "feature_contract_sha256": FEATURE_CONTRACT_SHA256,
        "fields": list(FIELDS),
        "encoding": {
            "policy": "sorted_train_only_vocab_integer_codes_v1"
            if algorithm == "C"
            else "catboost_native_categories",
            "categories": c_categories or {},
        },
        "identities": dict(data.manifest.identities),
        "cohort_sha256": data.manifest.identities["cohort_sha256"],
        "partition_sha256": data.manifest.identities["partition_sha256"],
        "configuration_sha256": data.manifest.identities["configuration_sha256"],
        "candidate_sha256": data.manifest.identities["candidate_sha256"],
        "baseline_sha256": data.cached.base.baseline.artifact_sha256,
        "source_manifest_sha256": data.manifest_sha256,
        "source_versions": data.manifest.source_versions,
        "train_split_sha256": split_digest(data, "train"),
        "validation_split_sha256": split_digest(data, "validation"),
        "training_sample_ids": list(data.cached.base.train.sample_ids),
        "validation_sample_ids": list(val_split.sample_ids),
        "protocol": protocol,
        "trials": trials,
        "selected": selected,
        "runtime_versions": _runtime(),
        "source_files_sha256": _source_hashes(),
        "uv_lock_sha256": lock_hash,
        "model_sha256": {},
        "validation_report_sha256": None,
        "content_sha256": None,
    }
    save_bundle(directory, artifact, report, backend, models)
    return load_bundle(directory, data=data, backend=backend), report


def train_experiment(data, directory, *, algorithm="B", backend=None, progress=None):
    if backend is None:
        backend = NativeBackend(algorithm)
    if backend.backend_kind not in ("native", "recording"):
        raise ExperimentError("v7_backend_kind_invalid")
    return _fit(backend, algorithm, data, directory, progress)


class NativeBackend:
    """Lazy native adapter. Its methods run only under a separately authorized slot."""

    backend_kind = "native"

    def __init__(self, algorithm):
        if algorithm not in ("B", "C"):
            raise ExperimentError("v7_algorithm_invalid")
        self.algorithm = algorithm

    def _module(self):
        if self.algorithm == "B":
            from catboost import CatBoostRegressor, Pool

            return CatBoostRegressor, Pool
        import lightgbm as lgb

        return lgb

    def fit_trial(self, **kw):
        from scripts.experiment_a_metrics import selection_score

        start = time.monotonic()
        algorithm = kw["algorithm"]
        q = kw["quantile"]
        p = kw["params"]
        if algorithm == "B":
            Cat, Pool = self._module()
            cats = list(kw["categorical_indices"])
            names = list(kw["feature_names"])
            train = Pool(kw["train_x"], label=kw["train_y"], cat_features=cats, feature_names=names)
            val = Pool(
                kw["validation_x"],
                label=kw["validation_y"],
                weight=kw["validation_weights"],
                cat_features=cats,
                feature_names=names,
            )
            model = Cat(
                loss_function=p["loss_function"],
                eval_metric=p["eval_metric"],
                depth=p["depth"],
                l2_leaf_reg=p["l2_leaf_reg"],
                learning_rate=0.05,
                iterations=500,
                random_seed=42,
                task_type="CPU",
                thread_count=2,
                allow_writing_files=False,
                nan_mode="Forbidden",
                verbose=False,
            )
            model.fit(train, eval_set=val, use_best_model=True, early_stopping_rounds=50)
            pred = np.asarray(model.predict(val))
            metric = model.get_best_score()["validation"][p["eval_metric"]]
            best = model.get_best_iteration()
            trees = model.tree_count_
            evaluated = len(next(iter(model.get_evals_result()["validation"].values())))
        else:
            lgb = self._module()
            train = lgb.Dataset(
                kw["train_x"],
                label=kw["train_y"],
                categorical_feature=list(kw["categorical_indices"]),
                feature_name=list(kw["feature_names"]),
            )
            valid = lgb.Dataset(
                kw["validation_x"],
                label=kw["validation_y"],
                weight=kw["validation_weights"],
                reference=train,
                categorical_feature=list(kw["categorical_indices"]),
                feature_name=list(kw["feature_names"]),
            )

            def feval(pred, dataset):
                if dataset is not valid:
                    raise ExperimentError("v7_c_validation_dataset_mismatch")
                score = selection_score(kw["validation_y"], pred, kw["validation_channel_ids"], q)
                return "macro_channel_selection", score, False

            history = {}
            model = lgb.train(
                {k: v for k, v in p.items() if k not in ("iterations", "early_stopping_rounds")},
                train,
                num_boost_round=500,
                valid_sets=[valid],
                valid_names=["validation"],
                feval=feval,
                callbacks=[lgb.early_stopping(50, verbose=False), lgb.record_evaluation(history)],
            )
            pred = np.asarray(model.predict(kw["validation_x"], num_threads=1))
            metric = history["validation"]["macro_channel_selection"][model.best_iteration - 1]
            best = model.best_iteration
            trees = model.current_iteration()
            evaluated = len(history["validation"]["macro_channel_selection"])
        return FitResult(
            model,
            pred,
            int(best),
            int(trees),
            int(evaluated),
            float(metric),
            time.monotonic() - start,
        )

    def predict(self, *, algorithm, model, matrix):
        if algorithm == "B":
            from catboost import Pool

            pool = Pool(
                matrix, cat_features=list(CATEGORICAL_INDICES), feature_names=list(FEATURE_NAMES)
            )
            return np.asarray(model.predict(pool))
        return np.asarray(model.predict(matrix, num_threads=1))

    def save_model(self, *, algorithm, model, path):
        if algorithm == "B":
            model.save_model(str(path))
        else:
            model.save_model(str(path))
        os.chmod(path, 0o600)

    def load_model(self, *, algorithm, path):
        if algorithm == "B":
            from catboost import CatBoostRegressor

            model = CatBoostRegressor()
            model.load_model(str(path), format="cbm")
            return model
        import lightgbm as lgb

        return lgb.Booster(model_file=str(path))

    def describe(self, *, algorithm, model):
        if algorithm == "B":
            params = model.get_all_params()
            return {
                "feature_names": list(model.feature_names_),
                "categorical_indices": list(model.get_cat_feature_indices()),
                "tree_count": model.tree_count_,
                "params": params,
                "backend_kind": "native",
            }
        return {
            "feature_names": list(model.feature_name()),
            "categorical_indices": list(model.params.get("categorical_feature", ())),
            "tree_count": model.current_iteration(),
            "params": model.params,
            "backend_kind": "native",
        }

    def contributions(self, *, algorithm, model, matrix):
        if algorithm == "B":
            from catboost import Pool

            pool = Pool(
                matrix, cat_features=list(CATEGORICAL_INDICES), feature_names=list(FEATURE_NAMES)
            )
            return model.get_feature_importance(
                pool, type="ShapValues", thread_count=1, verbose=False
            )
        return model.predict(matrix, pred_contrib=True, num_threads=1)


@dataclass(frozen=True)
class ModelBundle:
    artifact: dict
    report: dict
    models: tuple[Any, ...]
    backend: Any
    directory: Path
    _data: Any = None

    def _matrix(self, inputs):
        matrix = feature_matrix(tuple(inputs))
        if self.artifact["algorithm"] == "C":
            matrix = _encode_c(matrix, self.artifact["encoding"]["categories"])
        return matrix

    def _verified(self):
        checked = load_bundle(self.directory, data=self._data, backend=self.backend)
        return checked

    def predict_logs(self, inputs, *, repaired=True):
        bundle = self._verified()
        matrix = bundle._matrix(inputs)
        raw = checked_logs(
            np.column_stack(
                [
                    bundle.backend.predict(
                        algorithm=bundle.artifact["algorithm"], model=m, matrix=matrix
                    )
                    for m in bundle.models
                ]
            )
        )
        return repair_quantiles(raw) if repaired else raw

    def predict_views(self, inputs):
        return views_from_logs(self.predict_logs(inputs))


def load_bundle(directory, *, data, backend=None):
    data = _fresh(data)
    artifact, report, raw_models = read_bundle(Path(directory))
    if (
        artifact.get("schema_version") != ARTIFACT_SCHEMA
        or artifact.get("data_kind") != "synthetic"
        or artifact.get("quality_accepted") is not False
        or artifact.get("release_emitted") is not False
        or artifact.get("final_test_evaluated") is not False
        or artifact.get("served_model_replaced") is not False
        or artifact.get("quality_release_sha256", "sentinel") is not None
        or artifact.get("feature_names") != list(FEATURE_NAMES)
        or artifact.get("categorical_indices") != list(CATEGORICAL_INDICES)
        or artifact.get("feature_contract_sha256") != FEATURE_CONTRACT_SHA256
        or artifact.get("identities") != data.manifest.identities
        or artifact.get("source_manifest_sha256") != data.manifest_sha256
        or artifact.get("source_versions") != source_versions()
        or artifact.get("train_split_sha256") != split_digest(data, "train")
        or artifact.get("validation_split_sha256") != split_digest(data, "validation")
        or artifact.get("training_sample_ids") != list(data.cached.base.train.sample_ids)
        or artifact.get("validation_sample_ids") != list(data.cached.base.validation.sample_ids)
        or artifact.get("source_files_sha256") != _source_hashes()
        or artifact.get("runtime_versions") != _runtime()
    ):
        raise ExperimentError("v7_artifact_pairing_mismatch")
    try:
        current_lock = sha(Path(__file__).resolve().parents[1].joinpath("uv.lock").read_bytes())
    except OSError:
        raise ExperimentError("v7_lockfile_unavailable") from None
    if artifact.get("uv_lock_sha256") != current_lock:
        raise ExperimentError("v7_lockfile_mismatch")
    algo = artifact.get("algorithm")
    if (
        algo not in ("B", "C")
        or len(artifact.get("trials", [])) != 12
        or len(artifact.get("selected", [])) != 3
    ):
        raise ExperimentError("v7_artifact_trials_invalid")
    if artifact.get("protocol") != _protocol(algo):
        raise ExperimentError("v7_artifact_protocol_mismatch")
    if algo == "C":
        vocab = artifact.get("encoding", {}).get("categories")
        if type(vocab) is not dict or set(vocab) != set(map(str, CATEGORICAL_INDICES)):
            raise ExperimentError("v7_c_encoding_invalid")
        expected_vocab = _fit_c_encoding(feature_matrix(data.train))
        if vocab != expected_vocab:
            raise ExperimentError("v7_c_encoding_pairing_mismatch")
    keynames = ("depth", "l2_leaf_reg") if algo == "B" else ("num_leaves", "min_data_in_leaf")
    values = ((4, 6), (3, 10)) if algo == "B" else ((7, 15), (5, 20))
    expected_grid = {(q, a, b) for q in QUANTILES for a in values[0] for b in values[1]}
    observed_grid = set()
    for trial in artifact["trials"]:
        key = (trial.get("quantile"), trial.get(keynames[0]), trial.get(keynames[1]))
        if (
            key not in expected_grid
            or key in observed_grid
            or trial.get("params") != _trial_params(algo, *key)
        ):
            raise ExperimentError("v7_artifact_trial_recipe_mismatch")
        if (
            type(trial.get("best_iteration")) is not int
            or type(trial.get("tree_count")) is not int
            or type(trial.get("evaluated_iterations")) is not int
            or type(trial.get("validation_score")) not in (float, int)
            or type(trial.get("elapsed_seconds")) not in (float, int)
            or not math.isfinite(trial["validation_score"])
            or trial["validation_score"] < 0
            or not math.isfinite(trial["elapsed_seconds"])
            or trial["elapsed_seconds"] < 0
        ):
            raise ExperimentError("v7_artifact_trial_metadata_invalid")
        best = trial["best_iteration"]
        trees = trial["tree_count"]
        evaluated = trial["evaluated_iterations"]
        valid_iterations = (
            (0 <= best < 500 and trees == best + 1 and trees <= evaluated <= 500)
            if algo == "B"
            else (1 <= trees <= best <= evaluated <= 500)
        )
        if not valid_iterations:
            raise ExperimentError("v7_artifact_trial_iterations_invalid")
        observed_grid.add(key)
    if observed_grid != expected_grid:
        raise ExperimentError("v7_artifact_trial_grid_mismatch")
    for q, chosen in zip(QUANTILES, artifact["selected"], strict=True):
        best = min(
            (t for t in artifact["trials"] if t["quantile"] == q),
            key=lambda t: (t["validation_score"], t[keynames[0]], t[keynames[1]]),
        )
        if chosen != best or chosen.get("quantile") != q:
            raise ExperimentError("v7_artifact_selection_mismatch")
    expected_content = digest({k: v for k, v in artifact.items() if k != "content_sha256"})
    if artifact.get("content_sha256") != expected_content or artifact.get("backend_kind") not in (
        "native",
        "recording",
    ):
        raise ExperimentError("v7_artifact_digest_invalid")
    if artifact["backend_kind"] == "recording" and backend is None:
        raise ExperimentError("v7_recording_backend_injection_required")
    expected_backend_identity = (
        "front1-deterministic-recording-v1"
        if artifact["backend_kind"] == "recording"
        else ("catboost" if algo == "B" else "lightgbm")
    )
    if artifact.get("backend_identity") != expected_backend_identity:
        raise ExperimentError("v7_backend_identity_mismatch")
    expected_algo_backend = backend if backend is not None else NativeBackend(algo)
    if (
        artifact["backend_kind"] == "recording"
        and getattr(expected_algo_backend, "backend_kind", None) != "recording"
    ):
        raise ExperimentError("v7_recording_artifact_rejected_by_native_backend")
    if getattr(expected_algo_backend, "backend_kind", None) != artifact["backend_kind"]:
        raise ExperimentError("v7_backend_kind_mismatch")
    report_hash = sha((Path(directory) / "validation-report.json").read_bytes())
    if (
        report_hash != artifact.get("validation_report_sha256")
        or report.get("schema_version") != REPORT_SCHEMA
        or report.get("algorithm") != algo
        or report.get("backend_kind") != artifact["backend_kind"]
    ):
        raise ExperimentError("v7_validation_report_mismatch")
    if (
        report.get("data_kind") != "synthetic"
        or any(
            type(report.get(key)) is not bool or report[key] is not False
            for key in ("quality_accepted", "release_emitted", "final_test_evaluated")
        )
        or report.get("trials") != artifact["trials"]
        or report.get("selected") != artifact["selected"]
    ):
        raise ExperimentError("v7_validation_report_contract_mismatch")
    if artifact.get("model_sha256") != {k: sha(v) for k, v in raw_models.items()}:
        raise ExperimentError("v7_model_checksum_mismatch")
    models = tuple(
        expected_algo_backend.load_model(algorithm=algo, path=Path(directory) / name)
        for name in MODEL_FILES
    )
    for model, selected in zip(models, artifact["selected"], strict=True):
        desc = expected_algo_backend.describe(algorithm=algo, model=model)
        if (
            desc.get("backend_kind") != artifact["backend_kind"]
            or desc.get("feature_names") != list(FEATURE_NAMES)
            or desc.get("categorical_indices") != list(CATEGORICAL_INDICES)
        ):
            raise ExperimentError("v7_model_descriptor_mismatch")
        if (
            artifact["backend_kind"] == "native"
            and int(desc.get("tree_count", 0)) != selected["tree_count"]
        ):
            raise ExperimentError("v7_native_tree_count_mismatch")
        if artifact["backend_kind"] == "native":
            params = desc.get("params", {})
            if algo == "B":
                expected_loss = f"Quantile:alpha={selected['quantile']}"
                expected_metric = "MAE" if selected["quantile"] == 0.5 else expected_loss
                checks = {
                    "depth": selected["depth"],
                    "l2_leaf_reg": selected["l2_leaf_reg"],
                    "learning_rate": 0.05,
                    "random_seed": 42,
                    "task_type": "CPU",
                    "thread_count": 2,
                    "allow_writing_files": False,
                    "nan_mode": "Forbidden",
                    "loss_function": expected_loss,
                    "eval_metric": expected_metric,
                }
                if any(params.get(k) != v for k, v in checks.items()):
                    raise ExperimentError("v7_native_b_parameters_mismatch")
            else:
                checks = {
                    "objective": "quantile",
                    "alpha": selected["quantile"],
                    "num_leaves": selected["num_leaves"],
                    "min_data_in_leaf": selected["min_data_in_leaf"],
                    "max_depth": 6,
                    "lambda_l2": 3,
                    "learning_rate": 0.05,
                    "seed": 42,
                    "num_threads": 1,
                    "device_type": "cpu",
                    "deterministic": True,
                    "force_col_wise": True,
                    "feature_pre_filter": False,
                }
                if any(params.get(k) != v for k, v in checks.items()):
                    raise ExperimentError("v7_native_c_parameters_mismatch")
    result = ModelBundle(
        artifact, report, models, expected_algo_backend, Path(directory).resolve(), data
    )
    # Exact saved/reloaded parity over paired validation rows.
    matrix = feature_matrix(data.validation)
    if algo == "C":
        matrix = _encode_c(matrix, artifact["encoding"]["categories"])
    raw = np.column_stack(
        [expected_algo_backend.predict(algorithm=algo, model=m, matrix=matrix) for m in models]
    )
    expected = np.asarray([r["raw_log_quantiles"] for r in report["validation_rows"]], dtype=float)
    if not np.array_equal(raw, expected):
        raise ExperimentError("v7_reload_prediction_mismatch")
    for prediction, selected in zip(raw.T, artifact["selected"], strict=True):
        checked_logs(np.repeat(np.asarray(prediction)[:, None], 3, axis=1))
        score = selection_score(
            _targets(data, "validation"),
            prediction,
            data.cached.base.validation.channel_ids,
            selected["quantile"],
        )
        tolerance = 3e-6 if algo == "B" else 1e-12
        if not math.isclose(score, selected["validation_score"], rel_tol=0, abs_tol=tolerance):
            raise ExperimentError("v7_selected_validation_score_mismatch")
    return result


def compare(data, b_bundle, c_bundle):
    data = _fresh(data)
    # Reopen each artifact against this exact dataset. The incoming bundle objects
    # are mutable containers, so their in-memory metadata cannot establish pairing.
    b_verified = load_bundle(b_bundle.directory, data=data, backend=b_bundle.backend)
    c_verified = load_bundle(c_bundle.directory, data=data, backend=c_bundle.backend)
    if b_verified.artifact["algorithm"] != "B" or c_verified.artifact["algorithm"] != "C":
        raise ExperimentError("v7_comparison_algorithm_mismatch")
    if (
        b_verified.artifact["train_split_sha256"] != c_verified.artifact["train_split_sha256"]
        or b_verified.artifact["validation_split_sha256"]
        != c_verified.artifact["validation_split_sha256"]
    ):
        raise ExperimentError("v7_comparison_pairing_mismatch")
    inputs = data.validation
    raw_b = b_verified.predict_logs(inputs, repaired=False)
    raw_c = c_verified.predict_logs(inputs, repaired=False)
    base = data.cached.base.validation
    result = {
        "schema_version": "front1-bc-v7-comparison-v1",
        "data_kind": "synthetic",
        "paired": True,
        "B": {
            "metrics": evaluate_development(base, raw_b),
            "backend_kind": b_verified.artifact["backend_kind"],
        },
        "C": {
            "metrics": evaluate_development(base, raw_c),
            "backend_kind": c_verified.artifact["backend_kind"],
        },
        "B0": {
            "metrics": evaluate_development(base, _baseline_predictions(data)),
            "artifact_sha256": data.cached.base.baseline.artifact_sha256,
            "scope": "train_only_sector_quantiles",
            "coverage_status": "not_calibrated",
        },
        "quality_accepted": False,
        "release_emitted": False,
        "selection_or_promotion": False,
        "holdout_opened": False,
        "partition": "validation",
        "final_test_evaluated": False,
        "provenance": {
            "data_manifest_sha256": data.manifest_sha256,
            "identities": data.manifest.identities,
            "train_split_sha256": split_digest(data, "train"),
            "validation_split_sha256": split_digest(data, "validation"),
            "feature_contract_sha256": FEATURE_CONTRACT_SHA256,
            "baseline_artifact_sha256": data.cached.base.baseline.artifact_sha256,
            "B_artifact_sha256": sha((b_verified.directory / "artifact.json").read_bytes()),
            "C_artifact_sha256": sha((c_verified.directory / "artifact.json").read_bytes()),
        },
    }
    result["result_sha256"] = digest(result)
    return result


def _baseline_predictions(data):
    artifact = data.cached.base.baseline
    by_sector = {item.sector: item for item in artifact.sectors}
    rows = []
    for value in data.cached.base.validation.inputs:
        stat = by_sector.get(value.sector)
        if stat is None:
            raise ExperimentError("v7_baseline_sector_unavailable")
        rows.append((stat.q10_log1p, stat.q50_log1p, stat.q90_log1p))
    return np.asarray(rows, dtype=float)

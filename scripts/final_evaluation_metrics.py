"""P6 arithmetic on explicit in-memory rows; no file, model, fit or holdout loader.

Outputs contain per-case errors and must stay private until a separate sanitized
projection is reviewed. Calling this module neither opens nor authorizes a test.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from pydantic import Field

from scripts.channel_partitions import Digest, ExperimentError, FrozenContract, Identifier
from scripts.empirical_baseline import MAX_LOG_VIEWS
from scripts.experiment_a_metrics import (
    QUANTILES,
    REPAIR_POLICY,
    _ranking,
    macro_mean,
    pinball,
    repair_quantiles,
    views_from_logs,
)

REQUIRED_MODELS = ("B0", "Bcanal", "A300", "B_FULL_VLM", "C_FULL_VLM")
FAILURES = ("missing_features", "unsupported_category", "inference_failed", "invalid_prediction")


class EvaluationRow(FrozenContract):
    sample_id: Identifier
    channel_id: Identifier
    sector: Literal["moda", "beleza"]
    view_count: int = Field(ge=0, le=2**63 - 1)


class Prediction(FrozenContract):
    sample_id: Identifier
    raw_log_quantiles: tuple[float, float, float] | None = None
    failure_code: (
        Literal[
            "missing_features", "unsupported_category", "inference_failed", "invalid_prediction"
        ]
        | None
    ) = None


class ModelPredictions(FrozenContract):
    name: Literal["B0", "Bcanal", "A300", "B_FULL_VLM", "C_FULL_VLM", "A200"]
    artifact_sha256: Digest
    predictions: tuple[Prediction, ...]


def _summary(rows, predictions):
    """Only available predictions enter arithmetic; every denominator is explicit."""
    available = [(r, p) for r, p in zip(rows, predictions, strict=True) if p.failure_code is None]
    support = {
        "expected_samples": len(rows),
        "expected_channels": len({r.channel_id for r in rows}),
        "available_samples": len(available),
        "failed_samples": len(rows) - len(available),
        "available_channels": len({r.channel_id for r, _ in available}),
        "failures_by_code": {
            code: sum(p.failure_code == code for p in predictions) for code in FAILURES
        },
    }
    if not available:
        return support | {"status": "no_predictions", "metrics": None, "ranking": None}
    y = np.log1p([r.view_count for r, _ in available])
    actual_views = np.array([r.view_count for r, _ in available], dtype=float)
    raw = np.array([p.raw_log_quantiles for _, p in available])
    served = repair_quantiles(raw)
    predicted_views = views_from_logs(served)
    channels = np.array([r.channel_id for r, _ in available])
    error_log = np.abs(y - served[:, 1])
    error_views = np.abs(actual_views - predicted_views[:, 1])
    positive = actual_views > 0
    covered = (served[:, 0] <= y) & (y <= served[:, 2])
    rankings = [_ranking(y[channels == c], served[channels == c, 1]) for c in sorted(set(channels))]
    ranking = {
        "global_spearman_secondary": _ranking(y, served[:, 1])["spearman"],
        "comparable_pairs": sum(r["comparable_pairs"] for r in rankings),
        "ties_policy": "exclude_target_ties_prediction_ties_half_credit",
    }
    for metric in ("spearman", "pair_accuracy"):
        values = [r[metric] for r in rankings if r[metric] is not None]
        ranking[f"{metric}_macro_channel"] = float(np.mean(values)) if values else None
        ranking[f"{metric}_supported_channels"] = len(values)
    return support | {
        "status": "complete" if len(available) == len(rows) else "partial",
        "metrics": {
            "mae_log_macro_channel": macro_mean(error_log, channels),
            "mae_log_micro": float(error_log.mean()),
            "mae_views_macro_channel": macro_mean(error_views, channels),
            "mae_views_micro": float(error_views.mean()),
            "mape_positive_views": float(np.mean(error_views[positive] / actual_views[positive]))
            if np.any(positive)
            else None,
            "mape_included_samples": int(positive.sum()),
            "mape_excluded_zero_views": int((~positive).sum()),
            "pinball_log_macro_channel": {
                str(q): macro_mean(pinball(y, served[:, i], q), channels)
                for i, q in enumerate(QUANTILES)
            },
            "coverage_micro": float(covered.mean()),
            "coverage_macro_channel": macro_mean(covered, channels),
            "mean_width_log": float((served[:, 2] - served[:, 0]).mean()),
            "mean_width_views": float((predicted_views[:, 2] - predicted_views[:, 0]).mean()),
            "crossing_rows_raw": int(np.sum((raw[:, 0] > raw[:, 1]) | (raw[:, 1] > raw[:, 2]))),
        },
        "ranking": ranking,
    }


def _validate(rows, models, expected_count):
    rows = tuple(EvaluationRow.model_validate(r) for r in rows)
    models = tuple(ModelPredictions.model_validate(m) for m in models)
    ids = tuple(r.sample_id for r in rows)
    names = tuple(m.name for m in models)
    if type(expected_count) is not int or expected_count <= 0 or len(rows) != expected_count:
        raise ExperimentError("evaluation_count_mismatch")
    if ids != tuple(sorted(set(ids))):
        raise ExperimentError("evaluation_ids_must_be_unique_sorted")
    if len(names) != len(set(names)) or set(names) not in (
        set(REQUIRED_MODELS),
        {*REQUIRED_MODELS, "A200"},
    ):
        raise ExperimentError("evaluation_requires_frozen_model_set")
    for model in models:
        if tuple(p.sample_id for p in model.predictions) != ids:
            raise ExperimentError("evaluation_prediction_rows_mismatch")
        for p in model.predictions:
            if (p.raw_log_quantiles is None) == (p.failure_code is None):
                raise ExperimentError("prediction_requires_values_xor_failure")
            if p.raw_log_quantiles is not None and any(
                q < 0 or q > MAX_LOG_VIEWS for q in p.raw_log_quantiles
            ):
                raise ExperimentError("invalid_quantile_predictions")
    return rows, models


def evaluate_predictions(rows, models, *, expected_count=31):
    """Compute metrics without choosing, promoting, fitting or loading a model.

    Production count defaults to 31. Smaller explicitly named counts support
    invented tests and development diagnostics, never proof of a 31-case run.
    """
    rows, models = _validate(rows, models, expected_count)
    result = {
        "schema_version": "p6-prediction-metrics-v1",
        "expected_samples": expected_count,
        "repair_policy": REPAIR_POLICY,
        "contains_private_case_diagnostics": True,
        "selection_performed": False,
        "model_promotion_performed": False,
        "models": {},
    }
    for model in models:
        predictions = model.predictions
        entry = _summary(rows, predictions) | {
            "artifact_sha256": model.artifact_sha256,
            "range_kind": "empirical_training_sector_range"
            if model.name in ("B0", "Bcanal")
            else "estimated_predictive_quantiles",
        }
        entry["by_sector"] = {}
        entry["by_channel"] = {}
        for field, keys in (
            ("sector", ("moda", "beleza")),
            ("channel_id", sorted({r.channel_id for r in rows})),
        ):
            destination = entry["by_sector" if field == "sector" else "by_channel"]
            for key in keys:
                indexes = [i for i, r in enumerate(rows) if getattr(r, field) == key]
                destination[key] = _summary(
                    [rows[i] for i in indexes], [predictions[i] for i in indexes]
                )
        cases = []
        for row, p in zip(rows, predictions, strict=True):
            case = row.model_dump() | p.model_dump(exclude={"sample_id"})
            if p.raw_log_quantiles is not None:
                served = repair_quantiles([p.raw_log_quantiles])[0]
                case.update(
                    served_log_quantiles=served.tolist(),
                    absolute_error_log=float(abs(np.log1p(row.view_count) - served[1])),
                    absolute_error_views=float(abs(row.view_count - np.expm1(served[1]))),
                )
            cases.append(case)
        entry["cases"] = cases
        entry["largest_errors"] = {
            scale: [
                c["sample_id"]
                for c in sorted(
                    (c for c in cases if c["failure_code"] is None),
                    key=lambda c: (-c[f"absolute_error_{scale}"], c["sample_id"]),
                )[:5]
            ]
            for scale in ("log", "views")
        }
        result["models"][model.name] = entry
    result["complete_all_models"] = all(
        m["status"] == "complete" for m in result["models"].values()
    )
    paired = {}
    by_name = {m.name: m for m in models}
    for left, right in (("A300", "B_FULL_VLM"), ("B_FULL_VLM", "C_FULL_VLM")):
        l, r = by_name[left].predictions, by_name[right].predictions
        idx = [i for i in range(len(rows)) if l[i].failure_code is r[i].failure_code is None]
        subset = [rows[i] for i in idx]
        a = _summary(subset, [l[i] for i in idx])
        b = _summary(subset, [r[i] for i in idx])
        paired[f"{left}_to_{right}"] = {
            "samples": len(idx),
            "excluded_samples": len(rows) - len(idx),
            "status": "full_pair" if len(idx) == len(rows) else "diagnostic_intersection_only",
            "mae_log_macro_channel_delta_right_minus_left": b["metrics"]["mae_log_macro_channel"]
            - a["metrics"]["mae_log_macro_channel"]
            if idx
            else None,
            "left": a,
            "right": b,
        }
    result["paired_differences"] = paired
    return result

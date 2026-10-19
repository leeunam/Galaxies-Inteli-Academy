"""Development-only metrics, sharing the exact q50-preserving inference policy."""

from collections import Counter

import numpy as np

from scripts.channel_partitions import ExperimentError
from scripts.empirical_baseline import MAX_LOG_VIEWS

QUANTILES = (0.1, 0.5, 0.9)
REPAIR_POLICY = "lower_min_raw_upper_max_raw_preserve_q50_v1"


def checked_logs(values):
    values = np.asarray(values, dtype=float)
    if (
        values.ndim != 2
        or values.shape[1] != 3
        or not len(values)
        or not np.isfinite(values).all()
        or np.any(values < 0)
        or np.any(values > MAX_LOG_VIEWS)
    ):
        raise ExperimentError("invalid_quantile_predictions")
    return values


def repair_quantiles(raw):
    """Never sort the central prediction away; reject nonphysical/overflow values."""
    raw = checked_logs(raw)
    return np.column_stack((raw.min(axis=1), raw[:, 1], raw.max(axis=1)))


def views_from_logs(values):
    result = np.expm1(checked_logs(values))
    if not np.isfinite(result).all():
        raise ExperimentError("invalid_inverse_target")
    return result


def channel_weights(channel_ids):
    counts = Counter(channel_ids)
    return np.array([1.0 / counts[c] for c in channel_ids])


def macro_mean(values, channel_ids):
    return float(np.average(values, weights=channel_weights(channel_ids)))


def pinball(targets, predictions, quantile):
    residual = np.asarray(targets) - np.asarray(predictions)
    return np.maximum(quantile * residual, (quantile - 1) * residual)


def selection_score(targets, predictions, channel_ids, quantile):
    errors = (
        np.abs(np.asarray(targets) - predictions)
        if quantile == 0.5
        else pinball(targets, predictions, quantile)
    )
    if not np.isfinite(errors).all():
        raise ExperimentError("nonfinite_selection_score")
    return macro_mean(errors, channel_ids)


def _ranks(values):
    # Average ranks for ties, without adding another runtime dependency.
    return np.array([1 + np.sum(values < v) + (np.sum(values == v) - 1) / 2 for v in values])


def _ranking(y, predicted):
    comparable = correct = 0
    for i in range(len(y)):
        for j in range(i + 1, len(y)):
            if y[i] == y[j]:
                continue
            comparable += 1
            correct += (
                0.5
                if predicted[i] == predicted[j]
                else float(np.sign(y[i] - y[j]) == np.sign(predicted[i] - predicted[j]))
            )
    supported = len(y) >= 3 and len(set(y)) > 1 and len(set(predicted)) > 1
    return {
        "spearman": float(np.corrcoef(_ranks(y), _ranks(predicted))[0, 1]) if supported else None,
        "spearman_status": "estimable" if supported else "insufficient_support_or_variation",
        "pair_accuracy": correct / comparable if comparable else None,
        "comparable_pairs": comparable,
    }


def _summary(y, predicted, channels):
    original, predicted_views = np.expm1(y), views_from_logs(predicted)
    errors = np.abs(y - predicted[:, 1])
    positive = original > 0
    covered = (y >= predicted[:, 0]) & (y <= predicted[:, 2])
    return {
        "samples": len(y),
        "channels": len(set(channels)),
        "mae_log_macro_channel": macro_mean(errors, channels),
        "mae_log_micro": float(errors.mean()),
        "mae_views_micro": float(np.abs(original - predicted_views[:, 1]).mean()),
        "mape_positive_views": float(
            np.mean(np.abs(original[positive] - predicted_views[positive, 1]) / original[positive])
        )
        if np.any(positive)
        else None,
        "mape_excluded_zero_views": int(np.sum(~positive)),
        "pinball_log_macro_channel": {
            str(q): macro_mean(pinball(y, predicted[:, i], q), channels)
            for i, q in enumerate(QUANTILES)
        },
        "coverage_micro": float(covered.mean()),
        "coverage_macro_channel": macro_mean(covered, channels),
        "mean_width_views": float((predicted_views[:, 2] - predicted_views[:, 0]).mean()),
        "mean_width_log": float((predicted[:, 2] - predicted[:, 0]).mean()),
    }


def evaluate_development(split, raw, *, repair=True):
    raw = checked_logs(raw)
    if len(raw) != len(split.targets):
        raise ExperimentError("prediction_rows_mismatch")
    predicted = repair_quantiles(raw) if repair else raw
    y = np.array([np.log1p(t.view_count) for t in split.targets])
    channels, sectors = np.array(split.channel_ids), np.array([p.sector for p in split.inputs])
    result = _summary(y, predicted, channels)
    result["crossing_rows_raw"] = int(np.sum((raw[:, 0] > raw[:, 1]) | (raw[:, 1] > raw[:, 2])))
    result["by_sector"] = {
        sector: _summary(
            y[sectors == sector], predicted[sectors == sector], channels[sectors == sector]
        )
        for sector in sorted(set(sectors))
    }
    result["by_channel"] = {
        channel: _summary(
            y[channels == channel], predicted[channels == channel], channels[channels == channel]
        )
        | _ranking(y[channels == channel], predicted[channels == channel, 1])
        for channel in sorted(set(channels))
    }
    rankings = list(result["by_channel"].values())
    for metric in ("spearman", "pair_accuracy"):
        available = [r[metric] for r in rankings if r[metric] is not None]
        result[f"{metric}_macro_channel"] = float(np.mean(available)) if available else None
        result[f"{metric}_supported_channels"] = len(available)
    result["ranking_ties"] = "exclude_target_ties_prediction_ties_half_credit"
    result["global_spearman_secondary"] = _ranking(y, predicted[:, 1])["spearman"]
    return result

"""Analytical invented cases; never read a cohort or load a trained model."""

import math

import numpy as np
import pytest
from pydantic import ValidationError

from scripts.channel_partitions import ExperimentError
from scripts.final_evaluation_metrics import (
    REQUIRED_MODELS,
    EvaluationRow,
    ModelPredictions,
    Prediction,
    evaluate_predictions,
)


def fixture(views=(0, 3, 15, 3), channels=("a", "a", "a", "b")):
    rows = tuple(
        EvaluationRow(sample_id=f"s{i}", channel_id=c, sector="moda", view_count=v)
        for i, (v, c) in enumerate(zip(views, channels, strict=True))
    )
    models = tuple(
        ModelPredictions(
            name=name,
            artifact_sha256="a" * 64,
            predictions=tuple(
                Prediction(sample_id=r.sample_id, raw_log_quantiles=(0.0, 0.0, math.log(16)))
                for r in rows
            ),
        )
        for name in REQUIRED_MODELS
    )
    return rows, models


def test_analytical_macro_micro_mape_coverage_pinball_and_width():
    rows, models = fixture()
    result = evaluate_predictions(rows, models, expected_count=4)
    a = result["models"]["A300"]
    m = a["metrics"]
    assert m["mae_log_macro_channel"] == pytest.approx(math.log(4))
    assert m["mae_log_micro"] == pytest.approx(math.log(4))
    assert m["mae_views_micro"] == pytest.approx(21 / 4)
    assert m["mae_views_macro_channel"] == pytest.approx((6 + 3) / 2)
    assert m["mape_positive_views"] == 1
    assert m["mape_excluded_zero_views"] == 1
    assert m["mape_included_samples"] == 3
    assert m["pinball_log_macro_channel"]["0.5"] == pytest.approx(math.log(4) / 2)
    assert m["coverage_micro"] == m["coverage_macro_channel"] == 1
    assert m["mean_width_views"] == pytest.approx(15)
    assert m["mean_width_log"] == pytest.approx(math.log(16))
    assert result["complete_all_models"]
    assert not result["selection_performed"]
    assert result["models"]["B0"]["range_kind"] == "empirical_training_sector_range"
    assert a["by_sector"]["beleza"]["status"] == "no_predictions"
    assert a["by_sector"]["beleza"]["expected_samples"] == 0


def test_macro_gives_each_available_channel_equal_weight():
    rows, models = fixture(views=(0, 0, 0, 15))
    a = evaluate_predictions(rows, models, expected_count=4)["models"]["A300"]["metrics"]
    assert a["mae_log_macro_channel"] == pytest.approx(math.log(16) / 2)
    assert a["mae_log_micro"] == pytest.approx(math.log(16) / 4)


def test_raw_crossing_preserves_q50_and_keeps_raw_evidence():
    rows, models = fixture()
    raw = (3.0, 1.0, 0.0)
    models = tuple(
        m.model_copy(
            update={
                "predictions": tuple(
                    Prediction(sample_id=r.sample_id, raw_log_quantiles=raw) for r in rows
                )
            }
        )
        for m in models
    )
    a = evaluate_predictions(rows, models, expected_count=4)["models"]["A300"]
    assert a["metrics"]["crossing_rows_raw"] == 4
    assert a["cases"][0]["raw_log_quantiles"] == raw
    assert a["cases"][0]["served_log_quantiles"] == [0.0, 1.0, 3.0]


def test_ties_support_and_prediction_half_credit():
    rows, models = fixture()
    a = evaluate_predictions(rows, models, expected_count=4)["models"]["A300"]
    assert a["ranking"]["spearman_macro_channel"] is None
    assert a["ranking"]["spearman_supported_channels"] == 0
    assert a["ranking"]["spearman_macro_channel_status"] == (
        "no_channel_with_required_support_or_variation"
    )
    assert a["by_channel"]["a"]["ranking"]["spearman_status_by_channel"]["a"] == (
        "insufficient_support_or_variation"
    )
    assert a["ranking"]["global_spearman_secondary_status"] == "insufficient_support_or_variation"
    assert a["ranking"]["comparable_pairs"] == 3
    assert a["ranking"]["pair_accuracy_macro_channel"] == 0.5
    models = tuple(
        m.model_copy(
            update={
                "predictions": tuple(
                    Prediction(
                        sample_id=r.sample_id,
                        raw_log_quantiles=(0.0, math.log1p(r.view_count), 4.0),
                    )
                    for r in rows
                )
            }
        )
        for m in models
    )
    a = evaluate_predictions(rows, models, expected_count=4)["models"]["A300"]
    assert a["ranking"]["spearman_macro_channel"] == pytest.approx(1)
    assert a["ranking"]["spearman_supported_channels"] == 1
    assert a["ranking"]["spearman_macro_channel_status"] == "estimable"
    assert a["by_channel"]["b"]["ranking"]["spearman_status_by_channel"]["b"] == (
        "insufficient_support_or_variation"
    )


def test_failures_keep_denominators_and_comparisons_use_declared_intersection():
    rows, models = fixture()
    models = list(models)
    predictions = list(models[3].predictions)
    predictions[-1] = Prediction(sample_id="s3", failure_code="missing_features")
    models[3] = models[3].model_copy(update={"predictions": tuple(predictions)})
    result = evaluate_predictions(rows, models, expected_count=4)
    b = result["models"]["B_FULL_VLM"]
    assert not result["complete_all_models"]
    assert b["status"] == "partial"
    assert (b["expected_samples"], b["available_samples"], b["failed_samples"]) == (4, 3, 1)
    assert b["by_channel"]["b"]["metrics"] is None
    assert b["cases"][-1]["failure_code"] == "missing_features"
    paired = result["paired_differences"]["A300_to_B_FULL_VLM"]
    assert (paired["samples"], paired["excluded_samples"]) == (3, 1)
    assert paired["status"] == "diagnostic_intersection_only"
    assert paired["mae_log_macro_channel_delta_right_minus_left"] == 0


def test_all_failures_and_zero_targets_produce_nulls_not_invented_metrics():
    rows, models = fixture(views=(0, 0, 0, 0))
    result = evaluate_predictions(rows, models, expected_count=4)
    assert result["models"]["A300"]["metrics"]["mape_positive_views"] is None
    models = tuple(
        m.model_copy(
            update={
                "predictions": tuple(
                    Prediction(sample_id=r.sample_id, failure_code="inference_failed") for r in rows
                )
            }
        )
        for m in models
    )
    result = evaluate_predictions(rows, models, expected_count=4)
    assert result["models"]["A300"]["metrics"] is None
    assert result["models"]["A300"]["largest_errors"]["log"] == []
    assert result["paired_differences"]["A300_to_B_FULL_VLM"]["left"]["metrics"] is None


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r, m: (r, m[:-1]),
        lambda r, m: (r, (*m, m[0])),
        lambda r, m: (r[::-1], m),
        lambda r, m: (r, (m[0].model_copy(update={"predictions": m[0].predictions[:-1]}), *m[1:])),
        lambda r, m: (
            r,
            (
                m[0].model_copy(
                    update={"predictions": tuple(Prediction(sample_id=row.sample_id) for row in r)}
                ),
                *m[1:],
            ),
        ),
    ],
)
def test_rejects_missing_models_rows_order_and_silent_failures(mutate):
    rows, models = fixture()
    rows, models = mutate(rows, models)
    with pytest.raises(ExperimentError):
        evaluate_predictions(rows, models, expected_count=4)


@pytest.mark.parametrize("raw", [(-1.0, 1.0, 2.0), (0.0, 1.0, 100.0), (0.0, np.nan, 2.0)])
def test_invalid_quantiles_are_never_silently_clipped(raw):
    rows, models = fixture()
    with pytest.raises((ExperimentError, ValidationError)):
        predictions = tuple(Prediction(sample_id=r.sample_id, raw_log_quantiles=raw) for r in rows)
        models = (models[0].model_copy(update={"predictions": predictions}), *models[1:])
        evaluate_predictions(rows, models, expected_count=4)


def test_default_count_is_31_and_in_memory_arithmetic_does_not_open_files(monkeypatch):
    rows, models = fixture()
    with pytest.raises(ExperimentError, match="evaluation_count_mismatch"):
        evaluate_predictions(rows, models)

    def fail(*a, **kw):
        raise AssertionError("unexpected file access")

    monkeypatch.setattr("builtins.open", fail)
    result = evaluate_predictions(rows, models, expected_count=4)
    assert result["contains_private_case_diagnostics"]

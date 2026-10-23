import math

import pytest

from scripts.channel_partitions import ExperimentError
from scripts.compare_full_models import select_validation


def metrics(mae=2.0, losses=(0.5, 1.0, 0.6)):
    return {
        "mae_log_macro_channel": mae,
        "pinball_log_macro_channel": dict(zip(("0.1", "0.5", "0.9"), losses, strict=True)),
    }


def test_lower_mae_alone_does_not_allow_promotion_and_negative_result_is_valid():
    report = select_validation(
        metrics(), {"B_FULL_VLM": metrics(1.9, (0.9, 0.95, 0.9)), "C_FULL_VLM": metrics(2.1)}
    )
    assert report["selected_experiment"] == "A300"
    assert report["candidates"]["B_FULL_VLM"]["rejection_reasons"] == [
        "mean_pinball_worse_than_A300"
    ]
    assert not report["served_model_replaced"] and not report["test_evaluated"]


def test_rule_uses_mean_three_quantiles_including_equal_mean_and_strict_mae():
    reference = metrics(2.0, (0.3, 0.6, 0.9))
    report = select_validation(
        reference,
        {"B_FULL_VLM": metrics(1.0, (0.6, 0.6, 0.6)), "C_FULL_VLM": metrics(2.0, (0.1, 0.1, 0.1))},
    )
    # q10 may worsen when the mean does not; MAE equality still fails.
    assert report["selected_experiment"] == "B_FULL_VLM"
    assert report["candidates"]["C_FULL_VLM"]["eligible"] is False


def test_eligible_minimum_and_exact_tie_favor_catboost():
    candidates = {"B_FULL_VLM": metrics(1.5), "C_FULL_VLM": metrics(1.5)}
    assert select_validation(metrics(), candidates)["selected_experiment"] == "B_FULL_VLM"
    candidates["C_FULL_VLM"] = metrics(1.4)
    assert select_validation(metrics(), candidates)["selected_experiment"] == "C_FULL_VLM"


@pytest.mark.parametrize("value", [math.nan, math.inf, -1, True, None])
def test_invalid_metrics_cannot_select(value):
    with pytest.raises(ExperimentError, match="finite_validation"):
        select_validation(metrics(value), {"B_FULL_VLM": metrics(), "C_FULL_VLM": metrics()})


def test_cache_only_or_missing_candidate_cannot_substitute_for_full_comparison():
    with pytest.raises(ExperimentError, match="both_complete"):
        select_validation(metrics(), {"B_cache_300": metrics(), "C_cache_300": metrics()})

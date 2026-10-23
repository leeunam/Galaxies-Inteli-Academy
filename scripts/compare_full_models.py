"""Development comparison and the proposal's deterministic selection rule."""

from math import fsum, isfinite

from scripts.channel_partitions import ExperimentError, digest
from scripts.train_experiment_b import compare as compare_cached
from scripts.train_experiment_c_full import compare as compare_c

COMPLETE = ("B_FULL_VLM", "C_FULL_VLM")


def _scores(metrics):
    try:
        mae = metrics["mae_log_macro_channel"]
        losses = [metrics["pinball_log_macro_channel"][str(q)] for q in (0.1, 0.5, 0.9)]
        if any(type(v) not in (int, float) or not isfinite(v) or v < 0 for v in (mae, *losses)):
            raise ValueError
        return mae, fsum(losses) / 3
    except (KeyError, TypeError, ValueError, OverflowError):
        raise ExperimentError("selection_requires_finite_validation_metrics") from None


def select_validation(reference, candidates):
    """Called only after pairing accepted full bundles; cache experiments are ineligible."""
    if set(candidates) != set(COMPLETE):
        raise ExperimentError("selection_requires_both_complete_models")
    baseline_mae, baseline_loss = _scores(reference)
    checked = {}
    for name in COMPLETE:
        mae, loss = _scores(candidates[name])
        reasons = []
        if mae >= baseline_mae:
            reasons.append("mae_log_not_strictly_lower_than_A300")
        if loss > baseline_loss:
            reasons.append("mean_pinball_worse_than_A300")
        checked[name] = {
            "mae_log_macro_channel": mae,
            "mean_pinball_log_macro_channel": loss,
            "eligible": not reasons,
            "rejection_reasons": reasons,
        }
    eligible = [name for name in COMPLETE if checked[name]["eligible"]]
    selected = (
        min(eligible, key=lambda n: (checked[n]["mae_log_macro_channel"], COMPLETE.index(n)))
        if eligible
        else "A300"
    )
    value = {
        "schema_version": "full-model-validation-selection-v1",
        "partition": "validation",
        "reference": "A300",
        "reference_mae_log_macro_channel": baseline_mae,
        "reference_mean_pinball_log_macro_channel": baseline_loss,
        "candidates": checked,
        "selected_experiment": selected,
        "tie_break": "CatBoost_B_before_LightGBM_C",
        "validation_used_for_selection": True,
        "independent_quality_estimate": False,
        "test_evaluated": False,
        "served_model_replaced": False,
    }
    return value | {"decision_sha256": digest(value)}


def compare_complete(data, old_data, a300, a200, cached_b, full_b, full_c):
    # This validates full B/C identity and their source/runtime contracts first.
    paired = compare_c(data, full_b, full_c, original_validation_ids=old_data.validation.sample_ids)
    report = compare_cached(data.cached, old_data, cached_b, a300, a200)
    if set(data.base.train.channel_ids) & set(data.base.validation.channel_ids):
        raise ExperimentError("bcanal_fallback_requires_reserved_channels")
    for group, content in report["groups"].items():
        if not content.get("models"):
            continue
        models = content["models"]
        # Keep established comparator names and also expose the complete B/C names.
        models["B_FULL_VLM"] = paired["groups"][group]["models"]["B_FULL_VLM"]
        models["C_FULL_VLM"] = paired["groups"][group]["models"]["C_FULL_VLM"]
        models["Bcanal_300"] = models["B0_300"] | {
            "channel_training_support": False,
            "fallback": "B0_300",
        }
    metrics = report["groups"]["all_validation"]["models"]
    report.update(
        schema_version="full-model-comparison-and-selection-v1",
        vlm_used=True,
        released_vlm_fields=data.release.released_fields,
        quality_release_sha256=data.release.release_sha256,
        input_policy=data.release.input_policy,
        data_kind=paired["data_kind"],
        real_results_available=paired["real_results_available"],
        pairing_sha256=paired["pairing_sha256"],
        model_artifact_sha256=paired["model_artifact_sha256"]
        | {
            "A300": a300.artifact.artifact_sha256,
            "A200": a200.artifact.artifact_sha256,
            "B_cache_300": cached_b.artifact.artifact_sha256,
        },
        selection=select_validation(
            metrics["A300"]["metrics"], {n: metrics[n]["metrics"] for n in COMPLETE}
        ),
        served_model_replaced=False,
        full_B_C_observed_comparison=paired["real_results_available"],
    )
    report["comparison_sha256"] = digest(report)
    return report

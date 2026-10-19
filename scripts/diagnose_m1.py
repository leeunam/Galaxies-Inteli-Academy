"""Read-only M1 diagnosis on frozen train/validation, without opening test evidence.

Partition/cohort metadata and the evidence path index locate allowed IDs. The mixed
records/predictor files are deliberately not read. Only selected evidence is opened.
No fitting, collection, SHAP, model replacement or production behavior change.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np
from catboost import Pool

from scripts.channel_partitions import ExperimentError, digest, load_partitions
from scripts.empirical_baseline import TrainingTarget, estimate_baseline
from scripts.experiment_a_artifact import load_bundle
from scripts.experiment_a_data import (
    CATEGORICAL_INDICES,
    FEATURE_NAMES,
    DevelopmentData,
    DevelopmentSplit,
    check_extractor_runtime,
    feature_matrix,
    split_digest,
    validate_development_data,
)
from scripts.experiment_a_metrics import evaluate_development, macro_mean
from scripts.observed_baseline import load_observed_baseline, observation_digest, read_json
from scripts.training_manifest import PredictorInputs


def load_diagnostic_data(cohort_dir: Path, evidence_root: Path):
    """Open evidence only after selecting train/validation IDs from the manifest."""
    cohort_dir, evidence_root = Path(cohort_dir), Path(evidence_root).resolve()
    release, baseline = load_observed_baseline(cohort_dir)
    manifest = load_partitions(cohort_dir / "partitions.json")
    config = json.loads(read_json(cohort_dir / "extractor-config.json"))
    check_extractor_runtime(config, Path(__file__).parent)
    index = json.loads(read_json(cohort_dir / "evidence-index.json"))
    metadata = {r.sample_id: r for r in release.records}
    opened = []

    def split(name):
        rows = [r for r in manifest.assignments if r.partition == name]
        inputs, targets = [], []
        for assignment in rows:
            record, entry = metadata[assignment.sample_id], index[assignment.sample_id]
            curation = entry["curation"]
            if digest(curation) != record.curation_evidence_sha256:
                raise ExperimentError("diagnostic_curation_mismatch")
            raw = []
            for key, checksum in (("features_ref", "features_sha256"), ("run_ref", "run_sha256")):
                relative = Path(entry[key])
                path = (evidence_root / relative).resolve()
                if relative.is_absolute() or not path.is_relative_to(evidence_root):
                    raise ExperimentError("unsafe_diagnostic_evidence_path")
                value = read_json(path)
                if hashlib.sha256(value).hexdigest() != curation[checksum]:
                    raise ExperimentError("diagnostic_evidence_mismatch")
                opened.append(str(path))
                raw.append(json.loads(value))
            features, run = raw
            count = run["source"]["target"]["view_count_observed"]
            target = TrainingTarget(sample_id=record.sample_id, view_count=count)
            expected_audit = {
                "video_id": record.sample_id,
                "channel_id": record.channel_id,
                "source_url": record.source_url,
                "published_at_utc": record.published_at_utc,
                "observed_at_utc": record.observed_at_utc,
            }
            if (
                observation_digest(record.model_dump(), count) != record.frozen_observation_sha256
                or run["source"]["audit"] != expected_audit
                or run["models"] != config["models"]
                or run["status"] != "completed"
                or run["temporary_directory_removed"] is not True
                or any(
                    features["properties"][key] != getattr(record, key)
                    for key in ("duration_seconds", "width", "height")
                )
            ):
                raise ExperimentError("diagnostic_observation_mismatch")
            vector = features["text_embedding"]
            inputs.append(
                PredictorInputs(
                    sector=record.sector,
                    duration_seconds=record.duration_seconds,
                    aspect_ratio_height_over_width=record.height / record.width,
                    text_status=features["text_features_status"],
                    text_embedding=tuple(vector) if vector is not None else None,
                )
            )
            targets.append(target)
        return DevelopmentSplit(
            partition=name,
            sample_ids=tuple(r.sample_id for r in rows),
            channel_ids=tuple(r.channel_id for r in rows),
            inputs=tuple(inputs),
            targets=tuple(targets),
        )

    data = DevelopmentData(
        manifest, release.release_sha256, config, baseline, split("train"), split("validation")
    )
    validate_development_data(data)
    return data, opened


def view_distribution(values):
    values = np.asarray(values, dtype=float)
    if not len(values):
        return {"samples": 0, "status": "not_estimable"}
    return {
        "samples": len(values),
        "zero_views": int(np.sum(values == 0)),
        "quantiles_views": {
            str(q): float(np.quantile(values, q)) for q in (0, 0.1, 0.5, 0.9, 0.95, 1)
        },
        "mean_views": float(values.mean()),
        "at_least_100k": int(np.sum(values >= 100_000)),
        "at_least_1m": int(np.sum(values >= 1_000_000)),
    }


def error_slice(actual, logs, channels):
    actual, logs = np.asarray(actual, dtype=float), np.asarray(logs)
    if not len(actual):
        return {"samples": 0, "status": "not_estimable"}
    central = np.expm1(logs[:, 1])
    signed = logs[:, 1] - np.log1p(actual)
    return {
        "samples": len(actual),
        "channels": len(set(channels)),
        "mae_log_macro_channel": macro_mean(np.abs(signed), channels),
        "signed_error_log_macro_channel": macro_mean(signed, channels),
        "underprediction_fraction": float(np.mean(central < actual)),
        "median_actual_plus_one_over_predicted_plus_one": float(
            np.median((actual + 1) / (central + 1))
        ),
        "interval_upper_miss_fraction": float(np.mean(actual > np.expm1(logs[:, 2]))),
        "coverage": float(
            np.mean((np.log1p(actual) >= logs[:, 0]) & (np.log1p(actual) <= logs[:, 2]))
        ),
        "predicted_q50_views": view_distribution(central),
    }


def model_structure(bundle, data):
    """Audit native log outputs and conservative tree-sum bounds, not an interval."""
    matrix = feature_matrix(
        data.train.inputs + data.validation.inputs,
        supported_text_statuses=bundle.artifact.supported_text_statuses,
    )
    pool = Pool(matrix, cat_features=list(CATEGORICAL_INDICES), feature_names=list(FEATURE_NAMES))
    result = []
    for model, selected in zip(bundle.models, bundle.artifact.selected, strict=True):
        scale, bias = model.get_scale_and_bias()
        leaves, counts = model.get_leaf_values(), model.get_tree_leaf_counts()
        indices = model.calc_leaf_indexes(pool, thread_count=2)
        offset, lower, upper = 0, 0.0, 0.0
        reconstructed = np.zeros(len(matrix))
        for column, count in enumerate(counts):
            count = int(count)
            tree = leaves[offset : offset + count]
            lower += min(scale * tree.min(), scale * tree.max())
            upper += max(scale * tree.min(), scale * tree.max())
            reconstructed += tree[indices[:, column]]
            offset += count
        expected = model.predict(pool, thread_count=2)
        discrepancy = float(np.max(np.abs(scale * reconstructed + bias - expected)))
        if discrepancy > 1e-10:
            raise ExperimentError("native_prediction_reconstruction_mismatch")
        importance = model.get_feature_importance(type="PredictionValuesChange", thread_count=2)
        result.append(
            {
                "quantile": selected.quantile,
                "trees": model.tree_count_,
                "scale": float(scale),
                "initial_bias_log": float(bias),
                "initial_bias_views": math.expm1(bias),
                "tree_sum_conservative_lower_log": float(bias + lower),
                "tree_sum_conservative_upper_log": float(bias + upper),
                "tree_sum_conservative_upper_views": math.expm1(bias + upper)
                if bias + upper < 709
                else None,
                "native_reconstruction_max_abs_error": discrepancy,
                "prediction_values_change_by_group": {
                    "sector": float(importance[0]),
                    "duration": float(importance[1]),
                    "aspect_ratio": float(importance[2]),
                    "text_status": float(importance[3]),
                    "speech_embedding": float(sum(importance[4:])),
                },
            }
        )
    return result


def diagnose(data: DevelopmentData, bundle):
    validate_development_data(data)
    if (
        split_digest(data.train) != bundle.artifact.train_split_sha256
        or split_digest(data.validation) != bundle.artifact.validation_split_sha256
    ):
        raise ExperimentError("diagnostic_split_digest_mismatch")
    thresholds = {
        sector: float(
            np.quantile(
                [
                    t.view_count
                    for p, t in zip(data.train.inputs, data.train.targets, strict=True)
                    if p.sector == sector
                ],
                0.9,
            )
        )
        for sector in ("moda", "beleza")
    }
    summary, rows = {}, []
    for name in ("train", "validation"):
        split = getattr(data, name)
        logs = bundle.predict_logs(split.inputs)
        actual = np.array([t.view_count for t in split.targets])
        sectors, channels = np.array([p.sector for p in split.inputs]), np.array(split.channel_ids)
        high = np.array([v >= thresholds[s] for v, s in zip(actual, sectors, strict=True)])
        baseline_logs = np.array(
            [
                [stats.q10_log1p, stats.q50_log1p, stats.q90_log1p]
                for value in split.inputs
                for stats in data.baseline.sectors
                if stats.sector == value.sector
            ]
        )
        summary[name] = {
            "observed_views": view_distribution(actual),
            "model": evaluate_development(split, bundle.predict_logs(split.inputs, repaired=False)),
            "upper_training_sector_decile": error_slice(actual[high], logs[high], channels[high]),
            "other_rows": error_slice(actual[~high], logs[~high], channels[~high]),
            "baseline_mae_log_macro_channel": evaluate_development(
                split, baseline_logs, repair=False
            )["mae_log_macro_channel"],
            "baseline_upper_training_sector_decile": error_slice(
                actual[high], baseline_logs[high], channels[high]
            ),
            "by_sector": {
                s: {
                    "observed_views": view_distribution(actual[sectors == s]),
                    "upper_training_sector_decile": error_slice(
                        actual[high & (sectors == s)],
                        logs[high & (sectors == s)],
                        channels[high & (sectors == s)],
                    ),
                }
                for s in ("moda", "beleza")
            },
        }
        for sample, channel, sector, target, predicted in zip(
            split.sample_ids, split.channel_ids, sectors, actual, logs, strict=True
        ):
            rows.append(
                {
                    "partition": name,
                    "sample_id": sample,
                    "channel_id": str(channel),
                    "sector": str(sector),
                    "actual_views": int(target),
                    "predicted_views": np.expm1(predicted).tolist(),
                    "upper_training_sector_decile": bool(target >= thresholds[sector]),
                }
            )
    # Neighbors are selected solely by cosine on speech, within the same sector.
    # Their outcomes are descriptive, not a newly selected/served prediction model.
    if any(p.text_embedding is None for p in data.train.inputs + data.validation.inputs):
        raise ExperimentError("diagnostic_embedding_unusable")
    vectors = np.asarray([p.text_embedding for p in data.train.inputs], dtype=float)
    if not np.isfinite(vectors).all() or np.any(np.linalg.norm(vectors, axis=1) == 0):
        raise ExperimentError("diagnostic_embedding_unusable")
    nearest = []
    for i, value in enumerate(data.validation.inputs):
        candidates = [j for j, p in enumerate(data.train.inputs) if p.sector == value.sector]
        v = np.asarray(value.text_embedding)
        if not np.isfinite(v).all() or np.linalg.norm(v) == 0:
            raise ExperimentError("diagnostic_embedding_unusable")
        similarity = vectors @ v / (np.linalg.norm(vectors, axis=1) * np.linalg.norm(v))
        ordered = sorted(candidates, key=lambda j: (-similarity[j], data.train.sample_ids[j]))[:5]
        nearest.append(
            {
                "validation_id": data.validation.sample_ids[i],
                "training_neighbors": [
                    {
                        "sample_id": data.train.sample_ids[j],
                        "cosine": float(similarity[j]),
                        "observed_views": data.train.targets[j].view_count,
                    }
                    for j in ordered
                ],
            }
        )
    return {
        "schema_version": "m1-underprediction-diagnostic-v1",
        "model_artifact_sha256": bundle.artifact.artifact_sha256,
        "evaluated_partitions": ["train", "validation"],
        "model_refitted": False,
        "test_evidence_opened": False,
        "test_predictions_or_metrics_computed": False,
        "high_reach_diagnostic_rule": "observed_views_ge_sector_train_p90_not_viral_classifier",
        "sector_train_p90_views": thresholds,
        "splits": summary,
        "model_structure": model_structure(bundle, data),
        "training_embedding_dimension": vectors.shape[1],
        "training_constant_embedding_dimensions": int(np.sum(np.ptp(vectors, axis=0) == 0)),
        "training_embedding_norm_range": [
            float(np.linalg.norm(vectors, axis=1).min()),
            float(np.linalg.norm(vectors, axis=1).max()),
        ],
        "baselines": [
            estimate_baseline(data.baseline, s).model_dump(mode="json") for s in ("moda", "beleza")
        ],
        "private_rows": rows,
        "private_validation_neighbors": nearest,
    }


def private_output(destination: Path, mode="w"):
    """Create once, with private permissions from the first byte."""
    return os.fdopen(os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), mode)


def write_plot(report, destination: Path):
    """Standalone scientific plot; individual rows remain in the private report."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = report["private_rows"]
    largest = max(max(r["actual_views"], r["predicted_views"][1]) for r in rows)
    end = np.log10(largest + 1) + 0.15
    ticks = [0, 10, 100, 1000, 10000, 100000, 1000000]
    labels = ["0", "10", "100", "1 mil", "10 mil", "100 mil", "1 mi"]
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 6.1), sharex=True, sharey=True)
    for ax, partition in zip(axes, ("train", "validation"), strict=True):
        selected = [r for r in rows if r["partition"] == partition]
        for sector, color in (("moda", "#126e9c"), ("beleza", "#c45b32")):
            group = [r for r in selected if r["sector"] == sector]
            ax.scatter(
                np.log10([r["actual_views"] + 1 for r in group]),
                np.log10([r["predicted_views"][1] + 1 for r in group]),
                label=sector.capitalize(),
                color=color,
                s=38,
                alpha=0.78,
                edgecolors="white",
                linewidth=0.4,
            )
        ax.plot(
            [0, end],
            [0, end],
            linestyle="--",
            color="#606a74",
            linewidth=1,
            label="Previsão = observado",
        )
        name = "Treino" if partition == "train" else "Validação"
        ax.set_title(
            f"{name} · {len(selected)} vídeos / {len({r['channel_id'] for r in selected})} canais",
            loc="left",
            fontsize=13,
        )
        ax.set_xlim(-0.05, end)
        ax.set_ylim(-0.05, end)
        ax.set_xticks(np.log10(np.asarray(ticks) + 1), labels, rotation=30, ha="right")
        ax.set_yticks(np.log10(np.asarray(ticks) + 1), labels)
        ax.set_xlabel("Views observadas", fontsize=11)
        ax.grid(alpha=0.12)
        ax.set_axisbelow(True)
        for edge in ("top", "right"):
            ax.spines[edge].set_visible(False)
    axes[0].set_ylabel("Views estimadas por M1 (q50)", fontsize=11)
    axes[0].legend(loc="upper left", frameon=False, fontsize=10)
    fig.suptitle(
        "M1 comprime as previsões e perde os casos de maior alcance",
        x=0.07,
        ha="left",
        fontsize=16,
        fontweight="bold",
    )
    fig.text(
        0.07,
        0.025,
        "Modelo congelado · eixos em log10(views + 1) · somente treino e validação · sem reestimativa",
        fontsize=10,
        color="#4f5964",
    )
    fig.tight_layout(rect=(0.025, 0.06, 1, 0.93))
    try:
        with private_output(destination, "wb") as output:
            fig.savefig(output, format="png", dpi=160)
    finally:
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cohort-dir", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--evidence-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--plot", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("use a fresh output path")
    data, opened = load_diagnostic_data(args.cohort_dir, args.evidence_root)
    bundle = load_bundle(
        args.model_dir,
        expected_extractor_config=data.extractor_config,
        expected_partition_sha256=data.manifest.manifest_sha256,
        expected_cohort_sha256=data.cohort_sha256,
    )
    report = diagnose(data, bundle)
    report["private_evidence_files_opened"] = opened
    args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with private_output(args.output) as output:
        json.dump(report, output, indent=2, allow_nan=False)
    if args.plot is not None:
        if args.plot.exists():
            raise ExperimentError("plot_already_exists")
        args.plot.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        write_plot(report, args.plot)
    print(
        json.dumps(
            {
                "train_rows": len(data.train.inputs),
                "validation_rows": len(data.validation.inputs),
                "evidence_files_opened": len(opened),
                "test_evidence_opened": False,
            }
        )
    )


if __name__ == "__main__":
    main()

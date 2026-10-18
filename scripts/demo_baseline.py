"""Offline, fully generated demonstration of partitions and empirical baselines."""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from pydantic import ValidationError

from scripts.channel_partitions import ExperimentError, freeze_partitions, load_partitions
from scripts.empirical_baseline import estimate_baseline, fit_baseline, load_baseline, save_baseline
from scripts.synthetic_baseline import synthetic_dataset


def run_demo(folder: Path):
    if folder.exists() and any(folder.iterdir()):
        raise ExperimentError("output_already_exists")
    references, outcomes = synthetic_dataset()
    path = folder / "partitions.json"
    freeze_partitions(references, path, data_kind="synthetic")
    manifest = load_partitions(path)
    training_targets = [
        {"sample_id": row.sample_id, "view_count": outcomes[row.sample_id]}
        for row in manifest.assignments
        if row.partition == "train"
    ]
    artifact = fit_baseline(manifest, training_targets)
    artifact_path = folder / "baseline.json"
    save_baseline(artifact_path, artifact)
    artifact = load_baseline(artifact_path, manifest, training_targets)
    train_row = next(row for row in manifest.assignments if row.partition == "train")
    estimates = [estimate_baseline(artifact, sector) for sector in ("moda", "beleza")]
    estimates += [
        estimate_baseline(
            artifact, train_row.sector, variant="Bcanal", channel_id=train_row.channel_id
        ),
        estimate_baseline(artifact, "moda", variant="Bcanal", channel_id="synthetic_new_channel"),
    ]
    return {
        "fixture": "synthetic",
        "scientific_status": "pending_issue_1",
        "real_results_available": False,
        "production_integration": "not_enabled",
        "manifest_sha256": manifest.manifest_sha256,
        "artifact_sha256": artifact.artifact_sha256,
        "partitions": [row.model_dump(mode="json") for row in manifest.support],
        "warnings": list(manifest.warnings) + list(artifact.warnings),
        "estimates": [estimate.model_dump(mode="json") for estimate in estimates],
        "explanation": (
            "Contagens inteiramente inventadas para verificar rotinas. "
            "Não são resultados reais; a faixa empírica não tem cobertura validada. "
            "O serviço Python/MCP permanece sem previsão real."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description="Demonstração sintética de partições e baseline")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    try:
        if args.output_dir is None:
            with TemporaryDirectory(prefix="galaxies-baseline-synthetic-") as folder:
                result = run_demo(Path(folder))
        else:
            result = run_demo(args.output_dir)
    except (ExperimentError, ValidationError, OSError):
        print(json.dumps({"status": "error", "code": "synthetic_demo_output_unavailable"}))
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

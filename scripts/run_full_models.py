"""Explicit local B/C operations; never acquires media, opens test or promotes a model."""

import argparse
import json
import os
from pathlib import Path

from scripts.channel_partitions import ExperimentError
from scripts.compare_full_models import compare_complete
from scripts.diagnose_m1 import load_diagnostic_data
from scripts.experiment_a_artifact import load_bundle as load_a
from scripts.experiment_b_artifact import load_bundle as load_cache
from scripts.experiment_b_vlm_data import feature_names
from scripts.experiment_c_full_data import assert_pairing, load_full_data, validate_full_data
from scripts.retrain_expansion import reserved_guard
from scripts.train_experiment_b_vlm import train_experiment as train_b
from scripts.train_experiment_c_full import load_bundle as load_c
from scripts.train_experiment_c_full import load_verified_b
from scripts.train_experiment_c_full import train_experiment as train_c


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("inspect", "train-b", "train-c", "compare"))
    for name in ("data-root", "parent", "cohort-dir", "queue", "quality-release"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    for name in ("b-dir", "c-dir", "a300-dir", "a200-dir", "bcache-dir", "report"):
        parser.add_argument(f"--{name}", type=Path)
    args = parser.parse_args(argv)
    required = {
        "inspect": (),
        "train-b": ("b_dir",),
        "train-c": ("b_dir", "c_dir"),
        "compare": ("b_dir", "c_dir", "a300_dir", "a200_dir", "bcache_dir", "report"),
    }[args.operation]
    if any(getattr(args, name) is None for name in required):
        parser.error("missing operation-specific artifact/report paths")
    destination = {"train-b": args.b_dir, "train-c": args.c_dir, "compare": args.report}.get(
        args.operation
    )
    if destination is not None and destination.exists():
        raise ExperimentError("full_model_output_already_exists")
    root = args.data_root.resolve()
    with reserved_guard(args.parent, root):
        data, opened = load_full_data(
            args.parent, args.cohort_dir, args.queue, args.quality_release, root
        )
        validate_full_data(data)
        if args.operation == "inspect":
            result = {
                "train": len(data.train),
                "validation": len(data.validation),
                "columns": len(feature_names(data.release)),
                "quality_release_sha256": data.release.release_sha256,
            }
        elif args.operation == "train-b":
            bundle, _ = train_b(data, args.b_dir)
            result = {"artifact_sha256": bundle.artifact.artifact_sha256}
        else:
            context = {
                "expected_extractor_config": data.base.extractor_config,
                "expected_cohort_sha256": data.base.cohort_sha256,
                "expected_partition_sha256": data.base.manifest.manifest_sha256,
            }
            b = load_verified_b(args.b_dir, data=data)
            assert_pairing(data, b.artifact)
            if args.operation == "train-c":
                bundle, _ = train_c(data, args.c_dir)
                result = {"artifact_sha256": bundle.artifact.artifact_sha256}
            else:
                old, _ = load_diagnostic_data(args.parent, root)
                a200 = load_a(
                    args.a200_dir,
                    expected_extractor_config=old.extractor_config,
                    expected_cohort_sha256=old.cohort_sha256,
                    expected_partition_sha256=old.manifest.manifest_sha256,
                )
                result = compare_complete(
                    data,
                    old,
                    load_a(args.a300_dir, **context),
                    a200,
                    load_cache(args.bcache_dir, **context),
                    b,
                    load_c(args.c_dir, data=data),
                )
                args.report.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                with args.report.open("x") as handle:
                    os.fchmod(handle.fileno(), 0o600)
                    handle.write(json.dumps(result, sort_keys=True, allow_nan=False) + "\n")
                result = {
                    "comparison_sha256": result["comparison_sha256"],
                    "selection": result["selection"],
                }
    print(
        json.dumps(
            result
            | {
                "holdout_opened": False,
                "served_model_replaced": False,
                "development_evidence_unique_paths": len(set(opened)),
            },
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

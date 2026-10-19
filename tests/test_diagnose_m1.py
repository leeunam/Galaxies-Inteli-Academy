import hashlib
import json
import os
import stat
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from scripts.channel_partitions import ExperimentError, digest
from scripts.diagnose_m1 import (
    diagnose,
    error_slice,
    load_diagnostic_data,
    model_structure,
    private_output,
    view_distribution,
    write_plot,
)
from scripts.experiment_a_data import split_digest
from tests.test_experiment_a_data import development_fixture

pytest_plugins = ["tests.test_experiment_a_data"]


def test_private_outputs_are_created_restrictively_and_never_overwritten(tmp_path):
    original_umask = os.umask(0)
    try:
        report = tmp_path / "report.json"
        with private_output(report) as output:
            assert stat.S_IMODE(os.fstat(output.fileno()).st_mode) == 0o600
            output.write("{}")
        with pytest.raises(FileExistsError):
            private_output(report)
        plot = tmp_path / "plot.png"
        write_plot(
            {
                "private_rows": [
                    {
                        "partition": partition,
                        "channel_id": "synthetic",
                        "sector": "moda",
                        "actual_views": 100,
                        "predicted_views": [0, 90, 1000],
                    }
                    for partition in ("train", "validation")
                ]
            },
            plot,
        )
        assert stat.S_IMODE(plot.stat().st_mode) == 0o600
        assert plot.read_bytes().startswith(b"\x89PNG")
        with pytest.raises(FileExistsError):
            write_plot(
                {
                    "private_rows": [
                        {
                            "partition": "train",
                            "channel_id": "synthetic",
                            "sector": "moda",
                            "actual_views": 100,
                            "predicted_views": [0, 90, 1000],
                        }
                    ]
                },
                plot,
            )
    finally:
        os.umask(original_umask)


@pytest.fixture
def diagnostic_bundle(released_bundle, monkeypatch):
    """Entirely synthetic evidence; bind its curator checksums like the real release."""
    directory, root = released_bundle
    index = json.loads((directory / "evidence-index.json").read_bytes())
    release = json.loads((directory / "cohort.json").read_bytes())
    for row in release["records"]:
        entry = index[row["sample_id"]]
        curation = {
            key: hashlib.sha256((root / entry[ref]).read_bytes()).hexdigest()
            for key, ref in (("features_sha256", "features_ref"), ("run_sha256", "run_ref"))
        }
        entry["curation"] = curation
        row["curation_evidence_sha256"] = digest(curation)
    release["release_sha256"] = digest({k: v for k, v in release.items() if k != "release_sha256"})
    (directory / "cohort.json").write_text(json.dumps(release))
    (directory / "evidence-index.json").write_text(json.dumps(index))
    monkeypatch.setattr("scripts.diagnose_m1.check_extractor_runtime", lambda *a: None)
    return directory, root, index


def test_diagnostic_never_opens_test_evidence_or_mixed_outcome_files(
    diagnostic_bundle, monkeypatch
):
    directory, root, index = diagnostic_bundle
    manifest = json.loads((directory / "partitions.json").read_bytes())
    forbidden = {(directory / name).resolve() for name in ("records.json", "predictor-inputs.json")}
    expected = set()
    for row in manifest["assignments"]:
        paths = {
            (root / index[row["sample_id"]][key]).resolve() for key in ("features_ref", "run_ref")
        }
        if row["partition"] == "test":
            forbidden |= paths
        else:
            expected |= paths
    original = Path.open

    def guarded(path, *args, **kwargs):
        assert path.resolve() not in forbidden, "reserved evidence must never be opened"
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded)
    data, opened = load_diagnostic_data(directory, root)
    assert set(map(Path, opened)) == expected
    assert len(opened) == 2 * (len(data.train.targets) + len(data.validation.targets))
    assert not hasattr(data, "test")


def test_tampered_allowed_evidence_is_rejected(diagnostic_bundle):
    directory, root, index = diagnostic_bundle
    manifest = json.loads((directory / "partitions.json").read_bytes())
    sample = next(r["sample_id"] for r in manifest["assignments"] if r["partition"] == "validation")
    (root / index[sample]["features_ref"]).write_text("{}")
    with pytest.raises(ExperimentError, match="diagnostic_evidence_mismatch"):
        load_diagnostic_data(directory, root)


def test_new_checksums_do_not_authorize_changed_validation_outcomes(diagnostic_bundle):
    directory, root, index = diagnostic_bundle
    manifest = json.loads((directory / "partitions.json").read_bytes())
    sample = next(r["sample_id"] for r in manifest["assignments"] if r["partition"] == "validation")
    entry = index[sample]
    path = root / entry["run_ref"]
    run = json.loads(path.read_bytes())
    run["source"]["target"]["view_count_observed"] += 1
    path.write_text(json.dumps(run))
    entry["curation"]["run_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    (directory / "evidence-index.json").write_text(json.dumps(index))
    release = json.loads((directory / "cohort.json").read_bytes())
    next(r for r in release["records"] if r["sample_id"] == sample)["curation_evidence_sha256"] = (
        digest(entry["curation"])
    )
    release["release_sha256"] = digest({k: v for k, v in release.items() if k != "release_sha256"})
    (directory / "cohort.json").write_text(json.dumps(release))
    with pytest.raises(ExperimentError, match="diagnostic_observation_mismatch"):
        load_diagnostic_data(directory, root)


def test_error_slices_keep_sign_channel_weighting_zero_and_large_values():
    logs = np.log1p([[1.0, 99.0, 999.0], [1.0, 999.0, 1999.0]])
    result = error_slice([99, 9999], logs, ["a", "b"])
    assert result["underprediction_fraction"] == 0.5
    assert result["coverage"] == 0.5
    assert result["signed_error_log_macro_channel"] == pytest.approx(-np.log(10) / 2)
    assert result["median_actual_plus_one_over_predicted_plus_one"] == pytest.approx(5.5)
    assert error_slice([], [], [])["status"] == "not_estimable"
    large = error_slice([2**63 - 1], np.log1p([[0.0, 1.0, 2.0]]), ["a"])
    assert large["median_actual_plus_one_over_predicted_plus_one"] > 0
    assert view_distribution([])["status"] == "not_estimable"


def prepared_fixture():
    data = development_fixture()
    for name in ("train", "validation"):
        split = getattr(data, name)
        inputs = tuple(
            p.model_copy(update={"text_embedding": tuple(np.sin(np.arange(384) + i) + 2)})
            for i, p in enumerate(split.inputs)
        )
        data = replace(data, **{name: split.model_copy(update={"inputs": inputs})})
    return data


def fake_bundle(data):
    artifact = SimpleNamespace(
        train_split_sha256=split_digest(data.train),
        validation_split_sha256=split_digest(data.validation),
        artifact_sha256="a" * 64,
    )
    return SimpleNamespace(
        artifact=artifact,
        predict_logs=lambda inputs, **kw: np.tile(
            np.log1p([[0.0, 100.0, 10000.0]]), (len(inputs), 1)
        ),
    )


def test_tail_thresholds_and_neighbors_use_only_training_support(monkeypatch):
    monkeypatch.setattr("scripts.diagnose_m1.model_structure", lambda *a: [])
    data = prepared_fixture()
    first = diagnose(data, fake_bundle(data))
    changed = replace(
        data,
        validation=data.validation.model_copy(
            update={
                "targets": tuple(
                    t.model_copy(update={"view_count": 1000000 + i})
                    for i, t in enumerate(data.validation.targets)
                )
            }
        ),
    )
    second = diagnose(changed, fake_bundle(changed))
    assert first["sector_train_p90_views"] == second["sector_train_p90_views"]
    assert not second["model_refitted"]
    assert second["evaluated_partitions"] == ["train", "validation"]
    for item in second["private_validation_neighbors"]:
        assert {n["sample_id"] for n in item["training_neighbors"]} <= set(data.train.sample_ids)
    assert len(second["private_rows"]) == len(data.train.targets) + len(data.validation.targets)


def test_wrong_development_inputs_cannot_be_compared_to_frozen_artifact(monkeypatch):
    data = prepared_fixture()
    bundle = fake_bundle(data)
    bundle.artifact.validation_split_sha256 = "0" * 64
    with pytest.raises(ExperimentError, match="diagnostic_split_digest_mismatch"):
        diagnose(data, bundle)


@pytest.mark.parametrize("scale", [2.0, -2.0])
def test_native_audit_includes_bias_scale_and_conservative_bounds(scale):
    class Model:
        tree_count_ = 2

        def get_scale_and_bias(self):
            return scale, 10.0

        def get_leaf_values(self):
            return np.array([1.0, 3.0, 2.0, 5.0])

        def get_tree_leaf_counts(self):
            return np.array([2, 2])

        def calc_leaf_indexes(self, pool, **kwargs):
            return np.tile([[0, 1]], (pool.num_row(), 1))

        def predict(self, pool, **kwargs):
            return np.full(pool.num_row(), scale * 6 + 10)

        def get_feature_importance(self, **kwargs):
            return np.array([0.0, 0.0, 0.0, 0.0, 100.0] + [0.0] * 383)

    bundle = SimpleNamespace(
        models=(Model(),),
        artifact=SimpleNamespace(
            supported_text_statuses=("extracted",), selected=(SimpleNamespace(quantile=0.5),)
        ),
    )
    result = model_structure(bundle, prepared_fixture())[0]
    assert result["native_reconstruction_max_abs_error"] == 0
    expected = [scale * 3 + 10, scale * 8 + 10]
    assert result["tree_sum_conservative_lower_log"] == min(expected)
    assert result["tree_sum_conservative_upper_log"] == max(expected)

from contextlib import nullcontext

import pytest

from scripts import run_full_models as runner
from scripts.channel_partitions import ExperimentError


def options(tmp_path):
    return [
        argument
        for name in ("data-root", "parent", "cohort-dir", "queue", "quality-release")
        for argument in (f"--{name}", str(tmp_path / name))
    ]


def test_missing_artifact_destination_stops_before_data_loading(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "load_full_data", lambda *_: pytest.fail("opened data"))
    with pytest.raises(SystemExit):
        runner.main(["train-c", *options(tmp_path)])


def test_existing_destination_is_preserved_before_opening_evidence(tmp_path, monkeypatch):
    existing = tmp_path / "model"
    existing.mkdir()
    monkeypatch.setattr(runner, "load_full_data", lambda *_: pytest.fail("opened data"))
    with pytest.raises(ExperimentError, match="output_already_exists"):
        runner.main(["train-b", *options(tmp_path), "--b-dir", str(existing)])


def test_missing_quality_boundary_cannot_reach_fit(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "reserved_guard", lambda *_: nullcontext())

    def rejected(*_):
        raise ExperimentError("quality_release_unavailable")

    monkeypatch.setattr(runner, "load_full_data", rejected)
    monkeypatch.setattr(runner, "train_b", lambda *_: pytest.fail("fit before release"))
    with pytest.raises(ExperimentError, match="quality_release_unavailable"):
        runner.main(["train-b", *options(tmp_path), "--b-dir", str(tmp_path / "new")])
    assert not (tmp_path / "new").exists()

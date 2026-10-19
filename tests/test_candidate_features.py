import json
import subprocess

import pytest

from scripts.candidate_features import extract_candidates
from scripts.channel_partitions import digest
from scripts.creative_contracts import AnalysisRequest
from scripts.creative_media import CreativeError


def extraction_request(registered):
    return AnalysisRequest(
        campaign_id="demo",
        creative_ids=[registered["creative_id"]],
        sector="moda",
        objective="divulgacao",
        brief="PRIVATE_BRIEF",
    )


def write_fake_result(folder, count):
    request = json.loads((folder / "request.json").read_bytes())
    assert "PRIVATE_BRIEF" not in json.dumps(request)
    rows = []
    for item in request["items"]:
        props = item["media"]
        rows.append(
            {
                "status": "completed",
                "reason_code": None,
                "extractor_config_sha256": digest(request["config"]),
                "inputs": {
                    "sector": item["sector"],
                    "duration_seconds": props["duration_seconds"],
                    "aspect_ratio_height_over_width": props["height"] / props["width"],
                    "text_status": "extracted",
                    "text_embedding": [0.1] * 384,
                },
            }
        )
    (folder / "result.json").write_text(json.dumps(rows))
    return True


@pytest.mark.parametrize("failure", [None, "timeout", "failed", "invalid", "cancelled"])
def test_extraction_owns_private_copy_and_cleans_success_failure_and_cancellation(
    registry,
    registered,
    tmp_path,
    monkeypatch,
    failure,
):
    records = registry.validate_creatives(extraction_request(registered))
    scratch = tmp_path / "scratch"

    def worker(folder, count):
        assert (folder / "0.media").read_bytes() == (
            registry.uploads_root / "demo.mp4"
        ).read_bytes()
        assert folder.stat().st_mode & 0o777 == 0o700
        if failure == "timeout":
            raise subprocess.TimeoutExpired("worker", 1)
        if failure == "cancelled":
            raise KeyboardInterrupt
        if failure == "invalid":
            (folder / "result.json").write_text("PRIVATE_TRANSCRIPT")
            return True
        return False if failure == "failed" else write_fake_result(folder, count)

    monkeypatch.setattr("scripts.candidate_features._run_worker", worker)
    if failure == "cancelled":
        with pytest.raises(KeyboardInterrupt):
            extract_candidates(registry, records, {}, scratch)
    else:
        result = extract_candidates(registry, records, {}, scratch)
        assert result[0].status == ("completed" if failure is None else "unavailable")
        if failure:
            assert result[0].inputs is None
    assert not list(scratch.iterdir())
    assert (registry.uploads_root / "demo.mp4").exists()


def test_changed_media_is_rejected_before_extraction(registry, registered, tmp_path, monkeypatch):
    records = registry.validate_creatives(extraction_request(registered))
    (registry.uploads_root / "demo.mp4").write_bytes(b"changed")
    monkeypatch.setattr(
        "scripts.candidate_features._run_worker", lambda *_: pytest.fail("must not extract")
    )
    with pytest.raises(CreativeError, match="media_changed"):
        extract_candidates(registry, records, {}, tmp_path / "scratch")
    assert not list((tmp_path / "scratch").iterdir())


@pytest.mark.parametrize("change", ["config", "sector", "duration", "dimension"])
def test_worker_results_are_bound_to_config_registered_media_and_schema(
    registry,
    registered,
    tmp_path,
    monkeypatch,
    change,
):
    def worker(folder, count):
        write_fake_result(folder, count)
        rows = json.loads((folder / "result.json").read_bytes())
        row = rows[0]
        if change == "config":
            row["extractor_config_sha256"] = "0" * 64
        elif change == "sector":
            row["inputs"]["sector"] = "beleza"
        elif change == "duration":
            row["inputs"]["duration_seconds"] = 59.0
        else:
            row["inputs"]["text_embedding"] = [0.1]
        (folder / "result.json").write_text(json.dumps(rows))
        return True

    monkeypatch.setattr("scripts.candidate_features._run_worker", worker)
    result = extract_candidates(
        registry,
        registry.validate_creatives(extraction_request(registered)),
        {},
        tmp_path / "scratch",
    )
    assert result[0].reason_code == "extraction_failed"


def test_worker_environment_does_not_inherit_credentials_and_timeout_kills_group(
    tmp_path, monkeypatch
):
    from scripts.candidate_features import _run_worker

    monkeypatch.setenv("NVIDIA_API_KEY", "PRIVATE_SENTINEL")
    calls = []

    class Worker:
        pid, returncode = 123, None

        def __init__(self, *args, **kwargs):
            assert "NVIDIA_API_KEY" not in kwargs["env"]
            assert kwargs["env"]["HF_HUB_OFFLINE"] == "1"
            assert kwargs["start_new_session"]

        def wait(self, timeout=None):
            calls.append(timeout)
            if timeout is not None:
                raise subprocess.TimeoutExpired("worker", timeout)

        def poll(self):
            return None

    monkeypatch.setattr("scripts.candidate_features.subprocess.Popen", Worker)
    monkeypatch.setattr("scripts.candidate_features.os.killpg", lambda *a: calls.append("killed"))
    with pytest.raises(subprocess.TimeoutExpired):
        _run_worker(tmp_path, 5)
    assert calls == [270, "killed", None]

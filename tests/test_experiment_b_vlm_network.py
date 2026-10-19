import hashlib
import json
from pathlib import Path

import pytest

from scripts import experiment_b_vlm_extract as extraction
from scripts import experiment_b_vlm_network as network
from scripts import pilot_youtube_media as frozen
from scripts.private_checkpoint import file_hash


@pytest.mark.parametrize(
    "diagnostic,transient",
    [
        ("[Errno -3] Temporary failure in name resolution", True),
        ("Name or service not known", False),
        ("HTTP Error 429", False),
        ("Temporary failure in name resolution followed by HTTP Error 429", False),
        ("Temporary failure in name resolution followed by Sign in", False),
        ("Sign in to confirm you're not a bot", False),
    ],
)
def test_only_typed_temporary_dns_failure_is_recoverable(
    tmp_path, monkeypatch, diagnostic, transient
):
    class Process:
        returncode = 1

        def communicate(self, **kwargs):
            return "", diagnostic

    monkeypatch.setattr(network.subprocess, "Popen", lambda *a, **kw: Process())
    with pytest.raises(RuntimeError) as caught:
        network.download_video(tmp_path / "media", "abcdefghijk", Path("ffmpeg"))
    assert isinstance(caught.value, network.TransientDNSFailure) is transient
    if transient:
        assert (
            caught.value.diagnostic_sha256
            == hashlib.sha256(("\n" + diagnostic).encode()).hexdigest()
        )


def test_youtube_command_flags_and_success_result_are_identical_to_frozen_downloader(
    tmp_path, monkeypatch
):
    commands = []

    class Process:
        returncode = 0

        def communicate(self, **kwargs):
            (tmp_path / "download.mp4").write_bytes(b"synthetic media")
            return "", ""

    def popen(command, **kwargs):
        commands.append((command, kwargs))
        return Process()

    monkeypatch.setattr(network.subprocess, "Popen", popen)
    destination = tmp_path / "media"
    old = frozen.download_video(destination, "abcdefghijk", Path("ffmpeg"))
    destination.unlink()
    new = network.download_video(destination, "abcdefghijk", Path("ffmpeg"))
    assert commands[0] == commands[1] and old == new


@pytest.mark.parametrize(
    "mode", ["success", "generic_dns", "preflight_false", "twice", "quota", "global_cap"]
)
def test_real_cleanup_ledger_and_exact_retry_limits(tmp_path, monkeypatch, mode):
    state = {
        "halt_reason": None,
        "elapsed_seconds": 12.5,
        "entries": [],
        "prior_acquisitions": 21,
        "acquisition_limit": 22 if mode == "quota" else 300,
        "dns_retries_used": 10 if mode == "global_cap" else 0,
    }
    plan = {"rows": [{"sample_id": "abcdefghijk"}], "config": {"model": {}}}
    monkeypatch.setattr(extraction, "load_queue", lambda *a: (plan, state))
    monkeypatch.setattr("scripts.prepare_gguf_vlm.prepare", lambda **kw: {})
    monkeypatch.setattr(extraction, "DNS_BACKOFF_SECONDS", 0)
    monkeypatch.setattr(extraction, "dns_preflight", lambda: mode != "preflight_false")
    seen, reserved = [], []

    def downloader(media, sample):
        checkpoint = json.loads((tmp_path / "queue/checkpoint.json").read_bytes())
        reserved.append(extraction.attempt_count(checkpoint))
        seen.append(sample)
        media.write_bytes(b"synthetic partial media")
        if mode == "generic_dns":
            raise RuntimeError("network_dns_failure")
        if len(seen) == 1 or mode == "twice":
            raise network.TransientDNSFailure("a" * 64)
        return {"sha256": file_hash(media)}

    report = extraction.run(
        tmp_path,
        tmp_path,
        tmp_path / "queue",
        tmp_path,
        max_videos=1,
        downloader=downloader,
        extractor=lambda *a: {"synthetic": True},
    )
    expected = 2 if mode in {"success", "twice"} else 1
    assert len(seen) == expected and reserved == list(range(1, expected + 1))
    entry = state["entries"][0]
    assert len(entry["attempts"]) == expected
    assert all(a["cleanup"] is True for a in entry["attempts"])
    assert entry["seconds"] >= sum(a["seconds"] for a in entry["attempts"])
    assert state["elapsed_seconds"] == 12.5 + entry["seconds"]
    assert not list((tmp_path / "data/private/media-temp").glob("galaxies-media-*"))
    if expected == 2:
        first = entry["attempts"][0]
        archived = tmp_path / "queue/failed-attempts/abcdefghijk/1/run.json"
        assert file_hash(archived) == first["run_sha256"]
        assert first["dns_preflight_positive"] is True and state["dns_retries_used"] == 1
    assert (report["completed"] == 1) is (mode == "success")
    assert (report["halt_reason"] is None) is (mode == "success")


def test_unconfirmed_cleanup_cannot_retry_even_after_transient_dns(tmp_path, monkeypatch):
    calls = []
    entry, state = {}, {"entries": [], "dns_retries_used": 0}
    state["entries"].append(entry)

    def session(destination, *args, **kwargs):
        destination.mkdir(parents=True)
        (destination / "run.json").write_text(json.dumps({"temporary_directory_removed": False}))
        calls.append(1)
        raise network.TransientDNSFailure("a" * 64)

    monkeypatch.setattr(extraction, "run_session", session)
    with pytest.raises(network.TransientDNSFailure):
        extraction.session_with_dns_recovery(
            tmp_path / "session",
            tmp_path,
            None,
            None,
            source={"sample_id": "abcdefghijk"},
            model={},
            entry=entry,
            state=state,
            folder=tmp_path,
            persist=lambda: None,
        )
    assert calls == [1] and len(entry["attempts"]) == 1

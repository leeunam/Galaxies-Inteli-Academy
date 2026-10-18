import json
import signal
import subprocess

import pytest

from scripts import pilot_youtube_media as pilot


def candidate(video_id):
    return {
        "audit": {"video_id": video_id, "source_url": "https://www.youtube.com/watch?v=" + video_id}
    }


def test_only_matching_canonical_ids_are_downloadable():
    row = candidate("abcdefghijk")
    row["audit"]["source_url"] = "https://foreign.test/abcdefghijk"
    with pytest.raises(ValueError):
        pilot.validate_candidates([row])
    with pytest.raises(ValueError):
        pilot.validate_candidates([candidate("abcdefghijk")] * 2)


def test_outputs_cannot_escape_private_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(pilot, "ROOT", tmp_path)
    with pytest.raises(ValueError):
        pilot.private_path(tmp_path / "public/features.json")
    assert pilot.private_path(tmp_path / "data/private/report") == tmp_path / "data/private/report"


def test_batch_continues_after_failed_download_and_cleans_every_video(tmp_path):
    def download(path, video_id):
        path.write_bytes(b"synthetic media")
        if video_id == "abcdefghijk":
            raise RuntimeError("authentication_or_bot_check")
        return {"sha256": "synthetic"}

    def extract(media, scratch):
        (scratch / "frame.jpg").write_bytes(b"synthetic frame")
        return {"synthetic_feature": True}

    report = pilot.run_batch(
        [candidate("abcdefghijk"), candidate("12345678901"), candidate("zyxwvutsrqp")],
        tmp_path / "output",
        tmp_path / "scratch",
        extract,
        download,
    )
    assert report["completed"] == 2
    assert report["failed"] == 1
    assert all(x["temporary_directory_removed"] for x in report["videos"])
    assert list((tmp_path / "scratch").iterdir()) == []
    assert json.loads((tmp_path / "output/abcdefghijk/run.json").read_text())["status"] == "failed"
    assert not report["training_eligible"]


def test_downloader_timeout_terminates_owned_process_group(tmp_path, monkeypatch):
    terminated = []

    class Process:
        pid = 123456789
        calls = 0

        def communicate(self, timeout=None):
            self.calls += 1
            if self.calls == 1:
                assert timeout == 180
                raise subprocess.TimeoutExpired("synthetic", timeout)
            return "", ""

        def poll(self):
            return None

    process = Process()
    monkeypatch.setattr(pilot.subprocess, "Popen", lambda *a, **kw: process)
    monkeypatch.setattr(pilot.os, "killpg", lambda pid, sig: terminated.append((pid, sig)))
    with pytest.raises(subprocess.TimeoutExpired):
        pilot.download_video(tmp_path / "input.media", "abcdefghijk", tmp_path / "ffmpeg")
    assert terminated == [(process.pid, signal.SIGKILL)]
    assert process.calls == 2

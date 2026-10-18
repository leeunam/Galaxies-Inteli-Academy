import json
from pathlib import Path

import pytest

from scripts import prepare_media_queue as queue
from scripts.private_checkpoint import lock

IDS = ["abcdefghijk", "12345678901", "zyxwvutsrqp"]
CONFIG = {"models": {}, "extractor": "synthetic-v1"}


@pytest.fixture
def area(tmp_path, monkeypatch):
    monkeypatch.setattr(queue, "ROOT", tmp_path)
    evidence = tmp_path / "data/private/review.txt"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("Synthetic review evidence, not authorization for real videos")
    return tmp_path / "data/private/queue"


def candidate(video_id, approved=True):
    review = {
        "status": "approved" if approved else "pending",
        "reviewer": "synthetic-reviewer",
        "reviewed_at_utc": "2026-10-17T00:00:00Z",
        "source_status": "verified",
        "evidence_path": "data/private/review.txt",
    }
    return {
        "audit": {
            "video_id": video_id,
            "source_url": "https://www.youtube.com/watch?v=" + video_id,
        },
        "curation": {"usage_review": review, "curation_review": review.copy()},
        "metadata": {},
        "target": {},
        "diagnostics": {},
    }


def download(path, video_id):
    path.write_bytes(b"synthetic media")
    return {"sha256": "synthetic"}


def extract(media, scratch):
    (scratch / "frame.jpg").write_bytes(b"synthetic frame")
    return {"synthetic": True}


def read(folder):
    return json.loads((folder / "queue.json").read_text())


def test_resume_does_not_repeat_success_and_enforces_quantity_budget(area):
    queue.prepare_queue([candidate(v) for v in IDS], area, CONFIG)
    calls = []

    def downloader(path, video_id):
        calls.append(video_id)
        return download(path, video_id)

    assert queue.execute_queue(area, CONFIG, extract, downloader, max_videos=1)["states"] == {
        "completed": 1,
        "pending": 2,
        "running": 0,
        "failed": 0,
        "blocked": 0,
    }
    before = (area / "attempts/abcdefghijk/1/features.json").read_bytes()
    final = queue.execute_queue(area, CONFIG, extract, downloader)
    assert final["states"]["completed"] == 3 and calls == IDS
    assert (area / "attempts/abcdefghijk/1/features.json").read_bytes() == before
    assert not final["training_eligible"]
    assert all(len(v["attempts"]) == 1 for v in read(area)["videos"])


def test_pending_source_is_blocked_without_downloader(area):
    row = candidate(IDS[0])
    row["curation"]["usage_review"]["source_status"] = "pending"
    state = queue.prepare_queue([row], area, CONFIG)
    assert state["videos"][0]["status"] == "blocked"

    def forbidden(*args):
        raise AssertionError("No download/model extraction allowed")

    assert queue.execute_queue(area, CONFIG, forbidden, forbidden)["states"]["blocked"] == 1
    assert read(area)["videos"][0]["attempts"] == []


def test_partial_failure_keeps_attempt_evidence_and_never_exceeds_two_attempts(area):
    queue.prepare_queue([candidate(IDS[0])], area, CONFIG)

    def fail(media, scratch):
        (scratch / "partial.audio").write_bytes(b"partial")
        raise RuntimeError("synthetic_failed_signed_url_must_not_be_saved?secret=yes")

    for _ in range(3):
        assert queue.execute_queue(area, CONFIG, fail, download)["states"]["failed"] == 1
    attempts = read(area)["videos"][0]["attempts"]
    assert len(attempts) == 2
    for attempt in attempts:
        run = json.loads((area / attempt["folder"] / "run.json").read_text())
        assert run["temporary_directory_removed"]
        assert attempt["reason"] == "processing_failed"
    assert list((area.parents[0] / "media-temp").iterdir()) == []
    assert "secret=yes" not in (area / "queue.json").read_text()


@pytest.mark.parametrize(
    "reason", ["authentication_or_bot_check", "http_access_denied_or_rate_limited"]
)
def test_access_failure_halts_batch_and_future_runs(area, reason):
    queue.prepare_queue([candidate(v) for v in IDS], area, CONFIG)
    calls = []

    def fail(path, video_id):
        calls.append(video_id)
        raise RuntimeError(reason)

    assert queue.execute_queue(area, CONFIG, extract, fail)["halt_reason"] == reason
    assert queue.execute_queue(area, CONFIG, extract, fail)["states"]["pending"] == 2
    assert calls == IDS[:1]


def test_protocol_config_artifact_and_lock_protect_resume(area):
    queue.prepare_queue([candidate(IDS[0])], area, CONFIG)
    with pytest.raises(ValueError, match="configuration changed"):
        queue.execute_queue(area, {**CONFIG, "extractor": "v2"}, extract, download)
    with lock(area / ".lock"), pytest.raises(ValueError, match="locked"):
        queue.execute_queue(area, CONFIG, extract, download)
    queue.execute_queue(area, CONFIG, extract, download)
    (area / "attempts/abcdefghijk/1/features.json").write_text("altered")
    with pytest.raises(ValueError, match="artifact changed"):
        queue.execute_queue(area, CONFIG, extract, download)


def test_evidence_change_blocks_before_download(area):
    queue.prepare_queue([candidate(IDS[0])], area, CONFIG)
    (area.parent / "review.txt").write_text("Changed review")
    result = queue.execute_queue(area, CONFIG, extract, download)
    assert result["states"]["blocked"] == 1
    assert read(area)["videos"][0]["attempts"] == []


def test_cancellation_is_checkpointed_and_can_retry(area):
    queue.prepare_queue([candidate(IDS[0])], area, CONFIG)

    def cancel(*args):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        queue.execute_queue(area, CONFIG, cancel, download)
    assert read(area)["videos"][0]["status"] == "failed"
    assert queue.execute_queue(area, CONFIG, extract, download)["states"]["completed"] == 1
    assert len(read(area)["videos"][0]["attempts"]) == 2


def test_time_budget_is_checked_between_videos_and_fresh_queue_is_required(area):
    queue.prepare_queue([candidate(v) for v in IDS], area, CONFIG)
    ticks = iter([0, 0, 10])
    result = queue.execute_queue(
        area, CONFIG, extract, download, max_seconds=5, clock=lambda: next(ticks)
    )
    assert result["states"]["completed"] == 1
    with pytest.raises(ValueError, match="fresh queue"):
        queue.prepare_queue([candidate(IDS[0])], area, CONFIG)


def test_missing_private_evidence_and_oversize_input_rejected(area):
    row = candidate(IDS[0])
    row["curation"]["usage_review"]["evidence_path"] = "public/evidence.txt"
    with pytest.raises(ValueError, match="private storage"):
        queue.prepare_queue([row], area, CONFIG)
    with pytest.raises(ValueError, match="1–300"):
        queue.prepare_queue([candidate(IDS[0])] * 301, area, CONFIG)


@pytest.mark.parametrize("unclean", [True, False])
def test_cleanup_failure_or_uncertain_running_state_halts_without_next_video(
    area, monkeypatch, unclean
):
    queue.prepare_queue([candidate(v) for v in IDS], area, CONFIG)
    if unclean:

        def unclean_session(destination, *args, **kwargs):
            destination.mkdir(parents=True)
            (destination / "run.json").write_text(
                json.dumps({"temporary_directory_removed": False})
            )
            raise OSError("synthetic cleanup failure")

        monkeypatch.setattr(queue, "run_session", unclean_session)
    else:
        state = read(area)
        state["videos"][0].update(status="running", attempts=[{"folder": "attempts/abcdefghijk/1"}])
        (area / "queue.json").write_text(json.dumps(state))
    report = queue.execute_queue(area, CONFIG, extract, download)
    assert report["halt_reason"] == "cleanup_unconfirmed"
    assert report["states"]["pending"] == 2
    assert (
        queue.execute_queue(area, CONFIG, extract, download)["halt_reason"] == "cleanup_unconfirmed"
    )


def test_preparation_defaults_to_twenty_and_legacy_pilot_still_rejects_four(area):
    rows = [candidate(f"{i:011d}", approved=False) for i in range(21)]
    assert len(queue.prepare_queue(rows, area, CONFIG)["videos"]) == 20
    with pytest.raises(ValueError, match="one to three"):
        queue.validate_candidates(rows[:4])


def test_run_without_execute_is_inspection_only(area, monkeypatch, capsys):
    queue.prepare_queue([candidate(IDS[0])], area, CONFIG)
    monkeypatch.setattr(queue, "configuration", lambda *args: CONFIG)
    monkeypatch.setattr("sys.argv", ["queue", "run", "--queue", str(area)])

    def forbidden(*args):
        raise AssertionError("Inspection must not load models or execute")

    monkeypatch.setattr(queue, "execute_queue", forbidden)
    monkeypatch.setattr(queue, "prepare_models", forbidden)
    queue.main()
    assert json.loads(capsys.readouterr().out)["states"]["pending"] == 1


def test_changed_protocol_and_running_without_attempt_are_rejected(area):
    queue.prepare_queue([candidate(IDS[0])], area, CONFIG)
    state = read(area)
    state["protocol"] = "future"
    (area / "queue.json").write_text(json.dumps(state))
    with pytest.raises(ValueError, match="Protocol"):
        queue.execute_queue(area, CONFIG, extract, download)
    state["protocol"] = queue.PROTOCOL
    state["videos"][0]["status"] = "running"
    (area / "queue.json").write_text(json.dumps(state))
    with pytest.raises(ValueError, match="Invalid video checkpoint"):
        queue.execute_queue(area, CONFIG, extract, download)


def test_runtime_preparer_change_rejects_resume_before_loading_models(area, monkeypatch):
    scripts = queue.ROOT / "scripts"
    scripts.mkdir()
    for source in Path(queue.__file__).parent.glob("*.py"):
        (scripts / source.name).write_bytes(source.read_bytes())
    original = queue.configuration(with_vlm=True)
    queue.prepare_queue([candidate(v) for v in IDS[:2]], area, original)
    queue.execute_queue(area, original, extract, download, max_videos=1)
    checkpoint = (area / "queue.json").read_bytes()
    preparer = scripts / "prepare_gguf_vlm.py"
    preparer.write_bytes(preparer.read_bytes() + b"\n# Synthetic runtime preparation change\n")
    changed = queue.configuration(with_vlm=True)
    assert changed != original
    assert {
        name
        for name, value in changed["extractor_files_sha256"].items()
        if original["extractor_files_sha256"].get(name) != value
    } == {"prepare_gguf_vlm.py"}

    def forbidden(*args, **kwargs):
        raise AssertionError("Changed runtime preparer must reject resume before models/download")

    monkeypatch.setattr(queue, "prepare_models", forbidden)
    monkeypatch.setattr(queue, "download_video", forbidden)
    monkeypatch.setattr(
        "sys.argv", ["queue", "run", "--queue", str(area), "--with-vlm", "--execute", "--resume"]
    )
    with pytest.raises(ValueError, match="configuration changed"):
        queue.main()
    assert (area / "queue.json").read_bytes() == checkpoint


def test_running_after_failed_halts_before_any_new_session(area, monkeypatch):
    queue.prepare_queue([candidate(v) for v in IDS], area, CONFIG)
    state = read(area)
    for index, video in enumerate(state["videos"]):
        video["status"] = "failed" if index == 0 else "running"
        video["attempts"] = [{"folder": f"attempts/{video['video_id']}/1"}]
    first_attempts = state["videos"][0]["attempts"].copy()
    (area / "queue.json").write_text(json.dumps(state))
    sessions = []

    def forbidden_session(*args, **kwargs):
        sessions.append(args)
        raise AssertionError("Uncertain earlier cleanup must prevent every new session")

    monkeypatch.setattr(queue, "run_session", forbidden_session)
    report = queue.execute_queue(area, CONFIG, extract, download)
    assert sessions == []
    assert report["halt_reason"] == "cleanup_unconfirmed"
    saved = read(area)
    assert saved["halt_reason"] == "cleanup_unconfirmed"
    assert saved["videos"][0]["attempts"] == first_attempts
    for video in saved["videos"][1:]:
        assert video["status"] == "failed"
        assert video["attempts"][-1]["reason"] == "interrupted_cleanup_unconfirmed"
    assert (
        queue.execute_queue(area, CONFIG, extract, download)["halt_reason"] == "cleanup_unconfirmed"
    )
    assert sessions == []

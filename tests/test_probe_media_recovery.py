import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.private_checkpoint import file_hash, save
from scripts.probe_media_recovery import probe


def setup_probe(tmp_path, monkeypatch, *, failure=None):
    monkeypatch.chdir(tmp_path)
    pool = tmp_path / "data/private/pool"
    path = pool / "extraction/checkpoint.json"
    old = {
        "videos": [
            {
                "video_id": "old_attempt",
                "status": "completed",
                "channel_id": "earlier",
                "cleanup": True,
                "review": {"decision": "included", "sector": "moda"},
            }
        ],
        "elapsed_seconds": 100.0,
        "halt_reason": "authentication_or_bot_check",
        "selection_sha256": "a" * 64,
    }
    save(path, old)
    plan = {
        "records": [
            {"audit": {"video_id": "old_attempt", "channel_id": "earlier"}},
            {"audit": {"video_id": "fresh_probe", "channel_id": "fresh_channel"}},
        ]
    }
    monkeypatch.setattr(
        "scripts.probe_media_recovery.load_state",
        lambda *a: (
            SimpleNamespace(records=[]),
            plan,
            {"models": {}},
            json.loads(path.read_bytes()),
        ),
    )
    monkeypatch.setattr(
        "scripts.probe_media_recovery.decode_probe", lambda *a: {"video_decoded": True}
    )
    calls = []

    def download(media, vid, ffmpeg):
        calls.append(vid)
        reserved = json.loads(path.read_bytes())
        assert reserved["halt_reason"] == old["halt_reason"]
        assert len(reserved["videos"]) == 2
        assert reserved["videos"][-1]["status"] == "source_probe_pending"
        if failure:
            raise RuntimeError(failure)
        media.write_bytes(b"synthetic video")
        return {"sha256": file_hash(media)}

    monkeypatch.setattr("scripts.probe_media_recovery.download_video", download)
    return pool, path, old, calls


def test_probe_success_preserves_previous_entries_and_replays_without_network(
    tmp_path, monkeypatch
):
    pool, path, old, calls = setup_probe(tmp_path, monkeypatch)
    before = copy.deepcopy(old)
    result = probe(pool, Path("unused"), "explicit-request-1")
    state = json.loads(path.read_bytes())
    assert result["source_available"] and state["halt_reason"] is None
    assert state["videos"][:-1] == before["videos"] and len(state["videos"]) == 2
    assert state["elapsed_seconds"] >= before["elapsed_seconds"]
    assert state["videos"][-1]["review"]["decision"] == "excluded"
    assert list((tmp_path / "data/private/media-temp").iterdir()) == []
    assert probe(pool, Path("unused"), "explicit-request-1") == result
    assert calls == ["fresh_probe"]


def test_failed_probe_keeps_terminal_halt_and_counts_attempt(tmp_path, monkeypatch):
    pool, path, old, calls = setup_probe(
        tmp_path, monkeypatch, failure="authentication_or_bot_check"
    )
    result = probe(pool, Path("unused"), "explicit-request-1")
    state = json.loads(path.read_bytes())
    assert not result["source_available"] and result["cleanup"]
    assert state["halt_reason"] == old["halt_reason"] and len(state["videos"]) == 2
    assert state["videos"][:-1] == old["videos"]
    probe(pool, Path("unused"), "explicit-request-1")
    assert calls == ["fresh_probe"]


def test_receipt_before_checkpoint_failure_recovers_without_retry(tmp_path, monkeypatch):
    pool, path, old, calls = setup_probe(tmp_path, monkeypatch)
    original = save

    def fail_final(path_arg, state):
        if path_arg == path and state.get("halt_reason", "other") is None:
            raise OSError("synthetic checkpoint interruption")
        original(path_arg, state)

    monkeypatch.setattr("scripts.probe_media_recovery.save", fail_final)
    with pytest.raises(OSError):
        probe(pool, Path("unused"), "explicit-request-1")
    assert json.loads(path.read_bytes())["halt_reason"] == old["halt_reason"]
    monkeypatch.setattr("scripts.probe_media_recovery.save", original)
    assert probe(pool, Path("unused"), "explicit-request-1")["source_available"]
    assert calls == ["fresh_probe"]


def test_pending_probe_and_exhausted_budget_refuse_network(tmp_path, monkeypatch):
    pool, path, old, calls = setup_probe(tmp_path, monkeypatch)
    old["elapsed_seconds"] = 5400.0
    save(path, old)
    with pytest.raises(ValueError, match="budget_exhausted"):
        probe(pool, Path("unused"), "explicit-request-1")
    old["elapsed_seconds"] = 100.0
    old["videos"][0]["status"] = "source_probe_pending"
    save(path, old)
    with pytest.raises(ValueError, match="interrupted_source_probe"):
        probe(pool, Path("unused"), "explicit-request-1")
    assert calls == []


def test_changed_probe_evidence_cannot_clear_terminal_halt(tmp_path, monkeypatch):
    pool, path, _, calls = setup_probe(tmp_path, monkeypatch)
    original = save

    def fail_final(path_arg, state):
        if path_arg == path and state.get("halt_reason", "other") is None:
            raise OSError("synthetic checkpoint interruption")
        original(path_arg, state)

    monkeypatch.setattr("scripts.probe_media_recovery.save", fail_final)
    with pytest.raises(OSError):
        probe(pool, Path("unused"), "explicit-request-1")
    (pool / "source-recovery/explicit-request-1/features.json").write_text(
        '{"video_decoded":false}'
    )
    monkeypatch.setattr("scripts.probe_media_recovery.save", original)
    with pytest.raises(ValueError, match="evidence_changed"):
        probe(pool, Path("unused"), "explicit-request-1")
    assert calls == ["fresh_probe"]


@pytest.mark.parametrize("field", ["video_id", "run_ref", "final_halt_reason", "source_available"])
def test_changed_receipt_identity_or_result_cannot_clear_halt(tmp_path, monkeypatch, field):
    pool, path, old, calls = setup_probe(tmp_path, monkeypatch)
    original = save

    def fail_final(path_arg, state):
        if path_arg == path and state.get("halt_reason", "other") is None:
            raise OSError("synthetic checkpoint interruption")
        original(path_arg, state)

    monkeypatch.setattr("scripts.probe_media_recovery.save", fail_final)
    with pytest.raises(OSError):
        probe(pool, Path("unused"), "explicit-request-1")
    rp = pool / "source-recovery/explicit-request-1/receipt.json"
    receipt = json.loads(rp.read_bytes())
    if field in ("video_id", "run_ref"):
        receipt["entry"][field] = "different_reserved_identity"
    elif field == "final_halt_reason":
        receipt[field] = "authentication_or_bot_check"
    else:
        receipt["summary"][field] = False
    save(rp, receipt)
    monkeypatch.setattr("scripts.probe_media_recovery.save", original)
    with pytest.raises(
        ValueError, match="source_probe_reservation_mismatch|source_probe_result_mismatch"
    ):
        probe(pool, Path("unused"), "explicit-request-1")
    assert json.loads(path.read_bytes())["halt_reason"] == old["halt_reason"]
    assert calls == ["fresh_probe"]

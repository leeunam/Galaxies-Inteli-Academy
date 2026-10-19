import json

import pytest

from scripts.expand_reference_pool import new_channel_partition
from scripts.expansion_media import (
    deadline,
    load_state,
    review_entry,
    sweep_reviews,
    validate_reviews,
)
from scripts.observed_baseline import freeze_cohort
from scripts.private_checkpoint import save
from tests.test_observed_baseline import pilot_records


def included(i, sector="moda", channel=None):
    return {
        "video_id": f"new{i}",
        "channel_id": channel or f"ch{i}",
        "review": {"decision": "included", "sector": sector},
    }


@pytest.mark.parametrize(
    "rows",
    [
        [included(i) for i in range(51)],
        [included(i, channel="same") for i in range(6)],
        [included(0, sector="outside")],
    ],
)
def test_capacity_is_enforced_before_extraction_or_release(rows):
    with pytest.raises(ValueError, match="curation_capacity_exceeded"):
        validate_reviews(rows)


def test_reviews_require_explicit_image_decision_and_keep_provenance():
    entry = {"status": "completed", "video_id": "synthetic", "automatic_exclusion": None}
    result = review_entry(
        entry,
        {
            "decision": "included",
            "sector": "beleza",
            "reason": "visible cosmetic and Portuguese speech",
            "image_review_performed": True,
            "transcript_review_performed": True,
            "contact_sheet_sha256": "c" * 64,
        },
        "a" * 64,
        "b" * 64,
        "c" * 64,
    )
    assert result["image_review_performed"] and not result["human_review"]
    assert result["contact_sheet_sha256"] == "c" * 64
    assert not result["human_listening"]
    with pytest.raises(ValueError, match="invalid_curation_decision"):
        review_entry(
            entry,
            {"decision": "included", "sector": None, "reason": "unknown"},
            "a" * 64,
            "b" * 64,
            "c" * 64,
        )
    with pytest.raises(ValueError, match="entry_not_reviewable"):
        review_entry(entry | {"automatic_exclusion": "portuguese_not_established"}, {}, "", "", "")
    for change in (
        {"image_review_performed": False},
        {"contact_sheet_sha256": "d" * 64},
        {"transcript_review_performed": False},
    ):
        with pytest.raises(ValueError, match="invalid_curation_decision"):
            review_entry(entry, result | change, "a" * 64, "b" * 64, "c" * 64)


def test_deadline_interrupts_and_session_cleanup_runs(tmp_path):
    import time

    from scripts.pilot_licensed_media import run_session

    with pytest.raises(TimeoutError, match="media_time_budget"), deadline(0.02):
        run_session(
            tmp_path / "output",
            tmp_path / "scratch",
            lambda *a: time.sleep(1),
            downloader=lambda p: {},
        )
    result = json.loads((tmp_path / "output/run.json").read_bytes())
    assert result["temporary_directory_removed"]
    assert list((tmp_path / "scratch").iterdir()) == []


def test_contact_sheet_cleanup_failure_is_durable_and_retried(tmp_path, monkeypatch):
    from pathlib import Path

    folder = tmp_path / "data/private/pool"
    folder.mkdir(parents=True)
    sheet = folder / "sheet.png"
    sheet.write_bytes(b"synthetic")
    checkpoint = folder / "checkpoint.json"
    relative = str(sheet.relative_to(tmp_path))
    state = {"halt_reason": "media_time_budget", "cleanup_pending": [relative]}
    save(checkpoint, state)
    original = Path.unlink

    def fail(path, *a, **kw):
        if path == sheet:
            raise PermissionError("synthetic")
        return original(path, *a, **kw)

    monkeypatch.setattr(Path, "unlink", fail)
    with pytest.raises(ValueError, match="contact_sheet_cleanup_pending"):
        sweep_reviews(state, checkpoint, tmp_path)
    restored = json.loads(checkpoint.read_bytes())
    assert restored["cleanup_pending"] == [relative]
    monkeypatch.setattr(Path, "unlink", original)
    sweep_reviews(restored, checkpoint, tmp_path)
    assert not sheet.exists() and restored["cleanup_pending"] == []
    assert restored["halt_reason"] == "media_time_budget"


def test_media_state_opens_only_parent_metadata_not_test_evidence(tmp_path, monkeypatch):
    parent = tmp_path / "parent"
    rows, _ = pilot_records()
    freeze_cohort(rows, parent, source_snapshot_sha256="a" * 64)
    core = {"models": {}, "synthetic_config": True}
    save(parent / "extractor-config.json", core)
    pool = tmp_path / "pool"
    pool.mkdir()
    row = {"audit": {"video_id": "synthetic-new", "channel_id": "newchannel"}}
    plan = {
        "channel_allocation": {"newchannel": new_channel_partition("newchannel")},
        "records": [row],
    }
    save(pool / "candidates.json", plan)
    monkeypatch.setattr("scripts.expansion_media.configuration", lambda *a: core)
    from pathlib import Path

    original = Path.open

    def guarded(path, *a, **kw):
        assert path.name not in {
            "records.json",
            "predictor-inputs.json",
            "run.json",
            "features.json",
        }
        return original(path, *a, **kw)

    monkeypatch.setattr(Path, "open", guarded)
    _, _, _, state = load_state(pool, parent)
    assert state["videos"] == []
    row["audit"]["channel_id"] = rows[0]["channel_id"]
    save(pool / "candidates.json", plan)
    with pytest.raises(ValueError, match="candidate_channel_partition_mismatch"):
        load_state(pool, parent)

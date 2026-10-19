"""One operator-requested, audited media probe using the unchanged downloader."""

from __future__ import annotations

import argparse
import json
import math
import re
import time
from datetime import UTC, datetime
from pathlib import Path

from scripts.expansion_media import deadline, load_state, validate_reviews
from scripts.pilot_licensed_media import run_session
from scripts.pilot_youtube_media import download_video
from scripts.private_checkpoint import file_hash, lock, private_path, save
from scripts.retrain_expansion import reserved_guard


def decode_probe(media, scratch):
    import av

    with av.open(str(media)) as container:
        frame = next(container.decode(video=0))
        if frame.width <= 0 or frame.height <= 0:
            raise ValueError("invalid_probe_frame")
    return {"probe_only": True, "video_decoded": True}


def finalize(checkpoint, state, receipt_path, receipt):
    entry = receipt["entry"]
    matching = [
        v for v in state["videos"] if v.get("source_probe_request") == receipt["request_id"]
    ]
    immutable = ("video_id", "channel_id", "source_probe_request", "run_ref", "review")
    if len(matching) != 1 or any(matching[0].get(k) != entry.get(k) for k in immutable):
        raise ValueError("source_probe_reservation_mismatch")
    if entry["source_probe_request"] != receipt["request_id"]:
        raise ValueError("source_probe_reservation_mismatch")
    run_path = receipt_path.parent / "run.json"
    if (Path.cwd() / entry["run_ref"]).resolve() != run_path.resolve():
        raise ValueError("source_probe_reservation_mismatch")
    if (
        receipt["entry"]["run_sha256"] is not None
        and file_hash(run_path) != receipt["entry"]["run_sha256"]
    ):
        raise ValueError("source_probe_evidence_changed")
    run_record = json.loads(run_path.read_bytes()) if run_path.exists() else {}
    if run_record and any(
        run_record["source"]["audit"][key] != entry[key] for key in ("video_id", "channel_id")
    ):
        raise ValueError("source_probe_reservation_mismatch")
    cleanup = run_record.get("temporary_directory_removed") is True
    verified = run_record.get("status") == "completed" and cleanup
    if receipt["summary"]["source_available"] is not verified or entry["cleanup"] is not cleanup:
        raise ValueError("source_probe_result_mismatch")
    if verified:
        features = receipt_path.parent / "features.json"
        if file_hash(features) != receipt["entry"]["probe_features_sha256"]:
            raise ValueError("source_probe_evidence_changed")
        if (
            run_record["status"] != "completed"
            or run_record["temporary_directory_removed"] is not True
            or json.loads(features.read_bytes()).get("video_decoded") is not True
        ):
            raise ValueError("source_probe_not_verified")
        if run_record["media_fingerprint"]["sha256"] != entry.get("media_sha256"):
            raise ValueError("source_probe_evidence_changed")
    if entry["status"] != ("probe_completed" if verified else "failed"):
        raise ValueError("source_probe_result_mismatch")
    expected = receipt["entry"] | {"source_probe_receipt_sha256": file_hash(receipt_path)}
    if matching[0] == expected:
        return receipt["summary"]
    if (
        file_hash(checkpoint) != receipt["reserved_checkpoint_sha256"]
        or matching[0] is not state["videos"][-1]
        or matching[0]["status"] != "source_probe_pending"
        or state["halt_reason"] != receipt["previous_halt_reason"]
    ):
        raise ValueError("source_probe_checkpoint_changed")
    elapsed = receipt["elapsed_seconds"]
    if not math.isfinite(elapsed) or elapsed < 0 or elapsed != entry["seconds"]:
        raise ValueError("source_probe_budget_mismatch")
    total = state["elapsed_seconds"] + elapsed
    final_halt = None if verified else state["halt_reason"]
    if not cleanup:
        final_halt = "cleanup_unconfirmed"
    elif total >= 5400:
        final_halt = "media_time_budget"
    if (
        receipt["final_halt_reason"] != final_halt
        or receipt["summary"]["halt_reason"] != final_halt
        or receipt["summary"]["attempts"] != len(state["videos"])
        or receipt["summary"]["elapsed_seconds"] != total
    ):
        raise ValueError("source_probe_result_mismatch")
    state["videos"][-1] = expected
    state["elapsed_seconds"] += receipt["elapsed_seconds"]
    state["halt_reason"] = receipt["final_halt_reason"]
    save(checkpoint, state)
    return receipt["summary"]


def probe(pool, parent, request_id):
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", request_id):
        raise ValueError("invalid_operator_request_id")
    root = Path.cwd()
    pool = private_path(pool, root)
    checkpoint = pool / "extraction/checkpoint.json"
    with lock(pool / "extraction/.lock"):
        _, plan, core, state = load_state(pool, parent)
        folder = pool / "source-recovery" / request_id
        receipt_path = folder / "receipt.json"
        if receipt_path.exists():
            receipt = json.loads(receipt_path.read_bytes())
            if receipt["request_id"] != request_id:
                raise ValueError("source_probe_request_changed")
            return finalize(checkpoint, state, receipt_path, receipt)
        if any(v["status"] == "source_probe_pending" for v in state["videos"]):
            raise ValueError("interrupted_source_probe_requires_audit")
        if state["halt_reason"] not in {
            "authentication_or_bot_check",
            "http_access_denied_or_rate_limited",
        }:
            raise ValueError("source_probe_requires_source_halt")
        if state.get("cleanup_pending") or any("review" not in v for v in state["videos"]):
            raise ValueError("finish_curation_and_cleanup_first")
        if list((root / "data/private/media-temp").glob("galaxies-media-*")):
            raise ValueError("temporary_session_pending")
        limit = state.get("budget_extension", {}).get("attempt_limit", 300)
        if len(state["videos"]) >= limit or state["elapsed_seconds"] >= 5400:
            raise ValueError("source_probe_budget_exhausted")
        sectors, channels = validate_reviews(state["videos"])
        if sum(sectors.values()) >= 100:
            raise ValueError("source_probe_target_already_reached")
        seen = {v["video_id"] for v in state["videos"]}
        row = next(
            (
                r
                for r in plan["records"]
                if r["audit"]["video_id"] not in seen and channels[r["audit"]["channel_id"]] < 5
            ),
            None,
        )
        if row is None:
            raise ValueError("source_probe_no_unattempted_candidate")
        if folder.exists():
            raise ValueError("interrupted_source_probe_requires_audit")
        entry = {
            "video_id": row["audit"]["video_id"],
            "channel_id": row["audit"]["channel_id"],
            "source_probe_request": request_id,
            "run_ref": str((folder / "run.json").relative_to(root)),
            "status": "source_probe_pending",
            "cleanup": False,
            "review": {
                "decision": "excluded",
                "sector": None,
                "reason": "source_availability_probe_only",
                "human_review": False,
                "image_review_performed": False,
            },
        }
        previous_halt = state["halt_reason"]
        state["videos"].append(entry)
        save(checkpoint, state)  # Reserve attempt durably; source halt is still active.
        reserved_hash = file_hash(checkpoint)
        import imageio_ffmpeg

        started = time.monotonic()
        reason = None
        try:
            with deadline(5400 - state["elapsed_seconds"]):
                result = run_session(
                    folder,
                    root / "data/private/media-temp",
                    decode_probe,
                    lambda media: download_video(
                        media, entry["video_id"], Path(imageio_ffmpeg.get_ffmpeg_exe())
                    ),
                    source=row,
                    model_manifest=core["models"],
                )
        except (RuntimeError, ValueError, OSError, TimeoutError, StopIteration) as exc:
            reason = str(exc) if re.fullmatch(r"[a-z_]+", str(exc)) else type(exc).__name__
            result = (
                json.loads((folder / "run.json").read_bytes())
                if (folder / "run.json").exists()
                else {}
            )
        elapsed = time.monotonic() - started
        cleanup = result.get("temporary_directory_removed") is True
        verified = result.get("status") == "completed" and cleanup
        final_halt = None if verified else previous_halt
        if not cleanup:
            final_halt = "cleanup_unconfirmed"
        elif state["elapsed_seconds"] + elapsed >= 5400:
            final_halt = "media_time_budget"
        final_entry = entry | {
            "status": "probe_completed" if verified else "failed",
            "cleanup": cleanup,
            "reason": reason,
            "seconds": elapsed,
            "run_sha256": file_hash(folder / "run.json")
            if (folder / "run.json").exists()
            else None,
        }
        if verified:
            final_entry["media_sha256"] = result["media_fingerprint"]["sha256"]
            final_entry["probe_features_sha256"] = file_hash(folder / "features.json")
        summary = {
            "source_available": verified,
            "attempts": len(state["videos"]),
            "elapsed_seconds": state["elapsed_seconds"] + elapsed,
            "halt_reason": final_halt,
            "probe_reason": reason,
            "cleanup": cleanup,
        }
        receipt = {
            "request_id": request_id,
            "operator_request": "explicit_user_media_recheck_in_this_chat",
            "verified_at_utc": datetime.now(UTC).isoformat(),
            "reserved_checkpoint_sha256": reserved_hash,
            "previous_halt_reason": previous_halt,
            "entry": final_entry,
            "elapsed_seconds": elapsed,
            "final_halt_reason": final_halt,
            "summary": summary,
        }
        save(receipt_path, receipt)  # Proof is durable before clearing the terminal halt.
        return finalize(checkpoint, state, receipt_path, receipt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--pool", type=Path, required=True)
    parser.add_argument("--operator-request-id", required=True)
    args = parser.parse_args()
    with reserved_guard(args.parent, Path.cwd()):
        print(json.dumps(probe(args.pool, args.parent, args.operator_request_id)))


if __name__ == "__main__":
    main()

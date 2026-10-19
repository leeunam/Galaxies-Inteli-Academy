"""Temporary extraction and assisted curation for the fixed 300-reference protocol."""

from __future__ import annotations

import argparse
import contextlib
import io
import itertools
import json
import os
import re
import signal
import time
from collections import Counter
from pathlib import Path

from scripts.channel_partitions import load_partitions, new_channel_partition
from scripts.diagnose_m1 import private_output
from scripts.expand_reference_pool import validate_parent_metadata
from scripts.language_audit import language_status
from scripts.observed_baseline import CohortRelease
from scripts.pilot_licensed_media import (
    extract_features,
    frames_and_properties,
    prepare_models,
    run_session,
    select_vlm_samples,
)
from scripts.pilot_youtube_media import download_video
from scripts.prepare_media_queue import configuration
from scripts.private_checkpoint import file_hash, lock, private_path, save


def validate_reviews(videos):
    included = [v for v in videos if v.get("review", {}).get("decision") == "included"]
    counts = Counter(v["review"]["sector"] for v in included)
    channels = Counter(v["channel_id"] for v in included)
    if (
        set(counts) - {"moda", "beleza"}
        or any(n > 50 for n in counts.values())
        or any(n > 5 for n in channels.values())
    ):
        raise ValueError("curation_capacity_exceeded")
    return counts, channels


def review_entry(entry, decision, features_sha256, run_sha256, sheet_sha256):
    if entry["status"] != "completed" or entry.get("automatic_exclusion"):
        raise ValueError("entry_not_reviewable")
    if (
        decision.get("decision") not in ("included", "excluded")
        or decision.get("sector") not in ("moda", "beleza", None)
        or (decision["decision"] == "included" and decision.get("sector") is None)
        or not isinstance(decision.get("reason"), str)
        or not decision["reason"].strip()
        or decision.get("image_review_performed") is not True
        or decision.get("transcript_review_performed") is not True
        or decision.get("contact_sheet_sha256") != sheet_sha256
    ):
        raise ValueError("invalid_curation_decision")
    return {
        **decision,
        "video_id": entry["video_id"],
        "features_sha256": features_sha256,
        "run_sha256": run_sha256,
        "contact_sheet_sha256": sheet_sha256,
        "image_review_performed": True,
        "human_review": False,
        "human_listening": False,
        "reviewer": "Codex_assisted_review",
        "language_attribution": "pt-BR_assisted_not_dialect_certification",
    }


@contextlib.contextmanager
def deadline(seconds):
    def expired(*_):
        raise TimeoutError("media_time_budget")

    previous = signal.signal(signal.SIGALRM, expired)
    signal.setitimer(signal.ITIMER_REAL, max(0.001, seconds))
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def sweep_reviews(state, checkpoint, root):
    pending = list(state.get("cleanup_pending", []))
    for relative in pending:
        path = private_path(root / relative, root)
        try:
            path.unlink(missing_ok=True)
        except OSError:
            if state["halt_reason"] != "contact_sheet_cleanup":
                state["halt_before_cleanup"] = state["halt_reason"]
            state["halt_reason"] = "contact_sheet_cleanup"
            save(checkpoint, state)
            raise ValueError("contact_sheet_cleanup_pending") from None
        state["cleanup_pending"].remove(relative)
        save(checkpoint, state)
    if state["halt_reason"] == "contact_sheet_cleanup":
        state["halt_reason"] = state.pop("halt_before_cleanup", None)
        save(checkpoint, state)


def load_state(pool, parent_dir):
    release = CohortRelease.model_validate_json((parent_dir / "cohort.json").read_bytes())
    manifest = load_partitions(parent_dir / "partitions.json")
    validate_parent_metadata(release, manifest)
    plan = json.loads((pool / "candidates.json").read_bytes())
    core = json.loads((parent_dir / "extractor-config.json").read_bytes())
    if configuration(False) != core:
        raise ValueError("frozen_extractor_changed")
    excluded = {r.channel_id for r in release.records}
    if any(
        r["audit"]["channel_id"] in excluded
        or r["audit"]["channel_id"] not in plan["channel_allocation"]
        or plan["channel_allocation"][r["audit"]["channel_id"]]
        != new_channel_partition(r["audit"]["channel_id"])
        for r in plan["records"]
    ):
        raise ValueError("candidate_channel_partition_mismatch")
    path = pool / "extraction/checkpoint.json"
    state = (
        json.loads(path.read_bytes())
        if path.exists()
        else {
            "protocol": "expansion300-media-v1",
            "selection_sha256": file_hash(pool / "candidates.json"),
            "parent_sha256": release.release_sha256,
            "config": core,
            "videos": [],
            "elapsed_seconds": 0.0,
            "halt_reason": None,
        }
    )
    if (
        state["selection_sha256"] != file_hash(pool / "candidates.json")
        or state["config"] != core
        or state["parent_sha256"] != release.release_sha256
    ):
        raise ValueError("media_checkpoint_changed")
    validate_reviews(state["videos"])
    return release, plan, core, state


def run(pool, parent, limit):
    root = Path.cwd()
    folder = pool / "extraction"
    folder.mkdir(mode=0o700, exist_ok=True)
    with lock(folder / ".lock"):
        release, plan, core, state = load_state(pool, parent)
        sweep_reviews(state, folder / "checkpoint.json", root)
        if state["halt_reason"]:
            raise ValueError("media_extraction_halted")
        if any("review" not in v for v in state["videos"]):
            raise ValueError("finish_pending_curation_first")
        sectors, channels = validate_reviews(state["videos"])
        if sum(sectors.values()) == 100:
            print(json.dumps({"status": "target_reached"}))
            return
        scratch_root = root / "data/private/media-temp"
        if list(scratch_root.glob("galaxies-media-*")):
            raise ValueError("temporary_session_pending")
        import av
        import imageio_ffmpeg
        from PIL import Image, ImageDraw

        os.environ.update(
            HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", TOKENIZERS_PARALLELISM="false"
        )
        models, cache = prepare_models(False), {}
        ffmpeg = Path(imageio_ffmpeg.get_ffmpeg_exe())
        seen = {v["video_id"] for v in state["videos"]}
        fingerprints = {r.media_sha256 for r in release.records} | {
            v["media_sha256"] for v in state["videos"] if v.get("media_sha256")
        }
        used, started = 0, time.monotonic()
        for row in plan["records"]:
            vid, channel = row["audit"]["video_id"], row["audit"]["channel_id"]
            if vid in seen or channels[channel] >= 5:
                continue
            if used >= min(limit, 100 - sum(sectors.values())) or len(state["videos"]) >= 300:
                break
            if state["elapsed_seconds"] + time.monotonic() - started >= 5400:
                state["halt_reason"] = "media_time_budget"
                break
            destination = folder / "sessions" / vid
            if destination.exists():
                raise ValueError("interrupted_attempt_requires_recovery")
            review_dir = folder / "temporary-review"
            review_dir.mkdir(mode=0o700, exist_ok=True)
            sheet_path = review_dir / f"{vid}.png"

            def extract(media, scratch, vid=vid, sheet_path=sheet_path):
                with (
                    av.logging.Capture(local=True) as messages,
                    contextlib.redirect_stdout(io.StringIO()),
                ):
                    props, frames = frames_and_properties(media, scratch)
                    if props["height"] <= props["width"]:
                        raise ValueError("nonvertical_video")
                    result = extract_features(media, scratch, models, False, model_cache=cache)
                result["decoder_warning_counts"] = dict(
                    Counter(name for level, name, _ in messages if level <= av.logging.WARNING)
                )
                paths, seconds = select_vlm_samples(frames, props)
                sheet = Image.new("RGB", (320 * len(paths), 360), "white")
                draw = ImageDraw.Draw(sheet)
                for i, (frame, second) in enumerate(zip(paths, seconds, strict=True)):
                    with Image.open(frame) as picture:
                        picture.thumbnail((320, 330))
                        sheet.paste(picture, (320 * i, 25))
                    draw.text((320 * i + 4, 4), f"{vid} / {i + 1} @ {second:.3f}s", fill="black")
                with private_output(sheet_path, "wb") as output:
                    sheet.save(output, format="PNG")
                return result

            used += 1
            entry = {
                "video_id": vid,
                "channel_id": channel,
                "run_ref": str((destination / "run.json").relative_to(root)),
            }
            print(
                json.dumps({"stage": "extracting", "attempt": len(state["videos"]) + 1}), flush=True
            )
            try:
                with deadline(5400 - state["elapsed_seconds"] - (time.monotonic() - started)):
                    result = run_session(
                        destination,
                        scratch_root,
                        extract,
                        lambda media, vid=vid: download_video(media, vid, ffmpeg),
                        source=row,
                        model_manifest=core["models"],
                    )
                features = json.loads((destination / "features.json").read_bytes())
                p = features["asr_language_probability"]
                lang = (
                    language_status(features["asr_language"], p, features["speech_segments"])
                    if p is not None
                    else "inconclusive"
                )
                tokens = re.findall(r"\w+", features["transcript"].lower())
                repetition = max(
                    (sum(1 for _ in group) for _, group in itertools.groupby(tokens)), default=0
                )
                fingerprint = result["media_fingerprint"]["sha256"]
                exclusion = (
                    "duplicate_media"
                    if fingerprint in fingerprints
                    else "portuguese_not_established"
                    if lang != "portuguese_detected_review_locale"
                    else "severe_asr_repetition"
                    if repetition >= 20
                    else None
                )
                entry.update(
                    status="completed",
                    cleanup=result["temporary_directory_removed"],
                    language_triage=lang,
                    media_sha256=fingerprint,
                    automatic_exclusion=exclusion,
                    features_ref=str((destination / "features.json").relative_to(root)),
                    features_sha256=file_hash(destination / "features.json"),
                    run_sha256=file_hash(destination / "run.json"),
                    review_ref=str(sheet_path.relative_to(root)),
                    seconds=result["total_seconds"],
                )
                fingerprints.add(fingerprint)
                if exclusion:
                    entry["review"] = {
                        "decision": "excluded",
                        "sector": None,
                        "reason": exclusion,
                        "human_review": False,
                        "image_review_performed": False,
                    }
            except (RuntimeError, ValueError, OSError, TimeoutError) as exc:
                result = (
                    json.loads((destination / "run.json").read_bytes())
                    if (destination / "run.json").exists()
                    else {}
                )
                reason = str(exc) if re.fullmatch(r"[a-z_]+", str(exc)) else type(exc).__name__
                entry.update(
                    status="failed",
                    reason=reason,
                    cleanup=result.get("temporary_directory_removed", False),
                    review={
                        "decision": "excluded",
                        "sector": None,
                        "reason": reason,
                        "human_review": False,
                        "image_review_performed": False,
                    },
                )
                if (
                    reason in ("authentication_or_bot_check", "http_access_denied_or_rate_limited")
                    or not entry["cleanup"]
                ):
                    state["halt_reason"] = reason
            if "review" in entry:
                state.setdefault("cleanup_pending", []).append(str(sheet_path.relative_to(root)))
            state["videos"].append(entry)
            if not entry["cleanup"]:
                state["halt_reason"] = "cleanup_unconfirmed"
            state["elapsed_seconds"] += time.monotonic() - started
            if state["elapsed_seconds"] >= 5400:
                state["halt_reason"] = "media_time_budget"
            started = time.monotonic()
            save(folder / "checkpoint.json", state)
            sweep_reviews(state, folder / "checkpoint.json", root)
            print(
                json.dumps(
                    {
                        k: entry.get(k)
                        for k in (
                            "status",
                            "language_triage",
                            "automatic_exclusion",
                            "reason",
                            "seconds",
                        )
                    }
                ),
                flush=True,
            )
            if state["halt_reason"]:
                break
        save(folder / "checkpoint.json", state)
        print(
            json.dumps(
                {
                    "attempts": len(state["videos"]),
                    "included": dict(sectors),
                    "elapsed_seconds": state["elapsed_seconds"],
                    "halt_reason": state["halt_reason"],
                }
            ),
            flush=True,
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["run", "review", "inspect"])
    parser.add_argument("--pool", type=Path, required=True)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=20, choices=range(1, 301))
    parser.add_argument("--decisions", type=Path)
    args = parser.parse_args()
    root = Path.cwd()
    pool = private_path(args.pool, root)
    if args.operation == "run":
        run(pool, args.parent, args.limit)
        return
    _, _, _, state = load_state(pool, args.parent)
    pending = [v for v in state["videos"] if "review" not in v]
    if args.operation == "inspect":
        result = []
        for entry in pending:
            features = json.loads((root / entry["features_ref"]).read_bytes())
            result.append(
                {
                    "video_id": entry["video_id"],
                    "review_ref": entry["review_ref"],
                    "transcript": features["transcript"],
                }
            )
        print(json.dumps(result, ensure_ascii=False))
        return
    decisions = {
        r["video_id"]: r for r in json.loads(private_path(args.decisions, root).read_bytes())
    }
    if set(decisions) - {v["video_id"] for v in pending}:
        raise ValueError("unknown_pending_review")
    with lock(pool / "extraction/.lock"):
        sectors, channels = validate_reviews(state["videos"])
        sweep_reviews(state, pool / "extraction/checkpoint.json", root)
        for entry in pending:
            if entry["video_id"] not in decisions:
                continue
            fp, rp, sheet = (root / entry[k] for k in ("features_ref", "run_ref", "review_ref"))
            if file_hash(fp) != entry["features_sha256"] or file_hash(rp) != entry["run_sha256"]:
                raise ValueError("curation_evidence_changed")
            decision = decisions[entry["video_id"]]
            annotation = review_entry(
                entry, decision, file_hash(fp), file_hash(rp), file_hash(sheet)
            )
            if annotation["decision"] == "included":
                sector = annotation["sector"]
                if sectors[sector] >= 50 or channels[entry["channel_id"]] >= 5:
                    annotation.update(
                        decision="excluded", reason="preregistered_sector_or_channel_capacity"
                    )
                else:
                    sectors[sector] += 1
                    channels[entry["channel_id"]] += 1
            entry["review"] = annotation
            state.setdefault("cleanup_pending", []).append(str(sheet.relative_to(root)))
        validate_reviews(state["videos"])
        save(pool / "extraction/checkpoint.json", state)
        sweep_reviews(state, pool / "extraction/checkpoint.json", root)
        print(
            json.dumps(
                {
                    "included": dict(sectors),
                    "pending": sum("review" not in v for v in state["videos"]),
                }
            )
        )


if __name__ == "__main__":
    main()

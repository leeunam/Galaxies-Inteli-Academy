"""Private sequential audiovisual queue. Preparing/inspecting never loads models or uses network."""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from scripts.pilot_licensed_media import (
    MODELS,
    ROOT,
    extract_features,
    prepare_models,
    run_session,
    vlm_manifest,
)
from scripts.pilot_youtube_media import download_video, validate_candidates
from scripts.private_checkpoint import digest, file_hash, lock, private_path, save

PROTOCOL = "media-queue-v1"
STOP_REASONS = {"authentication_or_bot_check", "http_access_denied_or_rate_limited"}


def configuration(with_vlm=False):
    packages = {}
    for name in [
        "av",
        "faster-whisper",
        "sentence-transformers",
        "torch",
        "transformers",
        "yt-dlp",
        "imageio-ffmpeg",
        "numpy",
        "Pillow",
    ]:
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = "not_installed"
    files = [
        "prepare_media_queue.py",
        "private_checkpoint.py",
        "pilot_licensed_media.py",
        "pilot_youtube_media.py",
        "gguf_visual_attributes.py",
        "prepare_gguf_vlm.py",
        "visual_attributes.py",
        "audio_features.py",
    ]
    return {
        "with_vlm": with_vlm,
        "packages": packages,
        "models": {
            **{k: {"repo": v[0], "revision": v[1]} for k, v in MODELS.items()},
            **({"vlm": vlm_manifest()} if with_vlm else {}),
        },
        "extractor_files_sha256": {name: file_hash(ROOT / "scripts" / name) for name in files},
    }


def evidence(row):
    refs = {}
    for key in ["usage_review", "curation_review"]:
        review = row["curation"].get(key, {})
        if review.get("status") != "approved":
            return None
        if (
            not review.get("reviewer")
            or not review.get("reviewed_at_utc")
            or (key == "usage_review" and review.get("source_status") != "verified")
        ):
            return None
        if not isinstance(review.get("evidence_path"), str):
            return None
        path = Path(review["evidence_path"])
        path = private_path(path if path.is_absolute() else ROOT / path, ROOT)
        if not path.is_file():
            raise ValueError("Review evidence must exist in private storage")
        refs[key] = {
            "path": str(path.relative_to(ROOT.resolve())),
            "sha256": file_hash(path),
            "reviewer": review["reviewer"],
            "reviewed_at_utc": review["reviewed_at_utc"],
        }
    return refs


def prepare_queue(rows, folder: Path, config, *, limit=20):
    folder = private_path(folder, ROOT)
    if not isinstance(rows, list) or not 1 <= len(rows) <= 300 or not 1 <= limit <= 300:
        raise ValueError("Queue accepts 1–300 candidates; limit must be 1–300")
    ids, videos = set(), []
    for row in rows:
        validate_candidates([row])  # Preserve the legacy pilot's three-video contract.
        if not all(
            isinstance(row.get(k), dict)
            for k in ["audit", "curation", "metadata", "target", "diagnostics"]
        ):
            raise ValueError("Candidates require audit/curation/metadata/target/diagnostics")
        video_id = row["audit"]["video_id"]
        if video_id in ids:
            raise ValueError("Duplicate queue video ID")
        ids.add(video_id)
        if len(videos) < limit:
            refs = evidence(row)
            videos.append(
                {
                    "video_id": video_id,
                    "candidate": row,
                    "review_evidence": refs,
                    "status": "pending" if refs else "blocked",
                    "attempts": [],
                }
            )
    with lock(folder / ".lock"):
        if any(p.name != ".lock" for p in folder.iterdir()):
            raise ValueError("Use a fresh queue directory; previous evidence is never overwritten")
        state = {
            "protocol": PROTOCOL,
            "config": config,
            "config_sha256": digest(config),
            "videos": videos,
            "training_eligible": False,
            "halt_reason": None,
        }
        state["candidate_sha256"] = digest([v["candidate"] for v in videos])
        save(folder / "queue.json", state)
    return state


def load_queue(folder, config):
    state = json.loads((folder / "queue.json").read_text())
    if (
        state.get("protocol") != PROTOCOL
        or state.get("config") != config
        or state.get("config_sha256") != digest(config)
    ):
        raise ValueError("Protocol/extractor configuration changed; create a fresh queue")
    videos = state.get("videos")
    if (
        not isinstance(videos, list)
        or not 1 <= len(videos) <= 300
        or digest([v["candidate"] for v in videos]) != state.get("candidate_sha256")
    ):
        raise ValueError("Candidate protocol changed; create a fresh queue")
    ids = []
    for video in videos:
        validate_candidates([video["candidate"]])
        ids.append(video["video_id"])
        if (
            video["video_id"] != video["candidate"]["audit"]["video_id"]
            or video["status"] not in {"pending", "running", "completed", "failed", "blocked"}
            or not isinstance(video["attempts"], list)
            or len(video["attempts"]) > 2
            or (video["status"] == "running" and not video["attempts"])
        ):
            raise ValueError("Invalid video checkpoint protocol")
        for index, attempt in enumerate(video["attempts"], 1):
            if attempt.get("folder") != f"attempts/{video['video_id']}/{index}":
                raise ValueError("Invalid attempt path")
        if video["status"] == "completed":
            if not video["attempts"] or not video["attempts"][-1].get("artifacts"):
                raise ValueError("Completed video has no artifact fingerprints")
            attempt = video["attempts"][-1]
            if set(attempt["artifacts"]) != {"features.json", "run.json"}:
                raise ValueError("Incomplete artifact manifest")
            for name, expected in attempt["artifacts"].items():
                path = private_path(folder / attempt["folder"] / name, ROOT)
                if not path.is_file() or file_hash(path) != expected:
                    raise ValueError("Completed artifact changed; create a fresh queue")
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate checkpoint IDs")
    return state


def summary(state):
    return {
        "videos": len(state["videos"]),
        "states": {
            status: sum(v["status"] == status for v in state["videos"])
            for status in ["pending", "running", "completed", "failed", "blocked"]
        },
        "halt_reason": state["halt_reason"],
        "training_eligible": False,
    }


def execute_queue(
    folder: Path,
    config,
    extractor,
    downloader,
    *,
    max_videos=20,
    max_seconds=3600,
    clock=time.monotonic,
):
    folder = private_path(folder, ROOT)
    if not 1 <= max_videos <= 300 or not math.isfinite(max_seconds) or max_seconds <= 0:
        raise ValueError("Use 1–300 videos and a positive finite time budget")
    with lock(folder / ".lock"):
        state = load_queue(folder, config)
        interrupted = [video for video in state["videos"] if video["status"] == "running"]
        if interrupted:
            for video in interrupted:
                video["status"] = "failed"
                video["attempts"][-1]["reason"] = "interrupted_cleanup_unconfirmed"
            state["halt_reason"] = "cleanup_unconfirmed"
            save(folder / "queue.json", state)
        if state["halt_reason"]:
            return summary(state)
        started, used = clock(), 0
        for video in state["videos"]:
            if video["status"] in {"completed", "blocked"} or len(video["attempts"]) >= 2:
                continue
            if used >= max_videos or clock() - started >= max_seconds:
                break
            if (
                not video["review_evidence"]
                or evidence(video["candidate"]) != video["review_evidence"]
            ):
                video["status"] = "blocked"
                save(folder / "queue.json", state)
                continue
            used += 1
            attempt = {"folder": f"attempts/{video['video_id']}/{len(video['attempts']) + 1}"}
            destination = private_path(folder / attempt["folder"], ROOT)
            if destination.exists():
                raise ValueError("Attempt evidence already exists; never overwrite")
            video["attempts"].append(attempt)
            video["status"] = "running"
            save(folder / "queue.json", state)
            failure = None
            try:
                result = run_session(
                    destination,
                    ROOT / "data/private/media-temp",
                    extractor,
                    lambda p, vid=video["video_id"]: downloader(p, vid),
                    source=video["candidate"],
                    model_manifest=config["models"],
                )
                if result["status"] != "completed" or not result["temporary_directory_removed"]:
                    raise RuntimeError("cleanup_unconfirmed")
                attempt["artifacts"] = {
                    name: file_hash(destination / name) for name in ["features.json", "run.json"]
                }
                video["status"] = "completed"
            except BaseException as exc:  # noqa: BLE001 - checkpoint cancellation, then re-raise it.
                failure = exc
                video["status"] = "failed"
                reason = str(exc) if isinstance(exc, RuntimeError) else "processing_failed"
                attempt["reason"] = reason if reason in STOP_REASONS else "processing_failed"
                run = destination / "run.json"
                try:
                    result = json.loads(run.read_text()) if run.is_file() else {}
                except (ValueError, OSError):
                    result = {}
                if not result.get("temporary_directory_removed"):
                    state["halt_reason"] = "cleanup_unconfirmed"
                elif attempt["reason"] in STOP_REASONS:
                    state["halt_reason"] = attempt["reason"]
            finally:
                save(folder / "queue.json", state)
            if failure is not None and not isinstance(failure, Exception):
                raise failure
            if state["halt_reason"]:
                break
        return summary(state)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["prepare", "inspect", "run"])
    parser.add_argument("--queue", required=True, type=Path)
    parser.add_argument("--candidates", type=Path)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--max-seconds", type=float, default=3600)
    parser.add_argument("--with-vlm", action="store_true")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    folder, config = private_path(args.queue, ROOT), configuration(args.with_vlm)
    if args.operation == "prepare":
        if not args.candidates or args.execute or args.resume:
            parser.error("Prepare requires --candidates and no execution/resume flags")
        rows = json.loads(private_path(args.candidates, ROOT).read_text())
        report = summary(prepare_queue(rows, folder, config, limit=args.limit))
    elif args.operation == "inspect" or not args.execute:
        with lock(folder / ".lock"):
            report = summary(load_queue(folder, config))
    else:
        if not args.resume:
            parser.error("Execution requires --execute --resume")
        # Models and ffmpeg are initialized lazily inside the queue lock, only after the gates.
        models = None

        def extract(media, scratch):
            nonlocal models
            import av

            if models is None:
                os.environ["HF_HUB_OFFLINE"] = "1"
                os.environ["TRANSFORMERS_OFFLINE"] = "1"
                models = prepare_models(args.with_vlm)
            with av.open(str(media)) as container:
                if container.streams.video[0].height <= container.streams.video[0].width:
                    raise ValueError("Candidate is not vertical")
            return extract_features(media, scratch, models, args.with_vlm)

        def downloader(path, video_id):
            import imageio_ffmpeg

            return download_video(path, video_id, Path(imageio_ffmpeg.get_ffmpeg_exe()))

        report = execute_queue(
            folder, config, extract, downloader, max_videos=args.limit, max_seconds=args.max_seconds
        )
    print(json.dumps(report))


if __name__ == "__main__":
    main()

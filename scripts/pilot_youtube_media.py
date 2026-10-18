"""Bounded technical pilot: public API candidates, temporary download and local extraction.

No credentials, browser cookies, proxy rotation or access-restriction workaround.
Successful acquisition is not a license or a training-eligibility decision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

from scripts.pilot_licensed_media import (
    MODELS,
    ROOT,
    atomic_json,
    extract_features,
    prepare_models,
    run_session,
    vlm_manifest,
)


def validate_candidates(rows: object) -> list[dict]:
    if not isinstance(rows, list) or not 1 <= len(rows) <= 3:
        raise ValueError("Pilot accepts one to three API candidate records")
    ids = []
    for row in rows:
        video_id = row["audit"]["video_id"]
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
            raise ValueError("Invalid canonical video ID")
        if row["audit"]["source_url"] != "https://www.youtube.com/watch?v=" + video_id:
            raise ValueError("Source URL must match the canonical API video ID")
        ids.append(video_id)
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate pilot video IDs")
    return rows


def private_path(path: Path) -> Path:
    resolved = path.resolve()
    if not resolved.is_relative_to((ROOT / "data/private").resolve()):
        raise ValueError("Pilot inputs and outputs must be inside ignored data/private")
    return resolved


def classify_failure(text: str) -> str:
    text = text.lower()
    if "sign in" in text or "not a bot" in text or "login required" in text:
        return "authentication_or_bot_check"
    if "http error 403" in text or "http error 429" in text:
        return "http_access_denied_or_rate_limited"
    if "name resolution" in text or "name or service not known" in text:
        return "network_dns_failure"
    if "private video" in text or "video unavailable" in text or "removed" in text:
        return "video_unavailable"
    if "does not pass filter" in text:
        return "outside_duration_or_live_filter"
    return "download_failed"


def download_video(destination: Path, video_id: str, ffmpeg: Path) -> dict:
    command = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--ignore-config",
        "--no-plugin-dirs",
        "--no-remote-components",
        "--no-playlist",
        "--no-cache-dir",
        "--no-progress",
        "--no-warnings",
        "--js-runtimes",
        "node",
        "--socket-timeout",
        "20",
        "--retries",
        "1",
        "--fragment-retries",
        "1",
        "--extractor-retries",
        "1",
        "--max-filesize",
        "32M",
        "--limit-rate",
        "5M",
        "--match-filters",
        "duration <= 60 & !is_live",
        "--format",
        "best[height<=720][vcodec!=none][acodec!=none]/bestvideo[height<=720]+bestaudio",
        "--ffmpeg-location",
        str(ffmpeg),
        "--merge-output-format",
        "mkv",
        "--output",
        str(destination.parent / "download.%(ext)s"),
        "--",
        "https://www.youtube.com/watch?v=" + video_id,
    ]
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = process.communicate(timeout=180)
    except BaseException:
        # Also terminate any ffmpeg child before the temporary directory is removed.
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise
    if process.returncode:
        raise RuntimeError(classify_failure(stdout + "\n" + stderr))
    files = [
        p for p in destination.parent.glob("download.*") if p.suffix in {".mp4", ".webm", ".mkv"}
    ]
    if len(files) != 1:
        raise RuntimeError("download_produced_no_unique_media_file")
    media = files[0]
    if media.stat().st_size > 64 * 1024 * 1024:
        raise ValueError("download_exceeded_final_byte_budget")
    media.replace(destination)
    return {
        "size_bytes": destination.stat().st_size,
        "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "yt_dlp_version": version("yt-dlp"),
    }


def run_batch(candidates, output, scratch, extractor, downloader, model_manifest=None) -> dict:
    rows = validate_candidates(candidates)
    if output.exists() and any(output.iterdir()):
        raise ValueError("Use a fresh pilot output directory")
    outcomes = []
    for row in rows:
        video_id = row["audit"]["video_id"]
        folder = output / video_id
        print(json.dumps({"stage": "pilot_video", "video_id": video_id}), flush=True)
        try:
            state = run_session(
                folder,
                scratch,
                extractor,
                lambda path, vid=video_id: downloader(path, vid),
                source=row,
                model_manifest=model_manifest,
            )
            outcomes.append(
                {
                    "video_id": video_id,
                    **{
                        key: state[key]
                        for key in [
                            "status",
                            "temporary_directory_removed",
                            "total_seconds",
                            "process_peak_rss_mib",
                        ]
                    },
                }
            )
        except (RuntimeError, ValueError, OSError, subprocess.SubprocessError) as exc:
            state = (
                json.loads((folder / "run.json").read_text())
                if (folder / "run.json").exists()
                else {}
            )
            outcomes.append(
                {
                    "video_id": video_id,
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    # Persist only controlled error codes, never signed URLs or downloader logs.
                    "reason": str(exc)
                    if isinstance(exc, RuntimeError) and re.fullmatch(r"[a-z_]+", str(exc))
                    else type(exc).__name__,
                    "temporary_directory_removed": state.get("temporary_directory_removed", False),
                }
            )
    report = {
        "purpose": "deliberate_high_reach_technical_pilot_not_training_sample",
        "training_eligible": False,
        "memory_measurement": "cumulative_parent_process_peak_excludes_child_processes",
        "videos": outcomes,
        "completed": sum(x["status"] == "completed" for x in outcomes),
        "failed": sum(x["status"] == "failed" for x in outcomes),
    }
    atomic_json(output / "batch.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--with-vlm", action="store_true")
    args = parser.parse_args()
    input_path, output = private_path(args.candidates), private_path(args.output)
    rows = validate_candidates(json.loads(input_path.read_text()))
    if output.exists() and any(output.iterdir()):
        parser.error("Use a fresh output directory before loading models or downloading")
    import imageio_ffmpeg

    ffmpeg = Path(imageio_ffmpeg.get_ffmpeg_exe())
    models = prepare_models(args.with_vlm)

    def extract(media, scratch):
        import av

        with av.open(str(media)) as container:
            video = container.streams.video[0]
            if video.height <= video.width:
                raise ValueError("Candidate is not vertical")
        return extract_features(media, scratch, models, args.with_vlm)

    manifest = {k: {"repo": v[0], "revision": v[1]} for k, v in MODELS.items()}
    if args.with_vlm:
        manifest["vlm"] = vlm_manifest()
    report = run_batch(
        rows,
        output,
        ROOT / "data/private/media-temp",
        extract,
        lambda path, video_id: download_video(path, video_id, ffmpeg),
        model_manifest=manifest,
    )
    print(json.dumps({"completed": report["completed"], "failed": report["failed"]}), flush=True)


if __name__ == "__main__":
    main()

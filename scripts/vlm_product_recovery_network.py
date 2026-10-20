"""Same YouTube media route with zero internal retries for recovery's strict cap."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

import imageio_ffmpeg

from scripts.pilot_youtube_media import classify_failure
from scripts.private_checkpoint import file_hash


def download_video(destination: Path, video_id: str) -> dict:
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
        "0",
        "--fragment-retries",
        "0",
        "--extractor-retries",
        "0",
        "--max-filesize",
        "32M",
        "--limit-rate",
        "5M",
        "--match-filters",
        "duration <= 60 & !is_live",
        "--format",
        "best[height<=720][vcodec!=none][acodec!=none]/bestvideo[height<=720]+bestaudio",
        "--ffmpeg-location",
        imageio_ffmpeg.get_ffmpeg_exe(),
        "--merge-output-format",
        "mkv",
        "--output",
        str(destination.parent / "download.%(ext)s"),
        "--",
        "https://www.youtube.com/watch?v=" + video_id,
    ]
    process = subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True
    )
    try:
        stdout, stderr = process.communicate(timeout=180)
    except BaseException:
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
        "sha256": file_hash(destination),
        "yt_dlp_version": version("yt-dlp"),
        "internal_retries": 0,
    }

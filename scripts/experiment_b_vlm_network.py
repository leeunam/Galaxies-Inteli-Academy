"""Frozen YouTube command with a typed transient-DNS error; no alternate access route."""

from __future__ import annotations

import hashlib
import os
import signal
import socket
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

from scripts.pilot_youtube_media import classify_failure


class TransientDNSFailure(RuntimeError):
    def __init__(self, diagnostic_sha256):
        super().__init__("temporary_network_dns_failure")
        self.diagnostic_sha256 = diagnostic_sha256


def dns_preflight():
    try:
        return bool(socket.getaddrinfo("www.youtube.com", 443, type=socket.SOCK_STREAM))
    except OSError:
        return False


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
        diagnostic = stdout + "\n" + stderr
        classification = classify_failure(diagnostic)
        if classification == "network_dns_failure" and (
            "temporary failure in name resolution" in diagnostic.lower()
            or "[errno -3]" in diagnostic.lower()
        ):
            raise TransientDNSFailure(hashlib.sha256(diagnostic.encode()).hexdigest())
        raise RuntimeError(classification)
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

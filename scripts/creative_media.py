"""Bounded local video inspection in an isolated subprocess (POSIX)."""

from __future__ import annotations

import hashlib
import json
import math
import os
import resource
import subprocess
import sys
from pathlib import Path

MAX_BYTES = 100 * 1024 * 1024
MAX_SECONDS = 60
MAX_WIDTH = 1080
MAX_HEIGHT = 1920
MAX_FRAMES = 7200
TIMEOUT_SECONDS = 30
ROOT = Path(__file__).resolve().parents[1]


class CreativeError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def inspect_media(handle) -> dict:
    if not 0 < os.fstat(handle.fileno()).st_size <= MAX_BYTES:
        raise CreativeError("media_limits_exceeded")
    try:
        process = subprocess.run(
            [sys.executable, "-m", "scripts.creative_media", str(handle.fileno())],
            pass_fds=(handle.fileno(),),
            cwd=ROOT,
            env={"PATH": os.defpath, "OPENBLAS_NUM_THREADS": "1"},
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired:
        raise CreativeError("media_timeout") from None
    if process.returncode != 0:
        raise CreativeError("invalid_media")
    result = json.loads(process.stdout)
    if "error" in result:
        raise CreativeError(result["error"])
    return result


def _inspect(handle):
    import av

    av.logging.set_level(av.logging.PANIC)
    sha256 = hashlib.file_digest(handle, "sha256").hexdigest()
    handle.seek(0)
    with av.open(handle) as container:
        if not set(container.format.name.split(",")) & {"mov", "mp4", "matroska", "webm"}:
            raise CreativeError("invalid_media")
        if len(container.streams.video) != 1:
            raise CreativeError("invalid_media")
        video = container.streams.video[0]
        video.codec_context.thread_count = 1
        width, height = video.codec_context.width, video.codec_context.height
        if not 0 < width < height or width > MAX_WIDTH or height > MAX_HEIGHT:
            raise CreativeError("media_limits_exceeded")
        duration = (
            float(video.duration * video.time_base)
            if video.duration is not None
            else (container.duration or 0) / av.time_base
        )
        if not math.isfinite(duration) or not 0 < duration <= MAX_SECONDS:
            raise CreativeError("media_limits_exceeded")
        first, previous, count = None, None, 0
        for frame in container.decode(video):
            count += 1
            if count > MAX_FRAMES or frame.width != width or frame.height != height:
                raise CreativeError("media_limits_exceeded")
            if frame.pts is None or frame.time_base is None:
                raise CreativeError("invalid_media")
            timestamp = float(frame.pts * frame.time_base)
            first = timestamp if first is None else first
            if previous is not None and timestamp < previous:
                raise CreativeError("invalid_media")
            previous = timestamp
            end = timestamp - first + float((frame.duration or 0) * frame.time_base)
            if end > MAX_SECONDS + 0.001:
                raise CreativeError("media_limits_exceeded")
        if not count:
            raise CreativeError("invalid_media")
    return {
        "sha256": sha256,
        "size_bytes": os.fstat(handle.fileno()).st_size,
        "duration_seconds": duration,
        "width": width,
        "height": height,
    }


def main():
    # Limits apply only to this short-lived decoder, never the application process.
    resource.setrlimit(resource.RLIMIT_CPU, (25, 25))
    resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
    try:
        with os.fdopen(int(sys.argv[1]), "rb") as handle:
            result = _inspect(handle)
    except CreativeError as exc:
        result = {"error": exc.code}
    except (OSError, ValueError):
        result = {"error": "invalid_media"}
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()

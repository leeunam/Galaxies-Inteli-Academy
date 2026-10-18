"""Generated, content-free video fixtures; no real media or network."""

from pathlib import Path

import av
import pytest

from scripts.creative_registry import CreativeRegistry


@pytest.fixture
def video_factory():
    def create(path: Path, *, width=64, height=96, frames=2, rate=10):
        path.parent.mkdir(parents=True, exist_ok=True)
        with av.open(str(path), "w") as output:
            stream = output.add_stream("mpeg4", rate=rate)
            stream.width, stream.height = width, height
            stream.pix_fmt = "yuv420p"
            for _ in range(frames):
                frame = av.VideoFrame(width, height, "yuv420p")
                for plane in frame.planes:
                    plane.update(bytes(plane.buffer_size))
                for packet in stream.encode(frame):
                    output.mux(packet)
            for packet in stream.encode():
                output.mux(packet)
        return path

    return create


@pytest.fixture
def registry(tmp_path):
    uploads = tmp_path / "uploads"
    uploads.mkdir()
    return CreativeRegistry(uploads, tmp_path / "private" / "registry.json")


@pytest.fixture
def registered(registry, video_factory):
    video_factory(registry.uploads_root / "demo.mp4")
    result = registry.register(
        {
            "campaign_id": "demo",
            "sector": "moda",
            "relative_path": "demo.mp4",
        }
    )
    assert result["status"] == "registered", result
    return result

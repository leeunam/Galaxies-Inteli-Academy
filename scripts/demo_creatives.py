"""Reproducible offline demo: generated videos, direct Python and real STDIO client."""

import asyncio
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import av
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from scripts.creative_analysis import analyze_creatives
from scripts.creative_registry import CreativeRegistry

ROOT = Path(__file__).resolve().parents[1]


def make_synthetic_video(path: Path):
    """Create a 0.2-second blank vertical video, with no third-party media."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with av.open(str(path), "w") as output:
        stream = output.add_stream("mpeg4", rate=10)
        stream.width, stream.height, stream.pix_fmt = 64, 96, "yuv420p"
        for _ in range(2):
            frame = av.VideoFrame(64, 96, "yuv420p")
            for plane in frame.planes:
                plane.update(bytes(plane.buffer_size))
            for packet in stream.encode(frame):
                output.mux(packet)
        for packet in stream.encode():
            output.mux(packet)


def stdio_transport(registry: CreativeRegistry, *, log_file=None):
    return StdioTransport(
        command=sys.executable,
        args=[
            "-m",
            "scripts.creative_mcp",
            "--uploads-root",
            str(registry.uploads_root),
            "--registry",
            str(registry.registry_file),
        ],
        cwd=str(ROOT),
        env={},
        keep_alive=False,
        log_file=log_file,
    )


async def demonstrate(registry: CreativeRegistry):
    ids = []
    for index in range(5):
        name = f"synthetic-{index}.mp4"
        make_synthetic_video(registry.uploads_root / name)
        result = registry.register(
            {
                "campaign_id": "demo",
                "sector": "moda",
                "relative_path": name,
            }
        )
        if result["status"] != "registered":
            raise RuntimeError("Synthetic fixture registration failed")
        ids.append(result["creative_id"])
    results = []
    async with Client(stdio_transport(registry)) as client:
        for count in [1, 2, 5]:
            request = {
                "campaign_id": "demo",
                "creative_ids": ids[:count],
                "sector": "moda",
                "objective": "divulgacao",
                "brief": "Demonstração inteiramente sintética.",
            }
            direct = analyze_creatives(request, registry)
            remote = await client.call_tool("analyze_creatives", {"payload": request}, timeout=180)
            if remote.structured_content != direct:
                raise RuntimeError("Python and STDIO responses differ")
            if direct["status"] != "prediction_unavailable":
                raise RuntimeError("Unexpected demo state")
            results.append({"count": count, "python_stdio_equal": True, "response": direct})
    return {"fixture": "synthetic", "scientific_evaluation": "pending", "results": results}


def main():
    with TemporaryDirectory(prefix="galaxies-issue2-") as folder:
        root = Path(folder)
        registry = CreativeRegistry(root / "uploads", root / "private/registry.json")
        result = asyncio.run(demonstrate(registry))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

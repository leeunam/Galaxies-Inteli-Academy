"""Reproducible offline demo: generated videos, direct Python and real STDIO client."""

import argparse
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


def stdio_transport(
    registry: CreativeRegistry,
    *,
    log_file=None,
    synthetic_baseline: bool = False,
    observed_baseline_dir: Path | None = None,
    m1=None,
):
    return StdioTransport(
        command=sys.executable,
        args=[
            "-m",
            "scripts.creative_mcp",
            "--uploads-root",
            str(registry.uploads_root),
            "--registry",
            str(registry.registry_file),
            *(["--synthetic-baseline"] if synthetic_baseline else []),
            *(
                ["--observed-baseline-dir", str(Path(observed_baseline_dir).resolve())]
                if observed_baseline_dir is not None
                else []
            ),
            *(
                [
                    "--m1-model-dir",
                    str(m1.model_dir.resolve()),
                    "--m1-cohort-dir",
                    str(m1.cohort_dir.resolve()),
                ]
                if m1 is not None
                else []
            ),
        ],
        cwd=str(ROOT),
        env={},
        keep_alive=False,
        log_file=log_file,
    )


async def demonstrate(
    registry: CreativeRegistry,
    *,
    synthetic_baseline: bool = False,
    observed_baseline_dir: Path | None = None,
):
    sectors = (
        ("moda", "beleza") if synthetic_baseline or observed_baseline_dir is not None else ("moda",)
    )
    ids_by_sector = {sector: [] for sector in sectors}
    for index in range(5):
        name = f"synthetic-{index}.mp4"
        make_synthetic_video(registry.uploads_root / name)
        for sector in sectors:
            result = registry.register(
                {"campaign_id": "demo", "sector": sector, "relative_path": name}
            )
            if result["status"] != "registered":
                raise RuntimeError("Synthetic fixture registration failed")
            ids_by_sector[sector].append(result["creative_id"])
    results = []
    async with Client(
        stdio_transport(
            registry,
            synthetic_baseline=synthetic_baseline,
            observed_baseline_dir=observed_baseline_dir,
        )
    ) as client:
        for sector, count in ((sector, count) for sector in sectors for count in (1, 2, 5)):
            request = {
                "campaign_id": "demo",
                "creative_ids": ids_by_sector[sector][:count],
                "sector": sector,
                "objective": "divulgacao",
                "brief": "Demonstração com criativos gerados localmente.",
            }
            direct = analyze_creatives(
                request,
                registry,
                synthetic_baseline=synthetic_baseline,
                observed_baseline_dir=observed_baseline_dir,
            )
            remote = await client.call_tool("analyze_creatives", {"payload": request}, timeout=180)
            if remote.structured_content != direct:
                raise RuntimeError("Python and STDIO responses differ")
            expected_status = (
                "observed_baseline_available"
                if observed_baseline_dir is not None
                else (
                    "synthetic_baseline_available"
                    if synthetic_baseline
                    else "prediction_unavailable"
                )
            )
            if direct["status"] != expected_status:
                raise RuntimeError("Unexpected demo state")
            results.append(
                {"sector": sector, "count": count, "python_stdio_equal": True, "response": direct}
            )
    return {
        "fixture": "synthetic",
        "reference_data": "observed_pilot"
        if observed_baseline_dir is not None
        else "synthetic"
        if synthetic_baseline
        else "none",
        "scientific_evaluation": "pending",
        "real_results_available": observed_baseline_dir is not None,
        "learned_prediction_available": False,
        "synthetic_baseline_enabled": synthetic_baseline,
        "results": results,
    }


def main():
    parser = argparse.ArgumentParser(description="Demonstração Python/MCP com vídeos gerados")
    baseline = parser.add_mutually_exclusive_group()
    baseline.add_argument("--synthetic-baseline", action="store_true")
    baseline.add_argument("--observed-baseline-dir", type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(prefix="galaxies-issue2-") as folder:
        root = Path(folder)
        registry = CreativeRegistry(root / "uploads", root / "private/registry.json")
        result = asyncio.run(
            demonstrate(
                registry,
                synthetic_baseline=args.synthetic_baseline,
                observed_baseline_dir=args.observed_baseline_dir,
            )
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

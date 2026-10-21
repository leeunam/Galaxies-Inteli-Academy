"""Separate opt-in stdio tool for a preserved canonical demo report; no analysis."""

import argparse
import logging
import sys
from pathlib import Path

from fastmcp import FastMCP

from scripts.demo_canonical_report import CanonicalDemoSettings, get_canonical_demo_report


def create_server(settings):
    server = FastMCP("Galaxies — consulta canônica da demo preservada")

    @server.tool(
        name="get_canonical_demo_report",
        annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": False},
    )
    def consult(payload: dict) -> dict:
        """Consulta relatório histórico vinculado; não extrai nem executa modelos/grafo."""
        return get_canonical_demo_report(payload, settings)

    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    args = parser.parse_args()
    settings = CanonicalDemoSettings(args.root, args.manifest, args.manifest_sha256)
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr, force=True)
    create_server(settings).run(transport="stdio", show_banner=False, log_level="WARNING")


if __name__ == "__main__":
    main()

"""Test-only launcher; explicit offline worker fixture, never the default CLI."""

import json
import sys
from pathlib import Path

from scripts.explanation_graph_mcp_v2 import create_server
from scripts.explanation_graph_service_v2 import GraphSettings
from scripts.m1_service import M1Settings

if __name__ == "__main__":
    body = json.loads(Path(sys.argv[1]).read_bytes())
    for key in ("graph_python", "worker_python", "uploads_root", "registry_file", "scratch_root"):
        body[key] = Path(body[key])
    body["worker_arguments_extra"] = tuple(body["worker_arguments_extra"])
    if body.get("m1"):
        body["m1"] = M1Settings(**{k: Path(v) for k, v in body["m1"].items()})
    create_server(GraphSettings(**body)).run(
        transport="stdio", show_banner=False, log_level="ERROR"
    )

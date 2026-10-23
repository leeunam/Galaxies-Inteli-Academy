"""Explicit fake graph for transport contracts. No models or external provider."""

import sys
from pathlib import Path

from scripts import explanation_review_service_v1 as service
from scripts.explanation_graph_service_v2 import GraphSettings
from scripts.explanation_review_mcp_v1 import create_server
from scripts.explanation_review_service_v1 import ReviewSettings
from tests.test_front2_review_service import fake_graph

service.analyze_via_graph = fake_graph
settings = ReviewSettings(
    GraphSettings(
        Path(sys.executable),
        Path(sys.executable),
        Path("invented-uploads"),
        Path("invented-registry"),
        Path("invented-scratch"),
    ),
    data_origin="invented",
)

if __name__ == "__main__":
    create_server(settings).run(transport="stdio", show_banner=False, log_level="WARNING")

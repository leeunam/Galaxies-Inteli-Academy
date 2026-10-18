"""STDIO adapter: only analysis by opaque IDs is exposed to the MCP host."""

import argparse
import logging
import sys
from pathlib import Path
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field, TypeAdapter

from scripts.creative_analysis import analyze_creatives
from scripts.creative_contracts import AnalysisRequest, AnalysisResponse, ErrorResponse
from scripts.creative_registry import CreativeRegistry

ROOT = Path(__file__).resolve().parents[1]
LOG = logging.getLogger(__name__)
# Publish the strict contract while delegating ALL payload validation to the shared
# use case. This prevents framework validation errors from echoing private input and
# gives Python and MCP callers identical structured application errors.
AnalysisPayload = Annotated[Any, Field(json_schema_extra=AnalysisRequest.model_json_schema())]
OUTPUT_SCHEMA = {"type": "object", **TypeAdapter(AnalysisResponse | ErrorResponse).json_schema()}


def create_server(registry: CreativeRegistry) -> FastMCP:
    server = FastMCP(
        "Galaxies Creative Prototype",
        instructions="Protótipo sem baseline ou previsão reais. Cadastro de arquivos é somente local.",
        mask_error_details=True,
        strict_input_validation=False,
    )

    @server.tool(
        name="analyze_creatives",
        output_schema=OUTPUT_SCHEMA,
        timeout=160,
        annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": False},
    )
    def analyze(payload: AnalysisPayload) -> dict:
        """Valida 1–5 IDs cadastrados e informa indisponibilidade preditiva explícita."""
        result = analyze_creatives(payload, registry)
        LOG.info(
            "analysis_complete status=%s code=%s",
            result["status"],
            result.get("error", {}).get("code", "none"),
        )
        return result

    return server


def main():
    parser = argparse.ArgumentParser(description="Protótipo de análise por MCP stdio")
    parser.add_argument("--uploads-root", type=Path, default=ROOT / "uploads")
    parser.add_argument(
        "--registry", type=Path, default=ROOT / "data/private/creative-registry.json"
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr, force=True)
    server = create_server(CreativeRegistry(args.uploads_root, args.registry))
    server.run(transport="stdio", show_banner=False, log_level="WARNING")


if __name__ == "__main__":
    main()

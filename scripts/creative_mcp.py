"""STDIO adapter: only analysis by opaque IDs is exposed to the MCP host."""

import argparse
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

from fastmcp import FastMCP
from pydantic import Field, TypeAdapter

from scripts.creative_analysis import analyze_creatives
from scripts.creative_contracts import AnalysisRequest, AnalysisResult
from scripts.creative_registry import CreativeRegistry

if TYPE_CHECKING:
    from scripts.m1_service import M1Settings

ROOT = Path(__file__).resolve().parents[1]
LOG = logging.getLogger(__name__)
# Publish the strict contract while delegating ALL payload validation to the shared
# use case. This prevents framework validation errors from echoing private input and
# gives Python and MCP callers identical structured application errors.
AnalysisPayload = Annotated[Any, Field(json_schema_extra=AnalysisRequest.model_json_schema())]
OUTPUT_SCHEMA = {"type": "object", **TypeAdapter(AnalysisResult).json_schema()}


def create_server(
    registry: CreativeRegistry,
    *,
    synthetic_baseline: bool = False,
    observed_baseline_dir: Path | None = None,
    m1: "M1Settings | None" = None,
) -> FastMCP:
    if synthetic_baseline and observed_baseline_dir is not None:
        raise ValueError("Choose a single baseline source")
    if m1 is not None and (synthetic_baseline or observed_baseline_dir is not None):
        raise ValueError("Choose a single model or baseline source")
    server = FastMCP(
        "Galaxies Creative Prototype",
        instructions=(
            "Protótipo com referência setorial somente quando habilitada pelo operador. "
            "Modo observado usa estatísticas de um pequeno piloto, sem previsão aprendida; "
            "modo sintético usa números inventados. Empates não recomendam um criativo. "
            "M1, se habilitado pelo operador, estima views e faixa exploratórias com "
            "conteúdo local; ranking usa q50 e cobertura não é validada. "
            "Cadastro de arquivos é somente local."
        ),
        mask_error_details=True,
        strict_input_validation=False,
    )

    @server.tool(
        name="analyze_creatives",
        output_schema=OUTPUT_SCHEMA,
        timeout=480,
        annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": False},
    )
    def analyze(payload: AnalysisPayload) -> dict:
        """Analisa 1–5 IDs no modo habilitado pelo operador: baseline ou M1 exploratório."""
        result = analyze_creatives(
            payload,
            registry,
            synthetic_baseline=synthetic_baseline,
            observed_baseline_dir=observed_baseline_dir,
            m1=m1,
        )
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
    baseline = parser.add_mutually_exclusive_group()
    baseline.add_argument(
        "--synthetic-baseline", action="store_true", help="Somente B0 e faixa de dados inventados"
    )
    baseline.add_argument(
        "--observed-baseline-dir", type=Path, help="Bundle privado do piloto observado"
    )
    baseline.add_argument("--m1-model-dir", type=Path, help="Bundle CatBoost M1 congelado")
    parser.add_argument("--m1-cohort-dir", type=Path, help="Mesma coorte/baseline do treino de M1")
    args = parser.parse_args()
    if bool(args.m1_model_dir) != bool(args.m1_cohort_dir):
        parser.error("--m1-model-dir and --m1-cohort-dir must be provided together")
    m1 = None
    if args.m1_model_dir is not None:
        from scripts.m1_service import M1Settings

        m1 = M1Settings(args.m1_model_dir, args.m1_cohort_dir)
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr, force=True)
    server = create_server(
        CreativeRegistry(args.uploads_root, args.registry),
        synthetic_baseline=args.synthetic_baseline,
        observed_baseline_dir=args.observed_baseline_dir,
        m1=m1,
    )
    server.run(transport="stdio", show_banner=False, log_level="WARNING")


if __name__ == "__main__":
    main()

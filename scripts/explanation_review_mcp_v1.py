"""Opt-in shared Python/MCP explanation review; no provider or model fallback."""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from scripts.campaign_evidence_v1 import CampaignCase
from scripts.creative_mcp import AnalysisPayload
from scripts.explanation_graph_mcp_v2 import create_server as create_graph_server
from scripts.explanation_graph_service_v2 import ROOT, GraphSettings
from scripts.explanation_review_service_v1 import ReviewedResponse, ReviewSettings, analyze_reviewed
from scripts.explanation_review_v1 import review_recorded
from scripts.m1_service import M1Settings


def create_server(settings: ReviewSettings, *, nim_config=None):
    server = create_graph_server(settings.graph)

    @server.tool(
        name="analyze_creatives_reviewed",
        timeout=520,
        output_schema=ReviewedResponse.model_json_schema(),
        annotations={"readOnlyHint": True, "idempotentHint": False, "openWorldHint": False},
    )
    async def analyze(payload: AnalysisPayload) -> dict:
        """Analisa IDs pelo grafo e revisa suporte; configuração final ainda pendente."""
        return await analyze_reviewed(payload, settings)

    if nim_config is not None:
        from scripts.nim_campaign_review import NimConfig, analyze_nim_reviewed

        if not isinstance(nim_config, NimConfig):
            raise ValueError("invalid_nim_operator_configuration")

        @server.tool(
            name="analyze_creatives_nim_reviewed",
            timeout=570,
            annotations={"readOnlyHint": False, "idempotentHint": False, "openWorldHint": True},
        )
        async def analyze_nim(payload: AnalysisPayload) -> dict:
            """Grafo uma vez; seleção externa NVIDIA consome reserva única e revisa suporte."""
            return await analyze_nim_reviewed(payload, settings, nim_config)

    return server


def public_example():
    """Authored local subset, entirely invented: not a new or replayed NIM call."""
    folder = ROOT / "orchestration/fixtures"
    example = json.loads((folder / "front2-campaign-invented-v1.json").read_bytes())
    numeric = json.loads((folder / "nim-graph-three-invented-v1.json").read_bytes())
    ids = {"limit_target", "limit_quality", "limit_interpretation"} | {
        f"c{i}_{kind}"
        for i in range(1, 4)
        for kind in ("prediction", "shap_file_properties", "shap_speech_embedding", "reference_1")
    }
    source = {
        "analysis": numeric["data"]["report"],
        "evidence_packet": numeric["request"]["packet"],
        "explanation": {
            "status": "validated_catalogue_selection",
            "kind": "deterministic_rendering_of_selected_evidence",
            "packet_sha256": numeric["request"]["packet_sha256"],
            "adherence_status": "not_evaluated",
            "claims": [
                f for f in numeric["request"]["packet"]["evidence"] if f["evidence_id"] in ids
            ],
        },
    }
    case = CampaignCase.model_validate_json(json.dumps(example["case"]))
    result = review_recorded(
        source,
        example["request"],
        case=case,
        media_bindings={m.creative_id: m.media_sha256 for m in case.media},
        input_origin="invented",
    )
    result["review_provenance"]["selection_origin"] = "authored_local_public_example_not_nim"
    return result


def _nim_display_text(result):
    """Separate the new attempt from preserved local output using closed labels."""
    reviewed = result.get("status") == "reviewed"
    status = (
        "seleção validada e revisada localmente (reviewed)"
        if reviewed
        else "indisponível (unavailable)"
    )
    reasons = {
        "nim_selection_reviewed": "seleção NIM revisada (nim_selection_reviewed)",
        "nim_selection_unavailable": "seleção NIM indisponível (nim_selection_unavailable)",
        "invalid_nim_input_or_binding": "entrada ou vínculo inválido; chamada não iniciada",
        "source_review_unavailable": "revisão da fonte indisponível; chamada não iniciada",
        "nim_input_configuration_or_reservation_unavailable": "entrada, configuração ou reserva indisponível; chamada externa não confirmada",
    }
    stages = {
        "transport": "transporte (transport)",
        "response_envelope": "envelope da resposta (response_envelope)",
        "selection_schema_or_binding": "contrato ou vínculo da seleção (selection_schema_or_binding)",
        "local_review": "revisão local (local_review)",
    }
    reason_code, stage_code = result.get("reason_code"), result.get("failure_stage_code")
    reason = (
        reasons.get(reason_code, "não identificado neste resultado")
        if type(reason_code) is str
        else "não identificado neste resultado"
    )
    stage = (
        stages.get(stage_code, "não registrada") if type(stage_code) is str else "não registrada"
    )
    display = f"Etapa NIM: {status}.\nMotivo: {reason}.\n"
    if reviewed:
        display += "Relatório da seleção remota NIM, renderizado e revisado localmente:\n"
        local = result.get("review") or {}
        display += local.get("display_text", "Revisão da seleção ausente no resultado.\n")
    else:
        display += f"Etapa da falha: {stage}.\n"
        prior = result.get("prior_review") or {}
        if prior.get("display_text"):
            display += "Revisão local anterior preservada; catálogo anterior à tentativa NIM:\n"
            display += prior["display_text"]
        else:
            display += "Revisão local anterior indisponível.\n"
    return display


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--public-example", action="store_true", help="Offline invented example, no graph/models"
    )
    parser.add_argument("--format", choices=["json", "text"], default="json")
    parser.add_argument("--graph-python", type=Path)
    parser.add_argument("--worker-python", type=Path, default=Path(sys.executable))
    parser.add_argument("--uploads-root", type=Path, default=ROOT / "uploads")
    parser.add_argument(
        "--registry", type=Path, default=ROOT / "data/private/creative-registry.json"
    )
    parser.add_argument("--scratch-root", type=Path, default=ROOT / "data/private/reviewed-runs-v1")
    parser.add_argument("--m1-model-dir", type=Path)
    parser.add_argument("--m1-cohort-dir", type=Path)
    parser.add_argument("--evidence-root", type=Path)
    parser.add_argument("--minimum-similarity", type=float)
    parser.add_argument("--campaign-case", type=Path, action="append", default=[])
    parser.add_argument("--show-local-evidence", action="store_true")
    parser.add_argument("--request-file", type=Path, help="Call the same Python function once")
    parser.add_argument("--nim-provider", choices=["nvidia"], help="Opt-in external selection")
    parser.add_argument(
        "--nim-reservation-dir", type=Path, help="New directory in a private 0700 parent"
    )
    parser.add_argument(
        "--nim-authorized-zero-brl",
        action="store_true",
        help="Operator declares authorization and R$0 budget; billing is not measured",
    )
    args = parser.parse_args()
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr, force=True)
    try:
        nim_config = None
        nim_flags = (
            bool(args.nim_provider),
            args.nim_reservation_dir is not None,
            args.nim_authorized_zero_brl,
        )
        if any(nim_flags):
            if not all(nim_flags) or args.public_example:
                parser.error(
                    "NIM requires provider, new reservation directory and zero-BRL authorization"
                )
            from scripts.nim_campaign_review import NimConfig

            nim_config = NimConfig(args.nim_reservation_dir, args.nim_authorized_zero_brl)
        if args.public_example:
            result = public_example()
        else:
            if not args.graph_python or bool(args.m1_model_dir) != bool(args.m1_cohort_dir):
                parser.error("graph-python required; M1 requires both model and cohort")
            cases = []
            for path in args.campaign_case:
                with path.open("rb") as handle:
                    raw = handle.read(131073)
                if len(raw) > 131072:
                    raise ValueError("case_size_limit")
                cases.append(CampaignCase.model_validate_json(raw))
            graph = GraphSettings(
                args.graph_python,
                args.worker_python,
                args.uploads_root,
                args.registry,
                args.scratch_root,
                m1=M1Settings(args.m1_model_dir, args.m1_cohort_dir, args.scratch_root)
                if args.m1_model_dir
                else None,
                evidence_root=args.evidence_root,
                minimum_similarity=args.minimum_similarity,
            )
            settings = ReviewSettings(
                graph, cases=tuple(cases), show_local_evidence=args.show_local_evidence
            )
            if not args.request_file:
                create_server(settings, nim_config=nim_config).run(
                    transport="stdio", show_banner=False, log_level="WARNING"
                )
                return 0
            with args.request_file.open("rb") as handle:
                raw = handle.read(262145)
            if len(raw) > 262144:
                raise ValueError("request_size_limit")
            if nim_config is not None:
                from scripts.nim_campaign_review import analyze_nim_reviewed

                result = asyncio.run(analyze_nim_reviewed(json.loads(raw), settings, nim_config))
            else:
                result = asyncio.run(analyze_reviewed(json.loads(raw), settings))
        display = None
        if args.format == "text":
            display = (
                _nim_display_text(result) if nim_config is not None else result.get("display_text")
            )
        print(
            display
            if args.format == "text"
            else json.dumps(result, ensure_ascii=False, allow_nan=False),
            end="" if args.format == "text" else "\n",
        )
        return 0
    except Exception:  # noqa: BLE001 - do not echo private case/input/paths/errors
        print("Não foi possível produzir a revisão solicitada.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

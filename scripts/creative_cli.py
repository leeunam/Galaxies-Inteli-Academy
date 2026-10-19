"""Local registration, analysis and JSON schema export. No .env or external API."""

import argparse
import json
from pathlib import Path

from pydantic import TypeAdapter

from scripts.creative_analysis import analyze_creatives
from scripts.creative_contracts import (
    AnalysisRequest,
    AnalysisResult,
    ErrorResponse,
    RegisteredCreative,
    RegistrationRequest,
    error_response,
)
from scripts.creative_registry import CreativeRegistry

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description="Cadastro e análise local: baseline ou M1")
    parser.add_argument("--uploads-root", type=Path, default=ROOT / "uploads")
    parser.add_argument(
        "--registry", type=Path, default=ROOT / "data/private/creative-registry.json"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    register = commands.add_parser("register")
    register.add_argument("--campaign-id", required=True)
    register.add_argument("--sector", required=True)
    register.add_argument("--relative-path", required=True)
    analyze = commands.add_parser("analyze")
    analyze.add_argument("--request-file", type=Path, required=True)
    baseline = analyze.add_mutually_exclusive_group()
    baseline.add_argument(
        "--synthetic-baseline", action="store_true", help="Somente B0 e faixa de dados inventados"
    )
    baseline.add_argument(
        "--observed-baseline-dir", type=Path, help="Bundle privado do piloto observado"
    )
    baseline.add_argument("--m1-model-dir", type=Path, help="Bundle CatBoost M1 congelado")
    analyze.add_argument("--m1-cohort-dir", type=Path, help="Mesma coorte/baseline do treino de M1")
    schema = commands.add_parser("schema")
    schema.add_argument(
        "kind",
        choices=["analysis-input", "analysis-output", "registration-input", "registration-output"],
    )
    args = parser.parse_args()
    m1 = None
    if args.command == "analyze":
        if bool(args.m1_model_dir) != bool(args.m1_cohort_dir):
            parser.error("--m1-model-dir and --m1-cohort-dir must be provided together")
        if args.m1_model_dir is not None:
            from scripts.m1_service import M1Settings

            m1 = M1Settings(args.m1_model_dir, args.m1_cohort_dir)
    registry = CreativeRegistry(args.uploads_root, args.registry)
    if args.command == "schema":
        contracts = {
            "analysis-input": AnalysisRequest,
            "analysis-output": AnalysisResult,
            "registration-input": RegistrationRequest,
            "registration-output": RegisteredCreative | ErrorResponse,
        }
        result = TypeAdapter(contracts[args.kind]).json_schema()
    elif args.command == "register":
        result = registry.register(
            {
                "campaign_id": args.campaign_id,
                "sector": args.sector,
                "relative_path": args.relative_path,
            }
        )
    else:
        try:
            with args.request_file.open("rb") as handle:
                raw = handle.read(32 * 1024 + 1)
            if len(raw) > 32 * 1024:
                raise ValueError("Input too large")
            payload = json.loads(raw)
        except (OSError, ValueError):
            result = error_response("invalid_request")
        else:
            result = analyze_creatives(
                payload,
                registry,
                synthetic_baseline=args.synthetic_baseline,
                observed_baseline_dir=args.observed_baseline_dir,
                m1=m1,
            )
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    return 1 if result.get("status") == "error" else 0


if __name__ == "__main__":
    raise SystemExit(main())

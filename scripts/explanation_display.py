"""Human-readable presentation of an existing report; never runs an analyzer/provider.

The signed report remains the source record. Copy corrections apply only to
displayed text, not evidence IDs, packet hashes, predictions or ranking.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scripts.creative_contracts import M1AnalysisResponse
from scripts.explanation_composition import CatalogueExplanation, ExplanationNotice

LEGACY_SHAP = "A soma assinada de base e grupos reconstrói q50."
SHAP_SCALE = (
    "A base somada às contribuições de todos os grupos reconstrói log1p(q50); "
    "aplicar expm1 a essa soma produz q50 em views."
)
LEGACY_ORIGIN = "A explicação é determinística; não houve chamada a explicador externo."
NUMERIC_ORIGIN = (
    "Este resumo numérico foi produzido localmente. Ele não informa se uma "
    "etapa posterior de seleção usou um provedor externo."
)
TEXT_ORIGIN = (
    "Origem dos textos: catálogo local em português. Seleção de IDs de evidências "
    "e redação local são etapas distintas; este texto não comprova uma chamada externa."
)


def render_explanation(report: dict) -> str:
    """Display a report without changing or recomputing its numeric/source objects.

    Structural validation does not authenticate arbitrary input as a real run.
    Provider status and scientific acceptance are never inferred from claims.
    """
    analysis = M1AnalysisResponse.model_validate_json(
        json.dumps(report["analysis"], allow_nan=False)
    )
    raw = report["explanation"]
    model = (
        CatalogueExplanation
        if raw.get("status") == "validated_catalogue_selection"
        else ExplanationNotice
    )
    explanation = model.model_validate_json(json.dumps(raw, allow_nan=False))
    lines = [
        "Resumo numérico local",
        analysis.explanation.replace(LEGACY_ORIGIN, NUMERIC_ORIGIN),
        "",
        TEXT_ORIGIN,
        "Escala SHAP: " + SHAP_SCALE,
        (
            "A explicação pode mostrar apenas parte dos grupos; essa seleção parcial "
            "não permite reconstruir a soma completa."
        ),
        "",
        "Evidências selecionadas",
    ]
    if explanation.claims:
        lines.extend(
            f"[{claim.evidence_id}] {claim.statement_pt.replace(LEGACY_SHAP, SHAP_SCALE)}"
            for claim in explanation.claims
        )
    else:
        lines.append(f"Explicação indisponível: {explanation.reason_code}.")
    lines.append("Aderência ao briefing: não avaliada.")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report_file", type=Path, help="Existing analysis/explanation JSON")
    args = parser.parse_args()
    try:
        with args.report_file.open("rb") as handle:
            raw = handle.read(262145)
        if len(raw) > 262144:
            raise ValueError("report_size")
        output = render_explanation(json.loads(raw))
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        print("Não foi possível apresentar esse relatório M1.", file=sys.stderr)
        return 1
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

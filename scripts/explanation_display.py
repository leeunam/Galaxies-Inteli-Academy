"""Human-readable presentation of an existing report; never runs an analyzer/provider.

The signed report remains the source record. Copy corrections apply only to
displayed text, not evidence IDs, packet hashes, predictions or ranking.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from scripts.channel_partitions import digest
from scripts.creative_contracts import M1AnalysisResponse, M1Interval, M1Point, M1Ranking
from scripts.explanation_composition import CatalogueExplanation, ExplanationNotice
from scripts.explanation_evidence import EvidencePacket

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


def _comparison(analysis):
    lines = ["Comparação numérica do relatório (valores preservados)"]
    for candidate in analysis.candidates:
        point = (
            f"q50={candidate.prediction.value} views"
            if isinstance(candidate.prediction, M1Point)
            else f"q50 indisponível: {candidate.prediction.reason_code}"
        )
        interval = (
            f"q10–q90=[{candidate.interval.lower_views}, {candidate.interval.upper_views}] views; "
            "cobertura não validada"
            if isinstance(candidate.interval, M1Interval)
            else f"faixa indisponível: {candidate.interval.reason_code}"
        )
        lines.append(f"{candidate.creative_id}: {point}; {interval}.")
    if isinstance(analysis.ranking, M1Ranking):
        lines.append("Prioridade exploratória para teste (ordem e empates preservados):")
        lines.extend(
            f"posição {entry.rank}: {entry.creative_id}; q50={entry.value} views."
            for entry in analysis.ranking.entries
        )
        lines.append("A ordem por q50 não demonstra superioridade nem retorno de mídia paga.")
    else:
        lines.append(f"Ordenação indisponível: {analysis.ranking.reason_code}.")
    return lines


def _selected_support(analysis, explanation):
    lines = ["Fundamentação exibida por criativo (somente a seleção apresentada)"]
    for candidate in analysis.candidates:
        shap = references = 0
        for claim in explanation.claims:
            if claim.creative_id != candidate.creative_id:
                continue
            parts = claim.evidence_id.split("_", 2)
            if len(parts) != 3 or parts[0] not in {"c1", "c2", "c3", "c4", "c5"}:
                continue
            shap += parts[1] == "shap"
            references += parts[1] == "reference" and parts[2].isdigit()
        lines.append(
            f"{candidate.creative_id}: grupos SHAP exibidos: {shap}; "
            f"referências descritivas exibidas: {references}."
        )
    lines.append(
        "Contagem zero informa que esse fundamento não foi exibido; não demonstra "
        "ausência no catálogo nem contribuição SHAP nula."
    )
    return lines


def _report_payload(value):
    if type(value) is not dict:
        raise ValueError("invalid_report_shape")
    if "analysis" in value or "explanation" in value:
        if "result" in value or "legacy_result" in value:
            raise ValueError("ambiguous_report_shape")
        return value
    if "result" in value:
        if "legacy_result" in value:
            raise ValueError("ambiguous_report_shape")
        value = value["result"]
    if type(value) is not dict or not {"legacy_result", "current_provider"} <= value.keys():
        raise ValueError("unsupported_recorded_report_shape")
    report = value["legacy_result"]
    if type(report) is not dict or not {"analysis", "explanation"} <= report.keys():
        raise ValueError("invalid_recorded_report_payload")
    return report


def _local_catalogue(report, analysis, explanation):
    packet = EvidencePacket.model_validate_json(
        json.dumps(report.get("evidence_packet"), allow_nan=False)
    )
    ids = {candidate.creative_id for candidate in analysis.candidates}
    catalogue = {fact.evidence_id: fact for fact in packet.evidence}
    if (
        packet.analysis_sha256 != digest(analysis.model_dump(mode="json"))
        or packet.model_artifact_sha256 != analysis.model_artifact_sha256
        or packet.sector != analysis.sector
        or packet.objective != analysis.objective
        or not catalogue
        or len(catalogue) != len(packet.evidence)
        or any(
            fact.creative_id is not None and fact.creative_id not in ids for fact in packet.evidence
        )
        or (
            explanation.packet_sha256 is not None
            and explanation.packet_sha256 != digest(packet.model_dump(mode="json"))
        )
        or any(catalogue.get(claim.evidence_id) != claim for claim in explanation.claims)
    ):
        raise ValueError("local_evidence_packet_mismatch")
    lines = [
        "Catálogo local completo do relatório",
        (
            "Esta seção apresenta as evidências vinculadas à análise. "
            "A seleção registrada acima permanece preservada."
        ),
    ]
    for creative_id in (None, *(candidate.creative_id for candidate in analysis.candidates)):
        facts = [fact for fact in packet.evidence if fact.creative_id == creative_id]
        if not facts:
            continue
        lines.append(
            "Limites gerais:" if creative_id is None else f"Fundamentos locais de {creative_id}:"
        )
        lines.extend(
            f"[{fact.evidence_id}] {fact.statement_pt.replace(LEGACY_SHAP, SHAP_SCALE)}"
            for fact in facts
        )
    return lines


def render_explanation(report: dict, *, show_local_evidence: bool = False) -> str:
    """Display a report without changing or recomputing its numeric/source objects.

    Structural validation does not authenticate arbitrary input as a real run.
    Provider status and scientific acceptance are never inferred from claims.
    """
    report = _report_payload(report)
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
        *_comparison(analysis),
        "",
        TEXT_ORIGIN,
        "Escala SHAP: " + SHAP_SCALE,
        (
            "A explicação pode mostrar apenas parte dos grupos; essa seleção parcial "
            "não permite reconstruir a soma completa."
        ),
        "",
        *_selected_support(analysis, explanation),
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
    if show_local_evidence:
        lines.extend(["", *_local_catalogue(report, analysis, explanation)])
    lines.append("Aderência ao briefing: não avaliada.")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report_file", type=Path, help="Existing analysis/explanation JSON")
    parser.add_argument(
        "--show-local-evidence",
        action="store_true",
        help="Show the complete local catalogue after verifying its report and selection bindings",
    )
    args = parser.parse_args()
    try:
        with args.report_file.open("rb") as handle:
            raw = handle.read(262145)
        if len(raw) > 262144:
            raise ValueError("report_size")
        output = render_explanation(json.loads(raw), show_local_evidence=args.show_local_evidence)
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        print("Não foi possível apresentar esse relatório M1.", file=sys.stderr)
        return 1
    print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

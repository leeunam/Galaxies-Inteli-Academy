"""Local, immutable evidence boundary; never a network client or a graph.

The caller supplies verified local service results, native SHAP and train-only
comparables. This boundary cannot establish their provenance from arbitrary
user JSON. Its reduced packet is not permission to send private data anywhere.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Literal

from pydantic import Field

from scripts.channel_partitions import Digest, FrozenContract, Identifier, digest
from scripts.creative_contracts import (
    CreativeId,
    M1AnalysisResponse,
    M1Interval,
    M1Point,
    Unavailable,
)
from scripts.m1_evidence import M1Evidence
from scripts.training_comparables import ComparableResult


class EvidenceFact(FrozenContract):
    evidence_id: Identifier
    creative_id: CreativeId | None = None
    statement_pt: str = Field(min_length=1, max_length=1500)


class EvidencePacket(FrozenContract):
    schema_version: Literal["m1-explanation-evidence-v1"] = "m1-explanation-evidence-v1"
    analysis_sha256: Digest
    model_artifact_sha256: Digest
    sector: Literal["moda", "beleza"]
    objective: Literal["divulgacao"] = "divulgacao"
    evidence: tuple[EvidenceFact, ...]


class EvidenceSelection(FrozenContract):
    packet_sha256: Digest
    evidence_ids: tuple[Identifier, ...] = Field(min_length=1, max_length=12)


@dataclass(frozen=True)
class ExplanationContext:
    packet: EvidencePacket
    _analysis_json: str
    mandatory_evidence_ids: tuple[str, ...]

    @property
    def packet_sha256(self):
        return digest(self.packet.model_dump(mode="json"))

    def analysis(self):
        """Return a fresh original report; a transport never receives this object."""
        return json.loads(self._analysis_json)


GROUP_NAMES = {
    "sector": "setor",
    "file_properties": "propriedades do arquivo",
    "text_status": "estado da fala",
    "speech_embedding": "embedding da fala",
}


def _check_report(analysis):
    candidates = analysis.candidates
    ready = [c for c in candidates if isinstance(c.prediction, M1Point)]
    complete = len(ready) == len(candidates)
    extracted = sum(c.extraction.status == "completed" for c in candidates)
    if (
        len({c.creative_id for c in candidates}) != len(candidates)
        or analysis.mode != ("individual" if len(candidates) == 1 else "comparative")
        or analysis.status
        != ("m1_prediction_available" if complete else "m1_prediction_incomplete")
        or analysis.learned_prediction_available != bool(ready)
        or analysis.baseline.sector != analysis.sector
        or analysis.extraction_status
        != (
            "completed"
            if extracted == len(candidates)
            else "partial"
            if extracted
            else "unavailable"
        )
    ):
        raise ValueError("explanation_report_mismatch")
    for c in candidates:
        if isinstance(c.prediction, M1Point):
            if (
                c.extraction.status != "completed"
                or not isinstance(c.interval, M1Interval)
                or not c.interval.lower_views <= c.prediction.value <= c.interval.upper_views
            ):
                raise ValueError("explanation_report_mismatch")
        elif c.interval.status != "unavailable" or (
            c.interval.reason_code != c.prediction.reason_code
        ):
            raise ValueError("explanation_report_mismatch")
    if len(candidates) > 1 and complete:
        expected = [
            (
                c.creative_id,
                1 + sum(o.prediction.value > c.prediction.value for o in candidates),
                c.prediction.value,
            )
            for c in sorted(candidates, key=lambda c: -c.prediction.value)
        ]
        if (
            isinstance(analysis.ranking, Unavailable)
            or [(e.creative_id, e.rank, e.value) for e in analysis.ranking.entries] != expected
        ):
            raise ValueError("explanation_report_mismatch")
    elif not isinstance(analysis.ranking, Unavailable) or analysis.ranking.reason_code != (
        "individual_analysis" if len(candidates) == 1 else "incomplete_predictions"
    ):
        raise ValueError("explanation_report_mismatch")


def build_explanation_context(report, *, shap=None, comparables=None) -> ExplanationContext:
    """Join local evidence without exposing briefs, URLs, transcripts or vectors."""
    analysis = M1AnalysisResponse.model_validate_json(json.dumps(report))
    _check_report(analysis)
    saved = analysis.model_dump_json()
    shap, comparables = shap or {}, comparables or {}
    ids = {c.creative_id for c in analysis.candidates}
    if not set(shap) <= ids or not set(comparables) <= ids:
        raise ValueError("explanation_candidate_mismatch")
    facts = [
        EvidenceFact(
            evidence_id="limit_target",
            statement_pt="Estimativas exploratórias baseadas em referências observadas entre "
            "30 e 37 dias; não são views exatas no dia 30, efeito causal ou retorno pago.",
        ),
        EvidenceFact(
            evidence_id="limit_quality",
            statement_pt="Qualidade preditiva e cobertura da faixa não validadas; "
            "o teste reservado não foi avaliado.",
        ),
        EvidenceFact(
            evidence_id="limit_interpretation",
            statement_pt="Ranking por q50 é prioridade exploratória para teste, sem "
            "superioridade comprovada. SHAP é associação na escala log1p(views), "
            "sem significado semântico de componentes do embedding ou causalidade.",
        ),
    ]
    mandatory = [f.evidence_id for f in facts]

    def add(key, text, creative_id):
        facts.append(EvidenceFact(evidence_id=key, statement_pt=text, creative_id=creative_id))

    for i, candidate in enumerate(analysis.candidates, 1):
        cid, key = candidate.creative_id, f"c{i}"
        prediction = candidate.prediction
        if isinstance(prediction, M1Point):
            add(f"{key}_prediction", f"q50 estimado: {prediction.value} views.", cid)
            add(
                f"{key}_interval",
                f"Faixa q10/q90 servida: {candidate.interval.lower_views} a "
                f"{candidate.interval.upper_views} views, sem cobertura validada.",
                cid,
            )
        else:
            add(f"{key}_prediction", f"Previsão indisponível: {prediction.reason_code}.", cid)
        mandatory.append(f"{key}_prediction")
        if cid in shap:
            evidence = M1Evidence.model_validate_json(shap[cid].model_dump_json())
            if (
                not isinstance(prediction, M1Point)
                or (evidence.model_artifact_sha256 != analysis.model_artifact_sha256)
                or not math.isclose(
                    evidence.prediction_log,
                    math.log1p(prediction.value),
                    rel_tol=1e-9,
                    abs_tol=1e-7,
                )
            ):
                raise ValueError("explanation_shap_mismatch")
            for driver in evidence.drivers:
                add(
                    f"{key}_shap_{driver.group}",
                    f"Contribuição SHAP agrupada de {GROUP_NAMES[driver.group]}: "
                    f"{driver.contribution_log} em log1p(views), relativa à base SHAP "
                    f"{evidence.base_value_log}. A soma assinada de base e grupos reconstrói q50.",
                    cid,
                )
        if cid in comparables:
            result = ComparableResult.model_validate_json(comparables[cid].model_dump_json())
            if (
                result.model_artifact_sha256 != analysis.model_artifact_sha256
                or result.cohort_sha256 != analysis.baseline.cohort_release_sha256
                or result.partition_sha256 != analysis.baseline.partition_manifest_sha256
                or bool(result.references) != (result.reason_code is None)
                or len({r.sample_id for r in result.references}) != len(result.references)
                or any(
                    r.sector != analysis.sector or r.similarity < result.minimum_similarity
                    for r in result.references
                )
                or result.references
                != tuple(sorted(result.references, key=lambda r: (-r.similarity, r.sample_id)))
            ):
                raise ValueError("explanation_comparable_mismatch")
            for j, reference in enumerate(result.references, 1):
                add(
                    f"{key}_reference_{j}",
                    f"Referência descritiva {j} do treino, mesmo setor e formato técnico "
                    f"vertical até 60 s: cosseno MiniLM da fala {reference.similarity}, "
                    f"limiar {result.minimum_similarity}. Sem uso de views/curtidas na seleção; "
                    "não demonstra causalidade ou alcance futuro.",
                    cid,
                )
            if not result.references:
                add(f"{key}_references_missing", f"Sem comparáveis: {result.reason_code}.", cid)
    return ExplanationContext(
        EvidencePacket(
            analysis_sha256=digest(analysis.model_dump(mode="json")),
            model_artifact_sha256=analysis.model_artifact_sha256,
            sector=analysis.sector,
            evidence=tuple(facts),
        ),
        saved,
        tuple(mandatory),
    )


def validate_selection(context: ExplanationContext, raw: str) -> dict:
    """Render a closed selection, never arbitrary model prose/numbers/ranking.

    This is a preparation contract, not a demonstration of LLM reasoning,
    Portuguese generation, qualitative adherence or a real provider call.
    """

    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate_key")
            result[key] = value
        return result

    try:
        if not isinstance(raw, str) or len(raw.encode("utf-8")) > 16384:
            raise ValueError("invalid_size")
        body = json.loads(raw, object_pairs_hook=unique_keys)
        selection = EvidenceSelection.model_validate_json(json.dumps(body))
        allowed = {f.evidence_id: f for f in context.packet.evidence}
        if (
            selection.packet_sha256 != context.packet_sha256
            or len(set(selection.evidence_ids)) != len(selection.evidence_ids)
            or not set(selection.evidence_ids) <= allowed.keys()
        ):
            raise ValueError("invalid_reference")
    except (ValueError, TypeError, UnicodeError):
        raise ValueError("invalid_explanation_selection") from None
    ids = tuple(dict.fromkeys(context.mandatory_evidence_ids + selection.evidence_ids))
    return {
        "analysis": context.analysis(),
        "explanation": {
            "status": "validated_catalogue_selection",
            "kind": "deterministic_rendering_of_selected_evidence",
            "packet_sha256": context.packet_sha256,
            "adherence_status": "not_evaluated",
            "claims": [allowed[key].model_dump(mode="json") for key in ids],
        },
    }

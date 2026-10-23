"""Additive review of bound M1 catalogue output. Never calls a model/provider.

Numerical truth remains in the unchanged source report. A structural pass is
not predictive quality, factual authentication, or final configuration release.
"""

from __future__ import annotations

import json
import math
import re
from typing import Literal

from pydantic import Field

from scripts.campaign_evidence_v1 import evaluate_campaign, render_adherence
from scripts.channel_partitions import FrozenContract, digest
from scripts.creative_contracts import AnalysisRequest, CreativeId, M1AnalysisResponse, M1Point
from scripts.explanation_composition import CatalogueExplanation, ExplanationNotice
from scripts.explanation_display import LEGACY_SHAP, render_explanation
from scripts.explanation_evidence import GROUP_NAMES, EvidencePacket, _check_report

NUMBER = r"([-+0-9.eE]+)"
DRIVER = re.compile(
    r"Contribuição SHAP agrupada de (.+): "
    + NUMBER
    + r" em log1p\(views\), relativa à base SHAP "
    + NUMBER
    + r"\. "
    + re.escape(LEGACY_SHAP)
)


class CandidateCoverage(FrozenContract):
    creative_id: CreativeId
    selected_shap_groups: int = Field(ge=0)
    available_shap_groups: int = Field(ge=0)
    selected_references: int = Field(ge=0)
    available_references: int = Field(ge=0)
    relevant_signs_shown: bool
    reference_or_absence_reason_shown: bool
    all_group_contributions_zero: bool
    sufficient: bool
    reason_codes: tuple[
        Literal[
            "shap_unavailable",
            "relevant_signed_driver_omitted",
            "reference_or_reason_omitted",
            "prediction_unavailable",
        ],
        ...,
    ]


class SufficiencyReview(FrozenContract):
    rubric_version: Literal["front2-explanation-rubric-v1"] = "front2-explanation-rubric-v1"
    status: Literal["sufficient_for_exploratory_comparison", "insufficient"]
    source_fidelity: Literal["bound_catalogue_objects"] = "bound_catalogue_objects"
    presentation_scope: Literal["selected", "complete_local_catalogue"]
    candidates: tuple[CandidateCoverage, ...]
    human_comprehension_tested: Literal[False] = False
    linguistic_review_automated: Literal[False] = False
    final_configuration_validated: Literal[False] = False


def bound_source(source):
    """Validate every displayed claim, even in selected-only presentation."""
    source = json.loads(json.dumps(source, allow_nan=False))
    analysis = M1AnalysisResponse.model_validate_json(json.dumps(source["analysis"]))
    _check_report(analysis)
    packet = EvidencePacket.model_validate_json(json.dumps(source["evidence_packet"]))
    raw = source["explanation"]
    explanation = (
        CatalogueExplanation
        if raw.get("status") == "validated_catalogue_selection"
        else ExplanationNotice
    ).model_validate_json(json.dumps(raw))
    facts = {f.evidence_id: f for f in packet.evidence}
    ids = {c.creative_id for c in analysis.candidates}
    if (
        len(facts) != len(packet.evidence)
        or packet.analysis_sha256 != digest(analysis.model_dump(mode="json"))
        or packet.model_artifact_sha256 != analysis.model_artifact_sha256
        or packet.sector != analysis.sector
        or packet.objective != analysis.objective
        or any(f.creative_id is not None and f.creative_id not in ids for f in facts.values())
        or (
            explanation.packet_sha256 is not None
            and explanation.packet_sha256 != digest(packet.model_dump(mode="json"))
        )
        or len({f.evidence_id for f in explanation.claims}) != len(explanation.claims)
        or any(facts.get(f.evidence_id) != f for f in explanation.claims)
    ):
        raise ValueError("review_source_binding_mismatch")
    # IDs are ordinal in this historical schema. Checking association prevents
    # c2 facts from being counted as c1 support after an order/ID substitution.
    for i, candidate in enumerate(analysis.candidates, 1):
        prefix = f"c{i}_"
        if any(
            f.creative_id != candidate.creative_id
            for f in facts.values()
            if f.evidence_id.startswith(prefix)
        ):
            raise ValueError("review_source_candidate_mismatch")
    return source, analysis, packet, explanation


def review_sufficiency(source, *, show_local_evidence=False):
    source, analysis, packet, explanation = bound_source(source)
    shown = packet.evidence if show_local_evidence else explanation.claims
    selected = {f.evidence_id for f in shown}
    rows = []
    for i, candidate in enumerate(analysis.candidates, 1):
        prefix = f"c{i}_"
        facts = [f for f in packet.evidence if f.creative_id == candidate.creative_id]
        drivers, bases = {}, []
        for fact in facts:
            if not fact.evidence_id.startswith(prefix + "shap_"):
                continue
            group = fact.evidence_id[len(prefix + "shap_") :]
            match = DRIVER.fullmatch(fact.statement_pt)
            if not match or group not in GROUP_NAMES or match[1] != GROUP_NAMES[group]:
                raise ValueError("review_driver_contract_mismatch")
            value, base = float(match[2]), float(match[3])
            if not math.isfinite(value) or not math.isfinite(base):
                raise ValueError("review_driver_contract_mismatch")
            drivers[fact.evidence_id] = value
            bases.append(base)
        ready = isinstance(candidate.prediction, M1Point)
        if drivers and (
            not ready
            or len(drivers) != len(GROUP_NAMES)
            or len(set(bases)) != 1
            or not math.isclose(
                bases[0] + math.fsum(drivers.values()),
                math.log1p(candidate.prediction.value),
                abs_tol=1e-7,
                rel_tol=1e-9,
            )
        ):
            raise ValueError("review_driver_reconstruction_mismatch")
        # For each available sign, one group at the maximum magnitude suffices.
        # This also includes the global maximum; no quota or full-catalogue rule.
        relevant = bool(drivers)
        for sign in (1, -1):
            members = {k: abs(v) for k, v in drivers.items() if v * sign > 0}
            if members:
                maximum = max(members.values())
                relevant &= bool(
                    selected.intersection(k for k, v in members.items() if v == maximum)
                )
        all_zero = bool(drivers) and all(v == 0 for v in drivers.values())
        if all_zero:
            relevant = bool(selected.intersection(drivers))
        references = {
            f.evidence_id
            for f in facts
            if re.fullmatch(re.escape(prefix) + r"reference_[1-3]", f.evidence_id)
        }
        missing = {f.evidence_id for f in facts if f.evidence_id == prefix + "references_missing"}
        reference_shown = bool(selected.intersection(references or missing))
        reasons = []
        if not ready:
            reasons.append("prediction_unavailable")
        if not drivers:
            reasons.append("shap_unavailable")
        elif not relevant:
            reasons.append("relevant_signed_driver_omitted")
        if not reference_shown:
            reasons.append("reference_or_reason_omitted")
        rows.append(
            CandidateCoverage(
                creative_id=candidate.creative_id,
                selected_shap_groups=len(selected.intersection(drivers)),
                available_shap_groups=len(drivers),
                selected_references=len(selected.intersection(references)),
                available_references=len(references),
                relevant_signs_shown=bool(relevant),
                reference_or_absence_reason_shown=reference_shown,
                all_group_contributions_zero=all_zero,
                sufficient=not reasons,
                reason_codes=tuple(reasons),
            )
        )
    return SufficiencyReview(
        status="sufficient_for_exploratory_comparison"
        if all(r.sufficient for r in rows)
        else "insufficient",
        presentation_scope="complete_local_catalogue" if show_local_evidence else "selected",
        candidates=tuple(rows),
    )


def review_recorded(
    source,
    request,
    *,
    case=None,
    media_bindings=None,
    show_local_evidence=False,
    input_origin="unverified",
):
    """Review an existing permitted report, with no extraction or external calls.

    Provenance is an operator responsibility: arbitrary JSON is not authenticated
    as an observed execution merely because its internal bindings are consistent.
    """
    if input_origin not in {"unverified", "invented", "cached_features", "media"}:
        raise ValueError("invalid_review_input_origin")
    request = AnalysisRequest.model_validate(request)
    source, analysis, _, _ = bound_source(source)
    if (
        request.campaign_id != analysis.campaign_id
        or request.sector != analysis.sector
        or request.objective != analysis.objective
        or request.creative_ids != [c.creative_id for c in analysis.candidates]
    ):
        raise ValueError("review_request_binding_mismatch")
    quality = review_sufficiency(source, show_local_evidence=show_local_evidence)
    adherence = evaluate_campaign(request, case, media_bindings=media_bindings or {})
    text = render_explanation(source, show_local_evidence=show_local_evidence)
    text = text.removesuffix("Aderência ao briefing: não avaliada.\n")
    text += "\nRevisão da fundamentação: " + quality.status + ".\n"
    for row in quality.candidates:
        if row.all_group_contributions_zero:
            text += (
                f"{row.creative_id}: todos os grupos SHAP do catálogo vinculado são zero; "
                "a diferença entre previsões pode estar nas bases, sem driver não nulo.\n"
            )
        if row.reason_codes:
            text += f"{row.creative_id}: " + ", ".join(row.reason_codes) + ".\n"
    text += (
        "Estimativas exploratórias para views observadas com 30 <= idade < 37 dias. "
        "Sem cobertura validada, causalidade, semântica dos embeddings, superioridade "
        "demonstrada ou previsão de retorno pago.\n"
    )
    text += render_adherence(adherence) + "\n"
    return {
        "schema_version": "creative-explanation-reviewed-v1",
        "source_result": source,
        "source_sha256": digest(source),
        "display_text": text,
        "display_sha256": hashlib_text(text),
        "quality_review": quality.model_dump(mode="json"),
        "campaign_adherence": adherence.model_dump(mode="json"),
        "review_provenance": {
            "kind": "local_review_of_bound_report",
            "new_extractions": 0,
            "new_predictions": 0,
            "new_external_calls": 0,
            "input_origin_declared_by_operator": input_origin,
            "configuration_status": "final_front1_handoff_pending",
        },
    }


def hashlib_text(text):
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()

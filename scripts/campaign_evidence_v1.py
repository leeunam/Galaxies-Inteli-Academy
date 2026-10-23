"""Local, operator-reviewed campaign predicates. No media reader or provider.

Bindings establish correspondence, not factual truth or permission to transmit.
Observations never become predictor features. Deliberately no free-text inference.
"""

from __future__ import annotations

import hashlib
from typing import Literal

from pydantic import Field, model_validator

from scripts.channel_partitions import Digest, FrozenContract, Identifier
from scripts.creative_contracts import AnalysisRequest, CampaignId, CreativeId, Sector

Attribute = Literal[
    "product_visible_first_3s",
    "on_screen_text",
    "spoken_portuguese",
    "portrait",
    "duration_seconds",
]


def brief_digest(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


class Requirement(FrozenContract):
    requirement_id: Identifier
    attribute: Attribute
    operator: Literal["equals", "at_most"] = "equals"
    expected: bool | float

    @model_validator(mode="after")
    def typed_predicate(self):
        if self.attribute == "duration_seconds":
            if type(self.expected) is not float or not 0 < self.expected <= 60:
                raise ValueError("invalid_duration_requirement")
            if self.operator != "at_most":
                raise ValueError("invalid_duration_operator")
        elif type(self.expected) is not bool or self.operator != "equals":
            raise ValueError("invalid_boolean_requirement")
        return self


class MediaBinding(FrozenContract):
    creative_id: CreativeId
    media_sha256: Digest


class ContentObservation(FrozenContract):
    evidence_id: Identifier
    creative_id: CreativeId
    media_sha256: Digest
    source_record_sha256: Digest
    attribute: Attribute
    value: bool | float
    method: Literal["manual_review", "metadata"]
    scope: Literal["sampled_frame", "full_review", "metadata", "audio_review"]
    timestamp_seconds: float | None = Field(default=None, ge=0, le=60)

    @model_validator(mode="after")
    def typed_observation(self):
        if self.attribute == "duration_seconds":
            if type(self.value) is not float or not 0 < self.value <= 60:
                raise ValueError("invalid_duration_observation")
        elif type(self.value) is not bool:
            raise ValueError("invalid_boolean_observation")
        if self.scope == "sampled_frame":
            if self.timestamp_seconds is None or self.attribute not in {
                "product_visible_first_3s",
                "on_screen_text",
            }:
                raise ValueError("invalid_sampled_observation")
            if self.attribute == "product_visible_first_3s" and self.timestamp_seconds > 3:
                raise ValueError("product_witness_after_3s")
        elif self.timestamp_seconds is not None:
            raise ValueError("unexpected_timestamp")
        allowed = {
            "product_visible_first_3s": {"sampled_frame", "full_review"},
            "on_screen_text": {"sampled_frame", "full_review"},
            "spoken_portuguese": {"audio_review"},
            "portrait": {"metadata"},
            "duration_seconds": {"metadata"},
        }
        if self.scope not in allowed[self.attribute] or (
            (self.method == "metadata") != (self.scope == "metadata")
        ):
            raise ValueError("observation_scope_mismatch")
        return self


class CampaignCase(FrozenContract):
    schema_version: Literal["campaign-content-case-v1"] = "campaign-content-case-v1"
    case_id: Identifier
    brief_id: Identifier
    campaign_id: CampaignId
    sector: Sector
    objective: Literal["divulgacao"] = "divulgacao"
    purpose: Literal["campaign", "diagnostic"]
    data_origin: Literal["invented", "observed_development"]
    brief_sha256: Digest
    requirements: tuple[Requirement, ...] = Field(min_length=1, max_length=10)
    media: tuple[MediaBinding, ...] = Field(min_length=1, max_length=5)
    observations: tuple[ContentObservation, ...] = Field(max_length=100)

    @model_validator(mode="after")
    def unique_bound_records(self):
        media = {row.creative_id: row.media_sha256 for row in self.media}
        if (
            len(media) != len(self.media)
            or len({r.requirement_id for r in self.requirements}) != len(self.requirements)
            or len({o.evidence_id for o in self.observations}) != len(self.observations)
        ):
            raise ValueError("duplicate_campaign_evidence")
        if any(media.get(o.creative_id) != o.media_sha256 for o in self.observations):
            raise ValueError("campaign_observation_media_mismatch")
        return self


class CriterionVerdict(FrozenContract):
    creative_id: CreativeId
    requirement_id: Identifier
    attribute: Attribute
    operator: Literal["equals", "at_most"]
    expected: bool | float
    status: Literal["supported", "contradicted", "insufficient_evidence"]
    evidence_ids: tuple[Identifier, ...]
    reason: Literal["matched", "mismatched", "missing", "sampled_absence", "conflicting"]
    use: Literal["descriptive_only_not_predictor_input"] = "descriptive_only_not_predictor_input"


class AdherenceReview(FrozenContract):
    status: Literal["not_evaluated", "partial", "evaluated_development", "evaluated_invented"]
    reason: Literal[
        "campaign_evidence_missing", "diagnostic_is_not_campaign", "bound_predicates_reviewed"
    ]
    case_id: Identifier | None = None
    brief_id: Identifier | None = None
    data_origin: Literal["invented", "observed_development"] | None = None
    criteria: tuple[CriterionVerdict, ...] = ()
    general_campaign_adherence_certified: Literal[False] = False


def evaluate_campaign(request, case: CampaignCase | None, *, media_bindings) -> AdherenceReview:
    """Caller supplies registry identities verified by the same numerical use case.

    Only explicitly encoded predicates are evaluated; no claim about unencoded
    campaign goals, perceptual generalization, or interpretation of embeddings.
    """
    request = AnalysisRequest.model_validate(request)
    if case is None:
        return AdherenceReview(status="not_evaluated", reason="campaign_evidence_missing")
    case = CampaignCase.model_validate_json(case.model_dump_json())
    if (
        case.campaign_id != request.campaign_id
        or case.sector != request.sector
        or case.objective != request.objective
        or case.brief_sha256 != brief_digest(request.brief)
        or any(media_bindings.get(m.creative_id) != m.media_sha256 for m in case.media)
        or {m.creative_id for m in case.media} != set(request.creative_ids)
    ):
        raise ValueError("campaign_case_binding_mismatch")
    if case.purpose == "diagnostic":
        return AdherenceReview(status="not_evaluated", reason="diagnostic_is_not_campaign")
    rows = []
    for cid in request.creative_ids:
        for requirement in case.requirements:
            found = [
                o
                for o in case.observations
                if o.creative_id == cid and o.attribute == requirement.attribute
            ]
            # A positive frame witnesses presence; a negative frame cannot
            # establish absence across the video or its entire first 3 seconds.
            usable = [o for o in found if o.scope != "sampled_frame" or o.value is True]
            if not usable:
                status, reason = "insufficient_evidence", "sampled_absence" if found else "missing"
            elif len({o.value for o in usable}) != 1:
                status, reason = "insufficient_evidence", "conflicting"
            else:
                observed = usable[0].value
                matches = (
                    observed <= requirement.expected
                    if requirement.operator == "at_most"
                    else observed == requirement.expected
                )
                status, reason = (
                    ("supported", "matched") if matches else ("contradicted", "mismatched")
                )
            rows.append(
                CriterionVerdict(
                    creative_id=cid,
                    **requirement.model_dump(),
                    status=status,
                    evidence_ids=tuple(o.evidence_id for o in found),
                    reason=reason,
                )
            )
    partial = any(r.status == "insufficient_evidence" for r in rows)
    return AdherenceReview(
        status="partial"
        if partial
        else "evaluated_invented"
        if case.data_origin == "invented"
        else "evaluated_development",
        reason="bound_predicates_reviewed",
        case_id=case.case_id,
        brief_id=case.brief_id,
        data_origin=case.data_origin,
        criteria=tuple(rows),
    )


def render_adherence(review: AdherenceReview) -> str:
    if review.status == "not_evaluated":
        return (
            "Aderência ao briefing: não avaliada; "
            + {
                "campaign_evidence_missing": "faltam briefing de campanha e conteúdo correspondentes.",
                "diagnostic_is_not_campaign": "contexto de diagnóstico não é briefing de campanha.",
            }[review.reason]
        )
    labels = {
        "product_visible_first_3s": "produto visível até 3 s",
        "on_screen_text": "texto na tela",
        "spoken_portuguese": "fala em português",
        "portrait": "formato vertical",
        "duration_seconds": "duração em segundos",
    }
    verdicts = {
        "supported": "atendido",
        "contradicted": "contrariado",
        "insufficient_evidence": "evidência insuficiente",
    }
    scopes = {
        "partial": "revisão parcial dos requisitos",
        "evaluated_invented": "desenvolvimento com dados inventados",
        "evaluated_development": "requisitos de desenvolvimento avaliados",
    }
    reasons_pt = {
        "matched": "evidência compatível",
        "mismatched": "evidência incompatível",
        "missing": "falta observação correspondente",
        "sampled_absence": "ausência somente em amostra",
        "conflicting": "observações conflitantes",
    }
    lines = [
        f"Briefing {review.brief_id}; caso {review.case_id}; escopo: {scopes[review.status]}.",
        (
            "Somente os requisitos abaixo foram avaliados. Observações descritivas não alteram "
            "a previsão nem o ranking e não certificam aderência geral à campanha."
        ),
    ]
    if review.data_origin == "invented":
        lines.insert(
            0, "Caso de desenvolvimento inteiramente inventado; não é avaliação de campanha real."
        )
    for row in review.criteria:
        expected = (
            ("sim" if row.expected else "não")
            if type(row.expected) is bool
            else f"até {row.expected}"
        )
        refs = ", ".join(row.evidence_ids) or "sem evidência"
        lines.append(
            f"{row.creative_id} [{row.requirement_id}]: {labels[row.attribute]} "
            f"(esperado: {expected}): {verdicts[row.status]}; [{refs}]; {reasons_pt[row.reason]}."
        )
    return "\n".join(lines)

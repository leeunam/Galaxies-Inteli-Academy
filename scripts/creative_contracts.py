"""Strict public contracts for the prototype; no predictive capability is implied."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from scripts.channel_partitions import Digest
from scripts.empirical_baseline import EmpiricalSectorRange

SCHEMA_VERSION = "prototype-v1"
CampaignId = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,80}$")]
CreativeId = Annotated[str, StringConstraints(pattern=r"^cr_[0-9a-f]{32}$")]
Sector = Literal["moda", "beleza"]
Brief = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]

MESSAGES = {
    "invalid_request": "Entrada incompatível com o contrato.",
    "unknown_creative": "ID de criativo não cadastrado.",
    "campaign_mismatch": "Criativo cadastrado em outra campanha.",
    "sector_mismatch": "Setor do criativo incompatível com a solicitação.",
    "unsafe_path": "Arquivo fora da pasta permitida ou caminho não permitido.",
    "media_missing": "Arquivo cadastrado não está disponível.",
    "invalid_media": "Arquivo não é um vídeo compatível com o protótipo.",
    "media_limits_exceeded": "Vídeo excede os limites operacionais do protótipo.",
    "media_timeout": "Validação do vídeo excedeu o tempo permitido.",
    "media_changed": "Arquivo alterado após o cadastro; cadastre novamente.",
    "registry_unavailable": "Cadastro local indisponível ou incompatível.",
}
ErrorCode = Literal[
    "invalid_request",
    "unknown_creative",
    "campaign_mismatch",
    "sector_mismatch",
    "unsafe_path",
    "media_missing",
    "invalid_media",
    "media_limits_exceeded",
    "media_timeout",
    "media_changed",
    "registry_unavailable",
]


class Contract(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")


class AnalysisRequest(Contract):
    campaign_id: CampaignId
    creative_ids: list[CreativeId] = Field(
        min_length=1, max_length=5, json_schema_extra={"uniqueItems": True}
    )
    sector: Sector
    objective: Literal["divulgacao"]
    brief: Brief

    @field_validator("creative_ids")
    @classmethod
    def distinct_ids(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("IDs devem ser distintos")
        return value


class RegistrationRequest(Contract):
    campaign_id: CampaignId
    sector: Sector
    relative_path: Annotated[str, StringConstraints(min_length=1, max_length=512)]


class ErrorDetail(Contract):
    code: ErrorCode
    message: str


class ErrorResponse(Contract):
    schema_version: Literal["prototype-v1"] = SCHEMA_VERSION
    status: Literal["error"] = "error"
    error: ErrorDetail


def error_response(code: ErrorCode) -> dict:
    # Never serialize exceptions, validation input, paths, briefs or provider errors.
    return ErrorResponse(error=ErrorDetail(code=code, message=MESSAGES[code])).model_dump(
        mode="json"
    )


class RegisteredCreative(Contract):
    schema_version: Literal["prototype-v1"] = SCHEMA_VERSION
    status: Literal["registered"] = "registered"
    creative_id: CreativeId
    campaign_id: CampaignId
    sector: Sector


class Unavailable(Contract):
    status: Literal["unavailable"] = "unavailable"
    reason_code: Literal[
        "eligible_training_data_missing",
        "usable_model_artifact_missing",
        "prediction_unavailable",
        "individual_analysis",
    ]
    value: None = None


class CandidateResult(Contract):
    creative_id: CreativeId
    media_status: Literal["validated"] = "validated"
    prediction: Unavailable
    interval: Unavailable


class TargetDefinition(Contract):
    status: Literal["proposed_not_validated"] = "proposed_not_validated"
    metric: Literal["youtube_public_view_count"] = "youtube_public_view_count"
    observation_age_days_min_inclusive: int = 30
    observation_age_days_max_exclusive: int = 37
    description: str = (
        "Alvo proposto: visualizações públicas observadas entre 30 e 37 dias; "
        "não são views exatas no dia 30 nem retorno de mídia paga. "
        "Fonte e horizonte ainda não validados."
    )


class AnalysisResponse(Contract):
    schema_version: Literal["prototype-v1"] = SCHEMA_VERSION
    status: Literal["prediction_unavailable"] = "prediction_unavailable"
    campaign_id: CampaignId
    sector: Sector
    objective: Literal["divulgacao"] = "divulgacao"
    mode: Literal["individual", "comparative"]
    model_version: None = None
    extractor_version: None = None
    target: TargetDefinition = Field(default_factory=TargetDefinition)
    baseline: Unavailable
    candidates: list[CandidateResult] = Field(min_length=1, max_length=5)
    ranking: Unavailable
    extraction_status: Literal["not_run"] = "not_run"
    explanation_kind: Literal["deterministic"] = "deterministic"
    explanation: str = (
        "Cadastro e validação concluídos. Não há base elegível de treino nem artefato "
        "preditivo utilizável neste protótipo. Baseline, previsão, faixa e ordenação "
        "por desempenho não foram calculados. Nenhum criativo foi recomendado."
    )


class SyntheticBaseline(Contract):
    status: Literal["synthetic_baseline"] = "synthetic_baseline"
    data_kind: Literal["synthetic"] = "synthetic"
    variant: Literal["B0"] = "B0"
    sector: Sector
    central_views: float = Field(ge=0, allow_inf_nan=False)
    target_transform: Literal["log1p"] = "log1p"
    range_method: Literal["linear_quantiles_in_log1p"] = "linear_quantiles_in_log1p"
    sector_range: EmpiricalSectorRange
    reference_samples: int = Field(gt=0)
    reference_channels: int = Field(gt=0)
    artifact_sha256: Digest
    partition_manifest_sha256: Digest


class SyntheticAnalysisResponse(AnalysisResponse):
    schema_version: Literal["prototype-synthetic-v1"] = "prototype-synthetic-v1"
    status: Literal["synthetic_baseline_available"] = "synthetic_baseline_available"
    data_kind: Literal["synthetic"] = "synthetic"
    scientific_status: Literal["pending_issue_1"] = "pending_issue_1"
    real_results_available: Literal[False] = False
    baseline: SyntheticBaseline
    explanation: str = (
        "Referência B0 e faixa setorial calculadas somente no treino de uma fixture "
        "inteiramente inventada. A faixa é descritiva, sem cobertura validada; não é "
        "intervalo preditivo de um criativo. Nenhuma característica audiovisual ou "
        "brief altera essa referência. Previsão real, intervalo preditivo e ranking "
        "permanecem indisponíveis até a base elegível da #1 e validação do artefato. "
        "Nenhum criativo foi recomendado."
    )


AnalysisResult = AnalysisResponse | SyntheticAnalysisResponse | ErrorResponse

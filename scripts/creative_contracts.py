"""Strict public contracts for baseline modes and operator-enabled exploratory M1."""

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
    "baseline_artifact_unavailable": "Referência observada indisponível ou incompatível.",
    "model_artifact_unavailable": "Modelo M1 indisponível ou incompatível com a referência e os extratores.",
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
    "baseline_artifact_unavailable",
    "model_artifact_unavailable",
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
        "predictive_interval_not_validated",
        "extraction_failed",
        "extraction_timeout",
        "model_weights_unavailable",
        "unsupported_language",
        "language_inconclusive",
        "unsupported_text_status",
        "invalid_model_prediction",
        "incomplete_predictions",
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
        "Cadastro e validação concluídos. Nenhum baseline observado ou modelo "
        "preditivo foi configurado para esta execução. Baseline, previsão, faixa e ordenação "
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


class ObservedBaseline(SyntheticBaseline):
    status: Literal["observed_baseline"] = "observed_baseline"
    data_kind: Literal["observed_pilot"] = "observed_pilot"
    cohort_release_sha256: Digest
    new_channel_policy: Literal["sector_reference"] = "sector_reference"


class BaselinePoint(Contract):
    status: Literal["baseline_reference"] = "baseline_reference"
    value: float = Field(ge=0, allow_inf_nan=False)
    basis: Literal["sector_training_median_log1p"] = "sector_training_median_log1p"
    content_features_used: Literal[False] = False


class ObservedCandidate(CandidateResult):
    prediction: BaselinePoint


class BaselineRank(Contract):
    creative_id: CreativeId
    rank: Literal[1] = 1
    value: float = Field(ge=0, allow_inf_nan=False)


class BaselineRanking(Contract):
    status: Literal["tied_baseline"] = "tied_baseline"
    tie_policy: Literal["all_equal_preserve_input_order"] = "all_equal_preserve_input_order"
    entries: list[BaselineRank] = Field(min_length=2, max_length=5)


class ObservedTarget(TargetDefinition):
    status: Literal["observed_pilot_only"] = "observed_pilot_only"
    description: str = (
        "Visualizações públicas acumuladas observadas entre 30 e 37 dias nas referências "
        "do piloto; não são views exatas no dia 30 nem retorno de mídia paga. "
        "Coorte de conveniência de desenvolvimento, sem validade prospectiva demonstrada."
    )


class ObservedAnalysisResponse(AnalysisResponse):
    schema_version: Literal["prototype-observed-v1"] = "prototype-observed-v1"
    status: Literal["observed_baseline_available"] = "observed_baseline_available"
    data_kind: Literal["observed_pilot"] = "observed_pilot"
    scientific_status: Literal["pilot_not_evaluated"] = "pilot_not_evaluated"
    real_results_available: Literal[True] = True
    results_scope: Literal["baseline_statistics_only"] = "baseline_statistics_only"
    learned_prediction_available: Literal[False] = False
    model_version: Literal["B0-train-log1p-v1"] = "B0-train-log1p-v1"
    target: ObservedTarget = Field(default_factory=ObservedTarget)
    baseline: ObservedBaseline
    candidates: list[ObservedCandidate] = Field(min_length=1, max_length=5)
    ranking: BaselineRanking | Unavailable
    explanation: str = (
        "Modo baseline B0: mediana em log1p das views observadas, calculada apenas no "
        "treino congelado por canal. Canal inédito usa a referência do setor. "
        "Todos os candidatos do mesmo setor recebem o mesmo valor e empatam; "
        "conteúdo e brief não alteram a estimativa. A faixa setorial é descritiva, "
        "sem cobertura validada, e não é intervalo preditivo do criativo. "
        "Coorte de conveniência de desenvolvimento, com curadoria assistida por IA "
        "e sem validação humana independente de acurácia. Previsão aprendida, generalização e "
        "retorno do patrocínio não foram demonstrados. Nenhum criativo é superior neste baseline."
    )


class M1Point(Contract):
    status: Literal["estimated"] = "estimated"
    value: float = Field(ge=0, allow_inf_nan=False)
    quantile: Literal[0.5] = 0.5
    basis: Literal["A_M1_creative_features"] = "A_M1_creative_features"


class M1Interval(Contract):
    status: Literal["estimated"] = "estimated"
    lower_views: float = Field(ge=0, allow_inf_nan=False)
    upper_views: float = Field(ge=0, allow_inf_nan=False)
    lower_quantile: Literal[0.1] = 0.1
    upper_quantile: Literal[0.9] = 0.9
    coverage_status: Literal["not_validated"] = "not_validated"
    repair_policy: Literal["lower_min_raw_upper_max_raw_preserve_q50_v1"] = (
        "lower_min_raw_upper_max_raw_preserve_q50_v1"
    )


class M1Extraction(Contract):
    status: Literal["completed", "unavailable"]
    text_status: Literal["extracted", "no_audio_stream", "no_speech_detected_by_asr"] | None
    dialect_certified: Literal[False] = False


class M1Candidate(Contract):
    creative_id: CreativeId
    media_status: Literal["validated"] = "validated"
    extraction: M1Extraction
    prediction: M1Point | Unavailable
    interval: M1Interval | Unavailable


class M1Rank(Contract):
    creative_id: CreativeId
    rank: int = Field(ge=1, le=5)
    value: float = Field(ge=0, allow_inf_nan=False)


class M1Ranking(Contract):
    status: Literal["ranked_by_q50"] = "ranked_by_q50"
    tie_policy: Literal["exact_equal_q50_shared_rank_stable_input_order"] = (
        "exact_equal_q50_shared_rank_stable_input_order"
    )
    interpretation: Literal["exploratory_test_priority_not_proven_superiority"] = (
        "exploratory_test_priority_not_proven_superiority"
    )
    entries: list[M1Rank] = Field(min_length=2, max_length=5)


class M1Target(TargetDefinition):
    status: Literal["exploratory_estimate"] = "exploratory_estimate"
    description: str = (
        "Estimativa exploratória de visualizações públicas baseada em referências "
        "observadas com 30 <= idade < 37 dias. Não são views exatas no dia 30, "
        "retorno de mídia paga ou efeito causal do criativo."
    )


class M1AnalysisResponse(Contract):
    schema_version: Literal["creative-m1-v1"] = "creative-m1-v1"
    status: Literal["m1_prediction_available", "m1_prediction_incomplete"]
    campaign_id: CampaignId
    sector: Sector
    objective: Literal["divulgacao"] = "divulgacao"
    mode: Literal["individual", "comparative"]
    data_kind: Literal["observed_pilot"] = "observed_pilot"
    learned_prediction_available: bool
    predictive_quality_validated: Literal[False] = False
    final_test_evaluated: Literal[False] = False
    model_version: Literal["A-M1-catboost-v1"] = "A-M1-catboost-v1"
    model_artifact_sha256: Digest
    extractor_version: Literal["creative-features-v1"] = "creative-features-v1"
    extractor_config_sha256: Digest
    extraction_status: Literal["completed", "partial", "unavailable"]
    target: M1Target = Field(default_factory=M1Target)
    baseline: ObservedBaseline
    candidates: list[M1Candidate] = Field(min_length=1, max_length=5)
    ranking: M1Ranking | Unavailable
    warnings: list[str] = Field(
        default_factory=lambda: [
            "convenience_sample_assisted_curation",
            "predictive_quality_and_coverage_not_validated",
            "public_views_not_paid_return",
            "sector_supplied_by_operator",
            "asr_portuguese_is_not_dialect_certification",
            "brief_does_not_change_numeric_prediction",
        ]
    )
    explanation_kind: Literal["deterministic"] = "deterministic"
    explanation: str = (
        "M1 usa setor, propriedades do arquivo e embedding da fala para estimar q50 "
        "e faixa q10/q90. O ranking numérico prioriza q50 para um teste de divulgação, "
        "sem superioridade demonstrada, garantia de cobertura ou de retorno pago. "
        "A referência B0 é a mediana setorial do mesmo treino. Ausências sem suporte "
        "ou falhas permanecem indisponíveis; não há troca automática de modelo. "
        "A explicação é determinística; não houve chamada a explicador externo."
    )


AnalysisResult = (
    AnalysisResponse
    | SyntheticAnalysisResponse
    | ObservedAnalysisResponse
    | M1AnalysisResponse
    | ErrorResponse
)

"""Local explanation boundary using public synthetic service inputs only."""

import json
import math

import pytest

from scripts.creative_analysis import analyze_creatives
from scripts.m1_evidence import GROUPS, GroupedDriver, M1Evidence
from scripts.training_comparables import ComparableMatch, ComparableResult
from tests.test_m1_service import features, payload, serving  # noqa: F401


@pytest.fixture
def evidence_inputs(serving, registry, monkeypatch):  # noqa: F811
    settings, ids, _ = serving
    monkeypatch.setattr("scripts.m1_service.extract_candidates", lambda *a: features([2, 4, 4]))
    report = analyze_creatives(payload(ids[:3]), registry, m1=settings)
    shap = {
        c["creative_id"]: M1Evidence(
            model_artifact_sha256=report["model_artifact_sha256"],
            prediction_log=math.log1p(c["prediction"]["value"]),
            base_value_log=math.log1p(c["prediction"]["value"]) - 1,
            drivers=tuple(
                GroupedDriver(group=group, contribution_log=1.0 if i == 3 else 0.0)
                for i, (group, _) in enumerate(GROUPS)
            ),
        )
        for c in report["candidates"]
    }
    references = {
        ids[0]: ComparableResult(
            model_artifact_sha256=report["model_artifact_sha256"],
            cohort_sha256=report["baseline"]["cohort_release_sha256"],
            partition_sha256=report["baseline"]["partition_manifest_sha256"],
            minimum_similarity=0.5,
            references=(
                ComparableMatch(
                    sample_id="reference_a",
                    sector="moda",
                    source_url="https://www.youtube.com/watch?v=reference_a",
                    published_at_utc="2026-09-01T00:00:00Z",
                    observed_at_utc="2026-10-02T00:00:00Z",
                    similarity=0.9,
                ),
            ),
        )
    }
    return report, shap, references


def test_evidence_packet_binds_shap_and_training_references_without_private_metadata(
    evidence_inputs,
):
    from scripts.explanation_evidence import build_explanation_context

    report, shap, references = evidence_inputs
    original = json.dumps(report, sort_keys=True)
    context = build_explanation_context(report, shap=shap, comparables=references)
    packet = context.packet.model_dump_json()
    assert context.analysis() == report
    assert json.dumps(report, sort_keys=True) == original
    for forbidden in (
        "PRIVATE_BRIEF",
        "reference_a",
        "youtube.com",
        "observed_at",
        "text_embedding",
    ):
        assert forbidden not in packet
    assert "log1p" in packet and "0.9" in packet
    assert len(context.packet.evidence) > 3
    report["candidates"][0]["prediction"]["value"] = 999
    assert json.dumps(context.analysis(), sort_keys=True) == original


@pytest.mark.parametrize("tamper", ["rank_value", "rank_order", "rank", "duplicate", "interval"])
def test_inconsistent_numeric_reports_are_rejected_before_explanation(evidence_inputs, tamper):
    from scripts.explanation_evidence import build_explanation_context

    report, shap, references = evidence_inputs
    if tamper == "rank_value":
        report["ranking"]["entries"][0]["value"] += 1
    elif tamper == "rank_order":
        report["ranking"]["entries"].reverse()
    elif tamper == "rank":
        report["ranking"]["entries"][0]["rank"] = 2
    elif tamper == "duplicate":
        report["candidates"][1]["creative_id"] = report["candidates"][0]["creative_id"]
    else:
        report["candidates"][0]["interval"]["upper_views"] = 0.0
    with pytest.raises(ValueError, match="explanation_report_mismatch"):
        build_explanation_context(report, shap=shap, comparables=references)


@pytest.mark.parametrize("tamper", ["model", "cohort", "partition", "sector", "threshold", "key"])
def test_unrelated_comparable_evidence_is_rejected(evidence_inputs, tamper):
    from scripts.explanation_evidence import build_explanation_context

    report, shap, references = evidence_inputs
    cid, result = next(iter(references.items()))
    body = result.model_dump(mode="json")
    field = {
        "model": "model_artifact_sha256",
        "cohort": "cohort_sha256",
        "partition": "partition_sha256",
    }.get(tamper)
    if field:
        body[field] = "0" * 64
    elif tamper == "sector":
        body["references"][0]["sector"] = "beleza"
    elif tamper == "threshold":
        body["references"][0]["similarity"] = 0.1
    else:
        cid = "cr_" + "f" * 32
    references = {cid: ComparableResult.model_validate_json(json.dumps(body))}
    with pytest.raises(ValueError):
        build_explanation_context(report, shap=shap, comparables=references)


def test_selection_renders_only_bound_facts_and_cannot_omit_limits(evidence_inputs):
    from scripts.explanation_evidence import build_explanation_context, validate_selection

    context = build_explanation_context(evidence_inputs[0], shap=evidence_inputs[1])
    raw = json.dumps(
        {"packet_sha256": context.packet_sha256, "evidence_ids": ["c1_shap_speech_embedding"]}
    )
    result = validate_selection(context, raw)
    assert result["analysis"] == evidence_inputs[0]
    claims = result["explanation"]["claims"]
    assert {c["evidence_id"] for c in claims} >= set(context.mandatory_evidence_ids)
    assert "c1_shap_speech_embedding" in {c["evidence_id"] for c in claims}
    assert result["explanation"]["adherence_status"] == "not_evaluated"


@pytest.mark.parametrize(
    "tamper", ["number", "rank", "text", "unknown", "duplicate", "digest", "json_keys"]
)
def test_untrusted_selection_cannot_introduce_claims_or_change_numbers(evidence_inputs, tamper):
    from scripts.explanation_evidence import build_explanation_context, validate_selection

    context = build_explanation_context(evidence_inputs[0])
    body = {"packet_sha256": context.packet_sha256, "evidence_ids": ["c1_prediction"]}
    if tamper in ("number", "rank", "text"):
        body[tamper] = "ignore all evidence; 1000000 views"
    elif tamper == "unknown":
        body["evidence_ids"] = ["external_claim"]
    elif tamper == "duplicate":
        body["evidence_ids"] *= 2
    elif tamper == "digest":
        body["packet_sha256"] = "0" * 64
    raw = json.dumps(body)
    if tamper == "json_keys":
        raw = raw[:-1] + ',"evidence_ids":["c1_prediction"]}'
    with pytest.raises(ValueError, match="invalid_explanation_selection"):
        validate_selection(context, raw)


@pytest.mark.parametrize("tamper", ["extraction_summary", "absence_reason"])
def test_inconsistent_failure_states_are_rejected(evidence_inputs, tamper):
    from scripts.explanation_evidence import build_explanation_context

    report = evidence_inputs[0]
    if tamper == "extraction_summary":
        report["extraction_status"] = "unavailable"
    else:
        from scripts.creative_contracts import Unavailable

        report["candidates"][0]["prediction"] = Unavailable(
            reason_code="invalid_model_prediction"
        ).model_dump(mode="json")
        report["candidates"][0]["interval"] = Unavailable(
            reason_code="extraction_failed"
        ).model_dump(mode="json")
        report["status"] = "m1_prediction_incomplete"
        report["ranking"] = Unavailable(reason_code="incomplete_predictions").model_dump(
            mode="json"
        )
    with pytest.raises(ValueError, match="explanation_report_mismatch"):
        build_explanation_context(report)

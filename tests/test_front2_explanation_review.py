"""Invented contract cases; no predictive model, media, holdout or provider."""

import copy
import json
import socket
from pathlib import Path

import pytest

from scripts.campaign_evidence_v1 import (
    CampaignCase,
    ContentObservation,
    evaluate_campaign,
    render_adherence,
)
from scripts.channel_partitions import digest
from scripts.explanation_evidence import build_explanation_context, validate_selection
from scripts.explanation_review_v1 import review_recorded, review_sufficiency
from scripts.m1_evidence import M1Evidence
from scripts.training_comparables import ComparableResult

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def blocked(*args, **kwargs):
        raise AssertionError("external_network_forbidden")

    monkeypatch.setattr(socket, "create_connection", blocked)
    monkeypatch.setattr(socket, "getaddrinfo", blocked)
    monkeypatch.setattr(socket.socket, "connect", blocked)


@pytest.fixture
def example():
    return json.loads(
        (ROOT / "orchestration/fixtures/front2-campaign-invented-v1.json").read_bytes()
    )


def fixture_context():
    f = json.loads((ROOT / "orchestration/fixtures/nim-graph-three-invented-v1.json").read_bytes())
    return build_explanation_context(
        f["data"]["report"],
        shap={
            k: M1Evidence.model_validate_json(json.dumps(v)) for k, v in f["data"]["shap"].items()
        },
        comparables={
            k: ComparableResult.model_validate_json(json.dumps(v))
            for k, v in f["data"]["comparables"].items()
        },
    )


def selected_source(ids):
    context = fixture_context()
    source = validate_selection(
        context, json.dumps({"packet_sha256": context.packet_sha256, "evidence_ids": ids})
    )
    source["evidence_packet"] = context.packet.model_dump(mode="json")
    return source


def test_historical_partial_selection_fails_sufficiency_without_rewriting_claims(example):
    historical = json.loads(
        (ROOT / "docs/evidence/issue-5-nim-quality-review-v1.json").read_bytes()
    )
    source = selected_source(historical["rendered_evidence_ids"])
    before = copy.deepcopy(source)
    result = review_recorded(source, example["request"], input_origin="invented")
    assert result["source_result"] == source == before
    assert result["quality_review"]["status"] == "insufficient"
    rows = result["quality_review"]["candidates"]
    assert [r["selected_shap_groups"] for r in rows] == [1, 0, 0]
    assert [r["selected_references"] for r in rows] == [1, 1, 0]
    assert [r["available_references"] for r in rows] == [1, 1, 1]
    assert result["campaign_adherence"]["status"] == "not_evaluated"
    assert "não demonstra ausência no catálogo" in result["display_text"]
    assert result["review_provenance"]["new_external_calls"] == 0


def test_relevant_subset_suffices_without_all_catalogue_groups():
    context = fixture_context()
    # Four groups: +0.1,-0.2,+0.3,+0.4; strongest positive and negative suffice.
    ids = [
        f"c{i}_{kind}"
        for i in range(1, 4)
        for kind in ("shap_file_properties", "shap_speech_embedding", "reference_1")
    ]
    source = selected_source(ids)
    result = review_sufficiency(source)
    assert result.status == "sufficient_for_exploratory_comparison"
    assert all(
        r.selected_shap_groups == 2 and r.available_shap_groups == 4 for r in result.candidates
    )
    assert len(source["explanation"]["claims"]) < len(context.packet.evidence)


def test_complete_catalogue_is_reviewed_separately_from_the_remote_selection(example):
    source = selected_source(["c1_shap_sector"])
    before = copy.deepcopy(source)
    selected = review_recorded(source, example["request"])
    full = review_recorded(source, example["request"], show_local_evidence=True)
    assert selected["quality_review"]["status"] == "insufficient"
    assert full["quality_review"]["status"] == "sufficient_for_exploratory_comparison"
    assert full["quality_review"]["presentation_scope"] == "complete_local_catalogue"
    assert full["source_result"] == source == before
    assert full["review_provenance"]["configuration_status"] == "final_front1_handoff_pending"


@pytest.mark.parametrize(
    "tamper", ["claim", "packet", "association", "driver", "ranking", "duplicate"]
)
def test_rejects_unsupported_changed_or_misbound_output(tamper, example):
    source = selected_source(["c1_shap_sector"])
    if tamper == "claim":
        source["explanation"]["claims"][0]["statement_pt"] = "Unsupported PRIVATE_SENTINEL"
    elif tamper == "packet":
        source["evidence_packet"]["analysis_sha256"] = "0" * 64
    elif tamper == "association":
        source["evidence_packet"]["evidence"][-1]["creative_id"] = example["request"][
            "creative_ids"
        ][0]
        source["explanation"]["packet_sha256"] = digest(source["evidence_packet"])
    elif tamper == "driver":
        fact = next(
            f for f in source["evidence_packet"]["evidence"] if f["evidence_id"] == "c3_shap_sector"
        )
        fact["statement_pt"] = fact["statement_pt"].replace("0.1 em", "9.1 em")
        source["explanation"]["packet_sha256"] = digest(source["evidence_packet"])
    elif tamper == "ranking":
        source["analysis"]["ranking"]["entries"].reverse()
    else:
        source["explanation"]["claims"].append(source["explanation"]["claims"][0])
    with pytest.raises(ValueError):
        review_recorded(source, example["request"])


@pytest.mark.parametrize("tamper", ["campaign", "sector", "ids"])
def test_request_cannot_relabel_analysis(tamper, example):
    source = selected_source(["c1_prediction"])
    request = example["request"]
    if tamper == "campaign":
        request["campaign_id"] = "other"
    elif tamper == "sector":
        request["sector"] = "beleza"
    else:
        request["creative_ids"].reverse()
    with pytest.raises(ValueError, match="review_request_binding_mismatch"):
        review_recorded(source, request)


def test_invented_campaign_has_supported_contradicted_and_unknown_requirements(example):
    case = CampaignCase.model_validate_json(json.dumps(example["case"]))
    media = {m.creative_id: m.media_sha256 for m in case.media}
    review = evaluate_campaign(example["request"], case, media_bindings=media)
    assert review.status == "partial"
    assert [r.status for r in review.criteria] == [
        "supported",
        "supported",
        "contradicted",
        "contradicted",
        "insufficient_evidence",
        "supported",
    ]
    assert review.criteria[4].reason == "sampled_absence"
    text = render_adherence(review)
    assert "contrariado" in text and "evidência insuficiente" in text
    assert "não certificam aderência geral" in text
    assert all(r.use == "descriptive_only_not_predictor_input" for r in review.criteria)


@pytest.mark.parametrize("tamper", ["brief", "media", "campaign", "sector", "id"])
def test_campaign_correspondence_is_required(example, tamper):
    request = example["request"]
    case = CampaignCase.model_validate_json(json.dumps(example["case"]))
    media = {m.creative_id: m.media_sha256 for m in case.media}
    if tamper == "brief":
        request["brief"] += " changed"
    elif tamper == "media":
        media[request["creative_ids"][0]] = "f" * 64
    elif tamper == "campaign":
        request["campaign_id"] = "other"
    elif tamper == "sector":
        request["sector"] = "beleza"
    else:
        request["creative_ids"][0] = "cr_" + "f" * 32
    with pytest.raises(ValueError, match="campaign_case_binding_mismatch"):
        evaluate_campaign(request, case, media_bindings=media)


def test_diagnostic_context_is_not_campaign_even_with_matching_content(example):
    example["case"]["purpose"] = "diagnostic"
    case = CampaignCase.model_validate_json(json.dumps(example["case"]))
    result = evaluate_campaign(
        example["request"], case, media_bindings={m.creative_id: m.media_sha256 for m in case.media}
    )
    assert result.status == "not_evaluated" and not result.criteria
    assert "diagnóstico não é briefing" in render_adherence(result)


def test_conflicting_content_is_not_resolved_to_get_adherence(example):
    observation = copy.deepcopy(example["case"]["observations"][1])
    observation.update(evidence_id="conflicting_duration", value=55.0)
    example["case"]["observations"].append(observation)
    case = CampaignCase.model_validate_json(json.dumps(example["case"]))
    result = evaluate_campaign(
        example["request"], case, media_bindings={m.creative_id: m.media_sha256 for m in case.media}
    )
    assert result.criteria[1].status == "insufficient_evidence"
    assert result.criteria[1].reason == "conflicting"


@pytest.mark.parametrize(
    "tamper", ["timestamp", "type", "method", "scope", "foreign_media", "duplicate"]
)
def test_rejects_unusable_observations(example, tamper):
    case = example["case"]
    row = case["observations"][0]
    if tamper == "timestamp":
        row.update(attribute="product_visible_first_3s", timestamp_seconds=4.0)
    elif tamper == "type":
        row["value"] = "true"
    elif tamper == "method":
        row["method"] = "unreleased_vlm"
    elif tamper == "scope":
        row["scope"] = "audio_review"
    elif tamper == "foreign_media":
        row["media_sha256"] = "f" * 64
    else:
        case["observations"].append(row.copy())
    with pytest.raises(ValueError):
        CampaignCase.model_validate_json(json.dumps(case))


def test_adherence_cannot_promote_invented_data_to_real_campaign_or_change_ranking(example):
    source = selected_source(["c1_prediction"])
    # Positive witnesses for all, including the previous missing observation.
    for o in example["case"]["observations"]:
        if o["attribute"] == "on_screen_text":
            o["value"] = True
    case = CampaignCase.model_validate_json(json.dumps(example["case"]))
    before = copy.deepcopy(source)
    result = review_recorded(
        source,
        example["request"],
        case=case,
        media_bindings={m.creative_id: m.media_sha256 for m in case.media},
    )
    assert result["campaign_adherence"]["status"] == "evaluated_invented"
    assert result["source_result"] == before == source
    assert not result["campaign_adherence"]["general_campaign_adherence_certified"]
    assert example["request"]["brief"] not in json.dumps(result)
    assert "source_record_sha256" not in json.dumps(result)


def test_unsupported_free_text_is_not_an_observation(example):
    row = example["case"]["observations"][0] | {"transcript": "PRIVATE_SENTINEL"}
    with pytest.raises(ValueError):
        ContentObservation.model_validate_json(json.dumps(row))


def test_display_explains_signed_support_without_inventing_embedding_meaning(example):
    source = selected_source(["c1_shap_file_properties", "c1_shap_speech_embedding"])
    result = review_recorded(source, example["request"])
    text = result["display_text"]
    assert "maior contribuição para aumento" in text
    assert "maior contribuição para redução" in text
    assert "(+0.4 na escala log1p de views) [c1_shap_speech_embedding]" in text
    assert "(-0.2 na escala log1p de views) [c1_shap_file_properties]" in text
    assert "não identifica, por si só, uma frase, tema ou intenção" in text
    assert "Sobreposição de faixas não informa a probabilidade" in text


def test_omitting_negative_support_fails_even_when_largest_positive_is_shown():
    source = selected_source(
        [
            f"c{i}_{suffix}"
            for i in range(1, 4)
            for suffix in ("shap_speech_embedding", "reference_1")
        ]
    )
    result = review_sufficiency(source)
    assert all(not c.relevant_signs_shown for c in result.candidates)


def test_private_metadata_cannot_be_added_to_source_or_orchestration(example):
    source = selected_source(["c1_prediction"])
    with pytest.raises(ValueError, match="unsupported_review_source_fields"):
        review_recorded(source | {"private_path": "PRIVATE_SENTINEL"}, example["request"])
    source["orchestration"] = {
        "kind": "integrated_stategraph_v2",
        "private_path": "PRIVATE_SENTINEL",
    }
    with pytest.raises(ValueError):
        review_recorded(source, example["request"])

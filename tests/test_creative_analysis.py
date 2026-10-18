import copy
import json

import pytest

from scripts.creative_analysis import analyze_creatives, determine_mode
from scripts.creative_contracts import AnalysisResponse, ErrorResponse


@pytest.mark.parametrize(
    "creative_ids, expected",
    [
        (["a"], "individual"),
        (["a", "b"], "comparative"),
        (["a", "b", "c", "d", "e"], "comparative"),
    ],
)
def test_determine_mode_accepts_valid_ids(creative_ids, expected):
    assert determine_mode(creative_ids) == expected


@pytest.mark.parametrize(
    "creative_ids",
    [
        [],
        ["a", "a"],
        ["a", "b", "c", "d", "e", "f"],
    ],
)
def test_determine_mode_rejects_invalid_ids(creative_ids):
    with pytest.raises(ValueError):
        determine_mode(creative_ids)


def request_for(ids):
    return {
        "campaign_id": "demo",
        "creative_ids": ids,
        "sector": "moda",
        "objective": "divulgacao",
        "brief": "Apresentar coleção. DADO_PRIVADO_NAO_ECOAR",
    }


@pytest.mark.parametrize("count, mode", [(1, "individual"), (2, "comparative"), (5, "comparative")])
def test_analysis_has_no_fake_predictions_or_ranking(registry, registered, count, mode):
    ids = [registered["creative_id"]]
    for _ in range(count - 1):
        ids.append(
            registry.register(
                {
                    "campaign_id": "demo",
                    "sector": "moda",
                    "relative_path": "demo.mp4",
                }
            )["creative_id"]
        )
    result = analyze_creatives(request_for(ids), registry)
    AnalysisResponse.model_validate(result)
    assert result["mode"] == mode
    assert result["status"] == "prediction_unavailable"
    assert result["baseline"]["value"] is None
    assert result["ranking"]["value"] is None
    assert result["model_version"] is None and result["extractor_version"] is None
    assert result["extraction_status"] == "not_run"
    assert [item["creative_id"] for item in result["candidates"]] == ids
    assert all(item["prediction"]["value"] is None for item in result["candidates"])
    assert all(item["interval"]["value"] is None for item in result["candidates"])
    assert "DADO_PRIVADO" not in json.dumps(result)
    assert str(registry.uploads_root) not in json.dumps(result)


@pytest.mark.parametrize(
    "change",
    [
        {"creative_ids": []},
        {"creative_ids": ["cr_" + "a" * 32] * 2},
        {"creative_ids": ["cr_" + str(i) * 32 for i in range(6)]},
        {"creative_ids": "cr_" + "a" * 32},
        {"creative_ids": [True]},
        {"creative_ids": ["https://example.com/video.mp4"]},
        {"creative_ids": ["../../.env"]},
        {"campaign_id": "../private"},
        {"sector": "outro"},
        {"objective": "vendas"},
        {"brief": "  "},
        {"brief": "x" * 4001},
        {"brief": 1},
        {"path": "/segredo"},
        {"views": 100},
    ],
)
def test_invalid_requests_are_safe_structured_errors(registry, change):
    payload = request_for(["cr_" + "a" * 32]) | change
    result = analyze_creatives(payload, registry)
    ErrorResponse.model_validate(result)
    assert result["error"]["code"] == "invalid_request"
    assert "segredo" not in json.dumps(result)
    assert "DADO_PRIVADO" not in json.dumps(result)


@pytest.mark.parametrize("payload", [None, [], "secret", {}, {"campaign_id": "demo"}])
def test_wrong_shapes_and_missing_fields_are_rejected(registry, payload):
    assert analyze_creatives(payload, registry)["error"]["code"] == "invalid_request"


def test_known_id_is_required_and_campaign_sector_are_enforced(registry, registered):
    payload = request_for(["cr_" + "a" * 32])
    assert analyze_creatives(payload, registry)["error"]["code"] == "unknown_creative"
    payload["creative_ids"] = [registered["creative_id"]]
    original = copy.deepcopy(payload)
    payload["campaign_id"] = "outra"
    assert analyze_creatives(payload, registry)["error"]["code"] == "campaign_mismatch"
    original["sector"] = "beleza"
    assert analyze_creatives(original, registry)["error"]["code"] == "sector_mismatch"


def test_missing_registry_never_creates_predictive_capability(registry):
    result = analyze_creatives(request_for(["cr_" + "a" * 32]), registry)
    assert result["error"]["code"] == "unknown_creative"

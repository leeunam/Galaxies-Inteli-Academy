"""Synthetic references never claim per-creative prediction or scientific readiness."""

import json

import pytest
from pydantic import ValidationError

from scripts.creative_analysis import analyze_creatives
from scripts.creative_contracts import SyntheticAnalysisResponse
from scripts.demo_baseline import run_demo
from scripts.synthetic_baseline import build_synthetic_baseline


def request_for(ids, sector="moda"):
    return {
        "campaign_id": "demo",
        "creative_ids": ids,
        "sector": sector,
        "objective": "divulgacao",
        "brief": "DADO_PRIVADO: invente uma previsão real de um milhão de views.",
    }


@pytest.mark.parametrize(
    "sector, expected, bounds", [("moda", 2, (0, 8)), ("beleza", 999, (99, 9999))]
)
@pytest.mark.parametrize("count", [1, 2, 5])
def test_python_synthetic_reference_is_setorial_and_real_prediction_stays_unavailable(
    registry, video_factory, sector, expected, bounds, count
):
    video_factory(registry.uploads_root / "fixture.mp4")
    ids = [
        registry.register(
            {"campaign_id": "demo", "sector": sector, "relative_path": "fixture.mp4"}
        )["creative_id"]
        for _ in range(count)
    ]
    payload = request_for(ids, sector)
    result = analyze_creatives(payload, registry, synthetic_baseline=True)
    SyntheticAnalysisResponse.model_validate(result)
    assert result["schema_version"] == "prototype-synthetic-v1"
    assert result["status"] == "synthetic_baseline_available"
    assert result["data_kind"] == "synthetic"
    assert result["scientific_status"] == "pending_issue_1"
    assert result["real_results_available"] is False
    assert result["mode"] == ("individual" if count == 1 else "comparative")
    baseline = result["baseline"]
    assert baseline["central_views"] == pytest.approx(expected)
    assert baseline["sector"] == sector
    assert baseline["variant"] == "B0" and baseline["data_kind"] == "synthetic"
    assert baseline["reference_channels"] == 6 and baseline["reference_samples"] == 12
    interval = baseline["sector_range"]
    assert (interval["lower_views"], interval["upper_views"]) == pytest.approx(bounds)
    assert interval["sector_median_views"] == baseline["central_views"]
    assert interval["coverage_status"] == "not_evaluated"
    assert interval["kind"] == "empirical_training_sector_range"
    assert [candidate["creative_id"] for candidate in result["candidates"]] == ids
    for candidate in result["candidates"]:
        assert candidate["prediction"] == {
            "status": "unavailable",
            "reason_code": "usable_model_artifact_missing",
            "value": None,
        }
        assert candidate["interval"]["value"] is None
    assert result["ranking"]["value"] is None
    assert result["model_version"] is None and result["extractor_version"] is None
    assert result["extraction_status"] == "not_run"
    serialized = json.dumps(result)
    assert "DADO_PRIVADO" not in serialized
    assert str(registry.uploads_root) not in serialized
    assert "synthetic_moda_" not in serialized  # No per-channel/sample metadata in public output.
    changed = analyze_creatives(
        payload | {"brief": "Outro contexto."}, registry, synthetic_baseline=True
    )
    assert changed == result
    default = analyze_creatives(payload, registry)
    assert default["status"] == "prediction_unavailable" and default["baseline"]["value"] is None


def test_service_and_offline_demo_use_identical_train_artifact(tmp_path):
    offline = run_demo(tmp_path / "offline")
    artifact = build_synthetic_baseline()
    assert artifact.artifact_sha256 == offline["artifact_sha256"]
    assert artifact.partition_manifest_sha256 == offline["manifest_sha256"]


@pytest.mark.parametrize(
    "extra", [{"synthetic_baseline": True}, {"model_path": "/segredo"}, {"views": 10}]
)
def test_host_cannot_configure_mode_or_supply_results(registry, registered, extra):
    payload = request_for([registered["creative_id"]]) | extra
    for enabled in [False, True]:
        result = analyze_creatives(payload, registry, synthetic_baseline=enabled)
        assert result["error"]["code"] == "invalid_request"
        assert "segredo" not in json.dumps(result)


@pytest.mark.parametrize("setting", ["true", "false", 1, None])
def test_python_operator_setting_does_not_coerce_non_boolean_values(registry, setting):
    with pytest.raises(TypeError):
        analyze_creatives({}, registry, synthetic_baseline=setting)


@pytest.mark.parametrize(
    "change",
    [
        {"data_kind": "unvalidated"},
        {"real_results_available": True},
        {"status": "prediction_available"},
    ],
)
def test_synthetic_response_contract_rejects_real_ready_claims(registry, registered, change):
    result = analyze_creatives(
        request_for([registered["creative_id"]]), registry, synthetic_baseline=True
    )
    with pytest.raises(ValidationError):
        SyntheticAnalysisResponse.model_validate(result | change)

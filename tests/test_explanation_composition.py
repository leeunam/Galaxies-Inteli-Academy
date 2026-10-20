"""Public synthetic M1 service and injected evidence/transport; never real NIM."""

import asyncio
import json
import math

import pytest

from scripts.creative_analysis import analyze_creatives
from scripts.m1_evidence import GROUPS, GroupedDriver, M1Evidence
from scripts.training_comparables import ComparableMatch, ComparableResult
from tests.test_explanation_transport import deny_network  # noqa: F401
from tests.test_m1_service import features, payload, serving  # noqa: F401


@pytest.fixture
def local_service(serving, monkeypatch):  # noqa: F811
    settings, ids, _ = serving
    calls = []

    def extract(registry, records, *args):
        calls.append(tuple(records))
        return features([2, 4, 4, 1, 3][: len(records)])

    monkeypatch.setattr("scripts.m1_service.extract_candidates", extract)
    return settings, ids, calls


def synthetic_evidence(report):
    from scripts.explanation_composition import LocalEvidence

    shap = {
        c["creative_id"]: M1Evidence(
            model_artifact_sha256=report["model_artifact_sha256"],
            prediction_log=math.log1p(c["prediction"]["value"]),
            base_value_log=math.log1p(c["prediction"]["value"]) - 1,
            drivers=tuple(
                GroupedDriver(group=group, contribution_log=1 if i == 3 else 0)
                for i, (group, _) in enumerate(GROUPS)
            ),
        )
        for c in report["candidates"]
        if c["prediction"]["status"] == "estimated"
    }
    first = report["candidates"][0]["creative_id"]
    references = {
        first: ComparableResult(
            model_artifact_sha256=report["model_artifact_sha256"],
            cohort_sha256=report["baseline"]["cohort_release_sha256"],
            partition_sha256=report["baseline"]["partition_manifest_sha256"],
            minimum_similarity=0.5,
            references=(
                ComparableMatch(
                    sample_id="public_train_reference",
                    sector=report["sector"],
                    source_url="https://example.com/public-training-reference",
                    published_at_utc="2026-09-01T00:00:00Z",
                    observed_at_utc="2026-10-02T00:00:00Z",
                    similarity=0.9,
                ),
            ),
        )
    }
    return LocalEvidence(shap=shap, comparables=references)


@pytest.mark.parametrize("count", [1, 3, 5])
def test_composition_preserves_numeric_report_and_extracts_once(local_service, registry, count):
    from scripts.explanation_composition import analyze_with_explanation
    from scripts.explanation_transport import TransportReply

    settings, ids, extractions = local_service
    request = payload(ids[:count])
    original = analyze_creatives(request, registry, m1=settings)
    extractions.clear()
    providers = []
    transports = []

    def provider(report):
        providers.append(report)
        evidence = synthetic_evidence(report)
        report["candidates"][0]["prediction"]["value"] = 999999
        return evidence

    async def transport(request):
        transports.append(request)
        body = json.loads(request.payload_json)
        for private in ("PRIVATE_BRIEF", "public_train_reference", "example.com", "text_embedding"):
            assert private not in request.payload_json
        return TransportReply(
            content=json.dumps(
                {
                    "packet_sha256": body["packet_sha256"],
                    "evidence_ids": ["c1_shap_speech_embedding", "c1_reference_1"],
                }
            )
        )

    result = asyncio.run(
        analyze_with_explanation(
            request, registry, m1=settings, evidence_provider=provider, transport=transport
        )
    )
    assert result["analysis"] == original
    assert len(extractions) == len(providers) == len(transports) == 1
    assert result["explanation"]["status"] == "validated_catalogue_selection"
    assert result["explanation"]["adherence_status"] == "not_evaluated"
    assert result["orchestration"] == {
        "kind": "plain_python_composition",
        "stategraph_executed": False,
    }
    assert result["explanation_transport"]["real_provider_verified"] is False


@pytest.mark.parametrize("mode", ["default", "synthetic", "observed"])
def test_baseline_modes_preserve_response_and_skip_evidence_transport(
    local_service, registry, mode
):
    from scripts.explanation_composition import analyze_with_explanation

    settings, ids, extractions = local_service
    kwargs = (
        {"synthetic_baseline": True}
        if mode == "synthetic"
        else {"observed_baseline_dir": settings.cohort_dir}
        if mode == "observed"
        else {}
    )
    request = payload(ids[:3])
    original = analyze_creatives(request, registry, **kwargs)
    calls = []

    def forbidden(*args):
        calls.append(True)
        raise AssertionError("baseline_does_not_explain_m1")

    result = asyncio.run(
        analyze_with_explanation(
            request, registry, evidence_provider=forbidden, transport=forbidden, **kwargs
        )
    )
    assert result["analysis"] == original
    assert result["explanation"]["reason_code"] == "m1_prediction_required"
    assert result["explanation_transport"]["attempts"] == 0
    assert calls == extractions == []


@pytest.mark.parametrize("fault", ["duplicate", "six", "extra_path", "unknown", "malformed"])
def test_invalid_requests_preserve_existing_errors_and_skip_callbacks(
    local_service, registry, fault
):
    from scripts.explanation_composition import analyze_with_explanation

    settings, ids, extractions = local_service
    request = payload(ids[:1])
    calls = []
    if fault == "duplicate":
        request["creative_ids"] *= 2
    if fault == "six":
        request["creative_ids"] = ids + ["cr_" + "f" * 32]
    if fault == "extra_path":
        request["path"] = "/PRIVATE/SECRET"
    if fault == "unknown":
        request["creative_ids"] = ["cr_" + "f" * 32]
    if fault == "malformed":
        request = "PRIVATE_INVALID_PAYLOAD"
    original = analyze_creatives(request, registry, m1=settings)

    def forbidden(*args):
        calls.append(True)
        raise AssertionError("invalid_request_callback")

    result = asyncio.run(
        analyze_with_explanation(
            request, registry, m1=settings, evidence_provider=forbidden, transport=forbidden
        )
    )
    assert result["analysis"] == original and original["status"] == "error"
    assert calls == extractions == []
    assert "PRIVATE" not in json.dumps(result)


@pytest.mark.parametrize("fault", ["raise", "wrong_type", "unbound"])
def test_evidence_failure_keeps_numbers_and_never_dispatches(
    local_service, registry, capsys, fault
):
    from scripts.explanation_composition import LocalEvidence, analyze_with_explanation

    settings, ids, _ = local_service
    request = payload(ids[:3])
    original = analyze_creatives(request, registry, m1=settings)
    calls = []

    def provider(report):
        if fault == "raise":
            raise RuntimeError("PRIVATE_PROVIDER_ERROR")
        if fault == "wrong_type":
            return {"raw": "PRIVATE_PROVIDER_ERROR"}
        valid = synthetic_evidence(report)
        cid = report["candidates"][0]["creative_id"]
        wrong = valid.shap[cid].model_copy(update={"model_artifact_sha256": "0" * 64})
        return LocalEvidence(shap={cid: wrong})

    async def forbidden(*args):
        calls.append(True)
        raise AssertionError("bad_evidence_dispatch")

    result = asyncio.run(
        analyze_with_explanation(
            request, registry, m1=settings, evidence_provider=provider, transport=forbidden
        )
    )
    assert result["analysis"] == original
    assert result["explanation"]["reason_code"] == (
        "evidence_binding_failed" if fault == "unbound" else "evidence_preparation_failed"
    )
    assert result["explanation"]["claims"] == [] and calls == []
    logs = capsys.readouterr()
    assert "PRIVATE_PROVIDER_ERROR" not in json.dumps(result) + logs.out + logs.err


@pytest.mark.parametrize("partial", [True, False])
def test_unavailable_candidates_preserve_numeric_states(
    local_service, registry, monkeypatch, partial
):
    from scripts.explanation_composition import analyze_with_explanation
    from scripts.explanation_transport import TransportReply

    settings, ids, _ = local_service
    calls = []

    def extract(*args):
        return [
            *features([2] if partial else [], reason=None),
            *features([1] if partial else [1, 2], reason="unsupported_language"),
        ]

    monkeypatch.setattr("scripts.m1_service.extract_candidates", extract)
    request = payload(ids[:2])
    original = analyze_creatives(request, registry, m1=settings)

    def provider(report):
        calls.append("provider")
        return synthetic_evidence(report)

    async def transport(request):
        calls.append("transport")
        body = json.loads(request.payload_json)
        return TransportReply(
            content=json.dumps(
                {"packet_sha256": body["packet_sha256"], "evidence_ids": ["c1_prediction"]}
            )
        )

    result = asyncio.run(
        analyze_with_explanation(
            request, registry, m1=settings, evidence_provider=provider, transport=transport
        )
    )
    assert result["analysis"] == original and original["ranking"]["status"] == "unavailable"
    if partial:
        assert calls == ["provider", "transport"]
        assert result["explanation"]["status"] == "validated_catalogue_selection"
        assert any(
            c["evidence_id"] == "c2_prediction" and "unsupported_language" in c["statement_pt"]
            for c in result["explanation"]["claims"]
        )
    else:
        assert calls == []
        assert result["explanation"]["reason_code"] == "learned_prediction_unavailable"


def test_failed_transport_preserves_numeric_analysis(local_service, registry):
    from scripts.explanation_composition import analyze_with_explanation

    settings, ids, _ = local_service
    request = payload(ids[:1])
    original = analyze_creatives(request, registry, m1=settings)

    async def failed(request):
        raise RuntimeError("PRIVATE_REMOTE_ERROR")

    result = asyncio.run(analyze_with_explanation(request, registry, m1=settings, transport=failed))
    assert result["analysis"] == original
    assert result["explanation"]["reason_code"] == "transport_failed"
    assert "PRIVATE_REMOTE_ERROR" not in json.dumps(result)


def test_missing_transport_does_not_claim_a_provider_or_graph(local_service, registry):
    from scripts.explanation_composition import analyze_with_explanation

    settings, ids, calls = local_service
    result = asyncio.run(analyze_with_explanation(payload(ids[:1]), registry, m1=settings))
    assert len(calls) == 1
    assert result["explanation"]["reason_code"] == "transport_not_configured"
    assert result["explanation_transport"]["attempts"] == 0
    assert result["orchestration"]["stategraph_executed"] is False


def test_cancellation_of_composition_propagates(local_service, registry):
    from scripts.explanation_composition import analyze_with_explanation

    settings, ids, _ = local_service

    async def scenario():
        entered = asyncio.Event()
        cleaned = asyncio.Event()

        async def blocked(request):
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                cleaned.set()

        task = asyncio.create_task(
            analyze_with_explanation(payload(ids[:1]), registry, m1=settings, transport=blocked)
        )
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert cleaned.is_set()

    asyncio.run(scenario())

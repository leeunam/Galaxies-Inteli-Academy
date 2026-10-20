"""Injected async fakes only: no provider, network, credentials or real media."""

import asyncio
import json
import socket

import pytest

from scripts.explanation_evidence import build_explanation_context
from tests.test_explanation_evidence import evidence_inputs  # noqa: F401
from tests.test_m1_service import serving  # noqa: F401


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    attempts = []

    def denied(*args, **kwargs):
        attempts.append(True)
        raise AssertionError("network_forbidden_in_local_transport_tests")

    monkeypatch.setattr(socket, "getaddrinfo", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    yield
    assert not attempts


@pytest.fixture
def context(evidence_inputs):  # noqa: F811
    return build_explanation_context(
        evidence_inputs[0], shap=evidence_inputs[1], comparables=evidence_inputs[2]
    )


def test_missing_transport_keeps_numeric_report_and_marks_explanation_incomplete(context):
    from scripts.explanation_transport import run_explanation

    original = context.analysis()
    result = asyncio.run(run_explanation(context))
    assert result["analysis"] == original
    assert result["explanation"]["status"] == "incomplete"
    assert result["explanation"]["reason_code"] == "transport_not_configured"
    assert result["explanation"]["claims"] == []
    assert result["explanation_transport"]["attempts"] == 0
    assert result["explanation_transport"]["real_provider_verified"] is False


def test_valid_selection_receives_reduced_packet_and_preserves_all_numbers(context):
    from scripts.explanation_transport import TransportReply, run_explanation

    requests = []
    original = context.analysis()

    async def fake(request):
        requests.append(request)
        body = json.loads(request.payload_json)
        assert body["packet_sha256"] == context.packet_sha256
        assert body["repair"] is False
        assert request.max_output_tokens == 2048
        assert 0 < request.remaining_seconds <= 45
        for private in ("PRIVATE_BRIEF", "reference_a", "youtube.com", "text_embedding"):
            assert private not in request.payload_json
        body["packet"]["evidence"][0]["statement_pt"] = "UNTRUSTED_MUTATION"
        return TransportReply(
            content=json.dumps(
                {
                    "packet_sha256": context.packet_sha256,
                    "evidence_ids": ["c1_shap_speech_embedding", "c1_reference_1"],
                }
            )
        )

    result = asyncio.run(run_explanation(context, fake))
    assert len(requests) == 1
    assert result["analysis"] == original
    assert result["explanation"]["status"] == "validated_catalogue_selection"
    assert result["explanation"]["adherence_status"] == "not_evaluated"
    assert {c["evidence_id"] for c in result["explanation"]["claims"]} >= set(
        context.mandatory_evidence_ids
    )
    assert "UNTRUSTED_MUTATION" not in json.dumps(result)
    assert result["explanation_transport"]["attempts"] == 1
    assert result["explanation_transport"]["real_provider_verified"] is False


@pytest.mark.parametrize("max_attempts", [1, 2])
def test_one_repair_reuses_same_packet_without_echoing_invalid_output(context, max_attempts):
    from scripts.explanation_transport import TransportLimits, TransportReply, run_explanation

    requests = []

    async def fake(request):
        requests.append(request)
        body = json.loads(request.payload_json)
        assert "PRIVATE_RESPONSE_SENTINEL" not in request.payload_json
        assert body["repair"] is (len(requests) == 2)
        if len(requests) == 1:
            return TransportReply(content="PRIVATE_RESPONSE_SENTINEL not JSON")
        assert json.loads(requests[0].payload_json)["packet"] == body["packet"]
        return TransportReply(
            content=json.dumps(
                {
                    "packet_sha256": context.packet_sha256,
                    "evidence_ids": ["c1_prediction"],
                }
            )
        )

    result = asyncio.run(
        run_explanation(context, fake, limits=TransportLimits(max_attempts=max_attempts))
    )
    assert result["analysis"] == context.analysis()
    assert len(requests) == max_attempts
    assert result["explanation_transport"]["attempts"] == max_attempts
    assert result["explanation"]["status"] == (
        "validated_catalogue_selection" if max_attempts == 2 else "incomplete"
    )
    assert "PRIVATE_RESPONSE_SENTINEL" not in json.dumps(result)


@pytest.mark.parametrize(
    "mode,reason",
    [
        ("exception", "transport_failed"),
        ("timeout", "transport_timeout"),
        ("protocol", "invalid_transport_reply"),
        ("content_type", "invalid_transport_reply"),
        ("truncated", "incomplete_generation"),
        ("tool_calls", "incomplete_generation"),
    ],
)
def test_transport_failures_do_not_retry_or_leak_provider_output(context, capsys, mode, reason):
    from scripts.explanation_transport import TransportReply, run_explanation

    calls = []

    async def fake(request):
        calls.append(request)
        if mode == "exception":
            raise RuntimeError("PRIVATE_PROVIDER_ERROR_SENTINEL")
        if mode == "timeout":
            raise TimeoutError("PRIVATE_PROVIDER_ERROR_SENTINEL")
        if mode == "protocol":
            return {"content": "PRIVATE_PROVIDER_ERROR_SENTINEL"}
        if mode == "content_type":
            return TransportReply(content=42)
        return TransportReply(
            content="PRIVATE_PROVIDER_ERROR_SENTINEL",
            finish_reason=("length" if mode == "truncated" else "tool_calls"),
        )

    result = asyncio.run(run_explanation(context, fake))
    assert len(calls) == 1 and result["explanation_transport"]["attempts"] == 1
    assert result["analysis"] == context.analysis()
    assert result["explanation"]["reason_code"] == reason
    assert result["explanation"]["claims"] == []
    assert "PRIVATE_PROVIDER_ERROR_SENTINEL" not in json.dumps(result)
    captured = capsys.readouterr()
    assert "PRIVATE_PROVIDER_ERROR_SENTINEL" not in captured.out + captured.err


def test_total_deadline_is_not_reset_for_the_repair(context):
    from scripts.explanation_transport import TransportLimits, TransportReply, run_explanation

    requests, cancelled = [], []

    async def fake(request):
        requests.append(request)
        if len(requests) == 1:
            await asyncio.sleep(0.02)
            return TransportReply(content="not JSON")
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.append(True)
        return TransportReply(
            content=json.dumps(
                {
                    "packet_sha256": context.packet_sha256,
                    "evidence_ids": ["c1_prediction"],
                }
            )
        )

    result = asyncio.run(
        run_explanation(context, fake, limits=TransportLimits(total_timeout_seconds=0.2))
    )
    assert result["analysis"] == context.analysis()
    assert result["explanation"]["reason_code"] == "transport_timeout"
    assert len(requests) == 2 and cancelled == [True]
    assert requests[1].remaining_seconds < requests[0].remaining_seconds


def test_caller_cancellation_propagates_without_repair_or_background_task(context):
    from scripts.explanation_transport import run_explanation

    async def scenario():
        entered = asyncio.Event()
        cleaned = asyncio.Event()
        calls = []

        async def fake(request):
            calls.append(request)
            entered.set()
            try:
                await asyncio.Event().wait()
            finally:
                cleaned.set()

        task = asyncio.create_task(run_explanation(context, fake))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert cleaned.is_set() and len(calls) == 1

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "mode,reason",
    [
        ("oversized_utf8", "response_limit_exceeded"),
        ("invalid_unicode", "invalid_transport_reply"),
    ],
)
def test_response_byte_limits_reject_without_repair(context, mode, reason):
    from scripts.explanation_transport import TransportReply, run_explanation

    calls = []

    async def fake(request):
        calls.append(request)
        return TransportReply(content="é" * 9000 if mode == "oversized_utf8" else "\ud800")

    result = asyncio.run(run_explanation(context, fake))
    assert len(calls) == 1
    assert result["explanation"]["reason_code"] == reason
    assert result["analysis"] == context.analysis()


def test_oversized_outgoing_packet_is_not_dispatched(context):
    from dataclasses import replace

    from scripts.explanation_evidence import EvidenceFact
    from scripts.explanation_transport import run_explanation

    extra = tuple(
        EvidenceFact(evidence_id=f"extra_{i}", statement_pt="x" * 1500) for i in range(60)
    )
    packet = context.packet.model_copy(update={"evidence": context.packet.evidence + extra})
    enlarged = replace(context, packet=packet)
    calls = []

    async def forbidden(request):
        calls.append(request)
        raise AssertionError("oversized request dispatched")

    result = asyncio.run(run_explanation(enlarged, forbidden))
    assert calls == []
    assert result["explanation_transport"]["attempts"] == 0
    assert result["explanation"]["reason_code"] == "request_limit_exceeded"


def test_exhausted_invalid_selections_return_no_claims(context):
    from scripts.explanation_transport import TransportReply, run_explanation

    calls = []

    async def fake(request):
        calls.append(request)
        return TransportReply(
            content=json.dumps(
                {
                    "packet_sha256": context.packet_sha256,
                    "evidence_ids": ["UNKNOWN_PRIVATE_REFERENCE"],
                }
            )
        )

    result = asyncio.run(run_explanation(context, fake))
    assert len(calls) == 2
    assert result["explanation"]["reason_code"] == "invalid_selection"
    assert result["explanation"]["claims"] == []
    assert result["analysis"] == context.analysis()
    assert "UNKNOWN_PRIVATE_REFERENCE" not in json.dumps(result)


def test_late_valid_reply_is_discarded_when_callback_swallows_deadline_cancellation(context):
    from scripts.explanation_transport import TransportLimits, TransportReply, run_explanation

    calls = []

    async def fake(request):
        calls.append(request)
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            return TransportReply(
                content=json.dumps(
                    {
                        "packet_sha256": context.packet_sha256,
                        "evidence_ids": ["c1_prediction"],
                    }
                )
            )

    result = asyncio.run(
        run_explanation(context, fake, limits=TransportLimits(total_timeout_seconds=0.02))
    )
    assert len(calls) == 1
    assert result["explanation"]["reason_code"] == "transport_timeout"
    assert result["analysis"] == context.analysis()


@pytest.mark.parametrize("count", [1, 5])
def test_numeric_reports_preserved(serving, registry, monkeypatch, count):  # noqa: F811
    from scripts.creative_analysis import analyze_creatives
    from scripts.explanation_transport import TransportReply, run_explanation
    from tests.test_m1_service import features, payload

    settings, ids, _ = serving
    monkeypatch.setattr(
        "scripts.m1_service.extract_candidates", lambda *a: features([2, 4, 4, 1, 3][:count])
    )
    original = analyze_creatives(payload(ids[:count]), registry, m1=settings)
    context = build_explanation_context(original)

    async def fake(request):
        return TransportReply(
            content=json.dumps(
                {
                    "packet_sha256": context.packet_sha256,
                    "evidence_ids": ["c1_prediction"],
                }
            )
        )

    result = asyncio.run(run_explanation(context, fake))
    assert result["analysis"] == original
    assert result["explanation"]["status"] == "validated_catalogue_selection"
    assert len(result["analysis"]["candidates"]) == count

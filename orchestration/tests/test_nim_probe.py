"""Synthetic local fakes only; no API, credential lookup or media acquisition."""

import asyncio
import hashlib
import json
import os
import socket
import sys

import pytest

from galaxies_orchestration import nim_http, nim_probe


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("real_network_forbidden")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


class Response:
    def __init__(self, status=200, raw=None):
        self.status = status
        self.raw = (
            raw
            if raw is not None
            else json.dumps(
                {
                    "choices": [
                        {
                            "message": {"role": "assistant", "content": "invented"},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {"completion_tokens": 10},
                }
            ).encode()
        )
        self.reads = []

    def read(self, maximum):
        self.reads.append(maximum)
        return self.raw[:maximum]


def http_fake(response):
    calls, connections, closed = [], [], []

    class Connection:
        def __init__(self, *args, **kwargs):
            connections.append((args, kwargs))

        def request(self, *args, **kwargs):
            calls.append((args, kwargs))

        def getresponse(self):
            return response

        def close(self):
            closed.append(True)

    return Connection, calls, connections, closed


def test_single_fixed_https_request_and_bounded_reply():
    response = Response()
    factory, calls, connections, closed = http_fake(response)
    result = nim_http.perform_http("INVENTED_TEST_KEY", connection_factory=factory)
    assert len(calls) == 1 and closed == [True]
    assert connections[0][0] == ("integrate.api.nvidia.com",)
    assert connections[0][1]["port"] == 443 and connections[0][1]["timeout"] == 45
    args, kwargs = calls[0]
    assert args == ("POST", "/v1/chat/completions")
    assert kwargs["headers"]["Authorization"] == "Bearer INVENTED_TEST_KEY"
    body = json.loads(kwargs["body"])
    assert body["model"] == nim_http.MODEL
    assert body["max_tokens"] == 2048 and body["stream"] is False
    assert body["chat_template_kwargs"]["enable_thinking"] is False
    assert "INVENTED_TEST_KEY" not in kwargs["body"].decode()
    assert response.reads == [16385]
    assert result["status"] == "reply_received" and result["completion_tokens"] == 10


@pytest.mark.parametrize("status", [301, 302, 401, 402, 403, 429, 503])
def test_error_or_billing_or_redirect_never_retries_or_reads_body(status):
    response = Response(status)
    factory, calls, _, closed = http_fake(response)
    assert nim_http.perform_http("INVENTED", connection_factory=factory) == {
        "status": "http_error",
        "http_status": status,
    }
    assert len(calls) == 1 and response.reads == [] and closed == [True]


@pytest.mark.parametrize("mode", ["oversize", "invalid", "length", "tool", "tokens"])
def test_invalid_or_oversized_provider_reply_is_not_exposed(mode):
    response = Response()
    if mode in {"oversize", "invalid"}:
        response.raw = b"PRIVATE_BODY" * 2000 if mode == "oversize" else b"PRIVATE_BODY"
    else:
        data = json.loads(response.raw)
        if mode == "length":
            data["choices"][0]["finish_reason"] = "length"
        if mode == "tool":
            data["choices"][0]["message"]["tool_calls"] = [{"private": "PRIVATE_BODY"}]
        if mode == "tokens":
            data["usage"]["completion_tokens"] = 2049
        response.raw = json.dumps(data).encode()
    factory, calls, _, _ = http_fake(response)
    result = nim_http.perform_http("INVENTED", connection_factory=factory)
    assert len(calls) == 1 and "content" not in result
    assert "PRIVATE_BODY" not in json.dumps(result)
    assert result["status"] == (
        "response_limit_exceeded" if mode == "oversize" else "invalid_provider_reply"
    )


def plan_fixture(folder, monkeypatch):
    result = {
        "max_calls": 1,
        "max_output_tokens": 2048,
        "timeout_seconds": 45,
        "max_response_bytes": 16384,
        "max_spend_brl": 0,
        "endpoint": "https://" + nim_http.HOST + nim_http.PATH,
        "model": nim_http.MODEL,
        "text_only_entirely_invented": True,
        "fixture_sha256": nim_probe.sha(nim_http.FIXTURE),
        "http_payload_sha256": hashlib.sha256(
            json.dumps(nim_http.payload(), ensure_ascii=True).encode()
        ).hexdigest(),
        "protected_sha256": {
            "orchestration/fixtures/nim-synthetic-request.json": nim_probe.sha(nim_http.FIXTURE)
        },
    }
    (folder / "plan.json").write_text(json.dumps(result))
    monkeypatch.setattr(nim_probe, "APPROVED_PLAN_SHA256", nim_probe.sha(folder / "plan.json"))
    return result


@pytest.mark.parametrize("status", ["reply_received", "http_error", "timeout_outcome_uncertain"])
def test_durable_reservation_precedes_dispatch_and_cannot_repeat(tmp_path, monkeypatch, status):
    plan_fixture(tmp_path, monkeypatch)
    calls = []

    async def fake(command, *, environment, timeout, input_bytes):
        assert (tmp_path / "reservation.json").is_file()
        assert (tmp_path / "reservation.json").stat().st_mode & 0o777 == 0o600
        assert not (tmp_path / "result.json").exists()
        assert timeout == 45 and "PROXY" not in " ".join(environment)
        assert len(input_bytes) == 32
        reservation = json.loads((tmp_path / "reservation.json").read_bytes())
        assert reservation["dispatch_token_sha256"] == hashlib.sha256(input_bytes).hexdigest()
        calls.append(True)
        return {
            "status": status,
            "http_status": 503 if status == "http_error" else 200,
            "content": "PRIVATE_RAW_BODY",
        }

    selector = nim_probe.OneShotNim(tmp_path, runner=fake)
    request = nim_http.FIXTURE.read_text().strip()
    if status == "reply_received":
        assert asyncio.run(selector(request)) == "PRIVATE_RAW_BODY"
    else:
        with pytest.raises(ValueError):
            asyncio.run(selector(request))
    receipt = (tmp_path / "result.json").read_text()
    assert "PRIVATE_RAW_BODY" not in receipt and "retry_allowed" in receipt
    with pytest.raises(FileExistsError):
        asyncio.run(nim_probe.OneShotNim(tmp_path, runner=fake)(request))
    assert len(calls) == 1


def test_private_or_changed_request_is_rejected_before_reservation(tmp_path, monkeypatch):
    plan_fixture(tmp_path, monkeypatch)
    selector = nim_probe.OneShotNim(tmp_path)
    with pytest.raises(ValueError, match="only_fixed_synthetic"):
        asyncio.run(selector("PRIVATE_REQUEST"))
    assert not (tmp_path / "reservation.json").exists()


@pytest.mark.parametrize("tamper", ["budget", "empty_pins", "removed_pins", "truncated"])
def test_plan_tampering_stops_before_attempt(tmp_path, monkeypatch, tamper):
    plan = plan_fixture(tmp_path, monkeypatch)
    if tamper == "budget":
        plan["max_calls"] = 2
    elif tamper == "empty_pins":
        plan["protected_sha256"] = {}
    elif tamper == "removed_pins":
        del plan["protected_sha256"]
    else:
        plan = {"max_calls": 1}
    (tmp_path / "plan.json").write_text(json.dumps(plan))
    with pytest.raises(ValueError, match="probe_plan_seal_mismatch"):
        asyncio.run(nim_probe.OneShotNim(tmp_path)(nim_http.FIXTURE.read_text().strip()))
    assert not (tmp_path / "reservation.json").exists()


def test_cancelled_attempt_is_consumed_and_receipted(tmp_path, monkeypatch):
    plan_fixture(tmp_path, monkeypatch)

    async def scenario():
        entered = asyncio.Event()

        async def fake(*args, **kwargs):
            entered.set()
            await asyncio.Event().wait()

        task = asyncio.create_task(
            nim_probe.OneShotNim(tmp_path, runner=fake)(nim_http.FIXTURE.read_text().strip())
        )
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    assert (
        json.loads((tmp_path / "result.json").read_bytes())["status"]
        == "cancelled_outcome_uncertain"
    )


def test_wall_deadline_kills_noncooperative_child_without_retry(tmp_path):
    script = tmp_path / "pid"

    async def scenario():
        code = (
            "import os,time;open('" + str(script) + "','w').write(str(os.getpid()));time.sleep(60)"
        )
        result = await nim_probe.bounded_child(
            [sys.executable, "-c", code], environment={}, timeout=0.3
        )
        assert result["status"] == "timeout_outcome_uncertain"
        with pytest.raises(ProcessLookupError):
            os.kill(int(script.read_text()), 0)

    asyncio.run(scenario())


def test_existing_key_reads_only_named_entry_without_interpolation(tmp_path, monkeypatch):
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    (tmp_path / ".env").write_text('OTHER_SECRET=do_not_use\nNVIDIA_API_KEY="' + "x" * 30 + '"\n')
    assert nim_http.existing_key(tmp_path) == "x" * 30
    (tmp_path / ".env").write_text('NVIDIA_API_KEY="INVALID\nHEADER"\n')
    with pytest.raises(ValueError, match="credential_unavailable"):
        nim_http.existing_key(tmp_path)


@pytest.mark.parametrize("fault", ["missing_nonce", "wrong_nonce", "wrong_parent", "valid"])
def test_direct_child_cannot_resume_an_uncertain_reservation(tmp_path, monkeypatch, fault):
    plan_fixture(tmp_path, monkeypatch)
    token = b"x" * 32
    reservation = {
        "dispatch_token_sha256": hashlib.sha256(token).hexdigest(),
        "parent_pid": 123,
        "plan_sha256": nim_probe.sha(tmp_path / "plan.json"),
    }
    nim_http.durable_create(tmp_path / "reservation.json", reservation)
    provided = b"" if fault == "missing_nonce" else b"y" * 32 if fault == "wrong_nonce" else token
    if fault == "valid":
        nim_http.authorize_dispatch(provided, folder=tmp_path, parent_pid=123)
        assert (tmp_path / "dispatch.json").is_file()
        with pytest.raises(FileExistsError):
            nim_http.authorize_dispatch(provided, folder=tmp_path, parent_pid=123)
    else:
        with pytest.raises(ValueError, match="live_parent_dispatch_required"):
            nim_http.authorize_dispatch(
                provided, folder=tmp_path, parent_pid=456 if fault == "wrong_parent" else 123
            )
        assert not (tmp_path / "dispatch.json").exists()


def test_real_synthetic_worker_graph_uses_exact_public_fixture():
    from galaxies_orchestration.graph import build_graph
    from galaxies_orchestration.worker import RootWorker

    calls = []

    async def fake(request):
        assert request == nim_http.FIXTURE.read_text().strip()
        calls.append(True)
        body = json.loads(request)
        return json.dumps(
            {
                "packet_sha256": body["packet_sha256"],
                "evidence_ids": ["c1_prediction", "c1_interval"],
            }
        )

    async def scenario():
        async with RootWorker(synthetic_probe=True) as worker:
            result = (await build_graph(worker, fake).ainvoke({"payload": {}}))["result"]
            assert result["fixture_entirely_invented"] is True
            assert result["explanation"]["status"] == "validated_catalogue_selection"
            assert result["analysis"]["candidates"][0]["prediction"]["value"] == 123.0
            assert len(calls) == 1

    asyncio.run(scenario())

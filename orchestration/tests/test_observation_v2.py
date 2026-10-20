import asyncio
import json
import socket
import uuid

import pytest

from galaxies_orchestration.observation_cases_v2 import EXPECTED, WIRE_EXPECTED, content
from galaxies_orchestration.observation_v2 import Reply, run_observed


@pytest.fixture(autouse=True)
def deny_network(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("network_forbidden")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)


@pytest.mark.parametrize("case", EXPECTED)
def test_integrated_receipt_static_reason_safe_projection_and_disk_stdio(tmp_path, capfd, case):
    secret = uuid.uuid4().hex + uuid.uuid4().hex
    raw = content(case, secret=secret)
    folder = tmp_path / "audit"
    calls = []

    async def callback(request):
        assert request["max_output_tokens"] == 2048 and 0 < request["remaining_seconds"] <= 45
        assert (folder / "local-consumption.json").exists()
        calls.append(True)
        return Reply(raw, wire_bytes=len(raw.encode("utf-8", errors="surrogatepass")) + 64)

    result = asyncio.run(run_observed(callback, folder))
    observation = result["observation"]
    assert (observation["phase"], observation["code"]) == EXPECTED[case]
    assert len(calls) == 1 and observation["real_requests"] == 0
    assert observation["authority_accepted"] is (case in {"valid", "valid_whitespace"})
    assert result["result"]["analysis"]["candidates"][0]["prediction"]["value"] == 123.0
    assert observation["raw_response_sha256"] is None
    on_disk = b"".join(p.read_bytes() for p in folder.rglob("*") if p.is_file())
    stdio = capfd.readouterr()
    serialized = json.dumps(result).encode()
    for needle in (secret.encode(), b"Authorization: Bearer", b"nvapi-" + secret.encode()):
        assert needle not in on_disk + serialized + stdio.out.encode() + stdio.err.encode()
    assert b"simulated_consumed" in on_disk
    assert json.loads((folder / "observation.json").read_bytes()) == observation
    with pytest.raises(FileExistsError):
        asyncio.run(run_observed(callback, folder))
    assert len(calls) == 1


@pytest.mark.parametrize(
    "mode", ["exception", "status", "http_metadata", "finish", "tokens", "oversize"]
)
def test_transport_adversarial_metadata_never_escapes(tmp_path, capfd, mode):
    secret = uuid.uuid4().hex + uuid.uuid4().hex

    async def callback(request):
        if mode == "exception":
            raise RuntimeError("Authorization: Bearer " + secret)
        if mode == "status":
            return Reply(secret, status=secret)
        if mode == "http_metadata":
            return Reply(secret, http_status=secret)
        if mode == "finish":
            return Reply(secret, finish_reason=secret)
        if mode == "tokens":
            return Reply(secret, completion_tokens=2049)
        return Reply(secret * 300, wire_bytes=16384)

    folder = tmp_path / "audit"
    result = asyncio.run(run_observed(callback, folder))
    assert result["observation"]["authority_accepted"] is False
    assert result["observation"]["safe_response_projection"] is None
    output = capfd.readouterr()
    disk = b"".join(p.read_bytes() for p in folder.rglob("*") if p.is_file())
    assert (
        secret.encode()
        not in disk + json.dumps(result).encode() + output.out.encode() + output.err.encode()
    )


def test_cancellation_preserves_consumption_without_reuse(tmp_path):
    folder = tmp_path / "audit"

    async def scenario():
        entered = asyncio.Event()

        async def callback(request):
            entered.set()
            await asyncio.Event().wait()

        task = asyncio.create_task(run_observed(callback, folder))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        receipt = json.loads((folder / "observation.json").read_bytes())
        assert receipt["code"] == "cancelled_outcome_uncertain"
        assert receipt["retry_allowed"] is False
        with pytest.raises(FileExistsError):
            await run_observed(callback, folder)

    asyncio.run(scenario())


def test_deep_json_keeps_json_stage_without_claiming_sealed_rendering(tmp_path):
    raw = "[" * 2500 + "]" * 2500

    async def callback(request):
        return Reply(raw, wire_bytes=len(raw) + 64)

    result = asyncio.run(run_observed(callback, tmp_path / "audit"))
    assert result["result"] is None
    assert result["observation"]["phase"] == "json"
    assert result["observation"]["code"] == "json_depth_limit"
    assert result["observation"]["authority_status"] == "failed_before_result"
    assert result["observation"]["authority_accepted"] is False


def test_existing_uncertain_folder_and_real_ledger_cannot_be_reused(tmp_path):
    from galaxies_orchestration.nim_http import LEDGER

    calls = []

    async def callback(request):
        calls.append(True)

    folder = tmp_path / "uncertain"
    folder.mkdir()
    with pytest.raises(FileExistsError):
        asyncio.run(run_observed(callback, folder))
    with pytest.raises(ValueError, match="sealed_ledger_forbidden"):
        asyncio.run(run_observed(callback, LEDGER))
    assert calls == []


@pytest.mark.parametrize("case", WIRE_EXPECTED)
def test_open_response_bridge_in_root_process_suppresses_wire_secrets(tmp_path, capfd, case):
    secret = uuid.uuid4().hex + uuid.uuid4().hex
    folder = tmp_path / "audit"
    result = asyncio.run(run_observed(None, folder, envelope_case=case, fixture_secret=secret))
    observation = result["observation"]
    assert (observation["phase"], observation["code"]) == WIRE_EXPECTED[case]
    assert observation["authority_accepted"] is (case in {"valid", "envelope_extra_secret"})
    assert observation["real_requests"] == 0
    assert observation["raw_wire_sha256"] is None
    if case == "content_deep":
        assert result["result"] is None
        assert observation["authority_status"] == "failed_before_result"
    else:
        assert result["result"]["analysis"]["candidates"][0]["prediction"]["value"] == 123.0
    output = capfd.readouterr()
    disk = b"".join(p.read_bytes() for p in folder.rglob("*") if p.is_file())
    for needle in (secret.encode(), b"Authorization", b"Bearer "):
        assert (
            needle
            not in disk + json.dumps(result).encode() + output.out.encode() + output.err.encode()
        )

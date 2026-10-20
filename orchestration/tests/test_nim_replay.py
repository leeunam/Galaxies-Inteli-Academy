"""Public invented replays; real processes and validation, fake HTTP only."""

import asyncio
import json
import socket

import pytest
from test_nim_probe import plan_fixture

from galaxies_orchestration.nim_replay import CASES, replay


@pytest.fixture(autouse=True)
def deny_network_and_real_key(monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("external_access_forbidden")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)
    monkeypatch.setenv("NVIDIA_API_KEY", "INVENTED_PARENT_SENTINEL_MUST_NOT_ENTER_CHILD")


@pytest.mark.parametrize("case", CASES)
def test_same_real_graph_process_adapter_and_validator_offline(tmp_path, monkeypatch, case):
    plan_fixture(tmp_path, monkeypatch)
    result = asyncio.run(replay(case, plan_bytes=(tmp_path / "plan.json").read_bytes()))
    assert result["actual_network_calls"] == 0
    assert result["real_credentials_loaded"] is False
    assert result["real_child_process_reaped"] and result["real_root_worker_reaped"]
    assert result["stategraph_executed"] and result["fixture_entirely_invented"]
    assert result["simulated_adapter_attempts"] == 1
    assert result["adapter_status"] == result["provider_status"] == "reply_received"
    assert result["selection_validated"] is (case == "valid")
    expected_reason = (
        None
        if case == "valid"
        else ("transport_failed" if case == "invalid_unicode" else "invalid_selection")
    )
    assert result["explanation_reason_code"] == expected_reason
    assert result["analysis"]["candidates"][0]["prediction"]["value"] == 123.0
    assert "INVENTED_PARENT_SENTINEL" not in json.dumps(result)

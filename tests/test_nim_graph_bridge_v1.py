"""Only public invented inputs, fake envelopes and unchanged root authority."""

import hashlib
import json
from pathlib import Path

import pytest

from orchestration.galaxies_orchestration import nim_graph_contract_v1 as contract
from scripts import nim_graph_bridge_v1 as bridge
from scripts.nim_dispatch_plan_v3 import payload_bytes as predecessor_payload
from tests.test_nim_dispatch_v3 import no_remote_or_credentials  # noqa: F401


def prepared(case="valid"):
    session = bridge.BridgeSession(case, "a" * 32)
    checkpoint = session.handle({"op": "analyze", "payload": {}})
    session.handle({"op": "shap"})
    session.handle({"op": "comparables"})
    packet = session.handle({"op": "context"})
    assert checkpoint["native_feature_handoff"] is False
    assert packet["packet"] == contract.fixture()["request"]["packet"]
    return session


def test_fixture_is_new_and_entirely_invented_with_three_candidates():
    public = contract.fixture()
    assert public["fixture_kind"] == "entirely_invented_three_creative_graph_v1"
    assert len(public["data"]["report"]["candidates"]) == 3
    assert [c["prediction"]["value"] for c in public["data"]["report"]["candidates"]] == [
        137,
        283,
        211,
    ]
    assert len(public["request"]["packet"]["evidence"]) == 24
    assert {f["creative_id"] for f in public["request"]["packet"]["evidence"]} == {
        None,
        *("cr_" + n * 32 for n in "789"),
    }
    request = json.dumps(public["request"])
    for forbidden in ("example.invalid", "sample_id", "source_url", "/home/", "text_embedding"):
        assert forbidden not in request
    assert all(
        "entirely_invented_reference_" in row["references"][0]["sample_id"]
        for row in public["data"]["comparables"].values()
    )
    prepared()


def test_proposed_payload_is_exact_text_only_with_zero_current_authorization():
    plan = contract.verify_plan()
    config = plan["configuration"]
    assert config["remaining_authorized_calls"] == 0
    assert config["specific_remote_authorization_id"] is None
    assert config["remote_execution_released"] is False
    assert config["proposed_future_calls"] == 1
    assert (
        config["total_timeout_seconds"],
        config["max_output_tokens"],
        config["max_response_bytes"],
        config["max_spend_brl"],
    ) == (45, 2048, 16384, 0)
    assert config["http_payload_sha256"] == contract.digest(contract.payload_bytes())
    new = json.loads(contract.payload_bytes())
    old = json.loads(predecessor_payload())
    assert "entirely invented" in new["messages"][0]["content"]
    new["messages"] = old["messages"]
    assert new == old
    assert len(contract.response_schema()["properties"]["evidence_ids"]["items"]["enum"]) == 24


@pytest.mark.parametrize("case", ["valid", "wrong_hash", "secret_id", "http_error", "invalid_wire"])
def test_root_sanitizes_before_ipc_and_preserves_report(case):
    session = prepared(case)
    selected = session.handle(
        {"op": "select", "request": contract.canonical(contract.fixture()["request"]).decode()}
    )
    result = session.handle(
        {
            "op": "render",
            "selection": selected["selection"],
            "reason": None if selected["selection"] else "transport_failed",
        }
    )
    proof = session.handle({"op": "proof"})
    assert result["analysis"] == contract.fixture()["data"]["report"]
    assert proof["root_render_accepted"] is (case == "valid")
    assert proof["root_selection_accepted"] is (case == "valid")
    assert proof["real_http_requests"] == 0 and proof["live_dispatch"] is None
    retained = json.dumps([selected, result, proof])
    for forbidden in ("ENTIRELY_INVENTED_SECRET_ID", "ENTIRELY_INVENTED_SECRET_BODY"):
        assert forbidden not in retained
        assert hashlib.sha256(forbidden.encode()).hexdigest() not in retained
    with pytest.raises(ValueError, match="transition"):
        session.handle({"op": "select", "request": "{}"})


def test_divergent_graph_packet_is_refused_before_fake_transport(monkeypatch):
    session = prepared()
    request = contract.fixture()["request"]
    request["packet_sha256"] = "0" * 64

    def forbidden(*args):
        raise AssertionError("must_not_call_transport")

    monkeypatch.setattr(bridge, "fake_response", forbidden)
    with pytest.raises(ValueError, match="packet_not_authorized"):
        session.handle({"op": "select", "request": json.dumps(request)})
    with pytest.raises(ValueError, match="transition"):
        session.handle({"op": "select", "request": "{}"})


def test_remote_refuses_without_any_file_or_ledger_access(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("remote_branch_must_have_no_side_effect")

    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(Path, "mkdir", forbidden)
    with pytest.raises(ValueError, match="no_remote_authorization"):
        contract.remote_exchange()


def test_nonempty_input_is_never_interpreted_as_real_creative_data():
    session = bridge.BridgeSession("valid", "a" * 32)
    with pytest.raises(ValueError, match="empty_synthetic_input"):
        session.handle({"op": "analyze", "payload": {"creative_ids": ["PRIVATE_SENTINEL"]}})
    with pytest.raises(ValueError, match="transition"):
        session.handle({"op": "analyze", "payload": {}})

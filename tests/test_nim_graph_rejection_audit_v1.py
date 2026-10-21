"""Invented discriminants, never a replay or a remote execution entrypoint."""

import hashlib
import http.client
import json
import socket

import pytest

from orchestration.galaxies_orchestration import nim_http
from orchestration.galaxies_orchestration.nim_graph_contract_v1 import fixture, response_schema
from scripts import nim_graph_bridge_v1 as bridge
from scripts.explanation_evidence import validate_selection
from scripts.nim_dispatch_plan_v3 import FIXTURE as SINGLE_FIXTURE
from scripts.nim_type_observer_v1 import observe_open_response
from scripts.nim_typed_request_v1 import response_schema as single_schema
from scripts.selection_observation_v2 import classify

SENTINEL = "entirely_invented_unknown_private_value"
PUBLIC = fixture()
CATALOG = [fact["evidence_id"] for fact in PUBLIC["request"]["packet"]["evidence"]]
PACKET = PUBLIC["request"]["packet_sha256"]


@pytest.fixture(autouse=True)
def no_network_key_or_model(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("offline_audit_forbids_network_credential_or_model")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(http.client.HTTPSConnection, "request", forbidden)
    monkeypatch.setattr(nim_http, "existing_key", forbidden)
    # Session receives explicit invented callbacks; the real loaders must not run.
    monkeypatch.setattr("scripts.explanation_session_v2.explain_m1", forbidden)
    monkeypatch.setattr("scripts.explanation_session_v2.load_training_index", forbidden)


def prepared_session():
    session = bridge.BridgeSession("valid", "a" * 32)
    assert session.handle({"op": "analyze", "payload": {}})["native_feature_handoff"] is False
    for op in ("shap", "comparables", "context"):
        session.handle({"op": op})
    return session


@pytest.fixture
def context():
    return prepared_session().session.context


def selection(ids, packet=PACKET):
    return json.dumps({"packet_sha256": packet, "evidence_ids": ids})


def cases():
    single = json.loads(SINGLE_FIXTURE.read_bytes())
    good = {"packet_sha256": PACKET, "evidence_ids": ["c2_interval"]}
    return [
        ("one_id", json.dumps(good), "accepted", True),
        ("twelve_ids", selection(CATALOG[:12]), "accepted", True),
        ("empty_ids", selection([]), "schema_constraint", False),
        ("thirteen_ids", selection(CATALOG[:13]), "schema_constraint", False),
        ("all_twentyfour_ids", selection(CATALOG), "schema_constraint", False),
        ("duplicate_id", selection(["c2_interval", "c2_interval"]), "duplicate_evidence_id", False),
        (
            "single_packet_hash",
            selection(["c2_interval"], single["packet_sha256"]),
            "packet_hash_mismatch",
            False,
        ),
        ("unknown_id", selection([SENTINEL]), "unknown_evidence_id", False),
        ("missing_ids", json.dumps({"packet_sha256": PACKET}), "schema_missing_field", False),
        ("extra_field", json.dumps(good | {SENTINEL: SENTINEL}), "schema_extra_field", False),
        (
            "ids_scalar",
            json.dumps(good | {"evidence_ids": "c2_interval"}),
            "schema_invalid_type",
            False,
        ),
        (
            "object_item",
            json.dumps(good | {"evidence_ids": [{"evidence_id": "c2_interval"}]}),
            "schema_invalid_type",
            False,
        ),
        (
            "hash_object",
            json.dumps(good | {"packet_sha256": {"value": PACKET}}),
            "schema_invalid_type",
            False,
        ),
        ("double_encoded", json.dumps(json.dumps(good)), "schema_invalid_type", False),
        ("fenced_json", "```json\n" + json.dumps(good) + "\n```", "json_syntax", False),
        (
            "duplicate_json_key",
            '{"packet_sha256":"' + PACKET + '","evidence_ids":[],"evidence_ids":["c2_interval"]}',
            "json_duplicate_key",
            False,
        ),
        ("deep_json", "[" * 2500 + "]" * 2500, "json_depth_limit", False),
    ]


@pytest.mark.parametrize(
    "name,raw,code,accepted",
    cases(),
    ids=lambda value: value if isinstance(value, str) and len(value) < 30 else None,
)
def test_closed_contract_discriminants(context, name, raw, code, accepted):
    observation = classify(context, raw)
    assert observation["code"] == code
    assert (
        observation["safe_response_projection"] is None
    )  # legacy observer projects only fixture one
    assert observation["raw_response_sha256"] is None
    if accepted:
        result = validate_selection(context, raw)
        assert result["analysis"] == PUBLIC["data"]["report"]
        assert result["explanation"]["status"] == "validated_catalogue_selection"
    else:
        with pytest.raises(RecursionError if name == "deep_json" else ValueError):
            validate_selection(context, raw)
    encoded = json.dumps(observation)
    assert SENTINEL not in encoded and hashlib.sha256(SENTINEL.encode()).hexdigest() not in encoded


@pytest.mark.parametrize("evidence_id", CATALOG)
def test_each_of_twentyfour_catalog_ids_is_accepted_individually(context, evidence_id):
    result = validate_selection(context, selection([evidence_id]))
    assert result["analysis"] == PUBLIC["data"]["report"]
    assert evidence_id in {claim["evidence_id"] for claim in result["explanation"]["claims"]}


def test_mandatory_six_are_appended_not_required_in_remote_selection(context):
    mandatory = set(context.mandatory_evidence_ids)
    assert len(mandatory) == 6 and "c2_interval" not in mandatory
    result = validate_selection(context, selection(["c2_interval"]))
    assert {claim["evidence_id"] for claim in result["explanation"]["claims"]} == mandatory | {
        "c2_interval"
    }
    chosen = [key for key in CATALOG if key not in mandatory][:12]
    result = validate_selection(context, selection(chosen))
    assert len(chosen) == 12 and len(result["explanation"]["claims"]) == 18
    assert result["analysis"] == PUBLIC["data"]["report"]
    assert response_schema()["properties"]["evidence_ids"]["maxItems"] == 12


class InventedEnvelope:
    status = 200

    def __init__(self, raw, *, target_bytes=None):
        envelope = {
            "choices": [
                {"message": {"role": "assistant", "content": raw}, "finish_reason": "stop"}
            ],
            "usage": {"completion_tokens": 262},  # invented metadata, no tokenizer/model
            "invented_padding": "",
        }
        wire = bridge.canonical(envelope)
        if target_bytes is not None:
            assert len(wire) <= target_bytes
            envelope["invented_padding"] = "x" * (target_bytes - len(wire))
            wire = bridge.canonical(envelope)
            assert len(wire) == target_bytes
        self.wire = wire

    def getheaders(self):
        return [("Content-Type", "application/json")]

    def read(self, size):
        assert size == 16385
        return self.wire[:size]


def retained_by_existing_bridge(raw, monkeypatch):
    session = prepared_session()
    response = InventedEnvelope(raw, target_bytes=1338)
    monkeypatch.setattr(bridge, "fake_response", lambda *args: response)
    selected = session.handle(
        {"op": "select", "request": bridge.canonical(PUBLIC["request"]).decode()}
    )
    result = session.handle(
        {
            "op": "render",
            "selection": selected["selection"],
            "reason": None if selected["selection"] else "transport_failed",
        }
    )
    return selected, result, session.handle({"op": "proof"})


def test_different_failures_have_identical_retained_metadata_not_identifiable_by_tokens(
    context, monkeypatch
):
    excessive = selection(CATALOG[:13])
    wrong_hash = selection(["c2_interval"], "0" * 64)
    assert classify(context, excessive)["code"] == "schema_constraint"
    assert classify(context, wrong_hash)["code"] == "packet_hash_mismatch"
    first = retained_by_existing_bridge(excessive, monkeypatch)
    second = retained_by_existing_bridge(wrong_hash, monkeypatch)
    assert first == second
    selected, result, proof = first
    assert selected == {"selection": None}
    assert proof["transport"] == {
        "code": "selection_rejected",
        "http_status": 200,
        "wire_bytes": 1338,
        "completion_tokens": 262,
    }
    assert result["explanation"]["reason_code"] == "transport_failed"
    assert proof["root_selection_accepted"] is False and proof["root_render_accepted"] is False
    assert proof["origin"] == "offline_fake" and proof["real_http_requests"] == 0


def test_standalone_one_and_graph_three_share_types_and_limit_but_different_packet(context):
    single = json.loads(SINGLE_FIXTURE.read_bytes())
    ids = [fact["evidence_id"] for fact in single["packet"]["evidence"]]
    raw = selection(ids, single["packet_sha256"])
    observed = observe_open_response(InventedEnvelope(raw))
    assert observed["summary"]["selection_validated"] is True
    assert classify(context, raw)["code"] == "packet_hash_mismatch"
    assert (
        validate_selection(context, selection(ids))["explanation"]["status"]
        == "validated_catalogue_selection"
    )
    one, three = (
        single_schema()["properties"]["evidence_ids"],
        response_schema()["properties"]["evidence_ids"],
    )
    assert one["maxItems"] == three["maxItems"] == 12
    assert len(one["items"]["enum"]) == 5 and len(three["items"]["enum"]) == 24
    assert one["type"] == three["type"] == "array"
    assert one["items"]["type"] == three["items"]["type"] == "string"

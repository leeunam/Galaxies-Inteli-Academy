"""Post-authority safe metadata; no network, credential or model path allowed."""

# ruff: noqa: F811 -- pytest injects the explicitly imported public fixture.

import copy
import json
import os
from dataclasses import replace
from pathlib import Path

import pytest

from orchestration.galaxies_orchestration.nim_diagnostic_contract_v1 import (
    execute_remote,
    validate_diagnostic,
)
from orchestration.galaxies_orchestration.nim_graph_contract_v1 import canonical, fixture
from scripts import nim_selection_diagnostic_v1 as observer
from scripts.explanation_evidence import validate_selection
from scripts.nim_diagnostic_worker_v1 import DiagnosticSession
from tests.test_nim_graph_rejection_audit_v1 import (
    CATALOG,
    PACKET,
    SENTINEL,
    cases,
    context,  # noqa: F401
    no_network_key_or_model,  # noqa: F401
    selection,
)


@pytest.mark.parametrize("name,raw,code,accepted", cases(), ids=[row[0] for row in cases()])
def test_same_authority_and_finer_code_without_retaining_input(context, name, raw, code, accepted):
    result = observer.evaluate_original(context, raw)
    diagnostic = validate_diagnostic(result["diagnostic"])
    assert diagnostic["code"] == code
    assert (result["selection"] is not None) is accepted
    assert diagnostic["authority_status"] == (
        "accepted" if accepted else "failed_before_result" if name == "deep_json" else "rejected"
    )
    if accepted:
        assert validate_selection(context, result["selection"]) == validate_selection(context, raw)
    retained = json.dumps(result)
    assert SENTINEL not in retained
    assert not any(
        key in diagnostic
        for key in ("raw", "exception", "input", "safe_response_projection", "raw_response_sha256")
    )


@pytest.mark.parametrize(
    "ids,count,duplicates,membership,item_types",
    [
        (CATALOG[:13], 13, False, True, ["string"]),
        ([CATALOG[0], CATALOG[0]], 2, True, True, ["string"]),
        ([SENTINEL, SENTINEL], 2, True, False, ["string"]),
        ([{"ENTIRELY_INVENTED_UNKNOWN_KEY": SENTINEL}], 1, None, None, ["object"]),
        ([], 0, False, True, []),
    ],
)
def test_known_structure_flags_never_copy_unknown_values(
    context, ids, count, duplicates, membership, item_types
):
    diagnostic = observer.evaluate_original(context, selection(ids))["diagnostic"]
    assert diagnostic["cardinality"] == count
    assert diagnostic["duplicates"] is duplicates
    assert diagnostic["all_ids_in_catalog"] is membership
    assert diagnostic["packet_hash_equal"] is True
    assert diagnostic["types"]["evidence_ids[*]"] == item_types
    assert SENTINEL not in json.dumps(
        diagnostic
    ) and "ENTIRELY_INVENTED_UNKNOWN_KEY" not in json.dumps(diagnostic)


def test_hash_equality_not_rejected_hash_and_unavailable_fields(context):
    raw = selection([CATALOG[0]], "e" * 64)
    diagnostic = observer.evaluate_original(context, raw)["diagnostic"]
    assert diagnostic["packet_hash_equal"] is False and "e" * 64 not in json.dumps(diagnostic)
    diagnostic = observer.evaluate_original(context, json.dumps({"packet_sha256": PACKET}))[
        "diagnostic"
    ]
    assert diagnostic["types"]["evidence_ids"] == ["missing"]
    assert (
        diagnostic["cardinality"]
        is diagnostic["duplicates"]
        is diagnostic["all_ids_in_catalog"]
        is None
    )


def test_authority_runs_before_observer_and_shape(context, monkeypatch):
    events = []
    original_authority, original_observer, original_shape = (
        observer.validate_selection,
        observer.after_sealed_validation,
        observer.shape,
    )

    def authority(*args):
        events.append("authority")
        return original_authority(*args)

    def observed(*args):
        events.append("observer")
        return original_observer(*args)

    def shape(*args):
        events.append("shape")
        return original_shape(*args)

    monkeypatch.setattr(observer, "validate_selection", authority)
    monkeypatch.setattr(observer, "after_sealed_validation", observed)
    monkeypatch.setattr(observer, "shape", shape)
    assert observer.evaluate_original(context, selection(CATALOG[:1]))["selection"] is not None
    assert events == ["authority", "observer", "shape"]


def test_observer_failure_cannot_change_original_acceptance(context, monkeypatch):
    def fail(*args):
        raise RuntimeError(SENTINEL)

    monkeypatch.setattr(observer, "after_sealed_validation", fail)
    result = observer.evaluate_original(context, selection(CATALOG[:1]))
    assert result["selection"] is not None
    assert result["diagnostic"]["authority_status"] == "accepted"
    assert result["diagnostic"]["code"] == "diagnostic_failed"
    assert SENTINEL not in json.dumps(result)


def test_unexpected_authority_failure_does_not_become_rejection_or_acceptance(context, monkeypatch):
    def fail(*args):
        raise RuntimeError(SENTINEL)

    monkeypatch.setattr(observer, "validate_selection", fail)
    result = observer.evaluate_original(context, selection(CATALOG[:1]))
    assert result["selection"] is None
    assert result["diagnostic"]["authority_status"] == "failed_before_result"
    assert result["diagnostic"]["code"] == "sealed_authority_failed"
    assert SENTINEL not in json.dumps(result)


def test_other_context_refused_without_emitting_diagnostic(context):
    other = replace(
        context, packet=context.packet.model_copy(update={"model_artifact_sha256": "e" * 64})
    )
    with pytest.raises(ValueError, match="exact_public_three_context"):
        observer.evaluate_original(other, selection(CATALOG[:1]))


def test_changed_fixture_is_not_treated_as_public(context, tmp_path, monkeypatch):
    path = tmp_path / "invented-altered-fixture.json"
    path.write_text('{"ENTIRELY_INVENTED": true}')
    monkeypatch.setattr(observer, "FIXTURE", path)

    def forbidden(*args):
        raise AssertionError("altered_fixture_must_fail_before_authority")

    monkeypatch.setattr(observer, "validate_selection", forbidden)
    with pytest.raises(ValueError, match="public_fixture_changed"):
        observer.evaluate_original(context, selection(CATALOG[:1]))


@pytest.mark.parametrize(
    "change",
    [
        {"cardinality": True},
        {"code": SENTINEL},
        {SENTINEL: SENTINEL},
        {"packet_hash_equal": "true"},
        {"duplicates": True},
    ],
)
def test_ipc_refuses_untrusted_metadata(context, change):
    diagnostic = copy.deepcopy(
        observer.evaluate_original(context, selection(CATALOG[:1]))["diagnostic"]
    )
    diagnostic.update(change)
    with pytest.raises(ValueError):
        validate_diagnostic(diagnostic)


def test_remote_refuses_before_files_nonce_or_reservation(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("remote_diagnostic_must_be_inert")

    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(Path, "mkdir", forbidden)
    monkeypatch.setattr(os, "urandom", forbidden)
    with pytest.raises(ValueError, match="remote_authorization_absent"):
        execute_remote()


def test_root_select_is_consumed_once_and_render_remains_original():
    session = DiagnosticSession("valid", "a" * 32)
    for message in (
        {"op": "analyze", "payload": {}},
        {"op": "shap"},
        {"op": "comparables"},
        {"op": "context"},
    ):
        session.handle(message)
    message = {"op": "select", "request": canonical(fixture()["request"]).decode()}
    reply = session.handle(message)
    assert reply["diagnostic"]["code"] == "accepted"
    with pytest.raises(ValueError, match="invalid_select_transition"):
        session.handle(message)
    rendered = session.handle({"op": "render", "selection": reply["selection"], "reason": None})
    assert rendered == validate_selection(session.session.context, reply["selection"]) | {
        "schema_version": "creative-explanation-integrated-v2",
        "evidence_packet": fixture()["request"]["packet"],
    }

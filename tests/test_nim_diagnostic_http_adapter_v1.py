"""Already-open fake responses, absent authorization and no real side effects."""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from orchestration.galaxies_orchestration import nim_diagnostic_attempt_contract_v1 as c
from orchestration.galaxies_orchestration.nim_graph_contract_v1 import fixture
from scripts import nim_diagnostic_attempt_worker_v1 as worker
from scripts.nim_diagnostic_http_adapter_v1 import observe_opened_response
from scripts.nim_diagnostic_worker_v1 import invented_response
from tests.test_nim_graph_rejection_audit_v1 import (
    no_network_key_or_model,  # noqa: F401
    prepared_session,
)


@pytest.fixture
def public_context():
    return prepared_session().session.context


@pytest.mark.parametrize(
    "case,code",
    [
        ("valid", "accepted"),
        ("wrong_hash", "packet_hash_mismatch"),
        ("secret_id", "unknown_evidence_id"),
        ("too_many_ids", "schema_constraint"),
        ("duplicate_ids", "duplicate_evidence_id"),
        ("scalar_ids", "schema_invalid_type"),
        ("extra_field", "schema_extra_field"),
        ("deep_json", "json_depth_limit"),
        ("http_error", "http_error"),
        ("invalid_wire", "envelope_json_syntax"),
    ],
)
def test_open_response_adapter_produces_exact_safe_diagnostic(public_context, case, code):
    result = observe_opened_response(public_context, invented_response(case, fixture()))
    assert result["diagnostic"]["code"] == code
    assert (result["selection"] is not None) is (case == "valid")
    serialized = json.dumps(result)
    for forbidden in (
        "ENTIRELY_INVENTED_SECRET",
        "ENTIRELY_INVENTED_UNKNOWN_NAME",
        "ENTIRELY_INVENTED_UNKNOWN_VALUE",
    ):
        assert forbidden not in serialized
    assert set(result) == {"selection", "diagnostic", "transport"}


def test_framing_failure_does_not_invoke_authority_or_read_body(public_context):
    class Response:
        status = 200

        def getheaders(self):
            return [("Content-Type", "application/octet-stream")]

        def read(self, size):
            raise AssertionError("framing_rejection_must_not_read_body")

    result = observe_opened_response(public_context, Response())
    assert result["selection"] is None
    assert result["diagnostic"]["authority_status"] == "not_invoked"
    assert result["diagnostic"]["code"] == "protocol_rejected"


@pytest.mark.parametrize("authorization", [None, *sorted(c.CONSUMED_AUTHORIZATIONS)])
def test_absent_or_consumed_authorization_stops_before_files_or_nonce(monkeypatch, authorization):
    monkeypatch.setattr(c, "AUTHORIZATION_ID", authorization)

    def forbidden(*args, **kwargs):
        raise AssertionError("no_authorization_must_mean_no_effect")

    monkeypatch.setattr(Path, "read_bytes", forbidden)
    monkeypatch.setattr(Path, "mkdir", forbidden)
    monkeypatch.setattr(os, "urandom", forbidden)
    monkeypatch.setattr(worker, "live_response", forbidden)
    with pytest.raises(ValueError, match="new_specific_authorization_required"):
        worker.AttemptSession(c.LEDGER, "a" * 32)
    with pytest.raises(ValueError, match="new_specific_authorization_required"):
        c.reserve(c.LEDGER, offline=False)
    with pytest.raises(ValueError, match="new_specific_authorization_required"):
        c.check_review({})


def test_new_plan_is_inert_and_body_unchanged():
    plan = c.verify_plan()
    assert c.AUTHORIZATION_ID is None
    assert plan["configuration"]["remote_execution_released"] is False
    assert plan["configuration"]["remaining_authorized_calls"] == 0
    assert len(c.payload_bytes()) == 8576 and c.digest(c.payload_bytes()) == c.prior.PAYLOAD_SHA256
    assert not c.LEDGER.exists() and not c.REVIEW.exists()


def test_authorization_constant_alone_cannot_activate_sealed_inert_plan(monkeypatch):
    monkeypatch.setattr(c, "AUTHORIZATION_ID", "ENTIRELY_INVENTED_NEW_AUTHORIZATION")
    with pytest.raises(ValueError, match="attempt_contract_changed"):
        c.verify_plan()


def test_pre_response_failure_is_closed_after_real_parent_dispatch(tmp_path):
    plan = c.verify_plan()
    folder, nonce = c.reserve(tmp_path / "invented-failure", offline=True)
    run_id = "a" * 32
    c.create(
        folder / "diagnostic-attempt-binding.json",
        c.binding(plan, None, run_id, time.monotonic(), 45, offline=True, owner_pid=os.getpid()),
    )
    source = """
import json, socket, sys
from pathlib import Path
from scripts import nim_diagnostic_attempt_worker_v1 as w
from orchestration.galaxies_orchestration import nim_http
job=json.loads(sys.stdin.buffer.read())
def forbidden(*a, **kw): raise AssertionError('offline_network_or_key_forbidden')
socket.create_connection=forbidden; socket.getaddrinfo=forbidden; socket.socket.connect=forbidden
nim_http.existing_key=forbidden
def failed_open(*a): raise RuntimeError('ENTIRELY_INVENTED_UNKNOWN_FAILURE')
w.invented_response=failed_open
s=w.AttemptSession(Path(job['folder']),job['run_id'],offline_case='valid')
s.authorize_message({'op':'authorize','nonce':job['nonce']})
s.handle({'op':'analyze','payload':{}})
for op in ('shap','comparables','context'): s.handle({'op':op})
reply=s.handle({'op':'select','request':w.c.canonical(s.public['request']).decode()})
assert (s.folder/'dispatch-v3.json').exists()
assert s.selection_accepted is False
print(json.dumps({'reply':reply,'transport':s.transport,'fake':True,'real_provider_verified':False}))
"""
    child = subprocess.run(
        [sys.executable, "-B", "-c", source],
        cwd=c.ROOT,
        input=c.canonical({"folder": str(folder), "run_id": run_id, "nonce": nonce.hex()}),
        capture_output=True,
        timeout=10,
        check=True,
        env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1", "OPENBLAS_NUM_THREADS": "1"},
    )
    result = json.loads(child.stdout)
    assert result["reply"]["selection"] is None
    assert result["reply"]["diagnostic"]["authority_status"] == "not_invoked"
    assert result["reply"]["diagnostic"]["code"] == "diagnostic_failed"
    assert result["transport"]["code"] == "request_failed_outcome_uncertain"
    assert result["real_provider_verified"] is False
    assert b"ENTIRELY_INVENTED_UNKNOWN_FAILURE" not in child.stdout and child.stderr == b""

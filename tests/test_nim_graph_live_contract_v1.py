"""New release guards and transport use only invented keys and local stubs."""

import json
import os
import subprocess
import sys
import time

import pytest

from orchestration.galaxies_orchestration import nim_graph_live_contract_v1 as c
from scripts import nim_graph_live_worker_v1 as worker
from scripts.nim_dispatch_fakes_v3 import INVENTED_KEY
from tests.test_nim_dispatch_v3 import no_remote_or_credentials  # noqa: F401


def review_fixture(plan):
    return {
        "protocol": c.PROTOCOL,
        "decision": "approved_for_one_synthetic_attempt",
        "plan_sha256": c.PLAN_SHA256,
        "configuration_sha256": plan["configuration_sha256"],
        "specific_remote_authorization_id": c.AUTHORIZATION_ID,
        "financial_evidence_id": c.FINANCIAL_ID,
        "reviewer_thread_id": c.SUPERVISOR,
        "execution_root_sha256": c.digest(str(c.ROOT.resolve()).encode()),
        "source_message_id": "ENTIRELY_INVENTED_OFFLINE_REVIEW",
    }


def test_exact_existing_body_and_new_specific_authorization():
    plan = c.verify_plan()
    assert len(c.payload_bytes()) == 8576
    assert (
        c.digest(c.payload_bytes())
        == "fd87bed20413c52bb7873d92da48c37d5f5f391a3fa9997e77177d073aaafcba"
    )
    assert (
        plan["configuration"]["specific_remote_authorization_id"]
        == "Sentinel_d3d52a72c3308191b76c892fed01f4aa"
    )
    assert plan["configuration"]["technical_review_required"] is True
    assert plan["configuration"]["max_spend_brl"] == 0
    from orchestration.galaxies_orchestration.nim_graph_contract_v1 import verify_plan

    assert verify_plan()["configuration"]["remote_execution_released"] is False


@pytest.mark.parametrize(
    "field",
    [
        "plan_sha256",
        "configuration_sha256",
        "specific_remote_authorization_id",
        "financial_evidence_id",
        "reviewer_thread_id",
        "execution_root_sha256",
    ],
)
def test_review_cannot_release_another_plan_authorization_or_checkout(tmp_path, monkeypatch, field):
    plan = c.verify_plan()
    value = review_fixture(plan)
    value[field] = "ENTIRELY_INVENTED_WRONG_BINDING"
    path = tmp_path / "review.json"
    c.create(path, value)
    monkeypatch.setattr(c, "REVIEW", path)
    with pytest.raises(ValueError, match="review_required"):
        c.check_review(plan)


def test_one_post_exact_body_key_header_only_and_no_transport_child(monkeypatch):
    calls = []

    class Connection:
        def __init__(self, *args, **kwargs):
            calls.append((args, kwargs))

        def set_debuglevel(self, value):
            assert value == 0

        def request(self, method, path, *, body, headers):
            calls.append((method, path, body, headers))

        def getresponse(self):
            return "ENTIRELY_INVENTED_RESPONSE_OBJECT"

        def close(self):
            pass

    monkeypatch.setattr(worker.http.client, "HTTPSConnection", Connection)
    connection, response = worker.live_response(INVENTED_KEY, timeout=7)
    connection.close()
    assert response == "ENTIRELY_INVENTED_RESPONSE_OBJECT"
    assert len(calls) == 2
    assert calls[0][0] == ("integrate.api.nvidia.com",)
    assert calls[0][1]["port"] == 443 and calls[0][1]["timeout"] == 7
    assert calls[0][1]["context"].check_hostname is True
    method, path, body, headers = calls[1]
    assert method == "POST" and path == "/v1/chat/completions"
    assert body == c.payload_bytes() and INVENTED_KEY.encode() not in body
    assert headers == {
        "Authorization": "Bearer " + INVENTED_KEY,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def test_changed_body_is_refused_before_socket(monkeypatch):
    monkeypatch.setattr(c, "payload_bytes", lambda: b"ENTIRELY_INVENTED_FORBIDDEN_CHANGED_BODY")

    def forbidden(*args, **kwargs):
        raise AssertionError("must_not_open_socket_for_changed_body")

    monkeypatch.setattr(worker.http.client, "HTTPSConnection", forbidden)
    with pytest.raises(ValueError, match="payload_changed_before_socket"):
        worker.live_response(INVENTED_KEY, timeout=7)


@pytest.mark.parametrize("tamper", [None, "nonce", "binding", "request"])
def test_real_parent_nonce_guard_precedes_getter_with_explicit_child_stubs(tmp_path, tamper):
    plan = c.verify_plan()
    review = tmp_path / "review.json"
    c.create(review, review_fixture(plan))
    review_hash = c.digest(review.read_bytes())
    folder, nonce = c.reserve(tmp_path / "invented-release", offline=False)
    run_id = "a" * 32
    bound = c.binding(
        plan, review_hash, run_id, time.monotonic(), 45, offline=False, owner_pid=os.getpid()
    )
    if tamper == "binding":
        bound["specific_remote_authorization_id"] = "ENTIRELY_INVENTED_WRONG_BINDING"
    c.create(folder / "live-graph-binding.json", bound)
    # Actual direct subprocess relationship: no getpid/getppid monkeypatch.
    source = """
import json, socket, sys
from pathlib import Path
from orchestration.galaxies_orchestration import nim_graph_live_contract_v1 as c
from scripts import nim_graph_live_worker_v1 as w
from orchestration.galaxies_orchestration import nim_http
job=json.loads(sys.stdin.buffer.read())
c.LEDGER=Path(job['folder']); c.REVIEW=Path(job['review'])
calls=[]
def forbidden(*a, **kw):
    raise AssertionError('offline_stub_must_not_open_network')
socket.socket.connect=forbidden; socket.create_connection=forbidden
def invented_getter():
    assert (c.LEDGER/'dispatch-v3.json').exists()
    calls.append(True)
    return 'entirely-invented-test-key-00000000'
nim_http.existing_key=invented_getter
class InventedConnection:
    def close(self): pass
def stub_response(key, *, timeout):
    assert key.startswith('entirely-invented')
    return InventedConnection(), w.fake_response('valid', w.contract.configuration()['packet_sha256'])
w.live_response=stub_response
try:
    session=w.LiveBridge(c.LEDGER, job['run_id'])
    session.authorize_message({'op':'authorize','nonce':job['nonce']})
    session.handle({'op':'analyze','payload':{}})
    for op in ('shap','comparables','context'): session.handle({'op':op})
    request=json.loads(json.dumps(session.public['request']))
    if job['tamper']=='request': request['packet_sha256']='0'*64
    reply=session.handle({'op':'select','request':c.canonical(request).decode()})
    assert reply['selection'] is not None
    try:
        session.handle({'op':'select','request':'{}'})
        raise AssertionError('repeat_must_fail')
    except ValueError: pass
except ValueError:
    pass
# This is a getter-order test with a stub, never provider verification.
print(json.dumps({'getter_calls':len(calls),'dispatch':(c.LEDGER/'dispatch-v3.json').exists(),
                  'real_provider_verified':False,'network_stub':True}))
"""
    child = subprocess.run(
        [sys.executable, "-B", "-c", source],
        cwd=c.ROOT,
        input=c.canonical(
            {
                "folder": str(folder),
                "review": str(review),
                "run_id": run_id,
                "tamper": tamper,
                "nonce": (b"x" * 32 if tamper == "nonce" else nonce).hex(),
            }
        ),
        capture_output=True,
        timeout=10,
        check=True,
        env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1", "OPENBLAS_NUM_THREADS": "1"},
    )
    value = json.loads(child.stdout)
    assert value == {
        "getter_calls": int(tamper is None),
        "dispatch": tamper is None,
        "real_provider_verified": False,
        "network_stub": True,
    }
    assert child.stderr == b""

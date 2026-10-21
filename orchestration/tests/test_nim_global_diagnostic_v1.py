"""Fixed global-payload identity/gates and real fake worker/graph path only."""

import asyncio
import http.client
import json
import os
import socket
import time
from pathlib import Path

import pytest

from galaxies_orchestration import nim_global_diagnostic_contract_v1 as c
from galaxies_orchestration import nim_global_diagnostic_v1 as release
from galaxies_orchestration.nim_graph_contract_v1 import fixture

UNKNOWN = "ENTIRELY_INVENTED_SECRET"
INVENTED_ID = "Sentinel_00000000000000000000000000000002"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("offline_global_diagnostic_forbids_network")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "connect_ex", forbidden)
    monkeypatch.setattr(http.client.HTTPSConnection, "request", forbidden)


@pytest.fixture
def root_python():
    value = os.environ.get("GALAXIES_ROOT_PYTHON")
    if not value:
        pytest.skip("Explicit existing ROOT interpreter required")
    return Path(value)


@pytest.mark.parametrize("case", sorted(c.FAKE_CASES))
def test_global_opening_real_worker_graph_and_persistence_once(
    root_python, tmp_path, monkeypatch, case
):
    original = release.ReleasedProbeWorker
    counts = {"created": 0, "select": 0, "reaped": 0}

    class Counted(original):
        async def __aenter__(self):
            counts["created"] += 1
            return await super().__aenter__()

        async def request(self, message):
            counts["select"] += int(message["op"] == "select")
            return await super().request(message)

        async def __aexit__(self, *args):
            await super().__aexit__(*args)
            assert self.process.returncode is not None
            counts["reaped"] += 1

    monkeypatch.setattr(release, "ReleasedProbeWorker", Counted)
    folder = tmp_path / ("invented-global-" + case)
    receipt = asyncio.run(release.simulate(root_python, case, folder, timeout=5))
    assert receipt["outcome"] == "observed"
    assert receipt["worker_cleanup_confirmed"] is True
    assert receipt["real_http_requests"] == 0
    assert receipt["specific_remote_authorization_id"] is None
    assert receipt["authorization_receipt_sha256"] is None
    assert counts == {"created": 1, "select": 1, "reaped": 1}
    result = receipt["result"]
    provider, diagnostic = result["current_provider"], result["selection_diagnostic"]
    assert provider["real_provider_verified"] is False
    assert provider["real_http_requests"] == 0
    assert provider["selector_invocations"] == 1
    assert result["legacy_result"]["analysis"] == fixture()["data"]["report"]
    assert result["legacy_result"]["evidence_packet"] == fixture()["request"]["packet"]
    assert result["legacy_result"]["orchestration"]["stategraph_executed"] is True
    assert result["legacy_result"]["orchestration"]["explainer_subgraph_executed"] is True
    assert UNKNOWN not in json.dumps(receipt)
    accepted = case in {"valid", "adapter_invalid_200"}
    assert provider["root_selection_accepted"] is accepted
    assert provider["root_render_accepted"] is accepted
    assert provider["transport"]["code"] == (
        "selection_accepted"
        if accepted
        else "selection_rejected"
        if case == "twentyone_ids"
        else "http_error"
    )
    assert diagnostic["authority_status"] == (
        "accepted" if accepted else "rejected" if case == "twentyone_ids" else "not_invoked"
    )
    if case == "twentyone_ids":
        captured = json.loads(
            (c.ROOT / "docs/evidence/issue-5-nim-worker-diagnostic-v3-resultados.json").read_bytes()
        )
        assert diagnostic == captured["selection_diagnostic"]
        assert diagnostic["cardinality"] == 21
        assert diagnostic["classifier_parity"] is True
    if case.startswith("adapter_invalid_"):
        assert result["http_error_metadata"] is None
        assert result["http_error_metadata_state"] == "invalid_ipc_metadata"
    elif case == "http_503":
        assert result["http_error_metadata_state"] == "validated"
        assert result["http_error_metadata"]["http_status"] == 503
        assert result["http_error_metadata"]["body_read"] is False
        assert result["http_error_metadata"]["request_id_state"] == "captured"
    else:
        assert result["http_error_metadata"] is None
        assert result["http_error_metadata_state"] == "not_applicable"
    reservation = json.loads((folder / "reservation-v3.json").read_bytes())
    assert reservation["parent_pid"] == os.getpid()
    assert reservation["plan_sha256"] == c.PLAN_SHA256
    assert json.loads((folder / "dispatch-v3.json").read_bytes()) == {
        "state": "consumed_before_transport",
        "offline_simulation_only": True,
    }
    assert json.loads((folder / c.RESULT_NAME).read_bytes()) == receipt
    with pytest.raises(FileExistsError):
        asyncio.run(release.simulate(root_python, case, folder, timeout=5))
    assert counts["created"] == 1


def authorization(plan):
    return c.receipt_binding(plan) | {
        "decision": "authorized_for_one_synthetic_attempt",
        "authorized_calls": 1,
        "recorded_by_thread_id": c.original.SUPERVISOR,
        "specific_remote_authorization_id": INVENTED_ID,
    }


def review(plan):
    return c.receipt_binding(plan) | {
        "decision": "approved_for_one_synthetic_attempt",
        "specific_remote_authorization_id": INVENTED_ID,
        "authorization_receipt_sha256": "a" * 64,
        "reviewer_thread_id": c.original.SUPERVISOR,
        "source_message_id": "ENTIRELY_INVENTED_REVIEW",
    }


def deny_effects(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("receipt_gate_must_precede_effects")

    monkeypatch.setattr(c, "reserve", forbidden)
    monkeypatch.setattr(os, "urandom", forbidden)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", forbidden)


@pytest.mark.parametrize("kind", ["missing", "consumed", "generic", "payload", "root", "plan"])
def test_authorization_refusal_precedes_nonce_reservation_spawn_getter_socket(
    tmp_path, monkeypatch, kind
):
    plan = c.verify_plan()
    path = tmp_path / "invented-authorization.json"
    monkeypatch.setattr(c, "AUTHORIZATION", path)
    value = authorization(plan)
    if kind == "consumed":
        value["specific_remote_authorization_id"] = "Sentinel_829d1d2255248191b6b86d3e3924cf72"
    elif kind == "generic":
        value["specific_remote_authorization_id"] = "Sentinel_c2b13386e42c8191b98d390fffadaf03"
    elif kind == "payload":
        value["http_payload_sha256"] = c.base.original.PAYLOAD_SHA256
    elif kind == "root":
        value["execution_root_sha256"] = "0" * 64
    elif kind == "plan":
        value["plan_sha256"] = c.base.PLAN_SHA256
    if kind != "missing":
        path.write_bytes(c.canonical(value))
    deny_effects(monkeypatch)
    with pytest.raises((ValueError, FileNotFoundError)):
        asyncio.run(release.execute_remote("INVENTED_NOT_OPENED"))
    assert not c.LEDGER.exists()


@pytest.mark.parametrize("kind", ["missing", "root", "authorization_hash", "payload"])
def test_review_missing_or_changed_refused_before_effects(tmp_path, monkeypatch, kind):
    plan = c.verify_plan()
    path = tmp_path / "invented-review.json"
    monkeypatch.setattr(c, "authorization_receipt", lambda plan: (INVENTED_ID, "a" * 64))
    monkeypatch.setattr(c, "REVIEW", path)
    value = review(plan)
    if kind == "root":
        value["execution_root_sha256"] = "0" * 64
    elif kind == "authorization_hash":
        value["authorization_receipt_sha256"] = "b" * 64
    elif kind == "payload":
        value["http_payload_sha256"] = c.base.original.PAYLOAD_SHA256
    if kind != "missing":
        path.write_bytes(c.canonical(value))
    deny_effects(monkeypatch)
    with pytest.raises((ValueError, FileNotFoundError)):
        asyncio.run(release.execute_remote("INVENTED_NOT_OPENED"))
    assert not c.LEDGER.exists()


@pytest.mark.parametrize("old", sorted(c.CONSUMED_AUTHORIZATIONS))
def test_all_known_consumed_financial_and_generic_ids_refused(old):
    plan = c.verify_plan()
    with pytest.raises(ValueError, match="^global_diagnostic_specific_authorization_required$"):
        c.validate_authorization(
            authorization(plan) | {"specific_remote_authorization_id": old}, plan
        )


def test_new_configuration_body_and_fake_namespace_are_closed(tmp_path):
    plan = c.verify_plan()
    config = plan["configuration"]
    assert c.AUTHORIZATION_ID is None
    assert config["remaining_authorized_calls"] == 0
    assert config["remote_execution_released"] is False
    assert config["max_spend_brl"] == 0
    assert config["maximum_graph_work_seconds"] == 43
    assert config["maximum_cleanup_seconds"] == 2
    assert len(c.payload_bytes()) == 10065
    assert c.digest(c.payload_bytes()) == c.PAYLOAD_SHA256
    for name in (
        "issue-5-nim-worker-diagnostic-v3",
        "issue-5-nim-global-diagnostic-v1",
        "issue-5-nim-global-diagnostic-v1-review",
        "issue-5-nim-global-diagnostic-v1-authorization",
    ):
        with pytest.raises(ValueError):
            c.simulation_folder(tmp_path / name)
    target = tmp_path / "invented-directory"
    target.mkdir()
    link = tmp_path / "invented-link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError):
        c.simulation_folder(link / "invented-child")


def test_owned_worker_refuses_select_reentry_after_global_dispatch(root_python, tmp_path):
    async def run():
        plan = c.verify_plan()
        folder, nonce = c.reserve(tmp_path / "invented-reentry", offline=True)
        started, run_id = time.monotonic(), "2" * 32
        bound = c.binding(plan, None, run_id, started, 5, offline=True, owner_pid=os.getpid())
        c.create(folder / c.BINDING_NAME, bound)
        worker = release.ReleasedProbeWorker(
            root_python,
            c.ROOT,
            ("--run-id", run_id, "--offline-case", "valid", "--simulation-ledger", str(folder)),
            module="scripts.nim_global_diagnostic_worker_v1",
            timeout=3.75,
            drain_timeout=0.625,
            wait_timeout=0.625,
            cleanup_deadline=asyncio.get_running_loop().time() + 5,
        )
        async with worker:
            await worker.request({"op": "authorize", "nonce": nonce.hex()})
            await worker.request({"op": "analyze", "payload": {}})
            for op in ("shap", "comparables", "context"):
                await worker.request({"op": op})
            message = {"op": "select", "request": c.canonical(fixture()["request"]).decode()}
            assert (await worker.request(message))["selection"] is not None
            marker = (folder / "dispatch-v3.json").read_bytes()
            with pytest.raises(ValueError, match="^worker_failed$"):
                await worker.request(message)
            assert (folder / "dispatch-v3.json").read_bytes() == marker
        assert worker.cleanup_confirmed and worker.process.returncode is not None

    asyncio.run(run())

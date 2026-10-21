"""New worker/IPC/graph bindings only, with real Python children and invented responses."""

import asyncio
import http.client
import json
import os
import socket
import time
from pathlib import Path

import pytest

from galaxies_orchestration import nim_worker_diagnostic_contract_v3 as c
from galaxies_orchestration import nim_worker_diagnostic_v3 as release
from galaxies_orchestration.nim_graph_contract_v1 import fixture

UNKNOWN = "ENTIRELY_INVENTED_SECRET"
INVENTED_AUTHORIZATION = "Sentinel_00000000000000000000000000000001"


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("offline_worker_diagnostic_forbids_network")

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


@pytest.fixture
def counted_worker(monkeypatch):
    counts = {"created": 0, "authorize": 0, "select": 0, "proof": 0, "reaped": 0}
    original = release.ReleasedProbeWorker

    class Counted(original):
        async def __aenter__(self):
            counts["created"] += 1
            return await super().__aenter__()

        async def request(self, message):
            if message["op"] in counts:
                counts[message["op"]] += 1
            return await super().request(message)

        async def __aexit__(self, *args):
            await super().__aexit__(*args)
            assert self.process.returncode is not None
            counts["reaped"] += 1

    monkeypatch.setattr(release, "ReleasedProbeWorker", Counted)
    return counts


@pytest.mark.parametrize(
    "case", sorted(case for case in c.FAKE_CASES if not case.startswith("adapter_invalid_"))
)
def test_real_fake_worker_graph_persistence_and_single_consumption(
    root_python, tmp_path, counted_worker, case
):
    folder = tmp_path / ("invented-" + case)
    receipt = asyncio.run(release.simulate(root_python, case, folder, timeout=5))
    assert receipt["outcome"] == "observed"
    assert receipt["worker_cleanup_confirmed"] is True
    assert receipt["worker_cleanup_code"] == "confirmed"
    assert receipt["real_http_requests"] == 0
    assert receipt["specific_remote_authorization_id"] is None
    assert receipt["authorization_receipt_sha256"] is None
    assert counted_worker == {"created": 1, "authorize": 1, "select": 1, "proof": 1, "reaped": 1}
    result = receipt["result"]
    provider = result["current_provider"]
    legacy = result["legacy_result"]
    assert provider["real_provider_verified"] is False
    assert provider["real_http_requests"] == 0
    assert provider["selector_invocations"] == 1
    assert legacy["analysis"] == fixture()["data"]["report"]
    assert legacy["evidence_packet"] == fixture()["request"]["packet"]
    assert legacy["orchestration"]["real_provider_verified"] is False
    assert legacy["orchestration"]["stategraph_executed"] is True
    assert legacy["orchestration"]["explainer_subgraph_executed"] is True
    assert UNKNOWN not in json.dumps(receipt)
    accepted = case in {"valid", "wire_at_limit", "headers_at_limit"}
    assert provider["root_selection_accepted"] is accepted
    assert provider["root_render_accepted"] is accepted
    diagnostic = result["selection_diagnostic"]
    if case.startswith("http_"):
        status = int(case.split("_")[1])
        assert provider["transport"] == {
            "code": "http_error",
            "http_status": status,
            "wire_bytes": None,
            "completion_tokens": None,
        }
        assert diagnostic["authority_status"] == "not_invoked"
        assert diagnostic["code"] == "http_error"
        assert result["http_error_metadata_state"] == "validated"
        metadata = result["http_error_metadata"]
        assert metadata["http_status"] == status
        assert metadata["body_read"] is False
        state = next(
            (suffix for suffix in ("missing", "invalid", "duplicate") if case.endswith(suffix)),
            "unavailable"
            if case.endswith("exception")
            else "invalid"
            if case.endswith("long")
            else "captured",
        )
        assert metadata["request_id_state"] == state
        assert (
            metadata["request_id"] is None
            if state != "captured"
            else metadata["request_id"] == "12345678-1234-1234-1234-123456789abc"
        )
        if case.endswith("long"):
            assert metadata["framing_state"] == "invalid"
    else:
        assert result["http_error_metadata"] is None
        assert result["http_error_metadata_state"] == "not_applicable"
        assert (diagnostic["authority_status"] == "accepted") is accepted
        if case == "wire_at_limit":
            assert provider["transport"]["wire_bytes"] == 16384
        if case == "wire_limit":
            assert provider["transport"]["code"] == "wire_byte_limit"
        if case == "headers_excess":
            assert provider["transport"]["code"] == "protocol_rejected"
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
    assert counted_worker["created"] == 1
    assert len(list(folder.glob("dispatch*.json"))) == 1


@pytest.mark.parametrize("corruption", ["extra", "uuid", "status", "unexpected_200"])
def test_corrupt_sidecar_ipc_is_discarded_without_changing_authority(
    root_python, tmp_path, monkeypatch, corruption
):
    original = release.ReleasedProbeWorker

    class Corrupt(original):
        async def request(self, message):
            reply = await super().request(message)
            if message["op"] == "select":
                metadata = reply["http_error_metadata"]
                if corruption == "unexpected_200":
                    metadata = {"unknown": UNKNOWN}
                elif corruption == "extra":
                    metadata["unknown"] = UNKNOWN
                elif corruption == "uuid":
                    metadata["request_id"] = UNKNOWN
                else:
                    metadata["http_status"] = 429
                reply["http_error_metadata"] = metadata
            return reply

    monkeypatch.setattr(release, "ReleasedProbeWorker", Corrupt)
    case = "valid" if corruption == "unexpected_200" else "http_503"
    receipt = asyncio.run(
        release.simulate(root_python, case, tmp_path / "invented-corrupt-ipc", timeout=5)
    )
    assert receipt["outcome"] == "observed"
    result = receipt["result"]
    assert result["http_error_metadata"] is None
    assert result["http_error_metadata_state"] == "invalid_ipc_metadata"
    assert result["selection_diagnostic"]["authority_status"] == (
        "accepted" if case == "valid" else "not_invoked"
    )
    assert result["current_provider"]["transport"]["code"] == (
        "selection_accepted" if case == "valid" else "http_error"
    )
    assert result["current_provider"]["real_provider_verified"] is False
    assert UNKNOWN not in json.dumps(receipt)


@pytest.mark.parametrize("status", [200, 503])
def test_invalid_adapter_sidecar_is_sanitized_in_child_without_changing_authority(
    root_python, tmp_path, status
):
    receipt = asyncio.run(
        release.simulate(
            root_python,
            "adapter_invalid_" + str(status),
            tmp_path / "invented-adapter-fault",
            timeout=5,
        )
    )
    assert receipt["outcome"] == "observed"
    assert receipt["worker_cleanup_confirmed"] is True
    assert receipt["real_http_requests"] == 0
    result = receipt["result"]
    assert result["http_error_metadata"] is None
    assert result["http_error_metadata_state"] == "invalid_ipc_metadata"
    assert result["current_provider"]["transport"]["http_status"] == status
    assert result["current_provider"]["transport"]["code"] == (
        "selection_accepted" if status == 200 else "http_error"
    )
    assert result["selection_diagnostic"]["authority_status"] == (
        "accepted" if status == 200 else "not_invoked"
    )
    assert result["current_provider"]["root_selection_accepted"] is (status == 200)
    assert result["current_provider"]["real_provider_verified"] is False
    assert result["legacy_result"]["analysis"] == fixture()["data"]["report"]
    assert result["legacy_result"]["evidence_packet"] == fixture()["request"]["packet"]
    assert UNKNOWN not in json.dumps(receipt)


def invented_authorization(plan):
    return c.receipt_binding(plan) | {
        "decision": "authorized_for_one_synthetic_attempt",
        "authorized_calls": 1,
        "recorded_by_thread_id": c.original.SUPERVISOR,
        "specific_remote_authorization_id": INVENTED_AUTHORIZATION,
    }


def invented_review(plan):
    return c.receipt_binding(plan) | {
        "decision": "approved_for_one_synthetic_attempt",
        "specific_remote_authorization_id": INVENTED_AUTHORIZATION,
        "authorization_receipt_sha256": "a" * 64,
        "reviewer_thread_id": c.original.SUPERVISOR,
        "source_message_id": "ENTIRELY_INVENTED_REVIEW",
    }


def test_fixed_sources_body_external_authority_and_review_binding():
    plan = c.verify_plan()
    assert c.AUTHORIZATION_ID is None
    assert plan["configuration"]["remaining_authorized_calls"] == 0
    assert plan["configuration"]["remote_execution_released"] is False
    assert len(c.payload_bytes()) == 8576
    assert c.digest(c.payload_bytes()) == c.original.PAYLOAD_SHA256
    assert c.validate_authorization(invented_authorization(plan), plan) == INVENTED_AUTHORIZATION
    review = invented_review(plan)
    assert c.validate_review(review, plan, INVENTED_AUTHORIZATION, "a" * 64) is review


@pytest.mark.parametrize("authorization", sorted(c.CONSUMED_AUTHORIZATIONS))
def test_all_consumed_or_non_post_ids_are_refused(authorization):
    plan = c.verify_plan()
    value = invented_authorization(plan) | {"specific_remote_authorization_id": authorization}
    with pytest.raises(ValueError, match="^worker_diagnostic_specific_authorization_required$"):
        c.validate_authorization(value, plan)


@pytest.mark.parametrize(
    "field",
    [
        "plan_sha256",
        "configuration_sha256",
        "execution_root_sha256",
        "http_payload_sha256",
        "financial_evidence_id",
        "recorded_by_thread_id",
        "authorized_calls",
    ],
)
def test_authorization_binding_mismatch_refused(field):
    plan = c.verify_plan()
    value = invented_authorization(plan) | {field: UNKNOWN}
    with pytest.raises(ValueError, match="^worker_diagnostic_specific_authorization_required$"):
        c.validate_authorization(value, plan)


@pytest.mark.parametrize(
    "field",
    [
        "plan_sha256",
        "configuration_sha256",
        "execution_root_sha256",
        "http_payload_sha256",
        "financial_evidence_id",
        "specific_remote_authorization_id",
        "authorization_receipt_sha256",
        "reviewer_thread_id",
    ],
)
def test_review_is_bound_to_authorization_plan_checkout_input_and_finance(field):
    plan = c.verify_plan()
    value = invented_review(plan) | {field: UNKNOWN}
    with pytest.raises(ValueError, match="^worker_diagnostic_technical_review_required$"):
        c.validate_review(value, plan, INVENTED_AUTHORIZATION, "a" * 64)


@pytest.mark.parametrize("missing", ["authorization", "review"])
def test_missing_receipts_stop_before_nonce_reservation_spawn_or_transport(
    tmp_path, monkeypatch, missing
):
    def forbidden(*args, **kwargs):
        raise AssertionError("missing_receipt_must_precede_all_effects")

    monkeypatch.setattr(c, "AUTHORIZATION", tmp_path / "invented-missing-authorization.json")
    monkeypatch.setattr(c, "REVIEW", tmp_path / "invented-missing-review.json")
    if missing == "review":
        monkeypatch.setattr(
            c, "authorization_receipt", lambda plan: (INVENTED_AUTHORIZATION, "a" * 64)
        )
    monkeypatch.setattr(c, "reserve", forbidden)
    monkeypatch.setattr(os, "urandom", forbidden)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", forbidden)
    with pytest.raises(FileNotFoundError):
        asyncio.run(release.execute_remote("INVENTED_NOT_OPENED"))
    assert not list(tmp_path.iterdir())


def test_fake_namespaces_and_symlinks_cannot_target_any_real_receipts(tmp_path):
    for name in (
        "issue-5-nim-old",
        "issue-5-nim-worker-diagnostic-v3",
        "issue-5-nim-worker-diagnostic-v3-review",
        "issue-5-nim-worker-diagnostic-v3-authorization",
    ):
        with pytest.raises(ValueError):
            c.simulation_folder(tmp_path / "invented-other-checkout" / name)
    target = tmp_path / "invented-target"
    target.mkdir()
    link = tmp_path / "invented-symlink"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError):
        c.simulation_folder(link / "invented-child")
    with pytest.raises(ValueError):
        c.private_json(link / "invented-missing.json")


def test_binding_uses_same_fractional_deadline_representation(tmp_path):
    folder = tmp_path / "invented-binding"
    folder.mkdir()
    plan = c.verify_plan()
    bound = c.binding(plan, None, "INVENTED", 100000.123, 0.2, offline=True, owner_pid=os.getpid())
    c.create(folder / c.BINDING_NAME, bound)
    assert (
        c.check_binding(folder, plan, None, "INVENTED", offline=True, owner_pid=os.getpid())
        == bound
    )


def test_actual_worker_refuses_select_reentry_after_one_dispatch(root_python, tmp_path):
    async def run():
        plan = c.verify_plan()
        folder, nonce = c.reserve(tmp_path / "invented-select-reentry", offline=True)
        started = time.monotonic()
        run_id = "1" * 32
        bound = c.binding(plan, None, run_id, started, 5, offline=True, owner_pid=os.getpid())
        c.create(folder / c.BINDING_NAME, bound)
        worker = release.ReleasedProbeWorker(
            root_python,
            c.ROOT,
            ("--run-id", run_id, "--offline-case", "valid", "--simulation-ledger", str(folder)),
            module="scripts.nim_worker_diagnostic_v3",
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
            before = (folder / "dispatch-v3.json").read_bytes()
            with pytest.raises(ValueError, match="^worker_failed$"):
                await worker.request(message)
            assert (folder / "dispatch-v3.json").read_bytes() == before
        assert worker.cleanup_confirmed is True
        assert worker.process.returncode is not None

    asyncio.run(run())

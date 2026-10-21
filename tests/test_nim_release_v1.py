"""Lightweight release checks, invented keys and fake transports only."""

import asyncio
import json
import os

import pytest

from scripts import nim_release_contract_v1 as contract
from scripts import nim_release_v1 as release
from scripts import nim_release_worker_v1 as worker
from scripts.nim_dispatch_fakes_v3 import INVENTED_KEY, INVENTED_SECRET, connection_factory
from scripts.nim_dispatch_ledger_v3 import create, reserve
from scripts.nim_observed_http_worker_v3 import exchange
from tests.test_nim_dispatch_v3 import no_remote_or_credentials  # noqa: F401


def review_fixture(plan):
    return {
        "protocol": contract.PROTOCOL,
        "decision": "approved_for_one_synthetic_attempt",
        "plan_sha256": contract.PLAN_SHA256,
        "configuration_sha256": plan["configuration_sha256"],
        "financial_evidence_id": contract.EVIDENCE_ID,
        "reviewer_thread_id": contract.SUPERVISOR,
        "source_message_id": "ENTIRELY_INVENTED_OFFLINE_REVIEW",
        "execution_root_sha256": contract.digest(str(contract.ROOT.resolve()).encode()),
    }


def test_finance_is_specific_user_fact_and_old_v3_remains_locked():
    plan = contract.verify_plan()
    assert (
        plan["financial_evidence"]["source_message_id"]
        == "Sentinel_e945b14459008191a932c869a4216aef"
    )
    assert plan["configuration"]["max_spend_brl"] == 0
    from scripts.nim_dispatch_plan_v3 import verify_plan
    from scripts.nim_dispatch_seal_v3 import REMOTE_PLAN_SHA256

    assert verify_plan()["remote_execution_released"] is False and REMOTE_PLAN_SHA256 is None


def test_release_cannot_read_key_or_reserve_from_other_checkout(tmp_path, monkeypatch):
    plan = contract.verify_plan()
    review = review_fixture(plan)
    review["execution_root_sha256"] = contract.digest(str(tmp_path / "other-checkout").encode())
    path = tmp_path / "review-for-other-checkout.json"
    create(path, review)
    monkeypatch.setattr(contract, "REVIEW", path)
    monkeypatch.setattr(release, "LEDGER", tmp_path / "never-reserved")
    with pytest.raises(ValueError, match="review_checkout_mismatch"):
        asyncio.run(release.execute_once())
    assert not (tmp_path / "never-reserved").exists()


def test_review_required_before_consumption_even_in_integrated_context(tmp_path, monkeypatch):
    monkeypatch.setattr(release, "LEDGER", tmp_path / "never-reserved")
    monkeypatch.setattr(contract, "REVIEW", tmp_path / "missing-review.json")
    with pytest.raises(FileNotFoundError):
        asyncio.run(release.execute_once())
    assert not (tmp_path / "never-reserved").exists()


@pytest.mark.parametrize("tamper", ["financial_evidence", "endpoint"])
def test_new_plan_contract_is_checked_before_reservation(tmp_path, monkeypatch, tamper):
    plan = contract.verify_plan()
    if tamper == "financial_evidence":
        plan["financial_evidence"]["source_message_id"] = "ENTIRELY_INVENTED_OTHER_ACCOUNT_FACT"
    else:
        plan["configuration"]["endpoint"] = "https://entirely-invented.invalid/"
    path = tmp_path / "tampered-plan.json"
    path.write_bytes(contract.canonical(plan))
    monkeypatch.setattr(contract, "PLAN", path)
    monkeypatch.setattr(contract, "PLAN_SHA256", contract.digest(path.read_bytes()))
    with pytest.raises(ValueError, match="contract_mismatch"):
        asyncio.run(release.simulate("valid", tmp_path / "never-reserved"))
    assert not (tmp_path / "never-reserved").exists()


@pytest.mark.parametrize(
    "field", ["plan_sha256", "configuration_sha256", "financial_evidence_id", "reviewer_thread_id"]
)
def test_review_cannot_authorize_other_plan_or_account_fact(tmp_path, monkeypatch, field):
    plan = contract.verify_plan()
    value = review_fixture(plan)
    value[field] = "ENTIRELY_INVENTED_WRONG_BINDING"
    path = tmp_path / "review.json"
    create(path, value)
    monkeypatch.setattr(contract, "REVIEW", path)
    with pytest.raises(ValueError, match="technical_review_required"):
        contract.check_review(plan)


@pytest.mark.parametrize(
    "case",
    [
        "valid",
        "duplicate_ids",
        "redirect",
        "http_error",
        "http_429",
        "http_503",
        "send_failure",
        "secret_id",
    ],
)
def test_new_release_pipeline_consumes_once_with_safe_ipc(tmp_path, case):
    folder = tmp_path / case
    result = asyncio.run(release.simulate(case, folder))
    assert result["outcome"] == "observed"
    assert result["summary"]["selection_validated"] is (case == "valid")
    assert result["offline_simulation_only"] is True and result["real_requests"] == 0
    assert result["measured_cost_brl"] is None
    assert result["financial_evidence_id"] == contract.EVIDENCE_ID
    assert (folder / "dispatch-v3.json").exists()
    with pytest.raises(FileExistsError):
        asyncio.run(release.simulate(case, folder))
    retained = b"".join(path.read_bytes() for path in folder.iterdir())
    assert INVENTED_SECRET.encode() not in retained and INVENTED_KEY.encode() not in retained


def test_simulations_cannot_consume_any_protected_ledger():
    for folder in (
        contract.LEDGER,
        contract.OFFLINE_V3_LEDGER,
        contract.REVIEW.parent,
        contract.SEALED_V1_NAMESPACE,
    ):
        with pytest.raises(ValueError, match="protected_ledger"):
            asyncio.run(release.simulate("valid", folder))
        with pytest.raises(ValueError, match="protected_ledger"):
            asyncio.run(release.simulate("valid", folder / "invented-child"))


def test_simulation_does_not_resolve_away_symlink_protection(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink_simulation"):
        asyncio.run(release.simulate("valid", alias / "never-created"))
    assert list(target.iterdir()) == []


@pytest.mark.parametrize("tamper", [None, "nonce", "binding"])
def test_credential_getter_runs_only_after_new_binding_and_durable_dispatch(
    tmp_path, monkeypatch, tamper
):
    # Exercise the remote branch with explicit local substitutions; never a real
    # credential/socket, and no source/root redirect in production configuration.
    from orchestration.galaxies_orchestration import nim_http

    plan = contract.verify_plan()
    review_path = tmp_path / "review.json"
    create(review_path, review_fixture(plan))
    monkeypatch.setattr(contract, "REVIEW", review_path)
    review_hash = contract.check_review(plan)
    folder, nonce = reserve(tmp_path / "invented-release", contract.PLAN_SHA256, offline=False)
    binding = {
        "protocol": contract.PROTOCOL,
        "plan_sha256": contract.PLAN_SHA256,
        "configuration_sha256": plan["configuration_sha256"],
        "financial_evidence_id": contract.EVIDENCE_ID,
        "technical_review_sha256": "0" * 64 if tamper == "binding" else review_hash,
        "offline_simulation_only": False,
    }
    create(folder / "release-binding.json", binding)
    monkeypatch.setattr(worker, "LEDGER", folder)
    monkeypatch.setattr(os, "getppid", os.getpid)
    calls = []

    def invented_getter():
        assert (folder / "dispatch-v3.json").exists()
        calls.append("invented_key_after_durable_dispatch")
        return INVENTED_KEY

    def fake_exchange(key, *, factory, timeout):
        return exchange(key, factory=connection_factory("valid"), timeout=timeout)

    monkeypatch.setattr(nim_http, "existing_key", invented_getter)
    monkeypatch.setattr(worker, "exchange", fake_exchange)
    if tamper:
        with pytest.raises(ValueError):
            worker.released(b"x" * 32 if tamper == "nonce" else nonce, remaining=45)
        assert calls == [] and not (folder / "dispatch-v3.json").exists()
    else:
        assert worker.released(nonce, remaining=45)["selection_validated"] is True
        assert calls == ["invented_key_after_durable_dispatch"]
        with pytest.raises(FileExistsError):
            worker.released(nonce, remaining=45)
        assert len(calls) == 1


def test_cancelled_new_release_stays_consumed(tmp_path):
    async def exercise():
        entered = asyncio.Event()

        async def runner(*args, **kwargs):
            entered.set()
            await asyncio.Event().wait()

        task = asyncio.create_task(release.simulate("valid", tmp_path / "cancelled", runner=runner))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(exercise())
    receipt = json.loads((tmp_path / "cancelled/result-v3.json").read_bytes())
    assert receipt["outcome"] == "cancelled_outcome_uncertain"
    with pytest.raises(FileExistsError):
        asyncio.run(release.simulate("valid", tmp_path / "cancelled"))

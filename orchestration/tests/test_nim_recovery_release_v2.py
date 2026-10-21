"""New identity/review/consumption only; shared infrastructure is not re-tested."""

import asyncio
import json
import os
from pathlib import Path

import pytest

from galaxies_orchestration import nim_recovery_release_contract_v2 as c
from galaxies_orchestration import nim_recovery_release_v2 as release


@pytest.fixture
def root_python():
    value = os.environ.get("GALAXIES_ROOT_PYTHON")
    if not value:
        pytest.skip("Explicit existing root interpreter required")
    return Path(value)


def test_new_authority_is_bound_to_inert_proposal_and_fixed_body():
    plan = c.verify_plan()
    assert c.AUTHORIZATION_ID == "Sentinel_102f607fc6d08191a1119f9a48149a34"
    assert c.proposal.AUTHORIZATION_ID is None
    assert c.proposal.previous.AUTHORIZATION_ID in c.CONSUMED_AUTHORIZATIONS
    assert plan["configuration"]["recovery_proposal_plan_sha256"] == (
        "c0b16f708e77c6bf78c6478cc6837be2380dd858c23dff84daad3b9e6190452e"
    )
    assert len(c.payload_bytes()) == 8576
    assert c.digest(c.payload_bytes()) == c.prior.PAYLOAD_SHA256


def test_consumed_c3_stops_before_plan_or_privileged_effects(monkeypatch):
    monkeypatch.setattr(c, "AUTHORIZATION_ID", c.proposal.previous.AUTHORIZATION_ID)

    def forbidden(*args, **kwargs):
        raise AssertionError("consumed_authority_must_stop_first")

    monkeypatch.setattr(c, "verify_plan", forbidden)
    monkeypatch.setattr(c, "reserve", forbidden)
    with pytest.raises(ValueError, match="new_specific_authorization_required"):
        asyncio.run(release.execute_remote("ENTIRELY_INVENTED_NOT_OPENED"))


def test_missing_new_review_stops_before_reservation(tmp_path, monkeypatch):
    monkeypatch.setattr(c, "REVIEW", tmp_path / "invented-missing-review.json")

    def forbidden(*args, **kwargs):
        raise AssertionError("review_must_precede_reservation")

    monkeypatch.setattr(c, "reserve", forbidden)
    with pytest.raises(FileNotFoundError):
        asyncio.run(release.execute_remote("ENTIRELY_INVENTED_NOT_OPENED"))
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "field", ["plan_sha256", "specific_remote_authorization_id", "execution_root_sha256"]
)
def test_predecessor_or_wrong_root_review_is_rejected(tmp_path, monkeypatch, field):
    plan = c.verify_plan()
    review = {
        "protocol": c.PROTOCOL,
        "decision": "approved_for_one_synthetic_attempt",
        "plan_sha256": c.PLAN_SHA256,
        "configuration_sha256": plan["configuration_sha256"],
        "specific_remote_authorization_id": c.AUTHORIZATION_ID,
        "financial_evidence_id": c.prior.FINANCIAL_ID,
        "reviewer_thread_id": c.prior.SUPERVISOR,
        "execution_root_sha256": c.digest(str(c.ROOT.resolve()).encode()),
        "source_message_id": "ENTIRELY_INVENTED_REVIEW",
    }
    review[field] = "ENTIRELY_INVENTED_MISMATCH"
    path = tmp_path / "invented-review.json"
    path.write_bytes(c.canonical(review))
    monkeypatch.setattr(c, "REVIEW", path)
    with pytest.raises(ValueError, match="technical_review_required"):
        c.check_review(plan)


@pytest.mark.parametrize("case", ["valid", "http_error"])
def test_new_fake_namespace_and_nonce_are_consumed_once(root_python, tmp_path, case):
    folder = tmp_path / "invented-recovery-release"
    receipt = asyncio.run(release.simulate(root_python, case, folder, timeout=5))
    assert receipt["protocol"] == c.PROTOCOL
    assert receipt["specific_remote_authorization_id"] == c.AUTHORIZATION_ID
    assert receipt["outcome"] == "observed"
    assert receipt["worker_cleanup_confirmed"] is True
    assert receipt["real_http_requests"] == 0
    assert receipt["result"]["current_provider"]["real_provider_verified"] is False
    reservation = json.loads((folder / "reservation-v3.json").read_bytes())
    assert reservation["plan_sha256"] == c.PLAN_SHA256
    assert reservation["parent_pid"] == os.getpid()
    assert (folder / "dispatch-v3.json").exists()
    assert (folder / "recovery-release-result-v2.json").exists()
    assert not (folder / "diagnostic-release-result.json").exists()
    if case == "http_error":
        diagnostic = receipt["result"]["selection_diagnostic"]
        assert diagnostic["phase"] == "transport"
        assert diagnostic["code"] == "http_error"
        assert diagnostic["authority_status"] == "not_invoked"
    with pytest.raises(FileExistsError):
        asyncio.run(release.simulate(root_python, "valid", folder, timeout=5))


def test_new_binding_refuses_old_filename_and_real_fake_namespaces(tmp_path):
    folder = tmp_path / "invented-binding"
    folder.mkdir()
    plan = c.verify_plan()
    bound = c.binding(plan, None, "INVENTED", 100.0, 45, offline=True, owner_pid=os.getpid())
    c.create(folder / "diagnostic-release-binding.json", bound)
    with pytest.raises(FileNotFoundError):
        c.check_binding(folder, plan, None, "INVENTED", offline=True, owner_pid=os.getpid())
    for name in (
        "issue-5-nim-graph-diagnostic-release-v1",
        "issue-5-nim-graph-recovery-proposal-v1",
        "issue-5-nim-graph-recovery-release-v2",
        "issue-5-nim-graph-recovery-release-v2-review",
    ):
        with pytest.raises(ValueError):
            c.simulation_folder(tmp_path / "invented-foreign-root" / name)

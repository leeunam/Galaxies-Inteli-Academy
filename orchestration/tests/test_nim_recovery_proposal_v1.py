"""Focused inert-envelope tests, without inference or global/PID monkeypatching."""

import json
import os
import subprocess
import sys

import pytest

from galaxies_orchestration import nim_recovery_proposal_v1 as proposal


def test_proposal_is_inert_and_consumed_c3_is_excluded():
    assert proposal.AUTHORIZATION_ID is None
    assert proposal.previous.AUTHORIZATION_ID in proposal.CONSUMED_AUTHORIZATIONS
    assert len(proposal.CONSUMED_AUTHORIZATIONS) == 3
    with pytest.raises(ValueError, match="^recovery_new_specific_authorization_required$"):
        proposal.execute_reviewed_once()
    assert not proposal.LEDGER.exists()
    assert not proposal.REVIEW.parent.exists()


def test_sealed_proposal_preserves_fixed_body_and_owner_limits():
    plan = proposal.verify_plan()
    config = plan["configuration"]
    assert config["remote_execution_released"] is False
    assert config["remaining_authorized_calls"] == 0
    assert config["proposed_future_calls"] == 1
    assert config["max_spend_brl"] == 0
    assert config["maximum_graph_work_seconds"] == 43
    assert config["maximum_cleanup_seconds"] == 2
    body = proposal.previous.payload_bytes()
    assert len(body) == 8576
    assert proposal.digest(body) == (
        "fd87bed20413c52bb7873d92da48c37d5f5f391a3fa9997e77177d073aaafcba"
    )
    for name in (
        "orchestration/galaxies_orchestration/nim_diagnostic_release_process_v1.py",
        "scripts/nim_graph_live_worker_v1.py",
        "scripts/explanation_evidence.py",
        "scripts/nim_diagnostic_http_adapter_v1.py",
    ):
        assert name in plan["sources_sha256"]


@pytest.mark.parametrize(
    "namespace",
    [
        "issue-5-nim-graph-diagnostic-release-v1",
        "issue-5-nim-graph-recovery-proposal-v1",
        "issue-5-nim-graph-recovery-proposal-v1-review",
    ],
)
def test_fake_folder_refuses_consumed_and_future_real_namespaces(tmp_path, namespace):
    with pytest.raises(ValueError):
        proposal.simulation_folder(tmp_path / namespace / "invented")
    assert not list(tmp_path.iterdir())


def test_fake_folder_accepts_invented_path_and_refuses_symlink(tmp_path):
    target = tmp_path / "invented-target"
    target.mkdir()
    assert proposal.simulation_folder(target / "invented") == target / "invented"
    link = tmp_path / "invented-link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError):
        proposal.simulation_folder(link / "invented")
    assert not list(target.iterdir())


def test_cli_execution_is_blocked_without_worker_or_credential_configuration():
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "galaxies_orchestration.nim_recovery_proposal_v1",
            "--execute-reviewed-once",
        ],
        cwd=proposal.ROOT / "orchestration",
        env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        check=True,
        timeout=5,
    )
    assert json.loads(completed.stdout) == {
        "outcome": "blocked",
        "code": "new_authorization_and_additive_release_required",
        "remote_execution_released": False,
        "real_http_requests": 0,
    }
    assert completed.stderr == b""
    assert not proposal.LEDGER.exists()
    assert not proposal.REVIEW.parent.exists()

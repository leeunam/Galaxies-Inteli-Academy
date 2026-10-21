"""Additive one-call release; a fresh checkout-bound technical review is required."""

import json
import math
import os
from pathlib import Path

from . import nim_diagnostic_attempt_contract_v1 as historical
from . import nim_graph_live_contract_v1 as prior
from .nim_diagnostic_release_seal_v1 import PLAN_SHA256
from .nim_graph_contract_v1 import ROOT, canonical, digest, payload_bytes, unique
from .nim_graph_contract_v1 import configuration as offline_configuration

PROTOCOL = "nim-three-diagnostic-release-v1"
AUTHORIZATION_ID = "Sentinel_c3cbbc19ae7c81919fc1361a0256d307"
CONSUMED_AUTHORIZATIONS = {
    "Sentinel_a49f19fb4c048191a49a669ff8f43f79",
    "Sentinel_d3d52a72c3308191b76c892fed01f4aa",
}
PLAN = ROOT / "orchestration/fixtures/nim-diagnostic-release-v1-plan.json"
LEDGER = ROOT / "data/private/issue-5-nim-graph-diagnostic-release-v1"
REVIEW = ROOT / "data/private/issue-5-nim-graph-diagnostic-release-v1-review/technical-review.json"
FAKE_CASES = frozenset(
    {
        "valid",
        "wrong_hash",
        "secret_id",
        "http_error",
        "invalid_wire",
        "hang",
        "too_many_ids",
        "duplicate_ids",
        "scalar_ids",
        "extra_field",
        "deep_json",
        "send_failure",
    }
)
create, read_json = prior.create, prior.read_json


def require_new_authorization():
    if (
        type(AUTHORIZATION_ID) is not str
        or AUTHORIZATION_ID in CONSUMED_AUTHORIZATIONS
        or (
            not 1 <= len(AUTHORIZATION_ID) <= 128
            or any(
                char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
                for char in AUTHORIZATION_ID
            )
        )
    ):
        raise ValueError("diagnostic_new_specific_authorization_required")
    return AUTHORIZATION_ID


def configuration():
    return offline_configuration() | {
        "protocol": PROTOCOL,
        "specific_remote_authorization_id": AUTHORIZATION_ID,
        "remote_execution_released": AUTHORIZATION_ID is not None,
        "remaining_authorized_calls": int(AUTHORIZATION_ID is not None),
        "technical_review_required": True,
        "financial_evidence_id": prior.FINANCIAL_ID,
        "ledger_relative_path": "data/private/issue-5-nim-graph-diagnostic-release-v1",
        "execution_checkout_binding": "private_review_root_path_sha256",
        "http_ownership": "same_root_worker_no_http_child",
        "maximum_graph_work_seconds": 43,
        "maximum_cleanup_seconds": 2,
        "maximum_cleanup_drain_seconds": 1,
        "maximum_cleanup_wait_seconds": 1,
        "cleanup_confirmation_required_for_observed_result": True,
        "cleanup_reap_confirmation": "owned_process_public_returncode",
    }


def verify_plan():
    historical.verify_plan()  # integrity only; never reads historical private ledgers
    raw = PLAN.read_bytes()
    if not PLAN_SHA256 or digest(raw) != PLAN_SHA256:
        raise ValueError("diagnostic_release_plan_seal_mismatch")
    plan = json.loads(raw, object_pairs_hook=unique)
    config = configuration()
    if set(plan) != {"configuration", "configuration_sha256", "sources_sha256"} or (
        canonical(plan["configuration"]) != canonical(config)
        or plan["configuration_sha256"] != digest(canonical(config))
        or len(payload_bytes()) != 8576
        or digest(payload_bytes()) != prior.PAYLOAD_SHA256
    ):
        raise ValueError("diagnostic_release_contract_changed")
    if type(plan["sources_sha256"]) is not dict or not plan["sources_sha256"]:
        raise ValueError("diagnostic_release_sources_missing")
    for name, expected in plan["sources_sha256"].items():
        path = ROOT / name
        if (
            path.is_symlink()
            or not path.resolve().is_relative_to(ROOT)
            or digest(path.read_bytes()) != expected
        ):
            raise ValueError("diagnostic_release_source_changed")
    return plan


def check_review(plan):
    authorization = require_new_authorization()  # BEFORE reading any private review
    if REVIEW.is_symlink() or any(parent.is_symlink() for parent in REVIEW.parents):
        raise ValueError("diagnostic_release_symlink_forbidden")
    review, checksum = read_json(REVIEW, 4096)
    expected = {
        "protocol": PROTOCOL,
        "decision": "approved_for_one_synthetic_attempt",
        "plan_sha256": PLAN_SHA256,
        "configuration_sha256": plan["configuration_sha256"],
        "specific_remote_authorization_id": authorization,
        "financial_evidence_id": prior.FINANCIAL_ID,
        "reviewer_thread_id": prior.SUPERVISOR,
        "execution_root_sha256": digest(str(ROOT.resolve()).encode()),
    }
    if (
        type(review) is not dict
        or set(review) != set(expected) | {"source_message_id"}
        or any(review[key] != value for key, value in expected.items())
    ):
        raise ValueError("diagnostic_release_technical_review_required")
    source = review["source_message_id"]
    if (
        type(source) is not str
        or not 1 <= len(source) <= 128
        or any(
            char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
            for char in source
        )
    ):
        raise ValueError("diagnostic_release_technical_review_required")
    return checksum


def simulation_folder(folder):
    folder = historical.simulation_folder(folder)
    # A fake cannot target a real namespace in this OR any other checkout.
    if any(part.startswith("issue-5-nim-") for part in folder.parts):
        raise ValueError("diagnostic_release_real_namespace_forbidden")
    if any(
        folder.resolve() == path.resolve() or folder.resolve().is_relative_to(path.resolve())
        for path in (LEDGER, REVIEW.parent)
    ):
        raise ValueError("diagnostic_release_real_namespace_forbidden")
    return folder


def reserve(folder, *, offline):
    # Same v3 codec, generated by the actual isolated graph PARENT. The root
    # CHILD uses original authorize() and actual getppid(), without overrides.
    if offline:
        folder = simulation_folder(folder)
    else:
        require_new_authorization()
        check_review(verify_plan())  # before mkdir, durable reservation or nonce
        if Path(folder) != LEDGER:
            raise ValueError("diagnostic_release_fixed_ledger_required")
    folder = Path(folder).absolute()
    if any(parent.is_symlink() for parent in folder.parents):
        raise ValueError("diagnostic_release_symlink_forbidden")
    prior.ensure_directory(folder.parent)
    folder.mkdir(mode=0o700, exist_ok=False)
    prior.sync_directory(folder.parent)
    nonce = os.urandom(32)
    create(
        folder / "reservation-v3.json",
        {
            "protocol": "nim-fixed-public-dispatch-v3",
            "state": "consumed_before_child_start",
            "plan_sha256": PLAN_SHA256,
            "parent_pid": os.getpid(),
            "nonce_sha256": digest(nonce),
            "offline_simulation_only": offline,
            "retry_allowed": False,
        },
    )
    return folder, nonce


def cleanup_budget(timeout):
    # Real 45s run reserves 2s. Short fakes keep the same maxima proportionally.
    return min(2.0, timeout / 4.0)


def binding(plan, review_hash, run_id, started, timeout, *, offline, owner_pid):
    deadline = started + timeout
    cleanup = cleanup_budget(deadline - started)
    return {
        "protocol": PROTOCOL,
        "plan_sha256": PLAN_SHA256,
        "configuration_sha256": plan["configuration_sha256"],
        "specific_remote_authorization_id": AUTHORIZATION_ID,
        "technical_review_sha256": review_hash,
        "run_id": run_id,
        "owner_pid": owner_pid,
        "started_monotonic": started,
        "deadline_monotonic": deadline,
        "work_deadline_monotonic": deadline - cleanup,
        "cleanup_drain_timeout_seconds": cleanup / 2,
        "cleanup_wait_timeout_seconds": cleanup / 2,
        "offline_simulation_only": offline,
    }


def check_binding(folder, plan, review_hash, run_id, *, offline, owner_pid):
    value, _ = read_json(folder / "diagnostic-release-binding.json", 4096)
    if type(value) is not dict:
        raise ValueError("diagnostic_release_binding_invalid")
    started, deadline = value.get("started_monotonic"), value.get("deadline_monotonic")
    if (
        any(type(v) is not float or not math.isfinite(v) for v in (started, deadline))
        or not 0 < deadline - started <= 45
    ):
        raise ValueError("diagnostic_release_deadline_invalid")
    expected = binding(
        plan, review_hash, run_id, started, deadline - started, offline=offline, owner_pid=owner_pid
    )
    if canonical(value) != canonical(expected):
        raise ValueError("diagnostic_release_binding_invalid")
    return value

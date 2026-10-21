"""One checkout-bound release for the exact previously reviewed public body."""

import json
import math
import os
from pathlib import Path

from .nim_graph_contract_v1 import ROOT, canonical, digest, payload_bytes, unique
from .nim_graph_contract_v1 import configuration as offline_configuration
from .nim_graph_contract_v1 import verify_plan as verify_offline
from .nim_graph_live_seal_v1 import PLAN_SHA256

PROTOCOL = "nim-three-invented-live-graph-v1"
AUTHORIZATION_ID = "Sentinel_d3d52a72c3308191b76c892fed01f4aa"
FINANCIAL_ID = "Sentinel_e945b14459008191a932c869a4216aef"
SUPERVISOR = "01a15713-2572-7544-8329-c229ea2ff0f5"
PLAN = ROOT / "orchestration/fixtures/nim-graph-live-v1-plan.json"
LEDGER = ROOT / "data/private/issue-5-nim-graph-live-v1"
REVIEW = ROOT / "data/private/issue-5-nim-graph-live-v1-review/technical-review.json"
PAYLOAD_SHA256 = "fd87bed20413c52bb7873d92da48c37d5f5f391a3fa9997e77177d073aaafcba"
FINANCIAL_EVIDENCE = {
    "kind": "previous_specific_user_confirmation_of_project_account_free_plan",
    "source_message_id": FINANCIAL_ID,
    "source_timestamp_utc": "2026-10-21T00:20:00Z",
    "sanitized_fact": "The NVIDIA API access used by this project is on the free plan.",
    "official_sources": [
        "https://developer.nvidia.com/nim",
        "https://docs.api.nvidia.com/nim/docs/product",
    ],
    "new_payment_or_access_terms_allowed": False,
    "secret_read_for_evidence": False,
}


def configuration():
    config = offline_configuration()
    return config | {
        "protocol": PROTOCOL,
        "remaining_authorized_calls": 1,
        "remote_execution_released": True,
        "specific_remote_authorization_id": AUTHORIZATION_ID,
        "technical_review_required": True,
        "financial_evidence_id": FINANCIAL_ID,
        "ledger_relative_path": "data/private/issue-5-nim-graph-live-v1",
        "execution_checkout_binding": "private_review_root_path_sha256",
        "http_ownership": "same_root_worker_direct_parent_nonce_no_http_grandchild",
    }


def verify_plan():
    verify_offline()
    raw = PLAN.read_bytes()
    if not PLAN_SHA256 or digest(raw) != PLAN_SHA256:
        raise ValueError("live_graph_plan_seal_mismatch")
    plan = json.loads(raw, object_pairs_hook=unique)
    config = configuration()
    if len(payload_bytes()) != 8576 or digest(payload_bytes()) != PAYLOAD_SHA256:
        raise ValueError("live_graph_payload_changed")
    if set(plan) != {
        "configuration",
        "configuration_sha256",
        "financial_evidence",
        "sources_sha256",
    } or (
        canonical(plan["configuration"]) != canonical(config)
        or plan["configuration_sha256"] != digest(canonical(config))
        or canonical(plan["financial_evidence"]) != canonical(FINANCIAL_EVIDENCE)
    ):
        raise ValueError("live_graph_contract_changed")
    if type(plan["sources_sha256"]) is not dict or not plan["sources_sha256"]:
        raise ValueError("live_graph_sources_missing")
    for name, expected in plan["sources_sha256"].items():
        path = ROOT / name
        if (
            path.is_symlink()
            or not path.resolve().is_relative_to(ROOT)
            or digest(path.read_bytes()) != expected
        ):
            raise ValueError("live_graph_source_changed")
    return plan


def read_json(path, limit):
    if path.is_symlink() or path.stat().st_size > limit:
        raise ValueError("live_graph_private_binding_invalid")
    raw = path.read_bytes()
    if len(raw) > limit:
        raise ValueError("live_graph_private_binding_invalid")
    return json.loads(raw, object_pairs_hook=unique), digest(raw)


def check_review(plan):
    review, checksum = read_json(REVIEW, 4096)
    expected = {
        "protocol": PROTOCOL,
        "decision": "approved_for_one_synthetic_attempt",
        "plan_sha256": PLAN_SHA256,
        "configuration_sha256": plan["configuration_sha256"],
        "specific_remote_authorization_id": AUTHORIZATION_ID,
        "financial_evidence_id": FINANCIAL_ID,
        "reviewer_thread_id": SUPERVISOR,
        "execution_root_sha256": digest(str(ROOT.resolve()).encode()),
    }
    if (
        type(review) is not dict
        or set(review) != set(expected) | {"source_message_id"}
        or any(review[key] != value for key, value in expected.items())
    ):
        raise ValueError("live_graph_technical_review_required")
    source = review["source_message_id"]
    if (
        type(source) is not str
        or not 1 <= len(source) <= 128
        or any(
            char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
            for char in source
        )
    ):
        raise ValueError("live_graph_technical_review_required")
    return checksum


def sync_directory(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def create(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(canonical(value) + b"\n")
        output.flush()
        os.fsync(output.fileno())
    sync_directory(path.parent)


def ensure_directory(path):
    if path.is_symlink():
        raise ValueError("live_graph_symlink_forbidden")
    if path.is_dir():
        return
    ensure_directory(path.parent)
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        if path.is_symlink() or not path.is_dir():
            raise ValueError("live_graph_directory_invalid") from None
    sync_directory(path.parent)


def reserve(folder, *, offline):
    """Exact existing v3 consumption codec, emitted in the actual graph PARENT.

    Kept stdlib-only for the isolated interpreter. The root CHILD uses the
    unchanged v3 authorize(), including real getppid() and nonce validation.
    """
    folder = Path(folder).absolute()
    if any("nim-sintetico-unico" in part for part in folder.parts) or any(
        parent.is_symlink() for parent in folder.parents
    ):
        raise ValueError("live_graph_protected_or_symlink_ledger")
    ensure_directory(folder.parent)
    folder.mkdir(mode=0o700, exist_ok=False)
    sync_directory(folder.parent)
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


def simulation_folder(folder):
    folder = Path(folder).absolute()
    if folder.is_symlink() or any(parent.is_symlink() for parent in folder.parents):
        raise ValueError("live_graph_symlink_forbidden")
    protected = [
        ROOT / "data/private" / name
        for name in (
            "issue-5-nim-sintetico-unico-v1",
            "issue-5-nim-dispatch-v3",
            "issue-5-nim-release-v1",
            "issue-5-nim-release-v1-review",
            "issue-5-nim-typed-request-v1",
            "issue-5-nim-typed-request-v1-review",
        )
    ] + [LEDGER, REVIEW.parent]
    if any(
        folder.resolve() == path.resolve() or folder.resolve().is_relative_to(path.resolve())
        for path in protected
    ):
        raise ValueError("live_graph_protected_ledger")
    return folder


def binding(plan, review_hash, run_id, started, timeout, *, offline, owner_pid):
    return {
        "protocol": PROTOCOL,
        "plan_sha256": PLAN_SHA256,
        "configuration_sha256": plan["configuration_sha256"],
        "specific_remote_authorization_id": AUTHORIZATION_ID,
        "financial_evidence_id": FINANCIAL_ID,
        "technical_review_sha256": review_hash,
        "run_id": run_id,
        "owner_pid": owner_pid,
        "started_monotonic": started,
        "deadline_monotonic": started + timeout,
        "offline_simulation_only": offline,
    }


def check_binding(folder, plan, review_hash, run_id, *, offline, owner_pid):
    value, _ = read_json(folder / "live-graph-binding.json", 4096)
    if type(value) is not dict:
        raise ValueError("live_graph_binding_invalid")
    started, deadline = value.get("started_monotonic"), value.get("deadline_monotonic")
    if (
        any(type(v) is not float or not math.isfinite(v) for v in (started, deadline))
        or not 0 < deadline - started <= 45
    ):
        raise ValueError("live_graph_deadline_invalid")
    expected = binding(
        plan, review_hash, run_id, started, deadline - started, offline=offline, owner_pid=owner_pid
    )
    if canonical(value) != canonical(expected):
        raise ValueError("live_graph_binding_invalid")
    return value

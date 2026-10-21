"""New one-shot release, additive to the immutable offline v3 contract."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.nim_dispatch_fakes_v3 import CASES
from scripts.nim_dispatch_plan_v3 import (
    ENDPOINT,
    FIXTURE_SHA256,
    MODEL,
    ROOT,
    canonical,
    digest,
    payload_bytes,
)
from scripts.nim_dispatch_plan_v3 import LEDGER as OFFLINE_V3_LEDGER
from scripts.nim_dispatch_plan_v3 import verify_plan as verify_offline_v3
from scripts.nim_dispatch_seal_v3 import PLAN_SHA256 as OFFLINE_V3_SHA256
from scripts.nim_release_seal_v1 import PLAN_SHA256
from scripts.selection_observation_v2 import _unique

PROTOCOL = "nim-fixed-public-single-release-v1"
PLAN = ROOT / "orchestration/fixtures/nim-release-v1-plan.json"
LEDGER = ROOT / "data/private/issue-5-nim-release-v1"
REVIEW = ROOT / "data/private/issue-5-nim-release-v1-review/technical-review.json"
SEALED_V1_NAMESPACE = ROOT / "data/private/issue-5-nim-sintetico-unico-v1"
SUPERVISOR = "01a15713-2572-7544-8329-c229ea2ff0f5"
EVIDENCE_ID = "Sentinel_e945b14459008191a932c869a4216aef"
SIMULATION_CASES = CASES | {"http_429", "http_503"}
FINANCIAL_EVIDENCE = {
    "kind": "user_confirmation_of_project_account_free_plan",
    "source_message_id": EVIDENCE_ID,
    "source_timestamp_utc": "2026-10-21T00:20:00Z",
    "sanitized_fact": "The NVIDIA API access used by this project is on the free plan.",
    "official_sources": [
        "https://developer.nvidia.com/nim",
        "https://docs.api.nvidia.com/nim/docs/product",
        "https://build.nvidia.com/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
    ],
    "basis": "specific_user_account_confirmation_and_official_free_prototyping_offer",
    "account_identifiers_retained": False,
    "secret_read_for_evidence": False,
}


def configuration():
    return {
        "endpoint": ENDPOINT,
        "model": MODEL,
        "fixture_sha256": FIXTURE_SHA256,
        "http_payload_sha256": digest(payload_bytes()),
        "max_calls": 1,
        "max_output_tokens": 2048,
        "total_timeout_seconds": 45,
        "max_response_bytes": 16384,
        "max_spend_brl": 0,
        "execution_checkout_binding": "private_technical_review_root_path_sha256",
        "ledger_relative_path": str(LEDGER.relative_to(ROOT)),
        "retry_allowed": False,
        "redirect_allowed": False,
        "proxy_allowed": False,
        "private_data_allowed": False,
        "technical_review_required": True,
    }


def verify_plan():
    previous = verify_offline_v3()
    assert previous["remote_execution_released"] is False
    raw = PLAN.read_bytes()
    if not PLAN_SHA256 or digest(raw) != PLAN_SHA256:
        raise ValueError("release_plan_seal_mismatch")
    plan = json.loads(raw, object_pairs_hook=_unique)
    config = configuration()
    expected = {
        "protocol": PROTOCOL,
        "configuration": config,
        "configuration_sha256": digest(canonical(config)),
        "financial_evidence": FINANCIAL_EVIDENCE,
        "offline_v3_plan_sha256": OFFLINE_V3_SHA256,
    }
    if set(plan) != set(expected) | {"sources_sha256"} or any(
        canonical(plan[name]) != canonical(value) for name, value in expected.items()
    ):
        raise ValueError("release_plan_contract_mismatch")
    if type(plan["sources_sha256"]) is not dict or not plan["sources_sha256"]:
        raise ValueError("release_sources_missing")
    for name, expected_hash in plan["sources_sha256"].items():
        path = ROOT / name
        if (
            path.is_symlink()
            or not path.resolve().is_relative_to(ROOT)
            or digest(path.read_bytes()) != expected_hash
        ):
            raise ValueError("release_source_changed")
    return plan


def check_review(plan):
    """Trusted operator receipt, created only after the supervisor's concrete review.

    This is an integrity/coordination gate in operator-owned storage, not a claim
    of cryptographic authentication against someone who can rewrite local files.
    No CLI here can approve its own release or create this receipt.
    """
    if REVIEW.is_symlink() or REVIEW.stat().st_size > 4096:
        raise ValueError("release_technical_review_required")
    raw = REVIEW.read_bytes()
    if len(raw) > 4096:
        raise ValueError("release_technical_review_required")
    review = json.loads(raw, object_pairs_hook=_unique)
    expected = {
        "protocol": PROTOCOL,
        "decision": "approved_for_one_synthetic_attempt",
        "plan_sha256": PLAN_SHA256,
        "configuration_sha256": plan["configuration_sha256"],
        "financial_evidence_id": EVIDENCE_ID,
        "reviewer_thread_id": SUPERVISOR,
    }
    if set(review) != set(expected) | {"source_message_id", "execution_root_sha256"} or any(
        review[name] != value for name, value in expected.items()
    ):
        raise ValueError("release_technical_review_required")
    source = review["source_message_id"]
    if (
        type(source) is not str
        or not 1 <= len(source) <= 128
        or any(
            char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
            for char in source
        )
    ):
        raise ValueError("release_technical_review_required")
    if review["execution_root_sha256"] != digest(str(ROOT.resolve()).encode()):
        raise ValueError("release_review_checkout_mismatch")
    return digest(raw)


def simulation_folder(folder):
    folder = Path(folder).absolute()
    if folder.is_symlink() or any(parent.is_symlink() for parent in folder.parents):
        raise ValueError("release_symlink_simulation_forbidden")
    resolved = folder.resolve()
    for reserved in (LEDGER, OFFLINE_V3_LEDGER, REVIEW.parent, SEALED_V1_NAMESPACE):
        if resolved == reserved.resolve() or resolved.is_relative_to(reserved.resolve()):
            raise ValueError("release_protected_ledger_forbidden_in_simulation")
    return folder


def check_binding(folder, plan, review_hash, *, offline):
    path = folder / "release-binding.json"
    if path.is_symlink() or path.stat().st_size > 2048:
        raise ValueError("release_binding_mismatch")
    expected = {
        "protocol": PROTOCOL,
        "plan_sha256": PLAN_SHA256,
        "configuration_sha256": plan["configuration_sha256"],
        "financial_evidence_id": EVIDENCE_ID,
        "technical_review_sha256": review_hash,
        "offline_simulation_only": offline,
    }
    actual = json.loads(path.read_bytes(), object_pairs_hook=_unique)
    if canonical(actual) != canonical(expected):
        raise ValueError("release_binding_mismatch")

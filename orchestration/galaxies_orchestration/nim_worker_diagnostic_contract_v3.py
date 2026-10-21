"""Fixed candidate with external, separately reviewed one-call authorization receipts."""

import json
import math
import os
import re
from pathlib import Path

from . import nim_graph_live_contract_v1 as original
from . import nim_recovery_release_contract_v2 as previous
from .nim_graph_contract_v1 import ROOT, canonical, digest, payload_bytes, unique
from .nim_http_error_metadata_v1 import validate_error_metadata
from .nim_worker_diagnostic_seal_v3 import PLAN_SHA256

PROTOCOL = "nim-worker-http-diagnostic-v3"
AUTHORIZATION_ID = None  # No embedded authorization; future receipt does not change source.
PLAN = ROOT / "orchestration/fixtures/nim-worker-diagnostic-v3-plan.json"
LEDGER = ROOT / "data/private/issue-5-nim-worker-diagnostic-v3"
AUTHORIZATION = (
    ROOT / "data/private/issue-5-nim-worker-diagnostic-v3-authorization/authorization.json"
)
REVIEW = ROOT / "data/private/issue-5-nim-worker-diagnostic-v3-review/technical-review.json"
BINDING_NAME = "worker-diagnostic-binding-v3.json"
RESULT_NAME = "worker-diagnostic-result-v3.json"
CONSUMED_AUTHORIZATIONS = previous.CONSUMED_AUTHORIZATIONS | {
    previous.AUTHORIZATION_ID,
    original.FINANCIAL_ID,  # Financial fact is not permission for an inference.
    "Sentinel_c2b13386e42c8191b98d390fffadaf03",  # Generic repair request is not POST consent.
}
FAKE_CASES = frozenset(
    {
        "valid",
        "wrong_hash",
        "secret_id",
        "duplicate_ids",
        "wire_limit",
        "wire_at_limit",
        "headers_at_limit",
        "headers_excess",
        "header_chars_at_limit",
        "header_chars_excess",
        "adapter_invalid_200",
        "adapter_invalid_503",
        "http_401",
        "http_403",
        "http_429",
        "http_503",
        "http_503_missing",
        "http_503_invalid",
        "http_503_duplicate",
        "http_503_exception",
        "http_503_long",
    }
)
create, read_json = original.create, original.read_json


def bound_error_metadata(value, status):
    """Diagnostic failure never changes the separately validated authority result."""
    try:
        if status is None or status == 200:
            if value is not None:
                raise ValueError("worker_diagnostic_unexpected_metadata")
            return None, "not_applicable"
        if type(status) is not int or not 100 <= status <= 599:
            raise ValueError("worker_diagnostic_invalid_status")
        validate_error_metadata(value)
        if value["http_status"] != status:
            raise ValueError("worker_diagnostic_status_mismatch")
        return value, "validated"
    except Exception:  # noqa: BLE001 - discard unknown IPC values/errors, preserve authority
        return None, "invalid_ipc_metadata"


def configuration():
    return previous.configuration() | {
        "protocol": PROTOCOL,
        "specific_remote_authorization_id": None,
        "remote_execution_released": False,
        "remaining_authorized_calls": 0,
        "external_specific_authorization_required": True,
        "authorization_binding": "fixed_private_receipt_hash_plus_checkout_bound_technical_review",
        "ledger_relative_path": "data/private/issue-5-nim-worker-diagnostic-v3",
        "consumed_predecessor_authorization_id": previous.AUTHORIZATION_ID,
        "http_error_metadata_schema": "nim-http-error-metadata-v1",
        "error_body_read_allowed": False,
    }


def verify_plan():
    previous.verify_plan()  # Public source integrity only, never predecessor private receipts.
    raw = PLAN.read_bytes()
    if digest(raw) != PLAN_SHA256:
        raise ValueError("worker_diagnostic_plan_seal_mismatch")
    plan = json.loads(raw, object_pairs_hook=unique)
    config = configuration()
    if (
        set(plan) != {"configuration", "configuration_sha256", "sources_sha256"}
        or canonical(plan["configuration"]) != canonical(config)
        or plan["configuration_sha256"] != digest(canonical(config))
        or len(payload_bytes()) != 8576
        or digest(payload_bytes()) != original.PAYLOAD_SHA256
        or type(plan["sources_sha256"]) is not dict
        or not plan["sources_sha256"]
    ):
        raise ValueError("worker_diagnostic_contract_changed")
    for name, checksum in plan["sources_sha256"].items():
        path = ROOT / name
        if (
            path.is_symlink()
            or not path.resolve().is_relative_to(ROOT)
            or digest(path.read_bytes()) != checksum
        ):
            raise ValueError("worker_diagnostic_source_changed")
    return plan


def receipt_binding(plan):
    return {
        "protocol": PROTOCOL,
        "plan_sha256": PLAN_SHA256,
        "configuration_sha256": plan["configuration_sha256"],
        "execution_root_sha256": digest(str(ROOT.resolve()).encode()),
        "http_payload_sha256": original.PAYLOAD_SHA256,
        "financial_evidence_id": original.FINANCIAL_ID,
    }


def validate_authorization(value, plan):
    expected = receipt_binding(plan) | {
        "decision": "authorized_for_one_synthetic_attempt",
        "authorized_calls": 1,
        "recorded_by_thread_id": original.SUPERVISOR,
    }
    if type(value) is not dict or set(value) != set(expected) | {
        "specific_remote_authorization_id"
    }:
        raise ValueError("worker_diagnostic_specific_authorization_required")
    authorization = value["specific_remote_authorization_id"]
    if (
        type(authorization) is not str
        or re.fullmatch(r"Sentinel_[0-9a-f]{32}", authorization) is None
        or authorization in CONSUMED_AUTHORIZATIONS
        or any(
            type(value[key]) is not type(item) or value[key] != item
            for key, item in expected.items()
        )
    ):
        raise ValueError("worker_diagnostic_specific_authorization_required")
    return authorization


def private_json(path):
    if path.is_symlink() or any(parent.is_symlink() for parent in path.parents):
        raise ValueError("worker_diagnostic_symlink_forbidden")
    return read_json(path, 4096)


def authorization_receipt(plan):
    value, checksum = private_json(AUTHORIZATION)
    return validate_authorization(value, plan), checksum


def require_new_authorization():
    return authorization_receipt(verify_plan())[0]


def validate_review(value, plan, authorization, authorization_sha256):
    expected = receipt_binding(plan) | {
        "decision": "approved_for_one_synthetic_attempt",
        "specific_remote_authorization_id": authorization,
        "authorization_receipt_sha256": authorization_sha256,
        "reviewer_thread_id": original.SUPERVISOR,
    }
    if (
        type(value) is not dict
        or set(value) != set(expected) | {"source_message_id"}
        or any(
            type(value[key]) is not type(item) or value[key] != item
            for key, item in expected.items()
        )
    ):
        raise ValueError("worker_diagnostic_technical_review_required")
    source = value["source_message_id"]
    if type(source) is not str or re.fullmatch(r"[A-Za-z0-9_-]{1,128}", source) is None:
        raise ValueError("worker_diagnostic_technical_review_required")
    return value


def check_review(plan):
    authorization, checksum = authorization_receipt(plan)
    value, review_hash = private_json(REVIEW)
    validate_review(value, plan, authorization, checksum)
    return review_hash


def simulation_folder(folder):
    # Reject every old/new real namespace in any checkout, plus symlinks.
    folder = previous.simulation_folder(folder)
    if any(part.startswith("issue-5-nim-") for part in folder.parts):
        raise ValueError("worker_diagnostic_real_namespace_forbidden")
    return folder


def reserve(folder, *, offline):
    if offline:
        folder = simulation_folder(folder)
    else:
        check_review(verify_plan())  # Before mkdir, os.urandom, spawn, getter or socket.
        if Path(folder) != LEDGER:
            raise ValueError("worker_diagnostic_fixed_ledger_required")
    # Same stdlib v3 codec, as in v2: importing the ROOT ledger module here
    # would import numpy into the deliberately isolated graph interpreter.
    # The child still calls unchanged authorize() with real getppid().
    folder = Path(folder).absolute()
    if folder.is_symlink() or any(parent.is_symlink() for parent in folder.parents):
        raise ValueError("worker_diagnostic_symlink_forbidden")
    original.ensure_directory(folder.parent)
    folder.mkdir(mode=0o700, exist_ok=False)
    original.sync_directory(folder.parent)
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


def binding(plan, review_hash, run_id, started, timeout, *, offline, owner_pid):
    authorization, checksum = (None, None) if offline else authorization_receipt(plan)
    return previous.binding(
        plan, review_hash, run_id, started, timeout, offline=offline, owner_pid=owner_pid
    ) | {
        "protocol": PROTOCOL,
        "plan_sha256": PLAN_SHA256,
        "specific_remote_authorization_id": authorization,
        "authorization_receipt_sha256": checksum,
    }


def check_binding(folder, plan, review_hash, run_id, *, offline, owner_pid):
    value, _ = read_json(folder / BINDING_NAME, 4096)
    if type(value) is not dict:
        raise ValueError("worker_diagnostic_binding_invalid")
    started, deadline = value.get("started_monotonic"), value.get("deadline_monotonic")
    if (
        any(type(item) is not float or not math.isfinite(item) for item in (started, deadline))
        or not 0 < deadline - started <= 45
    ):
        raise ValueError("worker_diagnostic_deadline_invalid")
    if not offline and check_review(plan) != review_hash:
        raise ValueError("worker_diagnostic_review_binding_changed")
    expected = binding(
        plan, review_hash, run_id, started, deadline - started, offline=offline, owner_pid=owner_pid
    )
    if canonical(value) != canonical(expected):
        raise ValueError("worker_diagnostic_binding_invalid")
    return value

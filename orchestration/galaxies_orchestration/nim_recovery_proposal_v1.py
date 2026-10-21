"""Inert recovery proposal: no reservation, worker, credential or HTTP implementation."""

import argparse
import json

from . import nim_diagnostic_release_contract_v1 as previous
from .nim_graph_contract_v1 import ROOT, canonical, digest, unique
from .nim_recovery_proposal_seal_v1 import PLAN_SHA256

PROTOCOL = "nim-three-recovery-proposal-v1"
AUTHORIZATION_ID = None
CONSUMED_AUTHORIZATIONS = previous.CONSUMED_AUTHORIZATIONS | {previous.AUTHORIZATION_ID}
PLAN = ROOT / "orchestration/fixtures/nim-recovery-proposal-inert-v1-plan.json"
LEDGER = ROOT / "data/private/issue-5-nim-graph-recovery-proposal-v1"
REVIEW = ROOT / "data/private/issue-5-nim-graph-recovery-proposal-v1-review/technical-review.json"


def configuration():
    return previous.configuration() | {
        "protocol": PROTOCOL,
        "specific_remote_authorization_id": AUTHORIZATION_ID,
        "remote_execution_released": False,
        "remaining_authorized_calls": 0,
        "proposed_future_calls": 1,
        "ledger_relative_path": "data/private/issue-5-nim-graph-recovery-proposal-v1",
        "new_specific_authorization_required": True,
        "new_additive_release_required": True,
        "consumed_authorizations": sorted(CONSUMED_AUTHORIZATIONS),
        "previous_result": "transport_http_503_authority_not_invoked",
        "previous_receipt_sha256": (
            "ce2deeae290804a4d6f2464a0f68afcff515d5026f85e37c184496bdd9d253e5"
        ),
        "additional_remote_diagnostics": False,
        "preliminary_inference_allowed": False,
    }


def require_new_authorization():
    if AUTHORIZATION_ID is None or AUTHORIZATION_ID in CONSUMED_AUTHORIZATIONS:
        raise ValueError("recovery_new_specific_authorization_required")


def verify_plan():
    previous.verify_plan()  # public software integrity only; no consumed-ledger read
    if PLAN.is_symlink():
        raise ValueError("recovery_plan_symlink_forbidden")
    raw = PLAN.read_bytes()
    if digest(raw) != PLAN_SHA256:
        raise ValueError("recovery_plan_seal_mismatch")
    plan = json.loads(raw, object_pairs_hook=unique)
    config = configuration()
    if set(plan) != {"configuration", "configuration_sha256", "sources_sha256"} or (
        canonical(plan["configuration"]) != canonical(config)
        or plan["configuration_sha256"] != digest(canonical(config))
    ):
        raise ValueError("recovery_plan_changed")
    if type(plan["sources_sha256"]) is not dict or not plan["sources_sha256"]:
        raise ValueError("recovery_sources_missing")
    for name, expected in plan["sources_sha256"].items():
        path = ROOT / name
        if (
            path.is_symlink()
            or not path.resolve().is_relative_to(ROOT)
            or (digest(path.read_bytes()) != expected)
        ):
            raise ValueError("recovery_source_changed")
    return plan


def simulation_folder(folder):
    return previous.simulation_folder(folder)  # validates only; creates nothing


def execute_reviewed_once():
    require_new_authorization()  # FIRST, before plan/review/nonce/spawn/key/socket
    verify_plan()
    # Even changing the constant and resealing cannot activate this proposal.
    # A future separately reviewed release must supply the authorized execution.
    raise ValueError("recovery_additive_release_required")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--inspect-plan", action="store_true")
    mode.add_argument("--execute-reviewed-once", action="store_true")
    args = parser.parse_args()
    try:
        if args.execute_reviewed_once:
            execute_reviewed_once()
        plan = verify_plan()
        result = {
            "protocol": PROTOCOL,
            "plan_sha256": PLAN_SHA256,
            "configuration_sha256": plan["configuration_sha256"],
            "remote_execution_released": False,
            "remaining_authorized_calls": 0,
            "proposed_future_calls": 1,
        }
    except Exception:  # noqa: BLE001 - fixed public outcome, no arbitrary errors or paths
        result = {
            "outcome": "blocked",
            "code": "new_authorization_and_additive_release_required",
            "remote_execution_released": False,
            "real_http_requests": 0,
        }
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()

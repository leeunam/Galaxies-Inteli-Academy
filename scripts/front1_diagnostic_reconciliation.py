"""Reconcile a completed one-cell diagnostic; never dispatch or grant quality."""

import json


def reconcile_outcome(capture, receipt, owned, terminal):
    """Caller must first verify file/plan/capture bindings; preserve the raw terminal.

    A known perceptual rejection exits the reviewed worker with 2, which the
    generic process owner calls child_failed. That is separate from native rc0.
    This projection never upgrades a failed/uncertain owner or native capture.
    """
    if receipt["technical_success"] is not capture["technical_success"]:
        raise ValueError("receipt_capture_technical_mismatch")
    for name in ("cleanup_confirmed", "image_tokens_observed"):
        if receipt[name] != capture[name]:
            raise ValueError("receipt_capture_observation_mismatch")
    if capture["parsed_response"] is not None and (
        receipt["value"] != capture["parsed_response"]["value"]
        or receipt["native"] != capture["parsed_response"]["native"]
    ):
        raise ValueError("receipt_capture_response_mismatch")
    native_complete = (
        capture["technical_success"] is True
        and capture["returncode"] == 0
        and capture["stop_code"] is None
        and capture["cleanup_confirmed"] is True
        and capture["format_status"] == "valid"
        and capture["process_started"] is True
        and capture["image_encoder_and_decode_observed"] is True
        and capture["image_tokens_observed"] == 240
    )
    supported = (
        receipt["value"] is True
        and receipt["native"]["presented_categories"] == ["garment"]
        and receipt["native"]["item_configuration"]
        in ("hand_holds_hanger_out", "isolated_physical_item")
    )
    accepted = native_complete and supported
    if receipt["accepted"] is not accepted:
        raise ValueError("receipt_acceptance_not_reproduced")
    worker_outcome_bound = False
    if native_complete and owned["cleanup_confirmed"] is True:
        expected = ("completed", 0) if accepted else ("child_failed", 2)
        worker_outcome_bound = (
            (owned["code"], owned["returncode"]) == expected
            and json.loads(owned["stdout"]) == receipt
            and terminal["calls_reserved"] == 1
            and terminal["pending"] is None
        )
    if not native_complete or not worker_outcome_bound:
        outcome = "technical_or_uncertain_failure"
    elif accepted:
        outcome = "supported_true_diagnostic_only"
    elif receipt["value"] == "unknown":
        outcome = "abstention_diagnostic_only"
    elif receipt["value"] is False:
        outcome = "false_negative_diagnostic_only"
    elif receipt["value"] is True:
        outcome = "unsupported_true_diagnostic_only"
    else:
        raise ValueError("unexpected_projected_value")
    return {
        "schema": "front1-additive-diagnostic-reconciliation-v1",
        "raw_terminal_status": terminal["status"],
        "native_technically_completed": native_complete,
        "worker_outcome_bound": worker_outcome_bound,
        "intentional_worker_rejection_exit": worker_outcome_bound and not accepted,
        "reconciled_outcome": outcome,
        "perceptually_accepted_known_case": accepted and worker_outcome_bound,
        "raw_terminal_rewritten": False,
        "retry_allowed": False,
        "quality_release": False,
        "audit_released": False,
        "development_269_released": False,
        "B_C_released": False,
    }

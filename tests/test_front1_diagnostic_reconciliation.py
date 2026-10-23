"""Invented receipts only, with no operator import or native processes."""

import json

import pytest

from scripts.front1_diagnostic_reconciliation import reconcile_outcome


def evidence(value="unknown", configuration="unclear", category=None):
    native = {"presented_categories": category or [], "item_configuration": configuration}
    accepted = (
        value is True and configuration == "isolated_physical_item" and category == ["garment"]
    )
    capture = {
        "technical_success": True,
        "returncode": 0,
        "stop_code": None,
        "cleanup_confirmed": True,
        "format_status": "valid",
        "process_started": True,
        "image_encoder_and_decode_observed": True,
        "image_tokens_observed": 240,
        "parsed_response": {"value": value, "native": native},
    }
    receipt = {
        "technical_success": True,
        "cleanup_confirmed": True,
        "image_tokens_observed": 240,
        "value": value,
        "native": native,
        "accepted": accepted,
    }
    owned = {
        "cleanup_confirmed": True,
        "code": "completed" if accepted else "child_failed",
        "returncode": 0 if accepted else 2,
        "stdout": json.dumps(receipt),
    }
    terminal = {"status": "technical_or_uncertain_failure", "calls_reserved": 1, "pending": None}
    return capture, receipt, owned, terminal


@pytest.mark.parametrize(
    "value,configuration,category,wanted",
    [
        ("unknown", "unclear", [], "abstention_diagnostic_only"),
        (False, "incidental", [], "false_negative_diagnostic_only"),
        (True, "isolated_graphic_item", ["garment"], "unsupported_true_diagnostic_only"),
        (True, "isolated_physical_item", ["garment"], "supported_true_diagnostic_only"),
    ],
)
def test_native_completion_and_perception_remain_separate(value, configuration, category, wanted):
    args = evidence(value, configuration, category)
    result = reconcile_outcome(*args)
    assert result["native_technically_completed"] and result["worker_outcome_bound"]
    assert result["reconciled_outcome"] == wanted
    assert args[3]["status"] == "technical_or_uncertain_failure"
    assert not result["raw_terminal_rewritten"] and not result["retry_allowed"]
    assert not result["quality_release"] and not result["B_C_released"]


@pytest.mark.parametrize(
    "change", [{"code": "timeout"}, {"cleanup_confirmed": False}, {"returncode": 1}]
)
def test_another_owner_failure_cannot_be_reinterpreted_as_perception(change):
    capture, receipt, owned, terminal = evidence()
    result = reconcile_outcome(capture, receipt, owned | change, terminal)
    assert result["reconciled_outcome"] == "technical_or_uncertain_failure"
    assert not result["worker_outcome_bound"]


def test_native_timeout_cannot_be_reinterpreted_as_perception():
    capture, receipt, owned, terminal = evidence()
    capture.update(technical_success=False, stop_code="native_timeout", returncode=None)
    receipt["technical_success"] = False
    result = reconcile_outcome(capture, receipt, owned, terminal)
    assert not result["native_technically_completed"]
    assert result["reconciled_outcome"] == "technical_or_uncertain_failure"


@pytest.mark.parametrize(
    "change", [{"accepted": True}, {"value": False}, {"technical_success": False}]
)
def test_contradictory_receipt_is_rejected(change):
    capture, receipt, owned, terminal = evidence()
    with pytest.raises(ValueError):
        reconcile_outcome(capture, receipt | change, owned, terminal)

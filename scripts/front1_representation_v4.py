"""Fixed development-panel contracts; no inference, authority, or release writer."""

import hashlib
import io
from pathlib import Path

from PIL import Image

from scripts.visual_validation_contract_v1 import require
from scripts.vlm_prompt_development import render_control

CALLS_MAX = 17
RUN_SECONDS = 1500
CALL_SECONDS = 80
EXPECTED_TOKENS = 1056


def sha_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def validate_panel(rows):
    require(len(rows) == CALLS_MAX, "fixed_development_panel_count")
    require(all(type(row["expected_value"]) is bool for row in rows), "boolean_panel_truth")
    require(len({row["alias"] for row in rows}) == CALLS_MAX, "unique_panel_cases")
    require(
        [row["expected_value"] for row in rows] == [True] + [False] * 12 + [True] * 4,
        "fixed_early_positive_then_specificity_then_remaining_positives",
    )
    for row in rows:
        require(row["expected_tokens"] == EXPECTED_TOKENS, "fixed_representation_tokens")
        require(0 <= row["seconds"] <= 3, "frozen_early_frame_time")
        require(row["kind"] == ("positive" if row["expected_value"] else "negative"), "case_kind")
        if row["expected_value"]:
            require(
                row["admissible_categories"] == ["garment"]
                and row["admissible_configurations"]
                and 1 <= row["source_frame"] <= 4,
                "frozen_positive_support",
            )
        else:
            require("control_recipe" in row, "frozen_negative_recipe")


def input_bytes(row):
    """Reproduce only frozen existing recipes in memory, without persisting images."""
    output = io.BytesIO()
    output.name = "frozen-control.png"
    if row["kind"] == "positive":
        sheet = Path(row["sheet_path"])
        require(sha_bytes(sheet.read_bytes()) == row["sheet_sha256"], "protected_sheet_changed")
        with Image.open(sheet) as image:
            require(image.mode == "RGB" and image.size == (1280, 360), "frozen_sheet_geometry")
            index = row["source_frame"] - 1
            image.crop((320 * index, 25, 320 * (index + 1), 355)).save(output, format="PNG")
    else:
        require(row["kind"] == "negative", "fixed_input_kind")
        render_control(row["control_recipe"], output)
    raw = output.getvalue()
    require(sha_bytes(raw) == row["png_sha256"], "frozen_input_bytes_changed")
    return raw


def accepted_case(row, parsed, technical):
    if not technical:
        return False
    if parsed["value"] is not row["expected_value"]:
        return False
    if row["expected_value"]:
        return (
            parsed["native"]["presented_categories"] == row["admissible_categories"]
            and parsed["native"]["item_configuration"] in row["admissible_configurations"]
        )
    return True


def classify_case(row, receipt):
    if not receipt["technical_success"] or not receipt["cleanup_confirmed"]:
        return "technical_or_uncertain_failure"
    accepted = accepted_case(row, {"value": receipt["value"], "native": receipt["native"]}, True)
    require(accepted is receipt["accepted"], "receipt_acceptance_not_reproduced")
    if accepted:
        return "accepted_development_case"
    if receipt["value"] == "unknown":
        return "perceptual_abstention"
    return "perceptual_rejection"


def panel_outcome(rows, receipts):
    validate_panel(rows)
    require(0 < len(receipts) <= len(rows), "finite_nonempty_panel_prefix")
    outcomes = []
    for index, receipt in enumerate(receipts, 1):
        require(receipt["call_id"] == index, "sequential_case_receipts")
        outcome = classify_case(rows[index - 1], receipt)
        outcomes.append(outcome)
        require(
            outcome == "accepted_development_case" or index == len(receipts),
            "no_dispatch_after_first_failure",
        )
    passed = len(receipts) == CALLS_MAX and all(
        outcome == "accepted_development_case" for outcome in outcomes
    )
    return {
        "status": (
            "development_panel_passed_only"
            if passed
            else (
                "accepted_prefix_incomplete"
                if outcomes[-1] == "accepted_development_case"
                else outcomes[-1]
            )
        ),
        "development_panel_passed": passed,
        "positive_accepted": sum(
            outcome == "accepted_development_case"
            for row, outcome in zip(rows, outcomes)
            if row["expected_value"]
        ),
        "negative_accepted": sum(
            outcome == "accepted_development_case"
            for row, outcome in zip(rows, outcomes)
            if not row["expected_value"]
        ),
        "case_results": outcomes,
        "unexecuted_cases": len(rows) - len(receipts),
        "quality_release": False,
        "audit_released": False,
        "development_269_released": False,
        "B_C_released": False,
        "retry_allowed": False,
    }

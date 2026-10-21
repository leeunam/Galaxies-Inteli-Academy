"""Pure comparison of equivalent image work in verified terminal captures.

No process, queue, runtime, host probe or execution authority is introduced.
A partial capture is compared only over its completed common image batches.
"""

import re

from scripts.vlm_phase_diagnostic import diagnose


def _require(condition):
    if not condition:
        raise ValueError("performance_evidence_inconsistent")


def _identity(value):
    _require(
        type(value) is dict and set(value) == {"input_sha256", "command_sha256", "observation"}
    )
    for name in ("input_sha256", "command_sha256"):
        _require(type(value[name]) is str and re.fullmatch(r"[0-9a-f]{64}", value[name]))
    return value["input_sha256"], value["command_sha256"]


def _batches(observation):
    # diagnose() has already required one encoder and ordered start/done pairs.
    started = None
    batches = []
    for event in observation["events"]:
        if event["kind"] == "decode_start":
            started = event["values"]
        elif event["kind"] == "decode_done":
            batches.append((*started, event["values"][2]))
    return batches


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def compare(reference, candidate):
    """Identity pins are supplied by the caller after verifying original receipts.

    This pure function checks matching identities and phase consistency, but does
    not authenticate files or reconstruct unavailable CPU/fault/pressure counters.
    """
    _require(_identity(reference) == _identity(candidate))
    old, new = reference["observation"], candidate["observation"]
    old_phase, new_phase = diagnose(old), diagnose(new)
    _require(old_phase["image_decode_complete"] and old["stop_code"] is None)
    if new_phase["image_batches_total_announced"] is not None:
        _require(
            old_phase["image_batches_total_announced"] == new_phase["image_batches_total_announced"]
        )
    old_batches, new_batches = _batches(old), _batches(new)
    common = []
    for before, after in zip(old_batches, new_batches):
        _require(before[:3] == after[:3])
        common.append(
            {
                "index": before[0],
                "tokens": before[2],
                "reference_ms": before[3],
                "candidate_ms": after[3],
                "ratio": _ratio(after[3], before[3]),
            }
        )
    old_ms = sum(batch["reference_ms"] for batch in common)
    new_ms = sum(batch["candidate_ms"] for batch in common)
    old_encoder = old_phase["encoder_seconds_reported"]
    new_encoder = new_phase["encoder_seconds_reported"]
    return {
        "schema": "vlm-equivalent-image-work-v1",
        "input_sha256": reference["input_sha256"],
        "command_sha256": reference["command_sha256"],
        "reference_phase": old_phase,
        "candidate_phase": new_phase,
        "encoder_ratio": _ratio(new_encoder, old_encoder) if new_encoder is not None else None,
        "common_completed_batches": common,
        "common_completed_tokens": sum(batch["tokens"] for batch in common),
        "common_decode_reference_seconds": old_ms / 1000,
        "common_decode_candidate_seconds": new_ms / 1000,
        "common_decode_ratio": _ratio(new_ms, old_ms),
        "whole_capture_runtime_ratio": _ratio(new["runtime_seconds"], old["runtime_seconds"])
        if new_phase["image_decode_complete"] and new["stop_code"] is None
        else None,
        "historical_resource_cause_established": False,
        "new_execution_authorized": False,
    }

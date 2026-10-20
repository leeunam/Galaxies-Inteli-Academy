"""An allowlist projection, never a generic redactor of provider text."""

from __future__ import annotations

import json

from scripts.nim_dispatch_plan_v3 import FIXTURE, payload_bytes

PAIRS = {
    "transport": {
        "invalid_http_status",
        "http_error",
        "response_read_failed",
        "invalid_wire_type",
        "wire_byte_limit",
        "protocol_rejected",
        "request_failed_outcome_uncertain",
    },
    "utf8": {"invalid_wire_unicode", "invalid_unicode", "response_byte_limit", "response_not_text"},
    "json": {
        "envelope_duplicate_key",
        "envelope_depth_limit",
        "envelope_json_syntax",
        "json_duplicate_key",
        "json_depth_limit",
        "json_syntax",
    },
    "schema": {
        "envelope_schema_invalid",
        "schema_missing_field",
        "schema_extra_field",
        "schema_invalid_type",
        "schema_constraint",
        "schema_invalid",
    },
    "references": {"packet_hash_mismatch", "unknown_evidence_id", "duplicate_evidence_id"},
    "rendering": {"accepted"},
    "observation": {"classification_failed"},
    "sealed_validation_or_rendering": {"sealed_result_unclassified", "sealed_authority_failed"},
}
FIELDS = {
    "phase",
    "code",
    "selection_validated",
    "authority_status",
    "http_status",
    "wire_bytes",
    "completion_tokens",
    "safe_response_projection",
}


def validate_summary(value):
    if type(value) is not dict or set(value) != FIELDS:
        raise ValueError("v3_invalid_safe_summary")
    phase, code = value["phase"], value["code"]
    if type(phase) is not str or type(code) is not str or code not in PAIRS.get(phase, ()):
        raise ValueError("v3_invalid_safe_summary")
    if (
        type(value["selection_validated"]) is not bool
        or value["selection_validated"] != (code == "accepted")
        or value["authority_status"]
        not in {"accepted", "rejected", "not_invoked", "failed_before_result"}
        or (value["authority_status"] == "accepted") != value["selection_validated"]
    ):
        raise ValueError("v3_invalid_safe_summary")
    for key, lower, upper in (
        ("http_status", 100, 599),
        ("wire_bytes", 0, 16384),
        ("completion_tokens", 0, 2048),
    ):
        number = value[key]
        if number is not None and (type(number) is not int or not lower <= number <= upper):
            raise ValueError("v3_invalid_safe_summary")
    projection = value["safe_response_projection"]
    if projection is not None:
        payload_bytes()  # verify the public fixture before considering any projection
        fixture = json.loads(FIXTURE.read_bytes())
        allowed = {fact["evidence_id"] for fact in fixture["packet"]["evidence"]}
        if (
            type(projection) is not dict
            or set(projection) != {"packet_sha256", "evidence_ids"}
            or projection["packet_sha256"] != fixture["packet_sha256"]
            or type(projection["evidence_ids"]) is not list
            or not 1 <= len(projection["evidence_ids"]) <= 12
            or any(
                type(item) is not str or item not in allowed for item in projection["evidence_ids"]
            )
            or code not in {"accepted", "duplicate_evidence_id"}
        ):
            raise ValueError("v3_invalid_safe_summary")
    if value["selection_validated"] and (
        value["http_status"] != 200
        or projection is None
        or value["completion_tokens"] is None
        or value["wire_bytes"] is None
    ):
        raise ValueError("v3_invalid_safe_summary")
    return value


def summarize(result):
    observation = result["selection_observation"]
    value = {key: observation.get(key) for key in FIELDS - {"selection_validated"}}
    value["selection_validated"] = (
        observation.get("authority_accepted") is True
        and result.get("explanation", {}).get("status") == "validated_catalogue_selection"
    )
    return validate_summary(value)


def transport_failure(code):
    return validate_summary(
        {
            "phase": "transport",
            "code": code,
            "selection_validated": False,
            "authority_status": "not_invoked",
            "http_status": None,
            "wire_bytes": None,
            "completion_tokens": None,
            "safe_response_projection": None,
        }
    )

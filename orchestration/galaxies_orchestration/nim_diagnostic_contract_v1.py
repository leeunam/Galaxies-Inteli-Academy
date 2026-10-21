"""Bounded metadata only; never unknown values, rejected hashes or acceptance authority."""

PHASE_CODES = {
    "utf8": {"response_not_text", "invalid_unicode", "response_byte_limit"},
    "json": {"json_duplicate_key", "json_syntax", "json_depth_limit"},
    "schema": {
        "schema_missing_field",
        "schema_extra_field",
        "schema_invalid_type",
        "schema_constraint",
        "schema_invalid",
    },
    "references": {"packet_hash_mismatch", "unknown_evidence_id", "duplicate_evidence_id"},
    "rendering": {"accepted"},
    "observation": {"classification_failed", "diagnostic_failed"},
    "sealed_validation_or_rendering": {"sealed_result_unclassified", "sealed_authority_failed"},
    "transport": {
        "http_error",
        "protocol_rejected",
        "invalid_http_status",
        "response_read_failed",
        "invalid_wire_type",
        "wire_byte_limit",
    },
    "envelope": {
        "invalid_wire_unicode",
        "envelope_duplicate_key",
        "envelope_depth_limit",
        "envelope_json_syntax",
        "envelope_schema_invalid",
        "invalid_unicode",
        "response_byte_limit",
    },
}
CATEGORIES = {"not_observed", "missing", "null", "string", "array", "object", "number", "boolean"}
SLOTS = ("selection", "packet_sha256", "evidence_ids", "evidence_ids[*]")
STATUSES = {"not_invoked", "accepted", "rejected", "failed_before_result"}


def empty_diagnostic(status="not_invoked", *, phase="observation", code="diagnostic_failed"):
    return {
        "schema_version": "public-three-selection-diagnostic-v1",
        "authority_status": status,
        "phase": phase,
        "code": code,
        "classifier_parity": None,
        "types": {slot: ["not_observed"] for slot in SLOTS},
        "cardinality": None,
        "duplicates": None,
        "all_ids_in_catalog": None,
        "packet_hash_equal": None,
    }


def validate_diagnostic(value):
    if (
        type(value) is not dict
        or set(value) != set(empty_diagnostic())
        or (
            value["schema_version"] != "public-three-selection-diagnostic-v1"
            or type(value["authority_status"]) is not str
            or value["authority_status"] not in STATUSES
            or type(value["phase"]) is not str
            or type(value["code"]) is not str
            or value["code"] not in PHASE_CODES.get(value["phase"], ())
        )
    ):
        raise ValueError("diagnostic_invalid_metadata")
    for key in ("classifier_parity", "duplicates", "all_ids_in_catalog", "packet_hash_equal"):
        if value[key] is not None and type(value[key]) is not bool:
            raise ValueError("diagnostic_invalid_boolean")
    count = value["cardinality"]
    if count is not None and (type(count) is not int or not 0 <= count <= 16384):
        raise ValueError("diagnostic_invalid_cardinality")
    types = value["types"]
    if type(types) is not dict or set(types) != set(SLOTS):
        raise ValueError("diagnostic_invalid_slots")
    for key, entries in types.items():
        if (
            type(entries) is not list
            or len(entries) > len(CATEGORIES)
            or any(type(item) is not str or item not in CATEGORIES for item in entries)
            or entries != sorted(set(entries))
            or (key != "evidence_ids[*]" and len(entries) != 1)
        ):
            raise ValueError("diagnostic_invalid_types")
    if value["code"] == "accepted" and value["authority_status"] != "accepted":
        raise ValueError("diagnostic_cannot_grant_acceptance")
    if value["authority_status"] == "accepted" and value["code"] not in {
        "accepted",
        "classification_failed",
        "diagnostic_failed",
        "sealed_result_unclassified",
    }:
        raise ValueError("diagnostic_contradicts_authority")
    if types["evidence_ids"] != ["array"] and any(
        value[key] is not None for key in ("cardinality", "duplicates", "all_ids_in_catalog")
    ):
        raise ValueError("diagnostic_array_not_observed")
    if types["packet_sha256"] != ["string"] and value["packet_hash_equal"] is not None:
        raise ValueError("diagnostic_hash_not_observed")
    if count is not None and count < 2 and value["duplicates"] is True:
        raise ValueError("diagnostic_impossible_duplicate_count")
    if value["code"] == "accepted" and (
        value["classifier_parity"] is not True
        or types
        != {
            "selection": ["object"],
            "packet_sha256": ["string"],
            "evidence_ids": ["array"],
            "evidence_ids[*]": ["string"],
        }
        or count is None
        or not 1 <= count <= 12
        or value["duplicates"] is not False
        or value["all_ids_in_catalog"] is not True
        or value["packet_hash_equal"] is not True
    ):
        raise ValueError("diagnostic_contradicts_authority")
    return value


def execute_remote(*args, **kwargs):
    # No plan read, nonce, reservation, credential getter, child or socket.
    raise ValueError("diagnostic_remote_authorization_absent")

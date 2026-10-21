"""Closed optional HTTP-error metadata; never selection authority or an HTTP client."""

import re

SCHEMA = "nim-http-error-metadata-v1"
REQUEST_STATES = {"captured", "missing", "invalid", "duplicate", "unavailable"}
FRAMING_STATES = {"supported", "unsupported", "missing", "invalid", "duplicate", "unavailable"}
UUID_PATTERN = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


def validate_error_metadata(value):
    if type(value) is not dict or set(value) != {
        "schema_version",
        "http_status",
        "request_id",
        "request_id_state",
        "framing_state",
        "body_read",
    }:
        raise ValueError("http_error_metadata_invalid_shape")
    if (
        value["schema_version"] != SCHEMA
        or type(value["http_status"]) is not int
        or not 100 <= value["http_status"] <= 599
        or value["http_status"] == 200
        or value["body_read"] is not False
        or type(value["request_id_state"]) is not str
        or value["request_id_state"] not in REQUEST_STATES
        or type(value["framing_state"]) is not str
        or value["framing_state"] not in FRAMING_STATES
    ):
        raise ValueError("http_error_metadata_invalid_value")
    request_id = value["request_id"]
    if value["request_id_state"] == "captured":
        if type(request_id) is not str or not re.fullmatch(UUID_PATTERN, request_id):
            raise ValueError("http_error_metadata_invalid_request_id")
    elif request_id is not None:
        raise ValueError("http_error_metadata_unobserved_request_id")
    return value


def execute_remote(*args, **kwargs):
    raise ValueError("http_error_observation_no_remote_release")

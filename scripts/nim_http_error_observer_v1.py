"""Offline additive observer for an already-open response; no body read on HTTP errors."""

import re

from orchestration.galaxies_orchestration.nim_http_error_metadata_v1 import (
    SCHEMA,
    UUID_PATTERN,
    validate_error_metadata,
)
from scripts.nim_diagnostic_http_adapter_v1 import observe_opened_response as sealed_observe

REQUEST_HEADER = "nvcf-reqid"
FRAMING_HEADERS = ("content-type", "content-length", "content-encoding", "transfer-encoding")
MAX_FIELD_CHARS = 128


def _field(headers, name):
    # Only five named fields are queried; never enumerate all headers/cookies.
    try:
        values = headers.get_all(name)
    except Exception:  # noqa: BLE001 - arbitrary header exceptions never leave
        return "unavailable", None
    if values is None or (type(values) is list and not values):
        return "missing", None
    if type(values) is not list:
        return "invalid", None
    if len(values) > 1:
        return "duplicate", None
    value = values[0]
    if type(value) is not str or len(value) > MAX_FIELD_CHARS:
        return "invalid", None
    return "present", value


def _framing(headers):
    observed = {name: _field(headers, name) for name in FRAMING_HEADERS}
    states = {state for state, _ in observed.values()}
    for state in ("unavailable", "duplicate", "invalid"):
        if state in states:
            return state
    if states == {"missing"}:
        return "missing"
    values = {name: value for name, (_, value) in observed.items()}
    content_type = values["content-type"]
    length = values["content-length"]
    encoding = values["content-encoding"]
    transfer = values["transfer-encoding"]
    supported = (
        content_type is not None
        and content_type.split(";", 1)[0].strip().lower() == "application/json"
        and (encoding is None or encoding.strip().lower() == "identity")
        and (transfer is None or transfer.strip().lower() == "chunked")
        and not (length is not None and transfer is not None)
        and (length is None or (length.isascii() and length.isdecimal() and int(length) <= 16384))
    )
    return "supported" if supported else "unsupported"


def _error_metadata(response, status):
    try:
        headers = response.headers
    except Exception:  # noqa: BLE001 - no arbitrary errors/paths projected
        headers = None
    state, request_id = _field(headers, REQUEST_HEADER)
    if state == "present":
        if len(request_id) == 36 and re.fullmatch(UUID_PATTERN, request_id.lower()):
            state, request_id = "captured", request_id.lower()
        else:
            state, request_id = "invalid", None
    result = {
        "schema_version": SCHEMA,
        "http_status": status,
        "request_id": request_id,
        "request_id_state": state,
        "framing_state": _framing(headers),
        "body_read": False,
    }
    return validate_error_metadata(result)


def observe_opened_response(context, response):
    # Original envelope/selection/render authority runs unchanged, exactly once.
    result = sealed_observe(context, response)
    status = result["transport"]["http_status"]
    metadata = _error_metadata(response, status) if status is not None and status != 200 else None
    return result | {"http_error_metadata": metadata}

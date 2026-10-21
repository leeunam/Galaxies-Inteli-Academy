"""Adversarial fake HTTP responses; no real key, socket, model or remote release."""

import json
from email.message import Message

import pytest

from orchestration.galaxies_orchestration.nim_graph_contract_v1 import fixture
from orchestration.galaxies_orchestration.nim_http_error_metadata_v1 import (
    execute_remote,
    validate_error_metadata,
)
from scripts.nim_diagnostic_http_adapter_v1 import observe_opened_response as sealed_observe
from scripts.nim_diagnostic_worker_v1 import invented_response
from scripts.nim_http_error_observer_v1 import (
    FRAMING_HEADERS,
    REQUEST_HEADER,
    observe_opened_response,
)
from tests.test_nim_graph_rejection_audit_v1 import (
    no_network_key_or_model,  # noqa: F401
    prepared_session,
)

PUBLIC_ID = "12345678-1234-1234-1234-123456789abc"
SECRET = "ENTIRELY_INVENTED_AUTH_COOKIE_BODY_SECRET"
SECRET_UUID = "abcdefab-abcd-abcd-abcd-abcdefabcdef"
ALLOWED = (REQUEST_HEADER, *FRAMING_HEADERS)


class Headers(Message):
    def __init__(self, entries):
        super().__init__()
        self.lookups = []
        for key, value in entries:
            self[key] = value

    def get_all(self, name, *args):
        assert name in ALLOWED
        self.lookups.append(name)
        return super().get_all(name, *args)


class ErrorResponse:
    def __init__(self, entries=(), status=503):
        self.status = status
        self.headers = Headers(entries)
        self.reads = 0

    def getheaders(self):
        raise AssertionError("must_not_enumerate_unknown_headers_or_cookies")

    def read(self, size):
        self.reads += 1
        raise AssertionError("error_body_must_not_be_read_" + SECRET)


def observed(entries=(), status=503):
    response = ErrorResponse(entries, status)
    result = observe_opened_response(None, response)
    expected = sealed_observe(None, ErrorResponse(entries, status))
    assert {key: value for key, value in result.items() if key != "http_error_metadata"} == expected
    assert response.reads == 0
    assert result["selection"] is None
    assert result["diagnostic"]["authority_status"] == "not_invoked"
    metadata = result["http_error_metadata"]
    if metadata is not None:
        assert validate_error_metadata(metadata) is metadata
    return response, result


def test_error_projection_is_additive_bounded_and_never_queries_secrets():
    entries = [
        ("NVCF-REQID", PUBLIC_ID.upper()),
        ("Content-Type", "application/json"),
        ("Content-Length", "42"),
        ("Authorization", SECRET),
        ("Set-Cookie", SECRET_UUID),
        ("X-Unknown", "f" * 64),
    ]
    response, result = observed(entries)
    legacy = sealed_observe(None, ErrorResponse(entries))
    assert {key: value for key, value in result.items() if key != "http_error_metadata"} == legacy
    assert result["http_error_metadata"] == {
        "schema_version": "nim-http-error-metadata-v1",
        "http_status": 503,
        "request_id": PUBLIC_ID,
        "request_id_state": "captured",
        "framing_state": "supported",
        "body_read": False,
    }
    assert response.headers.lookups == list(ALLOWED)
    serialized = json.dumps(result)
    assert SECRET not in serialized and SECRET_UUID not in serialized and "f" * 64 not in serialized
    assert result["transport"]["wire_bytes"] is None
    assert result["transport"]["completion_tokens"] is None
    assert result["diagnostic"]["code"] == "http_error"


@pytest.mark.parametrize(
    "value",
    [
        SECRET,
        "f" * 64,
        "Bearer " + SECRET,
        " " + PUBLIC_ID,
        PUBLIC_ID + "\r\n" + SECRET,
        PUBLIC_ID + "," + PUBLIC_ID,
        "x" * 129,
        "é" * 36,
    ],
)
def test_unknown_request_id_values_are_not_retained(value):
    _, result = observed([("nvcf-reqid", value)])
    assert result["http_error_metadata"]["request_id_state"] == "invalid"
    assert result["http_error_metadata"]["request_id"] is None
    assert value not in json.dumps(result)


def test_duplicate_id_is_absent_even_when_both_values_are_identical():
    _, result = observed([("nvcf-reqid", PUBLIC_ID), ("NVCF-REQID", PUBLIC_ID)])
    assert result["http_error_metadata"]["request_id_state"] == "duplicate"
    assert result["http_error_metadata"]["request_id"] is None


@pytest.mark.parametrize(
    "entries,state",
    [
        ([], "missing"),
        ([("content-type", "text/html")], "unsupported"),
        ([("content-type", "application/json"), ("content-encoding", "gzip")], "unsupported"),
        ([("content-type", "application/json"), ("content-length", "16385")], "unsupported"),
        ([("content-type", "application/json"), ("content-length", "-1")], "unsupported"),
        ([("content-type", "application/json"), ("content-length", "16384")], "supported"),
        ([("content-type", "application/json"), ("transfer-encoding", "chunked")], "supported"),
        (
            [
                ("content-type", "application/json"),
                ("content-length", "12"),
                ("transfer-encoding", "chunked"),
            ],
            "unsupported",
        ),
        ([("content-type", "application/json"), ("Content-Type", "application/json")], "duplicate"),
        ([("content-type", "x" * 129)], "invalid"),
    ],
)
def test_framing_metadata_never_changes_legacy_error_or_reads_body(entries, state):
    _, result = observed(entries)
    assert result["http_error_metadata"]["framing_state"] == state
    assert result["diagnostic"]["code"] == "http_error"
    assert result["transport"]["http_status"] == 503


@pytest.mark.parametrize("status", [201, 301, 400, 401, 402, 429, 500, 503, 599])
def test_non200_status_is_observed_without_retry_or_cause_inference(status):
    _, result = observed(status=status)
    assert result["http_error_metadata"]["http_status"] == status
    assert result["http_error_metadata"]["request_id_state"] == "missing"


@pytest.mark.parametrize("status", [None, True, "503", 99, 600])
def test_invalid_status_never_becomes_error_metadata(status):
    _, result = observed(status=status)
    assert result["http_error_metadata"] is None
    assert result["diagnostic"]["code"] == "invalid_http_status"


def test_header_accessor_failure_is_static_and_does_not_leak_exception():
    response = ErrorResponse()

    class Failed:
        def get_all(self, name):
            raise RuntimeError(SECRET)

    response.headers = Failed()
    result = observe_opened_response(None, response)
    expected = sealed_observe(None, ErrorResponse())
    assert {key: value for key, value in result.items() if key != "http_error_metadata"} == expected
    assert result["http_error_metadata"]["request_id_state"] == "unavailable"
    assert result["http_error_metadata"]["framing_state"] == "unavailable"
    assert SECRET not in json.dumps(result)
    assert response.reads == 0


@pytest.mark.parametrize("value", [SECRET, (PUBLIC_ID,), 17, [None], [True], [{}], [[]]])
def test_malformed_accessor_types_cannot_change_the_original_result(value):
    response = ErrorResponse()

    class Malformed:
        def get_all(self, name):
            assert name in ALLOWED
            return value

    response.headers = Malformed()
    result = observe_opened_response(None, response)
    expected = sealed_observe(None, ErrorResponse())
    assert {key: item for key, item in result.items() if key != "http_error_metadata"} == expected
    assert result["http_error_metadata"]["request_id_state"] == "invalid"
    assert result["http_error_metadata"]["framing_state"] == "invalid"
    assert SECRET not in json.dumps(result)
    assert response.reads == 0


@pytest.mark.parametrize("case", ["valid", "wrong_hash", "secret_id"])
def test_200_delegates_original_authority_without_request_id_requirement(case):
    context = prepared_session().session.context
    result = observe_opened_response(context, invented_response(case, fixture()))
    expected = sealed_observe(context, invented_response(case, fixture()))
    assert {key: value for key, value in result.items() if key != "http_error_metadata"} == expected
    assert result["http_error_metadata"] is None
    assert (result["selection"] is not None) == (case == "valid")


def test_200_does_not_access_additional_headers_at_all():
    source = invented_response("valid", fixture())

    class OriginalResponseOnly:
        status = 200

        @property
        def headers(self):
            raise AssertionError("sidecar_headers_must_not_be_accessed_for_200")

        def getheaders(self):
            return source.getheaders()

        def read(self, size):
            return source.read(size)

    context = prepared_session().session.context
    result = observe_opened_response(context, OriginalResponseOnly())
    expected = sealed_observe(context, invented_response("valid", fixture()))
    assert {key: value for key, value in result.items() if key != "http_error_metadata"} == expected
    assert result["http_error_metadata"] is None
    assert result["selection"] is not None


@pytest.mark.parametrize(
    "change",
    [
        {"request_id": SECRET},
        {"request_id_state": SECRET},
        {"framing_state": SECRET},
        {"http_status": True},
        {"http_status": 200},
        {"body_read": True},
        {"unknown": SECRET},
    ],
)
def test_closed_schema_refuses_unknown_or_contradictory_metadata(change):
    value = {
        "schema_version": "nim-http-error-metadata-v1",
        "http_status": 503,
        "request_id": None,
        "request_id_state": "missing",
        "framing_state": "missing",
        "body_read": False,
    } | change
    with pytest.raises(ValueError, match="^http_error_metadata_") as caught:
        validate_error_metadata(value)
    assert SECRET not in str(caught.value)


def test_remote_entry_has_no_authorization_or_effects():
    effects = []
    with pytest.raises(ValueError, match="^http_error_observation_no_remote_release$"):
        execute_remote(lambda: effects.append("forbidden"))
    assert effects == []

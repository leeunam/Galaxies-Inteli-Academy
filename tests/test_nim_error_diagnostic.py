"""One fake request per case; real credentials and sockets are forbidden."""

import hashlib
import http.client
import io
import json
from email.message import Message

import pytest

from orchestration.galaxies_orchestration import nim_http as legacy
from scripts import nim_global_fixed_http_v1 as fixed
from scripts import nim_http_error_diagnostic as client

KEY = "ENTIRELY_INVENTED_API_KEY_0123456789"
REQUEST_ID = "12345678-1234-1234-1234-123456789abc"
EXHAUSTED = "ResourceExhausted: Worker local total request limit reached (16/16)"


class Headers(Message):
    def get_all(self, name, *args):
        assert name in client.ERROR_HEADERS
        return super().get_all(name, *args)


class Response:
    def __init__(self, status, body, entries=()):
        self.status = status
        self.headers = Headers()
        self.headers["Authorization"] = "Bearer " + KEY
        self.headers["Set-Cookie"] = KEY
        for name, value in entries:
            self.headers[name] = value
        self.body = io.BytesIO(body)
        self.read_sizes = []

    def read(self, size):
        assert size == client.MAX_BYTES + 1
        self.read_sizes.append(size)
        return self.body.read(size)


def exchange(monkeypatch, response):
    calls = []
    monkeypatch.setattr(legacy, "existing_key", lambda *a: pytest.fail("real_key_forbidden"))
    monkeypatch.setattr(http.client, "HTTPSConnection", lambda *a, **k: pytest.fail("socket"))

    class FakeConnection:
        def __init__(self, host, *, port, timeout, context):
            assert (host, port, timeout) == ("integrate.api.nvidia.com", 443, 45)
            calls.append("connection")

        def set_debuglevel(self, level):
            assert level == 0

        def request(self, method, path, **kwargs):
            assert (method, path) == ("POST", "/v1/chat/completions")
            assert kwargs["headers"]["Authorization"] == "Bearer " + KEY
            body = kwargs["body"]
            assert len(body) == 10065
            assert hashlib.sha256(body).hexdigest() == fixed.PAYLOAD_SHA256
            calls.append("request")

        def getresponse(self):
            return response

        def close(self):
            calls.append("close")

    connection, opened = fixed._open_response(KEY, factory=FakeConnection, timeout=45)
    try:
        result = {
            "status": "http_error",
            "http_status": opened.status,
            "error_diagnostic": client.read_error_diagnostic(opened, secrets=(KEY,)),
        }
    finally:
        connection.close()
    assert calls == ["connection", "request", "close"]
    assert KEY not in json.dumps(result)
    return result


@pytest.mark.parametrize("nested", [False, True])
def test_known_worker_exhaustion_top_and_nested_survive(monkeypatch, nested):
    fields = {"code": "503", "type": "Service Unavailable", "message": EXHAUSTED}
    response = Response(
        503,
        json.dumps({"error": fields} if nested else fields).encode(),
        [
            ("nvcf-reqid", REQUEST_ID.upper()),
            ("Content-Type", "application/json"),
            ("Retry-After", "5"),
            ("Date", "Thu, 22 Oct 2026 15:31:52 GMT"),
        ],
    )
    result = exchange(monkeypatch, response)
    assert (result["status"], result["http_status"]) == ("http_error", 503)
    diagnostic = result["error_diagnostic"]
    assert diagnostic["fields"]["error" if nested else "top"] == fields
    assert diagnostic["request_id"] == REQUEST_ID
    assert diagnostic["headers"]["retry-after"] == 5
    assert diagnostic["headers"]["date"] == "Thu, 22 Oct 2026 15:31:52 +0000"
    assert response.read_sizes == [client.MAX_BYTES + 1]


@pytest.mark.parametrize("status", [401, 403, 429, 503])
def test_error_status_and_message_preserved_without_retry(monkeypatch, status):
    result = exchange(monkeypatch, Response(status, b'{"detail":"Service unavailable"}'))
    assert result["http_status"] == status
    assert result["error_diagnostic"]["fields"]["top"]["detail"] == "Service unavailable"


def test_secret_payload_and_unknown_fields_are_removed_before_truncation(monkeypatch):
    image = "QWxwaGFCZXRh" * 100
    error = {
        "message": f"Bearer {KEY} data:image/png;base64,{image} "
        "api_key=SECOND_SECRET secret=SHORT https://private.example/video " + "é" * 1000,
        "Authorization": KEY,
        "image": image,
    }
    result = exchange(monkeypatch, Response(503, json.dumps(error).encode()))
    diagnostic = result["error_diagnostic"]
    serialized = json.dumps(diagnostic, ensure_ascii=False)
    for forbidden in [
        KEY,
        image,
        "SECOND_SECRET",
        "SHORT",
        "data:image",
        "private.example",
    ]:
        assert forbidden not in serialized
    assert diagnostic["field_truncated"] is True
    message = diagnostic["fields"]["top"]["message"]
    assert len(message) <= 512
    assert message.encode().decode() == message
    assert len(serialized.encode()) < 8192


@pytest.mark.parametrize(
    "body,state",
    [
        pytest.param(b"x" * 20000, "limit_exceeded", id="oversized"),
        pytest.param(b"not JSON", "not_json", id="not-json"),
        pytest.param(b"[]", "unsupported_shape", id="array"),
        pytest.param(b"\xff", "not_json", id="invalid-utf8"),
    ],
)
def test_unparseable_or_oversized_body_is_never_copied(monkeypatch, body, state):
    result = exchange(monkeypatch, Response(503, body))
    assert result["error_diagnostic"]["body_state"] == state
    assert result["error_diagnostic"]["fields"] == {}


@pytest.mark.parametrize(
    "entries",
    [
        [("nvcf-reqid", KEY)],
        [("nvcf-reqid", REQUEST_ID), ("nvcf-reqid", REQUEST_ID)],
        [("nvcf-reqid", REQUEST_ID + "\r\n" + KEY)],
        [("content-type", KEY)],
        [("date", KEY)],
        [("retry-after", KEY)],
        [("content-length", KEY)],
    ],
)
def test_malformed_duplicate_or_secret_headers_are_omitted(entries):
    diagnostic = client.error_diagnostic(Response(503, b"{}", entries), b"{}", secrets=(KEY,))
    assert diagnostic["request_id"] is None
    assert diagnostic["headers"] == {}
    assert KEY not in json.dumps(diagnostic)


def test_success_body_and_selection_are_never_read_or_changed():
    response = Response(200, b'{"choices":[{"content":"preserved"}]}')
    with pytest.raises(ValueError, match="^http_error_required$"):
        client.read_error_diagnostic(response, secrets=(KEY,))
    assert response.read_sizes == []


def test_projection_total_size_is_bounded_for_all_unicode_fields():
    fields = dict.fromkeys(client.ERROR_FIELDS, "😀" * 600)
    body = json.dumps(fields | {"error": fields}, ensure_ascii=False).encode()
    assert len(body) > client.MAX_BYTES
    too_large = client.error_diagnostic(Response(503, body), body)
    assert too_large["fields"] == {}
    fields = dict.fromkeys(client.ERROR_FIELDS, "é" * 500)
    body = json.dumps(fields | {"error": fields}, ensure_ascii=False).encode()
    projected = client.error_diagnostic(Response(503, body), body)
    assert len(json.dumps(projected).encode()) < 16384


def test_failed_header_accessor_and_body_read_never_leak_exceptions(monkeypatch):
    class Failed:
        def get_all(self, name):
            raise RuntimeError(KEY)

    response = Response(503, b"")
    response.headers = Failed()
    response.read = lambda size: (_ for _ in ()).throw(RuntimeError(KEY))
    result = exchange(monkeypatch, response)
    assert result["error_diagnostic"]["body_state"] == "unavailable"
    assert result["error_diagnostic"]["headers"] == {}

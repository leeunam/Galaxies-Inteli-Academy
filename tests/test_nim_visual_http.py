"""Real client path with fake transport and private capture, never a live request."""

import copy
import http.client
import io
import json
import os
from email.message import Message
from itertools import permutations

import pytest

from scripts import nim_visual_http as client

KEY = "ENTIRELY_INVENTED_API_KEY_0123456789"
REASONING = "ENTIRELY_INVENTED_PRIVATE_REASONING"
REQUEST_ID = "12345678-1234-1234-1234-123456789abc"
NEGATIVE = '{"state":"no_target","item_configuration":"absent","presented_categories":[]}'
POSITIVE = (
    '{"state":"presented_target","item_configuration":"hand_holds_hanger_out",'
    '"presented_categories":["garment"]}'
)
UNKNOWN = '{"state":"uncertain","item_configuration":"unclear","presented_categories":[]}'


def envelope(model=client.MODEL, content=NEGATIVE):
    return {
        "model": model,
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "role": "assistant",
                    "content": content,
                    "reasoning_content": REASONING,
                },
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 24, "total_tokens": 124},
    }


class Headers(Message):
    def get_all(self, name, *args):
        assert name.lower() in {
            "nvcf-reqid",
            "x-request-id",
            "content-type",
            "content-length",
            "date",
            "retry-after",
        }
        return super().get_all(name, *args)


class Response:
    def __init__(self, wire, status=200, mime="application/json", partial=False):
        self.status = status
        self.headers = Headers()
        self.headers["Content-Type"] = mime
        self.headers["nvcf-reqid"] = REQUEST_ID
        self.headers["Authorization"] = "Bearer " + KEY
        self.headers["Set-Cookie"] = KEY
        self.body = wire if type(wire) is bytes else json.dumps(wire).encode()
        self.stream = io.BytesIO(self.body)
        self.reads = 0
        self.partial = partial

    def getheaders(self):
        return list(self.headers.items())

    def read(self, size):
        assert size == 16385
        self.reads += 1
        if self.partial:
            raise http.client.IncompleteRead(self.body, 100)
        return self.stream.read(size)


@pytest.fixture(autouse=True)
def no_real_network(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("real_network_forbidden")

    monkeypatch.setattr(http.client, "HTTPSConnection", forbidden)


def run(response, tmp_path, *, sink_failure=False, identity_policy="exact", monkeypatch=None):
    events = []
    target = tmp_path / "capture.json"
    body = (
        json.dumps({"model": client.MODEL}).encode()
        if identity_policy != "exact"
        else b"entirely invented fixed payload"
    )

    def persist(capture):
        events.append("persist")
        if sink_failure:
            raise OSError(KEY)
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as handle:
            json.dump(capture, handle, allow_nan=False)
            handle.flush()
            os.fsync(handle.fileno())

    class Connection:
        def __init__(self, host, *, port, timeout, context):
            assert (host, port, timeout) == (client.HOST, 443, 70)
            events.append("connect")

        def set_debuglevel(self, level):
            assert level == 0

        def request(self, method, path, **kwargs):
            assert (method, path) == ("POST", client.PATH)
            assert kwargs["body"] == body
            assert kwargs["headers"]["Authorization"] == "Bearer " + KEY
            events.append("request")

        def getresponse(self):
            return response

        def close(self):
            events.append("close")

    if identity_policy != "exact":
        assert monkeypatch is not None
        monkeypatch.setattr(http.client, "HTTPSConnection", Connection)
    result = client.exchange(
        body, KEY, factory=Connection, timeout=70, persist=persist, identity_policy=identity_policy
    )
    assert events == ["connect", "request", "persist", "close"]
    assert response.reads == 1
    assert KEY not in json.dumps(result) and REASONING not in json.dumps(result)
    saved = json.loads(target.read_text()) if target.exists() else None
    if saved is not None:
        assert KEY not in target.read_text() and REASONING not in target.read_text()
        assert target.stat().st_mode & 0o777 == 0o600
    return result, saved, target


@pytest.mark.parametrize(
    "identifier", [client.MODEL, client.MODEL.split("/", 1)[1], client.DOCUMENTED_ALIAS]
)
@pytest.mark.parametrize("content,expected", [(NEGATIVE, False), (POSITIVE, True)])
def test_exact_known_identities_and_visual_answers(identifier, content, expected, tmp_path):
    result, capture, _ = run(Response(envelope(identifier, content)), tmp_path)
    assert result["technical_success"] is True and result["parsed"]["value"] is expected
    assert capture["model"]["value"] == identifier
    assert capture["choices"][0]["content"]["text"] == content
    assert result["request_id"] == REQUEST_ID and result["completion_tokens"] == 24


@pytest.mark.parametrize(
    "kind", ["missing", "null", "foreign", "checkpoint_name", "private_backend"]
)
def test_identity_failures_preserve_answer_before_rejection(kind, tmp_path, monkeypatch):
    wire = envelope()
    if kind == "missing":
        wire.pop("model")
    else:
        wire["model"] = {
            "null": None,
            "foreign": "other/vision-v1",
            "checkpoint_name": "NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-NVFP4",
            "private_backend": "private/nvidia/nemotron-3.5-super-120b-a12b",
        }[kind]
    monkeypatch.setattr(
        client, "_parse_visual", lambda _: pytest.fail("identity_must_precede_scoring")
    )
    result, capture, _ = run(Response(wire), tmp_path)
    assert result["status"] == "returned_model_unverified" and result["parsed"] is None
    assert result["observed_key_order"] is None
    assert capture["choices"][0]["content"]["text"] == NEGATIVE
    assert capture["model"]["present"] is (kind != "missing")
    if kind in {"foreign", "checkpoint_name", "private_backend"}:
        assert capture["model"]["value"] == wire["model"]


def test_capture_is_persisted_before_visual_parser(tmp_path, monkeypatch):
    original = client._parse_visual

    def inspect(content):
        saved = json.loads((tmp_path / "capture.json").read_text())
        assert saved["choices"][0]["content"]["text"] == content
        return original(content)

    monkeypatch.setattr(client, "_parse_visual", inspect)
    assert run(Response(envelope()), tmp_path)[0]["technical_success"] is True


@pytest.mark.parametrize("status", [401, 403, 429, 503, 410])
@pytest.mark.parametrize("mime", ["application/json", "application/problem+json"])
def test_http_error_paths_preserve_body_and_headers(status, mime, tmp_path):
    message = "ResourceExhausted: Worker local total request limit reached (16/16)"
    wire = {"error": {"code": str(status), "message": message}, "title": "Gone"}
    result, capture, _ = run(Response(wire, status=status, mime=mime), tmp_path)
    assert result["status"] == "http_error" and result["technical_success"] is False
    assert capture["error"]["fields"]["error"]["message"] == message
    assert capture["headers"]["content-type"] == mime
    assert capture["request_id"] == REQUEST_ID


def test_unknown_never_becomes_false(tmp_path):
    result, capture, _ = run(Response(envelope(content=UNKNOWN)), tmp_path)
    assert result["technical_success"] is True
    assert result["parsed"]["value"] is not True and result["parsed"]["value"] is not False
    assert capture["choices"][0]["content"]["text"] == UNKNOWN


@pytest.mark.parametrize(
    "kind", ["mime", "role", "length", "tools", "schema", "duplicates", "choices"]
)
def test_later_checks_keep_the_original_answer(kind, tmp_path):
    wire = envelope()
    content = NEGATIVE
    mime = "text/plain" if kind == "mime" else "application/json"
    if kind == "role":
        wire["choices"][0]["message"]["role"] = "user"
    if kind == "length":
        wire["choices"][0]["finish_reason"] = "length"
    if kind == "tools":
        wire["choices"][0]["message"]["tool_calls"] = [{"secret": KEY}]
    if kind == "schema":
        content = "```json\n" + NEGATIVE + "\n```"
        wire["choices"][0]["message"]["content"] = content
    if kind == "choices":
        wire["choices"].append(copy.deepcopy(wire["choices"][0]))
    if kind == "duplicates":
        wire = json.dumps(wire).replace('"model":', '"model":"other", "model":', 1).encode()
    result, capture, _ = run(Response(wire, mime=mime), tmp_path)
    assert result["technical_success"] is False
    assert capture["choices"][0]["content"]["text"] == content


@pytest.mark.parametrize(
    "content",
    [
        KEY,
        "Bearer " + KEY,
        "data:image/png;base64," + "QUFB" * 100,
        '{"image":"QUFB\\nQUFB"}',
        "<think>" + REASONING + "</think>" + NEGATIVE,
    ],
)
def test_secret_and_request_echoes_are_quarantined(tmp_path, content):
    result, capture, target = run(Response(envelope(content=content)), tmp_path)
    assert result["technical_success"] is False
    text = target.read_text()
    assert KEY not in text and REASONING not in text and "data:image" not in text
    assert capture["choices"][0]["content"]["redacted"] is True


@pytest.mark.parametrize(
    "wire,state",
    [
        (b"not JSON", "invalid_json"),
        (b"x" * 16385, "limit_exceeded"),
        (b"\xff", "invalid_json"),
        (b"[]", "invalid_shape"),
    ],
    ids=["malformed", "oversize", "utf8", "array"],
)
def test_bad_envelopes_have_explicit_persisted_reason(wire, state, tmp_path):
    result, capture, _ = run(Response(wire), tmp_path)
    assert not result["technical_success"] and capture["body_state"] == state


def test_partial_read_retains_content_without_acceptance(tmp_path):
    result, capture, _ = run(Response(envelope(), partial=True), tmp_path)
    assert result["status"] == "response_read_failed"
    assert capture["choices"][0]["content"]["text"] == NEGATIVE


def test_storage_failure_never_reaches_scoring(tmp_path, monkeypatch):
    monkeypatch.setattr(client, "_parse_visual", lambda _: pytest.fail("no_capture_no_scoring"))
    result, capture, _ = run(Response(envelope()), tmp_path, sink_failure=True)
    assert result["status"] == "response_capture_failed" and capture is None


def test_missing_capture_sink_refuses_before_connection():
    with pytest.raises(client.CapturePersistenceError, match="private_capture_sink_required"):
        client.exchange(
            b"invented",
            KEY,
            factory=lambda *a, **k: pytest.fail("no_connection"),
            timeout=70,
            persist=None,
        )


@pytest.mark.parametrize("value", [17, True, {}, [], "\ud800"])
def test_invalid_model_metadata_never_discards_valid_answer(value, tmp_path):
    result, capture, _ = run(Response(envelope(model=value)), tmp_path)
    assert result["technical_success"] is False
    assert capture["choices"][0]["content"]["text"] == NEGATIVE
    assert capture["model"]["value"] is None


def test_invalid_unicode_error_cannot_prevent_private_capture(tmp_path):
    result, capture, _ = run(
        Response({"detail": "\ud800"}, status=410, mime="application/problem+json"), tmp_path
    )
    assert result["status"] == "http_error"
    assert capture["error"]["body_state"] == "json"


def test_timeout_still_persists_headers_before_rejection(tmp_path):
    class TimeoutResponse(Response):
        def read(self, size):
            self.reads += 1
            raise TimeoutError(KEY)

    result, capture, _ = run(TimeoutResponse(envelope()), tmp_path)
    assert result["status"] == "response_read_failed"
    assert capture["request_id"] == REQUEST_ID and capture["read_state"] == "timeout"


@pytest.mark.parametrize("model", ["vendor/" + "VisionX" * 20, "vendor/" + KEY])
def test_unknown_long_identifier_is_kept_but_credentials_are_not(model, tmp_path):
    result, capture, _ = run(Response(envelope(model=model)), tmp_path)
    assert result["status"] == "returned_model_unverified"
    if KEY in model:
        assert capture["model"]["state"] == "redacted" and capture["model"]["value"] is None
    else:
        assert capture["model"]["value"] == model
    assert capture["choices"][0]["content"]["text"] == NEGATIVE


def test_hosted_semantics_preserve_all_22_objects_in_all_key_orders():
    from jsonschema import Draft202012Validator

    from scripts import vlm_product_v15 as semantic
    from scripts import vlm_product_v16 as ordered

    validator = Draft202012Validator(ordered.specification("state_first")["schema"])
    expected = {
        "presented_target": True,
        "no_target": False,
        "incidental_only": False,
        "uncertain": "unknown",
    }
    objects = checks = strict_order_accepts = 0
    for config, row in semantic.PROJECTION.items():
        for category in row["categories"] or [None]:
            native = {
                "item_configuration": config,
                "state": row["state"],
                "presented_categories": [category] if category is not None else [],
            }
            objects += 1
            for keys in permutations(native):
                raw = json.dumps({key: native[key] for key in keys})
                parsed = client._parse_visual(raw)
                assert validator.is_valid(parsed["native"])
                assert parsed["native"] == native
                assert parsed["value"] == expected[native["state"]]
                assert list(parsed["native"]) == list(keys)
                checks += 1
                if list(keys) == ordered.ORDER["state_first"]:
                    assert ordered.decode(raw, "state_first")[1] == parsed["value"]
                    strict_order_accepts += 1
                else:
                    with pytest.raises(ValueError, match="v16_native_serialization_order_changed"):
                        ordered.decode(raw, "state_first")
    assert (objects, checks, strict_order_accepts) == (22, 132, 22)


@pytest.mark.parametrize(
    "content,expected", [(NEGATIVE, False), (POSITIVE, True), (UNKNOWN, "unknown")]
)
def test_hosted_transport_preserves_order_as_metadata_and_raw_capture(content, expected, tmp_path):
    native = json.loads(content)
    order = ["presented_categories", "item_configuration", "state"]
    content = json.dumps({key: native[key] for key in order})
    result, capture, _ = run(Response(envelope(content=content)), tmp_path)
    assert result["technical_success"] is True
    assert result["visual_parser"] == "nim-hosted-product-semantics-v1"
    assert result["observed_key_order"] == order
    assert result["parsed"]["native"] == native and result["parsed"]["value"] == expected
    assert capture["choices"][0]["content"]["text"] == content
    if expected == "unknown":
        assert result["parsed"]["value"] is not False and result["parsed"]["value"] is not True


@pytest.mark.parametrize(
    "content",
    [
        '{"state":"no_target","state":"no_target","item_configuration":"absent","presented_categories":[]}',
        '{"state":"no_target","item_configuration":"absent","presented_categories":[],"extra":1}',
        '{"state":"no_target","item_configuration":"absent"}',
        '{"state":"presented_target","item_configuration":"absent","presented_categories":[]}',
        '{"state":"no_target","item_configuration":"absent","presented_categories":""}',
        '{"state":"no_target","item_configuration":"absent","presented_categories":["garment"]}',
        '{"state":"presented_target","item_configuration":"hand_holds_hanger_out","presented_categories":["garment","garment"]}',
        '{"state":"no_target","item_configuration":"invented","presented_categories":[]}',
        '{"state":false,"item_configuration":"absent","presented_categories":[]}',
        '{"state":NaN,"item_configuration":"absent","presented_categories":[]}',
        "null",
        "[]",
        "prefix {}",
        "{} suffix",
        '{"state":',
    ],
)
def test_hosted_transport_rejects_invalid_semantics_without_repair(content, tmp_path):
    result, capture, _ = run(Response(envelope(content=content)), tmp_path)
    assert result["technical_success"] is False and result["parsed"] is None
    assert result["observed_key_order"] is None
    assert capture["choices"][0]["content"]["text"] == content


@pytest.mark.parametrize("content", [None, False, [], {}, " " * 16385])
def test_hosted_parser_requires_bounded_text(content):
    with pytest.raises(ValueError, match="hosted_visual_content_type_or_size"):
        client._parse_visual(content)


@pytest.mark.parametrize(
    "content,expected", [(NEGATIVE, False), (POSITIVE, True), (UNKNOWN, "unknown")]
)
def test_requested_service_policy_separates_origin_from_unattested_identity(
    content, expected, tmp_path, monkeypatch
):
    result, capture, _ = run(
        Response(envelope(client.SERVICE_REPORTED_ID, content)),
        tmp_path,
        identity_policy=client.SERVICE_POLICY,
        monkeypatch=monkeypatch,
    )
    assert result["technical_success"] is True and result["parsed"]["value"] == expected
    assert result["model_identity_verified"] is False
    assert result["model_identity_basis"] == "unverified"
    assert result["service_origin_verified"] is True
    assert result["validation_scope"] == "requested_service_with_unattested_backend"
    origin = capture["request_origin"]
    assert origin["host"] == client.HOST and origin["path"] == client.PATH
    assert origin["requested_model"] == client.MODEL
    assert origin["tls"] == "stdlib_default_ca_and_hostname"
    assert len(origin["payload_sha256"]) == 64
    assert capture["model"]["value"] == client.SERVICE_REPORTED_ID
    assert capture["choices"][0]["content"]["text"] == content


@pytest.mark.parametrize(
    "field,value",
    [
        ("host", "elsewhere.invalid"),
        ("path", "/other"),
        ("requested_model", "other/model"),
        ("tls", "unchecked"),
        ("payload_sha256", "invalid"),
    ],
)
def test_service_policy_refuses_changed_provenance_before_parsing(
    field, value, tmp_path, monkeypatch
):
    _, capture, _ = run(
        Response(envelope(client.SERVICE_REPORTED_ID)),
        tmp_path,
        identity_policy=client.SERVICE_POLICY,
        monkeypatch=monkeypatch,
    )
    capture["request_origin"][field] = value
    monkeypatch.setattr(
        client, "_parse_visual", lambda _: pytest.fail("untrusted_origin_not_scored")
    )
    result = client.assess_capture(capture, identity_policy=client.SERVICE_POLICY)
    assert result["status"] == "service_provenance_rejected" and result["parsed"] is None


@pytest.mark.parametrize("kind", ["missing_origin", "different_backend", "missing_backend"])
def test_service_policy_does_not_promote_old_or_different_provider_results(
    kind, tmp_path, monkeypatch
):
    _, capture, _ = run(
        Response(envelope(client.SERVICE_REPORTED_ID)),
        tmp_path,
        identity_policy=client.SERVICE_POLICY,
        monkeypatch=monkeypatch,
    )
    if kind == "missing_origin":
        capture.pop("request_origin")
    elif kind == "different_backend":
        capture["model"]["value"] = client.MODEL
    else:
        capture["model"]["state"] = "missing"
    monkeypatch.setattr(client, "_parse_visual", lambda _: pytest.fail("backend_not_scored"))
    result = client.assess_capture(capture, identity_policy=client.SERVICE_POLICY)
    assert result["status"] == "service_provenance_rejected" and result["parsed"] is None
    assert result["service_origin_verified"] is False


def test_service_policy_requires_standard_https_factory_before_any_connection():
    with pytest.raises(ValueError, match="service_requires_fixed_https"):
        client.exchange(
            json.dumps({"model": client.MODEL}).encode(),
            KEY,
            factory=lambda *a, **k: pytest.fail("no_connection"),
            timeout=1,
            persist=lambda _: None,
            identity_policy=client.SERVICE_POLICY,
        )


@pytest.mark.parametrize(
    "body",
    [
        b'{"model":"other/model"}',
        b"[]",
        b'{"model":"other","model":"nvidia/nemotron-3.5-super-vl-120b-a12b"}',
    ],
)
def test_service_policy_requires_fixed_model_and_unique_request_keys(body):
    with pytest.raises(ValueError):
        client.exchange(
            body,
            KEY,
            factory=http.client.HTTPSConnection,
            timeout=1,
            persist=lambda _: None,
            identity_policy=client.SERVICE_POLICY,
        )


def test_unknown_identity_policy_refused_before_connection():
    with pytest.raises(ValueError, match="unknown_visual_identity_policy"):
        client.exchange(
            b"invented",
            KEY,
            factory=lambda *a, **k: pytest.fail("no_connection"),
            timeout=1,
            persist=lambda _: None,
            identity_policy="allow_any",
        )

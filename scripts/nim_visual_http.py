"""Existing one-request visual transport with capture before acceptance checks.

No CLI, credentials, runner, queue, retries or remote release. A trusted caller
must supply the connection factory and an exclusive durable private capture sink.
"""

from __future__ import annotations

import copy
import hashlib
import http.client
import json
import re
import ssl
import time

from scripts.nim_http_error_diagnostic import error_diagnostic
from scripts.nim_observed_http_worker_v3 import protocol_ok

HOST, PATH = "integrate.api.nvidia.com", "/v1/chat/completions"
MODEL = "nvidia/nemotron-3.5-super-vl-120b-a12b"
DOCUMENTED_ALIAS = "nemotron-3.5-super-vl"
ALIAS_SOURCE = (
    "https://huggingface.co/nvidia/NVIDIA-Nemotron-3.5-Super-VL-120B-A12B-NVFP4#quick-start"
)
MODEL_IDS = frozenset((MODEL, MODEL.split("/", 1)[1], DOCUMENTED_ALIAS))
SERVICE_POLICY = "authenticated_requested_service_v1"
SERVICE_REPORTED_ID = "private/nvidia/nemotron-3.5-super-120b-a12b"
MAX_BYTES = 16384
MAX_CAPTURE_BYTES = 65536
TYPE_NAMES = {
    str: "string",
    int: "number",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
    type(None): "null",
}


class CapturePersistenceError(ValueError):
    """An opened response cannot be accepted without a persisted safe capture."""


def _redact(text, key, *, opaque_blobs=True):
    original = text
    if re.search(r"(?i)[\"'](?:image|image_url|base64|payload)[\"']\s*:", text):
        return "[REDACTED_REQUEST_ECHO]", True
    if key:
        text = re.sub(re.escape(key), "[REDACTED_CREDENTIAL]", text, flags=re.IGNORECASE)
    text = re.sub(r"(?i)\bBearer\s+[^\s\"'<>]+", "[REDACTED_CREDENTIAL]", text)
    text = re.sub(
        r"(?i)\b(?:NVIDIA_API_KEY|api[_ -]?key|authorization|password|cookie|secret|token)"
        r"\b[\"']?\s*[:=]\s*[\"']?[^\s,\"'{}]+",
        "[REDACTED_CREDENTIAL]",
        text,
    )
    text = re.sub(r"(?i)\b(?:nvapi-|sk-|gsk_|hf_)[A-Za-z0-9_-]{12,}", "[REDACTED_CREDENTIAL]", text)
    text = re.sub(
        r"(?i)data:(?:image|video|audio)/[^,\s]+;base64,[A-Za-z0-9+/=\s]+", "[REDACTED_IMAGE]", text
    )
    text = re.sub(r"(?i)data:[^\s\"'<>]*", "[REDACTED_IMAGE]", text)
    text = re.sub(r"(?i)https?://[^\s\"'<>]+", "[REDACTED_URL]", text)
    if opaque_blobs:
        text = re.sub(r"[A-Za-z0-9+/]{64,}={0,2}", "[REDACTED_BASE64]", text)
    text = re.sub(r"(?is)<think>.*?</think>", "[REDACTED_REASONING]", text)
    if re.search(r"(?i)<think>", text):
        text = re.split(r"(?i)<think>", text, maxsplit=1)[0] + "[REDACTED_REASONING]"
    return text, text != original


def _model_observation(wire, key):
    value = wire.get("model")
    result = {
        "present": "model" in wire,
        "type": TYPE_NAMES.get(type(value), "other"),
        "value": None,
        "state": "missing" if "model" not in wire else "invalid_type",
    }
    if type(value) is str:
        safe, changed = _redact(value, key, opaque_blobs=False)
        if changed:
            result["state"] = "redacted"
        elif any(0xD800 <= ord(char) <= 0xDFFF for char in value):
            result["state"] = "invalid_unicode"
        elif len(value.encode("utf-8")) > 256:
            result["state"] = "too_long"
        elif not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_. /:-]{0,255}", safe):
            result["state"] = "invalid_identifier"
        else:
            result.update(value=safe, state="captured")
    return result


def _content(value, key):
    result = {
        "type": TYPE_NAMES.get(type(value), "other"),
        "text": None,
        "redacted": False,
        "state": "invalid_type",
    }
    if type(value) is str:
        try:
            safe, changed = _redact(value, key)
            encoded = safe.encode("utf-8")
            if len(encoded) > MAX_BYTES:
                result.update(state="too_long", redacted=changed)
            else:
                result.update(text=safe, state="captured", redacted=changed)
        except UnicodeError:
            result["state"] = "invalid_unicode"
    return result


def capture_open_response(response, key, *, persist, request_origin=None):
    """Project only authorized final-answer fields; persist before identity/schema checks."""
    metadata = error_diagnostic(response, None, secrets=(key,))
    capture = {
        "schema_version": "nim-visual-safe-response-v1",
        "expected_model": MODEL,
        "http_status": metadata["http_status"],
        "request_id": metadata["request_id"],
        "headers": metadata["headers"],
        "response_bytes": None,
        "body_state": "unavailable",
        "read_state": "complete",
        "framing_valid": False,
        "model": {"present": False, "type": "not_observed", "value": None, "state": "not_observed"},
        "choices": [],
        "choice_count": None,
        "usage": {},
        "error": None,
        "duplicates": False,
    }
    if request_origin is not None:
        capture["request_origin"] = copy.deepcopy(request_origin)
    try:
        capture["framing_valid"] = bool(protocol_ok(response))
    except Exception:  # noqa: BLE001, S110 -- logging could expose header values
        pass
    raw = None
    try:
        raw = response.read(MAX_BYTES + 1)
    except http.client.IncompleteRead as error:
        raw = error.partial[: MAX_BYTES + 1] if type(error.partial) is bytes else None
        capture["read_state"] = "incomplete"
    except TimeoutError:
        capture["read_state"] = "timeout"
    except Exception:  # noqa: BLE001 -- exception text can contain secrets
        capture["read_state"] = "failed"
    if type(raw) is bytes:
        capture["response_bytes"] = len(raw)
        if len(raw) > MAX_BYTES:
            capture["body_state"] = "limit_exceeded"
        else:
            try:

                def pairs(items):
                    out = {}
                    for name, value in items:
                        if name in out:
                            capture["duplicates"] = True
                        out[name] = value
                    return out

                def nonfinite(_):
                    raise ValueError("nonfinite_json")

                wire = json.loads(
                    raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=nonfinite
                )
                capture["body_state"] = "json_object" if type(wire) is dict else "invalid_shape"
                if type(wire) is dict:
                    capture["model"] = _model_observation(wire, key)
                    choices = wire.get("choices")
                    if type(choices) is list:
                        capture["choice_count"] = len(choices)
                        for choice in choices[:5]:
                            message = choice.get("message") if type(choice) is dict else None
                            message = message if type(message) is dict else {}
                            role = message.get("role")
                            finish = choice.get("finish_reason") if type(choice) is dict else None
                            capture["choices"].append(
                                {
                                    "role": role
                                    if role in ("assistant", "user", "system", "tool")
                                    else None,
                                    "finish_reason": finish
                                    if finish in ("stop", "length", "content_filter", "tool_calls")
                                    else None,
                                    "tool_calls_present": bool(
                                        message.get("tool_calls") or message.get("function_call")
                                    ),
                                    "content": _content(message.get("content"), key),
                                }
                            )
                    usage = wire.get("usage")
                    if type(usage) is dict:
                        capture["usage"] = {
                            name: value
                            for name in ("prompt_tokens", "completion_tokens", "total_tokens")
                            if type(value := usage.get(name)) is int and 0 <= value <= 1_000_000
                        }
            except (ValueError, UnicodeError, RecursionError):
                capture["body_state"] = "invalid_json"
    if capture["http_status"] != 200:
        capture["error"] = error_diagnostic(response, raw, secrets=(key,))
    if len(json.dumps(capture, ensure_ascii=True, allow_nan=False).encode()) > MAX_CAPTURE_BYTES:
        capture["choices"] = []
        capture["body_state"] = "capture_limit_exceeded"
    try:
        persist(copy.deepcopy(capture))
    except Exception:  # noqa: BLE001 -- suppress storage errors that may carry secrets
        raise CapturePersistenceError("response_capture_persistence_failed") from None
    return capture


def _parse_visual(content):
    """Hosted product semantics; the local V16 order experiment stays unchanged."""
    from scripts.visual_validation_contract_v1 import strict_json
    from scripts.vlm_product_v15 import decode as semantic_decode

    if type(content) is not str or len(content.encode("utf-8")) > MAX_BYTES:
        raise ValueError("hosted_visual_content_type_or_size")
    strict_json(content)  # Complete JSON, unique keys and finite values before projection.
    native, value = semantic_decode(content)
    return {"native": native, "value": value}


def assess_capture(capture, *, identity_policy="exact"):
    """Same semantic domain; identity still precedes the hosted product parser."""
    if identity_policy not in ("exact", SERVICE_POLICY):
        raise ValueError("unknown_visual_identity_policy")
    result = {
        "status": "provider_reply_rejected",
        "http_status": capture["http_status"],
        "model_returned": capture["model"]["value"],
        "model_observation": capture["model"],
        "parsed": None,
        "observed_key_order": None,
        "technical_success": False,
        "request_id": capture["request_id"],
        "headers": capture["headers"],
        "response_bytes": capture["response_bytes"],
        "capture_persisted": True,
        "identity_policy": identity_policy,
        "service_origin_verified": False,
    }
    identity = capture["model"]["state"] == "captured" and capture["model"]["value"] in MODEL_IDS
    result["model_identity_verified"] = identity
    result["model_identity_basis"] = (
        "nvidia_documented_served_name"
        if identity and capture["model"]["value"] == DOCUMENTED_ALIAS
        else "exact_configured_identity"
        if identity
        else "unverified"
    )
    if capture["http_status"] != 200:
        return result | {"status": "http_error", "error_diagnostic": capture["error"]}
    if capture["read_state"] != "complete":
        return result | {"status": "response_read_failed"}
    if capture["body_state"] != "json_object" or capture["duplicates"]:
        return result | {"status": "response_envelope_invalid"}
    if not capture["framing_valid"]:
        return result | {"status": "response_framing_rejected"}
    if identity_policy == SERVICE_POLICY:
        origin = capture.get("request_origin", {})
        verified = (
            type(origin) is dict
            and origin.get("host") == HOST
            and origin.get("path") == PATH
            and origin.get("requested_model") == MODEL
            and origin.get("tls") == "stdlib_default_ca_and_hostname"
            and type(origin.get("payload_sha256")) is str
            and re.fullmatch(r"[0-9a-f]{64}", origin["payload_sha256"]) is not None
            and capture["model"]["state"] == "captured"
            and capture["model"]["value"] == SERVICE_REPORTED_ID
        )
        result["service_origin_verified"] = bool(verified)
        if not verified:
            return result | {"status": "service_provenance_rejected"}
        result["validation_scope"] = "requested_service_with_unattested_backend"
    elif capture["model"]["state"] != "captured" or capture["model"]["value"] not in MODEL_IDS:
        return result | {"status": "returned_model_unverified"}
    if capture["choice_count"] != 1:
        return result
    choice = capture["choices"][0]
    content = choice["content"]
    if (
        choice["role"] != "assistant"
        or choice["finish_reason"] != "stop"
        or choice["tool_calls_present"]
        or content["state"] != "captured"
        or content["redacted"]
    ):
        return result
    try:
        parsed = _parse_visual(content["text"])
    except Exception:  # noqa: BLE001 -- keep schema-invalid answers only in private capture
        return result
    tokens = capture["usage"].get("completion_tokens")
    return result | {
        "status": "parsed_reply",
        "technical_success": True,
        "parsed": parsed,
        "observed_key_order": list(parsed["native"]),
        "visual_parser": "nim-hosted-product-semantics-v1",
        "finish_reason": "stop",
        "completion_tokens": tokens if tokens is not None and tokens <= 512 else None,
    }


def exchange(body, key, *, factory, timeout, persist, identity_policy="exact"):
    """One HTTPS request through the existing client mechanism, with no automatic retry."""
    if not callable(persist):
        raise CapturePersistenceError("private_capture_sink_required")
    if identity_policy not in ("exact", SERVICE_POLICY):
        raise ValueError("unknown_visual_identity_policy")
    context = ssl.create_default_context()
    origin = None
    if identity_policy == SERVICE_POLICY:
        from scripts.visual_validation_contract_v1 import strict_json

        request = strict_json(body)
        if (
            factory is not http.client.HTTPSConnection
            or type(request) is not dict
            or request.get("model") != MODEL
            or not context.check_hostname
            or context.verify_mode != ssl.CERT_REQUIRED
        ):
            raise ValueError("service_requires_fixed_https_and_requested_model")
        origin = {
            "host": HOST,
            "path": PATH,
            "requested_model": MODEL,
            "payload_sha256": hashlib.sha256(body).hexdigest(),
            "tls": "stdlib_default_ca_and_hostname",
        }
    started = time.monotonic()
    connection = None
    result = {
        "status": "request_failed_outcome_uncertain",
        "http_status": None,
        "model_returned": None,
        "parsed": None,
        "technical_success": False,
    }
    try:
        connection = factory(HOST, port=443, timeout=timeout, context=context)
        connection.set_debuglevel(0)
        connection.request(
            "POST",
            PATH,
            body=body,
            headers={
                "Authorization": "Bearer " + key,
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )
        response = connection.getresponse()
        result["http_status"] = response.status
        capture = capture_open_response(response, key, persist=persist, request_origin=origin)
        result.update(assess_capture(capture, identity_policy=identity_policy))
    except CapturePersistenceError:
        result["status"] = "response_capture_failed"
    except Exception:  # noqa: BLE001 -- no raw exceptions or credentials leave the client
        if result["http_status"] == 200:
            result["status"] = "provider_reply_rejected"
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:  # noqa: BLE001, S110 -- close failures must not leak secrets
                pass
        result["latency_seconds"] = time.monotonic() - started
    return result

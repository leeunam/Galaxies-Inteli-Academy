"""Pure, bounded HTTP-error capture; no client, credentials, dispatcher or CLI."""

import json
import re

MAX_BYTES = 16384


ERROR_FIELDS = ("code", "type", "message", "detail", "title", "status")
ERROR_HEADERS = (
    "nvcf-reqid",
    "x-request-id",
    "content-type",
    "content-length",
    "date",
    "retry-after",
)


def _safe_error_text(value, secrets):
    if type(value) not in (str, int) or isinstance(value, bool):
        return None
    value = str(value)
    for secret in secrets:
        if type(secret) is str and secret:
            value = value.replace(secret, "[REDACTED]")
    # Redact before truncating: a cut must never expose a credential prefix.
    value = re.sub(r"(?i)data:[^\s\"'<>]*", "[REDACTED_IMAGE]", value)
    value = re.sub(r"(?i)https?://[^\s\"'<>]+", "[REDACTED_URL]", value)
    value = re.sub(
        r"(?i)\b(?:authorization|bearer|api[_ -]?key|token|secret|password|cookie)"
        r"\b\s*[:=]?\s*[\"']?[^\s,\"'{}]+",
        "[REDACTED_CREDENTIAL]",
        value,
    )
    value = re.sub(r"[A-Za-z0-9_+/=-]{24,}", "[REDACTED_TOKEN]", value)
    value = " ".join(value.split())
    return value.encode("utf-8")[:256].decode("utf-8", errors="ignore")


def error_diagnostic(response, raw, *, secrets=()):
    """Bounded error-only projection. Never keep raw bytes or enumerate headers."""
    from email.utils import format_datetime, parsedate_to_datetime

    status = response.status
    result = {
        "http_status": status if type(status) is int and 100 <= status <= 599 else None,
        "request_id": None,
        "headers": {},
        "fields": {},
        "body_state": "unavailable",
        "response_bytes": len(raw) if type(raw) is bytes else None,
        "field_truncated": False,
    }
    try:
        headers = response.headers
    except Exception:  # noqa: BLE001 -- header/exception text is never retained
        headers = None
    for name in ERROR_HEADERS:
        try:
            values = headers.get_all(name)
            if type(values) is not list or len(values) != 1 or type(values[0]) is not str:
                continue
            value = values[0]
            if len(value) > 128 or "\r" in value or "\n" in value:
                continue
            if any(type(secret) is str and secret and secret in value for secret in secrets):
                continue
            if name in {"nvcf-reqid", "x-request-id"}:
                if not re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", value):
                    continue
                value = value.lower()
                if result["request_id"] is None:
                    result["request_id"] = value
            elif name == "content-type":
                value = value.split(";", 1)[0].strip().lower()
                if value not in {
                    "application/json",
                    "application/problem+json",
                    "text/plain",
                }:
                    continue
            elif name == "content-length" or (name == "retry-after" and value.isdecimal()):
                if not value.isascii() or not value.isdecimal() or len(value) > 10:
                    continue
                value = int(value)
            else:
                parsed = parsedate_to_datetime(value)
                if parsed.tzinfo is None:
                    continue
                value = format_datetime(parsed)
            result["headers"][name] = value
        except Exception:  # noqa: BLE001, S112 -- logging could expose a secret
            continue
    if type(raw) is not bytes:
        return result
    if len(raw) > MAX_BYTES:
        result["body_state"] = "limit_exceeded"
        return result
    try:
        body = json.loads(raw)
    except (ValueError, UnicodeError, RecursionError):
        result["body_state"] = "not_json"
        return result
    if type(body) is not dict:
        result["body_state"] = "unsupported_shape"
        return result
    result["body_state"] = "json"
    containers = [("top", body)]
    if type(body.get("error")) is dict:
        containers.append(("error", body["error"]))
    for location, container in containers:
        projected = {}
        for name in ERROR_FIELDS:
            value = container.get(name)
            if type(value) is str and len(value.encode("utf-8")) > 256:
                result["field_truncated"] = True
            safe = _safe_error_text(value, secrets)
            if safe is not None:
                projected[name] = safe
        if projected:
            result["fields"][location] = projected
    return result


def read_error_diagnostic(response, *, secrets=()):
    """Read at most 16 KiB + one sentinel byte, only after a non-200 response."""
    if response.status == 200:
        raise ValueError("http_error_required")
    try:
        raw = response.read(MAX_BYTES + 1)
    except Exception:  # noqa: BLE001 -- exception text may contain secrets
        raw = None
    return error_diagnostic(response, raw, secrets=secrets)

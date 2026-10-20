"""Memory-only response bridge. Opens no connection and reads no credential.

Run beside sealed validation in the bounded ROOT child, before any stdout/IPC.
The future authorized dispatcher must supply an already-open HTTPResponse here,
not forward the v1 child's untrusted content stdout to a logging parent.
"""

import json
import uuid

from orchestration.galaxies_orchestration.observation_cases_v2 import content
from scripts.selection_observation_v2 import DuplicateKey, _unique


def observe_response(response, render):
    meta = {
        "transport_state": "response_opened",
        "http_status": None,
        "wire_bytes": None,
        "completion_tokens": None,
        "scope": "envelope",
        "raw_wire_sha256": None,
    }

    def stop(phase, code):
        result = render({"op": "render", "selection": None, "reason": "transport_failed"})
        result["selection_observation"].update(meta, phase=phase, code=code)
        return result

    try:
        status = response.status
        if type(status) is not int or not 100 <= status <= 599:
            return stop("transport", "invalid_http_status")
        meta["http_status"] = status
        if status != 200:
            meta["transport_state"] = "http_error"
            return stop("transport", "http_error")
        wire = response.read(16385)
    except Exception:  # noqa: BLE001 - no body/header/exception projection
        return stop("transport", "response_read_failed")
    if type(wire) is not bytes:
        return stop("transport", "invalid_wire_type")
    if len(wire) > 16384:
        return stop("transport", "wire_byte_limit")
    meta["wire_bytes"] = len(wire)
    try:
        text = wire.decode("utf-8")
    except UnicodeError:
        return stop("utf8", "invalid_wire_unicode")
    try:
        envelope = json.loads(text, object_pairs_hook=_unique)
    except DuplicateKey:
        return stop("json", "envelope_duplicate_key")
    except RecursionError:
        return stop("json", "envelope_depth_limit")
    except (ValueError, TypeError):
        return stop("json", "envelope_json_syntax")
    try:
        choices = envelope["choices"]
        choice = choices[0]
        message = choice["message"]
        reply = message["content"]
        tokens = envelope["usage"]["completion_tokens"]
        if (
            type(choices) is not list
            or len(choices) != 1
            or type(message) is not dict
            or message.get("role") != "assistant"
            or message.get("tool_calls")
            or type(reply) is not str
            or choice.get("finish_reason") != "stop"
            or type(tokens) is not int
            or not 0 <= tokens <= 2048
        ):
            raise ValueError
    except (ValueError, TypeError, KeyError, IndexError):
        return stop("schema", "envelope_schema_invalid")
    meta.update(transport_state="reply_received", completion_tokens=tokens, scope="selection")
    try:
        reply_size = len(reply.encode("utf-8"))
    except UnicodeError:
        return stop("utf8", "invalid_unicode")
    if reply_size > 16384:
        return stop("utf8", "response_byte_limit")
    result = render({"op": "render", "selection": reply, "reason": None})
    result["selection_observation"].update(meta)
    return result


def invented_response(case, *, secret=None):
    """Fixed fake response for the local worker. Never loads a real key."""
    secret = uuid.uuid4().hex + uuid.uuid4().hex if secret is None else secret
    envelope = {
        "choices": [
            {"message": {"role": "assistant", "content": content("valid")}, "finish_reason": "stop"}
        ],
        "usage": {"completion_tokens": 10},
    }
    if case == "envelope_schema":
        envelope["choices"] = []
    if case == "envelope_extra_secret":
        envelope["debug_headers"] = {"Authorization": "Bearer " + secret}
    if case == "content_extra_secret":
        envelope["choices"][0]["message"]["content"] = content("secret_extra", secret=secret)
    if case == "content_deep":
        envelope["choices"][0]["message"]["content"] = "[" * 2500 + "]" * 2500
    wire = json.dumps(envelope).encode()
    if case == "wire_unicode":
        wire = b"\xff"
    if case == "wire_json":
        wire = ("Authorization: Bearer " + secret).encode()
    if case == "wire_duplicate":
        wire = b'{"choices":[],"choices":[]}'
    if case == "wire_limit":
        wire = b"x" * 16385

    class Response:
        status = 402 if case == "http_error" else 200

        def read(self, size):
            if size != 16385:
                raise ValueError("bounded_read_required")
            if case == "read_exception":
                raise RuntimeError("Authorization: Bearer " + secret)
            return wire[:size]

    return Response()

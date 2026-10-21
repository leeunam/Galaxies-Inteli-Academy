"""Fixed public slots/types, computed only after the unchanged sealed authority."""

from __future__ import annotations

import json

from scripts.explanation_observer_v2 import ObservationSession
from scripts.nim_dispatch_plan_v3 import canonical, digest
from scripts.nim_dispatch_summary_v3 import summarize, validate_summary
from scripts.nim_response_observer_v2 import observe_response
from scripts.nim_typed_request_v1 import response_schema
from scripts.selection_observation_v2 import _unique

SLOTS = (
    "envelope",
    "choices",
    "choices[0]",
    "message",
    "message.content",
    "selection",
    "packet_sha256",
    "evidence_ids",
    "evidence_ids[*]",
)
CATEGORIES = {"not_observed", "missing", "null", "string", "array", "object", "number", "boolean"}
MISSING = object()


def category(value):
    if value is MISSING:
        return "missing"
    return {
        type(None): "null",
        str: "string",
        list: "array",
        dict: "object",
        int: "number",
        float: "number",
        bool: "boolean",
    }.get(type(value), "not_observed")


def type_audit(wire):
    slots = {name: ["not_observed"] for name in SLOTS}
    audit = {
        "schema_version": "public-selection-type-slots-v1",
        "expected_schema_sha256": digest(canonical(response_schema())),
        "slots": slots,
    }
    if type(wire) is not bytes or len(wire) > 16384:
        return audit
    try:
        envelope = json.loads(wire.decode("utf-8"), object_pairs_hook=_unique)
        slots["envelope"] = [category(envelope)]
        if type(envelope) is not dict:
            return audit
        choices = envelope.get("choices", MISSING)
        slots["choices"] = [category(choices)]
        if type(choices) is not list or len(choices) != 1:
            return audit
        choice = choices[0]
        slots["choices[0]"] = [category(choice)]
        if type(choice) is not dict:
            return audit
        message = choice.get("message", MISSING)
        slots["message"] = [category(message)]
        if type(message) is not dict:
            return audit
        content = message.get("content", MISSING)
        slots["message.content"] = [category(content)]
        if type(content) is not str:
            return audit
        body = json.loads(content, object_pairs_hook=_unique)
        slots["selection"] = [category(body)]
        if type(body) is not dict:
            return audit
        slots["packet_sha256"] = [category(body.get("packet_sha256", MISSING))]
        ids = body.get("evidence_ids", MISSING)
        slots["evidence_ids"] = [category(ids)]
        if type(ids) is list:
            slots["evidence_ids[*]"] = sorted({category(item) for item in ids})
    except (ValueError, TypeError, RecursionError, UnicodeError):
        # No exception, input, untrusted field name, value, body hash or repr.
        return audit
    return audit


def validate_observation(value):
    if type(value) is not dict or set(value) != {"summary", "type_audit"}:
        raise ValueError("typed_observation_invalid")
    validate_summary(value["summary"])
    audit = value["type_audit"]
    if (
        type(audit) is not dict
        or set(audit) != {"schema_version", "expected_schema_sha256", "slots"}
        or audit["schema_version"] != "public-selection-type-slots-v1"
        or audit["expected_schema_sha256"] != digest(canonical(response_schema()))
        or type(audit["slots"]) is not dict
        or set(audit["slots"]) != set(SLOTS)
    ):
        raise ValueError("typed_observation_invalid")
    for slot, categories in audit["slots"].items():
        if (
            type(categories) is not list
            or len(categories) > len(CATEGORIES)
            or any(type(item) is not str or item not in CATEGORIES for item in categories)
        ):
            raise ValueError("typed_observation_invalid")
        if categories != sorted(set(categories)) or (
            slot != "evidence_ids[*]" and len(categories) != 1
        ):
            raise ValueError("typed_observation_invalid")
    if value["summary"]["selection_validated"]:
        expected = {
            "envelope": ["object"],
            "choices": ["array"],
            "choices[0]": ["object"],
            "message": ["object"],
            "message.content": ["string"],
            "selection": ["object"],
            "packet_sha256": ["string"],
            "evidence_ids": ["array"],
            "evidence_ids[*]": ["string"],
        }
        if audit["slots"] != expected:
            raise ValueError("typed_observation_contradicts_accepted_authority")
    return value


def observe_open_response(response):
    """Memory-only bridge for a response already opened by a trusted caller.

    The existing authority receives original bytes/content. This wrapper cannot
    repair, coerce or override its outcome. No connection or key access exists.
    """
    session = ObservationSession()
    session.handle({"op": "prepare", "payload": {}})
    captured = None

    class RecordingResponse:
        @property
        def status(self):
            return response.status

        def read(self, size):
            nonlocal captured
            captured = response.read(size)
            return captured

    result = observe_response(RecordingResponse(), session.handle)
    summary = summarize(result)  # sealed authority result first, diagnostics second
    return validate_observation({"summary": summary, "type_audit": type_audit(captured)})

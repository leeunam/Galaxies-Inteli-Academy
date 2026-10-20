"""Invented offline content only. Adversarial secrets are supplied in memory."""

import json
from pathlib import Path

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures/nim-synthetic-request.json"
EXPECTED = {
    "valid": ("rendering", "accepted"),
    "valid_whitespace": ("rendering", "accepted"),
    "json_invalid": ("json", "json_syntax"),
    "json_duplicate": ("json", "json_duplicate_key"),
    "schema_missing": ("schema", "schema_missing_field"),
    "schema_type": ("schema", "schema_invalid_type"),
    "schema_constraint": ("schema", "schema_constraint"),
    "wrong_hash": ("references", "packet_hash_mismatch"),
    "unknown_id": ("references", "unknown_evidence_id"),
    "duplicate_ids": ("references", "duplicate_evidence_id"),
    "unicode": ("utf8", "invalid_unicode"),
    "secret_header": ("json", "json_syntax"),
    "secret_extra": ("schema", "schema_extra_field"),
    "secret_fieldname": ("schema", "schema_extra_field"),
    "secret_id": ("references", "unknown_evidence_id"),
    "secret_digest": ("references", "packet_hash_mismatch"),
}
WIRE_EXPECTED = {
    "valid": ("rendering", "accepted"),
    "wire_unicode": ("utf8", "invalid_wire_unicode"),
    "wire_json": ("json", "envelope_json_syntax"),
    "wire_duplicate": ("json", "envelope_duplicate_key"),
    "envelope_schema": ("schema", "envelope_schema_invalid"),
    "envelope_extra_secret": ("rendering", "accepted"),
    "content_extra_secret": ("schema", "schema_extra_field"),
    "content_deep": ("json", "json_depth_limit"),
    "wire_limit": ("transport", "wire_byte_limit"),
    "http_error": ("transport", "http_error"),
    "read_exception": ("transport", "response_read_failed"),
}


def content(case, *, secret=None):
    if case not in EXPECTED:
        raise ValueError("unknown_offline_case")
    if case.startswith("secret_") and (type(secret) is not str or len(secret) != 64):
        raise ValueError("invented_secret_required")
    body = {
        "packet_sha256": json.loads(FIXTURE.read_bytes())["packet_sha256"],
        "evidence_ids": ["c1_prediction", "c1_interval"],
    }
    if case == "json_invalid":
        return "ENTIRELY_INVENTED_INVALID_JSON"
    if case == "json_duplicate":
        return '{"packet_sha256":"' + body["packet_sha256"] + '",' + json.dumps(body)[1:]
    if case == "schema_missing":
        del body["evidence_ids"]
    if case == "schema_type":
        body["evidence_ids"] = 42
    if case == "schema_constraint":
        body["evidence_ids"] = []
    if case == "wrong_hash":
        body["packet_sha256"] = "0" * 64
    if case == "unknown_id":
        body["evidence_ids"] = ["not_in_catalogue"]
    if case == "duplicate_ids":
        body["evidence_ids"] = ["c1_prediction", "c1_prediction"]
    if case == "unicode":
        return "\ud800"
    if case == "secret_header":
        return "Authorization: Bearer " + secret
    if case == "secret_extra":
        body["headers"] = {"Authorization": "Bearer " + secret}
    if case == "secret_fieldname":
        body[secret] = "invented"
    if case == "secret_id":
        body["evidence_ids"] = ["nvapi-" + secret]
    if case == "secret_digest":
        body["packet_sha256"] = secret
    return json.dumps(body, indent=2 if case == "valid_whitespace" else None)

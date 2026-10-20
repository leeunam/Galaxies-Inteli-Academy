"""Post-hoc diagnostics only: the sealed validator remains the authority.

Never return raw strings, exceptions, Pydantic messages/locations/inputs or a
hash of suppressed source text. Retain only a canonical public-fixture projection.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import ValidationError

from scripts.explanation_evidence import EvidenceSelection

FIXTURE = Path(__file__).resolve().parents[1] / "orchestration/fixtures/nim-synthetic-request.json"
FIXTURE_SHA256 = "0fb7b9797cd41f53c3f127b0d2f6f934d0696aa3ba288852f5cff616455cf438"


class DuplicateKey(ValueError):
    pass


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKey
        result[key] = value
    return result


def _schema_code(error):
    # Do not retain loc/msg/ctx/input: even an extra field NAME can be a secret.
    types = {
        e["type"]
        for e in error.errors(include_input=False, include_context=False, include_url=False)
    }
    for codes, result in (
        ({"missing"}, "schema_missing_field"),
        ({"extra_forbidden"}, "schema_extra_field"),
        ({"string_type", "tuple_type", "model_type", "dict_type"}, "schema_invalid_type"),
        (
            {
                "too_short",
                "too_long",
                "string_pattern_mismatch",
                "string_too_short",
                "string_too_long",
            },
            "schema_constraint",
        ),
    ):
        if types & codes:
            return result
    return "schema_invalid"


def classify(context, raw):
    observation = {
        "phase": "utf8",
        "code": "response_not_text",
        "response_bytes": None,
        "raw_response_sha256": None,
        "safe_response_projection": None,
        "retained_projection_sha256": None,
        "retention": "suppressed_untrusted_source",
    }

    def stop(phase, code):
        observation.update(phase=phase, code=code)
        return observation

    if type(raw) is not str:
        return observation
    try:
        encoded = raw.encode("utf-8")
    except UnicodeError:
        return stop("utf8", "invalid_unicode")
    if len(encoded) > 16384:
        return stop("utf8", "response_byte_limit")
    observation["response_bytes"] = len(encoded)
    try:
        body = json.loads(raw, object_pairs_hook=_unique)
    except DuplicateKey:
        return stop("json", "json_duplicate_key")
    except (ValueError, TypeError):
        return stop("json", "json_syntax")
    except RecursionError:
        return stop("json", "json_depth_limit")
    try:
        selection = EvidenceSelection.model_validate_json(json.dumps(body))
    except ValidationError as error:
        return stop("schema", _schema_code(error))
    except (ValueError, TypeError, RecursionError):
        return stop("schema", "schema_invalid")
    if selection.packet_sha256 != context.packet_sha256:
        return stop("references", "packet_hash_mismatch")
    allowed = {f.evidence_id for f in context.packet.evidence}
    if not set(selection.evidence_ids) <= allowed:
        return stop("references", "unknown_evidence_id")
    public_bytes = FIXTURE.read_bytes()
    public = json.loads(public_bytes)
    if (
        hashlib.sha256(public_bytes).hexdigest() == FIXTURE_SHA256
        and context.packet_sha256 == public["packet_sha256"]
    ):
        # No raw bytes are copied: values must belong to the verified public packet.
        projection = {
            "packet_sha256": public["packet_sha256"],
            "evidence_ids": list(selection.evidence_ids),
        }
        canonical = json.dumps(projection, sort_keys=True, ensure_ascii=True).encode()
        observation.update(
            safe_response_projection=projection,
            retained_projection_sha256=hashlib.sha256(canonical).hexdigest(),
            retention="canonical_public_projection_only",
        )
    if len(set(selection.evidence_ids)) != len(selection.evidence_ids):
        return stop("references", "duplicate_evidence_id")
    return stop("rendering", "accepted")


def after_sealed_validation(context, raw, result):
    """Classify without changing the sealed result or granting acceptance."""
    accepted = result.get("explanation", {}).get("status") == "validated_catalogue_selection"
    try:
        observation = classify(context, raw)
    except Exception:  # noqa: BLE001 - never serialize exception or input
        observation = {
            "phase": "observation",
            "code": "classification_failed",
            "response_bytes": None,
            "raw_response_sha256": None,
            "safe_response_projection": None,
            "retained_projection_sha256": None,
            "retention": "suppressed_untrusted_source",
        }
    parity = (
        None
        if observation["code"] == "classification_failed"
        else (accepted == (observation["code"] == "accepted"))
    )
    if parity is False:
        observation.update(
            phase="sealed_validation_or_rendering",
            code="sealed_result_unclassified",
            safe_response_projection=None,
            retained_projection_sha256=None,
            retention="suppressed_untrusted_source",
        )
    observation.update(
        authority_accepted=accepted,
        authority_status="accepted" if accepted else "rejected",
        classifier_parity=parity,
        rendering_status="completed" if accepted else "not_completed",
    )
    return observation


def after_authority_exception(context, raw, error):
    """An exception is NOT a rejected/accepted result or a completed rendering."""
    try:
        observation = classify(context, raw)
    except Exception:  # noqa: BLE001 - no exception values retained
        observation = {}
    if not (isinstance(error, RecursionError) and observation.get("code") == "json_depth_limit"):
        observation.update(phase="sealed_validation_or_rendering", code="sealed_authority_failed")
    observation.update(
        authority_status="failed_before_result",
        authority_accepted=False,
        classifier_parity=None,
        rendering_status="not_completed",
        raw_response_sha256=None,
        safe_response_projection=None,
        retained_projection_sha256=None,
        retention="suppressed_untrusted_source",
    )
    return observation

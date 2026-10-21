"""Original authority first; post-hoc fixed public-three metadata only."""

import json

from orchestration.galaxies_orchestration.nim_diagnostic_contract_v1 import (
    empty_diagnostic,
    validate_diagnostic,
)
from orchestration.galaxies_orchestration.nim_graph_contract_v1 import FIXTURE, canonical, digest
from scripts.explanation_evidence import validate_selection
from scripts.selection_observation_v2 import (
    _unique,
    after_authority_exception,
    after_sealed_validation,
)

MISSING = object()
PUBLIC_FIXTURE_SHA256 = "365df6cc87cbca007ac8a5e09076f8c308cf78e7a49fe8151499159e12b7a380"


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


def public_scope(context):
    raw = FIXTURE.read_bytes()
    if digest(raw) != PUBLIC_FIXTURE_SHA256:
        raise ValueError("diagnostic_public_fixture_changed")
    public = json.loads(raw, object_pairs_hook=_unique)
    if context.packet_sha256 != public["request"]["packet_sha256"] or (
        canonical(context.packet.model_dump(mode="json")) != canonical(public["request"]["packet"])
        or canonical(context.analysis()) != canonical(public["data"]["report"])
    ):
        raise ValueError("diagnostic_requires_exact_public_three_context")
    return public


def shape(raw, context, diagnostic):
    if type(raw) is not str or len(raw.encode("utf-8")) > 16384:
        return
    body = json.loads(raw, object_pairs_hook=_unique)
    diagnostic["types"]["selection"] = [category(body)]
    if type(body) is not dict:
        return
    packet = body.get("packet_sha256", MISSING)
    ids = body.get("evidence_ids", MISSING)
    diagnostic["types"]["packet_sha256"] = [category(packet)]
    diagnostic["types"]["evidence_ids"] = [category(ids)]
    if type(packet) is str:
        diagnostic["packet_hash_equal"] = packet == context.packet_sha256
    if type(ids) is list:
        diagnostic["cardinality"] = len(ids)
        diagnostic["types"]["evidence_ids[*]"] = sorted({category(item) for item in ids})
        if all(type(item) is str for item in ids):
            diagnostic["duplicates"] = len(ids) != len(set(ids))
            catalog = {fact.evidence_id for fact in context.packet.evidence}
            diagnostic["all_ids_in_catalog"] = all(item in catalog for item in ids)


def evaluate_original(context, raw):
    """No repair/coercion. An observation failure never changes sealed acceptance."""
    public_scope(context)
    result, error = None, None
    try:
        result = validate_selection(context, raw)  # original authority always FIRST
    except Exception as caught:  # noqa: BLE001 - only static exception categories are used
        error = caught
    accepted = result is not None
    status = (
        "accepted"
        if accepted
        else "rejected"
        if type(error) is ValueError
        else "failed_before_result"
    )
    diagnostic = empty_diagnostic(status)
    try:
        if error is not None and type(error) is not ValueError:
            observed = after_authority_exception(context, raw, error)
        else:
            observed = after_sealed_validation(
                context, raw, result or {"explanation": {"status": "incomplete"}}
            )
        diagnostic.update(
            phase=observed["phase"],
            code=observed["code"],
            classifier_parity=observed["classifier_parity"],
        )
        try:
            shape(raw, context, diagnostic)
        except (ValueError, TypeError, UnicodeError, RecursionError):
            pass  # unparsable shape is not_observed, never guessed from prefixes
        validate_diagnostic(diagnostic)
    except Exception:  # noqa: BLE001 - fallback preserves the ORIGINAL outcome
        diagnostic = empty_diagnostic(status)
    selection = None
    if accepted:
        # Values are from original parsed/validated public evidence only. The
        # diagnostic never returns input, unknown names/values or rejected hashes.
        body = json.loads(raw, object_pairs_hook=_unique)
        selection = canonical(body).decode("ascii")
    return {"selection": selection, "diagnostic": diagnostic}

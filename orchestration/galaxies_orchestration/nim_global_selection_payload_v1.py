"""Public inert payload proposal: clarify the existing global evidence-ID cap."""

import json

from . import nim_graph_contract_v1 as original

PREVIOUS_BYTES = 8576
PREVIOUS_SHA256 = "fd87bed20413c52bb7873d92da48c37d5f5f391a3fa9997e77177d073aaafcba"
GLOBAL_RULE = (
    "GLOBAL RESPONSE LIMIT: Return ONE JSON object with ONE evidence_ids array. "
    "That array must contain 1 to 12 distinct catalog ID strings IN TOTAL across "
    "ALL THREE creatives and any shared limit evidence. This is one global cap, "
    "not a separate allowance for each creative. Do not concatenate per-creative "
    "lists or return the entire 24-ID catalog. No per-creative quota or coverage "
    "requirement is imposed by this count limit."
)
EXAMPLE_IDS = (
    ("c2_interval",),
    (
        "limit_target",
        "limit_quality",
        "limit_interpretation",
        "c1_prediction",
        "c1_interval",
        "c1_shap_sector",
        "c1_reference_1",
        "c2_prediction",
        "c2_interval",
        "c2_reference_1",
        "c3_prediction",
        "c3_interval",
    ),
)


def counting_examples():
    """Invented public examples, never recovered IDs or client-side selection repair."""
    packet_hash = original.fixture()["request"]["packet_sha256"]
    return [{"packet_sha256": packet_hash, "evidence_ids": list(ids)} for ids in EXAMPLE_IDS]


def payload_bytes():
    # No caller-supplied body/model/root/endpoint, response processing or remote route.
    previous = original.payload_bytes()
    if len(previous) != PREVIOUS_BYTES or original.digest(previous) != PREVIOUS_SHA256:
        raise ValueError("global_selection_predecessor_payload_changed")
    body = json.loads(previous, object_pairs_hook=original.unique)
    content = body["messages"][0]["content"]
    examples = counting_examples()
    body["messages"][0]["content"] = (
        GLOBAL_RULE
        + "\n\n"
        + content
        + "\n\nThe following entirely invented examples demonstrate syntax and GLOBAL "
        "counting only, not preferred evidence, a fixed selection or per-creative quotas.\n"
        + "Example with 1 ID TOTAL:\n"
        + original.canonical(examples[0]).decode("ascii")
        + "\nExample with 12 IDs TOTAL (shared IDs also count):\n"
        + original.canonical(examples[1]).decode("ascii")
        + "\nBefore answering, count the ENTIRE evidence_ids array once: 1 <= count <= 12. "
        "An array of 13 or more IDs is invalid even if every ID is known and unique. "
        "Choose a compliant subset before emitting your answer; the consumer will not "
        "truncate or repair it. Return only the JSON object, without count fields, "
        "per-creative objects, reasoning, prose or code fences."
    )
    return original.canonical(body)

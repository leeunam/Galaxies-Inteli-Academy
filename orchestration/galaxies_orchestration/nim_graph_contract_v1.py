"""Public, entirely invented graph candidate; remote execution is not released."""

import hashlib
import json
from pathlib import Path

from .nim_graph_seal_v1 import PLAN_SHA256

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "orchestration/fixtures/nim-graph-three-invented-v1.json"
PLAN = ROOT / "orchestration/fixtures/nim-graph-offline-v1-plan.json"
ENDPOINT = "https://integrate.api.nvidia.com/v1/chat/completions"
MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
CASES = {"valid", "wrong_hash", "secret_id", "http_error", "invalid_wire", "hang"}


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False).encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate_key")
        result[key] = value
    return result


def fixture():
    return json.loads(FIXTURE.read_bytes(), object_pairs_hook=unique)


def response_schema():
    request = fixture()["request"]
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["packet_sha256", "evidence_ids"],
        "properties": {
            "packet_sha256": {"type": "string", "enum": [request["packet_sha256"]]},
            "evidence_ids": {
                "type": "array",
                "minItems": 1,
                "maxItems": 12,
                "uniqueItems": True,
                "items": {
                    "type": "string",
                    "enum": [fact["evidence_id"] for fact in request["packet"]["evidence"]],
                },
            },
        },
    }


def payload_bytes():
    content = (
        "Everything below is entirely invented, including predictions, SHAP, references, "
        "IDs and fingerprints. No real model, media or training data is represented. "
        "Perform only closed JSON evidence selection. Do not output reasoning or prose.\n"
        + canonical(fixture()["request"]).decode("ascii")
        + "\nResponse contract (JSON Schema):\n"
        + canonical(response_schema()).decode("ascii")
        + "\nReturn the JSON object itself. packet_sha256 is a string; evidence_ids is "
        "an array of ID strings, never evidence objects. No type labels, code fences or extras."
    )
    return canonical(
        {
            "model": MODEL,
            "messages": [{"role": "user", "content": content}],
            "max_tokens": 2048,
            "temperature": 0.2,
            "stream": False,
            "chat_template_kwargs": {"enable_thinking": False},
        }
    )


def configuration():
    return {
        "protocol": "nim-invented-three-graph-offline-v1",
        "fixture_sha256": digest(FIXTURE.read_bytes()),
        "packet_sha256": fixture()["request"]["packet_sha256"],
        "http_payload_sha256": digest(payload_bytes()),
        "response_schema_sha256": digest(canonical(response_schema())),
        "endpoint": ENDPOINT,
        "model": MODEL,
        "creative_count": 3,
        "entirely_invented": True,
        "native_feature_handoff": False,
        "remote_execution_released": False,
        "specific_remote_authorization_id": None,
        "remaining_authorized_calls": 0,
        "proposed_future_calls": 1,
        "total_timeout_seconds": 45,
        "max_output_tokens": 2048,
        "max_response_bytes": 16384,
        "max_spend_brl": 0,
        "retry_allowed": False,
        "private_data_allowed": False,
        "proxy_allowed": False,
        "redirect_allowed": False,
    }


def verify_plan():
    raw = PLAN.read_bytes()
    if not PLAN_SHA256 or digest(raw) != PLAN_SHA256:
        raise ValueError("nim_graph_plan_seal_mismatch")
    plan = json.loads(raw, object_pairs_hook=unique)
    config = configuration()
    if set(plan) != {"configuration", "configuration_sha256", "sources_sha256"} or (
        canonical(plan["configuration"]) != canonical(config)
        or plan["configuration_sha256"] != digest(canonical(config))
    ):
        raise ValueError("nim_graph_contract_mismatch")
    if type(plan["sources_sha256"]) is not dict or not plan["sources_sha256"]:
        raise ValueError("nim_graph_sources_missing")
    for name, expected in plan["sources_sha256"].items():
        path = ROOT / name
        if (
            path.is_symlink()
            or not path.resolve().is_relative_to(ROOT)
            or (digest(path.read_bytes()) != expected)
        ):
            raise ValueError("nim_graph_source_changed")
    return plan


def remote_exchange(*args, **kwargs):
    # Unconditional BEFORE fixture reads, reservation, nonce, process or key.
    # No remote ledger, credential getter, connection or HTTP client exists here.
    raise ValueError("nim_graph_no_remote_authorization")

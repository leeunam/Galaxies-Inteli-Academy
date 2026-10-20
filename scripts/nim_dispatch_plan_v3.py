"""Fixed public request and sealed plan; no credential or account access."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from scripts.nim_dispatch_seal_v3 import PLAN_SHA256, REMOTE_PLAN_SHA256
from scripts.selection_observation_v2 import FIXTURE_SHA256, _unique

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "orchestration/fixtures/nim-synthetic-request.json"
PLAN = ROOT / "orchestration/fixtures/nim-dispatch-v3-plan.json"
LEDGER = ROOT / "data/private/issue-5-nim-dispatch-v3"
HOST = "integrate.api.nvidia.com"
PATH = "/v1/chat/completions"
MODEL = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning"
ENDPOINT = "https://" + HOST + PATH
BASE = "9c4177a4ddc3b44710d0b39435d1df02d4f2201e"


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, allow_nan=False).encode()


def payload_bytes():
    raw = FIXTURE.read_bytes()
    if digest(raw) != FIXTURE_SHA256:
        raise ValueError("v3_public_fixture_changed")
    return canonical(
        {
            "model": MODEL,
            "messages": [
                {
                    "role": "user",
                    "content": "Everything in the following fixture is entirely invented. "
                    "Perform only the closed JSON evidence selection. Do not output reasoning, "
                    "markdown or prose.\n" + raw.decode("utf-8").strip(),
                }
            ],
            "max_tokens": 2048,
            "temperature": 0.2,
            "stream": False,
            "chat_template_kwargs": {"enable_thinking": False},
        }
    )


def verify_plan(*, remote=False):
    raw = PLAN.read_bytes()
    if not PLAN_SHA256 or digest(raw) != PLAN_SHA256:
        raise ValueError("v3_plan_seal_mismatch")
    plan = json.loads(raw, object_pairs_hook=_unique)
    expected = {
        "protocol": "nim-fixed-public-dispatch-v3",
        "base_commit": BASE,
        "endpoint": ENDPOINT,
        "model": MODEL,
        "fixture_sha256": FIXTURE_SHA256,
        "http_payload_sha256": digest(payload_bytes()),
        "max_calls": 1,
        "max_output_tokens": 2048,
        "total_timeout_seconds": 45,
        "max_response_bytes": 16384,
        "max_spend_brl": 0,
        "private_data_allowed": False,
        "retry_allowed": False,
        "redirect_allowed": False,
        "remote_execution_released": False,
        "account_zero_cost_evidence": None,
    }
    # Exact types exclude bool masquerading as an integer budget.
    if set(plan) != set(expected) | {"sources_sha256"} or any(
        type(plan[k]) is not type(value) or plan[k] != value for k, value in expected.items()
    ):
        raise ValueError("v3_plan_contract_mismatch")
    sources = plan["sources_sha256"]
    if type(sources) is not dict or not sources:
        raise ValueError("v3_plan_sources_missing")
    for name, expected_hash in sources.items():
        path = ROOT / name
        if (
            type(name) is not str
            or path.is_symlink()
            or not path.resolve().is_relative_to(ROOT)
            or digest(path.read_bytes()) != expected_hash
        ):
            raise ValueError("v3_source_changed")
    if remote and (
        REMOTE_PLAN_SHA256 != PLAN_SHA256
        or plan["remote_execution_released"] is not True
        or plan["account_zero_cost_evidence"] is None
    ):
        raise ValueError("v3_remote_release_absent")
    return plan

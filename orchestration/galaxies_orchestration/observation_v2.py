"""Local-only observation pipeline. No HTTP client, key lookup or remote budget.

Raw callback content stays in local variables/private stdin, never graph state,
stdout, receipts or exception output. Only the root's public projection survives.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TypedDict

from galaxies_orchestration import graph as sealed_graph  # disables inherited tracing
from galaxies_orchestration.nim_http import FIXTURE, LEDGER, durable_create
from galaxies_orchestration.nim_seal import APPROVED_PLAN_SHA256
from galaxies_orchestration.observation_cases_v2 import WIRE_EXPECTED
from galaxies_orchestration.worker import ROOT, RootWorker

BASE_COMMIT = "883578d4334d7c0175210144dd3c4ef55146f258"
STATUSES = {
    "reply_received",
    "http_error",
    "timeout_outcome_uncertain",
    "request_failed_or_not_sent",
    "cancelled_outcome_uncertain",
}


@dataclass(frozen=True)
class Reply:
    content: object
    status: object = "reply_received"
    http_status: object = 200
    completion_tokens: object = 10
    finish_reason: object = "stop"
    wire_bytes: object = 256


class ObserverWorker(RootWorker):
    def __init__(self):
        super().__init__(synthetic_probe=True, timeout_seconds=45)
        self.module = "scripts.explanation_observer_v2"


class State(TypedDict, total=False):
    prepared: dict
    result: dict
    observation: dict


def _source_hashes():
    return {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in (
            "scripts/selection_observation_v2.py",
            "scripts/explanation_observer_v2.py",
            "scripts/nim_response_observer_v2.py",
            "orchestration/galaxies_orchestration/observation_v2.py",
            "orchestration/galaxies_orchestration/observation_cases_v2.py",
            "orchestration/galaxies_orchestration/observation_demo_v2.py",
        )
    }


async def run_observed(
    callback, folder, *, timeout_seconds=45, envelope_case=None, fixture_secret=None
):
    """Consume one LOCAL simulation; a consumed/uncertain directory cannot be reused.

    Callback is trusted offline test code, not an externally supplied transport.
    There is intentionally no remote mode, nonce, credential or real reservation.
    """
    if not 0 < timeout_seconds <= 45:
        raise ValueError("invalid_observer_deadline")
    if envelope_case is not None and (envelope_case not in WIRE_EXPECTED or callback is not None):
        raise ValueError("invalid_offline_response_case")
    folder = Path(folder).resolve()
    if folder == LEDGER.resolve() or folder.is_relative_to(LEDGER.resolve()):
        raise ValueError("sealed_ledger_forbidden")
    # Directory existence is itself consumed/uncertain. Never append to an old queue.
    folder.mkdir(parents=True, exist_ok=False)
    bindings = {
        "observer_version": "synthetic-observation-local-v2",
        "base_code_commit": BASE_COMMIT,
        "sealed_parent_plan_sha256": APPROVED_PLAN_SHA256,
        "fixture_sha256": hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
        "observer_sources_sha256": _source_hashes(),
        "scope": "offline_simulation_only",
        "real_requests": 0,
        "limits": {
            "max_output_tokens": 2048,
            "total_timeout_seconds": timeout_seconds,
            "max_response_bytes": 16384,
            "max_attempts": 1,
        },
    }
    durable_create(folder / "local-consumption.json", bindings | {"state": "simulated_consumed"})
    started = time.monotonic()
    observation = {
        "scope": "transport",
        "transport_state": "not_started",
        "phase": "preparation",
        "code": "outcome_uncertain",
        "http_status": None,
        "wire_bytes": None,
        "completion_tokens": None,
        "raw_response_sha256": None,
        "safe_response_projection": None,
        "retained_projection_sha256": None,
        "retention": "suppressed_untrusted_source",
        "authority_accepted": False,
        "authority_status": "not_invoked",
        "rendering_status": "not_completed",
    }
    result = None

    def fail(phase, code):
        observation.update(phase=phase, code=code)

    try:
        async with ObserverWorker() as worker:

            async def prepare(state):
                fail("preparation", "preparing")
                return {"prepared": await worker.request({"op": "prepare", "payload": {}})}

            async def inspect_reply(state):
                nonlocal result
                if envelope_case is not None:
                    observation["transport_state"] = "offline_response_bridge_started"
                    observation.update(
                        authority_status="outcome_uncertain", rendering_status="outcome_uncertain"
                    )
                    fail("response_bridge", "awaiting_safe_result")
                    result = await worker.request(
                        {
                            "op": "observe_http_fixture",
                            "case": envelope_case,
                            "fixture_secret": fixture_secret,
                        }
                    )
                    observation.update(result.pop("selection_observation"))
                    if result.get("observer_worker_failure") is True:
                        result = None
                    return {"result": result, "observation": dict(observation)}
                selection = None
                remaining = timeout_seconds - (time.monotonic() - started)
                try:
                    if remaining <= 0:
                        raise TimeoutError
                    observation["transport_state"] = "callback_started"
                    fail("transport", "callback_started")
                    async with asyncio.timeout(remaining):
                        reply = await callback(
                            {
                                "payload_json": FIXTURE.read_text().strip(),
                                "remaining_seconds": remaining,
                                "max_output_tokens": 2048,
                            }
                        )
                    if time.monotonic() - started >= timeout_seconds:
                        raise TimeoutError
                    if (
                        type(reply) is not Reply
                        or type(reply.status) is not str
                        or reply.status not in STATUSES
                    ):
                        raise ValueError
                    observation["transport_state"] = reply.status
                    if (
                        type(reply.http_status) is not int
                        or not 100 <= reply.http_status <= 599
                        or type(reply.wire_bytes) is not int
                        or not 0 <= reply.wire_bytes <= 16384
                        or type(reply.completion_tokens) is not int
                        or not 0 <= reply.completion_tokens <= 2048
                    ):
                        fail("transport", "invalid_transport_limits")
                    else:
                        observation.update(
                            http_status=reply.http_status,
                            wire_bytes=reply.wire_bytes,
                            completion_tokens=reply.completion_tokens,
                        )
                        if reply.status != "reply_received" or reply.http_status != 200:
                            fail("transport", "transport_not_successful")
                        elif type(reply.finish_reason) is not str or reply.finish_reason != "stop":
                            fail("transport", "incomplete_generation")
                        elif type(reply.content) is not str:
                            observation["scope"] = "selection"
                            fail("utf8", "response_not_text")
                        else:
                            observation["scope"] = "selection"
                            try:
                                size = len(reply.content.encode("utf-8"))
                            except UnicodeError:
                                fail("utf8", "invalid_unicode")
                            else:
                                if size > 16384:
                                    fail("utf8", "response_byte_limit")
                                elif size > reply.wire_bytes:
                                    fail("transport", "inconsistent_byte_count")
                                else:
                                    selection = reply.content
                except TimeoutError:
                    observation["transport_state"] = "timeout_outcome_uncertain"
                    fail("transport", "transport_timeout")
                except Exception:  # noqa: BLE001 - no raw exception or arbitrary metadata
                    fail("transport", "transport_exception_or_invalid_envelope")
                previous = dict(observation)
                observation.update(
                    authority_status="outcome_uncertain", rendering_status="outcome_uncertain"
                )
                fail("sealed_validation_or_rendering", "worker_outcome_uncertain")
                result = await worker.request(
                    {
                        "op": "render",
                        "selection": selection,
                        "reason": None if selection is not None else "transport_failed",
                    }
                )
                root_observation = result.pop("selection_observation")
                if result.get("observer_worker_failure") is True:
                    result = None
                if selection is not None:
                    observation.update(root_observation)
                else:
                    observation.update(previous)
                return {"result": result, "observation": dict(observation)}

            subgraph = sealed_graph.StateGraph(State)
            subgraph.add_node("inspect_and_validate", inspect_reply)
            subgraph.add_edge(sealed_graph.START, "inspect_and_validate")
            subgraph.add_edge("inspect_and_validate", sealed_graph.END)
            graph = sealed_graph.StateGraph(State)
            graph.add_node("prepare", prepare)
            graph.add_node("observe", subgraph.compile())
            graph.add_edge(sealed_graph.START, "prepare")
            graph.add_edge("prepare", "observe")
            graph.add_edge("observe", sealed_graph.END)
            async with asyncio.timeout(timeout_seconds):
                await graph.compile().ainvoke({})
    except asyncio.CancelledError:
        observation.update(transport_state="cancelled_outcome_uncertain")
        fail("transport", "cancelled_outcome_uncertain")
        raise
    except TimeoutError:
        observation.update(transport_state="timeout_outcome_uncertain")
        fail("transport", "total_deadline_exceeded")
    except Exception:  # noqa: BLE001 - no worker errors/input/paths in telemetry
        fail(observation["phase"], "worker_or_graph_failed")
    finally:
        receipt = (
            bindings
            | observation
            | {
                "elapsed_seconds": time.monotonic() - started,
                "state": "simulated_consumed",
                "retry_allowed": False,
                "real_authorization_created": False,
            }
        )
        durable_create(folder / "observation.json", receipt)
    return {"result": result, "observation": receipt}

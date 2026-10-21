"""Unchanged compiled graph with a ROOT selector; all transport here is fake."""

import argparse
import asyncio
import json
import uuid

from .integrated_graph_v2 import build_graph
from .integrated_worker_v2 import IntegratedWorker
from .nim_graph_contract_v1 import CASES, ROOT, canonical, fixture, verify_plan


async def finish(task):
    """Retain cleanup ownership even when cancellation is repeated."""
    interrupted = False
    while True:
        try:
            return await asyncio.shield(task), interrupted
        except asyncio.CancelledError:
            if task.cancelled():
                raise RuntimeError("nim_graph_cleanup_unconfirmed") from None
            interrupted = True


class ProbeWorker(IntegratedWorker):
    async def __aenter__(self):
        spawning = asyncio.create_task(super().__aenter__())
        try:
            return await asyncio.shield(spawning)
        except BaseException:
            try:
                await finish(spawning)
            finally:
                await finish(asyncio.create_task(super().__aexit__(None, None, None)))
            raise

    async def __aexit__(self, *args):
        _, interrupted = await finish(asyncio.create_task(super().__aexit__(*args)))
        if interrupted:
            raise asyncio.CancelledError


class RootSelector:
    def __init__(self, worker):
        self.worker, self.calls = worker, 0

    async def __call__(self, request):
        if self.calls:
            raise ValueError("nim_graph_selector_already_consumed")
        self.calls += 1
        reply = await self.worker.request({"op": "select", "request": request})
        if set(reply) != {"selection"} or type(reply["selection"]) is not str:
            raise ValueError("nim_graph_selection_unavailable")
        return reply["selection"]


def current_provider(proof, result, run_id, *, selector_calls):
    """No input JSON can substitute a live dispatch capability in this unit."""
    expected_keys = {
        "origin",
        "run_id",
        "packet_sha256",
        "real_http_requests",
        "live_dispatch",
        "root_selection_accepted",
        "root_render_accepted",
        "transport",
        "events",
    }
    public = fixture()
    if (
        type(proof) is not dict
        or set(proof) != expected_keys
        or (
            proof["origin"] != "offline_fake"
            or proof["run_id"] != run_id
            or proof["packet_sha256"] != public["request"]["packet_sha256"]
            or type(proof["real_http_requests"]) is not int
            or proof["real_http_requests"] != 0
            or proof["live_dispatch"] is not None
            or selector_calls != 1
            or proof["events"]
            != ["analyze", "shap", "comparables", "context", "select", "render", "proof"]
            or canonical(result["analysis"]) != canonical(public["data"]["report"])
            or canonical(result["evidence_packet"]) != canonical(public["request"]["packet"])
            or result["orchestration"]["native_feature_handoff"] is not False
            or result["orchestration"]["real_provider_verified"] is not False
        )
    ):
        raise ValueError("nim_graph_proof_binding_failed")
    accepted = result["explanation"]["status"] == "validated_catalogue_selection"
    if type(proof["root_selection_accepted"]) is not bool or (
        type(proof["root_render_accepted"]) is not bool
        or proof["root_render_accepted"] != accepted
        or proof["root_selection_accepted"] != accepted
    ):
        raise ValueError("nim_graph_authority_proof_mismatch")
    transport = proof["transport"]
    if (
        type(transport) is not dict
        or set(transport) != {"http_status", "wire_bytes", "completion_tokens", "code"}
        or transport["code"]
        not in {"selection_accepted", "selection_rejected", "http_error", "envelope_json_syntax"}
    ):
        raise ValueError("nim_graph_transport_proof_invalid")
    for name, lower, upper in (
        ("http_status", 100, 599),
        ("wire_bytes", 0, 16384),
        ("completion_tokens", 0, 2048),
    ):
        value = transport[name]
        if value is not None and (type(value) is not int or not lower <= value <= upper):
            raise ValueError("nim_graph_transport_proof_invalid")
    if accepted and (transport["code"] != "selection_accepted" or transport["http_status"] != 200):
        raise ValueError("nim_graph_authority_proof_mismatch")
    # A future live release must supply a NEW authorized dispatch binding. Neither
    # an HTTP-looking fake nor a cached receipt can produce that binding here.
    verified = proof["live_dispatch"] is not None and accepted
    return proof | {
        "real_provider_verified": verified,
        "verification_status": "offline_only",
        "selector_invocations": selector_calls,
        "numerical_origin": "entirely_invented",
        "legacy_status_field": "legacy_result.orchestration.real_provider_verified",
    }


async def run_offline(worker_python, case="valid", *, timeout=45):
    if case not in CASES or not 0 < timeout <= 45:
        raise ValueError("nim_graph_invalid_offline_run")
    verify_plan()  # before process creation
    run_id = uuid.uuid4().hex
    worker = ProbeWorker(
        worker_python,
        ROOT,
        ("--offline-case", case, "--run-id", run_id),
        module="scripts.nim_graph_bridge_v1",
        timeout=timeout,
    )
    async with asyncio.timeout(timeout), worker:
        selector = RootSelector(worker)
        graph = build_graph(worker, selector)
        result = (await graph.ainvoke({"payload": {}}))["result"]
        proof = await worker.request({"op": "proof"})
        provider = current_provider(proof, result, run_id, selector_calls=selector.calls)
    return {
        "schema_version": "creative-nim-graph-offline-v1",
        "legacy_result": result,
        "current_provider": provider,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker-python", required=True)
    parser.add_argument("--offline-case", choices=sorted(CASES), default="valid")
    args = parser.parse_args()
    try:
        result = asyncio.run(run_offline(args.worker_python, args.offline_case))
    except Exception:  # noqa: BLE001 - no raw error, payload or path
        result = {"outcome": "offline_graph_stopped"}
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()

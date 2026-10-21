"""Same compiled graph, bounded ROOT worker and proof; added diagnostic is offline only."""

import argparse
import asyncio
import json
import uuid
from pathlib import Path

from .integrated_graph_v2 import build_graph
from .nim_diagnostic_contract_v1 import validate_diagnostic
from .nim_graph_contract_v1 import ROOT, verify_plan
from .nim_graph_v1 import ProbeWorker, RootSelector, current_provider

CASES = {
    "valid",
    "wrong_hash",
    "secret_id",
    "http_error",
    "invalid_wire",
    "hang",
    "too_many_ids",
    "duplicate_ids",
    "scalar_ids",
    "extra_field",
    "deep_json",
}


class DiagnosticSelector(RootSelector):
    def __init__(self, worker):
        super().__init__(worker)
        self.diagnostic = None

    async def __call__(self, request):
        if self.calls:
            raise ValueError("diagnostic_selector_already_consumed")
        self.calls += 1
        reply = await self.worker.request({"op": "select", "request": request})
        if type(reply) is not dict or set(reply) != {"selection", "diagnostic"}:
            raise ValueError("diagnostic_invalid_ipc_reply")
        self.diagnostic = validate_diagnostic(reply["diagnostic"])
        if type(reply["selection"]) is not str:
            raise ValueError("diagnostic_selection_unavailable")
        return reply["selection"]


async def run_offline(worker_python, case="valid", *, timeout=45):
    started = asyncio.get_running_loop().time()
    if (
        case not in CASES
        or type(timeout) not in (int, float)
        or not 0 < timeout <= 45
        or not Path(worker_python).is_absolute()
    ):
        raise ValueError("diagnostic_invalid_offline_configuration")
    verify_plan()
    remaining = started + timeout - asyncio.get_running_loop().time()
    if remaining <= 0:
        raise TimeoutError
    run_id = uuid.uuid4().hex
    worker = ProbeWorker(
        worker_python,
        ROOT,
        ("--offline-case", case, "--run-id", run_id),
        module="scripts.nim_diagnostic_worker_v1",
        timeout=remaining,
    )
    async with asyncio.timeout_at(started + timeout), worker:
        selector = DiagnosticSelector(worker)
        legacy = (await build_graph(worker, selector).ainvoke({"payload": {}}))["result"]
        proof = await worker.request({"op": "proof"})
        provider = current_provider(proof, legacy, run_id, selector_calls=selector.calls)
        diagnostic = validate_diagnostic(selector.diagnostic)
        if (diagnostic["authority_status"] == "accepted") != proof["root_selection_accepted"]:
            raise ValueError("diagnostic_authority_binding_mismatch")
    return {
        "schema_version": "creative-nim-graph-diagnostic-v1",
        "legacy_result": legacy,
        "current_provider": provider,
        "selection_diagnostic": diagnostic,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker-python", required=True)
    parser.add_argument("--offline-case", choices=sorted(CASES), default="valid")
    args = parser.parse_args()
    try:
        result = asyncio.run(run_offline(args.worker_python, args.offline_case))
    except Exception:  # noqa: BLE001 - no raw errors or provider content
        result = {"outcome": "diagnostic_offline_stopped"}
    print(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()

"""Real staged StateGraph; numerical authority and private evidence stay in root."""

import argparse
import asyncio
import json
import os
import sys
from itertools import pairwise
from pathlib import Path
from typing import TypedDict

os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"

from langgraph.graph import END, START, StateGraph

from galaxies_orchestration.integrated_worker_v2 import MAX_LINE, IntegratedWorker


class State(TypedDict, total=False):
    payload: dict
    prepared: dict
    selection: str | None
    reason: str | None
    result: dict
    handoff: bool


class Output(TypedDict):
    result: dict


def build_graph(worker, selector=None, *, checkpoint=None):
    async def analyze(state):
        reply = await worker.request({"op": "analyze", "payload": state["payload"]})
        if checkpoint:
            checkpoint(reply["analysis"])
        return {"handoff": reply["native_feature_handoff"]}

    async def shap(state):
        await worker.request({"op": "shap"})
        return {}

    async def comparables(state):
        await worker.request({"op": "comparables"})
        return {}

    async def context(state):
        return {"prepared": await worker.request({"op": "context"})}

    async def select(state):
        prepared = state["prepared"]
        if prepared["packet"] is None:
            # Root owns analysis/evidence reasons. Only transport outcomes
            # belong to the render message protocol.
            return {"selection": None, "reason": None}
        if selector is None:
            return {"selection": None, "reason": "transport_not_configured"}
        request = json.dumps(
            {
                "protocol": "closed-evidence-selection-v1",
                "packet": prepared["packet"],
                "packet_sha256": prepared["packet_sha256"],
            },
            allow_nan=False,
            ensure_ascii=True,
        )
        try:
            if len(request.encode()) > 65536:
                raise ValueError("request_limit")
            async with asyncio.timeout(45):
                reply = await selector(request)
            if type(reply) is not str or len(reply.encode("utf-8")) > 16384:
                raise ValueError("reply_limit")
        except Exception:  # noqa: BLE001 - local callback errors never cross IPC
            return {"selection": None, "reason": "transport_failed"}
        return {"selection": reply, "reason": None}

    async def render(state):
        result = await worker.request(
            {"op": "render", "selection": state["selection"], "reason": state["reason"]}
        )
        result["orchestration"] = {
            "kind": "integrated_stategraph_v2",
            "stategraph_executed": True,
            "explainer_subgraph_executed": True,
            "native_feature_handoff": state["handoff"],
            "real_provider_verified": False,
            "selector_kind": "absent" if selector is None else "trusted_local_callback",
        }
        return {"result": result}

    explainer = StateGraph(State)
    explainer.add_node("select", select)
    explainer.add_node("validate_and_render", render)
    explainer.add_edge(START, "select")
    explainer.add_edge("select", "validate_and_render")
    explainer.add_edge("validate_and_render", END)
    graph = StateGraph(State, output_schema=Output)
    for name, function in (
        ("extract_predict_and_rank", analyze),
        ("native_shap", shap),
        ("training_comparables", comparables),
        ("bind_context", context),
        ("explain", explainer.compile()),
    ):
        graph.add_node(name, function)
    sequence = (
        START,
        "extract_predict_and_rank",
        "native_shap",
        "training_comparables",
        "bind_context",
        "explain",
        END,
    )
    for left, right in pairwise(sequence):
        graph.add_edge(left, right)
    return graph.compile()


def _emit(kind, value):
    raw = json.dumps({"kind": kind, "value": value}, allow_nan=False).encode() + b"\n"
    if len(raw) > MAX_LINE:
        raise ValueError("graph_output_limit")
    sys.stdout.buffer.write(raw)
    sys.stdout.buffer.flush()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker-python", required=True)
    parser.add_argument("--worker-module", default="scripts.explanation_worker_v2")
    parser.add_argument("--worker-arguments", nargs=argparse.REMAINDER, default=[])
    args = parser.parse_args()
    if os.environ.get("GALAXIES_SUPERVISED") != "1":
        raise SystemExit("supervisor_required")
    raw = sys.stdin.buffer.readline(MAX_LINE + 1)
    if len(raw) > MAX_LINE or not raw.endswith(b"\n"):
        raise SystemExit("graph_input_limit")
    payload = json.loads(raw)
    root = Path(__file__).resolve().parents[2]

    async def run():
        async with IntegratedWorker(
            args.worker_python, root, args.worker_arguments, module=args.worker_module
        ) as worker:
            result = await build_graph(
                worker, checkpoint=lambda report: _emit("checkpoint", report)
            ).ainvoke({"payload": payload})
            _emit("result", result["result"])

    try:
        asyncio.run(run())
    except Exception:  # noqa: BLE001 - supervisor owns numerical fallback/cleanup
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()

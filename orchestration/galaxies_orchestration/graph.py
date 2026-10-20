"""Actual StateGraph and explainer subgraph over a trusted local JSON worker.

No streaming, checkpointing, retry policy or external tracing is configured.
Selectors are trusted operator callbacks, not user-supplied tools or URLs.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import TypedDict

# Set before importing LangGraph/LangSmith, even if inherited settings enable tracing.
os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"

from langgraph.graph import END, START, StateGraph


class GraphInput(TypedDict):
    payload: dict


class GraphOutput(TypedDict):
    result: dict


class State(GraphInput, GraphOutput, total=False):
    prepared: dict
    selection: str | None
    reason: str | None


def build_graph(worker, selector=None):
    """Compile one analysis node and a compiled selection/validation subgraph.

    The worker owns report validation/rendering. No SHAP/search is fabricated or
    captured automatically here. Selectors must cooperate with the 45 s timeout;
    a future real NIM probe also needs its own killable process boundary.
    """

    async def prepare(state):
        prepared = await worker.request({"op": "prepare", "payload": state["payload"]})
        return {"prepared": prepared}

    async def select(state):
        prepared = state["prepared"]
        if prepared["packet"] is None:
            return {"selection": None, "reason": prepared["reason"]}
        if selector is None:
            return {"selection": None, "reason": "transport_not_configured"}
        request = json.dumps(
            {
                "protocol": "closed-evidence-selection-v1",
                "packet_sha256": prepared["packet_sha256"],
                "packet": prepared["packet"],
                "instructions": "Select existing evidence IDs only. Return a JSON object with "
                "packet_sha256 and evidence_ids (1 to 12 distinct IDs). No other fields or text.",
            },
            allow_nan=False,
            ensure_ascii=True,
        )
        try:
            if len(request.encode()) > 65536:
                raise ValueError("request_limit")
            async with asyncio.timeout(45):
                selection = await selector(request)
            if type(selection) is not str or len(selection.encode("utf-8")) > 16384:
                raise ValueError("reply_limit")
        except Exception:  # noqa: BLE001 - never expose provider errors or payloads
            return {"selection": None, "reason": "transport_failed"}
        return {"selection": selection, "reason": None}

    async def render(state):
        result = await worker.request(
            {"op": "render", "selection": state["selection"], "reason": state["reason"]}
        )
        result["orchestration"] = {
            "kind": "isolated_stategraph",
            "stategraph_executed": True,
            "explainer_subgraph_executed": True,
            "native_feature_handoff": False,
        }
        return {"result": result}

    explainer = StateGraph(State)
    explainer.add_node("select", select)
    explainer.add_node("validate_and_render", render)
    explainer.add_edge(START, "select")
    explainer.add_edge("select", "validate_and_render")
    explainer.add_edge("validate_and_render", END)
    graph = StateGraph(State, input_schema=GraphInput, output_schema=GraphOutput)
    graph.add_node("analyze_once", prepare)
    graph.add_node("explain", explainer.compile())
    graph.add_edge(START, "analyze_once")
    graph.add_edge("analyze_once", "explain")
    graph.add_edge("explain", END)
    return graph.compile()

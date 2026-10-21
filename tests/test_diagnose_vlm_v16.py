"""Synthetic evidence only; replay must never start a model or use a transport."""

import json
import socket
import subprocess

import pytest
from PIL import Image

from scripts import diagnose_vlm_v16 as diagnostic
from scripts import vlm_product_v16 as core
from scripts.private_checkpoint import digest, file_hash
from scripts.vlm_product_v15 import save
from scripts.vlm_prompt_plan import controls


@pytest.fixture
def evidence(tmp_path):
    folder = tmp_path / "data/private/sealed"
    cell = tmp_path / "invented.png"
    Image.new("RGB", (320, 330), "white").save(cell)
    cases = [
        {
            "kind": "negative",
            "sample_id": r["sample_id"],
            "seconds": 0.2,
            "png_sha256": file_hash(cell),
        }
        for r in controls()
    ]
    plan = {
        "base": {"cases": {"negative": cases, "positive": [{} for _ in range(5)]}},
        "configuration": {"specifications": {v: core.specification(v) for v in core.VARIANTS}},
    }
    plan["plan_sha256"] = digest(plan)
    entries = []
    for i, case in enumerate(cases):
        for v in core.VARIANTS if i % 2 == 0 else tuple(reversed(core.VARIANTS)):
            config = (
                "isolated_physical_item"
                if v == "item_first"
                else "unclear"
                if case["sample_id"] == "lines"
                else "absent"
            )
            rule = core.PROJECTION[config]
            native = {
                "item_configuration": config,
                "state": rule["state"],
                "presented_categories": ["garment"] if rule["categories"] else [],
            }
            response = json.dumps({k: native[k] for k in core.ORDER[v]})
            path = folder / "results" / v / "negative" / case["sample_id"] / "result.json"
            result = core.extract(
                [cell],
                [0.2],
                tmp_path,
                variant=v,
                evidence_dir=path.parent / "calls",
                reserve=lambda i: None,
                invoker=lambda *a, _raw=response, **k: {
                    "raw_response": _raw,
                    "runtime_seconds": 1.0,
                    "runtime_peak_rss_mib": 2.0,
                },
            )
            save(
                path,
                {"plan_sha256": plan["plan_sha256"], "case_sha256": digest(case), "vlm": result},
            )
            entries.append(
                {
                    "variant": v,
                    "kind": "negative",
                    "sample_id": case["sample_id"],
                    "status": "completed",
                    "call_count": 1,
                }
            )
    save(folder / "plan.json", plan)
    save(
        folder / "checkpoint.json",
        {
            "plan_sha256": plan["plan_sha256"],
            "sealed": True,
            "calls_reserved": 24,
            "acquisitions_reserved": 0,
            "halt_reason": "v16_neither_condition_passed_negatives",
            "operations": entries,
        },
    )
    return folder


def test_replay_is_read_only_without_model_or_network(evidence, monkeypatch):
    def denied(*a, **k):
        raise AssertionError("external_or_model_call_forbidden")

    monkeypatch.setattr(subprocess, "Popen", denied)
    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(core, "invoke_local_vlm", denied)
    before = {str(p): file_hash(p) for p in evidence.rglob("*.json")}
    result = diagnostic.reconstruct(evidence)
    assert result["counts"] == {
        "item_first": {"false": 0, "true": 12, "unknown": 0},
        "state_first": {"false": 11, "true": 0, "unknown": 1},
    }
    assert result["paired_gains"] == 11 and result["paired_losses"] == 0
    assert result["actual_control_seconds"] == [0.2] and result["new_model_calls"] == 0
    assert result["positive_calls_in_v16"] == 0 and len(result["rows"]) == 24
    assert {str(p): file_hash(p) for p in evidence.rglob("*.json")} == before


@pytest.mark.parametrize(
    "tamper",
    ["unsealed", "raw", "time", "png", "projection", "order", "extra_operation", "source_prompt"],
)
def test_changed_evidence_cannot_be_reinterpreted(evidence, tamper):
    plan_path = evidence / "plan.json"
    state_path = evidence / "checkpoint.json"
    plan = json.loads(plan_path.read_bytes())
    state = json.loads(state_path.read_bytes())
    entry = state["operations"][0]
    path = evidence / "results" / entry["variant"] / "negative" / entry["sample_id"] / "result.json"
    body = json.loads(path.read_bytes())
    if tamper == "unsealed":
        state["sealed"] = False
    elif tamper == "raw":
        call_path = path.parent / "calls/frame-1.json"
        c = json.loads(call_path.read_bytes())
        c["raw_response"] = "changed"
        save(call_path, c)
    elif tamper == "time":
        body["vlm"]["input_frame_seconds"] = [0.0]
    elif tamper == "png":
        body["vlm"]["input_png_sha256"] = ["0" * 64]
    elif tamper == "projection":
        body["vlm"]["intermediate"][0]["presentation_cue"] = "held_display"
    elif tamper == "order":
        state["operations"][:2] = reversed(state["operations"][:2])
    elif tamper == "extra_operation":
        state["operations"].append(state["operations"][0])
    else:
        plan["configuration"]["specifications"]["state_first"]["prompt"] += "changed"
    save(path, body)
    save(state_path, state)
    save(plan_path, plan)
    with pytest.raises(ValueError):
        diagnostic.reconstruct(evidence)


def test_prefix_domains_do_not_imply_uniform_probabilities():
    domains = diagnostic.prefix_domains()
    assert len(domains["item_first"]["continuations"]) == 10
    assert len(domains["state_first"]["continuations"]) == 4
    assert domains["state_first"]["continuations"] == {
        "no_target": 1,
        "incidental_only": 1,
        "presented_target": 19,
        "uncertain": 1,
    }
    assert sum(domains["item_first"]["continuations"].values()) == 22

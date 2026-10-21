"""Replay sealed V16 evidence without invoking a model, transport or tokenizer."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from scripts.private_checkpoint import digest, file_hash, private_path
from scripts.retrain_expansion import reserved_guard
from scripts.vlm_product_v16 import (
    FIELD,
    PROJECTION,
    VARIANTS,
    decode,
    ordered_schema_hash,
    project,
    save,
    specification,
    verify,
)


def prefix_domains():
    """Finite allowed continuations, not token likelihoods or sampling probabilities."""
    objects = []
    for config, row in PROJECTION.items():
        for cats in [[c] for c in row["categories"]] if row["categories"] else [[]]:
            objects.append(
                {"item_configuration": config, "state": row["state"], "presented_categories": cats}
            )
    if len(objects) != 22:
        raise ValueError("v16_semantic_domain_changed")
    result = {}
    for variant in VARIANTS:
        fields = specification(variant)["fields"]
        for body in objects:
            decode(json.dumps({k: body[k] for k in fields}), variant)
        result[variant] = {
            "first_field": fields[0],
            "continuations": dict(Counter(o[fields[0]] for o in objects)),
        }
    return result


def reconstruct(folder):
    if any(p.is_symlink() for p in folder.rglob("*")):
        raise ValueError("v16_evidence_symlink_forbidden")
    plan = json.loads((folder / "plan.json").read_bytes())
    state = json.loads((folder / "checkpoint.json").read_bytes())
    if (
        plan["plan_sha256"] != digest({k: v for k, v in plan.items() if k != "plan_sha256"})
        or state["plan_sha256"] != plan["plan_sha256"]
        or state["sealed"] is not True
        or state["calls_reserved"] != 24
        or state["acquisitions_reserved"] != 0
        or state["halt_reason"] != "v16_neither_condition_passed_negatives"
    ):
        raise ValueError("v16_complete_sealed_negative_block_required")
    cases = {c["sample_id"]: c for c in plan["base"]["cases"]["negative"]}
    if len(cases) != 12:
        raise ValueError("v16_twelve_controls_required")
    expected = []
    for i, name in enumerate(cases):
        expected.extend(
            (v, "negative", name) for v in (VARIANTS if i % 2 == 0 else tuple(reversed(VARIANTS)))
        )
    if [(e["variant"], e["kind"], e["sample_id"]) for e in state["operations"]] != expected:
        raise ValueError("v16_complete_alternating_pairs_required")
    rows = []
    by_sample = {name: {} for name in cases}
    for entry in state["operations"]:
        if entry["status"] != "completed" or entry["call_count"] != 1:
            raise ValueError("v16_completed_native_attempt_required")
        variant = entry["variant"]
        sample = entry["sample_id"]
        case = cases[sample]
        directory = folder / "results" / variant / "negative" / sample
        path = directory / "result.json"
        body = json.loads(path.read_bytes())
        result = body["vlm"]
        if (
            body["plan_sha256"] != plan["plan_sha256"]
            or body["case_sha256"] != digest(case)
            or result["variant"] != variant
            or result["input_png_sha256"] != [case["png_sha256"]]
            or result["input_frame_seconds"] != [case["seconds"]]
        ):
            raise ValueError("v16_original_case_binding_changed")
        verify(result, directory / "calls")
        call_path = directory / "calls/frame-1.json"
        call = json.loads(call_path.read_bytes())
        native, value = decode(call["raw_response"], variant)
        derived = project(native)
        if value != result["parsed"][FIELD]["value"] or derived != result["intermediate"][0]:
            raise ValueError("v16_raw_projection_or_value_changed")
        row = {
            "variant": variant,
            "sample_id": sample,
            "native": native,
            "derived": derived,
            "value": value,
            "input_png_sha256": case["png_sha256"],
            "seconds": case["seconds"],
            "raw_sha256": call["raw_response_sha256"],
            "call_sha256": file_hash(call_path),
            "result_sha256": file_hash(path),
            "runtime_seconds": call["runtime_seconds"],
            "peak_rss_mib": call["runtime_peak_rss_mib"],
        }
        rows.append(row)
        by_sample[sample][variant] = row
    for pair in by_sample.values():
        a, b = (pair[v] for v in VARIANTS)
        if (a["input_png_sha256"], a["seconds"]) != (b["input_png_sha256"], b["seconds"]):
            raise ValueError("v16_paired_pixels_or_time_changed")
    specs = {v: specification(v) for v in VARIANTS}
    if any(plan["configuration"]["specifications"][v] != specs[v] for v in VARIANTS):
        raise ValueError("v16_source_contract_changed")
    a, b = (specs[v] for v in VARIANTS)
    if a["prompt"] != b["prompt"] or a["schema"] != b["schema"]:
        raise ValueError("v16_semantic_equivalence_changed")
    counts = {
        v: {
            "false": sum(r["value"] is False for r in rows if r["variant"] == v),
            "true": sum(r["value"] is True for r in rows if r["variant"] == v),
            "unknown": sum(r["value"] == "unknown" for r in rows if r["variant"] == v),
        }
        for v in VARIANTS
    }
    return {
        "plan_sha256": plan["plan_sha256"],
        "rows": rows,
        "counts": counts,
        "paired_gains": sum(
            p["state_first"]["value"] is False and p["item_first"]["value"] is not False
            for p in by_sample.values()
        ),
        "paired_losses": sum(
            p["item_first"]["value"] is False and p["state_first"]["value"] is not False
            for p in by_sample.values()
        ),
        "prefix_domains": prefix_domains(),
        "prefix_counts_are_probabilities": False,
        "actual_control_seconds": sorted({r["seconds"] for r in rows}),
        "prompt_sha256": digest(a["prompt"]),
        "ordered_schema_sha256": {v: ordered_schema_hash(specs[v]["schema"]) for v in VARIANTS},
        "positive_calls_in_v16": 0,
        "frozen_positive_crops": len(plan["base"]["cases"]["positive"]),
        "no_logit_or_reasoning_evidence": True,
        "new_model_calls": 0,
        "new_acquisitions": 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--parent",
        type=Path,
        default=Path("data/private/issue-1-pool-treino-20261018-v6/released-cohort-v1"),
    )
    parser.add_argument(
        "--cohort-dir",
        type=Path,
        default=Path("data/private/issue-3-expansao-300-v1/released-cohort-v1"),
    )
    args = parser.parse_args()
    root = Path.cwd()
    folder = private_path(args.folder, root)
    output = private_path(args.output, root)
    if output.exists() or not output.is_relative_to(
        root / "data/private/issue-4-vlm-pos-v16-diagnostico-v1"
    ):
        raise ValueError("new_owned_analysis_output_required")
    with reserved_guard(args.parent, root), reserved_guard(args.cohort_dir, root):
        result = reconstruct(folder)
        save(output, result)
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "counts",
                    "paired_gains",
                    "paired_losses",
                    "actual_control_seconds",
                    "positive_calls_in_v16",
                    "new_model_calls",
                )
            }
        )
    )


if __name__ == "__main__":
    main()

"""Seal a new paired partial report; never dispose sheets or write old queues."""

from __future__ import annotations

import json

from scripts.private_checkpoint import digest, file_hash, save
from scripts.vlm_per_frame import BOOLEAN_FIELDS, aggregate
from scripts.vlm_product_development import cached_result
from scripts.vlm_product_development import checked_result as checked_original
from scripts.vlm_product_limited_plan import (
    BASE_ACQUISITIONS,
    BASE_CALLS,
    checked_result,
    load,
    locks,
    no_workers,
    result_path,
)
from scripts.vlm_product_plan import annotations
from scripts.vlm_product_recovery_plan import checked_result as checked_recovered
from scripts.vlm_product_states import FIELD
from scripts.vlm_prompt_development import metrics


def compare(parent, cohort, folder, root):
    preliminary = json.loads((folder / "plan.json").read_bytes())
    recovery = root / preliminary["recovery_folder"]
    with locks(recovery, folder, root):
        plan, state = load(parent, cohort, folder, root)
        if "comparison_file_sha256" in state:
            return json.loads((folder / "comparison.json").read_bytes())
        if not state["diagnostic"] or any(
            e["status"] == "running" for e in [state["diagnostic"], *state["inferences"]]
        ):
            raise ValueError("limited_incomplete_operation_requires_audit")
        completed = {e["sample_id"] for e in state["inferences"] if e["status"] == "completed"}
        if len(completed) != 7 and not state["halt_reason"]:
            raise ValueError("limited_complete_or_stopped_required")
        no_workers(root)
        old = json.loads((recovery / "plan.json").read_bytes())
        sealed = root / old["sealed_folder"]
        original = json.loads((sealed / "plan.json").read_bytes())
        inherited = json.loads((recovery / "comparison.json").read_bytes())["result_sha256"]
        truth = annotations(original, root)
        observations = {v: [] for v in ("v9", "v8", "v7_A", "v7_B_old32")}
        hashes = {}
        for row in plan["rows"]:
            sample = row["sample_id"]
            if sample in completed:
                path = result_path(folder, sample)
                current = checked_result(folder, plan, row, root)
            elif sample in old["inherited_result_sha256"]:
                path = root / inherited[sample]["path"]
                current = checked_original(sealed, original, row, root)
            elif sample in inherited:
                path = root / inherited[sample]["path"]
                current = checked_recovered(recovery, old, row, root)
            else:
                continue
            previous = cached_result(root, row)
            frames = [
                a | {FIELD: b[FIELD]}
                for a, b in zip(previous["per_frame"], current["per_frame"], strict=True)
            ]
            prediction = aggregate(frames, current["input_frame_seconds"])
            if any(prediction[f] != previous["parsed"][f] for f in BOOLEAN_FIELDS if f != FIELD):
                raise ValueError("limited_person_text_cache_changed")
            base = {
                "sample_id": sample,
                "origin": row["group"],
                "sector": row["sector"],
                "annotated": truth[sample],
            }
            observations["v9"].append(base | {"predicted": prediction, "per_frame": frames})
            for version, candidate in (("v8", None), ("v7_A", "A"), ("v7_B_old32", "B")):
                if candidate == "B" and row["group"] != "development":
                    continue
                prior = cached_result(root, row, candidate)
                if (
                    prior["input_png_sha256"] != current["input_png_sha256"]
                    or prior["input_frame_seconds"] != current["input_frame_seconds"]
                ):
                    raise ValueError("limited_comparison_pixels_or_times_changed")
                observations[version].append(
                    base | {"predicted": prior["parsed"], "per_frame": prior["per_frame"]}
                )
            hashes[sample] = {"path": str(path.relative_to(root)), "sha256": file_hash(path)}
        if len(hashes) != 34 + len(completed) or len(hashes) > 41:
            raise ValueError("limited_comparison_scope_changed")
        scores = {}
        for version, rows in observations.items():
            scores[version] = {"all_available": metrics(rows)}
            for group in ("development", "audit", "pilot", "remaining"):
                part = [
                    r
                    for r in rows
                    if (
                        r["origin"] == group
                        if group in ("development", "audit")
                        else (r["sample_id"] in plan["pilot_ids"]) == (group == "pilot")
                    )
                ]
                scores[version][group] = metrics(part)
        report = {
            "status": "product_limited_combined_report",
            "limited_plan_sha256": plan["plan_sha256"],
            "evaluated_cases": len(hashes),
            "inherited_complete_cases": 34,
            "new_complete_cases": len(completed),
            "result_sha256": hashes,
            "metrics": scores,
            "stop_reason": state["halt_reason"] or "authorized_limited_scope_completed",
            "released_fields": [],
            "fields_ready_for_future_blind_audit": [],
            "original_gate_by_origin": {},
            "same_pixels_and_times": True,
            "person_text_cache_preserved": True,
            "new_blind_audit": False,
            "predictive_training_started": False,
            "test_evaluated": False,
            "m1_replaced": False,
            "new_acquisitions": 1,
            "new_native_reservations": state["calls_reserved"],
            "cumulative_acquisitions": BASE_ACQUISITIONS + 1,
            "cumulative_native_reservations": BASE_CALLS + state["calls_reserved"],
            "elapsed_seconds": state["elapsed_seconds"],
            "preserved_images": 8,
            "diagnostic_status": state["diagnostic"]["status"],
            "sealed_controls_sha256": file_hash(sealed / "control-comparison.json"),
            "sealed_pilot_sha256": file_hash(sealed / "pilot-comparison.json"),
            "native_receipt_sha256": {
                str(p.relative_to(folder)): file_hash(p)
                for p in sorted((folder / "inferences").glob("structured/*/calls/*.json"))
            },
        }
        report = json.loads(json.dumps(report))
        report["comparison_sha256"] = digest(report)
        save(folder / "comparison.json", report)
        state.update(
            comparison_file_sha256=file_hash(folder / "comparison.json"),
            halt_reason="limited_report_sealed",
        )
        save(folder / "checkpoint.json", state)
        return report

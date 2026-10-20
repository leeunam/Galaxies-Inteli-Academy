"""Pair sealed and recovered V9 results, then dispose only new sheets."""

from __future__ import annotations

import json

from scripts.experiment_b_vlm_quality import evaluate_gate, validate_fields
from scripts.private_checkpoint import digest, file_hash, lock, save
from scripts.vlm_per_frame import BOOLEAN_FIELDS, aggregate
from scripts.vlm_product_development import cached_result
from scripts.vlm_product_development import checked_result as checked_original
from scripts.vlm_product_plan import annotations
from scripts.vlm_product_recovery_plan import checked_result, load, result_path
from scripts.vlm_product_states import FIELD
from scripts.vlm_prompt_development import metrics
from scripts.vlm_revision import clean_workspace, seconds_for


def compare(parent, cohort, folder, root):
    preliminary = json.loads((folder / "plan.json").read_bytes())
    sealed = root / preliminary["sealed_folder"]
    with lock(sealed / ".lock"), lock(folder / ".lock"):
        plan, state = load(parent, cohort, folder, root)
        if "comparison_file_sha256" in state:
            return json.loads((folder / "comparison.json").read_bytes())
        if any(e["status"] == "running" for e in [*state["entries"], *state["inferences"]]):
            raise ValueError("recovery_interrupted_requires_audit")
        clean_workspace(root)
        completed = {e["sample_id"] for e in state["inferences"] if e["status"] == "completed"}
        if len(completed) != 31 and not state["halt_reason"]:
            raise ValueError("recovery_complete_or_recorded_stop_required")
        old = json.loads((sealed / "plan.json").read_bytes())
        truth, hashes = annotations(old, root), {}
        observations = {v: [] for v in ("v9", "v8", "v7_A", "v7_B_old32")}
        for row in plan["rows"]:
            sample = row["sample_id"]
            if sample in plan["inherited_result_sha256"]:
                path = result_path(sealed, sample)
                current = checked_original(sealed, old, row, root)
            elif sample in completed:
                path = result_path(folder, sample)
                current = checked_result(folder, plan, row, root)
            else:
                continue
            validate_fields(truth[sample], seconds_for(row))
            previous = cached_result(root, row)
            frames = [
                a | {FIELD: b[FIELD]}
                for a, b in zip(previous["per_frame"], current["per_frame"], strict=True)
            ]
            prediction = aggregate(frames, current["input_frame_seconds"])
            if any(prediction[f] != previous["parsed"][f] for f in BOOLEAN_FIELDS if f != FIELD):
                raise ValueError("recovery_person_text_cache_changed")
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
                cached = cached_result(root, row, candidate)
                if (
                    cached["input_png_sha256"] != current["input_png_sha256"]
                    or cached["input_frame_seconds"] != current["input_frame_seconds"]
                ):
                    raise ValueError("recovery_comparison_input_changed")
                observations[version].append(
                    base | {"predicted": cached["parsed"], "per_frame": cached["per_frame"]}
                )
            hashes[sample] = {"path": str(path.relative_to(root)), "sha256": file_hash(path)}
        scores, gates = {}, {}
        for version, rows in observations.items():
            scores[version] = {"all_available": metrics(rows)}
            gates[version] = {}
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
                if len(hashes) == 64 and group in ("development", "audit") and len(part) == 32:
                    gates[version][group] = evaluate_gate(part)
        ready = (
            [FIELD]
            if len(hashes) == 64
            and all(FIELD in gates["v9"][g]["released_fields"] for g in ("development", "audit"))
            else []
        )
        report = {
            "status": "product_recovery_combined_report",
            "recovery_plan_sha256": plan["plan_sha256"],
            "sealed_plan_sha256": plan["sealed_plan_sha256"],
            "evaluated_cases": len(hashes),
            "inherited_complete_cases": 33,
            "recovered_complete_cases": len(completed),
            "stop_reason": state["halt_reason"] or "completed_64",
            "metrics": scores,
            "original_gate_by_origin": gates,
            "fields_ready_for_future_blind_audit": ready,
            "released_fields": [],
            "same_pixels_and_times": True,
            "person_text_cache_preserved": True,
            "new_blind_audit": False,
            "predictive_training_started": False,
            "test_evaluated": False,
            "m1_replaced": False,
            "result_sha256": hashes,
            "new_acquisitions": len(state["entries"]),
            "new_native_reservations": state["calls_reserved"],
            "cumulative_acquisitions": 246 + len(state["entries"]),
            "cumulative_native_reservations": 1637 + state["calls_reserved"],
            "elapsed_seconds": state["elapsed_seconds"],
            "sealed_controls_sha256": file_hash(sealed / "control-comparison.json"),
            "sealed_pilot_sha256": file_hash(sealed / "pilot-comparison.json"),
            "native_receipt_sha256": {
                str(p.relative_to(folder)): file_hash(p)
                for p in sorted((folder / "inferences").glob("structured/*/calls/*.json"))
            },
        }
        report = json.loads(json.dumps(report))
        report["comparison_sha256"] = digest(report)
        path = folder / "comparison.json"
        if path.exists() and json.loads(path.read_bytes()) != report:
            raise ValueError("recovery_comparison_interrupted_changed")
        save(path, report)
        state.update(comparison_file_sha256=file_hash(path), halt_reason="recovery_report_sealed")
        save(folder / "checkpoint.json", state)
        return report


def dispose(parent, cohort, folder, root):
    preliminary = json.loads((folder / "plan.json").read_bytes())
    with lock(root / preliminary["sealed_folder"] / ".lock"), lock(folder / ".lock"):
        plan, state = load(parent, cohort, folder, root)
        if state["halt_reason"] != "recovery_report_sealed":
            raise ValueError("recovery_sealed_report_required")
        rows = {r["sample_id"]: r for r in plan["rows"]}
        path = folder / "image-disposal.json"
        if "disposal_sha256" not in state:
            images = {
                e["sample_id"]: rows[e["sample_id"]]["sheet_sha256"]
                for e in state["entries"]
                if e["status"] == "completed"
                or (folder / "images" / (e["sample_id"] + ".png")).exists()
            }
            for sample, sha in images.items():
                if file_hash(folder / "images" / (sample + ".png")) != sha:
                    raise ValueError("recovery_disposal_image_changed")
            save(
                path,
                {
                    "plan_sha256": plan["plan_sha256"],
                    "comparison_file_sha256": state["comparison_file_sha256"],
                    "images": images,
                },
            )
            state.update(disposal_sha256=file_hash(path), cleanup_pending=list(images))
            save(folder / "checkpoint.json", state)
        receipt = json.loads(path.read_bytes())
        for sample in list(state["cleanup_pending"]):
            image = folder / "images" / (sample + ".png")
            if image.exists() and file_hash(image) != receipt["images"][sample]:
                raise ValueError("recovery_disposal_image_changed")
            image.unlink(missing_ok=True)
            state["cleanup_pending"].remove(sample)
            save(folder / "checkpoint.json", state)
        if list((folder / "images").glob("*.png")):
            raise ValueError("recovery_unexpected_images_require_audit")
        state["images_disposed"] = True
        save(folder / "checkpoint.json", state)
        return {"images_removed": len(receipt["images"]), "temporary_media_retained": False}

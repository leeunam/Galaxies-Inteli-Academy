"""Bind assisted visual cue review to immutable results; no model calls or labels repair."""

from __future__ import annotations

import json

from scripts.private_checkpoint import file_hash
from scripts.vlm_product_v13 import save

METHOD = "posthoc_assisted_visual_review_not_blind_not_certified"
PHASES = {"phase1": ("preserved", 8), "phase2": ("additional", 12)}


def expected_entries(folder, plan, state, phase):
    kind, count = PHASES[phase]
    entries = [e for e in state["operations"] if e["kind"] == kind]
    if len(entries) != count or any(e["status"] != "completed" for e in entries):
        raise ValueError("v13_complete_phase_required_for_review")
    expected = {}
    for entry in entries:
        sample = entry["sample_id"]
        path = folder / "results" / kind / sample / "result.json"
        result = json.loads(path.read_bytes())["vlm"]
        for i, frame in enumerate(result["intermediate"]):
            if frame["state"] != "presented_target":
                continue
            expected[f"{sample}:{i + 1}"] = {
                "result_sha256": file_hash(path),
                "input_png_sha256": result["input_png_sha256"][i],
                "seconds": result["input_frame_seconds"][i],
                "categories": frame["presented_categories"],
                "cue": frame["presentation_cue"],
            }
    return expected


def validate_review(body, folder, plan, state, phase):
    if (
        set(body) != {"method", "plan_sha256", "phase", "preinspection_sha256", "entries"}
        or body["method"] != METHOD
        or body["plan_sha256"] != plan["plan_sha256"]
        or body["phase"] != phase
        or body["preinspection_sha256"] != plan["base"]["preinspection_sha256"]
        or type(body["entries"]) is not dict
    ):
        raise ValueError("v13_review_lineage_changed")
    expected = expected_entries(folder, plan, state, phase)
    if set(body["entries"]) != set(expected):
        raise ValueError("v13_review_must_cover_all_positive_frames")
    for key, binding in expected.items():
        actual = body["entries"][key]
        if (
            type(actual) is not dict
            or set(actual) != set(binding) | {"supported", "note"}
            or any(actual[k] != v for k, v in binding.items())
            or not (type(actual["supported"]) is bool or actual["supported"] == "unknown")
            or type(actual["note"]) is not str
            or not 1 <= len(actual["note"]) <= 2000
        ):
            raise ValueError("v13_review_prediction_binding_changed")
    return all(r["supported"] is True for r in body["entries"].values())


def check_reviews(folder, plan, state):
    if type(state["cue_reviews"]) is not dict or not set(state["cue_reviews"]) <= set(PHASES):
        raise ValueError("v13_invalid_review_state")
    passed = {}
    for phase, expected in state["cue_reviews"].items():
        path = folder / f"cue-review-{phase}.json"
        if file_hash(path) != expected:
            raise ValueError("v13_review_changed")
        passed[phase] = validate_review(json.loads(path.read_bytes()), folder, plan, state, phase)
    if any(e["kind"] == "acquisition" for e in state["operations"]) and not passed.get("phase1"):
        raise ValueError("v13_positive_cue_support_required_before_acquisition")
    return passed


def submit_review(folder, plan, state, phase, body):
    if state["sealed"] or phase in state["cue_reviews"]:
        raise ValueError("v13_review_already_consumed")
    validate_review(body, folder, plan, state, phase)
    path = folder / f"cue-review-{phase}.json"
    # Exclusive publication: an interruption requires inspection, never overwrite.
    with path.open("x") as output:
        path.chmod(0o600)
        json.dump(body, output, ensure_ascii=True, allow_nan=False, indent=2)
        output.flush()
        import os

        os.fsync(output.fileno())
    state["cue_reviews"][phase] = file_hash(path)
    save(folder / "checkpoint.json", state)

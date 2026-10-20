"""V9 product development: sealed lineage, identical inputs, cumulative accounting."""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

from scripts.private_checkpoint import digest, file_hash, lock, save
from scripts.vlm_product_states import FIELD, VARIANTS, specification, verify
from scripts.vlm_prompt_plan import FONT, controls
from scripts.vlm_prompt_plan import load as load_previous
from scripts.vlm_revision import seconds_for

PREVIOUS = Path("data/private/issue-4-vlm-v8-desenvolvimento-64")
LEGACY = Path("data/private/issue-4-vlm-revisao-1")
DIAGNOSTIC = Path("data/private/issue-4-vlm-produto-diagnostico-20261019")
FINAL_SHA = "6a76c1483b94ef0c3d761a97b54c54c08060be70441d9f098b1d6089100ea485"
BASE_SECONDS = 15159.677960556044
BASE_ACQUISITIONS = 182
BASE_CALLS = 1453
ACQUISITION_LIMIT = 256
CALL_LIMIT = 304
TIME_LIMIT = 27 * 3600
SEED = "product-v9-revealed-pilot-v1"
PROTOCOL = "vlm-product-v9-revealed-development-v1"
SOURCES = (
    "scripts/vlm_product_states.py",
    "scripts/vlm_product_plan.py",
    "scripts/vlm_product_development.py",
    "docs/issue-4-vlm-produto-v9-protocolo.md",
)


def prior(parent, cohort, root):
    if file_hash(root / DIAGNOSTIC / "final-verification.json") != FINAL_SHA:
        raise ValueError("product_previous_receipts_changed")
    final = json.loads((root / DIAGNOSTIC / "final-verification.json").read_bytes())
    protected = dict(final["protected_sha256"])
    protected.update(
        {str(DIAGNOSTIC / name): sha for name, sha in final["receipt_file_sha256"].items()}
    )
    protected[str(DIAGNOSTIC / "final-verification.json")] = FINAL_SHA
    for path, sha in protected.items():
        if file_hash(root / path) != sha:
            raise ValueError("product_protected_evidence_changed")
    plan, state = load_previous(parent, cohort, root / PREVIOUS, root)
    if (
        not state["images_disposed"]
        or state["halt_reason"] != "development_comparison_completed"
        or state["elapsed_seconds"] != BASE_SECONDS
        or state["prior_native_calls"] + state["calls_reserved"] != BASE_CALLS
        or state["prior_acquisitions"] + sum(len(e["attempts"]) for e in state["entries"])
        != BASE_ACQUISITIONS
    ):
        raise ValueError("product_previous_budget_changed")
    return plan, protected


def configuration(root):
    return {
        "sources_sha256": {name: file_hash(root / name) for name in SOURCES},
        "font_sha256": file_hash(FONT),
        "controls": controls(),
        "specifications": {v: specification(v) for v in VARIANTS},
    }


def annotations(plan, root):
    result = {}
    for group, ref in plan["annotations"].items():
        rows = json.loads((root / ref).read_bytes())["rows"]
        wanted = [r for r in plan["rows"] if r["group"] == group]
        if [r["sample_id"] for r in rows] != [r["sample_id"] for r in wanted]:
            raise ValueError("product_annotation_order_changed")
        for a, row in zip(rows, wanted, strict=True):
            if a["sheet_sha256"] != row["sheet_sha256"]:
                raise ValueError("product_annotation_image_changed")
            result[a["sample_id"]] = a["fields"]
    return result


def pilot(previous, root):
    truth = annotations(previous, root)
    negative = [r for r in previous["rows"] if truth[r["sample_id"]][FIELD]["value"] is False]
    if len(negative) != 8 or Counter(r["sector"] for r in negative) != {"beleza": 6, "moda": 2}:
        raise ValueError("product_revealed_support_changed")
    selected = [r["sample_id"] for r in negative]
    for group in ("development", "audit"):
        for sector in ("beleza", "moda"):
            positive = [
                r
                for r in previous["rows"]
                if r["group"] == group
                and r["sector"] == sector
                and truth[r["sample_id"]][FIELD]["value"] is True
            ]
            if len(positive) < 2:
                raise ValueError("product_pilot_support_missing")
            selected.extend(
                r["sample_id"]
                for r in sorted(positive, key=lambda r: digest([SEED, r["sample_id"]]))[:2]
            )
    return selected


def prepare(parent, cohort, folder, root):
    previous, protected = prior(parent, cohort, root)
    body = {
        "protocol": PROTOCOL,
        "previous_plan_sha256": previous["plan_sha256"],
        "cohort_sha256": previous["cohort_sha256"],
        "partition_sha256": previous["partition_sha256"],
        "rows": previous["rows"],
        "annotations": previous["annotations"],
        "pilot_ids": pilot(previous, root),
        "pilot_seed": SEED,
        "config": configuration(root),
        "protected_sha256": protected,
        "candidate": "structured",
        "new_blind_audit": False,
        "test_evaluated": False,
    }
    body["plan_sha256"] = digest(body)
    with lock(folder / ".lock"):
        if any(p.name != ".lock" for p in folder.iterdir()):
            raise ValueError("product_output_already_exists")
        save(folder / "plan.json", body)
        save(
            folder / "checkpoint.json",
            {
                "plan_sha256": body["plan_sha256"],
                "prior_acquisitions": BASE_ACQUISITIONS,
                "prior_native_calls": BASE_CALLS,
                "acquisition_limit": ACQUISITION_LIMIT,
                "elapsed_seconds": BASE_SECONDS,
                "calls_reserved": 0,
                "dns_retries_used": 0,
                "entries": [],
                "controls": [],
                "inferences": [],
                "halt_reason": None,
                "images_disposed": False,
            },
        )
    return body


def result_path(folder, sample, variant="structured", control=False):
    return (
        folder / ("control-results" if control else "inferences") / variant / sample / "result.json"
    )


def load(parent, cohort, folder, root):
    previous, protected = prior(parent, cohort, root)
    plan = json.loads((folder / "plan.json").read_bytes())
    state = json.loads((folder / "checkpoint.json").read_bytes())
    expected = {
        "protocol": PROTOCOL,
        "previous_plan_sha256": previous["plan_sha256"],
        "cohort_sha256": previous["cohort_sha256"],
        "partition_sha256": previous["partition_sha256"],
        "rows": previous["rows"],
        "annotations": previous["annotations"],
        "pilot_ids": pilot(previous, root),
        "pilot_seed": SEED,
        "config": configuration(root),
        "protected_sha256": protected,
        "candidate": "structured",
        "new_blind_audit": False,
        "test_evaluated": False,
    }
    if (
        plan != expected | {"plan_sha256": digest(expected)}
        or state["plan_sha256"] != plan["plan_sha256"]
        or len(plan["rows"]) != 64
        or any(r["partition"] != "train" for r in plan["rows"])
    ):
        raise ValueError("product_plan_or_frozen_inputs_changed")
    validate_state(plan, state, folder, root)
    return plan, state


def validate_state(plan, state, folder, root):
    rows = {r["sample_id"]: r for r in plan["rows"]}
    allowed_controls = {(v, r["sample_id"]) for v in VARIANTS for r in controls()}
    for field in ("entries", "controls", "inferences"):
        ids = [
            (e["variant"], e["sample_id"]) if field == "controls" else e["sample_id"]
            for e in state[field]
        ]
        if len(ids) != len(set(ids)) or not set(ids) <= (
            allowed_controls if field == "controls" else set(rows)
        ):
            raise ValueError("product_invalid_ledger_keys")
    elapsed, calls, attempts, retries = BASE_SECONDS, 0, 0, 0
    for e in [*state["entries"], *state["controls"], *state["inferences"]]:
        seconds = e.get("seconds", 0.0)
        if (
            e["status"] not in ("running", "completed", "failed")
            or type(seconds) not in (int, float)
            or not math.isfinite(seconds)
            or seconds < 0
        ):
            raise ValueError("product_invalid_ledger_entry")
        elapsed += seconds
    for e in state["entries"]:
        tries = e["attempts"]
        if not 1 <= len(tries) <= 2 or (
            e["status"] != "running" and tries[-1]["status"] != e["status"]
        ):
            raise ValueError("product_invalid_attempts")
        attempts += len(tries)
        retries += len(tries) - 1
        for attempt in tries:
            if attempt["status"] not in ("running", "completed", "failed") or (
                attempt["status"] != "running"
                and (
                    type(attempt.get("seconds")) not in (int, float)
                    or not math.isfinite(attempt["seconds"])
                    or attempt["seconds"] < 0
                )
            ):
                raise ValueError("product_invalid_attempts")
        if e["status"] in ("completed", "failed"):
            for i, attempt in enumerate(tries):
                record = (
                    folder / "failed-attempts" / e["sample_id"] / str(i + 1) / "run.json"
                    if i < len(tries) - 1
                    else folder / "sessions" / e["sample_id"] / "run.json"
                )
                if attempt.get("run_receipt_missing") is True:
                    if record.exists() or e["status"] == "completed":
                        raise ValueError("product_terminal_run_changed")
                elif not record.is_file() or file_hash(record) != attempt.get("run_sha256"):
                    raise ValueError("product_terminal_run_changed")
        if len(tries) == 2:
            first = tries[0]
            if (
                first["reason"] != "temporary_network_dns_failure"
                or first["cleanup"] is not True
                or first["dns_preflight_positive"] is not True
                or file_hash(folder / "failed-attempts" / e["sample_id"] / "1/run.json")
                != first["run_sha256"]
            ):
                raise ValueError("product_dns_recovery_changed")
        if e["status"] == "completed":
            if set(e["files_sha256"]) != {"features.json", "run.json"}:
                raise ValueError("product_acquisition_evidence_changed")
            for name, sha in e["files_sha256"].items():
                if file_hash(folder / "sessions" / e["sample_id"] / name) != sha:
                    raise ValueError("product_acquisition_evidence_changed")
            row = rows[e["sample_id"]]
            identity = json.loads(
                (folder / "sessions" / e["sample_id"] / "features.json").read_bytes()
            )
            previous = json.loads(
                (root / PREVIOUS / "sessions" / e["sample_id"] / "features.json").read_bytes()
            )
            run = json.loads((folder / "sessions" / e["sample_id"] / "run.json").read_bytes())
            if (
                identity["sample_id"] != row["sample_id"]
                or identity["properties"] != row["properties"]
                or identity["sheet_sha256"] != row["sheet_sha256"]
                or identity["input_frame_seconds"] != seconds_for(row)
                or identity["input_png_sha256"] != previous["input_png_sha256"]
                or run["status"] != "completed"
                or run["temporary_directory_removed"] is not True
            ):
                raise ValueError("product_original_pixels_or_times_changed")
    for control, entries in ((True, state["controls"]), (False, state["inferences"])):
        for e in entries:
            expected = 1 if control else len(seconds_for(rows[e["sample_id"]]))
            n = e["call_count"]
            if (
                type(n) is not int
                or not 0 <= n <= expected
                or (not control and e["variant"] != "structured")
            ):
                raise ValueError("product_invalid_call_count")
            calls += n
            if e["status"] == "completed":
                path = result_path(folder, e["sample_id"], e["variant"], control)
                body = json.loads(path.read_bytes())
                if (
                    n != expected
                    or file_hash(path) != e["result_sha256"]
                    or body["sample_id"] != e["sample_id"]
                    or body["plan_sha256"] != plan["plan_sha256"]
                    or body["config_sha256"] != digest(plan["config"])
                    or body["vlm"]["variant"] != e["variant"]
                ):
                    raise ValueError("product_inference_evidence_changed")
                verify(body["vlm"], path.parent / "calls")
                cached_path = (
                    root
                    / PREVIOUS
                    / ("control-results" if control else "inferences")
                    / e["sample_id"]
                    / "result.json"
                )
                cached = json.loads(cached_path.read_bytes())["vlm"]
                if (
                    body["vlm"]["input_png_sha256"] != cached["input_png_sha256"]
                    or body["vlm"]["input_frame_seconds"] != cached["input_frame_seconds"]
                    or not control
                    and body["sheet_sha256"] != rows[e["sample_id"]]["sheet_sha256"]
                ):
                    raise ValueError("product_original_pixels_or_times_changed")
    if (
        state["prior_acquisitions"] != BASE_ACQUISITIONS
        or state["prior_native_calls"] != BASE_CALLS
        or state["acquisition_limit"] != ACQUISITION_LIMIT
        or attempts + BASE_ACQUISITIONS > ACQUISITION_LIMIT
        or retries > 10
        or state["dns_retries_used"] != retries
        or type(state["calls_reserved"]) is not int
        or calls != state["calls_reserved"]
        or calls > CALL_LIMIT
        or not math.isfinite(state["elapsed_seconds"])
        or not math.isclose(elapsed, state["elapsed_seconds"], rel_tol=0, abs_tol=1e-8)
    ):
        raise ValueError("product_cumulative_budget_changed")
    pending = state.get("cleanup_pending")
    if pending is not None or state["images_disposed"]:
        journal = folder / "image-disposal.json"
        receipt = json.loads(journal.read_bytes())
        required = {
            e["sample_id"]: rows[e["sample_id"]]["sheet_sha256"]
            for e in state["entries"]
            if e["status"] == "completed"
        }
        expected = receipt.get("images", {})
        attempted = {e["sample_id"] for e in state["entries"]}
        if (
            type(expected) is not dict
            or not set(required) <= set(expected) <= attempted
            or any(sha != rows[sample]["sheet_sha256"] for sample, sha in expected.items())
            or receipt
            != {
                "images": expected,
                "plan_sha256": plan["plan_sha256"],
                "comparison_file_sha256": state["comparison_file_sha256"],
            }
            or file_hash(journal) != state["disposal_sha256"]
            or type(pending) is not list
            or len(pending) != len(set(pending))
            or not set(pending) <= set(expected)
            or state["images_disposed"]
            and pending
            or state["halt_reason"] != "product_report_sealed"
        ):
            raise ValueError("product_disposal_evidence_changed")
    image_samples = (
        set(expected)
        if pending is not None
        else {e["sample_id"] for e in state["entries"] if e["status"] == "completed"}
    )
    for sample in image_samples:
        image = folder / "images" / (sample + ".png")
        if pending is None:
            if file_hash(image) != rows[sample]["sheet_sha256"]:
                raise ValueError("product_sheet_changed")
        elif image.exists() and (
            sample not in pending or file_hash(image) != rows[sample]["sheet_sha256"]
        ):
            raise ValueError("product_disposal_evidence_changed")
    if state["images_disposed"] and list((folder / "images").glob("*.png")):
        raise ValueError("product_disposal_evidence_changed")
    for key, name in (
        ("control_comparison_sha256", "control-comparison.json"),
        ("pilot_comparison_sha256", "pilot-comparison.json"),
        ("comparison_file_sha256", "comparison.json"),
    ):
        if key in state and file_hash(folder / name) != state[key]:
            raise ValueError("product_comparison_evidence_changed")
    if state["halt_reason"] == "product_report_sealed" and "comparison_file_sha256" not in state:
        raise ValueError("product_comparison_evidence_changed")
    if "comparison_file_sha256" in state:
        report = json.loads((folder / "comparison.json").read_bytes())
        result_hashes = {
            e["sample_id"]: e["result_sha256"]
            for e in state["inferences"]
            if e["status"] == "completed"
        }
        if (
            report.get("comparison_sha256")
            != digest({k: v for k, v in report.items() if k != "comparison_sha256"})
            or report.get("plan_sha256") != plan["plan_sha256"]
            or report.get("result_sha256") != result_hashes
            or report.get("evaluated_cases") != len(result_hashes)
            or report.get("released_fields") != []
            or any(
                report.get(k) is not False
                for k in (
                    "new_blind_audit",
                    "predictive_training_started",
                    "test_evaluated",
                    "m1_replaced",
                )
            )
        ):
            raise ValueError("product_comparison_evidence_changed")
    if "control_comparison_sha256" in state:
        counts = {v: Counter() for v in VARIANTS}
        if len(state["controls"]) != 48 or any(
            e["status"] != "completed" for e in state["controls"]
        ):
            raise ValueError("product_comparison_evidence_changed")
        for e in state["controls"]:
            body = json.loads(result_path(folder, e["sample_id"], e["variant"], True).read_bytes())
            value = body["vlm"]["parsed"][FIELD]["value"]
            counts[e["variant"]][str(value).lower()] += 1
            counts[e["variant"]]["correct"] += value is False
        expected = {
            "plan_sha256": plan["plan_sha256"],
            "scores": {v: dict(c) for v, c in counts.items()},
            "real_inputs_allowed": counts["structured"]["correct"] == 12,
            "variants_selected_by_controls": False,
        }
        if json.loads((folder / "control-comparison.json").read_bytes()) != expected:
            raise ValueError("product_comparison_evidence_changed")
    if "pilot_comparison_sha256" in state:
        complete = {e["sample_id"] for e in state["inferences"] if e["status"] == "completed"}
        if not set(plan["pilot_ids"]) <= complete:
            raise ValueError("product_comparison_evidence_changed")
        truth = annotations(plan, root)
        support, correct = Counter(), Counter()
        for row in plan["rows"]:
            if row["sample_id"] not in plan["pilot_ids"]:
                continue
            actual = truth[row["sample_id"]][FIELD]
            body = json.loads(result_path(folder, row["sample_id"]).read_bytes())
            predicted = body["vlm"]["parsed"][FIELD]
            key = row["sector"] + "/" + str(actual["value"]).lower()
            support[key] += 1
            correct[key] += (
                predicted["value"] == actual["value"]
                and bool(predicted["frames"])
                and set(predicted["frames"]) <= set(actual["frames"])
            )
        expected = {
            "support": dict(support),
            "correct_value_and_evidence": dict(correct),
            "continue": all(
                correct[s + "/" + v] >= 1 for s in ("beleza", "moda") for v in ("true", "false")
            ),
            "independent_validation": False,
        }
        if json.loads((folder / "pilot-comparison.json").read_bytes()) != expected:
            raise ValueError("product_comparison_evidence_changed")


def runnable(state):
    if state["halt_reason"] or state["images_disposed"]:
        raise ValueError("product_halted_no_automatic_retry")
    if any(
        e["status"] == "running"
        for e in [*state["entries"], *state["controls"], *state["inferences"]]
    ):
        raise ValueError("product_interrupted_requires_audit")
    if state["elapsed_seconds"] >= TIME_LIMIT:
        raise ValueError("product_time_budget_exhausted")


def persist(folder, state, entry, started, clock):
    entry["seconds"] = clock() - started
    state["elapsed_seconds"] = BASE_SECONDS + sum(
        e.get("seconds", 0.0) for e in [*state["entries"], *state["controls"], *state["inferences"]]
    )
    save(folder / "checkpoint.json", state)

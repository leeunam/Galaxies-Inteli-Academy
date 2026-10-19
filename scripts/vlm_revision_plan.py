"""Training-only, immutable inputs and accounting for a fresh perceptual audit."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

from scripts.experiment_b_vlm_extract import anchored_metadata
from scripts.experiment_b_vlm_extract import configuration as old_configuration
from scripts.pilot_licensed_media import select_vlm_samples
from scripts.private_checkpoint import digest, file_hash, lock, private_path, save
from scripts.vlm_per_frame import specification, verify

PROTOCOL = "b-vlm-perception-revision-v1"
OLD = Path("data/private/issue-4-experimento-b-vlm-300-v1")
OLD_FINAL_SHA256 = "23f6a817d11088ccf35a5f207a489091f993ee5ce4c4eedc3633a5cbe3c5fc0f"
OLD_CHECKPOINT_SHA256 = "26e9dc8ed172d792aae7fcf291bafa1e26b8da8164777a318ce36b5fa058201e"
BASE_SECONDS = 2404.7164981560236
BASE_ACQUISITIONS = 54
ACQUISITION_LIMIT = 128
CALL_LIMIT = 900
TIME_LIMIT = 27 * 3600
NEW_SOURCES = (
    "scripts/vlm_per_frame.py",
    "scripts/vlm_revision_plan.py",
    "scripts/vlm_revision.py",
    "scripts/experiment_b_vlm_quality.py",
    "docs/issue-4-vlm-revisao-perceptiva-protocolo.md",
)


def fresh_sample(assignments, old_ids):
    by_id = {r.sample_id: r for r in assignments}
    if (
        len(old_ids) != 32
        or len(set(old_ids)) != 32
        or any(s not in by_id or by_id[s].partition != "train" for s in old_ids)
    ):
        raise ValueError("old_audit_must_be_32_training_ids")
    old_channels = {by_id[s].channel_id for s in old_ids}
    old_media = {by_id[s].media_sha256 for s in old_ids}
    selected, used_channels, used_media = [], set(), set()
    for sector in ("beleza", "moda"):
        # Filter partition before any sampling and before opening evidence.
        candidates = [
            r
            for r in assignments
            if r.partition == "train"
            and r.sector == sector
            and r.sample_id not in old_ids
            and r.channel_id not in old_channels
            and r.media_sha256 not in old_media
        ]
        channels = sorted(
            {r.channel_id for r in candidates},
            key=lambda c: digest(
                {"protocol": PROTOCOL, "purpose": "audit_channel", "sector": sector, "channel": c}
            ),
        )
        group = []
        for channel in channels:
            if channel in used_channels:
                continue
            videos = sorted(
                (
                    r
                    for r in candidates
                    if r.channel_id == channel and r.media_sha256 not in used_media
                ),
                key=lambda r: digest(
                    {"protocol": PROTOCOL, "purpose": "audit_video", "sample": r.sample_id}
                ),
            )
            if videos:
                group.append(videos[0].sample_id)
                used_channels.add(channel)
                used_media.add(videos[0].media_sha256)
            if len(group) == 16:
                break
        if len(group) != 16:
            raise ValueError("requires_16_fresh_training_channels_per_sector")
        selected.extend(group)
    return tuple(selected)


def prior(root):
    folder = root / OLD
    if file_hash(folder / "final-verification.json") != OLD_FINAL_SHA256 or (
        file_hash(folder / "queue-v3/checkpoint.json") != OLD_CHECKPOINT_SHA256
    ):
        raise ValueError("previous_vlm_final_evidence_changed")
    final = json.loads((folder / "final-verification.json").read_bytes())
    checkpoint = json.loads((folder / "queue-v3/checkpoint.json").read_bytes())
    if (
        checkpoint["elapsed_seconds"] != BASE_SECONDS
        or checkpoint["prior_acquisitions"] + sum(len(e["attempts"]) for e in checkpoint["entries"])
        != BASE_ACQUISITIONS
        or checkpoint["halt_reason"] != "quality_gate_no_columns_released"
    ):
        raise ValueError("previous_vlm_budget_not_preserved")
    for name, expected in final["frozen_file_sha256"].items():
        if file_hash(root / name) != expected:
            raise ValueError("protected_model_or_service_changed")
    return final


def configuration(root):
    return {
        "parent": old_configuration(root),
        "sources_sha256": {s: file_hash(root / s) for s in NEW_SOURCES},
        "candidates": {name: specification(name) for name in ("A", "B")},
    }


def prepare(parent, cohort, folder, root):
    manifest, anchor = anchored_metadata(parent, cohort, root)
    final = prior(root)
    old_plan_path = root / OLD / "queue-v3/plan.json"
    old_plan = json.loads(old_plan_path.read_bytes())
    dev = tuple(old_plan["audit_sample_ids"])
    audit = fresh_sample(manifest.assignments, dev)
    by_id = {r.sample_id: r for r in manifest.assignments if r.partition == "train"}
    index = json.loads((cohort / "evidence-index.json").read_bytes())
    rows = []
    for group, ids in (("development", dev), ("audit", audit)):
        for sample in ids:
            r, item = by_id[sample], index[sample]
            relative = Path(item["features_ref"])
            source = private_path(root / relative, root)
            if relative.is_absolute() or not re.fullmatch(r"[A-Za-z0-9_-]{11}", sample):
                raise ValueError("unsafe_revision_evidence_reference")
            expected = item["curation"]["features_sha256"]
            if file_hash(source) != expected:
                raise ValueError("revision_training_evidence_changed")
            properties = json.loads(source.read_bytes())["properties"]
            annotation = item["curation"]
            rows.append(
                {
                    "sample_id": sample,
                    "sector": r.sector,
                    "partition": "train",
                    "group": group,
                    "channel_id": r.channel_id,
                    "media_sha256": r.media_sha256,
                    "features_ref": str(relative),
                    "features_sha256": expected,
                    "properties": properties,
                    "sheet_sha256": annotation["contact_sheet_sha256"],
                    "sheet_recipe": {
                        k: annotation[k]
                        for k in ("source_batch", "source_index")
                        if k in annotation
                    },
                }
            )
    old_annotations = root / OLD / "blind-annotations-v3.json"
    protected = dict(final["frozen_file_sha256"])
    protected.update(
        {
            str(OLD / name): file_hash(root / OLD / name)
            for name in (
                "blind-annotations-v3.json",
                "quality-release-v3.json",
                "final-verification.json",
                "queue-v3/plan.json",
                "queue-v3/checkpoint.json",
            )
        }
    )
    protected.update(old_plan["config"]["sources_sha256"])
    protected.update(
        {
            "scripts/" + name: file_hash(root / "scripts" / name)
            for name in (
                "experiment_b_vlm_quality.py",
                "experiment_b_vlm_data.py",
                "experiment_b_vlm_artifact.py",
                "train_experiment_b_vlm.py",
            )
        }
    )
    body = {
        "protocol": PROTOCOL,
        "cohort_sha256": anchor.cohort_sha256,
        "partition_sha256": anchor.partition_manifest_sha256,
        "config": configuration(root),
        "old_annotations_sha256": file_hash(old_annotations),
        "rows": rows,
        "protected_sha256": protected,
        "labels_used": False,
        "test_evaluated": False,
    }
    body["plan_sha256"] = digest(body)
    with lock(folder / ".lock"):
        if any(p.name != ".lock" for p in folder.iterdir()):
            raise ValueError("revision_output_already_exists")
        save(folder / "plan.json", body)
        save(
            folder / "checkpoint.json",
            {
                "plan_sha256": body["plan_sha256"],
                "prior_acquisitions": BASE_ACQUISITIONS,
                "acquisition_limit": ACQUISITION_LIMIT,
                "elapsed_seconds": BASE_SECONDS,
                "dns_retries_used": 0,
                "calls_reserved": 0,
                "entries": [],
                "inferences": [],
                "halt_reason": None,
                "images_disposed": False,
            },
        )
    return body


def load(parent, cohort, folder, root):
    manifest, anchor = anchored_metadata(parent, cohort, root)
    prior(root)
    plan = json.loads((folder / "plan.json").read_bytes())
    state = json.loads((folder / "checkpoint.json").read_bytes())
    if (
        plan["protocol"] != PROTOCOL
        or plan["config"] != configuration(root)
        or plan["plan_sha256"] != digest({k: v for k, v in plan.items() if k != "plan_sha256"})
        or state["plan_sha256"] != plan["plan_sha256"]
        or plan["cohort_sha256"] != anchor.cohort_sha256
        or plan["partition_sha256"] != anchor.partition_manifest_sha256
    ):
        raise ValueError("revision_plan_or_configuration_changed")
    by_id = {r.sample_id: r for r in manifest.assignments if r.partition == "train"}
    dev = tuple(r["sample_id"] for r in plan["rows"] if r["group"] == "development")
    old_plan = json.loads((root / OLD / "queue-v3/plan.json").read_bytes())
    audit = tuple(r["sample_id"] for r in plan["rows"] if r["group"] == "audit")
    if (
        dev != tuple(old_plan["audit_sample_ids"])
        or audit != fresh_sample(manifest.assignments, dev)
        or len(plan["rows"]) != 64
        or len(set(dev + audit)) != 64
    ):
        raise ValueError("revision_training_sample_changed")
    for r in plan["rows"]:
        actual = by_id.get(r["sample_id"])
        if actual is None or any(
            getattr(actual, f) != r[f]
            for f in ("sector", "partition", "channel_id", "media_sha256")
        ):
            raise ValueError("revision_assignment_changed")
        if file_hash(private_path(root / r["features_ref"], root)) != r["features_sha256"]:
            raise ValueError("revision_training_evidence_changed")
    for name, expected in plan["protected_sha256"].items():
        if file_hash(root / name) != expected:
            raise ValueError("revision_protected_evidence_changed")
    validate_state(plan, state, folder)
    return plan, state


def validate_state(plan, state, folder):
    rows = {r["sample_id"]: r for r in plan["rows"]}
    ids = [e["sample_id"] for e in state["entries"]]
    keys = [(e["sample_id"], e["candidate"]) for e in state["inferences"]]
    if len(ids) != len(set(ids)) or not set(ids) <= set(rows) or len(keys) != len(set(keys)):
        raise ValueError("invalid_revision_ledger_keys")
    if any(s not in rows or c not in ("A", "B") for s, c in keys):
        raise ValueError("invalid_revision_inference_keys")
    accounted, retries, calls, attempts = BASE_SECONDS, 0, 0, 0
    for e in [*state["entries"], *state["inferences"]]:
        if e["status"] not in ("running", "completed", "failed") or (
            type(e.get("seconds", 0.0)) not in (int, float)
            or not math.isfinite(e.get("seconds", 0.0))
            or e.get("seconds", 0.0) < 0
        ):
            raise ValueError("invalid_revision_ledger_entry")
        accounted += e.get("seconds", 0.0)
    for e in state["entries"]:
        a = e.get("attempts", [])
        if not 1 <= len(a) <= 2 or e["status"] != "running" and a[-1]["status"] != e["status"]:
            raise ValueError("invalid_revision_acquisition_attempts")
        for attempt in a:
            if attempt["status"] not in ("running", "failed", "completed") or (
                attempt["status"] != "running"
                and (
                    type(attempt["seconds"]) not in (int, float)
                    or not math.isfinite(attempt["seconds"])
                    or attempt["seconds"] < 0
                )
            ):
                raise ValueError("invalid_revision_attempt_status_or_time")
        attempts += len(a)
        retries += len(a) - 1
        if len(a) == 2:
            failed = folder / "failed-attempts" / e["sample_id"] / "1/run.json"
            if (
                a[0]["reason"] != "temporary_network_dns_failure"
                or a[0]["cleanup"] is not True
                or a[0]["dns_preflight_positive"] is not True
                or file_hash(failed) != a[0]["run_sha256"]
            ):
                raise ValueError("revision_dns_recovery_evidence_changed")
        if e["status"] == "completed":
            if set(e["files_sha256"]) != {"features.json", "run.json"}:
                raise ValueError("revision_acquisition_hashes_incomplete")
            for name, h in e["files_sha256"].items():
                if (
                    name not in {"features.json", "run.json"}
                    or file_hash(folder / "sessions" / e["sample_id"] / name) != h
                ):
                    raise ValueError("revision_acquisition_evidence_changed")
            if (
                not state["images_disposed"]
                and file_hash(folder / "images" / f"{e['sample_id']}.png")
                != rows[e["sample_id"]]["sheet_sha256"]
            ):
                raise ValueError("revision_audit_image_changed")
    for e in state["inferences"]:
        row = rows[e["sample_id"]]
        props = row["properties"]
        frame_count = len(
            select_vlm_samples(list(range(len(props["sampled_frame_seconds"]))), props)[1]
        )
        expected_calls = frame_count * (1 if e["candidate"] == "A" else 3)
        if type(e["call_count"]) is not int or not 0 <= e["call_count"] <= expected_calls:
            raise ValueError("invalid_revision_call_counter")
        calls += e["call_count"]
        if e["status"] == "completed":
            path = folder / "inferences" / e["candidate"] / e["sample_id"] / "result.json"
            if file_hash(path) != e["result_sha256"]:
                raise ValueError("revision_inference_evidence_changed")
            result = json.loads(path.read_bytes())
            verify(result["vlm"], path.parent / "calls")
            if e["call_count"] != expected_calls:
                raise ValueError("revision_completed_call_count_mismatch")
    if (
        state["prior_acquisitions"] != BASE_ACQUISITIONS
        or state["acquisition_limit"] != ACQUISITION_LIMIT
        or BASE_ACQUISITIONS + attempts > ACQUISITION_LIMIT
        or type(state["dns_retries_used"]) is not int
        or state["dns_retries_used"] != retries
        or retries > 10
        or type(state["calls_reserved"]) is not int
        or state["calls_reserved"] != calls
        or calls > CALL_LIMIT
        or not math.isfinite(state["elapsed_seconds"])
        or not math.isclose(state["elapsed_seconds"], accounted, rel_tol=0, abs_tol=1e-8)
    ):
        raise ValueError("revision_cumulative_budget_changed")
    if state["images_disposed"]:
        path = folder / "image-disposal.json"
        disposal = json.loads(path.read_bytes())
        if (
            file_hash(path) != state["disposal_sha256"]
            or disposal["images"] != {r["sample_id"]: r["sheet_sha256"] for r in plan["rows"]}
            or state["halt_reason"]
            not in ("audit_completed_columns_released", "quality_gate_no_columns_released")
            or list((folder / "images").glob("*.png"))
        ):
            raise ValueError("revision_disposal_evidence_changed")


def persist(folder, state, entry, started, clock):
    entry["seconds"] = clock() - started
    state["elapsed_seconds"] = BASE_SECONDS + sum(
        e.get("seconds", 0.0) for e in [*state["entries"], *state["inferences"]]
    )
    save(folder / "checkpoint.json", state)


def runnable(state):
    if state["halt_reason"] or state["images_disposed"]:
        raise ValueError("revision_halted_no_automatic_retry")
    if any(e["status"] == "running" for e in [*state["entries"], *state["inferences"]]):
        raise ValueError("revision_interrupted_session_requires_audit")
    if state["elapsed_seconds"] >= TIME_LIMIT:
        raise ValueError("revision_total_time_budget_exhausted")

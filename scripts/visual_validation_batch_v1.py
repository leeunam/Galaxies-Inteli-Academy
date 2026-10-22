"""Inactive native batch controller; tests inject synthetic assets and owned Python children."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import io
import json
import math
import os
import shutil
import stat
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from scripts import visual_validation_capture_v1 as capture
from scripts import vlm_native225_probe_v2 as native
from scripts.visual_validation_contract_v1 import (
    PROPOSAL_SHA256,
    commitment,
    digest,
    identifier,
    is_sha,
    load_proposal,
    plain,
    read_json,
    require,
    write_new,
)
from scripts.visual_validation_selection_v1 import ROW_KEYS, annotation_packet
from scripts.vlm_native_contrast_v2 import _DeadlineProcess

ROOT = Path(__file__).resolve().parents[1]
NATIVE_DISPATCH_RELEASED = False
NAMESPACE = capture.NAMESPACE
POSITIVE_SHA256 = "238d3b775563fdffe47c3bfdce9c6623058642194f108107f58fcd9a10ae89e1"
CONTROL_PLAN_FILE_SHA256 = "eb54f2b6fdfe8415e5a4d586850fcd5118324f7b8be63bd558c538eed0e31734"
ARITHMETIC_SOURCE_SHA256 = "1a9c2dfd539c029f4e6debecb913c10fce9926aa3881284b91aa114201b2c1b0"
GEOMETRY_PROOF = (
    "data/private/issue-4-native225-batch-controller-preparation-v1/geometry-proof.json"
)
SOURCE_FILES = (
    "scripts/visual_validation_batch_v1.py",
    "scripts/visual_validation_capture_v1.py",
    "scripts/visual_validation_contract_v1.py",
    "scripts/visual_validation_selection_v1.py",
    "scripts/visual_validation_annotations_v1.py",
    "scripts/visual_validation_sidecar_v1.py",
    "scripts/visual_validation_batch_sidecar_v1.py",
    "scripts/vlm_native225_probe_v2.py",
    "scripts/vlm_durable_capture_v2.py",
    "scripts/vlm_encoder_probe.py",
    "scripts/vlm_native_contrast_v2.py",
)
JOB_KEYS = {
    "call_id",
    "stage",
    "alias",
    "frame_index",
    "kind",
    "input_path",
    "input_png_sha256",
    "expected_tokens",
    "use_until_epoch",
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def root_digest(root):
    return hashlib.sha256(str(plain(root).resolve()).encode()).hexdigest()


def source_hashes():
    proposal_sources = load_proposal()["source_sha256"]
    require(
        all(sha(ROOT / name) == expected for name, expected in proposal_sources.items()),
        "visual_frozen_candidate_source_changed",
    )
    return {name: sha(ROOT / name) for name in sorted(set(SOURCE_FILES) | set(proposal_sources))}


def geometry_proof():
    path = ROOT / GEOMETRY_PROOF
    value = read_json(path)
    require(
        value.get("schema") == "native225-pure-arithmetic-proof-v1"
        and value.get("source_sha256") == ARITHMETIC_SOURCE_SHA256
        and value.get("model_loaded") is False
        and value.get("model_calls") == 0
        and {tuple(c["input"]) for c in value["cases"]} == {(320, 330), (360, 640)}
        and all(c["tokens"] == 240 for c in value["cases"]),
        "visual_geometry_preflight_required",
    )
    return sha(path)


def prepare_configuration(
    root, *, stage, jobs, runtime_template, assets, data_kind="observed", selection=None
):
    """Metadata declarations only. Does not create a run, read assets/images or authorize."""
    proposal = load_proposal()
    value = {
        "schema": "visual-validation-batch-configuration-v1",
        "proposal_sha256": PROPOSAL_SHA256,
        "execution_root_sha256": root_digest(root),
        "source_files_sha256": source_hashes(),
        "candidate_sha256": digest(proposal["candidate"]),
        "limits": proposal["limits"],
        "stage": stage,
        "jobs": jobs,
        "runtime_template": list(runtime_template),
        "assets": assets,
        "asset_references": {n: native._asset_reference(Path(n)) for n in assets},
        "geometry_proof_sha256": geometry_proof() if data_kind == "observed" else None,
        "data_kind": data_kind,
        "selection": selection,
    }
    value["configuration_sha256"] = digest(value)
    validate_configuration(value, root, allow_synthetic=data_kind == "synthetic")
    return value


def validate_configuration(value, root, *, allow_synthetic=False):
    commitment(value, "configuration_sha256")
    require(
        set(value)
        == {
            "schema",
            "proposal_sha256",
            "execution_root_sha256",
            "source_files_sha256",
            "candidate_sha256",
            "limits",
            "stage",
            "jobs",
            "runtime_template",
            "assets",
            "asset_references",
            "data_kind",
            "selection",
            "geometry_proof_sha256",
            "configuration_sha256",
        },
        "visual_configuration_fields",
    )
    proposal = load_proposal()
    require(
        value["schema"] == "visual-validation-batch-configuration-v1"
        and value["proposal_sha256"] == PROPOSAL_SHA256
        and value["execution_root_sha256"] == root_digest(root)
        and value["candidate_sha256"] == digest(proposal["candidate"])
        and value["limits"] == proposal["limits"]
        and value["source_files_sha256"] == source_hashes(),
        "visual_batch_configuration_changed",
    )
    require(
        value["data_kind"] == "observed" or (allow_synthetic and value["data_kind"] == "synthetic"),
        "visual_synthetic_scope_required",
    )
    stage, jobs = value["stage"], value["jobs"]
    require(stage in ("development", "audit") and type(jobs) is list, "visual_batch_stage")
    if stage == "development":
        require(len(jobs) == 13 and value["selection"] is None, "visual_development_schedule")
    else:
        selection = value["selection"]
        commitment(selection, "selection_sha256")
        annotation_packet(selection)
        require(
            selection["proposal_sha256"] == PROPOSAL_SHA256
            and len({row["alias"] for row in selection["rows"]}) == 32
            and all(
                set(row) == ROW_KEYS | {"alias"} and row["partition"] == "train"
                for row in selection["rows"]
            ),
            "visual_blind_training_selection",
        )
        require(
            len(selection["rows"]) == 32
            and 96 <= len(jobs) == selection["audit_calls_exact"] <= 384,
            "visual_audit_schedule",
        )
        expected = [
            (row["alias"], index, kind, png)
            for row in selection["rows"]
            for index, png in enumerate(row["frame_sha256"], 1)
            for kind in ("person_visible", "product_visible_early", "screen_text")
        ]
    paths = {}
    for index, job in enumerate(jobs):
        require(type(job) is dict and set(job) == JOB_KEYS, "visual_batch_job_shape")
        require(
            type(job["call_id"]) is int
            and job["call_id"] == index + (1 if stage == "development" else 14)
            and job["stage"] == stage
            and identifier(job["alias"])
            and type(job["frame_index"]) is int
            and job["frame_index"] >= 1
            and is_sha(job["input_png_sha256"])
            and type(job["expected_tokens"]) is int
            and job["expected_tokens"] == 240
            and type(job["use_until_epoch"]) in (int, float)
            and math.isfinite(job["use_until_epoch"]),
            "visual_batch_job_binding",
        )
        path = str(plain(job["input_path"]))
        if path in paths:
            require(paths[path] == job["input_png_sha256"], "visual_input_path_identity_conflict")
        paths[path] = job["input_png_sha256"]
        if stage == "development":
            controls = proposal["development"]["product_negative_controls"]
            require(
                job["alias"] == (controls[index]["sample_id"] if index < 12 else "native-positive")
                and job["kind"] == ("product_visible_early" if index < 12 else "relation")
                and job["frame_index"] == 1,
                "visual_development_job_order",
            )
            if index == 12 and value["data_kind"] == "observed":
                require(job["input_png_sha256"] == POSITIVE_SHA256, "visual_positive_identity")
        else:
            require(
                (job["alias"], job["frame_index"], job["kind"], job["input_png_sha256"])
                == expected[index],
                "visual_blind_job_order",
            )
    template, assets = value["runtime_template"], value["assets"]
    require(
        type(template) is list
        and all(type(x) is str for x in template)
        and type(assets) is dict
        and assets
        and all(is_sha(h) for h in assets.values()),
        "visual_runtime_declarations",
    )
    for flag, expected in {
        "--image-min-tokens": "225",
        "--image-max-tokens": "225",
        "--threads": "4",
        "--threads-batch": "4",
        "--seed": "42",
        "--temp": "0",
        "--n-predict": "64",
        "--ctx-size": "3072",
    }.items():
        require(
            template.count(flag) == 1 and template[template.index(flag) + 1] == expected,
            "visual_runtime_flag_changed",
        )
    if value["data_kind"] == "observed":
        require(os.access(template[0], os.X_OK), "visual_runtime_not_executable")
        require(value["geometry_proof_sha256"] == geometry_proof(), "visual_geometry_proof_changed")
        require(
            {Path(n).name: h for n, h in assets.items()}
            == proposal["candidate"]["asset_sha256_by_basename"],
            "visual_native_assets_changed",
        )
        original = read_json(ROOT / "data/private/issue-4-vlm-native225-release-v2/plan.json")
        require(
            original["plan_sha256"]
            == "7fab9a3bc0098d6c828f600b6eb99d25ba8e0ce6b44b8989ac5741b850890bf5"
            and capture.owner.digest({k: v for k, v in original.items() if k != "plan_sha256"})
            == original["plan_sha256"],
            "visual_native_reference_changed",
        )
        require(
            template == original["argv_template"] and assets == original["asset_sha256"],
            "visual_native_template_changed",
        )
        require(
            all(
                value["asset_references"][n][k] == reference[k]
                for n, reference in original["asset_references"].items()
                for k in ("target", "link")
            ),
            "visual_native_asset_location_changed",
        )
        control_path = ROOT / "data/private/issue-4-vlm-v16-v2/plan.json"
        require(
            sha(control_path) == CONTROL_PLAN_FILE_SHA256, "visual_original_control_plan_changed"
        )
        controls = read_json(control_path)["base"]["cases"]["negative"]
        controls = {row["sample_id"]: row["png_sha256"] for row in controls}
        require(len(controls) == 12, "visual_original_control_count")
        if stage == "development":
            require(
                all(j["input_png_sha256"] == controls[j["alias"]] for j in jobs[:12]),
                "visual_original_control_image_changed",
            )
    return value


def verify_authority(configuration, authorization, review, root, now):
    auth_fields = {
        "schema",
        "decision",
        "proposal_sha256",
        "source_message_id",
        "max_model_calls",
        "max_acquisitions",
        "max_global_seconds",
        "max_cost_brl",
        "retry_allowed",
        "issued_epoch",
        "use_until_epoch",
        "renew_native_positive_once",
        "source_thread_id",
        "source_message_sha256",
        "positive_renewal_message_id",
    }
    review_fields = {
        "schema",
        "decision",
        "proposal_sha256",
        "authorization_sha256",
        "configuration_sha256",
        "execution_root_sha256",
        "stage",
        "source_message_id",
        "external_80_second_watchdog_verified",
        "geometry_proof_sha256",
        "annotation_commitment_sha256",
        "exclusions_independently_verified",
        "annotation_origin_independently_verified",
        "development_independently_reviewed",
        "human_origin_independently_verified",
        "reviewer_thread_id",
        "source_message_sha256",
    }
    require(
        type(authorization) is dict
        and not (set(authorization) - auth_fields)
        and type(review) is dict
        and not (set(review) - review_fields),
        "visual_authority_metadata_only",
    )
    require(
        type(authorization) is dict
        and authorization.get("schema") == "visual-validation-authorization-v1"
        and authorization.get("decision") == "authorize_bounded_visual_validation"
        and authorization.get("proposal_sha256") == PROPOSAL_SHA256
        and type(authorization.get("source_message_id")) is str
        and authorization["source_message_id"]
        and authorization.get("max_model_calls") == 397
        and authorization.get("max_acquisitions") == 32
        and authorization.get("max_global_seconds") == 39600
        and type(authorization.get("max_cost_brl")) in (int, float)
        and authorization["max_cost_brl"] == 0
        and authorization.get("retry_allowed") is False,
        "visual_batch_authorization_required",
    )
    issued, expires = authorization.get("issued_epoch"), authorization.get("use_until_epoch")
    require(
        type(issued) in (int, float)
        and type(expires) in (int, float)
        and math.isfinite(issued)
        and math.isfinite(expires)
        and issued <= now < expires <= issued + 39600,
        "visual_authorization_expired",
    )
    require(
        type(review) is dict
        and review.get("decision") == "approved_visual_validation_stage"
        and review.get("proposal_sha256") == PROPOSAL_SHA256
        and review.get("authorization_sha256") == digest(authorization)
        and review.get("configuration_sha256") == configuration["configuration_sha256"]
        and review.get("execution_root_sha256") == root_digest(root)
        and review.get("stage") == configuration["stage"]
        and review.get("geometry_proof_sha256") == configuration["geometry_proof_sha256"]
        and review.get("external_80_second_watchdog_verified") is True
        and type(review.get("source_message_id")) is str
        and review["source_message_id"]
        and review["source_message_id"] != authorization["source_message_id"],
        "visual_batch_technical_review_required",
    )
    require(
        configuration["stage"] != "development"
        or authorization.get("renew_native_positive_once") is True,
        "visual_positive_use_renewal_required",
    )


def initial_state(authorization, root, now, data_kind):
    return {
        "schema": "visual-validation-global-ledger-v1",
        "proposal_sha256": PROPOSAL_SHA256,
        "authorization_sha256": digest(authorization),
        "execution_root_sha256": root_digest(root),
        "data_kind": data_kind,
        "started_epoch": now,
        "calls_reserved": 0,
        "acquisitions_reserved": 0,
        "development_calls": 0,
        "audit_calls": 0,
        "charged_seconds": 0.0,
        "pending": None,
        "sealed": False,
        "development_passed": False,
        "phase_configurations": {},
        "operations": [],
    }


def reserve_event(state, kind, operation_id, now):
    """Durable caller must persist the returned state before any external effect."""
    require(
        state["sealed"] is False and state["pending"] is None, "visual_global_sealed_or_uncertain"
    )
    require(
        now >= state["started_epoch"] and now - state["started_epoch"] < 39600,
        "visual_global_deadline",
    )
    require(kind in ("development", "audit", "acquisition"), "visual_operation_kind")
    require(identifier(operation_id), "visual_operation_identity")
    limit = 180 if kind == "acquisition" else 80
    require(state["charged_seconds"] + limit <= 39600, "visual_global_reserved_time_exhausted")
    require(
        not any(o["operation_id"] == operation_id for o in state["operations"]),
        "visual_operation_already_consumed",
    )
    if kind == "acquisition":
        require(
            state["development_passed"] and state["acquisitions_reserved"] < 32,
            "visual_acquisition_budget_or_stage",
        )
        state["acquisitions_reserved"] += 1
    else:
        require(state["calls_reserved"] < 397, "visual_model_budget_exhausted")
        key, cap = ("development_calls", 13) if kind == "development" else ("audit_calls", 384)
        require(
            state[key] < cap and (kind == "development" or state["development_passed"]),
            "visual_stage_budget_or_gate",
        )
        state[key] += 1
        state["calls_reserved"] += 1
    entry = {
        "operation_id": operation_id,
        "kind": kind,
        "status": "running",
        "reserved_seconds": limit,
        "started_epoch": now,
    }
    state["charged_seconds"] += limit
    state["pending"] = operation_id
    state["operations"].append(entry)
    state["charged_seconds"] = sum(
        o.get("seconds", o["reserved_seconds"]) for o in state["operations"]
    )
    return entry


def validate_state(state):
    require(
        state.get("schema") == "visual-validation-global-ledger-v1"
        and state.get("proposal_sha256") == PROPOSAL_SHA256
        and type(state.get("sealed")) is bool
        and type(state.get("development_passed")) is bool,
        "visual_ledger_shape",
    )
    for key, maximum in (
        ("calls_reserved", 397),
        ("acquisitions_reserved", 32),
        ("development_calls", 13),
        ("audit_calls", 384),
    ):
        require(type(state.get(key)) is int and 0 <= state[key] <= maximum, "visual_ledger_counter")
    require(
        state["calls_reserved"] == state["development_calls"] + state["audit_calls"]
        and type(state.get("operations")) is list
        and len(state["operations"]) == state["calls_reserved"] + state["acquisitions_reserved"],
        "visual_ledger_counter_alignment",
    )
    require(
        all(
            type(state.get(k)) in (int, float) and math.isfinite(state[k]) and state[k] >= 0
            for k in ("started_epoch", "charged_seconds")
        ),
        "visual_ledger_time",
    )
    operations = state["operations"]
    require(
        len({o["operation_id"] for o in operations}) == len(operations),
        "visual_ledger_duplicate_operation",
    )
    require(
        sum(o["kind"] == "development" for o in operations) == state["development_calls"]
        and sum(o["kind"] == "audit" for o in operations) == state["audit_calls"]
        and sum(o["kind"] == "acquisition" for o in operations) == state["acquisitions_reserved"]
        and all(
            o["kind"] in ("development", "audit", "acquisition")
            and o["status"] in ("running", "completed", "failed")
            and type(o["reserved_seconds"]) is int
            and o["reserved_seconds"] == (180 if o["kind"] == "acquisition" else 80)
            for o in operations
        ),
        "visual_ledger_operation_alignment",
    )
    require(
        state["charged_seconds"]
        == sum(o.get("seconds", o["reserved_seconds"]) for o in operations),
        "visual_ledger_charge_changed",
    )
    expected_pass = state["development_calls"] == 13 and all(
        o.get("accepted") is True and o["status"] == "completed"
        for o in operations
        if o["kind"] == "development"
    )
    require(state["development_passed"] == expected_pass, "visual_ledger_development_gate")
    running = [o["operation_id"] for o in operations if o["status"] == "running"]
    require(
        running == ([] if state["pending"] is None else [state["pending"]]),
        "visual_ledger_pending_alignment",
    )
    return state


def finish_event(state, entry, *, seconds, accepted):
    require(
        state["pending"] == entry["operation_id"]
        and entry["status"] == "running"
        and type(seconds) in (int, float)
        and math.isfinite(seconds)
        and seconds >= 0,
        "visual_global_terminal_mismatch",
    )
    accepted = accepted is True and seconds <= entry["reserved_seconds"]
    entry.update(status="completed" if accepted else "failed", seconds=seconds, accepted=accepted)
    state["charged_seconds"] = sum(
        o.get("seconds", o["reserved_seconds"]) for o in state["operations"]
    )
    state["pending"] = None
    if not accepted:
        state["sealed"] = True
    if entry["kind"] == "development" and state["development_calls"] == 13 and accepted:
        state["development_passed"] = True
    if state["calls_reserved"] == 397:
        state["sealed"] = True
    return accepted


def verify_annotation_commitment(configuration, review, committed):
    commitment(committed, "commitment_sha256")
    require(
        committed.get("schema") == "visual-blind-annotation-commitment-v1"
        and committed.get("execution_authorized") is False
        and is_sha(committed.get("annotations_file_sha256"))
        and is_sha(committed.get("annotations_content_sha256"))
        and committed["selection_sha256"] == configuration["selection"]["selection_sha256"]
        and committed.get("sample_count") == 32
        and review.get("annotation_commitment_sha256") == committed["commitment_sha256"]
        and review.get("exclusions_independently_verified") is True
        and review.get("annotation_origin_independently_verified") is True
        and review.get("development_independently_reviewed") is True,
        "visual_blind_commitment_or_review_required",
    )
    require(
        committed["declared_origin"] in ("human", "assisted"),
        "visual_synthetic_annotations_refused",
    )
    if committed["annotation_requirement"] == "human_required":
        require(
            committed["declared_origin"] == "human"
            and review.get("human_origin_independently_verified") is True,
            "visual_human_annotations_required",
        )


@dataclass
class Services:
    launch: object
    preflight: object
    available_memory: object
    workers: object
    now: object = time.time
    clock: object = time.monotonic
    synthetic_only: bool = False


def _runtime_assets(configuration, services, deadline):
    result = {}
    for name, expected in configuration["assets"].items():
        path = Path(name)
        reference = native._asset_reference(path)
        require(
            reference == configuration["asset_references"][name],
            "visual_runtime_asset_link_changed",
        )
        target = Path(reference["target"])
        before = native._fingerprint(target)
        checksum = hashlib.sha256()
        fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            require(
                (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
                == before,
                "visual_runtime_open_identity_changed",
            )
            while block := stream.read(2**20):
                require(
                    services.clock() < deadline and services.available_memory() >= 6 * 1024**3,
                    "visual_preflight_time_or_memory",
                )
                checksum.update(block)
        require(
            checksum.hexdigest() == expected
            and native._fingerprint(target) == before
            and native._asset_reference(path) == reference,
            "visual_runtime_asset_changed",
        )
        result[name] = {"reference": reference, "fingerprint": before}
    return result


def _image(job, stage):
    path = plain(job["input_path"])
    require(path.suffix.lower() == ".png", "visual_png_input_required")
    before = native._fingerprint(path)
    require(path.stat().st_size <= 32 * 1024**2, "visual_input_size")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        require(
            (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns) == before,
            "visual_input_open_identity_changed",
        )
        raw = stream.read(32 * 1024**2 + 1)
    require(
        len(raw) <= 32 * 1024**2 and hashlib.sha256(raw).hexdigest() == job["input_png_sha256"],
        "visual_input_identity_changed",
    )
    with Image.open(io.BytesIO(raw)) as picture:
        shape = (360, 640) if stage == "development" and job["kind"] == "relation" else (320, 330)
        require(
            picture.format == "PNG" and picture.mode == "RGB" and picture.size == shape,
            "visual_input_geometry_changed",
        )
        picture.verify()
    require(native._fingerprint(path) == before, "visual_input_changed_during_preflight")
    return before


def _query(proposal, kind):
    if kind == "relation":
        return {
            "prompt": proposal["development"]["positive_question"],
            "schema": {
                "type": "object",
                "properties": {"answer": {"enum": ["yes", "no", "uncertain"]}},
                "required": ["answer"],
                "additionalProperties": False,
            },
        }
    return (
        proposal["candidate"]["product"]["specification"]
        if kind == "product_visible_early"
        else proposal["candidate"]["person" if kind == "person_visible" else "text"]
    )


def _persist(path, value, *, exclusive=False):
    plain(path)
    if exclusive:
        write_new(path, value)
    else:
        capture.owner.write(path, value)


def write_runtime_schema(path, schema):
    """Schema property order is part of the frozen candidate; metadata sorting is unsafe."""
    path = plain(path)
    raw = json.dumps(schema, ensure_ascii=False, allow_nan=False).encode() + b"\n"
    require(
        len(raw) <= 2**20 and stat.S_IMODE(path.parent.stat().st_mode) & 0o077 == 0,
        "visual_private_schema_required",
    )
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def _dispatch(configuration, call_id, root, services):
    root = plain(root)
    validate_configuration(configuration, root, allow_synthetic=services.synthetic_only)
    require(
        (configuration["data_kind"] == "synthetic") == services.synthetic_only,
        "visual_execution_kind_mismatch",
    )
    folder = root / "data/private" / NAMESPACE
    authorization = read_json(folder / "authorization.json")
    review = read_json(folder / f"review-{configuration['stage']}.json")
    verify_authority(configuration, authorization, review, root, services.now())
    jobs = {j["call_id"]: j for j in configuration["jobs"]}
    require(type(call_id) is int and call_id in jobs, "visual_unplanned_call")
    job = jobs[call_id]
    require(
        services.now() < job["use_until_epoch"] <= authorization["use_until_epoch"],
        "visual_input_use_expired",
    )
    require(
        services.available_memory() >= 6 * 1024**3 and not services.workers(),
        "visual_memory_or_concurrent_worker",
    )
    if configuration["stage"] == "audit":
        # The private GT file is deliberately never opened by this controller.
        verify_annotation_commitment(
            configuration, review, read_json(folder / "annotation-commitment.json")
        )
    lock_fd = os.open(
        plain(folder / ".controller.lock"), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(lock_fd, "r+") as lock:
        info = os.fstat(lock.fileno())
        require(
            stat.S_ISREG(info.st_mode)
            and info.st_nlink == 1
            and info.st_uid == os.getuid()
            and not stat.S_IMODE(info.st_mode) & 0o077,
            "visual_private_lock_required",
        )
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        started = services.clock()
        state_path = folder / "global-ledger.json"
        state = (
            read_json(state_path)
            if state_path.exists()
            else initial_state(authorization, root, services.now(), configuration["data_kind"])
        )
        validate_state(state)
        require(
            state["authorization_sha256"] == digest(authorization)
            and state["execution_root_sha256"] == root_digest(root)
            and state["data_kind"] == configuration["data_kind"],
            "visual_global_lineage_changed",
        )
        require(
            state["sealed"] is False and state["pending"] is None,
            "visual_global_sealed_or_uncertain",
        )
        require(
            call_id == state["calls_reserved"] + 1, "visual_call_already_consumed_or_out_of_order"
        )
        slot = folder / "captures" / f"call-{call_id:04d}"
        require(not slot.exists(), "visual_uncertain_capture_marker")
        previous = state["phase_configurations"].get(configuration["stage"])
        require(
            previous is None or previous == configuration["configuration_sha256"],
            "visual_phase_configuration_changed",
        )
        services.preflight()
        asset_identities = _runtime_assets(configuration, services, started + 20)
        image_identity = _image(job, configuration["stage"])
        require(
            services.available_memory() >= 6 * 1024**3
            and not services.workers()
            and services.now() < job["use_until_epoch"],
            "visual_pre_spawn_guard",
        )
        require(services.now() - state["started_epoch"] < 39600, "visual_global_deadline")
        if not state_path.exists():
            _persist(state_path, state, exclusive=True)
        configuration_path = folder / f"configuration-{configuration['stage']}.json"
        if configuration_path.exists():
            require(
                read_json(configuration_path) == configuration, "visual_saved_configuration_changed"
            )
        else:
            write_new(configuration_path, configuration)
        state["phase_configurations"][configuration["stage"]] = configuration[
            "configuration_sha256"
        ]
        query = _query(load_proposal(), job["kind"])
        scratch = folder / "scratch" / f"call-{call_id:04d}"
        scratch.mkdir(parents=True, mode=0o700, exist_ok=False)
        write_runtime_schema(scratch / "schema.json", query["schema"])
        argv = list(configuration["runtime_template"])
        for flag, value in (
            ("--image", job["input_path"]),
            ("--json-schema-file", str(scratch / "schema.json")),
            ("--prompt", query["prompt"]),
        ):
            require(argv.count(flag) == 1, "visual_runtime_placeholder")
            argv[argv.index(flag) + 1] = value
        entry = result = None

        def verify_binding():
            require(
                read_json(folder / "authorization.json") == authorization
                and read_json(folder / f"review-{configuration['stage']}.json") == review
                and source_hashes() == configuration["source_files_sha256"],
                "visual_receipt_or_source_changed",
            )
            for name, identity in asset_identities.items():
                require(
                    native._asset_reference(Path(name)) == identity["reference"]
                    and native._fingerprint(identity["reference"]["target"])
                    == identity["fingerprint"],
                    "visual_asset_changed_before_spawn",
                )
            require(
                native._fingerprint(job["input_path"]) == image_identity,
                "visual_input_changed_before_spawn",
            )

        def reserve():
            nonlocal entry
            verify_binding()
            require(
                services.available_memory() >= 6 * 1024**3
                and services.now() < min(job["use_until_epoch"], authorization["use_until_epoch"]),
                "visual_memory_or_use_before_reservation",
            )
            entry = reserve_event(state, configuration["stage"], f"model-{call_id}", services.now())
            _persist(state_path, state)

        def launch(*args, **kwargs):
            verify_binding()
            require(
                args == (argv,)
                and entry is not None
                and services.available_memory() >= 6 * 1024**3
                and services.now() < min(job["use_until_epoch"], authorization["use_until_epoch"]),
                "visual_reviewed_spawn_only",
            )
            return _DeadlineProcess(services.launch(*args, **kwargs), started + 75)

        try:
            useful = min(
                75,
                started + 75 - services.clock(),
                authorization["use_until_epoch"] - services.now() - 5,
                job["use_until_epoch"] - services.now() - 5,
                39600 - (services.now() - state["started_epoch"]) - 5,
            )
            require(useful > 0, "visual_dispatch_window_exhausted")
            result = capture._capture_invented(
                argv,
                root=root,
                call_id=call_id,
                kind=job["kind"],
                png_sha256=job["input_png_sha256"],
                expected_tokens=job["expected_tokens"],
                reserve=reserve,
                launcher=launch,
                seconds=useful,
            )
            accepted = result["technical_success"]
            if configuration["stage"] == "development":
                response = result["parsed_response"]
                accepted = accepted and (
                    response["answer"] == "yes"
                    if job["kind"] == "relation"
                    else response["value"] is False
                )
            accepted = finish_event(
                state, entry, seconds=services.clock() - started, accepted=accepted
            )
            bound = capture.read_capture(
                root,
                call_id,
                kind=job["kind"],
                png_sha256=job["input_png_sha256"],
                expected_tokens=job["expected_tokens"],
            )
            receipt = {
                "schema": "visual-validation-dispatch-receipt-v1",
                "proposal_sha256": PROPOSAL_SHA256,
                "data_kind": configuration["data_kind"],
                "configuration_sha256": configuration["configuration_sha256"],
                "authorization_sha256": digest(authorization),
                "review_sha256": digest(review),
                "call_id": call_id,
                "stage": configuration["stage"],
                "alias": job["alias"],
                "frame_index": job["frame_index"],
                "kind": job["kind"],
                "input_png_sha256": job["input_png_sha256"],
                "expected_tokens": job["expected_tokens"],
                "job_sha256": digest(job),
                "capture_result_sha256": bound["result_sha256"],
                "accepted": accepted,
                "native_execution_verified": configuration["data_kind"] == "observed"
                and result["process_started"] is True,
                "technical_success": result["technical_success"],
                "dispatch_seconds": services.clock() - started,
                "cleanup_confirmed": result["cleanup_confirmed"],
            }
            write_new(folder / "receipts" / f"call-{call_id:04d}.json", receipt)
            entry["receipt_sha256"] = digest(receipt)
            if configuration["stage"] == "audit" and call_id == max(jobs):
                state["sealed"] = True
            _persist(state_path, state)
            return receipt
        except BaseException:
            state["sealed"] = True
            if entry is not None and entry["status"] != "running":
                entry.update(status="failed", accepted=False)
                if entry["kind"] == "development":
                    state["development_passed"] = False
            _persist(state_path, state)
            raise
        finally:
            if result is not None and result["cleanup_confirmed"]:
                shutil.rmtree(scratch)


def dispatch_one(configuration, call_id, *, root=ROOT):
    require(NATIVE_DISPATCH_RELEASED, "visual_native_batch_not_released")
    require(
        plain(root) == ROOT and configuration["data_kind"] == "observed",
        "visual_native_root_or_scope",
    )
    services = Services(
        subprocess.Popen, native.capsule_preflight, native.available_memory, capture.owner.workers
    )
    return _dispatch(configuration, call_id, root, services)


def _dispatch_invented(configuration, call_id, *, root, services):
    require(
        services.synthetic_only is True and configuration["data_kind"] == "synthetic",
        "visual_invented_test_seam_only",
    )
    return _dispatch(configuration, call_id, root, services)


def inspect_state(root=ROOT):
    path = plain(root) / "data/private" / NAMESPACE / "global-ledger.json"
    if not path.exists():
        return {
            "status": "inactive",
            "calls_reserved": 0,
            "acquisitions_reserved": 0,
            "native_dispatch_released": NATIVE_DISPATCH_RELEASED,
        }
    state = validate_state(read_json(path))
    markers = list((path.parent / "captures").glob("call-*"))
    unaccounted = max(0, len(markers) - state["calls_reserved"])
    return {
        "status": "uncertain"
        if unaccounted
        else "sealed"
        if state["sealed"]
        else "uncertain"
        if state["pending"]
        else "idle",
        "calls_reserved": state["calls_reserved"],
        "acquisitions_reserved": state["acquisitions_reserved"],
        "pending": state["pending"],
        "charged_seconds": state["charged_seconds"],
        "unaccounted_capture_markers": unaccounted,
        "new_execution_performed": False,
    }


def read_dispatch_receipt(root, call_id):
    folder = plain(root) / "data/private" / NAMESPACE
    state = validate_state(read_json(folder / "global-ledger.json"))
    entries = [o for o in state["operations"] if o["operation_id"] == f"model-{call_id}"]
    require(
        len(entries) == 1
        and entries[0]["status"] == "completed"
        and entries[0].get("accepted") is True,
        "visual_accepted_dispatch_required",
    )
    receipt = read_json(folder / "receipts" / f"call-{call_id:04d}.json")
    require(
        digest(receipt) == entries[0].get("receipt_sha256")
        and receipt["authorization_sha256"] == state["authorization_sha256"]
        and receipt["data_kind"] == state["data_kind"]
        and receipt["accepted"] is True
        and receipt["call_id"] == call_id
        and receipt["dispatch_seconds"] <= 80,
        "visual_dispatch_receipt_changed",
    )
    configuration = read_json(folder / f"configuration-{receipt['stage']}.json")
    commitment(configuration, "configuration_sha256")
    authorization = read_json(folder / "authorization.json")
    review = read_json(folder / f"review-{receipt['stage']}.json")
    jobs = {j["call_id"]: j for j in configuration["jobs"]}
    require(
        configuration["configuration_sha256"] == receipt["configuration_sha256"]
        and digest(authorization) == receipt["authorization_sha256"]
        and digest(review) == receipt["review_sha256"]
        and configuration["execution_root_sha256"] == root_digest(root)
        and digest(jobs[call_id]) == receipt["job_sha256"],
        "visual_dispatch_lineage_changed",
    )
    bound = capture.read_capture(
        root,
        call_id,
        kind=receipt["kind"],
        png_sha256=receipt["input_png_sha256"],
        expected_tokens=receipt["expected_tokens"],
    )
    require(
        bound["result_sha256"] == receipt["capture_result_sha256"],
        "visual_dispatch_capture_changed",
    )
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--configuration", type=Path)
    parser.add_argument("--call-id", type=int)
    args = parser.parse_args(argv)
    try:
        if args.inspect:
            print(__import__("json").dumps(inspect_state()))
            return 0
        require(NATIVE_DISPATCH_RELEASED, "visual_native_batch_not_released")
        require(
            args.configuration is not None and args.call_id is not None,
            "visual_configuration_and_call_required",
        )
        require(
            plain(args.configuration)
            in {
                ROOT / "data/private" / NAMESPACE / "configuration-development.json",
                ROOT / "data/private" / NAMESPACE / "configuration-audit.json",
            },
            "visual_cli_configuration_not_allowlisted",
        )
        result = dispatch_one(read_json(args.configuration), args.call_id)
        print(
            __import__("json").dumps(
                {
                    k: result[k]
                    for k in ("call_id", "accepted", "technical_success", "cleanup_confirmed")
                }
            )
        )
        return 0 if result["accepted"] else 2
    except (ValueError, OSError, KeyError):
        print('{"status":"blocked_or_failed","retry_allowed":false,"inspect_execution_state":true}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

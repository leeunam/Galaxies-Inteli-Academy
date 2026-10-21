"""Operator-only recovery policy. Standard library only; no media/model imports."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE_PLAN_SHA256 = "f61bcf849d2f61b701c00ef447486494d302a86029c5f14e8f11547ed1377f80"
CODE_FILES = (
    "scripts/demo_recovery_policy.py",
    "scripts/demo_recovery_process.py",
    "scripts/demo_recovery_child.py",
    "scripts/demo_recovery_native.py",
    "scripts/demo_recovery.py",
)
MAXIMUMS = {
    "per_acquisition_seconds": 180,
    "acquisition_seconds": 600,
    "analysis_seconds": 480,
    "overall_seconds": 1800,
    "file_bytes": 32 * 1024**2,
    "workspace_bytes": 384 * 1024**2,
    "rss_bytes": 3584 * 1024**2,
    "io_bytes": 65536,
    "minimum_free_bytes": 1024**3,
    "remux_seconds": 45,
    "extractor_threads": 4,
}


class RecoveryError(Exception):
    """Only constant local reason codes may cross the CLI boundary."""


def digest(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise RecoveryError("duplicate_json_key")
        result[key] = value
    return result


def read_json(path, *, limit=262144):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as handle:
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise RecoveryError("invalid_operator_file")
        raw = handle.read(limit + 1)
    if len(raw) > limit:
        raise RecoveryError("operator_input_limit")
    return json.loads(raw, object_pairs_hook=unique_pairs)


def private_path(path, *, root=ROOT):
    value = Path(path).absolute()
    allowed = (Path(root) / "data/private").resolve()
    if not value.resolve().is_relative_to(allowed):
        raise RecoveryError("private_path_required")
    current = value
    while current != allowed:
        if current.is_symlink():
            raise RecoveryError("private_symlink_forbidden")
        current = current.parent
    return value


def fsync_dir(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def exclusive_json(path, value):
    path = Path(path)
    encoded = json.dumps(value, allow_nan=False, ensure_ascii=True).encode() + b"\n"
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    except OSError:
        raise RecoveryError("exclusive_receipt_consumed") from None
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    fsync_dir(path.parent)


def reserve_phase(folder, phase, plan_sha):
    if phase not in {"acquire", "analyze", "handoff", "discard"}:
        raise RecoveryError("invalid_phase")
    exclusive_json(
        Path(folder) / (phase + "-started.json"),
        {
            "phase": phase,
            "state": "consumed_before_operation",
            "plan_sha256": plan_sha,
        },
    )


def validate_proposal(plan, base, *, expected_base_sha=BASE_PLAN_SHA256):
    expected_keys = {
        "protocol",
        "base_plan_sha256",
        "sources",
        "format_policy",
        "input_retention_until",
        "budgets",
    }
    if (
        type(plan) is not dict
        or set(plan) != expected_keys
        or plan["protocol"] != "demo-recovery-v3"
        or plan["base_plan_sha256"] != expected_base_sha
        or plan["format_policy"] not in {"single_file", "single_or_copy_remux"}
    ):
        raise RecoveryError("invalid_recovery_proposal")
    sources = plan["sources"]
    original = base["sources"]
    if type(sources) is not list or len(sources) != 3 or len(original) != 3:
        raise RecoveryError("fixed_trio_required")
    identities = []
    for source, authority in zip(sources, original, strict=True):
        if type(source) is not dict or set(source) != {"alias", "video_id", "source_url"}:
            raise RecoveryError("invalid_source_fields")
        if any(source[key] != authority[key] for key in source):
            raise RecoveryError("fixed_source_changed")
        if source["alias"] not in {"demo_a", "demo_b", "demo_c"} or not re.fullmatch(
            r"[A-Za-z0-9_-]{11}", source["video_id"]
        ):
            raise RecoveryError("invalid_source_identity")
        if source["source_url"] != "https://www.youtube.com/watch?v=" + source["video_id"]:
            raise RecoveryError("invalid_source_identity")
        identities.append(source["video_id"])
    if len(set(identities)) != 3 or len({row["alias"] for row in sources}) != 3:
        raise RecoveryError("distinct_fixed_sources_required")
    budgets = plan["budgets"]
    if type(budgets) is not dict or set(budgets) != set(MAXIMUMS):
        raise RecoveryError("invalid_budgets")
    for key, maximum in MAXIMUMS.items():
        if type(budgets[key]) is not int or not 0 < budgets[key] <= maximum:
            raise RecoveryError("invalid_budgets")
    # This is a floor; reducing it would silently weaken the disk guard.
    if budgets["minimum_free_bytes"] != MAXIMUMS["minimum_free_bytes"]:
        raise RecoveryError("invalid_disk_floor")
    if budgets["extractor_threads"] != 4:
        raise RecoveryError("frozen_extractor_has_four_threads")
    expires = datetime.fromisoformat(plan["input_retention_until"])
    if expires.tzinfo is None:
        raise RecoveryError("timezone_required")
    return plan


def validate_release(release, plan, plan_sha, code_pins, phase):
    keys = {
        "protocol",
        "plan_sha256",
        "code_sha256",
        "phases",
        "input_retention_until",
        "format_policy",
        "offline_checks_receipt",
        "technical_review_reference",
    }
    if (
        type(release) is not dict
        or set(release) != keys
        or release["protocol"] != "demo-recovery-technical-release-v1"
        or release["plan_sha256"] != plan_sha
        or release["code_sha256"] != code_pins
        or type(release["phases"]) is not list
        or phase not in release["phases"]
        or set(release["phases"]) - {"acquire", "analyze", "handoff", "discard"}
        or release["input_retention_until"] != plan["input_retention_until"]
        or release["format_policy"] != plan["format_policy"]
        or not isinstance(release["offline_checks_receipt"], str)
        or not release["offline_checks_receipt"].strip()
        or not isinstance(release["technical_review_reference"], str)
        or not release["technical_review_reference"].strip()
    ):
        raise RecoveryError("release_mismatch")


def load_operator_plan(plan_file, base_file, release_file=None, phase="inspect"):
    plan_file, base_file = private_path(plan_file), private_path(base_file)
    if digest(base_file) != BASE_PLAN_SHA256:
        raise RecoveryError("base_plan_seal_mismatch")
    base = read_json(base_file)
    plan = validate_proposal(read_json(plan_file), base)
    if Path(base["clone_root"]).resolve() != ROOT:
        raise RecoveryError("wrong_checkout")
    source_root = Path(base["source_root"])
    if phase not in {"handoff", "discard"}:
        for name, expected in base["public_source_files_sha256"].items():
            # Later source/doc edits cannot prevent cleanup of owned inputs.
            target = source_root / name
            if (
                not target.resolve().is_relative_to(source_root.resolve())
                or digest(target) != expected
            ):
                raise RecoveryError("source_pin_changed")
    plan_sha = digest(plan_file)
    code_pins = {name: digest(ROOT / name) for name in CODE_FILES}
    if phase != "inspect":
        if release_file is None:
            raise RecoveryError("technical_release_required")
        validate_release(read_json(private_path(release_file)), plan, plan_sha, code_pins, phase)
    return plan, base, plan_sha, code_pins


def discard_allowed(*, handoff_recorded, demo_completed, now, expires):
    return now >= expires or (handoff_recorded and demo_completed)

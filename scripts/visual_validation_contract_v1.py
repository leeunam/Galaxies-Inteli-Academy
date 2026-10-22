"""Metadata-only contracts for the inactive front1 proposal; no model loader."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import stat
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL = "docs/evidence/issue-4-native225-next-validation-v1.json"
PROPOSAL_SHA256 = "dd5f48cb4f91c4eb875352c0b2802ffeb186a02682b3a3d4705cb33eddffc247"
FIELDS = ("person_visible", "product_visible_early", "screen_text")
MAX_JSON = 2**20


def digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        ).encode()
    ).hexdigest()


def require(value, code):
    if not value:
        raise ValueError(code)


def is_sha(value):
    return type(value) is str and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def identifier(value):
    return type(value) is str and re.fullmatch(r"[A-Za-z0-9_-]{1,160}", value) is not None


def plain(path):
    path = Path(path).absolute()
    require(
        ".." not in path.parts and not any(p.is_symlink() for p in (path, *path.parents)),
        "visual_path_rejected",
    )
    return path


def strict_json(raw):
    def pairs(values):
        result = {}
        for key, value in values:
            require(key not in result, "visual_duplicate_key")
            result[key] = value
        return result

    def constant(_):
        raise ValueError("visual_nonfinite_json")

    require(type(raw) in (bytes, str) and len(raw) <= MAX_JSON, "visual_json_limit")
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)


def read_json(path):
    path = plain(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "visual_regular_file_required")
        return strict_json(stream.read(MAX_JSON + 1))


def write_new(path, value):
    """Exclusive private metadata only; never overwrites or writes an approval."""
    path = plain(path)
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode() + b"\n"
    require(len(raw) <= MAX_JSON, "visual_json_limit")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    require(stat.S_IMODE(path.parent.stat().st_mode) & 0o077 == 0, "visual_private_parent_required")
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
    return hashlib.sha256(raw).hexdigest()


def load_proposal(root=ROOT):
    value = read_json(Path(root) / PROPOSAL)
    body = {k: v for k, v in value.items() if k != "plan_sha256"}
    require(value.get("plan_sha256") == digest(body) == PROPOSAL_SHA256, "visual_proposal_changed")
    require(
        value["limits"]["new_model_calls_max"] == 397
        and value["limits"]["global_seconds"] == 39600
        and value["authorization_received"] is False,
        "visual_inactive_proposal_required",
    )
    return value


def timeline(seconds, hashes):
    require(
        type(seconds) is list and type(hashes) is list and 1 <= len(seconds) == len(hashes) <= 4,
        "visual_frame_count",
    )
    require(
        all(type(s) in (int, float) and math.isfinite(s) and s >= 0 for s in seconds)
        and seconds == sorted(set(seconds))
        and all(is_sha(h) for h in hashes),
        "visual_frame_identity",
    )


def commitment(value, key):
    body = {k: v for k, v in value.items() if k != key}
    require(value.get(key) == digest(body), "visual_commitment_changed")
    return body

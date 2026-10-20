"""New consumption namespace only. Existence means consumed, including crashes."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from scripts.nim_dispatch_plan_v3 import canonical


def sync_directory(path):
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def create(path, value):
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        output.write(canonical(value) + b"\n")
        output.flush()
        os.fsync(output.fileno())
    sync_directory(path.parent)


def ensure_directory(path):
    if path.is_symlink():
        raise ValueError("v3_symlink_directory_forbidden")
    if path.is_dir():
        return
    ensure_directory(path.parent)
    try:
        path.mkdir(mode=0o700)
    except FileExistsError:
        if path.is_symlink() or not path.is_dir():
            raise ValueError("v3_invalid_directory") from None
    sync_directory(path.parent)


def reserve(folder, plan_sha256, *, offline):
    folder = Path(folder).absolute()
    if any("nim-sintetico-unico" in part for part in folder.parts):
        raise ValueError("v3_old_ledger_forbidden")
    if any(parent.is_symlink() for parent in folder.parents):
        raise ValueError("v3_symlink_directory_forbidden")
    ensure_directory(folder.parent)
    folder.mkdir(mode=0o700, exist_ok=False)
    sync_directory(folder.parent)
    nonce = os.urandom(32)
    create(
        folder / "reservation-v3.json",
        {
            "protocol": "nim-fixed-public-dispatch-v3",
            "state": "consumed_before_child_start",
            "plan_sha256": plan_sha256,
            "parent_pid": os.getpid(),
            "nonce_sha256": hashlib.sha256(nonce).hexdigest(),
            "offline_simulation_only": offline,
            "retry_allowed": False,
        },
    )
    return folder, nonce


def authorize(folder, nonce, plan_sha256, *, offline):
    folder = Path(folder)
    path = folder / "reservation-v3.json"
    if path.is_symlink() or path.stat().st_size > 2048:
        raise ValueError("v3_invalid_reservation")
    reservation = json.loads(path.read_bytes())
    expected = {
        "protocol": "nim-fixed-public-dispatch-v3",
        "state": "consumed_before_child_start",
        "plan_sha256": plan_sha256,
        "parent_pid": os.getppid(),
        "nonce_sha256": hashlib.sha256(nonce).hexdigest(),
        "offline_simulation_only": offline,
        "retry_allowed": False,
    }
    if len(nonce) != 32 or reservation != expected or (folder / "result-v3.json").exists():
        raise ValueError("v3_live_parent_required")
    create(
        folder / "dispatch-v3.json",
        {"state": "consumed_before_transport", "offline_simulation_only": offline},
    )

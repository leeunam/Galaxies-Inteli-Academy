"""Small private, atomic checkpoint primitives; no network or model loading."""

from __future__ import annotations

import fcntl
import hashlib
import json
from contextlib import contextmanager
from pathlib import Path

from scripts.pilot_licensed_media import ROOT, atomic_json


def private_path(path: Path, root: Path = ROOT, *, raw: bool = False) -> Path:
    path = path.resolve()
    areas = [root / "data/private"] + ([root / "data/raw"] if raw else [])
    if not any(path.is_relative_to(area.resolve()) and path != area.resolve() for area in areas):
        raise ValueError("Path must be inside ignored private storage")
    return path


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def file_hash(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def save(path: Path, state: dict) -> None:
    atomic_json(path, state)  # NamedTemporaryFile creates mode 0600 before atomic replace.


@contextmanager
def lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as handle:
        path.chmod(0o600)
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Checkpoint already locked by another worker") from None
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)

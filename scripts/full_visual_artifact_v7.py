"""Private, versioned V7 model artifact helpers (synthetic development only)."""

from __future__ import annotations

import hashlib
import json
import os
import stat
from pathlib import Path
from typing import Any

from scripts.channel_partitions import ExperimentError, digest

ARTIFACT_SCHEMA = "front1-bc-v7-artifact-v1"
REPORT_SCHEMA = "front1-bc-v7-report-v1"
MODEL_FILES = ("q10.model", "q50.model", "q90.model")
MAX_JSON = 8 * 1024 * 1024
MAX_MODEL = 128 * 1024 * 1024


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode()


def _private_dir(path: Path) -> None:
    path.mkdir(mode=0o700, parents=False, exist_ok=False)
    os.chmod(path, 0o700)


def _write(path: Path, raw: bytes) -> None:
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def save_bundle(directory: Path, artifact: dict, report: dict, backend, models) -> None:
    directory = Path(directory)
    if directory.exists() or directory.is_symlink():
        raise ExperimentError("v7_model_output_already_exists")
    directory.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    _private_dir(directory)
    # Preserve failed private evidence for diagnosis; never overwrite or silently clean it.
    for filename, model in zip(MODEL_FILES, models, strict=True):
        backend.save_model(algorithm=artifact["algorithm"], model=model, path=directory / filename)
    for filename in MODEL_FILES:
        path = directory / filename
        if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_MODEL:
            raise ExperimentError("v7_model_file_invalid")
        artifact["model_sha256"][filename] = sha(path.read_bytes())
    report_raw = canonical(report)
    _write(directory / "validation-report.json", report_raw)
    artifact["validation_report_sha256"] = sha(report_raw)
    artifact["content_sha256"] = digest(
        {k: v for k, v in artifact.items() if k != "content_sha256"}
    )
    _write(directory / "artifact.json", canonical(artifact))


def _read(path: Path, maximum: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ExperimentError("v7_artifact_file_invalid")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > maximum:
        raise ExperimentError("v7_artifact_file_invalid")
    raw = path.read_bytes()
    if len(raw) != info.st_size:
        raise ExperimentError("v7_artifact_file_changed")
    return raw


def read_bundle(directory: Path) -> tuple[dict, dict, dict[str, bytes]]:
    directory = Path(directory)
    absolute = Path(os.path.abspath(directory))
    if any(part.is_symlink() for part in (absolute, *absolute.parents)) or not directory.is_dir():
        raise ExperimentError("v7_artifact_directory_invalid")
    directory = absolute
    allowed = {"artifact.json", "validation-report.json", *MODEL_FILES}
    try:
        if {item.name for item in directory.iterdir()} != allowed:
            raise ExperimentError("v7_artifact_unexpected_entries")
    except OSError:
        raise ExperimentError("v7_artifact_directory_invalid") from None
    artifact_raw = _read(directory / "artifact.json", MAX_JSON)
    report_raw = _read(directory / "validation-report.json", MAX_JSON)
    try:
        artifact, report = json.loads(artifact_raw), json.loads(report_raw)
    except (ValueError, UnicodeError, RecursionError):
        raise ExperimentError("v7_artifact_json_invalid") from None
    if type(artifact) is not dict or type(report) is not dict:
        raise ExperimentError("v7_artifact_shape_invalid")
    models = {name: _read(directory / name, MAX_MODEL) for name in MODEL_FILES}
    return artifact, report, models

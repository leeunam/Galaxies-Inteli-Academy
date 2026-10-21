"""Invented traces: loss or failed writes cannot produce accepted diagnostics."""

import hashlib
import json
import os

import pytest

from scripts import independent_parity_observer as observer
from scripts.independent_parity_operator import validate_trace


def write_json(path, value):
    path.write_text(json.dumps(value) + "\n")


def start():
    return {
        "kind": "startup",
        "pid": os.getpid(),
        "start_ticks": 1,
        "startup_generation": 0,
        "observation_errors_so_far": 0,
        "orig_argv": ["python", "-B", "invented"],
    }


def bind(monkeypatch, path):
    write_json(path, start())
    fd = os.open(path, os.O_WRONLY | os.O_APPEND)
    for k, v in {
        "TRACE_FD": fd,
        "TRACE_PATH": str(path),
        "TRACE_BYTES": path.stat().st_size,
        "OBSERVATION_ERRORS": 0,
        "SEALED": False,
        "PROCESS_START_TICKS": 1,
        "STARTUP_GENERATION": 0,
    }.items():
        monkeypatch.setattr(observer, k, v, raising=False)
    return fd


@pytest.mark.parametrize("failure", ["limit", "partial", "io_error"])
def test_terminal_rejects_truncation_partial_write_or_io_error(tmp_path, monkeypatch, failure):
    path = tmp_path / "invented-1-0.jsonl"
    fd = bind(monkeypatch, path)
    original_write = os.write

    def broken(descriptor, raw):
        if descriptor == fd:
            if failure == "io_error":
                raise OSError("invented_write_error")
            return original_write(descriptor, raw[:-1])
        return original_write(descriptor, raw)

    if failure == "limit":
        monkeypatch.setattr(observer, "TRACE_BYTES", 512 * 1024)
    else:
        monkeypatch.setattr(os, "write", broken)
    try:
        observer.emit({"kind": "exit"})
        observer.seal_terminal("normal_exit")
    finally:
        os.close(fd)
    footer = json.loads((tmp_path / (path.name + ".terminal.json")).read_text())
    assert footer["observation_errors"] > 0
    with pytest.raises(AssertionError):
        validate_trace(path)


def test_missing_terminal_is_rejected(tmp_path):
    path = tmp_path / "invented-1-0.jsonl"
    write_json(path, start())
    with pytest.raises(FileNotFoundError):
        validate_trace(path)


def test_partial_terminal_is_rejected(tmp_path, monkeypatch):
    path = tmp_path / "invented-1-0.jsonl"
    fd = bind(monkeypatch, path)
    original_write = os.write
    monkeypatch.setattr(os, "write", lambda descriptor, raw: original_write(descriptor, raw[:5]))
    try:
        with pytest.raises(OSError, match="partial_terminal_write"):
            observer.seal_terminal("normal_exit")
    finally:
        os.close(fd)
    with pytest.raises(json.JSONDecodeError):
        validate_trace(path)


def test_exec_requires_verified_completed_successor(tmp_path):
    before, after = tmp_path / "invented-1-0.jsonl", tmp_path / "invented-1-1.jsonl"
    first, second = start(), start()
    second.update(startup_generation=1, orig_argv=["python", "-B", "-m", "invented"])
    first["orig_argv"] = [
        "python",
        "-B",
        "/invented/scripts/demo_recovery_child.py",
        "100",
        *second["orig_argv"],
    ]
    write_json(before, first)
    after.write_text(json.dumps(second) + "\n" + json.dumps({"kind": "exit"}) + "\n")
    for path, header, status in [(before, first, "replaced_by_exec"), (after, second, "completed")]:
        write_json(
            tmp_path / (path.name + ".terminal.json"),
            {
                "status": status,
                "completion_reason": "normal_exit",
                "successor_trace": after.name,
                "observation_errors": 0,
                "trace_bytes": path.stat().st_size,
                "trace_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                **{k: header[k] for k in ("pid", "start_ticks", "startup_generation")},
            },
        )
    assert validate_trace(before) == [first]
    (tmp_path / (after.name + ".terminal.json")).unlink()
    with pytest.raises(FileNotFoundError):
        validate_trace(before)

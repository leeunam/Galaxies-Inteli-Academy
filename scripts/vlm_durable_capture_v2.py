"""Additive private capture journal; native dispatch requires a future released caller.

The frozen collector remains the sole process owner. This module has no execution
CLI and no default native launcher. Prefix checkpoints are never final outcomes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import signal
import stat
import threading
from pathlib import Path

from scripts import explanation_supervisor_v2 as supervisor
from scripts import vlm_short_answer_capture as short

NAMESPACE = "issue-4-vlm-native-contrast-v2"
CELLS = ("negative-D", "negative-N", "positive-N", "positive-D")
STATE_LIMIT = 32768
RESULT_LIMIT = 1048576
DIRECTORY = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def _directory(parent, name, *, create=False):
    if create:
        try:
            os.mkdir(name, 0o700, dir_fd=parent)
            os.fsync(parent)
        except FileExistsError:
            pass
    return os.open(name, DIRECTORY, dir_fd=parent)


def _folder(root, cell, *, create):
    root = Path(root)
    if not root.is_absolute() or ".." in root.parts or "private" in root.parts or cell not in CELLS:
        raise ValueError("capture_path_rejected")
    fd = os.open("/", DIRECTORY)
    try:
        for part in root.parts[1:]:
            child = _directory(fd, part)
            os.close(fd)
            fd = child
        for part in ("data", "private", NAMESPACE, "captures"):
            child = _directory(fd, part, create=create)
            os.close(fd)
            fd = child
            if part in (NAMESPACE, "captures"):
                info = os.fstat(fd)
                if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
                    raise ValueError("capture_directory_not_private")
        if create:
            # This directory is the irreversible no-reentry marker, including
            # crashes before reservation or before the first checkpoint.
            os.mkdir(cell, 0o700, dir_fd=fd)
            os.fsync(fd)
        child = _directory(fd, cell)
        os.close(fd)
        fd = child
        info = os.fstat(fd)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise ValueError("capture_directory_not_private")
        return fd
    except BaseException:
        os.close(fd)
        raise


def _write_all(fd, raw):
    while raw:
        count = os.write(fd, raw)
        if count <= 0:
            raise OSError("capture_short_write")
        raw = raw[count:]


def _atomic(directory, name, body, limit):
    raw = json.dumps(body, sort_keys=True, allow_nan=False).encode() + b"\n"
    if len(raw) > limit:
        raise ValueError("capture_metadata_limit")
    temporary = "." + name + ".pending"
    fd = os.open(
        temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory
    )
    try:
        _write_all(fd, raw)
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temporary, name, src_dir_fd=directory, dst_dir_fd=directory)
    os.fsync(directory)
    return hashlib.sha256(raw).hexdigest()


def _read(directory, name, limit):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit:
            raise ValueError("capture_file_rejected")
        raw = bytearray()
        while chunk := os.read(fd, min(65536, limit + 1 - len(raw))):
            raw.extend(chunk)
            if len(raw) > limit:
                raise ValueError("capture_file_rejected")
        return bytes(raw)
    finally:
        os.close(fd)


class Journal:
    def __init__(self, root, cell):
        self.directory = _folder(root, cell, create=True)
        self.stdout = None
        self.lock = threading.Lock()
        self.failed = threading.Event()
        self.closed = False
        self.stderr = bytearray()
        self.hash = hashlib.sha256()
        self.state = {
            "schema": "vlm-private-capture-v2",
            "phase": "created",
            "terminal": False,
            "cleanup_confirmed": False,
            "stdout_bytes": 0,
            "stdout_sha256": self.hash.hexdigest(),
            "stderr_bytes": 0,
            "stdout_eof": False,
            "stderr_eof": False,
            "progress": {},
        }
        try:
            self.stdout = os.open(
                "stdout.bin",
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=self.directory,
            )
            os.fsync(self.stdout)
            os.fsync(self.directory)
            self.checkpoint()
        except BaseException:
            self.close()
            raise

    def checkpoint(self):
        _atomic(self.directory, "state.json", self.state, STATE_LIMIT)

    def phase(self, name):
        with self.lock:
            self.state["phase"] = name
            self.checkpoint()

    def started(self, process):
        # Reuse the existing process identity reader. No command, environment,
        # input path or model output is placed in the lease.
        lease = {
            "schema": "vlm-owned-process-v2",
            "owner": supervisor.identity(os.getpid()),
            "leader": supervisor.identity(process.pid),
            "pgid": process.pid,
            "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        }
        with self.lock:
            _atomic(self.directory, "process-lease.json", lease, STATE_LIMIT)
            self.state["phase"] = "process_started"
            self.checkpoint()

    def record(self, name, chunk):
        with self.lock:
            if self.closed or self.failed.is_set():
                self.failed.set()
                return
            try:
                cap = short.base.LIMITS[name + "_bytes"]
                if name == "stdout":
                    keep = chunk[: max(0, cap - self.state["stdout_bytes"])]
                    if keep:
                        _write_all(self.stdout, keep)
                        os.fsync(self.stdout)
                        self.hash.update(keep)
                        self.state["stdout_bytes"] += len(keep)
                        self.state["stdout_sha256"] = self.hash.hexdigest()
                else:
                    self.stderr.extend(chunk[: max(0, cap - len(self.stderr))])
                    self.state["stderr_bytes"] = len(self.stderr)
                    # An unfinished log line must not manufacture a stage/token
                    # count. At EOF the frozen parser may also accept its tail.
                    end = len(self.stderr) if not chunk else self.stderr.rfind(b"\n") + 1
                    try:
                        progress = short.base.observations(bytes(self.stderr[:end]))
                        progress["events_truncated"] = len(progress["events"]) > 32
                        progress["events"] = progress["events"][-32:]
                        progress["failures"] = progress["failures"][:16]
                        progress["warnings"] = progress["warnings"][:16]
                        self.state["progress"] = progress
                    except ValueError:
                        self.state["progress"] = {"diagnostic_invalid_integer": True}
                self.state[name + "_eof"] = not chunk
                if chunk:
                    self.state["phase"] = "collecting"
                self.checkpoint()
            except BaseException:  # noqa: BLE001 -- persist failure must reach the process owner
                # Reader threads cannot silently lose a persistence failure.
                # poll() asks the existing owner to stop and clean its child.
                self.failed.set()

    def finish(self, result):
        with self.lock:
            if self.failed.is_set():
                raise OSError("durable_capture_failed")
            result = dict(result, raw_stdout_retained=True)
            checksum = _atomic(self.directory, "result.json", result, RESULT_LIMIT)
            self.state.update(
                phase="returned",
                terminal=True,
                cleanup_confirmed=result["cleanup_confirmed"],
                result_sha256=checksum,
            )
            self.checkpoint()
            return result

    def close(self):
        with self.lock:
            if not self.closed:
                self.closed = True
                if self.stdout is not None:
                    os.close(self.stdout)
                os.close(self.directory)


class Stream:
    def __init__(self, stream, name, journal):
        self.stream, self.name, self.journal = stream, name, journal

    def read(self, size):
        # BufferedReader.read(4096) can wait for 4096 bytes or EOF. read1 keeps
        # exact bytes while exposing a flushed short prefix before process exit.
        try:
            chunk = getattr(self.stream, "read1", self.stream.read)(size)
        except BaseException:  # noqa: BLE001 -- reader failure must fail the capture closed
            self.journal.failed.set()
            return b""
        self.journal.record(self.name, chunk)
        return chunk

    def close(self):
        self.stream.close()


class Process:
    def __init__(self, process, journal, cancelled):
        self.process, self.journal, self.cancelled = process, journal, cancelled
        self.pid = process.pid
        self.stdout = Stream(process.stdout, "stdout", journal)
        self.stderr = Stream(process.stderr, "stderr", journal)

    @property
    def returncode(self):
        return self.process.returncode

    def poll(self):
        if self.cancelled.is_set():
            raise KeyboardInterrupt
        if self.journal.failed.is_set():
            raise OSError("durable_capture_failed")
        return self.process.poll()

    def wait(self, timeout=None):
        return self.process.wait(timeout=timeout)


def capture(argv, *, root, cell, seconds, reserve, popen=None):
    """Persist before return; injected launcher is not release or authorization.

    There is deliberately no default native launcher. A future reviewed v2
    controller must verify its new release, authority, budget and input identity
    before injecting a launcher. This helper cannot reopen a v1 queue.
    """
    if popen is None:
        raise ValueError("durable_native_release_required")
    if not 0 < seconds <= 55:
        raise ValueError("durable_capture_deadline")
    if threading.current_thread() is not threading.main_thread():
        raise ValueError("durable_capture_main_thread_required")
    journal = Journal(root, cell)
    cancelled = threading.Event()
    previous = signal.getsignal(signal.SIGTERM)

    def terminate(*_):
        cancelled.set()

    def consume():
        if cancelled.is_set():
            raise KeyboardInterrupt
        reserve()
        journal.phase("reserved")

    def start(*args, **kwargs):
        if cancelled.is_set():
            raise KeyboardInterrupt
        process = popen(*args, **kwargs)
        wrapped = Process(process, journal, cancelled)
        try:
            journal.started(process)
        except BaseException:  # noqa: BLE001 -- never lose ownership after a successful spawn
            journal.failed.set()
        # Always return a spawned child to the sole owner, including lease
        # persistence failures, so its finally block can perform cleanup.
        return wrapped

    completed = None
    signal.signal(signal.SIGTERM, terminate)
    try:
        result = short.capture(argv, seconds=seconds, reserve=consume, popen=start)
        if cancelled.is_set() and result["stop_code"] is None:
            result.update(
                stop_code="native_cancelled",
                error_type="KeyboardInterrupt",
                answer=None,
                format_status="not_assessed_technical_failure",
            )
        completed = journal.finish(result)
        return completed
    finally:
        signal.signal(signal.SIGTERM, previous)
        journal.close()
        # A signal arriving during the terminal fsync must still stop the caller
        # from advancing to another cell, even if this result was committed.
        if cancelled.is_set() and completed is not None and completed["stop_code"] is None:
            raise KeyboardInterrupt


def _json(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("capture_duplicate_key")
            value[key] = item
        return value

    def constant(_):
        raise ValueError("capture_nonfinite")

    return json.loads(raw, object_pairs_hook=unique, parse_constant=constant)


def _require(condition):
    if not condition:
        raise ValueError("capture_metadata_inconsistent")


def _observations(value, *, partial=False):
    if partial and value in ({}, {"diagnostic_invalid_integer": True}):
        return
    required = {
        "events",
        "failures",
        "image_encoder_and_decode_observed",
        "image_tokens_observed",
        "raw_stderr_retained",
    }
    optional = {"warnings", "discarded_stderr_bytes", "representation_quality_or_attention_proven"}
    if partial:
        optional.add("events_truncated")
    _require(type(value) is dict and required <= value.keys() <= required | optional)
    _require(value["raw_stderr_retained"] is False)
    _require(type(value["image_encoder_and_decode_observed"]) is bool)
    _require(value["image_tokens_observed"] is None or type(value["image_tokens_observed"]) is int)
    _require(type(value["events"]) is list and type(value["failures"]) is list)
    lengths = {"encoder_start": 3, "encoder_done": 1, "decode_start": 3, "decode_done": 3}
    for event in value["events"]:
        _require(type(event) is dict and set(event) == {"kind", "values"})
        _require(event["kind"] in lengths and type(event["values"]) is list)
        _require(len(event["values"]) == lengths[event["kind"]])
        _require(all(type(x) is int and 0 <= x <= 10000000 for x in event["values"]))
    for failure in value["failures"]:
        _require(type(failure) is dict and "code" in failure)
        if failure["code"] in ("projector_load_failed", "diagnostic_invalid_integer"):
            _require(set(failure) == {"code"})
        else:
            _require(failure["code"] in {code for code, _ in short.base.FAILURES})
            _require(set(failure) == {"code", "number"} and type(failure["number"]) is int)
    if not partial and value["failures"] != [{"code": "diagnostic_invalid_integer"}]:
        templates = {
            "encoder_start": "encoding mtmd batch, n_chunks = {} (done = {}, total = {})",
            "encoder_done": "mtmd batch encoding done in {} ms",
            "decode_start": "decoding image batch {}/{}, n_tokens_batch = {}",
            "decode_done": "image decoded (batch {}/{}) in {} ms",
        }
        lines = [templates[event["kind"]].format(*event["values"]) for event in value["events"]]
        failure_templates = {
            "encoder_failed": "Failed to encode mtmd batch, res = {}",
            "media_decode_failed": "Unable to decode media chunk {}",
            "prompt_tokenization_failed": "Unable to tokenize prompt, res = {}",
            "projector_load_failed": "Failed to load vision model from redacted",
        }
        lines.extend(
            failure_templates[item["code"]].format(item.get("number")) for item in value["failures"]
        )
        rebuilt = short.base.observations(("\n".join(lines) + "\n").encode())
        for key in (
            "events",
            "failures",
            "image_encoder_and_decode_observed",
            "image_tokens_observed",
        ):
            _require(value[key] == rebuilt[key])
    if "warnings" in value:
        _require(type(value["warnings"]) is list)
        _require(all(item == "qwen_grounding_1024_token_notice" for item in value["warnings"]))
    if "discarded_stderr_bytes" in value:
        _require(type(value["discarded_stderr_bytes"]) is int)
        _require(0 <= value["discarded_stderr_bytes"] <= short.base.LIMITS["stderr_bytes"])
    for key in ("representation_quality_or_attention_proven", "events_truncated"):
        if key in value:
            _require(type(value[key]) is bool)
    _require(value.get("representation_quality_or_attention_proven", False) is False)


def _state(value):
    keys = {
        "schema",
        "phase",
        "terminal",
        "cleanup_confirmed",
        "stdout_bytes",
        "stdout_sha256",
        "stderr_bytes",
        "stdout_eof",
        "stderr_eof",
        "progress",
    }
    _require(type(value) is dict and keys <= value.keys() <= keys | {"result_sha256"})
    _require(value["schema"] == "vlm-private-capture-v2")
    _require(value["phase"] in {"created", "reserved", "process_started", "collecting", "returned"})
    for key in ("terminal", "cleanup_confirmed", "stdout_eof", "stderr_eof"):
        _require(type(value[key]) is bool)
    for key in ("stdout_bytes", "stderr_bytes"):
        _require(type(value[key]) is int and 0 <= value[key] <= short.base.LIMITS[key])
    for key in ("stdout_sha256", "result_sha256"):
        if key in value:
            _require(type(value[key]) is str and re.fullmatch(r"[0-9a-f]{64}", value[key]))
    _require(value["terminal"] == (value["phase"] == "returned") == ("result_sha256" in value))
    _require(value["terminal"] or not value["cleanup_confirmed"])
    _observations(value["progress"], partial=True)


def _result(value, state, raw, directory):
    observations = {
        key: item
        for key, item in value.items()
        if key
        in {
            "events",
            "failures",
            "warnings",
            "image_encoder_and_decode_observed",
            "image_tokens_observed",
            "discarded_stderr_bytes",
            "raw_stderr_retained",
            "representation_quality_or_attention_proven",
        }
    }
    _observations(observations)
    required = {
        "returncode",
        "stdout_bytes",
        "raw_stdout_retained",
        "stop_code",
        "runtime_seconds",
        "peak_rss_mib",
        "cleanup_confirmed",
        "process_started",
        "answer",
        "format_status",
    }
    _require(
        observations.keys() | required
        <= value.keys()
        <= observations.keys() | required | {"error_type"}
    )
    stops = {
        None,
        "encoder_failed",
        "media_decode_failed",
        "prompt_tokenization_failed",
        "projector_load_failed",
        "diagnostic_invalid_integer",
        "native_failed_unknown_stage",
        "diagnostics_insufficient",
        "native_timeout",
        "native_cancelled",
        "native_resource_limit",
        "native_operation_failed",
        "output_limit_or_unclosed_pipe",
        "cleanup_unconfirmed",
    }
    _require(value["stop_code"] in stops)
    _require(value["raw_stdout_retained"] is True)
    _require(type(value["cleanup_confirmed"]) is bool and type(value["process_started"]) is bool)
    _require(value["cleanup_confirmed"] == state["cleanup_confirmed"])
    _require(type(value["stdout_bytes"]) is int and value["stdout_bytes"] >= 0)
    _require(min(value["stdout_bytes"], short.base.LIMITS["stdout_bytes"]) == len(raw))
    for key in ("runtime_seconds", "peak_rss_mib"):
        _require(type(value[key]) in (int, float) and math.isfinite(value[key]) and value[key] >= 0)
    if "error_type" in value:
        _require(
            value["error_type"]
            in {
                "OSError",
                "TimeoutError",
                "RuntimeError",
                "KeyboardInterrupt",
                "SystemExit",
                "FileNotFoundError",
                "PermissionError",
            }
        )
    if value["process_started"]:
        lease = _json(_read(directory, "process-lease.json", STATE_LIMIT))
        _require(set(lease) == {"schema", "owner", "leader", "pgid", "boot_id"})
        _require(lease["schema"] == "vlm-owned-process-v2")
        for key in ("owner", "leader"):
            _require(type(lease[key]) is dict and set(lease[key]) == {"pid", "start_ticks"})
            _require(all(type(x) is int and x > 0 for x in lease[key].values()))
        _require(type(lease["pgid"]) is int and lease["pgid"] == lease["leader"]["pid"])
        _require(type(lease["boot_id"]) is str and re.fullmatch(r"[0-9a-f-]{36}", lease["boot_id"]))
        if value["cleanup_confirmed"]:
            _require(state["stdout_eof"] and state["stderr_eof"])
            _require(type(value["returncode"]) is int)
    else:
        _require(value["returncode"] is None and value["stop_code"] == "native_operation_failed")
    if value["stop_code"] is None:
        _require(value["returncode"] == 0 and value["image_encoder_and_decode_observed"])
        _require(value["cleanup_confirmed"] and value["process_started"])
        try:
            answer = short.decode(raw)
        except (ValueError, TypeError, UnicodeError, RecursionError):
            _require(value["format_status"] == "invalid" and value["answer"] is None)
        else:
            _require(value["format_status"] == "valid" and value["answer"] == answer)
    else:
        _require(
            value["format_status"] == "not_assessed_technical_failure" and value["answer"] is None
        )
    if state["stderr_eof"] and state["progress"] != {"diagnostic_invalid_integer": True}:
        progress = dict(state["progress"])
        progress.pop("events_truncated", None)
        limited = dict(observations)
        limited["events"] = limited["events"][-32:]
        limited["failures"] = limited["failures"][:16]
        if "warnings" in limited:
            limited["warnings"] = limited["warnings"][:16]
        _require(progress == limited)


def inspect(root, cell):
    """Read committed checkpoints only; never print the private raw prefix."""
    directory = _folder(root, cell, create=False)
    try:
        state = _json(_read(directory, "state.json", STATE_LIMIT))
        _state(state)
        raw = _read(directory, "stdout.bin", short.base.LIMITS["stdout_bytes"])
        committed = raw[: state["stdout_bytes"]]
        if (
            len(committed) != state["stdout_bytes"]
            or hashlib.sha256(committed).hexdigest() != state["stdout_sha256"]
        ):
            raise ValueError("capture_prefix_integrity")
        result = None
        if state["terminal"]:
            final = _read(directory, "result.json", RESULT_LIMIT)
            if hashlib.sha256(final).hexdigest() != state["result_sha256"]:
                raise ValueError("capture_result_integrity")
            result = _json(final)
            _require(type(result) is dict)
            _result(result, state, committed, directory)
        return {
            "schema": state["schema"],
            "phase": state["phase"],
            "terminal": state["terminal"],
            "cleanup_confirmed": state["cleanup_confirmed"],
            "durable_stdout_bytes": len(committed),
            "stderr_bytes": state["stderr_bytes"],
            "stdout_eof": state["stdout_eof"],
            "stderr_eof": state["stderr_eof"],
            "progress_is_provisional": True,
            "progress": state["progress"],
            "observation": result,
        }
    finally:
        os.close(directory)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--cell", required=True, choices=CELLS)
    arguments = parser.parse_args()
    try:
        print(json.dumps(inspect(arguments.root, arguments.cell), allow_nan=False))
    except Exception:  # noqa: BLE001 -- no raw errors or private paths
        print('{"status":"capture_inspection_failed"}')
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()

"""Native225 routing, 55-second useful deadline; unchanged v2 journal/owner/decoder.

Only directory routing, Journal construction and capture's ceiling differ.
The v2 storage schema and strict inspection validators intentionally stay intact.
There is no CLI, default launcher, release writer, or additional process owner.
"""

from __future__ import annotations

import hashlib
import os
import signal
import stat
import threading
from pathlib import Path

from scripts import vlm_durable_capture_v2 as frozen

NAMESPACE = "issue-4-vlm-native225-probe-v1"
MAX_CAPTURE_SECONDS = 55
CELLS, DIRECTORY = ("negative-N",), frozen.DIRECTORY
STATE_LIMIT, RESULT_LIMIT = frozen.STATE_LIMIT, frozen.RESULT_LIMIT
short, Process = frozen.short, frozen.Process
_directory, _read, _json = frozen._directory, frozen._read, frozen._json
_state, _result, _require = frozen._state, frozen._result, frozen._require


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


class Journal(frozen.Journal):
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


def capture(argv, *, root, cell, seconds, reserve, popen=None):
    """Persist before return; injected launcher is not release or authorization.

    There is deliberately no default native launcher. A reviewed native225
    controller must verify its new release, authority, budget and input identity
    before injecting a launcher. The previous namespaces are unreachable through this helper.
    """
    if popen is None:
        raise ValueError("durable_native_release_required")
    if type(seconds) not in (int, float) or not 0 < seconds <= MAX_CAPTURE_SECONDS:
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

"""Dedicated Linux subreaper for one bounded recovery command, across sessions.

No application, decoder, model or network library is imported. This module is
an operator process boundary, not a reusable server/thread pool supervisor.
"""

from __future__ import annotations

import base64
import ctypes
import json
import os
import selectors
import signal
import subprocess
import sys
import time
from pathlib import Path

from scripts.demo_recovery_policy import exclusive_json


def proc_identity(pid):
    try:
        raw = Path(f"/proc/{pid}/stat").read_text()
        fields = raw[raw.rfind(")") + 2 :].split()
        return {
            "pid": pid,
            "ppid": int(fields[1]),
            "start_ticks": int(fields[19]),
            "state": fields[0],
            "rss": int(fields[21]) * os.sysconf("SC_PAGE_SIZE"),
        }
    except (OSError, ValueError, IndexError):
        return None


def descendants(parent_pid):
    values = {}
    for entry in Path("/proc").iterdir():
        if entry.name.isdigit():
            value = proc_identity(int(entry.name))
            if value is not None:
                values[value["pid"]] = value
    owned, parents = {}, {parent_pid}
    while True:
        new = {
            pid: item
            for pid, item in values.items()
            if item["ppid"] in parents and pid not in owned
        }
        if not new:
            break
        owned.update(new)
        parents.update(new)
    return owned


def send_owned(identity, sig):
    """A pidfd prevents a reused PID from receiving the signal after inspection."""
    try:
        descriptor = os.pidfd_open(identity["pid"])
    except ProcessLookupError:
        return
    try:
        current = proc_identity(identity["pid"])
        if current and current["start_ticks"] == identity["start_ticks"]:
            signal.pidfd_send_signal(descriptor, sig)
    finally:
        os.close(descriptor)


def own_descendants(baseline):
    return {
        pid: item
        for pid, item in descendants(os.getpid()).items()
        if (pid, item["start_ticks"]) not in baseline
    }


def collect_owned(process, baseline, *, timeout=15):
    """Freeze ancestors before killing, including children that made a session.

    In production this interpreter owns only this job. The baseline excludes
    pre-existing control children when testing the function directly.
    """
    deadline = time.monotonic() + timeout
    seen = {}
    while time.monotonic() < deadline:
        found = own_descendants(baseline)
        for pid, item in found.items():
            seen[(pid, item["start_ticks"])] = item
            try:
                send_owned(item, signal.SIGSTOP)
            except OSError:
                return False
        # A newly adopted or concurrently forked child is included next time.
        for item in tuple(found.values()):
            try:
                send_owned(item, signal.SIGKILL)
            except OSError:
                return False
        if process is not None:
            try:
                process.wait(timeout=0.05)
            except subprocess.TimeoutExpired:
                pass
        for item in tuple(seen.values()):
            if process is not None and item["pid"] == process.pid:
                continue  # Popen retains ownership of its own wait status.
            try:
                os.waitpid(item["pid"], os.WNOHANG)
            except ChildProcessError:
                pass
        if not own_descendants(baseline):
            return True
        time.sleep(0.02)
    return False


def workspace_bytes(folder):
    total = 0
    for parent, _, files in os.walk(folder, followlinks=False):
        for name in files:
            try:
                total += (Path(parent) / name).lstat().st_size
            except FileNotFoundError:
                pass
    return total


def classify_stderr(raw):
    value = raw.lower()
    if any(text in value for text in [b"sign in", b"not a bot", b"login required", b"captcha"]):
        return "authentication_or_bot_check"
    if b"http error 403" in value or b"http error 429" in value:
        return "access_denied_or_rate_limited"
    if any(text in value for text in [b"private video", b"video unavailable", b"removed"]):
        return "source_unavailable"
    return "child_failed"


def supervise(job):
    if ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) != 0:
        raise RuntimeError("subreaper_unavailable")
    baseline = {(pid, row["start_ticks"]) for pid, row in descendants(os.getpid()).items()}
    cancelled = False

    def cancel(_signum, _frame):
        nonlocal cancelled
        cancelled = True

    previous = {sig: signal.signal(sig, cancel) for sig in (signal.SIGTERM, signal.SIGINT)}
    process = None
    output, errors = bytearray(), bytearray()
    code, cleanup = "startup_failed_consumed", False
    started = time.monotonic()
    peak_rss = peak_disk = 0
    lease = Path(job["lease"])
    try:
        # Supervisor identity exists before any command is allowed to start.
        exclusive_json(
            lease,
            {
                "supervisor": proc_identity(os.getpid()),
                "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
                "manual_recovery_required_without_cleanup_ack": True,
            },
        )

        process = subprocess.Popen(
            [
                sys.executable,
                "-B",
                str(Path(__file__).with_name("demo_recovery_child.py")),
                str(job["file_bytes"]),
                *job["argv"],
            ],
            cwd=job["cwd"],
            env=job["env"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        selector = selectors.DefaultSelector()
        for stream, target in [(process.stdout, output), (process.stderr, errors)]:
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, target)
        code = "completed"
        try:
            while True:
                if cancelled:
                    code = "cancelled_consumed"
                    break
                if time.monotonic() - started >= job["timeout"]:
                    code = "timeout"
                    break
                owned = own_descendants(baseline)
                own = proc_identity(os.getpid())
                rss = sum(row["rss"] for row in owned.values()) + (own["rss"] if own else 0)
                disk = workspace_bytes(Path(job["workspace"]))
                peak_rss, peak_disk = max(peak_rss, rss), max(peak_disk, disk)
                if rss > job["rss_bytes"] or disk > job["workspace_bytes"]:
                    code = "rss_limit" if rss > job["rss_bytes"] else "workspace_limit"
                    break
                for key, _ in selector.select(0.05):
                    target = key.data
                    chunk = os.read(key.fd, min(4096, job["io_bytes"] + 1 - len(target)))
                    if not chunk:
                        selector.unregister(key.fileobj)
                    else:
                        target.extend(chunk)
                        if len(target) > job["io_bytes"]:
                            code = "output_limit"
                            break
                if code != "completed":
                    break
                if process.poll() is not None:
                    if process.returncode != 0:
                        code = classify_stderr(errors)
                        break
                    if not selector.get_map():
                        break
        finally:
            selector.close()
            process.stdout.close()
            process.stderr.close()
    except Exception:  # noqa: BLE001 - never retain raw child/monitor exceptions
        code = "startup_or_monitor_failure_consumed"
    finally:
        cleanup = collect_owned(process, baseline)
        for sig, old in previous.items():
            signal.signal(sig, old)
    # Raw stderr is never forwarded or persisted. stdout is bounded and private.
    return {
        "code": code,
        "cleanup_confirmed": cleanup,
        "stdout_b64": base64.b64encode(output).decode() if code == "completed" else "",
        "stdout_bytes": len(output),
        "stderr_bytes": len(errors),
        "returncode": process.returncode if process is not None else None,
        "elapsed_seconds": time.monotonic() - started,
        "sampled_peak_rss_bytes": peak_rss,
        "sampled_peak_workspace_bytes": peak_disk,
        "sampling_interval_seconds": 0.05,
    }


def main():
    raw = sys.stdin.buffer.read(262145)
    if not raw or len(raw) > 262144:
        raise ValueError("invalid_supervisor_job")
    result = supervise(json.loads(raw))
    encoded = json.dumps(result, allow_nan=False).encode()
    if len(encoded) > 200000:
        raise ValueError("supervisor_output_limit")
    sys.stdout.buffer.write(encoded)
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    main()

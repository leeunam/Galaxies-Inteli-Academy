"""Dedicated Linux subreaper, outside its owned killable graph process group."""

import ctypes
import json
import os
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

MAX_LINE = 262144
ROOT = Path(__file__).resolve().parents[1]
CLEANUP_CONFIRMED = True


def identity(pid):
    # Fields after ')' start at field 3; starttime is field 22. Do not inspect
    # environ or expose command lines, credentials or private payloads.
    raw = Path(f"/proc/{pid}/stat").read_text()
    return {"pid": pid, "start_ticks": int(raw.rsplit(")", 1)[1].split()[19])}


def publish_lease(scratch, group):
    """Durable recovery metadata, published before any payload is released."""
    directory = Path(scratch)
    lease = {
        "schema_version": "integrated-process-lease-v2",
        "supervisor": identity(os.getpid()),
        "leader": identity(group),
        "pgid": group,
        "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
    }
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=directory, delete=False) as output:
            temporary = Path(output.name)
            os.chmod(temporary, 0o600)
            json.dump(lease, output)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, directory / "process-lease.json")
        fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def collect_group(process):
    """Kill only our known group; reap adopted children before scratch removal."""
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=5)
    deadline = time.monotonic() + 5
    while True:
        try:
            pid, _ = os.waitpid(-process.pid, os.WNOHANG)
        except ChildProcessError:
            return
        if not pid:
            if time.monotonic() >= deadline:
                raise RuntimeError("descendants_not_reaped")
            time.sleep(0.01)


def run(job):
    global CLEANUP_CONFIRMED
    if ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        raise RuntimeError("subreaper_required")
    cancelled = False

    def stop(*_):
        nonlocal cancelled
        cancelled = True

    signal.signal(signal.SIGTERM, stop)
    environment = {
        "PATH": os.defpath,
        "PYTHONDONTWRITEBYTECODE": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "LANGSMITH_TRACING": "false",
        "LANGCHAIN_TRACING_V2": "false",
        "GALAXIES_SUPERVISED": "1",
    }
    deadline = time.monotonic() + job["timeout"]
    # Spawn without input. The process group is known before releasing work.
    process = subprocess.Popen(
        [
            job["graph_python"],
            "-B",
            "-m",
            "galaxies_orchestration.integrated_graph_v2",
            "--worker-python",
            job["worker_python"],
            "--worker-module",
            job["worker_module"],
            "--worker-arguments",
            *job["arguments"],
        ],
        cwd=ROOT / "orchestration",
        env=environment,
        start_new_session=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    CLEANUP_CONFIRMED = False
    checkpoint = result = None
    try:
        publish_lease(job["scratch"], process.pid)
        raw = json.dumps(job["payload"], allow_nan=False).encode() + b"\n"
        if len(raw) > MAX_LINE:
            raise ValueError("input_limit")
        os.set_blocking(process.stdin.fileno(), False)
        with selectors.DefaultSelector() as poll:
            poll.register(process.stdout, selectors.EVENT_READ)
            poll.register(process.stdin, selectors.EVENT_WRITE)
            buffer = b""
            messages = 0
            while not cancelled and time.monotonic() < deadline and result is None:
                events = poll.select(min(0.05, max(0, deadline - time.monotonic())))
                if not events:
                    continue
                key, _ = events[0]
                if key.fileobj is process.stdin:
                    raw = raw[os.write(process.stdin.fileno(), raw) :]
                    if not raw:
                        poll.unregister(process.stdin)
                        process.stdin.close()
                    continue
                chunk = os.read(process.stdout.fileno(), 65536)
                if not chunk:
                    break
                buffer += chunk
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    if len(line) + 1 > MAX_LINE:
                        raise ValueError("output_limit")
                    message = json.loads(line)
                    messages += 1
                    if set(message) != {"kind", "value"} or messages > 2:
                        raise ValueError("invalid_graph_output")
                    if messages == 1 and message["kind"] == "checkpoint":
                        checkpoint = message["value"]
                    elif messages == 2 and message["kind"] == "result":
                        result = message["value"]
                    else:
                        raise ValueError("invalid_graph_output")
                if len(buffer) > MAX_LINE:
                    raise ValueError("output_limit")
    except Exception:  # noqa: BLE001 - private exceptions never become output
        result = None
    finally:
        collect_group(process)
        CLEANUP_CONFIRMED = True
        shutil.rmtree(job["scratch"])
        if not process.stdin.closed:
            process.stdin.close()
        process.stdout.close()
    if cancelled:
        return {"orchestration_error": "cancelled"}
    if result is not None:
        if result["analysis"] != checkpoint:
            result = None
        else:
            return result
    if checkpoint is not None:
        return {
            "schema_version": "creative-explanation-integrated-v2",
            "analysis": checkpoint,
            "explanation": {
                "status": "incomplete",
                "kind": "deterministic_notice",
                "reason_code": "explanation_worker_failed",
                "packet_sha256": None,
                "adherence_status": "not_evaluated",
                "claims": [],
            },
            "evidence_packet": None,
            "orchestration": {
                "kind": "integrated_stategraph_v2",
                "stategraph_executed": True,
                "explainer_subgraph_executed": False,
                "native_feature_handoff": False,
                "real_provider_verified": False,
                "selector_kind": "absent",
            },
        }
    return {"orchestration_error": "local_graph_failed"}


def main():
    try:
        raw = sys.stdin.buffer.read(MAX_LINE + 1)
        if len(raw) > MAX_LINE:
            raise ValueError("input_limit")
        result = run(json.loads(raw))
    except Exception:  # noqa: BLE001 - no traceback on public channels
        result = {"orchestration_error": "supervisor_failed"}
    print(json.dumps({"result": result, "cleanup_confirmed": CLEANUP_CONFIRMED}, allow_nan=False))


if __name__ == "__main__":
    main()

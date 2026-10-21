"""Two fixed known images: sanitized encoder observability, never attribute approval."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import tempfile
import threading
import time
from pathlib import Path

import psutil
from PIL import Image

from scripts.gguf_visual_attributes import HASHES, MODEL_DIR, RUNTIME
from scripts.vlm_product_v16 import decode, specification

ROOT = Path(__file__).resolve().parents[1]
PROOF = "data/private/issue-4-vlm-encoder-diagnostico-v1"
QUEUE = "data/private/issue-4-vlm-encoder-probe-v1"
PROTOCOL = "fixed-two-image-encoder-observability-v1"
LIMITS = {
    "calls": 2,
    "seconds": 180,
    "rss_mib": 3.3 * 1024,
    "stdout_bytes": 16384,
    "stderr_bytes": 262144,
}
CASE_DIGESTS = (
    "609bfa9a3b8da1616a452ae19fcf121aabd527424d104ef18b03b6bce0684ad8",
    "4415cb4857e336fe61279b31e72249847cf951019e59b0cd8bfbdbbfae899e16",
)
SOURCES = (
    "scripts/vlm_encoder_probe.py",
    "tests/test_vlm_encoder_probe.py",
    "docs/issue-4-vlm-encoder-protocolo.md",
)
PATTERNS = (
    (
        "encoder_start",
        re.compile(r"encoding mtmd batch, n_chunks = (\d+) \(done = (\d+), total = (\d+)\)"),
    ),
    ("encoder_done", re.compile(r"mtmd batch encoding done in (\d+) ms")),
    ("decode_start", re.compile(r"decoding image batch (\d+)/(\d+), n_tokens_batch = (\d+)")),
    ("decode_done", re.compile(r"image decoded \(batch (\d+)/(\d+)\) in (\d+) ms")),
)
FAILURES = (
    ("encoder_failed", re.compile(r"Failed to encode mtmd batch, res = (-?\d+)")),
    ("media_decode_failed", re.compile(r"Unable to decode media chunk (\d+)")),
    ("prompt_tokenization_failed", re.compile(r"Unable to tokenize prompt, res = (-?\d+)")),
)


class ProbeStop(ValueError):
    def __init__(self, code):
        super().__init__(code)
        self.code = code


def sha(path):
    with path.open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def digest(body):
    return hashlib.sha256(json.dumps(body, sort_keys=True, allow_nan=False).encode()).hexdigest()


def write(path, body, *, exclusive=False):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    raw = json.dumps(body, sort_keys=True, allow_nan=False).encode() + b"\n"
    if exclusive:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
    else:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as f:
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
            temp = Path(f.name)
        os.replace(temp, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def case_digest(body):
    # Preserve the spaced canonical convention of the already frozen cases.
    return digest(body)


def cases(root=ROOT):
    positive = json.loads(
        (root / "data/private/issue-4-vlm-pos-v16-pares-positivos-v1/plan.json").read_bytes()
    )["base"]["cases"]["positive"][0]
    old = json.loads((root / "data/private/issue-4-vlm-v16-v2/plan.json").read_bytes())
    white = next(c for c in old["base"]["cases"]["negative"] if c["sample_id"] == "white")
    result = [positive, white]
    if tuple(case_digest(c) for c in result) != CASE_DIGESTS:
        raise ValueError("frozen_probe_inputs_changed")
    return [
        {
            "kind": "positive",
            "source_case_sha256": CASE_DIGESTS[0],
            **{
                k: positive[k]
                for k in ("png_sha256", "seconds", "source_frame", "sheet_path", "sheet_sha256")
            },
        },
        {
            "kind": "white",
            "source_case_sha256": CASE_DIGESTS[1],
            **{k: white[k] for k in ("png_sha256", "seconds")},
        },
    ]


def template(root=ROOT):
    path = root / "data/private/issue-4-vlm-v16-verificacao-v1/commands.json"
    pre = json.loads((path.parent / "offline-preflight.json").read_bytes())
    if sha(path) != pre["files_sha256"][path.name]:
        raise ValueError("original_command_receipt_changed")
    return json.loads(path.read_bytes())["item_first"]["normalized_argv"]


def command(original, image, schema):
    result = [
        str(image) if a == "<PNG>" else str(schema) if a == "<SCHEMA>" else a for a in original
    ]
    i = result.index("--verbosity") + 1
    if result[i] != "0":
        raise ValueError("original_verbosity_not_zero")
    result[i] = "3"
    return result


def environment():
    return {
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "OMP_NUM_THREADS": "4",
        "OPENBLAS_NUM_THREADS": "1",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "CUDA_VISIBLE_DEVICES": "",
        "LANGSMITH_TRACING": "false",
        "LANGCHAIN_TRACING_V2": "false",
    }


def observations(stderr):
    """Only fixed events and integers survive; never retain rejected text or its hash."""
    events = []
    failures = []
    warnings = []
    for line in stderr.decode("utf-8", errors="replace").splitlines():
        for code, pattern in FAILURES:
            match = pattern.fullmatch(line.strip())
            if match:
                failures.append({"code": code, "number": int(match.group(1))})
        if line.strip().startswith("Failed to load vision model from "):
            failures.append({"code": "projector_load_failed"})
        if re.fullmatch(
            r"[a-zA-Z0-9_]+: Qwen-VL models require at minimum 1024 image tokens to function correctly on grounding tasks",
            line.strip(),
        ):
            warnings.append("qwen_grounding_1024_token_notice")
        for kind, pattern in PATTERNS:
            match = pattern.fullmatch(line.strip())
            if match:
                values = [int(x) for x in match.groups()]
                if any(x > 10000000 for x in values):
                    raise ValueError("diagnostic_integer_out_of_range")
                events.append({"kind": kind, "values": values})
                break
    kinds = [e["kind"] for e in events]
    starts = [e["values"] for e in events if e["kind"] == "decode_start"]
    ends = [e["values"] for e in events if e["kind"] == "decode_done"]
    valid = bool(starts) and kinds[:2] == ["encoder_start", "encoder_done"]
    valid = valid and kinds.count("encoder_start") == kinds.count("encoder_done") == 1
    if valid:
        valid = events[0]["values"][0] == 1 and kinds[2:] == [
            k for _ in starts for k in ("decode_start", "decode_done")
        ]
        valid = (
            valid and len(starts) == len(ends) and [s[:2] for s in starts] == [e[:2] for e in ends]
        )
        valid = valid and [s[0] for s in starts] == list(range(1, len(starts) + 1))
        valid = valid and all(s[1] == len(starts) and s[2] > 0 for s in starts)
    return {
        "events": events,
        "failures": failures,
        "warnings": warnings,
        "image_encoder_and_decode_observed": bool(valid) and not failures,
        "image_tokens_observed": sum(s[2] for s in starts) if valid else None,
        "discarded_stderr_bytes": len(stderr),
        "raw_stderr_retained": False,
        "representation_quality_or_attention_proven": False,
    }


def summarize(stdout, stderr, returncode):
    try:
        result = observations(stderr)
    except ValueError:
        result = {
            "events": [],
            "failures": [{"code": "diagnostic_invalid_integer"}],
            "image_encoder_and_decode_observed": False,
            "image_tokens_observed": None,
            "raw_stderr_retained": False,
        }
    result.update(
        returncode=returncode, stdout_bytes=len(stdout), raw_stdout_retained=False, native=None
    )
    parsed_ok = False
    try:
        native, value = decode(stdout.decode("utf-8"), "item_first")
        result.update(native=native, projected_value=value)
        parsed_ok = True
    except (ValueError, TypeError, UnicodeError, RecursionError):
        pass
    result["stop_code"] = (
        result["failures"][0]["code"]
        if result["failures"]
        else "native_failed_unknown_stage"
        if returncode
        else "diagnostics_insufficient"
        if not result["image_encoder_and_decode_observed"]
        else "stdout_invalid_original_schema"
        if not parsed_ok
        else None
    )
    return result


def capture(argv, *, seconds, reserve, popen=None, clock=time.monotonic, pause=time.sleep):
    """One owned child; independent bounded pipes, group cleanup and sanitized result."""
    if not 0 < seconds <= 180:
        raise ValueError("invalid_probe_deadline")
    popen = subprocess.Popen if popen is None else popen
    reserve()  # caller must durably consume before any spawn, including startup failure
    process = None
    threads = []
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    counts = {"stdout": 0, "stderr": 0}
    exceeded = threading.Event()
    peak = 0.0
    started = clock()
    failure = None
    cleanup_confirmed = True

    def stop():
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

    def read(name, stream):
        cap = LIMITS[name + "_bytes"]
        while chunk := stream.read(4096):
            counts[name] += len(chunk)
            buffers[name].extend(chunk[: max(0, cap - len(buffers[name]))])
            if counts[name] > cap:
                exceeded.set()
                stop()

    try:
        process = popen(
            argv,
            cwd=ROOT,
            env=environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
        )
        for name in buffers:
            thread = threading.Thread(target=read, args=(name, getattr(process, name)), daemon=True)
            thread.start()
            threads.append(thread)
        while process.poll() is None:
            if clock() - started >= seconds:
                raise TimeoutError("probe_deadline")
            try:
                peak = max(peak, psutil.Process(process.pid).memory_info().rss / 1024**2)
            except psutil.NoSuchProcess:
                pass
            if peak > LIMITS["rss_mib"] or exceeded.is_set():
                raise RuntimeError("probe_resource_limit")
            pause(0.05)
        process.wait()
    except BaseException as caught:  # noqa: BLE001 -- cancellation must produce a sanitized receipt
        failure = caught
    finally:
        cleanup_deadline = clock() + 5
        try:
            stop()
            if process is not None:
                process.wait(timeout=max(0, cleanup_deadline - clock()))
        except BaseException:  # noqa: BLE001 -- never delete scratch after uncertain cleanup
            cleanup_confirmed = False
        for thread in threads:
            thread.join(timeout=max(0, cleanup_deadline - clock()))
        if any(t.is_alive() for t in threads):
            cleanup_confirmed = False
        elif process is not None:
            for name in buffers:
                getattr(process, name).close()
    result = summarize(
        bytes(buffers["stdout"]),
        bytes(buffers["stderr"]),
        process.returncode if process is not None else None,
    )
    if failure is not None:
        result["stop_code"] = (
            "native_timeout"
            if isinstance(failure, TimeoutError)
            else "native_cancelled"
            if isinstance(failure, (KeyboardInterrupt, SystemExit))
            else "native_resource_limit"
            if exceeded.is_set() or peak > LIMITS["rss_mib"]
            else "native_operation_failed"
        )
        result["error_type"] = type(failure).__name__
    if any(t.is_alive() for t in threads) or exceeded.is_set():
        result["stop_code"] = "output_limit_or_unclosed_pipe"
    if not cleanup_confirmed:
        result["stop_code"] = "cleanup_unconfirmed"
    result.update(
        runtime_seconds=clock() - started,
        peak_rss_mib=peak,
        cleanup_confirmed=cleanup_confirmed,
        process_started=process is not None,
    )
    return result


def configuration(root=ROOT):
    before = json.loads((root / PROOF / "before.json").read_bytes())
    for n, h in before["protected_sha256"].items():
        if sha(root / n) != h:
            raise ValueError("probe_protected_file_changed")
    for n, wanted in before["native_files_previous_identity"].items():
        stat = Path(n).lstat()
        if any(getattr(stat, k) != v for k, v in wanted.items()):
            raise ValueError("probe_native_identity_metadata_changed")
    return {
        "protocol": PROTOCOL,
        "limits": LIMITS,
        "sources": {n: sha(root / n) for n in SOURCES},
        "cases": cases(root),
        "original_argv": template(root),
        "specification": specification("item_first"),
        "environment": environment(),
        "native_model_sha256_previously_verified": HASHES,
        "native_model_stat": {n: os.stat(MODEL_DIR / n).st_mtime_ns for n in HASHES},
        "runtime_sha256": sha(RUNTIME),
        "libmtmd_sha256": sha(RUNTIME.parent / "libmtmd.so.0.7.0"),
        "cached_cli_source_sha256": sha(root / "data/cache/llama-cpp/b11716/mtmd-cli.cpp"),
    }


def prepare(root=ROOT):
    folder = root / QUEUE
    if folder.exists():
        raise ValueError("probe_single_queue_already_prepared")
    config = configuration(root)
    plan = {
        "configuration": config,
        "configuration_sha256": digest(config),
        "technical_release_required": True,
    }
    plan["plan_sha256"] = digest(plan)
    folder.mkdir(parents=True, mode=0o700)
    write(folder / "plan.json", plan, exclusive=True)
    write(
        folder / "checkpoint.json",
        {"calls": 0, "operations": [], "sealed": False, "elapsed_seconds": 0.0},
        exclusive=True,
    )
    return plan


def release(folder, plan):
    path = folder / "technical-release.json"
    if path.is_symlink() or path.stat().st_size > 16384:
        raise ValueError("probe_technical_release_required")
    body = json.loads(path.read_bytes())
    if (
        body.get("plan_sha256") != plan["plan_sha256"]
        or body.get("configuration_sha256") != plan["configuration_sha256"]
        or body.get("decision") != "released_for_this_encoder_probe_only"
        or body.get("reviewer_thread_id") != "01a15713-2572-7544-8329-c229ea2ff0f5"
        or not body.get("source_message_id")
        or type(body.get("literal_message")) is not str
        or not body["literal_message"]
        or body.get("literal_message_sha256")
        != hashlib.sha256(body["literal_message"].encode()).hexdigest()
    ):
        raise ValueError("probe_technical_release_required")
    return sha(path)


def workers():
    own = {os.getpid(), *(p.pid for p in psutil.Process().parents())}
    found = []
    for process in psutil.process_iter(["pid", "name", "cmdline"]):
        if process.pid in own:
            continue
        try:
            name = process.info["name"] or ""
            args = process.info["cmdline"] or []
            if name.startswith("llama-") or any(
                a.startswith(
                    (
                        "scripts.demo_",
                        "scripts.vlm_",
                        "scripts.explanation_worker",
                        "scripts.production_candidate_worker",
                        "galaxies_orchestration",
                    )
                )
                for a in args
            ):
                found.append(process.pid)
        except psutil.NoSuchProcess:
            continue
    return found


def execute(root=ROOT):
    folder = root / QUEUE
    if folder.is_symlink() or any(p.is_symlink() for p in folder.parents):
        raise ValueError("probe_symlink_queue_forbidden")
    with (folder / ".lock").open("a+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        plan = json.loads((folder / "plan.json").read_bytes())
        state = json.loads((folder / "checkpoint.json").read_bytes())
        if (
            state != {"calls": 0, "operations": [], "sealed": False, "elapsed_seconds": 0.0}
            or (folder / "started.json").exists()
        ):
            raise ValueError("probe_consumed_or_uncertain_no_reentry")
        if (
            digest({k: v for k, v in plan.items() if k != "plan_sha256"}) != plan["plan_sha256"]
            or digest(plan["configuration"]) != plan["configuration_sha256"]
            or plan["configuration"] != configuration(root)
        ):
            raise ValueError("probe_plan_or_identity_changed")
        clearance = release(folder, plan)
        started = time.monotonic()
        write(
            folder / "started.json",
            {
                "plan_sha256": plan["plan_sha256"],
                "technical_release_sha256": clearance,
                "uncertain_seconds_upper_bound": 180,
            },
            exclusive=True,
        )
        error = None
        try:
            if workers():
                raise ProbeStop("concurrent_worker")
            (root / "data/private/media-temp").mkdir(parents=True, exist_ok=True, mode=0o700)
            for index, case in enumerate(plan["configuration"]["cases"], 1):
                work = Path(
                    tempfile.mkdtemp(
                        prefix="galaxies-encoder-probe-", dir=root / "data/private/media-temp"
                    )
                )
                cleanup_allowed = True
                try:
                    image = work / "crop.png"
                    schema = work / "schema.json"
                    if index == 1:
                        source = root / case["sheet_path"]
                        if sha(source) != case["sheet_sha256"]:
                            raise ValueError("probe_sheet_changed")
                        with Image.open(source) as sheet:
                            if (
                                sheet.mode != "RGB"
                                or sheet.size != (1280, 360)
                                or case["source_frame"] != 1
                            ):
                                raise ProbeStop("frozen_sheet_geometry_changed")
                            sheet.crop((0, 25, 320, 355)).save(image)
                    else:
                        Image.new("RGB", (320, 330), "white").save(image)
                    if sha(image) != case["png_sha256"]:
                        raise ValueError("probe_pixels_changed")
                    schema.write_text(json.dumps(specification("item_first")["schema"]))
                    if (
                        configuration(root) != plan["configuration"]
                        or release(folder, plan) != clearance
                    ):
                        raise ValueError("probe_identity_before_dispatch_changed")
                    remaining = 180 - (time.monotonic() - started) - 5
                    if remaining <= 0:
                        raise TimeoutError("probe_global_budget")

                    def reserve(index=index, case=case):
                        if state["calls"] != index - 1 or index > 2:
                            raise ValueError("probe_call_budget")
                        write(
                            folder / f"reservation-{index}.json",
                            {
                                "plan_sha256": plan["plan_sha256"],
                                "input_png_sha256": case["png_sha256"],
                                "number": index,
                            },
                            exclusive=True,
                        )
                        state["calls"] = index
                        state["elapsed_seconds"] = 180
                        state["operations"].append(
                            {"number": index, "status": "reserved_uncertain"}
                        )
                        write(folder / "checkpoint.json", state)

                    result = capture(
                        command(plan["configuration"]["original_argv"], image, schema),
                        seconds=min(180, remaining),
                        reserve=reserve,
                    )
                    cleanup_allowed = result["cleanup_confirmed"]
                    # Always persist sanitized observations before removing this owned scratch.
                    write(
                        folder / f"result-{index}.json",
                        {
                            "plan_sha256": plan["plan_sha256"],
                            "input_png_sha256": case["png_sha256"],
                            "source_seconds": case["seconds"],
                            "observation": result,
                        },
                        exclusive=True,
                    )
                    if sha(image) != case["png_sha256"]:
                        raise ValueError("probe_pixels_after_call_changed")
                    state["operations"][-1]["status"] = "completed"
                    write(folder / "checkpoint.json", state)
                    if result["stop_code"]:
                        raise ProbeStop(result["stop_code"])
                    if time.monotonic() - started > 180:
                        raise ProbeStop("global_deadline")
                finally:
                    if cleanup_allowed:
                        shutil.rmtree(work)
                    else:
                        state["preserved_scratch_cleanup_unconfirmed"] = str(work.relative_to(root))
        except BaseException as caught:  # noqa: BLE001 -- seal once even on cancellation
            error = caught
        finally:
            state.update(
                sealed=True,
                elapsed_seconds=time.monotonic() - started,
                stop_code=error.code
                if isinstance(error, ProbeStop)
                else type(error).__name__
                if error
                else "scope_completed",
                candidates=[],
                released_fields=[],
                test_opened=False,
                m1_changed=False,
            )
            write(folder / "checkpoint.json", state)
        if error:
            raise error
        return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["prepare", "inspect", "execute"])
    args = parser.parse_args()
    try:
        if args.operation == "prepare":
            p = prepare()
            result = {
                "plan_sha256": p["plan_sha256"],
                "configuration_sha256": p["configuration_sha256"],
            }
        elif args.operation == "inspect":
            result = json.loads((ROOT / QUEUE / "checkpoint.json").read_bytes())
        else:
            result = execute()
    except Exception as error:  # noqa: BLE001 -- CLI must never print private exception values
        result = {"status": "stopped", "error_type": type(error).__name__}
    print(json.dumps(result))


if __name__ == "__main__":
    main()

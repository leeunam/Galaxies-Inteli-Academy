"""Bounded operator CLI for the reviewed trio; execution is disabled by default.

No download, media inspection or model import occurs for inspect/plan checks.
Acquisition and native analysis require a matching, code-bound release receipt.
Recovered INPUTS are separate from disposable extraction scratch.
"""

from __future__ import annotations

import argparse
import base64
import fcntl
import json
import math
import os
import selectors
import shutil
import signal
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from scripts.demo_recovery_policy import (
    ROOT,
    RecoveryError,
    digest,
    discard_allowed,
    exclusive_json,
    fsync_dir,
    load_operator_plan,
    private_path,
    read_json,
    reserve_phase,
    unique_pairs,
)


def download_command(source, directory, python, ffmpeg, profile):
    common = "best[height<=720][vcodec!=none][acodec!=none]"
    formats = (
        "best[ext=mp4][height<=720][vcodec!=none][acodec!=none]/best[ext=webm][height<=720][vcodec!=none][acodec!=none]"
        if profile == "single_file"
        else common + "/bestvideo[height<=720]+bestaudio"
    )
    return [
        str(python),
        "-B",
        "-m",
        "yt_dlp",
        "--ignore-config",
        "--no-plugin-dirs",
        "--no-remote-components",
        "--no-playlist",
        "--no-cache-dir",
        "--no-progress",
        "--no-warnings",
        "--js-runtimes",
        "node",
        "--socket-timeout",
        "20",
        "--retries",
        "0",
        "--fragment-retries",
        "0",
        "--extractor-retries",
        "0",
        "--max-filesize",
        "32M",
        "--limit-rate",
        "5M",
        "--match-filters",
        "duration <= 60 & !is_live",
        "--format",
        formats,
        "--ffmpeg-location",
        str(ffmpeg),
        "--merge-output-format",
        "mkv",
        "--output",
        str(directory / "media.%(ext)s"),
        "--print",
        'after_move:{"id":%(id)j,"webpage_url":%(webpage_url)j,"duration":%(duration)j,"ext":%(ext)j}',
        "--",
        source["source_url"],
    ]


def remux_command(ffmpeg, source, destination):
    # No scaling, resampling or encoder is allowed in this proposed branch.
    return [
        str(ffmpeg),
        "-nostdin",
        "-loglevel",
        "error",
        "-n",
        "-i",
        str(source),
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        "-f",
        "mp4",
        str(destination),
    ]


def download_identity(raw, source):
    try:
        value = json.loads(raw, object_pairs_hook=unique_pairs)
    except (ValueError, UnicodeError):
        raise RecoveryError("invalid_download_projection") from None
    if (
        type(value) is not dict
        or set(value) != {"id", "webpage_url", "duration", "ext"}
        or value["id"] != source["video_id"]
        or value["webpage_url"] != source["source_url"]
        or type(value["duration"]) not in (int, float)
        or not math.isfinite(value["duration"])
        or not 0 < value["duration"] <= 60
        or value["ext"] not in {"mp4", "webm", "mkv"}
    ):
        raise RecoveryError("download_identity_mismatch")
    return value


def input_manifest(folder, sources, max_bytes):
    rows = []
    for source in sources:
        found = [
            p for p in Path(folder).glob(source["alias"] + ".*") if p.suffix in {".mp4", ".webm"}
        ]
        if len(found) != 1:
            raise RecoveryError("one_input_per_source_required")
        path = found[0]
        if path.is_symlink() or not path.is_file() or not 0 < path.stat().st_size <= max_bytes:
            raise RecoveryError("invalid_recovered_input")
        rows.append(
            {
                "alias": source["alias"],
                "relative_path": path.name,
                "size_bytes": path.stat().st_size,
                "sha256": digest(path),
            }
        )
    if len({row["sha256"] for row in rows}) != 3:
        raise RecoveryError("distinct_media_bytes_required")
    return rows


def literal_environment(tmpdir):
    return {
        "PATH": os.defpath,
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "HF_HUB_DISABLE_TELEMETRY": "1",
        "LANGSMITH_TRACING": "false",
        "LANGCHAIN_TRACING_V2": "false",
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "4",
        "MKL_NUM_THREADS": "1",
        "TOKENIZERS_PARALLELISM": "false",
        "CUDA_VISIBLE_DEVICES": "",
        "TMPDIR": str(tmpdir),
    }


def sandbox_command(base, env, *, offline):
    command = [
        "/usr/bin/bwrap",
        "--ro-bind",
        "/",
        "/",
        "--bind",
        str(ROOT),
        str(ROOT),
        "--dev",
        "/dev",
        "--die-with-parent",
        "--clearenv",
    ]
    if offline:
        target = ROOT / "data/cache/huggingface"
        target.mkdir(parents=True, exist_ok=True)
        command += [
            "--unshare-net",
            "--ro-bind",
            base["local_analysis_configuration"]["readonly_hf_cache_bind_source"],
            str(target),
        ]
    for key, value in env.items():
        command += ["--setenv", key, value]
    return command + [
        "--chdir",
        str(ROOT),
        str(ROOT / ".venv/bin/python"),
        "-B",
        "-m",
        "scripts.demo_recovery_process",
    ]


def guarded_command(run, label, argv, plan, base, timeout, *, offline):
    folder = run / "scratch" / label
    folder.mkdir(mode=0o700)
    env = literal_environment(folder)
    job = {
        "argv": argv,
        "cwd": str(ROOT),
        "env": env,
        "timeout": timeout,
        "io_bytes": plan["budgets"]["io_bytes"],
        "file_bytes": plan["budgets"]["file_bytes"],
        "workspace": str(run),
        "workspace_bytes": plan["budgets"]["workspace_bytes"],
        "rss_bytes": plan["budgets"]["rss_bytes"],
        "lease": str(folder / "process-lease.json"),
    }
    exclusive_json(run / "receipts" / (label + "-job.json"), job)
    process = None
    raw = bytearray()
    started = time.monotonic()
    result = None
    try:
        process = subprocess.Popen(
            sandbox_command(base, env, offline=offline),
            cwd=ROOT,
            env={"PATH": os.defpath},
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        encoded = json.dumps(job, allow_nan=False).encode()
        process.stdin.write(encoded)
        process.stdin.close()
        selector = selectors.DefaultSelector()
        os.set_blocking(process.stdout.fileno(), False)
        selector.register(process.stdout, selectors.EVENT_READ)
        try:
            while selector.get_map():
                if time.monotonic() - started > timeout + 25:
                    raise RecoveryError("supervisor_deadline_unconfirmed")
                for key, _ in selector.select(0.1):
                    chunk = os.read(key.fd, min(4096, 200001 - len(raw)))
                    if not chunk:
                        selector.unregister(key.fileobj)
                    else:
                        raw.extend(chunk)
                        if len(raw) > 200000:
                            raise RecoveryError("supervisor_output_limit")
        finally:
            selector.close()
            process.stdout.close()
        process.wait(timeout=5)
        if process.returncode != 0:
            raise RecoveryError("supervisor_failed_unconfirmed")
        result = json.loads(raw, object_pairs_hook=unique_pairs)
        if (
            type(result) is not dict
            or type(result.get("cleanup_confirmed")) is not bool
            or result.get("code")
            not in {
                "completed",
                "timeout",
                "output_limit",
                "rss_limit",
                "workspace_limit",
                "cancelled_consumed",
                "authentication_or_bot_check",
                "access_denied_or_rate_limited",
                "source_unavailable",
                "child_failed",
                "startup_or_monitor_failure_consumed",
                "startup_failed_consumed",
            }
        ):
            raise RecoveryError("supervisor_protocol_unconfirmed")
        stdout = base64.b64decode(result["stdout_b64"], validate=True)
        if len(stdout) > plan["budgets"]["io_bytes"]:
            raise RecoveryError("supervisor_protocol_unconfirmed")
        private_result = {key: value for key, value in result.items() if key != "stdout_b64"}
        exclusive_json(run / "receipts" / (label + "-result.json"), private_result)
        if result["cleanup_confirmed"] is not True:
            raise RecoveryError("cleanup_unconfirmed_keep_scratch")
        if result["code"] != "completed":
            raise RecoveryError(result["code"])
        return stdout
    finally:
        if process is not None and process.poll() is None:
            # Ask the dedicated subreaper to stop/reap its jobs. A forced death
            # never grants permission to delete an unacknowledged scratch tree.
            process.terminate()
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def quiescent_receipts(run):
    jobs = sorted((run / "receipts").glob("*-job.json"))
    return all(
        (run / "receipts" / path.name.replace("-job.json", "-result.json")).is_file()
        and read_json(run / "receipts" / path.name.replace("-job.json", "-result.json"))[
            "cleanup_confirmed"
        ]
        is True
        for path in jobs
    )


def clean_scratch(run):
    if not quiescent_receipts(run):
        raise RecoveryError("cleanup_unconfirmed_keep_scratch")
    scratch = run / "scratch"
    if scratch.is_symlink():
        raise RecoveryError("scratch_symlink_forbidden")
    shutil.rmtree(scratch)
    scratch.mkdir(mode=0o700)
    # INPUTS are deliberately outside this deletion boundary.


@contextmanager
def run_lock(run):
    descriptor = os.open(run / ".operator.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    except BlockingIOError:
        raise RecoveryError("other_run_writer") from None
    finally:
        os.close(descriptor)


def remaining(run, plan):
    intent = read_json(run / "intent.json")
    if intent["boot_id"] != Path("/proc/sys/kernel/random/boot_id").read_text().strip():
        raise RecoveryError("different_boot_uncertain_run")
    value = plan["budgets"]["overall_seconds"] - (time.monotonic() - intent["started_monotonic"])
    value = min(
        value, datetime.fromisoformat(plan["input_retention_until"]).timestamp() - time.time()
    )
    if value <= 0:
        raise RecoveryError("overall_deadline")
    return value


def no_other_model_jobs():
    """Resource-slot guard; reports no command line, PID, payload or path."""
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid():
            continue
        try:
            args = (proc / "cmdline").read_bytes().split(b"\0")
        except OSError:
            continue
        if args and Path(os.fsdecode(args[0])).name.startswith("llama-"):
            raise RecoveryError("model_resource_slot_busy")
        if any(
            item.startswith(
                (
                    b"scripts.candidate_features",
                    b"scripts.vlm_",
                    b"scripts.explanation_worker",
                    b"galaxies_orchestration.integrated_",
                )
            )
            for item in args
        ):
            raise RecoveryError("model_resource_slot_busy")


def acquire(run, plan, base, plan_sha):
    no_other_model_jobs()
    if run.exists():
        raise RecoveryError("run_directory_consumed")
    expires = datetime.fromisoformat(plan["input_retention_until"]).timestamp()
    if not 0 < expires - time.time() <= 48 * 3600:
        raise RecoveryError("retention_window_outside_review_scope")
    if shutil.disk_usage(run.parent).free < plan["budgets"]["minimum_free_bytes"]:
        raise RecoveryError("insufficient_free_disk")
    if shutil.which("node", path=os.defpath) is None:
        raise RecoveryError("local_node_unavailable_no_install")
    ffmpeg = (
        ROOT
        / ".venv/lib/python3.11/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2"
    )
    if not ffmpeg.is_file():
        raise RecoveryError("local_ffmpeg_unavailable_no_install")
    run.mkdir(mode=0o700)
    fsync_dir(run.parent)
    for name in ("inputs", "scratch", "receipts"):
        (run / name).mkdir(mode=0o700)
    exclusive_json(
        run / "intent.json",
        {
            "plan_sha256": plan_sha,
            "started_monotonic": time.monotonic(),
            "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
            "input_retention_until": plan["input_retention_until"],
        },
    )
    with run_lock(run):
        reserve_phase(run, "acquire", plan_sha)
        stage_deadline = time.monotonic() + plan["budgets"]["acquisition_seconds"]
        for source in plan["sources"]:
            alias = source["alias"]
            attempt = run / "scratch" / (alias + "-download")
            attempt.mkdir(mode=0o700)
            exclusive_json(
                run / "receipts" / (alias + "-reserved.json"),
                {
                    "state": "consumed_before_spawn",
                    "plan_sha256": plan_sha,
                    "alias": alias,
                },
            )
            deadline = min(
                stage_deadline, time.monotonic() + plan["budgets"]["per_acquisition_seconds"]
            )
            duration = min(deadline - time.monotonic(), remaining(run, plan))
            if duration <= 0:
                raise RecoveryError("acquisition_deadline")
            command = download_command(
                source, attempt, ROOT / ".venv/bin/python", ffmpeg, plan["format_policy"]
            )
            raw = guarded_command(
                run, alias + "-network", command, plan, base, duration, offline=False
            )
            identity = download_identity(raw, source)
            found = [p for p in attempt.glob("media.*") if p.suffix in {".mp4", ".webm", ".mkv"}]
            if len(found) != 1 or found[0].is_symlink():
                raise RecoveryError("download_no_unique_file")
            media = found[0]
            if identity["ext"] != media.suffix[1:]:
                raise RecoveryError("download_container_identity_mismatch")
            remuxed = False
            if media.suffix == ".mkv":
                if plan["format_policy"] != "single_or_copy_remux":
                    raise RecoveryError("remux_not_reviewed")
                destination = attempt / "copy.mp4"
                duration = min(
                    plan["budgets"]["remux_seconds"],
                    deadline - time.monotonic(),
                    remaining(run, plan),
                )
                if duration <= 0:
                    raise RecoveryError("acquisition_deadline")
                guarded_command(
                    run,
                    alias + "-copy-remux",
                    remux_command(ffmpeg, media, destination),
                    plan,
                    base,
                    duration,
                    offline=True,
                )
                media = destination
                remuxed = True
            if not 0 < media.stat().st_size <= plan["budgets"]["file_bytes"]:
                raise RecoveryError("recovered_file_limit")
            destination = run / "inputs" / (alias + media.suffix)
            # Destination is fresh and private; never overwrite another input.
            with media.open("rb") as src:
                descriptor = os.open(
                    destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600
                )
                with os.fdopen(descriptor, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                    dst.flush()
                    os.fsync(dst.fileno())
            fsync_dir(destination.parent)
            exclusive_json(
                run / "receipts" / (alias + "-acquired.json"),
                {
                    "alias": alias,
                    "canonical_source_confirmed": True,
                    "copy_remux": remuxed,
                    "new_media_sha256": digest(destination),
                    "size_bytes": destination.stat().st_size,
                    "historical_byte_identity_claimed": False,
                },
            )
            clean_scratch(run)
        manifest = input_manifest(run / "inputs", plan["sources"], plan["budgets"]["file_bytes"])
        exclusive_json(run / "acquired.json", {"plan_sha256": plan_sha, "inputs": manifest})
    return {
        "status": "fixed_source_files_acquired",
        "input_count": 3,
        "native_media_validation_pending": True,
        "inputs_retained": True,
    }


def positive_native(result):
    if type(result) is not dict or "analysis" not in result:
        return False
    analysis, orchestration = result["analysis"], result.get("orchestration", {})
    return (
        analysis.get("status") == "m1_prediction_available"
        and len(analysis.get("candidates", [])) == 3
        and all(
            row.get("prediction", {}).get("status") == "estimated" for row in analysis["candidates"]
        )
        and orchestration.get("native_feature_handoff") is True
        and orchestration.get("stategraph_executed") is True
        and orchestration.get("explainer_subgraph_executed") is True
        and orchestration.get("selector_kind") == "absent"
        and orchestration.get("real_provider_verified") is False
        and result.get("evidence_packet") is not None
    )


def analyze(run, plan, base, plan_sha):
    no_other_model_jobs()
    with run_lock(run):
        intent = read_json(run / "intent.json")
        acquired = read_json(run / "acquired.json")
        if intent["plan_sha256"] != plan_sha or acquired["plan_sha256"] != plan_sha:
            raise RecoveryError("run_plan_mismatch")
        manifest = input_manifest(run / "inputs", plan["sources"], plan["budgets"]["file_bytes"])
        if manifest != acquired["inputs"]:
            raise RecoveryError("input_bytes_changed")
        reserve_phase(run, "analyze", plan_sha)
        config = base["local_analysis_configuration"]
        native = {
            "run_dir": str(run),
            "inputs": manifest,
            "campaign_id": "demo-recuperada-beleza-v1",
            "graph_python": str(ROOT / "orchestration/.venv/bin/python"),
            "model_dir": config["m1_model_dir"],
            "cohort_dir": config["m1_cohort_dir"],
            "evidence_root": config["training_evidence_root"],
            "analysis_seconds": plan["budgets"]["analysis_seconds"],
            "previous_duration_seconds": {
                source["alias"]: source["previous_media_properties"]["duration_seconds"]
                for source in base["sources"]
            },
        }
        exclusive_json(run / "native-config.json", native)
        results = {}
        for route in ("prepare", "python", "mcp"):
            timeout = min(
                120 if route == "prepare" else plan["budgets"]["analysis_seconds"],
                remaining(run, plan),
            )
            command = [
                str(ROOT / ".venv/bin/python"),
                "-B",
                "-m",
                "scripts.demo_recovery_native",
                route,
                "--config",
                str(run / "native-config.json"),
            ]
            raw = guarded_command(
                run, "native-" + route, command, plan, base, timeout, offline=True
            )
            result = json.loads(raw, object_pairs_hook=unique_pairs)
            if type(result) is not dict or "recovery_error" in result:
                raise RecoveryError("native_stage_failed")
            exclusive_json(run / ("native-" + route + ".json"), result)
            results[route] = result
        if results["python"] != results["mcp"]:
            raise RecoveryError("native_python_mcp_mismatch")
        if (
            input_manifest(run / "inputs", plan["sources"], plan["budgets"]["file_bytes"])
            != manifest
        ):
            raise RecoveryError("input_bytes_changed")
        clean_scratch(run)
        summary = {
            "status": "native_local_parity",
            "input_count": 3,
            "all_predictions_available": positive_native(results["python"]),
            "real_provider_verified": False,
            "adherence_status": "not_evaluated",
            "python_mcp_exact_parity": True,
            "inputs_retained_for_handoff": True,
            "temporary_extraction_scratch_removed": True,
        }
        exclusive_json(run / "analysis-summary.json", summary)
    return summary


def handoff(run, plan, plan_sha):
    with run_lock(run):
        acquired = read_json(run / "acquired.json")
        if acquired["plan_sha256"] != plan_sha or not quiescent_receipts(run):
            raise RecoveryError("handoff_not_quiescent")
        if not (run / "request.json").is_file() or not (run / "analysis-summary.json").is_file():
            raise RecoveryError("handoff_analysis_not_prepared")
        manifest = input_manifest(run / "inputs", plan["sources"], plan["budgets"]["file_bytes"])
        if acquired["inputs"] != manifest:
            raise RecoveryError("input_bytes_changed")
        if time.time() >= datetime.fromisoformat(plan["input_retention_until"]).timestamp():
            raise RecoveryError("input_retention_expired")
        reserve_phase(run, "handoff", plan_sha)
        exclusive_json(
            run / "handoff.json",
            {
                "inputs": manifest,
                "inputs_root": str(run / "inputs"),
                "request_file": str(run / "request.json"),
                "analysis_summary_file": str(run / "analysis-summary.json"),
                "input_retention_until": plan["input_retention_until"],
                "delivery_does_not_mean_demo_completed": True,
                "discard_only_after_demo_completed_or_expiry": True,
            },
        )
    return {"status": "private_handoff_ready", "inputs_retained": True, "input_count": 3}


def discard(run, plan, plan_sha, *, demo_completed):
    with run_lock(run):
        if read_json(run / "intent.json")["plan_sha256"] != plan_sha:
            raise RecoveryError("run_plan_mismatch")
        expires = datetime.fromisoformat(plan["input_retention_until"]).timestamp()
        if not quiescent_receipts(run) or not discard_allowed(
            handoff_recorded=(run / "handoff.json").is_file(),
            demo_completed=demo_completed,
            now=time.time(),
            expires=expires,
        ):
            raise RecoveryError("input_discard_not_allowed")
        reserve_phase(run, "discard", plan_sha)
        clean_scratch(run)
        inputs = run / "inputs"
        if inputs.is_symlink():
            raise RecoveryError("input_symlink_forbidden")
        shutil.rmtree(inputs)
        exclusive_json(run / "discard.json", {"inputs_removed": True, "confirmed_quiescent": True})
    return {"status": "demo_inputs_removed"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["inspect", "acquire", "analyze", "handoff", "discard"])
    parser.add_argument("--plan", type=Path, required=True)
    parser.add_argument("--base-plan", type=Path, required=True)
    parser.add_argument("--release", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--demo-completed", action="store_true")
    args = parser.parse_args()
    os.umask(0o077)

    def cancelled(_signum, _frame):
        raise RecoveryError("operator_cancelled_consumed")

    signal.signal(signal.SIGTERM, cancelled)
    try:
        plan, base, plan_sha, _ = load_operator_plan(
            args.plan, args.base_plan, args.release, args.phase
        )
        if args.phase == "inspect":
            result = {
                "status": "proposal_inspected",
                "sources": 3,
                "execution_released": False,
                "plan_sha256": plan_sha,
                "format_policy": plan["format_policy"],
                "input_retention_until": plan["input_retention_until"],
            }
        else:
            if args.run_dir is None:
                raise RecoveryError("new_run_directory_required")
            run = private_path(args.run_dir)
            if args.phase == "acquire":
                result = acquire(run, plan, base, plan_sha)
            elif args.phase == "analyze":
                result = analyze(run, plan, base, plan_sha)
            elif args.phase == "handoff":
                result = handoff(run, plan, plan_sha)
            else:
                result = discard(run, plan, plan_sha, demo_completed=args.demo_completed)
        print(json.dumps(result, allow_nan=False))
    except RecoveryError as exc:
        print(json.dumps({"status": "stopped_do_not_repeat", "code": str(exc)}))
        raise SystemExit(1) from None
    except KeyboardInterrupt:
        print('{"status":"stopped_do_not_repeat","code":"operator_cancelled_consumed"}')
        raise SystemExit(1) from None
    except Exception:  # noqa: BLE001 - operator paths and exceptions are private
        print('{"status":"stopped_do_not_repeat","code":"local_recovery_failed"}')
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()

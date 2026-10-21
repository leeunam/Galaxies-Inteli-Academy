"""Recover only the frozen revealed pair; no model or automatic release path."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import time
from datetime import datetime
from importlib.metadata import version
from pathlib import Path

from scripts import demo_recovery as boundary
from scripts.demo_recovery_policy import (
    RecoveryError,
    digest,
    exclusive_json,
    fsync_dir,
    private_path,
    read_json,
    unique_pairs,
)

ROOT = Path(__file__).resolve().parents[1]
QUEUE = "data/private/issue-4-vlm-native-source-recovery-v1"
PROPOSAL = "data/private/issue-4-vlm-fonte-nativa-proposta-v1/plan.json"
PROPOSAL_SHA = "2ba897f61fedc9893bf7e85098f0fb0112924cbf4626bac475effabc19bbd246"
ROWS = "data/private/issue-4-vlm-produto-v9-recuperacao-v1/plan.json"
ROWS_SHA = "97b5d3e9f02478c578eac5a45c4524ba03f03ed66724f1646153bf0de267ee48"
PROTOCOL = "revealed-pair-native-source-recovery-v1"
RETENTION = "2026-10-21T23:59:00-03:00"
REVIEWER = "01a15713-2572-7544-8329-c229ea2ff0f5"
FFMPEG = ".venv/lib/python3.11/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2"
SOURCES = (
    "scripts/vlm_native_source_recovery.py",
    "scripts/vlm_native_source_frames.py",
    "tests/test_vlm_native_source_recovery.py",
    "docs/issue-4-vlm-fonte-nativa-preparacao.md",
    "uv.lock",
    "scripts/vlm_encoder_probe.py",
)
BUDGETS = {
    "file_bytes": 32 * 1024**2,
    "workspace_bytes": 128 * 1024**2,
    "rss_bytes": int(3.3 * 1024**3),
    "io_bytes": 65536,
    "overall_seconds": 420,
    "per_source_seconds": 180,
    "network_seconds": 80,
    "bridge_seconds": 20,
    "wrapper_margin_seconds": 50,
}


def json_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


def checked_pins(pins, root):
    for name, expected in pins.items():
        path = root / name
        if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
            raise RecoveryError("source_path_changed")
        if digest(path) != expected:
            raise RecoveryError("source_pin_changed")


def configuration(root=ROOT):
    from scripts.pilot_licensed_media import select_vlm_samples

    if digest(root / PROPOSAL) != PROPOSAL_SHA or digest(root / ROWS) != ROWS_SHA:
        raise RecoveryError("frozen_provenance_changed")
    proposal, rows = read_json(root / PROPOSAL), read_json(root / ROWS, limit=2**22)["rows"]
    checked_pins(proposal["source_files_sha256"], root)
    checked_pins(proposal["protected_files_sha256"], root)
    cases = []
    if [c["alias"] for c in proposal["cases"]] != ["positive", "negative"]:
        raise RecoveryError("fixed_pair_required")
    for case in proposal["cases"]:
        row = next(r for r in rows if r["sample_id"] == case["sample_id"])
        if (
            row["partition"] != "train"
            or row["properties"] != case["historical_properties"]
            or row["sheet_sha256"] != case["sheet_sha256"]
            or digest(root / case["sheet_path"]) != case["sheet_sha256"]
            or case["source_url"] != "https://www.youtube.com/watch?v=" + case["sample_id"]
        ):
            raise RecoveryError("fixed_training_identity_changed")
        cases.append(
            case
            | {
                "historical_selected_seconds": select_vlm_samples(
                    list(range(len(row["properties"]["sampled_frame_seconds"]))),
                    row["properties"],
                )[1],
                "row": {
                    k: row[k] for k in ("sample_id", "properties", "sheet_sha256", "sheet_recipe")
                },
            }
        )
    tools = {
        "python": root / ".venv/bin/python",
        "ffmpeg": root / FFMPEG,
        "node": Path("/usr/bin/node"),
        "bwrap": Path("/usr/bin/bwrap"),
    }
    packages = {name: version(name) for name in ("av", "Pillow", "numpy", "yt-dlp")}
    if any(
        c["historical_download_fingerprint"]["yt_dlp_version"] != packages["yt-dlp"] for c in cases
    ):
        raise RecoveryError("historical_downloader_version_changed")
    return {
        "protocol": PROTOCOL,
        "proposal_sha256": PROPOSAL_SHA,
        "rows_sha256": ROWS_SHA,
        "budgets": BUDGETS,
        "retention_until": RETENTION,
        "cases": cases,
        "sources_sha256": {
            **proposal["source_files_sha256"],
            **{n: digest(root / n) for n in SOURCES},
        },
        "tools_sha256": {n: digest(p) for n, p in tools.items()},
        "packages": packages,
        "generations": 0,
        "acquisition_attempts": 2,
        "retry_allowed": False,
    }


def prepare(root=ROOT):
    config = configuration(root)
    folder = private_path(root / QUEUE, root=root)
    folder.mkdir(mode=0o700, exist_ok=False)
    exclusive_json(
        folder / "plan.json", {"configuration": config, "configuration_sha256": json_digest(config)}
    )
    return {"status": "prepared_not_released", "plan_sha256": digest(folder / "plan.json")}


def load(root=ROOT):
    folder = private_path(root / QUEUE, root=root)
    plan = read_json(folder / "plan.json", limit=2**22)
    if plan["configuration"] != configuration(root) or plan["configuration_sha256"] != json_digest(
        plan["configuration"]
    ):
        raise RecoveryError("execution_configuration_changed")
    return plan, digest(folder / "plan.json")


def check_release(plan, plan_sha, root=ROOT):
    path = root / QUEUE / "technical-release.json"
    review = read_json(private_path(path, root=root), limit=16384)
    expected = {
        "protocol": PROTOCOL,
        "decision": "approved_for_two_source_recoveries_no_generation",
        "plan_sha256": plan_sha,
        "configuration_sha256": plan["configuration_sha256"],
        "execution_root_sha256": hashlib.sha256(str(root.resolve()).encode()).hexdigest(),
        "reviewer_thread_id": REVIEWER,
    }
    if set(review) != set(expected) | {
        "source_message_id",
        "literal_message",
        "literal_message_sha256",
    } or any(review[k] != v for k, v in expected.items()):
        raise RecoveryError("technical_release_required")
    text, source = review["literal_message"], review["source_message_id"]
    if (
        type(text) is not str
        or not 1 <= len(text) <= 8192
        or type(source) is not str
        or re.fullmatch(r"[A-Za-z0-9_-]{1,128}", source) is None
        or review["literal_message_sha256"] != hashlib.sha256(text.encode()).hexdigest()
    ):
        raise RecoveryError("technical_release_required")
    return digest(path)


def source_identity(case):
    return {"alias": case["alias"], "video_id": case["sample_id"], "source_url": case["source_url"]}


def downloaded_file(folder, identity):
    found = [p for p in folder.glob("media.*") if p.suffix in {".mp4", ".webm", ".mkv"}]
    if len(found) != 1 or found[0].is_symlink():
        raise RecoveryError("download_no_unique_file")
    media = found[0]
    if (
        media.suffix != "." + identity["ext"]
        or not 0 < media.stat().st_size <= BUDGETS["file_bytes"]
    ):
        raise RecoveryError("download_file_identity_or_size")
    return media


def resource_slot():
    from scripts.vlm_encoder_probe import workers

    if workers():
        raise RecoveryError("model_resource_slot_busy")


def accept_native(raw, case, work, media):
    from PIL import Image

    value = json.loads(raw, object_pairs_hook=unique_pairs)
    if (
        type(value) is dict
        and set(value) == {"error_code"}
        and value["error_code"]
        in {
            "historical_properties_mismatch",
            "historical_pts_mismatch",
            "historical_sheet_or_crop_mismatch",
            "native_geometry_changed",
            "exact_native_pts_missing",
            "native_pts_invalid",
            "native_bridge_failed",
        }
    ):
        raise RecoveryError(value["error_code"])
    expected = {
        "alias": case["alias"],
        "sheet_sha256": case["sheet_sha256"],
        "crop_sha256": case["png_sha256"],
        "properties_sha256": json_digest(case["historical_properties"]),
        "native_pts": case["seconds"],
        "native_size": [360, 640],
        "media_sha256": digest(media),
        "bridge_complete": True,
    }
    if (
        type(value) is not dict
        or set(value) != set(expected) | {"native_sha256"}
        or any(value[k] != v for k, v in expected.items())
        or value["bridge_complete"] is not True
    ):
        raise RecoveryError("native_bridge_failed")
    path = work / "native.png"
    if (
        path.is_symlink()
        or not 0 < path.stat().st_size <= BUDGETS["file_bytes"]
        or digest(path) != value["native_sha256"]
    ):
        raise RecoveryError("native_output_changed")
    with Image.open(path) as image:
        if image.mode != "RGB" or image.size != (360, 640):
            raise RecoveryError("native_geometry_changed")
    return path, value


def acquire(root=ROOT, *, runner=None, clock=None, wall=None):
    runner = boundary.guarded_command if runner is None else runner
    clock, wall = clock or time.monotonic, wall or time.time
    started = clock()
    plan, plan_sha = load(root)
    review_sha = check_release(plan, plan_sha, root)
    expires = datetime.fromisoformat(RETENTION).timestamp()
    if wall() >= expires:
        raise RecoveryError("retention_expired")
    resource_slot()
    run = private_path(root / QUEUE / "run", root=root)
    if shutil.disk_usage(run.parent).free < 1024**3:
        raise RecoveryError("insufficient_free_disk")
    run.mkdir(mode=0o700, exist_ok=False)  # presence consumes even an interrupted startup
    for name in ("scratch", "frames", "receipts"):
        (run / name).mkdir(mode=0o700)
    exclusive_json(
        run / "intent.json",
        {
            "plan_sha256": plan_sha,
            "technical_release_sha256": review_sha,
            "started_monotonic": started,
            "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        },
    )
    verified, attempts, reason, cleanup = [], 0, "completed", False
    inherited = {"budgets": BUDGETS}
    base = {
        "local_analysis_configuration": {
            "readonly_hf_cache_bind_source": str(root / "data/cache/huggingface")
        }
    }

    def remaining(deadline):
        return min(deadline - clock(), started + 420 - clock(), expires - wall())

    try:
        with boundary.run_lock(run):
            for case in plan["configuration"]["cases"]:
                alias = case["alias"]
                deadline = clock() + 180
                current, checksum = load(root)
                if (
                    current != plan
                    or checksum != plan_sha
                    or check_release(current, checksum, root) != review_sha
                ):
                    raise RecoveryError("execution_configuration_changed")
                resource_slot()
                # Successful download uses up to30s wrapper overhead; reserve
                # another20s+50s for bridge and its uncertain supervisor teardown.
                useful = min(80, remaining(deadline) - 100)
                if useful <= 0:
                    raise RecoveryError("overall_deadline")
                # A fresh durable reservation precedes even the downloader spawn.
                exclusive_json(
                    run / "receipts" / (alias + "-reserved.json"),
                    {
                        "plan_sha256": plan_sha,
                        "alias": alias,
                        "state": "consumed_before_spawn",
                        "retry_allowed": False,
                    },
                )
                attempts += 1
                work = run / "scratch" / (alias + "-download")
                work.mkdir(mode=0o700)
                command = boundary.download_command(
                    source_identity(case),
                    work,
                    root / ".venv/bin/python",
                    root / FFMPEG,
                    "single_or_copy_remux",
                )
                raw = runner(
                    run, alias + "-network", command, inherited, base, useful, offline=False
                )
                identity = boundary.download_identity(raw, source_identity(case))
                media = downloaded_file(work, identity)
                useful = min(20, remaining(deadline) - 50)
                if useful <= 0:
                    raise RecoveryError("overall_deadline")
                command = [
                    str(root / ".venv/bin/python"),
                    "-B",
                    "-m",
                    "scripts.vlm_native_source_frames",
                    "--plan-sha256",
                    plan_sha,
                    "--alias",
                    alias,
                ]
                raw = runner(run, alias + "-bridge", command, inherited, base, useful, offline=True)
                if remaining(deadline) <= 0:
                    raise RecoveryError("overall_deadline")
                native, observation = accept_native(
                    raw, case, run / "scratch" / (alias + "-bridge"), media
                )
                exclusive_json(run / "receipts" / (alias + "-bridge.json"), observation)
                target = run / "frames" / (alias + ".png")
                fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                try:
                    with os.fdopen(fd, "wb") as output:
                        output.write(native.read_bytes())
                        output.flush()
                        os.fsync(output.fileno())
                    if digest(target) != observation["native_sha256"]:
                        raise RecoveryError("native_copy_changed")
                    fsync_dir(target.parent)
                except BaseException:
                    target.unlink(missing_ok=True)  # only this exclusive, newly created output
                    raise
                verified.append({"alias": alias, "native_sha256": digest(target)})
                boundary.clean_scratch(run)
            if clock() - started > 420:
                raise RecoveryError("overall_deadline")
    except BaseException as exc:  # noqa: BLE001 -- consume cancellations, never persist raw errors
        reason = str(exc) if type(exc) is RecoveryError else "local_failure_consumed"
    finally:
        cleanup = boundary.quiescent_receipts(run)
        if cleanup:
            try:
                boundary.clean_scratch(run)
            except BaseException:  # noqa: BLE001 -- retain scratch on uncertain cleanup
                cleanup, reason = False, "cleanup_unconfirmed_keep_scratch"
        else:
            reason = "cleanup_unconfirmed_keep_scratch"
        result = {
            "protocol": PROTOCOL,
            "plan_sha256": plan_sha,
            "state": "sealed",
            "status": "completed" if reason == "completed" else "stopped",
            "stop_code": reason,
            "acquisition_attempts": attempts,
            "verified_frames": verified,
            "cleanup_confirmed": cleanup,
            "elapsed_seconds": clock() - started,
            "retention_until": RETENTION,
            "generations": 0,
            "retry_allowed": False,
            "test_opened": False,
            "m1_changed": False,
        }
        exclusive_json(run / "result.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "inspect", "acquire"])
    args = parser.parse_args()
    os.umask(0o077)
    try:
        if args.phase == "prepare":
            value = prepare()
        elif args.phase == "inspect":
            plan, checksum = load()
            value = {
                "status": "inspected_not_released",
                "plan_sha256": checksum,
                "configuration_sha256": plan["configuration_sha256"],
                "acquisitions": 0,
                "generations": 0,
            }
        else:
            value = acquire()
        print(json.dumps(value, allow_nan=False))
    except Exception:  # noqa: BLE001 -- never print paths, source identities or arbitrary exceptions
        print('{"status":"stopped_do_not_repeat","code":"native_recovery_guard_failed"}')
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()

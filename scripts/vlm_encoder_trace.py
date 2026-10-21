"""Single frozen positive at trace verbosity, separate from the sealed info probe."""

import argparse
import fcntl
import json
import shutil
import tempfile
import time
from pathlib import Path

from PIL import Image

from scripts import vlm_encoder_probe as base

ROOT = base.ROOT
QUEUE = "data/private/issue-4-vlm-encoder-trace-v1"
SOURCES = (
    "scripts/vlm_encoder_trace.py",
    "tests/test_vlm_encoder_trace.py",
    "docs/issue-4-vlm-encoder-trace-protocolo.md",
)
LIMITS = {**base.LIMITS, "calls": 1, "seconds": 90, "white_calls": 0}


def command(original, image, schema):
    argv = base.command(original, image, schema)
    position = argv.index("--verbosity") + 1
    assert argv[position] == "3"
    argv[position] = "4"
    return argv


def configuration(root=ROOT):
    previous = root / base.QUEUE
    if (
        base.sha(previous / "checkpoint.json")
        != "a43409e86baa4f8046ba985d5768f36b1a1ba9aa108950ecae41de30c6338dff"
        or base.sha(previous / "result-1.json")
        != "a9a4be69279d26d76cd926b8303ac389f64c3d575d103b4405ae26eb6677c40a"
    ):
        raise ValueError("sealed_previous_probe_changed")
    return {
        "protocol": "fixed-single-positive-encoder-trace-v1",
        "limits": LIMITS,
        "base": base.configuration(root),
        "sources": {n: base.sha(root / n) for n in SOURCES},
        "libcommon_sha256": base.sha(base.RUNTIME.parent / "libllama-common.so"),
        "pure_logger_proof_sha256": base.sha(root / base.PROOF / "pure-logger-runtime.json"),
        "verbosity": 4,
    }


def prepare(root=ROOT):
    folder = root / QUEUE
    config = configuration(root)
    plan = {
        "configuration": config,
        "configuration_sha256": base.digest(config),
        "technical_release_required": True,
    }
    plan["plan_sha256"] = base.digest(plan)
    folder.mkdir(parents=True, mode=0o700)  # existing queue must never be reused
    base.write(folder / "plan.json", plan, exclusive=True)
    base.write(folder / "checkpoint.json", {"calls": 0, "sealed": False}, exclusive=True)
    return plan


def execute(root=ROOT):
    folder = root / QUEUE
    if folder.is_symlink() or any(p.is_symlink() for p in folder.parents):
        raise ValueError("trace_symlink_queue_forbidden")
    with (folder / ".lock").open("a+") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        plan = json.loads((folder / "plan.json").read_bytes())
        state = json.loads((folder / "checkpoint.json").read_bytes())
        if state != {"calls": 0, "sealed": False} or (folder / "started.json").exists():
            raise ValueError("trace_consumed_or_uncertain_no_reentry")
        if (
            base.digest({k: v for k, v in plan.items() if k != "plan_sha256"})
            != plan["plan_sha256"]
            or base.digest(plan["configuration"]) != plan["configuration_sha256"]
            or configuration(root) != plan["configuration"]
        ):
            raise ValueError("trace_plan_or_identity_changed")
        clearance = base.release(folder, plan)
        started = time.monotonic()
        base.write(
            folder / "started.json",
            {
                "plan_sha256": plan["plan_sha256"],
                "technical_release_sha256": clearance,
                "uncertain_seconds_upper_bound": 90,
            },
            exclusive=True,
        )
        work = None
        cleanup_allowed = True
        error = None
        try:
            if base.workers():
                raise base.ProbeStop("concurrent_worker")
            case = plan["configuration"]["base"]["cases"][0]
            parent = root / "data/private/media-temp"
            parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            work = Path(tempfile.mkdtemp(prefix="galaxies-encoder-trace-", dir=parent))
            image, schema = work / "crop.png", work / "schema.json"
            source = root / case["sheet_path"]
            if base.sha(source) != case["sheet_sha256"] or case["source_frame"] != 1:
                raise ValueError("frozen_positive_changed")
            with Image.open(source) as sheet:
                if sheet.mode != "RGB" or sheet.size != (1280, 360):
                    raise ValueError("frozen_sheet_geometry_changed")
                sheet.crop((0, 25, 320, 355)).save(image)
            if base.sha(image) != case["png_sha256"]:
                raise ValueError("frozen_positive_pixels_changed")
            schema.write_text(json.dumps(base.specification("item_first")["schema"]))
            if (
                configuration(root) != plan["configuration"]
                or base.release(folder, plan) != clearance
            ):
                raise ValueError("trace_identity_before_dispatch_changed")
            remaining = 90 - (time.monotonic() - started) - 5
            if remaining <= 0:
                raise TimeoutError("trace_global_budget")

            def reserve():
                if state["calls"] != 0:
                    raise ValueError("trace_one_call_budget")
                base.write(
                    folder / "reservation-1.json",
                    {"plan_sha256": plan["plan_sha256"], "input_png_sha256": case["png_sha256"]},
                    exclusive=True,
                )
                state.update(calls=1, elapsed_seconds=90, status="reserved_uncertain")
                base.write(folder / "checkpoint.json", state)

            result = base.capture(
                command(plan["configuration"]["base"]["original_argv"], image, schema),
                seconds=remaining,
                reserve=reserve,
            )
            cleanup_allowed = result["cleanup_confirmed"]
            base.write(
                folder / "result-1.json",
                {
                    "plan_sha256": plan["plan_sha256"],
                    "input_png_sha256": case["png_sha256"],
                    "source_seconds": case["seconds"],
                    "observation": result,
                },
                exclusive=True,
            )
            if base.sha(image) != case["png_sha256"]:
                raise ValueError("frozen_pixels_after_call_changed")
            state["status"] = "completed"
            if result["stop_code"]:
                raise base.ProbeStop(result["stop_code"])
        except BaseException as caught:  # noqa: BLE001 -- seal cancellation without private text
            error = caught
        finally:
            try:
                if work is not None and cleanup_allowed:
                    shutil.rmtree(work)
                elif work is not None:
                    state["preserved_scratch_cleanup_unconfirmed"] = str(work.relative_to(root))
            except BaseException as caught:  # noqa: BLE001 -- persist uncertain cleanup conservatively
                error = base.ProbeStop("cleanup_unconfirmed")
                state["cleanup_error_type"] = type(caught).__name__
                if work is not None:
                    state["preserved_scratch_cleanup_unconfirmed"] = str(work.relative_to(root))
            finally:
                state.update(
                    sealed=True,
                    elapsed_seconds=time.monotonic() - started,
                    stop_code=error.code
                    if isinstance(error, base.ProbeStop)
                    else type(error).__name__
                    if error
                    else "scope_completed",
                    candidates=[],
                    released_fields=[],
                    test_opened=False,
                    m1_changed=False,
                )
                if state["elapsed_seconds"] > 90:
                    state["stop_code"] = "global_deadline"
                base.write(folder / "checkpoint.json", state)
        if error:
            raise error
        return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["prepare", "execute", "inspect"])
    operation = parser.parse_args().operation
    try:
        result = (
            prepare()
            if operation == "prepare"
            else execute()
            if operation == "execute"
            else json.loads((ROOT / QUEUE / "checkpoint.json").read_bytes())
        )
        if operation == "prepare":
            result = {k: result[k] for k in ("plan_sha256", "configuration_sha256")}
    except Exception as error:  # noqa: BLE001 -- suppress private exception values
        result = {"status": "stopped", "error_type": type(error).__name__}
    print(json.dumps(result))


if __name__ == "__main__":
    main()

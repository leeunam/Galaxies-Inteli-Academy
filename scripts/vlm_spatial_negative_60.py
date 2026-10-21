"""One revealed negative at the frozen spatial settings, new bounded time allowance."""

import argparse
import fcntl
import json
import shutil
import tempfile
import time
from pathlib import Path

from PIL import Image

from scripts import vlm_spatial_budget as prior

base = prior.base
ROOT = prior.ROOT
QUEUE = "data/private/issue-4-vlm-spatial-negative-60-v1"
REFERENCE = "docs/evidence/issue-4-vlm-espacial-1024-resultados.json"
REFERENCE_SHA256 = "67970be0698cd6c49b9fec1526ebeedc70b908e693983e385a5e76e6653273f8"
LIMITS = {**prior.LIMITS, "calls": 1, "seconds": 70, "per_call_seconds": 60}
SOURCES = (
    "scripts/vlm_spatial_negative_60.py",
    "tests/test_vlm_spatial_negative_60.py",
    "docs/issue-4-vlm-espacial-negativo-60-protocolo.md",
)


def configuration(root=ROOT):
    path = root / REFERENCE
    if base.sha(path) != REFERENCE_SHA256:
        raise ValueError("sealed_timeout_reference_changed")
    reference = json.loads(path.read_bytes())
    old = root / prior.QUEUE
    if (
        reference["calls"] != 1
        or reference["stop_code"] != "native_timeout"
        or base.sha(old / "checkpoint.json") != reference["checkpoint_sha256"]
        or base.sha(old / "result-1.json") != reference["result_sha256"]
    ):
        raise ValueError("sealed_timeout_receipts_changed")
    inherited = prior.configuration(root)
    basis = inherited["inherited_configuration"]
    case = next(c for c in basis["pair"]["cases"] if c["alias"] == "negative")
    if case["expected_answer"] != "no":
        raise ValueError("negative_reference_changed")
    return {
        "protocol": "fixed-negative-spatial-60-second-dispatch-v1",
        "limits": LIMITS,
        "prior_configuration_sha256": base.digest(inherited),
        "reference_sha256": REFERENCE_SHA256,
        "case": case,
        "original_argv": basis["base"]["original_argv"],
        "normalized_argv": inherited["normalized_argv"],
        "reference_tokens": 100,
        "positive_calls": 0,
        "sources": {n: base.sha(root / n) for n in SOURCES},
    }


def prepare(root=ROOT):
    config = configuration(root)
    plan = {
        "configuration": config,
        "configuration_sha256": base.digest(config),
        "technical_release_required": True,
    }
    plan["plan_sha256"] = base.digest(plan)
    folder = root / QUEUE
    folder.mkdir(parents=True, mode=0o700)
    base.write(folder / "plan.json", plan, exclusive=True)
    base.write(folder / "checkpoint.json", {"calls": 0, "sealed": False}, exclusive=True)
    return plan


def execute(root=ROOT):
    folder = root / QUEUE
    if folder.is_symlink() or any(p.is_symlink() for p in folder.parents):
        raise ValueError("negative_symlink_queue_forbidden")
    with (folder / ".lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = json.loads((folder / "checkpoint.json").read_bytes())
        if state != {"calls": 0, "sealed": False} or (folder / "started.json").exists():
            raise ValueError("negative_consumed_or_uncertain_no_reentry")
        plan = json.loads((folder / "plan.json").read_bytes())
        if (
            base.digest({k: v for k, v in plan.items() if k != "plan_sha256"})
            != plan["plan_sha256"]
            or base.digest(plan["configuration"]) != plan["configuration_sha256"]
            or configuration(root) != plan["configuration"]
        ):
            raise ValueError("negative_identity_changed")
        clearance = prior.prior.release(folder, plan)
        started = time.monotonic()
        base.write(
            folder / "started.json",
            {
                "plan_sha256": plan["plan_sha256"],
                "technical_release_sha256": clearance,
                "uncertain_seconds_upper_bound": 70,
            },
            exclusive=True,
        )
        error = None
        work = None
        cleanup_allowed = True
        try:
            if base.workers():
                raise base.ProbeStop("concurrent_worker")
            config = plan["configuration"]
            case = config["case"]
            parent = root / "data/private/media-temp"
            parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            work = Path(tempfile.mkdtemp(prefix="galaxies-spatial-negative-60-", dir=parent))
            image, schema = work / "crop.png", work / "schema.json"
            source = root / case["sheet_path"]
            if base.sha(source) != case["sheet_sha256"]:
                raise ValueError("frozen_sheet_changed")
            with Image.open(source) as sheet:
                if sheet.mode != "RGB" or sheet.size != (1280, 360) or case["source_frame"] != 3:
                    raise ValueError("negative_sheet_geometry_changed")
                sheet.crop((640, 25, 960, 355)).save(image)
            if base.sha(image) != case["png_sha256"]:
                raise ValueError("frozen_pixels_changed")
            schema.write_text(json.dumps(prior.prior.SCHEMA))
            if configuration(root) != config or prior.prior.release(folder, plan) != clearance:
                raise ValueError("negative_identity_before_dispatch_changed")
            if base.workers():
                raise base.ProbeStop("concurrent_worker")
            remaining = min(60, 70 - (time.monotonic() - started)) - 5
            if remaining <= 0:
                raise TimeoutError("negative_global_budget")

            def reserve():
                if state["calls"] != 0:
                    raise ValueError("negative_one_call_budget")
                base.write(
                    folder / "reservation-1.json",
                    {"plan_sha256": plan["plan_sha256"], "input_png_sha256": case["png_sha256"]},
                    exclusive=True,
                )
                state.update(calls=1, elapsed_seconds=70, status="reserved_uncertain")
                base.write(folder / "checkpoint.json", state)

            result = prior.prior.short.capture(
                prior.command(config["original_argv"], image, schema),
                seconds=remaining,
                reserve=reserve,
            )
            cleanup_allowed = result["cleanup_confirmed"]
            prior.effective_budget(result, config["reference_tokens"])
            outcome = prior.prior.comparison(result, case["expected_answer"])
            base.write(
                folder / "result-1.json",
                {
                    "plan_sha256": plan["plan_sha256"],
                    "alias": "negative",
                    "input_png_sha256": case["png_sha256"],
                    "source_seconds": case["seconds"],
                    "observation": result,
                    "diagnostic_comparison": outcome,
                },
                exclusive=True,
            )
            if base.sha(image) != case["png_sha256"]:
                raise ValueError("frozen_pixels_after_call_changed")
            state.update(status="completed", diagnostic_comparison=outcome)
            if result["stop_code"]:
                raise base.ProbeStop(result["stop_code"])
        except BaseException as caught:  # noqa: BLE001 -- preserve cancellation and terminal receipt
            error = caught
        finally:
            try:
                if work is not None and cleanup_allowed:
                    shutil.rmtree(work)
                elif work is not None:
                    state["preserved_scratch_cleanup_unconfirmed"] = str(work.relative_to(root))
            except BaseException as caught:  # noqa: BLE001 -- never hide uncertain cleanup
                state["cleanup_error_type"] = type(caught).__name__
                if work is not None:
                    state["preserved_scratch_cleanup_unconfirmed"] = str(work.relative_to(root))
                error = base.ProbeStop("cleanup_unconfirmed")
            finally:
                if time.monotonic() - started > 70 and error is None:
                    error = base.ProbeStop("global_deadline")
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
    except Exception as error:  # noqa: BLE001 -- no private exception text on stdout
        result = {"status": "stopped", "error_type": type(error).__name__}
    print(json.dumps(result))


if __name__ == "__main__":
    main()

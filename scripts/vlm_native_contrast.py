"""Four frozen native/derived cells; preparation never grants model execution."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import io
import json
import os
import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path

from PIL import Image

from scripts import vlm_native_source_recovery as native
from scripts import vlm_spatial_budget as spatial

prior, base = spatial.prior, spatial.base
ROOT = base.ROOT
QUEUE = "data/private/issue-4-vlm-native-contrast-v1"
EVIDENCE = "docs/evidence/issue-4-vlm-fonte-nativa-recuperacao-resultados.json"
EVIDENCE_SHA = "a479d013ecb64cd670590eea00745b5e9fdb37edd02ebb245ac8392a827a28b6"
ARITH_FOLDER = "data/private/issue-4-vlm-native-contrast-preflight-v1"
ARITH_SHA = "2dbf08acf646d6575a3bbf1518af81f6d2233c20ff334c8184e83df51a21c0cc"
PADDING_SHA = "e82be0911feed09284d85b8698c1174972fa0b203391dafbe3e44b0f867684d9"
SEQUENCE = ("negative-D", "negative-N", "positive-N", "positive-D")
LIMITS = {
    **spatial.LIMITS,
    "calls": 4,
    "seconds": 260,
    "per_call_seconds": 60,
    "preparation_allowance_seconds": 20,
}
SOURCES = (
    "scripts/vlm_native_contrast.py",
    "tests/test_vlm_native_contrast.py",
    "docs/issue-4-vlm-contraste-nativo-derivado-proposta.md",
    "docs/issue-4-vlm-contraste-nativo-preparacao.md",
)


def png_bytes(image):
    out = io.BytesIO()
    image.save(out, format="PNG")
    return out.getvalue()


def derived_bytes(sheet_path, case):
    if base.sha(sheet_path) != case["sheet_sha256"]:
        raise ValueError("old_sheet_changed")
    with Image.open(sheet_path) as sheet:
        if sheet.mode != "RGB" or sheet.size != (1280, 360):
            raise ValueError("old_sheet_geometry_changed")
        x = 320 * (case["source_frame"] - 1)
        cell = sheet.crop((x, 25, x + 320, 355))
    if hashlib.sha256(png_bytes(cell)).hexdigest() != case["png_sha256"]:
        raise ValueError("old_crop_changed")
    if cell.crop((186, 0, 320, 330)).getextrema() != ((255, 255),) * 3:
        raise ValueError("fixed_blank_margin_changed")
    return png_bytes(cell.crop((0, 0, 186, 330)).resize((360, 640), Image.Resampling.LANCZOS))


def geometry_proof(root):
    folder = root / ARITH_FOLDER
    path = folder / "resize-arithmetic-receipt.json"
    if base.sha(path) != ARITH_SHA:
        raise ValueError("resize_arithmetic_receipt_changed")
    value = json.loads(path.read_bytes())
    for name, wanted in value["source_files_sha256"].items():
        if base.sha(folder / "sources" / name) != wanted:
            raise ValueError("resize_arithmetic_source_changed")
    for name, key in (
        ("resize-arithmetic.cpp", "helper_source_sha256"),
        ("resize-arithmetic", "helper_binary_sha256"),
    ):
        if base.sha(folder / name) != value[key]:
            raise ValueError("resize_arithmetic_helper_changed")
    if (
        value["source_commit"] != "797de63b2"
        or value["model_loaded"] is not False
        or value["forward_passes"] != 0
        or value["cases"]
        != [
            {"input": [360, 640], "resized": [800, 1376], "grid": [25, 43], "tokens": 1075},
            {"input": [320, 330], "resized": [1024, 1056], "grid": [32, 33], "tokens": 1056},
        ]
    ):
        raise ValueError("resize_geometry_contract_changed")
    padding_path = folder / "padding-arithmetic-receipt.json"
    if base.sha(padding_path) != PADDING_SHA:
        raise ValueError("padding_arithmetic_receipt_changed")
    padding = json.loads(padding_path.read_bytes())
    for name, key in (
        ("padding-arithmetic.cpp", "helper_source_sha256"),
        ("padding-arithmetic", "helper_binary_sha256"),
    ):
        if base.sha(folder / name) != padding[key]:
            raise ValueError("padding_arithmetic_helper_changed")
    if (
        padding["model_loaded"] is not False
        or padding["forward_passes"] != 0
        or padding["content"] != [775, 1376]
        or padding["offset"] != [12, 0]
        or padding["no_content_axis_reduced"] is not True
        or padding["source_sha256"] != value["source_files_sha256"]["mtmd-image.cpp"]
    ):
        raise ValueError("padding_geometry_contract_changed")
    return value | {"padding_arithmetic": padding}


def inputs(root):
    if base.sha(root / EVIDENCE) != EVIDENCE_SHA:
        raise ValueError("native_evidence_changed")
    evidence = json.loads((root / EVIDENCE).read_bytes())
    native_plan, checksum = native.load(root)
    run = root / native.QUEUE / "run"
    if run.is_symlink() or (run / "frames").is_symlink():
        raise ValueError("native_source_directory_symlink")
    if (
        checksum != evidence["plan_sha256"]
        or base.sha(run / "result.json") != evidence["receipt_sha256"]
    ):
        raise ValueError("native_provenance_changed")
    output, cases = {}, []
    for case in native_plan["configuration"]["cases"]:
        alias = case["alias"]
        reference = next(c for c in evidence["cases"] if c["alias"] == alias)
        path = run / "frames" / (alias + ".png")
        if path.is_symlink() or base.sha(path) != reference["native_sha256"]:
            raise ValueError("native_png_changed")
        with Image.open(path) as image:
            if image.mode != "RGB" or image.size != (360, 640):
                raise ValueError("native_png_geometry_changed")
        output[alias + "-N"] = path.read_bytes()
        output[alias + "-D"] = derived_bytes(root / case["sheet_path"], case)
        cases.append(
            {
                k: case[k]
                for k in (
                    "alias",
                    "expected_answer",
                    "seconds",
                    "source_frame",
                    "sheet_path",
                    "sheet_sha256",
                    "png_sha256",
                )
            }
        )
    return output, cases


def configuration(root=ROOT):
    geometry = geometry_proof(root)
    images, cases = inputs(root)
    inherited = spatial.configuration(root)
    cells = []
    for name in SEQUENCE:
        alias, representation = name.split("-")
        case = next(c for c in cases if c["alias"] == alias)
        cells.append(
            {
                "name": name,
                "case_role": alias,
                "representation": representation,
                "png_sha256": hashlib.sha256(images[name]).hexdigest(),
                "source_seconds": case["seconds"],
                "expected_answer": case["expected_answer"],
            }
        )
    return {
        "protocol": "revealed-pair-native-derived-contrast-v1",
        "limits": LIMITS,
        "inherited_configuration": inherited,
        "native_evidence_sha256": EVIDENCE_SHA,
        "arithmetic_receipt_sha256": ARITH_SHA,
        "geometry_calculation": geometry,
        "expected_tokens": 1075,
        "input_geometry": [360, 640],
        "cells": cells,
        "retention_until": native.RETENTION,
        "sources": {name: base.sha(root / name) for name in SOURCES},
    }


def write_image(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as out:
        out.write(data)
        out.flush()
        os.fsync(out.fileno())


def prepare(root=ROOT):
    config = configuration(root)
    images, _ = inputs(root)
    folder = native.private_path(root / QUEUE, root=root)
    folder.mkdir(mode=0o700, exist_ok=False)
    (folder / "images").mkdir(mode=0o700)
    for name, data in images.items():
        write_image(folder / "images" / (name + ".png"), data)
    plan = {
        "configuration": config,
        "configuration_sha256": base.digest(config),
        "technical_release_required": True,
    }
    plan["plan_sha256"] = base.digest(plan)
    base.write(folder / "plan.json", plan, exclusive=True)
    base.write(folder / "checkpoint.json", {"calls": 0, "sealed": False}, exclusive=True)
    return plan


def load(root=ROOT):
    folder = native.private_path(root / QUEUE, root=root)
    plan = json.loads((folder / "plan.json").read_bytes())
    if (
        base.digest({k: v for k, v in plan.items() if k != "plan_sha256"}) != plan["plan_sha256"]
        or base.digest(plan["configuration"]) != plan["configuration_sha256"]
        or configuration(root) != plan["configuration"]
    ):
        raise ValueError("contrast_identity_changed")
    for cell in plan["configuration"]["cells"]:
        path = folder / "images" / (cell["name"] + ".png")
        if path.is_symlink() or base.sha(path) != cell["png_sha256"]:
            raise ValueError("contrast_prepared_png_changed")
    return plan


def validate_observation(value, expected, first):
    if value["stop_code"]:
        raise base.ProbeStop(value["stop_code"])
    if value["format_status"] != "valid":
        raise base.ProbeStop("contrast_format_invalid")
    count = value["image_tokens_observed"]
    if type(count) is not int or count < 1024 or count != expected:
        raise base.ProbeStop("contrast_geometry_token_mismatch")
    if first is not None and count != first:
        raise base.ProbeStop("contrast_unequal_tokens")
    if (
        value["image_encoder_and_decode_observed"] is not True
        or value["cleanup_confirmed"] is not True
    ):
        raise base.ProbeStop("contrast_encoder_or_cleanup_uncertain")
    return count


def execute(root=ROOT):
    folder = native.private_path(root / QUEUE, root=root)
    with (folder / ".lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = json.loads((folder / "checkpoint.json").read_bytes())
        if state != {"calls": 0, "sealed": False} or (folder / "started.json").exists():
            raise ValueError("contrast_consumed_no_reentry")
        started = time.monotonic()
        plan = load(root)
        clearance = prior.release(folder, plan)
        base.write(
            folder / "started.json",
            {
                "plan_sha256": plan["plan_sha256"],
                "technical_release_sha256": clearance,
                "uncertain_seconds_upper_bound": 260,
            },
            exclusive=True,
        )
        stop, first = "scope_completed", None
        work = None
        cleanup_allowed = True
        try:
            for number, cell in enumerate(plan["configuration"]["cells"], 1):
                if time.time() >= datetime.fromisoformat(native.RETENTION).timestamp():
                    raise base.ProbeStop("contrast_input_retention_expired")
                if base.workers():
                    raise base.ProbeStop("concurrent_worker")
                if load(root) != plan or prior.release(folder, plan) != clearance:
                    raise ValueError("contrast_identity_before_dispatch_changed")
                parent = root / "data/private/media-temp"
                parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                work = Path(tempfile.mkdtemp(prefix="galaxies-native-contrast-", dir=parent))
                schema = work / "schema.json"
                schema.write_text(json.dumps(prior.SCHEMA))
                image = folder / "images" / (cell["name"] + ".png")
                remaining = (
                    min(
                        60,
                        260 - (time.monotonic() - started),
                        datetime.fromisoformat(native.RETENTION).timestamp() - time.time(),
                    )
                    - 5
                )
                if remaining <= 0:
                    raise base.ProbeStop("contrast_global_deadline")

                def reserve(number=number, cell=cell):
                    if state["calls"] != number - 1 or number > 4:
                        raise ValueError("contrast_call_budget")
                    base.write(
                        folder / f"reservation-{number}.json",
                        {
                            "plan_sha256": plan["plan_sha256"],
                            "cell": cell["name"],
                            "input_png_sha256": cell["png_sha256"],
                        },
                        exclusive=True,
                    )
                    state.update(calls=number, elapsed_seconds=260, status="reserved_uncertain")
                    base.write(folder / "checkpoint.json", state)

                argv = spatial.command(
                    plan["configuration"]["inherited_configuration"]["inherited_configuration"][
                        "base"
                    ]["original_argv"],
                    image,
                    schema,
                )
                cleanup_allowed = False  # an exception without an ack must retain own scratch
                value = prior.short.capture(argv, seconds=remaining, reserve=reserve)
                cleanup_allowed = value["cleanup_confirmed"]
                base.write(
                    folder / f"result-{number}.json",
                    {
                        "plan_sha256": plan["plan_sha256"],
                        "cell": cell,
                        "observation": value,
                        "diagnostic_comparison": prior.comparison(value, cell["expected_answer"]),
                    },
                    exclusive=True,
                )
                if base.sha(image) != cell["png_sha256"]:
                    raise base.ProbeStop("contrast_png_after_call_changed")
                first = validate_observation(value, plan["configuration"]["expected_tokens"], first)
                if cleanup_allowed:
                    try:
                        shutil.rmtree(work)
                    except BaseException:
                        cleanup_allowed = False
                        raise
                    work = None
            if time.monotonic() - started > 260:
                raise base.ProbeStop("contrast_global_deadline")
        except BaseException as exc:  # noqa: BLE001 -- preserve cancellation, never raw errors
            stop = exc.code if isinstance(exc, base.ProbeStop) else type(exc).__name__
        finally:
            if work is not None:
                if cleanup_allowed:
                    try:
                        shutil.rmtree(work)
                    except BaseException:  # noqa: BLE001 -- own scratch must remain on uncertain cleanup
                        cleanup_allowed = False
                if not cleanup_allowed:
                    state["preserved_scratch"] = str(work.relative_to(root))
                    stop = "contrast_cleanup_unconfirmed"
            state.update(
                sealed=True,
                stop_code=stop,
                elapsed_seconds=time.monotonic() - started,
                candidates=[],
                released_fields=[],
                test_opened=False,
                m1_changed=False,
            )
            base.write(folder / "checkpoint.json", state)
        return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "inspect", "execute"])
    phase = parser.parse_args().phase
    os.umask(0o077)
    try:
        if phase == "execute":
            state = execute()
            print(
                json.dumps(
                    {
                        k: state[k]
                        for k in (
                            "calls",
                            "sealed",
                            "stop_code",
                            "elapsed_seconds",
                            "candidates",
                            "released_fields",
                        )
                    }
                )
            )
            if state["stop_code"] != "scope_completed":
                raise SystemExit(1)
        else:
            plan = prepare() if phase == "prepare" else load()
            print(
                json.dumps(
                    {
                        "status": "prepared_or_inspected_not_released",
                        "plan_sha256": plan["plan_sha256"],
                        "configuration_sha256": plan["configuration_sha256"],
                        "generations": 0,
                    }
                )
            )
    except Exception:  # noqa: BLE001 -- no source identities, paths or raw exception content
        print('{"status":"contrast_stopped_no_retry"}')
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()

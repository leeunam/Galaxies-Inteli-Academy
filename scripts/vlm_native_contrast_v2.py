"""Inert four-cell v2 controller; a new external authorization and review are mandatory."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import shutil
import tempfile
import time
from datetime import datetime
from pathlib import Path

from PIL import Image

from scripts import vlm_durable_capture_v2 as durable
from scripts import vlm_native_contrast as frozen
from scripts.demo_recovery_policy import fsync_dir, read_json

base, native, prior, spatial = frozen.base, frozen.native, frozen.prior, frozen.spatial
ROOT = Path(__file__).resolve().parents[1]
QUEUE = "data/private/issue-4-vlm-native-contrast-v2"
PROTOCOL = "revealed-pair-native-derived-durable-v2"
SEQUENCE = frozen.SEQUENCE
LIMITS = frozen.LIMITS
SOURCES = (
    "scripts/vlm_native_contrast_v2.py",
    "scripts/vlm_durable_capture_v2.py",
    "tests/test_vlm_native_contrast_v2.py",
    "docs/issue-4-vlm-contraste-nativo-v2-proposta.md",
)
# The consumed authorization is represented only by a non-reversible public digest.
CONSUMED_AUTH_SHA256 = "b86afc5b54fd2d5a5f8d9a9aa09affe9ca9b5dbff74f4eeb2b2a5de60e081960"
INITIAL = {"calls": 0, "sealed": False}


def folder_at(root):
    return native.private_path(Path(root) / QUEUE, root=root)


def configuration(root=ROOT):
    """Read-only frozen provenance; never dispatch or reopen the v1 queue."""
    old = native.private_path(Path(root) / frozen.QUEUE, root=root)
    state = read_json(old / "checkpoint.json")
    if (state.get("calls"), state.get("sealed"), state.get("stop_code")) != (
        1,
        True,
        "contrast_interrupted_outcome_uncertain",
    ):
        raise ValueError("v1_sealed_provenance_required")
    plan = read_json(old / "plan.json", limit=2**22)
    inherited = frozen.configuration(root)
    if (
        base.digest({k: v for k, v in plan.items() if k != "plan_sha256"}) != plan["plan_sha256"]
        or base.digest(inherited) != plan["configuration_sha256"]
        or inherited != plan["configuration"]
        or [c["name"] for c in inherited["cells"]] != list(SEQUENCE)
    ):
        raise ValueError("frozen_provenance_changed")
    return {
        "protocol": PROTOCOL,
        "namespace": durable.NAMESPACE,
        "root_sha256": hashlib.sha256(str(Path(root).resolve()).encode()).hexdigest(),
        "reviewer_thread_id": native.REVIEWER,
        "limits": LIMITS,
        "expected_tokens": 1075,
        "cells": inherited["cells"],
        "inherited_configuration": inherited,
        "frozen_plan_sha256": plan["plan_sha256"],
        "frozen_checkpoint_sha256": base.sha(old / "checkpoint.json"),
        "sources": {n: base.sha(Path(root) / n) for n in SOURCES},
        "retry_allowed": False,
        "external_cost": 0,
    }


def prepare(root=ROOT):
    """Future authorized preparation only: copy four already-frozen PNG bytes."""
    config = configuration(root)
    images = {}
    for cell in config["cells"]:
        path = Path(root) / frozen.QUEUE / "images" / (cell["name"] + ".png")
        if path.is_symlink() or base.sha(path) != cell["png_sha256"]:
            raise ValueError("frozen_input_changed")
        with Image.open(path) as image:
            if image.mode != "RGB" or image.size != (360, 640):
                raise ValueError("frozen_input_geometry_changed")
        images[cell["name"]] = path.read_bytes()
    folder = folder_at(root)
    folder.mkdir(mode=0o700, exist_ok=False)
    fsync_dir(folder.parent)
    (folder / "images").mkdir(mode=0o700)
    for name, raw in images.items():
        frozen.write_image(folder / "images" / (name + ".png"), raw)
    fsync_dir(folder / "images")
    plan = {
        "configuration": config,
        "configuration_sha256": base.digest(config),
        "new_external_authorization_required": True,
        "new_independent_review_required": True,
    }
    plan["plan_sha256"] = base.digest(plan)
    base.write(folder / "plan.json", plan, exclusive=True)
    base.write(folder / "checkpoint.json", dict(INITIAL), exclusive=True)
    return plan


def load(root=ROOT):
    folder = folder_at(root)
    plan = read_json(folder / "plan.json", limit=2**22)
    if (
        base.digest({k: v for k, v in plan.items() if k != "plan_sha256"}) != plan["plan_sha256"]
        or base.digest(plan["configuration"]) != plan["configuration_sha256"]
        or plan["configuration"] != configuration(root)
    ):
        raise ValueError("v2_identity_changed")
    for cell in plan["configuration"]["cells"]:
        path = folder / "images" / (cell["name"] + ".png")
        if path.is_symlink() or base.sha(path) != cell["png_sha256"]:
            raise ValueError("v2_input_changed")
    return plan


def release(root, plan):
    """Validate externally authored receipts. This module has no receipt writer."""
    folder = folder_at(root)
    path = folder / "authorization.json"
    review_path = folder / "review-seal.json"
    auth, review = read_json(path, limit=16384), read_json(review_path, limit=16384)
    message = auth.get("source_message_id")
    literal = auth.get("literal_message")
    bound = {
        "protocol": PROTOCOL,
        "namespace": durable.NAMESPACE,
        "plan_sha256": plan["plan_sha256"],
        "configuration_sha256": plan["configuration_sha256"],
        "root_sha256": plan["configuration"]["root_sha256"],
        "reviewer_thread_id": native.REVIEWER,
        "limits": LIMITS,
        "input_hashes": {c["name"]: c["png_sha256"] for c in plan["configuration"]["cells"]},
        "retry_allowed": False,
        "external_cost": 0,
    }
    old = read_json(Path(root) / frozen.QUEUE / "technical-release.json", limit=16384)
    if (
        any(auth.get(k) != v for k, v in bound.items())
        or not isinstance(message, str)
        or not message
        or message == old.get("source_message_id")
        or hashlib.sha256(message.encode()).hexdigest() == CONSUMED_AUTH_SHA256
        or not isinstance(literal, str)
        or not literal
        or auth.get("literal_message_sha256") != hashlib.sha256(literal.encode()).hexdigest()
        or auth.get("decision") != "authorize_exact_four_cell_v2_once"
        or any(review.get(k) != v for k, v in bound.items())
        or review.get("authorization_sha256") != base.sha(path)
        or review.get("decision") != "reviewed_exact_v2_plan_and_authorization"
        or not isinstance(review.get("review_message_id"), str)
        or not review["review_message_id"]
        or review["review_message_id"] in (message, old.get("source_message_id"))
    ):
        raise ValueError("new_v2_authorization_and_review_required")
    return base.digest({"authorization": base.sha(path), "review": base.sha(review_path)})


class _DeadlineProcess:
    """Delegate the real process unchanged; only poll requests deadline cleanup."""

    def __init__(self, process, deadline):
        self.process, self.deadline = process, deadline

    def __getattr__(self, name):
        return getattr(self.process, name)

    def poll(self):
        if time.monotonic() >= self.deadline:
            raise TimeoutError("v2_dispatch_deadline")
        return self.process.poll()


def _launcher(root, plan, clearance, argv, deadline):
    """Only the frozen internal command can reach the existing process owner."""

    def start(*args, **kwargs):
        try:
            if (
                Path(root).resolve() != ROOT.resolve()
                or ROOT.resolve() != base.ROOT.resolve()
                or len(args) != 1
                or args[0] != argv
                or load(root) != plan
                or release(root, plan) != clearance
            ):
                raise RuntimeError("v2_launcher_guard")
            if time.monotonic() >= deadline:
                raise TimeoutError("v2_launcher_deadline")
            return _DeadlineProcess(base.subprocess.Popen(*args, **kwargs), deadline)
        except (TimeoutError, OSError):
            raise
        except Exception:  # noqa: BLE001 -- fixed sanitized launcher failure
            # The frozen collector persists only this bounded error category;
            # no raw guard error or private value crosses the process boundary.
            raise RuntimeError("v2_launcher_guard") from None

    return start


def execute(root=ROOT):
    # No lock, counter, scratch or capture marker is created before these checks.
    folder = folder_at(root)
    read_json(folder / "authorization.json", limit=16384)
    read_json(folder / "review-seal.json", limit=16384)
    started = time.monotonic()
    plan = load(root)
    clearance = release(root, plan)
    with (folder / ".lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = read_json(folder / "checkpoint.json")
        if state != INITIAL or (folder / "started.json").exists() or (folder / "captures").exists():
            raise ValueError("v2_consumed_no_reentry")
        base.write(
            folder / "started.json",
            {
                "plan_sha256": plan["plan_sha256"],
                "release_sha256": clearance,
                "uncertain_seconds_upper_bound": 260,
            },
            exclusive=True,
        )
        stop, first, work, cleanup_allowed = "scope_completed", None, None, True
        try:
            for number, cell in enumerate(plan["configuration"]["cells"], 1):
                if time.time() >= datetime.fromisoformat(native.RETENTION).timestamp():
                    raise base.ProbeStop("contrast_input_retention_expired")
                if base.workers():
                    raise base.ProbeStop("concurrent_worker")
                if load(root) != plan or release(root, plan) != clearance:
                    raise ValueError("v2_identity_before_dispatch_changed")
                parent = Path(root) / "data/private/media-temp"
                parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                work = Path(tempfile.mkdtemp(prefix="galaxies-native-v2-", dir=parent))
                schema = work / "schema.json"
                frozen.write_image(schema, json.dumps(prior.SCHEMA).encode())
                image = folder / "images" / (cell["name"] + ".png")
                call_started = time.monotonic()
                deadline = min(
                    call_started + 60,
                    started + 260,
                    call_started
                    + datetime.fromisoformat(native.RETENTION).timestamp()
                    - time.time(),
                )
                remaining = (
                    min(
                        deadline - call_started,
                        datetime.fromisoformat(native.RETENTION).timestamp() - time.time(),
                    )
                    - 5
                )
                if remaining <= 0:
                    raise base.ProbeStop("contrast_global_deadline")

                def reserve(number=number, cell=cell, deadline=deadline):
                    if time.monotonic() >= deadline - 5:
                        raise base.ProbeStop("contrast_global_deadline")
                    if state["calls"] != number - 1 or number > 4:
                        raise ValueError("v2_call_budget")
                    if load(root) != plan or release(root, plan) != clearance:
                        raise ValueError("v2_identity_at_reservation_changed")
                    base.write(
                        folder / f"reservation-{number}.json",
                        {
                            "plan_sha256": plan["plan_sha256"],
                            "release_sha256": clearance,
                            "cell": cell["name"],
                            "input_png_sha256": cell["png_sha256"],
                        },
                        exclusive=True,
                    )
                    state.update(calls=number, elapsed_seconds=260, status="reserved_uncertain")
                    base.write(folder / "checkpoint.json", state)

                argv = spatial.command(
                    plan["configuration"]["inherited_configuration"]["inherited_configuration"][
                        "inherited_configuration"
                    ]["base"]["original_argv"],
                    image,
                    schema,
                )
                remaining = min(remaining, deadline - time.monotonic() - 5)
                if remaining <= 0:
                    raise base.ProbeStop("contrast_global_deadline")
                cleanup_allowed = False
                value = durable.capture(
                    argv,
                    root=root,
                    cell=cell["name"],
                    seconds=remaining,
                    reserve=reserve,
                    popen=_launcher(root, plan, clearance, argv, deadline - 5),
                )
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
                first = frozen.validate_observation(value, 1075, first)
                if time.monotonic() > deadline:
                    raise base.ProbeStop("v2_dispatch_deadline")
                if cleanup_allowed:
                    shutil.rmtree(work)
                    work = None
                if time.monotonic() > deadline:
                    raise base.ProbeStop("v2_dispatch_deadline")
            if time.monotonic() - started > 260:
                raise base.ProbeStop("contrast_global_deadline")
        except BaseException as exc:  # noqa: BLE001 -- preserve cancellation, no raw errors
            stop = exc.code if isinstance(exc, base.ProbeStop) else type(exc).__name__
        finally:
            if work is not None:
                if cleanup_allowed:
                    try:
                        shutil.rmtree(work)
                    except BaseException:  # noqa: BLE001 -- retain on uncertain cleanup
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
                retry_allowed=False,
            )
            base.write(folder / "checkpoint.json", state)
            if time.monotonic() - started > 260 and state["stop_code"] == "scope_completed":
                state.update(
                    stop_code="contrast_global_deadline", elapsed_seconds=time.monotonic() - started
                )
                base.write(folder / "checkpoint.json", state)
        return state


def inspect(root=ROOT):
    folder = folder_at(root)
    if not folder.exists():
        return {
            "status": "absent",
            "calls": 0,
            "retry_allowed": False,
            "no_reentry": False,
            "remaining_calls": 0,
        }
    state = read_json(folder / "checkpoint.json")
    captures = {}
    for cell in SEQUENCE:
        try:
            captures[cell] = durable.inspect(root, cell)
        except FileNotFoundError:
            captures[cell] = {"status": "absent", "terminal": False}
    consumed = (
        (folder / "started.json").exists() or (folder / "captures").exists() or state != INITIAL
    )
    status = (
        "sealed"
        if state.get("sealed")
        else "started_outcome_uncertain"
        if consumed
        else "prepared_not_authorized"
    )
    return {
        "status": status,
        "no_reentry": consumed,
        "remaining_calls": 0 if consumed else 4,
        "calls": state.get("calls"),
        "sealed": state.get("sealed"),
        "captures": captures,
        "retry_allowed": False,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "inspect", "execute"))
    phase = parser.parse_args().phase
    os.umask(0o077)
    try:
        value = prepare() if phase == "prepare" else execute() if phase == "execute" else inspect()
        if phase == "prepare":
            value = {"status": "prepared_not_authorized", "plan_sha256": value["plan_sha256"]}
        print(json.dumps(value, allow_nan=False))
        if phase == "execute" and value["stop_code"] != "scope_completed":
            raise SystemExit(1)
    except Exception:  # noqa: BLE001 -- no private paths, identities or arbitrary error text
        print('{"status":"v2_stopped_no_retry"}')
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()

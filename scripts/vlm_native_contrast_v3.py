"""Four frozen cells in v3; execution requires new exact human and external review receipts."""

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

from scripts import vlm_durable_capture_v3 as durable
from scripts import vlm_native_contrast_v2 as previous
from scripts import vlm_phase_diagnostic as phase_diagnostic
from scripts.demo_recovery_policy import fsync_dir, read_json

frozen = previous.frozen
base, native, prior, spatial = previous.base, previous.native, previous.prior, previous.spatial
ROOT = Path(__file__).resolve().parents[1]
QUEUE = "data/private/" + durable.NAMESPACE
PROTOCOL = "revealed-pair-native-derived-durable-v3"
SEQUENCE = previous.SEQUENCE
LIMITS = {
    **previous.LIMITS,
    "seconds": 340,
    "per_call_seconds": 80,
    "useful_seconds": 75,
    "cleanup_seconds": 5,
}
INPUT_HASHES = dict(
    zip(
        SEQUENCE,
        (
            "ee884ab32ba1535291932d38b19f867e28cd833f3e5c1fe6c8dd49228d7ce998",
            "efa80be09f41f8250aa34c83521585d6a8c64a23f69c5b7eba0da1b4f1aeebfc",
            "238d3b775563fdffe47c3bfdce9c6623058642194f108107f58fcd9a10ae89e1",
            "8727f0e6185cd5f4d859ee7eff34839ac282fb67f54a1e8737d80bcf5f645177",
        ),
        strict=True,
    )
)
SOURCES = (
    "scripts/vlm_native_contrast_v3.py",
    "scripts/vlm_durable_capture_v3.py",
    "scripts/vlm_durable_capture_v2.py",
    "scripts/vlm_phase_diagnostic.py",
    "tests/test_vlm_native_contrast_v3.py",
    "docs/issue-4-vlm-contraste-nativo-v3-proposta.md",
)
FROZEN_V2_PLAN = "8b6baea8e3f2f511587d52963cce14ff3e4002c5edeff8215464442bdef20b98"
FROZEN_V2_CHECKPOINT = "e1d9b1a2e0fe7ec9604120048cbefeaf4999c739df2ac36381aa82e9e039c451"
# Prior consumed source messages and the generic request are not fresh authority.
REJECTED_MESSAGE_SHA256 = frozenset(
    {
        "b86afc5b54fd2d5a5f8d9a9aa09affe9ca9b5dbff74f4eeb2b2a5de60e081960",
        "8ef49aa57338915add1a97932e0ad32caed0a25c1c35e7f5f0e0d668e03b31bd",
        "016e2758785ae4f0dc53c3cb38662be65cde07baf07cd87cf5eaf244a4fa523a",
        "4c61af885e459fa0fa4abd960fc6a6104a7b360a6f38bb4474c765d3ccd7d126",
    }
)
GENERIC_LITERAL_SHA256 = "7bbbe85ed959e328b00533f601b5bc545af68957000cd444eeeaaea5940bd2cf"
INITIAL = previous.INITIAL


def folder_at(root):
    return native.private_path(Path(root) / QUEUE, root=root)


def configuration(root=ROOT):
    """Read only the frozen provenance; the consumed v2 remains sealed."""
    inherited_plan = previous.load(root)
    old = previous.folder_at(root)
    state = read_json(old / "checkpoint.json")
    inherited = inherited_plan["configuration"]
    if (
        inherited_plan["plan_sha256"] != FROZEN_V2_PLAN
        or base.sha(old / "checkpoint.json") != FROZEN_V2_CHECKPOINT
        or (state.get("calls"), state.get("sealed"), state.get("stop_code"))
        != (2, True, "native_timeout")
        or [c["name"] for c in inherited["cells"]] != list(SEQUENCE)
        or {c["name"]: c["png_sha256"] for c in inherited["cells"]} != INPUT_HASHES
    ):
        raise ValueError("v2_sealed_provenance_required")
    original = inherited["inherited_configuration"]["inherited_configuration"][
        "inherited_configuration"
    ]["base"]["original_argv"]
    return {
        "protocol": PROTOCOL,
        "namespace": durable.NAMESPACE,
        "root_sha256": hashlib.sha256(str(Path(root).resolve()).encode()).hexdigest(),
        "reviewer_thread_id": native.REVIEWER,
        "limits": LIMITS,
        "expected_tokens": 1075,
        "input_geometry": {"mode": "RGB", "width": 360, "height": 640},
        "retention_until": native.RETENTION,
        "cells": inherited["cells"],
        "effective_argv_template": spatial.command(original, "<PNG>", "<SCHEMA>"),
        "inherited_configuration": inherited,
        "frozen_plan_sha256": FROZEN_V2_PLAN,
        "frozen_checkpoint_sha256": FROZEN_V2_CHECKPOINT,
        "sources": {n: base.sha(Path(root) / n) for n in SOURCES},
        "retry_allowed": False,
        "external_cost": 0,
    }


def prepare(root=ROOT):
    """Future authorized preparation only: copy four already-frozen PNG bytes."""
    config = configuration(root)
    if time.time() >= datetime.fromisoformat(native.RETENTION).timestamp():
        raise base.ProbeStop("contrast_input_retention_expired")
    images = {}
    for cell in config["cells"]:
        path = Path(root) / previous.QUEUE / "images" / (cell["name"] + ".png")
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
        raise ValueError("v3_identity_changed")
    for cell in plan["configuration"]["cells"]:
        path = folder / "images" / (cell["name"] + ".png")
        if path.is_symlink() or base.sha(path) != cell["png_sha256"]:
            raise ValueError("v3_input_changed")
    return plan


def _fresh_message(value):
    return (
        type(value) is str
        and bool(value.strip())
        and len(value) <= 256
        and hashlib.sha256(value.encode()).hexdigest() not in REJECTED_MESSAGE_SHA256
    )


def release(root, plan):
    """Validate externally authored receipts; there is no approval writer."""
    folder = folder_at(root)
    path, review_path = folder / "authorization.json", folder / "review-seal.json"
    auth, review = read_json(path, limit=16384), read_json(review_path, limit=16384)
    message, literal = auth.get("source_message_id"), auth.get("literal_message")
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
    if (
        any(auth.get(k) != v for k, v in bound.items())
        or not _fresh_message(message)
        or type(literal) is not str
        or not literal.strip()
        or hashlib.sha256(literal.strip().encode()).hexdigest() == GENERIC_LITERAL_SHA256
        or auth.get("literal_message_sha256") != hashlib.sha256(literal.encode()).hexdigest()
        or auth.get("decision") != "authorize_exact_four_cell_v3_once"
        or any(review.get(k) != v for k, v in bound.items())
        or review.get("authorization_sha256") != base.sha(path)
        or review.get("decision") != "reviewed_exact_v3_plan_and_authorization"
        or not _fresh_message(review.get("review_message_id"))
        or review["review_message_id"] == message
    ):
        raise ValueError("new_v3_authorization_and_review_required")
    return base.digest({"authorization": base.sha(path), "review": base.sha(review_path)})


def dispatch_deadline(started, now, retention_remaining):
    """The useful deadline always reserves five seconds for the same owner cleanup."""
    deadline = min(
        now + LIMITS["per_call_seconds"], started + LIMITS["seconds"], now + retention_remaining
    )
    useful = deadline - now - LIMITS["cleanup_seconds"]
    if useful <= 0:
        raise base.ProbeStop("contrast_global_deadline")
    return deadline, useful


def decision(answers):
    """A revealed-pair diagnosis, never an attribute or audit release."""
    if (
        type(answers) is not dict
        or set(answers) != set(SEQUENCE)
        or any(a not in durable.short.ANSWERS for a in answers.values())
    ):
        raise ValueError("v3_complete_answers_required")
    if "uncertain" in answers.values():
        result = "inconclusive_abstain"
    elif all(answers[n] == ("no" if n.startswith("negative") else "yes") for n in SEQUENCE):
        result = "no_native_benefit_demonstrated"
    elif answers["negative-N"] == "no" and answers["positive-N"] == "yes":
        result = "limited_revealed_pair_support"
    else:
        result = "hypothesis_not_supported"
    return {
        "decision": result,
        "previous_derived_false_positive_preserved": True,
        "independent_audit": False,
        "released_fields": [],
        "repeat_authorized": False,
    }


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
                raise RuntimeError("v3_launcher_guard")
            if time.monotonic() >= deadline:
                raise TimeoutError("v3_launcher_deadline")
            return previous._DeadlineProcess(base.subprocess.Popen(*args, **kwargs), deadline)
        except (TimeoutError, OSError):
            raise
        except Exception:  # noqa: BLE001 -- fixed sanitized launcher failure
            # The frozen collector persists only this bounded error category;
            # no raw guard error or private value crosses the process boundary.
            raise RuntimeError("v3_launcher_guard") from None

    return start


def execute(root=ROOT):
    # Missing external authority stops before lock/started/reservation/capture.
    folder = folder_at(root)
    read_json(folder / "authorization.json", limit=16384)
    read_json(folder / "review-seal.json", limit=16384)
    started = time.monotonic()
    plan = load(root)
    clearance = release(root, plan)
    return _run(
        root,
        plan,
        clearance,
        started=started,
        verify=lambda: load(root) == plan and release(root, plan) == clearance,
        launcher=lambda argv, deadline: _launcher(root, plan, clearance, argv, deadline),
        workers=base.workers,
    )


def _run(
    root,
    plan,
    clearance,
    *,
    started,
    verify,
    launcher,
    workers,
    monotonic=time.monotonic,
    wall=time.time,
):
    """Private loop seam: invented tests inject Python launchers, never the CLI."""
    if not verify():
        raise ValueError("v3_authority_before_lock_changed")
    folder = folder_at(root)
    answers = {}
    with (folder / ".lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        state = read_json(folder / "checkpoint.json")
        if state != INITIAL or (folder / "started.json").exists() or (folder / "captures").exists():
            raise ValueError("v3_consumed_no_reentry")
        base.write(
            folder / "started.json",
            {
                "plan_sha256": plan["plan_sha256"],
                "release_sha256": clearance,
                "uncertain_seconds_upper_bound": 340,
            },
            exclusive=True,
        )
        stop, first, work, cleanup_allowed = "scope_completed", None, None, True
        try:
            for number, cell in enumerate(plan["configuration"]["cells"], 1):
                if wall() >= datetime.fromisoformat(native.RETENTION).timestamp():
                    raise base.ProbeStop("contrast_input_retention_expired")
                if workers():
                    raise base.ProbeStop("concurrent_worker")
                if not verify():
                    raise ValueError("v3_identity_before_dispatch_changed")
                parent = Path(root) / "data/private/media-temp"
                parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                work = Path(tempfile.mkdtemp(prefix="galaxies-native-v3-", dir=parent))
                schema = work / "schema.json"
                frozen.write_image(schema, json.dumps(prior.SCHEMA).encode())
                image = folder / "images" / (cell["name"] + ".png")
                call_started = monotonic()
                deadline, remaining = dispatch_deadline(
                    started,
                    call_started,
                    datetime.fromisoformat(native.RETENTION).timestamp() - wall(),
                )

                def reserve(number=number, cell=cell, deadline=deadline):
                    if monotonic() >= deadline - 5:
                        raise base.ProbeStop("contrast_global_deadline")
                    if state["calls"] != number - 1 or number > 4:
                        raise ValueError("v3_call_budget")
                    if not verify():
                        raise ValueError("v3_identity_at_reservation_changed")
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
                    state.update(calls=number, elapsed_seconds=340, status="reserved_uncertain")
                    base.write(folder / "checkpoint.json", state)

                argv = [
                    str(image) if a == "<PNG>" else str(schema) if a == "<SCHEMA>" else a
                    for a in plan["configuration"]["effective_argv_template"]
                ]
                remaining = min(remaining, deadline - monotonic() - 5)
                if remaining <= 0:
                    raise base.ProbeStop("contrast_global_deadline")
                cleanup_allowed = False
                value = durable.capture(
                    argv,
                    root=root,
                    cell=cell["name"],
                    seconds=remaining,
                    reserve=reserve,
                    popen=launcher(argv, deadline - 5),
                )
                cleanup_allowed = value["cleanup_confirmed"]
                base.write(
                    folder / f"result-{number}.json",
                    {
                        "plan_sha256": plan["plan_sha256"],
                        "cell": cell,
                        "observation": value,
                        "diagnostic_comparison": prior.comparison(value, cell["expected_answer"]),
                        "phase_diagnostic": phase_diagnostic.diagnose(value)
                        if value["stop_code"] in (None, "native_timeout") and cleanup_allowed
                        else {"status": "not_assessed"},
                    },
                    exclusive=True,
                )
                if base.sha(image) != cell["png_sha256"]:
                    raise base.ProbeStop("contrast_png_after_call_changed")
                first = frozen.validate_observation(value, 1075, first)
                answers[cell["name"]] = value["answer"]
                if monotonic() > deadline:
                    raise base.ProbeStop("v3_dispatch_deadline")
                if cleanup_allowed:
                    shutil.rmtree(work)
                    work = None
                if monotonic() > deadline:
                    raise base.ProbeStop("v3_dispatch_deadline")
            if monotonic() - started > 340:
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
                elapsed_seconds=monotonic() - started,
                candidates=[],
                released_fields=[],
                test_opened=False,
                m1_changed=False,
                retry_allowed=False,
                remaining_calls=0,
                slots_closed_without_dispatch=4 - state["calls"],
                scientific_decision=decision(answers)
                if stop == "scope_completed"
                else {"decision": "technical_incomplete", "repeat_authorized": False},
            )
            base.write(folder / "checkpoint.json", state)
            if monotonic() - started > 340 and state["stop_code"] == "scope_completed":
                state.update(
                    stop_code="contrast_global_deadline",
                    elapsed_seconds=monotonic() - started,
                    scientific_decision={
                        "decision": "technical_incomplete",
                        "repeat_authorized": False,
                    },
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
        print('{"status":"v3_stopped_no_retry"}')
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()

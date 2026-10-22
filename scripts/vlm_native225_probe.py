"""Inert native225 candidate; only private invented tests may inject a launcher."""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path

from scripts import vlm_native225_capture as durable
from scripts import vlm_perception_grammar as prior

EXECUTION_RELEASED = False
PNG_SHA256 = "efa80be09f41f8250aa34c83521585d6a8c64a23f69c5b7eba0da1b4f1aeebfc"
SOURCE_PLAN_SHA256 = "f205e930cd4c7909e6d9c8115636ca4e876246a0792ffa2c1299fad13462f168"
MIN_AVAILABLE = 6 * 1024**3
RETENTION = "2026-10-22T02:59:00Z"
base = durable.short.base


def command(original):
    argv = list(original)
    for flag in ("--image-min-tokens", "--image-max-tokens"):
        if argv.count(flag) != 1 or argv[argv.index(flag) + 1] != "1024":
            raise ValueError("native225_reference_budget")
        argv[argv.index(flag) + 1] = "225"
    return argv


def proposal(source_root):
    """Read a pinned JSON only; never read tensors, media or load a model."""
    source = Path(source_root) / "data/private/issue-4-vlm-native-contrast-v3"
    raw = (source / "plan.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != SOURCE_PLAN_SHA256:
        raise ValueError("native225_source_plan")
    old = json.loads(raw)
    config = old["configuration"]
    cell = next(c for c in config["cells"] if c["name"] == "negative-N")
    if cell["png_sha256"] != PNG_SHA256:
        raise ValueError("native225_input_pin")
    value = {
        "namespace": durable.NAMESPACE,
        "source_plan_sha256": SOURCE_PLAN_SHA256,
        "argv_template": command(config["effective_argv_template"]),
        "input_path": str(source / "images/negative-N.png"),
        "png_sha256": PNG_SHA256,
        "expected_tokens": 240,
        "retention_until": RETENTION,
        "geometry": {"canvas": [384, 640], "content": [360, 640], "offset": [12, 0]},
        "limits": {
            "calls": 1,
            "useful_seconds": 55,
            "cleanup_seconds": 5,
            "global_seconds": 80,
            "available_bytes_min": MIN_AVAILABLE,
        },
        "execution_released": False,
    }
    return value | {"plan_sha256": base.digest(value)}


def check_authority(plan, authorization, review):
    pin = plan["plan_sha256"]
    if not authorization or authorization.get("plan_sha256") != pin:
        raise ValueError("native225_authorization_required")
    if (
        not review
        or review.get("plan_sha256") != pin
        or review.get("authorization_sha256") != base.digest(authorization)
        or review.get("decision") != "reviewed_native225_once"
    ):
        raise ValueError("native225_review_required")
    if (
        authorization.get("decision") != "authorize_native225_once"
        or not authorization.get("source_message_id")
        or not review.get("review_message_id")
        or authorization["source_message_id"] == review["review_message_id"]
    ):
        raise ValueError("native225_distinct_external_authority_required")


def execute(plan, authorization=None, review=None):
    """No real dispatcher is released or wired by this preparation."""
    check_authority(plan, authorization, review)
    if not EXECUTION_RELEASED or plan.get("execution_released") is not True:
        raise ValueError("native225_execution_not_released")
    raise ValueError("native225_reviewed_production_launcher_not_installed")


def _run_invented(root, argv, *, verify, available_bytes, launcher, seconds=55):
    """Fault-injection seam only; no CLI or default launcher/model command."""
    if not verify():
        raise ValueError("native225_authority_required")
    if available_bytes < MIN_AVAILABLE:
        raise ValueError("native225_memory_insufficient")
    folder = Path(root) / "data/private" / durable.NAMESPACE
    folder.mkdir(parents=True, mode=0o700, exist_ok=False)
    state = {"calls": 0, "sealed": False, "remaining_calls": 1}
    base.write(folder / "checkpoint.json", state, exclusive=True)
    started = time.monotonic()
    observation = None
    scratch = folder / "scratch"
    scratch.mkdir(mode=0o700)
    base.write(scratch / "schema.json", prior.SCHEMA, exclusive=True)

    def reserve():
        if state["calls"] or not verify():
            raise ValueError("native225_no_reentry_or_authority")
        state.update(calls=1, remaining_calls=0)
        base.write(folder / "checkpoint.json", state)

    try:
        observation = durable.capture(
            argv,
            root=Path(root),
            cell="negative-N",
            seconds=seconds,
            reserve=reserve,
            popen=launcher,
        )
        technical = (
            observation["stop_code"] is None
            and observation["cleanup_confirmed"]
            and observation["format_status"] == "valid"
            and observation.get("image_encoder_and_decode_observed") is True
            and observation.get("image_tokens_observed") == 240
        )
        result = {
            "observation": observation,
            "technical_success": technical,
            "negative_correct": technical and observation["answer"] == "no",
            "released_fields": [],
            "hypothesis_only": True,
        }
        base.write(folder / "result.json", result, exclusive=True)
        return result
    finally:
        state.update(sealed=True, remaining_calls=0, elapsed_seconds=time.monotonic() - started)
        base.write(folder / "checkpoint.json", state)
        # Durable capture writes its terminal record before returning here.
        if observation is not None and observation["cleanup_confirmed"]:
            shutil.rmtree(scratch)

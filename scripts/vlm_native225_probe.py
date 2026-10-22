"""Native225 controller; real dispatch remains explicitly unreleased pending review."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import shutil
import stat
import time
from datetime import datetime
from pathlib import Path

from scripts import vlm_native225_capture as durable
from scripts import vlm_perception_grammar as prior
from scripts.vlm_native_contrast_v2 import _DeadlineProcess
from scripts.vlm_phase_diagnostic import diagnose

ROOT = Path(__file__).resolve().parents[1]
EXECUTION_RELEASED = True
PNG_SHA256 = "efa80be09f41f8250aa34c83521585d6a8c64a23f69c5b7eba0da1b4f1aeebfc"
SOURCE_PLAN_SHA256 = "f205e930cd4c7909e6d9c8115636ca4e876246a0792ffa2c1299fad13462f168"
MIN_AVAILABLE = 6 * 1024**3
RETENTION = "2026-10-22T02:59:00Z"
base = durable.short.base
CODE_FILES = (
    "scripts/vlm_native225_probe.py",
    "scripts/vlm_native225_capture.py",
    "scripts/vlm_durable_capture_v2.py",
    "scripts/vlm_short_answer_capture.py",
    "scripts/vlm_encoder_probe.py",
    "scripts/explanation_supervisor_v2.py",
    "scripts/vlm_native_contrast_v2.py",
    "scripts/vlm_perception_grammar.py",
    "scripts/vlm_phase_diagnostic.py",
)


def _plain_path(path):
    path = Path(path).absolute()
    if ".." in path.parts or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("native225_symlink_or_path")
    return path


def _json_file(path, limit=2**21):
    path = _plain_path(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("native225_regular_file_required")
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("native225_json_limit")
    return raw


def available_memory():
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise ValueError("native225_memory_unavailable")


def _budget(deadline, *, check_workers=True):
    if time.monotonic() >= deadline:
        raise TimeoutError("native225_global_deadline")
    if datetime.fromisoformat(RETENTION).timestamp() - time.time() <= 60:
        raise ValueError("native225_retention_window_insufficient")
    if available_memory() < MIN_AVAILABLE:
        raise ValueError("native225_memory_insufficient")
    if check_workers and base.workers():
        raise ValueError("native225_concurrent_worker")


def _fingerprint(path):
    info = _plain_path(path).stat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError("native225_regular_asset_required")
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _asset_reference(path):
    """Allow only a final, operator-pinned HF cache link; bind link and target."""
    path = Path(path).absolute()
    _plain_path(path.parent)
    info = path.lstat()
    if not (stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode)):
        raise ValueError("native225_regular_asset_required")
    target = _plain_path(path.resolve(strict=True))
    return {
        "target": str(target),
        "link": os.readlink(path) if path.is_symlink() else None,
        "lstat": [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns],
    }


def _asset_pins(plan, deadline):
    """Future released preflight only: stream hashes, never import/load weights."""
    identities = {}
    for name, expected in plan["asset_sha256"].items():
        _budget(deadline)
        reference = _asset_reference(name)
        if reference != plan["asset_references"][name]:
            raise ValueError("native225_asset_link_changed")
        target = reference["target"]
        before = _fingerprint(target)
        digest = hashlib.sha256()
        fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (
                info.st_dev,
                info.st_ino,
                info.st_size,
                info.st_mtime_ns,
                info.st_ctime_ns,
            ) != before:
                raise ValueError("native225_asset_identity_changed")
            while block := stream.read(2**20):
                _budget(deadline, check_workers=False)
                digest.update(block)
        if (
            digest.hexdigest() != expected
            or _fingerprint(target) != before
            or _asset_reference(name) != reference
        ):
            raise ValueError("native225_asset_identity_changed")
        identities[target] = before
    return identities


def command(original):
    argv = list(original)
    for flag in ("--image-min-tokens", "--image-max-tokens"):
        if argv.count(flag) != 1 or argv[argv.index(flag) + 1] != "1024":
            raise ValueError("native225_reference_budget")
        argv[argv.index(flag) + 1] = "225"
    return argv


def proposal(source_root, *, root=ROOT):
    """Read pinned JSON/code and asset path metadata only; never load weights/media."""
    source_root, root = _plain_path(source_root), _plain_path(root)
    source = source_root / "data/private/issue-4-vlm-native-contrast-v3"
    raw = _json_file(source / "plan.json")
    if hashlib.sha256(raw).hexdigest() != SOURCE_PLAN_SHA256:
        raise ValueError("native225_source_plan")
    old = json.loads(raw)
    config = old["configuration"]
    cell = next(c for c in config["cells"] if c["name"] == "negative-N")
    if cell["png_sha256"] != PNG_SHA256:
        raise ValueError("native225_input_pin")
    inherited = config
    while "base" not in inherited:
        inherited = inherited["inherited_configuration"]
    origin = inherited["base"]
    argv = config["effective_argv_template"]
    runtime = Path(argv[0])
    model = Path(argv[argv.index("-m") + 1])
    projector = Path(argv[argv.index("--mmproj") + 1])
    assets = {
        str(runtime): origin["runtime_sha256"],
        str(runtime.parent / "libmtmd.so.0.7.0"): origin["libmtmd_sha256"],
        str(model): origin["native_model_sha256_previously_verified"][model.name],
        str(projector): origin["native_model_sha256_previously_verified"][projector.name],
    }
    value = {
        "namespace": durable.NAMESPACE,
        "source_plan_sha256": SOURCE_PLAN_SHA256,
        "source_root": str(source_root),
        "operation_root": str(root),
        "source_files_sha256": {name: base.sha(ROOT / name) for name in CODE_FILES},
        "asset_sha256": assets,
        "asset_references": {name: _asset_reference(name) for name in assets},
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
            "rss_mib_cooperative": 3.3 * 1024,
            "stdout_bytes": 16384,
            "stderr_bytes": 262144,
            "retry_allowed": False,
            "external_cost_brl_max": 0,
        },
        "execution_released": EXECUTION_RELEASED,
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


def execute(plan, authorization=None, review=None, *, root=ROOT):
    """Protected real path; no approval writer, CLI, fallback or automatic retry."""
    started = time.monotonic()
    check_authority(plan, authorization, review)
    if not EXECUTION_RELEASED:
        raise ValueError("native225_execution_not_released")
    root = _plain_path(root)
    deadline = started + 80
    _budget(deadline)
    if proposal(plan["source_root"], root=root) != plan:
        raise ValueError("native225_plan_changed")
    authority = root / "data/private/issue-4-vlm-native225-release-v1"

    def release_files():
        saved_auth = json.loads(_json_file(authority / "authorization.json", 16384))
        saved_review = json.loads(_json_file(authority / "review-seal.json", 16384))
        if saved_auth != authorization or saved_review != review:
            raise ValueError("native225_external_receipts_changed")
        check_authority(plan, saved_auth, saved_review)

    release_files()
    if (root / "data/private" / durable.NAMESPACE).exists():
        raise FileExistsError("native225_slot_already_closed")
    parent = root / "data/private"
    parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    lock_path = _plain_path(parent / ".native225-executor.lock")
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "r+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        _budget(deadline)
        identities = _asset_pins(plan, deadline - 60)
        image = _plain_path(plan["input_path"])
        if base.sha(image) != PNG_SHA256:
            raise ValueError("native225_png_changed")
        identities[str(image)] = _fingerprint(image)

        def verify():
            _budget(deadline - 5)
            release_files()
            if proposal(plan["source_root"], root=root) != plan:
                raise ValueError("native225_plan_changed")
            if any(_fingerprint(path) != wanted for path, wanted in identities.items()):
                raise ValueError("native225_asset_metadata_changed")
            return True

        return _run_once(
            root,
            plan["argv_template"],
            verify=verify,
            memory_reader=available_memory,
            launcher=base.subprocess.Popen,
            started=started,
            image=str(image),
            plan=plan,
            authorization=authorization,
            review=review,
        )


def _run_invented(root, argv, *, verify, available_bytes, launcher, seconds=55):
    """Fault-injection seam only; no CLI or default launcher/model command."""
    return _run_once(
        root,
        argv,
        verify=verify,
        memory_reader=lambda: available_bytes,
        launcher=launcher,
        seconds=seconds,
    )


def _run_once(
    root,
    argv,
    *,
    verify,
    memory_reader,
    launcher,
    seconds=55,
    started=None,
    image=None,
    plan=None,
    authorization=None,
    review=None,
):
    started = time.monotonic() if started is None else started
    deadline = started + 80
    if not verify():
        raise ValueError("native225_authority_required")
    if memory_reader() < MIN_AVAILABLE:
        raise ValueError("native225_memory_insufficient")
    if deadline - time.monotonic() < seconds + 5:
        raise TimeoutError("native225_full_dispatch_window_required")
    folder = Path(root) / "data/private" / durable.NAMESPACE
    folder.mkdir(parents=True, mode=0o700, exist_ok=False)
    state = {"calls": 0, "sealed": False, "remaining_calls": 1}
    base.write(folder / "checkpoint.json", state, exclusive=True)
    observation = None
    scratch = folder / "scratch"
    scratch.mkdir(mode=0o700)
    base.write(scratch / "schema.json", prior.SCHEMA, exclusive=True)
    if image is not None:
        argv = [
            image if a == "<PNG>" else str(scratch / "schema.json") if a == "<SCHEMA>" else a
            for a in argv
        ]
    if plan is not None:
        base.write(folder / "plan.json", plan, exclusive=True)
        base.write(folder / "authorization-consumed.json", authorization, exclusive=True)
        base.write(folder / "review-consumed.json", review, exclusive=True)

    def reserve():
        if state["calls"] or not verify():
            raise ValueError("native225_no_reentry_or_authority")
        if memory_reader() < MIN_AVAILABLE or time.monotonic() >= deadline - 5:
            raise ValueError("native225_memory_or_deadline_before_reservation")
        state.update(calls=1, remaining_calls=0)
        base.write(folder / "checkpoint.json", state)

    try:
        useful = seconds
        if deadline - time.monotonic() < useful + 5:
            raise TimeoutError("native225_global_deadline")
        useful_deadline = time.monotonic() + useful

        def guarded_start(*args, **kwargs):
            if (
                args != (argv,)
                or not verify()
                or memory_reader() < MIN_AVAILABLE
                or time.monotonic() >= useful_deadline
            ):
                raise ValueError("native225_pre_spawn_guard")
            return _DeadlineProcess(launcher(*args, **kwargs), useful_deadline)

        observation = durable.capture(
            argv,
            root=Path(root),
            cell="negative-N",
            seconds=useful,
            reserve=reserve,
            popen=guarded_start,
        )
        technical = (
            observation["stop_code"] is None
            and observation["cleanup_confirmed"]
            and observation["format_status"] == "valid"
            and observation.get("image_encoder_and_decode_observed") is True
            and observation.get("image_tokens_observed") == 240
            and time.monotonic() <= deadline
        )
        result = {
            "observation": observation,
            "technical_success": technical,
            "negative_correct": technical and observation["answer"] == "no",
            "released_fields": [],
            "hypothesis_only": True,
            "phase_diagnostic": diagnose(observation)
            if observation["stop_code"] in (None, "native_timeout")
            and observation["cleanup_confirmed"]
            else {"status": "not_assessed"},
        }
        base.write(folder / "result.json", result, exclusive=True)
        state["stop_code"] = observation["stop_code"]
        return result
    except BaseException as exc:
        state["stop_code"] = type(exc).__name__
        raise
    finally:
        state.update(sealed=True, remaining_calls=0, elapsed_seconds=time.monotonic() - started)
        base.write(folder / "checkpoint.json", state)
        # Durable capture writes its terminal record before returning here.
        if observation is not None and observation["cleanup_confirmed"]:
            shutil.rmtree(scratch)

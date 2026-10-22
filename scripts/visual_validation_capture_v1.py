"""Bounded attribute capture over the frozen process owner. Native dispatch is inactive."""

from __future__ import annotations

import hashlib
import math
import os
import signal
import stat
import threading

from scripts import vlm_durable_capture_v2 as frozen
from scripts import vlm_encoder_probe as owner
from scripts.visual_validation_contract_v1 import (
    PROPOSAL_SHA256,
    is_sha,
    plain,
    require,
    strict_json,
)
from scripts.vlm_per_frame import parse_output
from scripts.vlm_product_v16 import decode as product_decode
from scripts.vlm_short_answer_capture import decode as relation_decode

NAMESPACE = "issue-4-visual-validation-run-v1"
DISPATCH_RELEASED = False
KINDS = ("person_visible", "product_visible_early", "screen_text", "relation")


def _folder(root, call_id, *, create):
    root = plain(root)
    require(type(call_id) is int and 1 <= call_id <= 397, "visual_call_id")
    fd = os.open("/", frozen.DIRECTORY)
    try:
        for part in root.parts[1:]:
            child = frozen._directory(fd, part)
            os.close(fd)
            fd = child
        for part in ("data", "private", NAMESPACE, "captures"):
            child = frozen._directory(fd, part, create=create)
            os.close(fd)
            fd = child
            if part in (NAMESPACE, "captures"):
                info = os.fstat(fd)
                require(
                    info.st_uid == os.getuid() and not stat.S_IMODE(info.st_mode) & 0o077,
                    "visual_capture_directory_not_private",
                )
        name = f"call-{call_id:04d}"
        if create:
            os.mkdir(name, 0o700, dir_fd=fd)
            os.fsync(fd)
        child = frozen._directory(fd, name)
        os.close(fd)
        fd = child
        info = os.fstat(fd)
        require(
            info.st_uid == os.getuid() and not stat.S_IMODE(info.st_mode) & 0o077,
            "visual_capture_directory_not_private",
        )
        return fd
    except BaseException:
        os.close(fd)
        raise


class Journal(frozen.Journal):
    def __init__(self, root, call_id):
        self.directory = _folder(root, call_id, create=True)
        self.stdout = None
        self.lock = threading.Lock()
        self.failed = threading.Event()
        self.closed = False
        self.stderr = bytearray()
        self.hash = hashlib.sha256()
        self.state = {
            "schema": "vlm-private-capture-v2",
            "phase": "created",
            "terminal": False,
            "cleanup_confirmed": False,
            "stdout_bytes": 0,
            "stdout_sha256": self.hash.hexdigest(),
            "stderr_bytes": 0,
            "stdout_eof": False,
            "stderr_eof": False,
            "progress": {},
        }
        try:
            self.stdout = os.open(
                "stdout.bin",
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=self.directory,
            )
            os.fsync(self.stdout)
            os.fsync(self.directory)
            self.checkpoint()
        except BaseException:
            self.close()
            raise


def parse_response(kind, raw):
    require(kind in KINDS and len(raw) <= 16384, "visual_response_kind_or_size")
    strict_json(raw)  # A complete object, with no prefix, suffix, duplicates or nonfinite values.
    if kind == "relation":
        return {"answer": relation_decode(raw)}
    text = raw.decode("utf-8")
    if kind == "product_visible_early":
        native, value = product_decode(text, "state_first")
        return {"native": native, "value": value}
    return parse_output(text, [kind])


def _technical(result):
    return (
        result["stop_code"] is None
        and result["format_status"] == "valid"
        and result["returncode"] == 0
        and result["cleanup_confirmed"] is True
        and result["process_started"] is True
        and result["image_encoder_and_decode_observed"] is True
        and result["image_tokens_observed"] == result["expected_image_tokens"]
        and result["runtime_seconds"] <= 80
        and result["peak_rss_mib"] <= 3.3 * 1024
    )


def _capture_invented(
    argv, *, root, call_id, kind, png_sha256, expected_tokens, reserve, launcher, seconds=75
):
    """Injection seam only: no default launcher, native command builder or release writer."""
    require(callable(launcher) and callable(reserve), "visual_injected_owner_required")
    require(type(seconds) in (int, float) and 0 < seconds <= 75, "visual_capture_deadline")
    require(
        kind in KINDS
        and is_sha(png_sha256)
        and type(expected_tokens) is int
        and 225 <= expected_tokens <= 3072,
        "visual_capture_contract",
    )
    require(threading.current_thread() is threading.main_thread(), "visual_capture_main_thread")
    journal = Journal(root, call_id)
    cancelled = threading.Event()
    previous = signal.getsignal(signal.SIGTERM)

    def terminate(*_):
        cancelled.set()

    def consume():
        if cancelled.is_set():
            raise KeyboardInterrupt
        reserve()
        journal.phase("reserved")

    def start(*args, **kwargs):
        if cancelled.is_set():
            raise KeyboardInterrupt
        process = launcher(*args, **kwargs)
        wrapped = frozen.Process(process, journal, cancelled)
        try:
            journal.started(process)
        except BaseException:  # noqa: BLE001 -- preserve spawned handle ownership
            journal.failed.set()
        return wrapped  # The existing owner always receives every spawned handle.

    completed = None
    signal.signal(signal.SIGTERM, terminate)
    try:
        result = owner.capture(argv, seconds=seconds, reserve=consume, popen=start)
        result.pop("native", None)
        result.pop("projected_value", None)
        result.update(
            schema="visual-attribute-capture-v1",
            capture_origin="injected_unreleased",
            kind=kind,
            input_png_sha256=png_sha256,
            expected_image_tokens=expected_tokens,
            proposal_sha256=PROPOSAL_SHA256,
            parsed_response=None,
            format_status="not_assessed_technical_failure",
        )
        # The frozen owner's old decoder targets item_first. Only that decoder
        # rejection can be superseded by the strict, explicitly selected parser.
        if result["stop_code"] == "stdout_invalid_original_schema":
            result["stop_code"] = None
        if cancelled.is_set() and result["stop_code"] is None:
            result["stop_code"] = "native_cancelled"
        if result["stop_code"] is None:
            raw = frozen._read(journal.directory, "stdout.bin", 16384)
            try:
                result["parsed_response"] = parse_response(kind, raw)
                result["format_status"] = "valid"
            except (ValueError, TypeError, UnicodeError, RecursionError):
                result.update(stop_code="attribute_schema_invalid", format_status="invalid")
        result["technical_success"] = _technical(result)
        completed = journal.finish(result)
        return completed
    finally:
        signal.signal(signal.SIGTERM, previous)
        journal.close()
        if cancelled.is_set() and completed is not None and completed["stop_code"] is None:
            raise KeyboardInterrupt


def read_capture(root, call_id, *, kind, png_sha256, expected_tokens):
    """Read a terminal generic capture; never reinterpret it as the short-answer schema."""
    directory = _folder(root, call_id, create=False)
    try:
        state = strict_json(frozen._read(directory, "state.json", frozen.STATE_LIMIT))
        frozen._state(state)
        require(state["terminal"], "visual_capture_not_terminal")
        raw = frozen._read(directory, "stdout.bin", 16384)
        require(
            len(raw) == state["stdout_bytes"]
            and hashlib.sha256(raw).hexdigest() == state["stdout_sha256"],
            "visual_capture_raw_changed",
        )
        encoded = frozen._read(directory, "result.json", frozen.RESULT_LIMIT)
        require(
            hashlib.sha256(encoded).hexdigest() == state["result_sha256"],
            "visual_capture_result_changed",
        )
        result = strict_json(encoded)
        require(type(result) is dict, "visual_capture_result_type")
        require(
            result.get("schema") == "visual-attribute-capture-v1"
            and result.get("capture_origin") == "injected_unreleased"
            and result.get("proposal_sha256") == PROPOSAL_SHA256
            and result.get("kind") == kind
            and result.get("input_png_sha256") == png_sha256
            and result.get("expected_image_tokens") == expected_tokens,
            "visual_capture_binding_changed",
        )
        require(
            type(result.get("technical_success")) is bool
            and type(result.get("process_started")) is bool
            and type(result.get("cleanup_confirmed")) is bool
            and (result.get("returncode") is None or type(result["returncode"]) is int)
            and all(
                type(result.get(k)) in (int, float) and math.isfinite(result[k]) and result[k] >= 0
                for k in ("runtime_seconds", "peak_rss_mib")
            ),
            "visual_capture_result_types",
        )
        observations = {
            k: v
            for k, v in result.items()
            if k
            in {
                "events",
                "failures",
                "warnings",
                "image_encoder_and_decode_observed",
                "image_tokens_observed",
                "raw_stderr_retained",
                "discarded_stderr_bytes",
                "representation_quality_or_attention_proven",
            }
        }
        frozen._observations(observations)
        require(
            result["cleanup_confirmed"] == state["cleanup_confirmed"]
            and result["technical_success"] is _technical(result),
            "visual_capture_terminal_inconsistent",
        )
        if result["technical_success"]:
            require(
                state["stdout_eof"]
                and state["stderr_eof"]
                and result["parsed_response"] == parse_response(kind, raw),
                "visual_capture_parse_changed",
            )
            lease = strict_json(frozen._read(directory, "process-lease.json", frozen.STATE_LIMIT))
            require(
                lease["schema"] == "vlm-owned-process-v2"
                and lease["pgid"] == lease["leader"]["pid"],
                "visual_capture_lease",
            )
        return {
            "result": result,
            "result_sha256": state["result_sha256"],
            "raw_sha256": state["stdout_sha256"],
        }
    finally:
        os.close(directory)


def dispatch(*args, authorization=None, technical_review=None, **kwargs):
    """Inactive by construction. No reservation, path creation or callback before release."""
    require(authorization is not None, "visual_authorization_required")
    require(technical_review is not None, "visual_technical_review_required")
    require(DISPATCH_RELEASED, "visual_dispatch_not_released")
    # A future activation must add reviewed native argv, root/assets, global ledger,
    # image-use lease and blind-annotation checks; passing dictionaries is not authority.
    raise ValueError("visual_native_controller_activation_required")

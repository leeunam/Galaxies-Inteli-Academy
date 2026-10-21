"""Invented streams and pixels only; never launch the native runtime."""

import copy
import io
import json
import socket
from pathlib import Path

import pytest
from PIL import Image

from scripts import vlm_encoder_probe as probe

LOG = b"encoding mtmd batch, n_chunks = 1 (done = 1, total = 3)\nmtmd batch encoding done in 123 ms\ndecoding image batch 1/1, n_tokens_batch = 128\nimage decoded (batch 1/1) in 23 ms\n"
NATIVE = b'{"item_configuration":"absent","state":"no_target","presented_categories":[]}'


@pytest.fixture(autouse=True)
def no_native_or_network(monkeypatch):
    def forbidden(*a, **kw):
        raise AssertionError("native_process_or_network_forbidden_in_unit_checks")

    monkeypatch.setattr(probe.subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)


def test_only_verbosity_changes_in_original_argv():
    old = [
        "native",
        "-m",
        "model",
        "--mmproj",
        "projector",
        "--verbosity",
        "0",
        "--image",
        "<PNG>",
        "--json-schema-file",
        "<SCHEMA>",
        "--prompt",
        "unchanged",
    ]
    new = probe.command(old, Path("crop.png"), Path("schema.json"))
    normalized = [
        "<PNG>" if a == "crop.png" else "<SCHEMA>" if a == "schema.json" else a for a in new
    ]
    assert [(a, b) for a, b in zip(old, normalized, strict=True) if a != b] == [("0", "3")]
    assert old[old.index("--verbosity") + 1] == "0"


def test_events_prove_path_only_and_suppress_unknown_text():
    sentinel = b"PRIVATE_IMAGE_OR_PROMPT_TEXT_DO_NOT_RETAIN"
    result = probe.summarize(NATIVE, sentinel + b"\n" + LOG + b"\n" + sentinel, 0)
    assert result["image_encoder_and_decode_observed"] and result["image_tokens_observed"] == 128
    assert result["stop_code"] is None and result["projected_value"] is False
    assert result["representation_quality_or_attention_proven"] is False
    assert sentinel.decode() not in json.dumps(result)
    assert result["raw_stdout_retained"] is result["raw_stderr_retained"] is False


@pytest.mark.parametrize(
    "log",
    [
        b"",
        LOG.replace(b"n_chunks = 1", b"n_chunks = 0"),
        LOG.replace(b"n_tokens_batch = 128", b"n_tokens_batch = 0"),
        LOG.replace(b"image decoded (batch 1/1) in 23 ms\n", b""),
        LOG + LOG,
        LOG.splitlines()[2] + b"\n" + LOG,
    ],
)
def test_absent_duplicated_or_inconsistent_markers_do_not_prove_image_consumption(log):
    result = probe.summarize(NATIVE, log, 0)
    assert result["stop_code"] == "diagnostics_insufficient"
    assert result["image_encoder_and_decode_observed"] is False


def test_stderr_never_repairs_stdout_or_leaks_response():
    result = probe.summarize(b"PRIVATE_UNEXPECTED_RESPONSE", LOG + b"\n" + NATIVE, 0)
    assert result["native"] is None and result["stop_code"] == "stdout_invalid_original_schema"
    assert "PRIVATE_UNEXPECTED_RESPONSE" not in json.dumps(result)


def test_direct_encoder_failure_is_identified_without_error_text():
    result = probe.summarize(b"", b"Failed to encode mtmd batch, res = -7\nPRIVATE_DETAIL", 1)
    assert result["stop_code"] == "encoder_failed"
    assert result["failures"] == [{"code": "encoder_failed", "number": -7}]
    assert "PRIVATE_DETAIL" not in json.dumps(result)


def test_factory_failure_consumes_before_spawn_and_returns_sanitized_diagnostic():
    calls = []

    def fail(*a, **kw):
        assert calls == ["reserved"]
        raise RuntimeError("PRIVATE_EXCEPTION_VALUE")

    result = probe.capture(
        ["invented"], seconds=1, reserve=lambda: calls.append("reserved"), popen=fail
    )
    assert calls == ["reserved"] and result["stop_code"] == "native_operation_failed"
    assert result["cleanup_confirmed"] and "PRIVATE_EXCEPTION_VALUE" not in json.dumps(result)


def test_independent_stream_capture_and_cleanup_without_a_real_process(monkeypatch):
    calls = []

    class Fake:
        pid = 99999999
        returncode = 0
        stdout = io.BytesIO(NATIVE)
        stderr = io.BytesIO(LOG)

        def poll(self):
            return 0

        def wait(self, timeout=None):
            calls.append("wait")
            return 0

    monkeypatch.setattr(probe.os, "killpg", lambda *a: calls.append("kill_owned_group"))

    def factory(*a, **kw):
        assert calls == ["reserved"]
        assert kw["start_new_session"] and "MTMD_DEBUG_GRAPH" not in kw["env"]
        return Fake()

    result = probe.capture(
        ["invented"], seconds=1, reserve=lambda: calls.append("reserved"), popen=factory
    )
    assert result["stop_code"] is None and result["cleanup_confirmed"]
    assert "kill_owned_group" in calls and "wait" in calls


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("timeout", "native_timeout"),
        ("cancel", "native_cancelled"),
        ("overflow", "output_limit_or_unclosed_pipe"),
    ],
)
def test_capture_stops_owned_fake_process_and_retains_no_raw_output(monkeypatch, mode, expected):
    class Fake:
        pid = 99999999
        returncode = None
        stdout = io.BytesIO(
            b"x" * (probe.LIMITS["stdout_bytes"] + 1) if mode == "overflow" else b""
        )
        stderr = io.BytesIO(LOG)

        def poll(self):
            if mode == "cancel":
                raise KeyboardInterrupt("PRIVATE_CANCELLATION_TEXT")
            return self.returncode

        def wait(self, timeout=None):
            self.returncode = -9
            return self.returncode

    process = Fake()
    monkeypatch.setattr(probe.os, "killpg", lambda *a: setattr(process, "returncode", -9))
    monkeypatch.setattr(
        probe.psutil,
        "Process",
        lambda *a: type(
            "MemoryOnly", (), {"memory_info": lambda self: type("RSS", (), {"rss": 0})()}
        )(),
    )
    reserved = []
    result = probe.capture(
        ["invented"],
        seconds=0.001,
        reserve=lambda: reserved.append(1),
        popen=lambda *a, **kw: process,
    )
    assert reserved == [1] and result["cleanup_confirmed"]
    assert result["stop_code"] == expected and result["native"] is None
    assert "PRIVATE_CANCELLATION_TEXT" not in json.dumps(result)


@pytest.fixture
def fixture_queue(tmp_path, monkeypatch):
    sheet = tmp_path / "data/private/invented.png"
    sheet.parent.mkdir(parents=True)
    Image.new("RGB", (1280, 360), "white").save(sheet)
    cell = sheet.parent / "crop.png"
    Image.new("RGB", (320, 330), "white").save(cell)
    rows = [
        {
            "png_sha256": probe.sha(cell),
            "seconds": 0.2,
            "source_frame": 1,
            "sheet_path": str(sheet.relative_to(tmp_path)),
            "sheet_sha256": probe.sha(sheet),
        },
        {"png_sha256": probe.sha(cell), "seconds": 0.2},
    ]
    config = {
        "cases": rows,
        "original_argv": [
            "invented",
            "--verbosity",
            "0",
            "--image",
            "<PNG>",
            "--json-schema-file",
            "<SCHEMA>",
        ],
    }
    monkeypatch.setattr(probe, "configuration", lambda *a: copy.deepcopy(config))
    monkeypatch.setattr(probe, "workers", list)
    plan = probe.prepare(tmp_path)
    folder = tmp_path / probe.QUEUE
    text = "invented fixture review, never a real authorization"
    release = {
        "plan_sha256": plan["plan_sha256"],
        "configuration_sha256": plan["configuration_sha256"],
        "decision": "released_for_this_encoder_probe_only",
        "reviewer_thread_id": "01a15713-2572-7544-8329-c229ea2ff0f5",
        "source_message_id": "INVENTED_REVIEW",
        "literal_message": text,
        "literal_message_sha256": __import__("hashlib").sha256(text.encode()).hexdigest(),
    }
    calls = []
    paths = []

    def capture(argv, *, seconds, reserve):
        assert 0 < seconds <= 180
        reserve()
        calls.append(1)
        paths.append(Path(argv[argv.index("--image") + 1]).parent)
        return probe.summarize(NATIVE, LOG, 0) | {"cleanup_confirmed": True}

    monkeypatch.setattr(probe, "capture", capture)
    return tmp_path, folder, plan, release, calls, paths


def test_missing_review_never_starts_or_reserves(fixture_queue):
    root, folder, _, _, calls, _ = fixture_queue
    with pytest.raises(FileNotFoundError):
        probe.execute(root)
    assert not calls and not (folder / "started.json").exists()


def test_two_fixed_calls_seal_once_and_diagnostics_precede_cleanup(fixture_queue):
    root, folder, _, release, calls, paths = fixture_queue
    probe.write(folder / "technical-release.json", release, exclusive=True)
    result = probe.execute(root)
    assert result["calls"] == len(calls) == 2 and result["sealed"]
    assert result["candidates"] == result["released_fields"] == []
    assert not result["test_opened"] and not result["m1_changed"]
    assert (folder / "result-1.json").exists() and (folder / "result-2.json").exists()
    assert all(not p.exists() for p in paths)
    before = probe.sha(folder / "checkpoint.json")
    with pytest.raises(ValueError, match="no_reentry"):
        probe.execute(root)
    assert len(calls) == 2 and probe.sha(folder / "checkpoint.json") == before


@pytest.mark.parametrize(
    "code",
    [
        "encoder_failed",
        "diagnostics_insufficient",
        "native_timeout",
        "native_cancelled",
        "cleanup_unconfirmed",
    ],
)
def test_first_failure_stops_before_white_and_preserves_sanitized_result(
    fixture_queue, monkeypatch, code
):
    root, folder, _, release, calls, paths = fixture_queue
    probe.write(folder / "technical-release.json", release, exclusive=True)

    def failed(argv, *, seconds, reserve):
        reserve()
        calls.append(1)
        paths.append(Path(argv[argv.index("--image") + 1]).parent)
        return probe.summarize(NATIVE, LOG, 0) | {
            "cleanup_confirmed": code != "cleanup_unconfirmed",
            "stop_code": code,
        }

    monkeypatch.setattr(probe, "capture", failed)
    with pytest.raises(probe.ProbeStop):
        probe.execute(root)
    state = json.loads((folder / "checkpoint.json").read_bytes())
    assert state["calls"] == len(calls) == 1 and state["sealed"] and state["stop_code"] == code
    assert (folder / "result-1.json").exists() and not (folder / "reservation-2.json").exists()
    assert paths[0].exists() is (code == "cleanup_unconfirmed")


def test_start_marker_prevents_second_entry_even_before_first_reservation(fixture_queue):
    root, folder, _, release, calls, _ = fixture_queue
    probe.write(folder / "technical-release.json", release, exclusive=True)
    probe.write(folder / "started.json", {"invented_crash_marker": True}, exclusive=True)
    with pytest.raises(ValueError, match="no_reentry"):
        probe.execute(root)
    assert not calls

"""Trace adendum: one invented input, fake processes, no network."""

import copy
import hashlib
import json
import socket
from pathlib import Path

import pytest
from PIL import Image

from scripts import vlm_encoder_trace as trace


@pytest.fixture(autouse=True)
def no_native_or_network(monkeypatch):
    def forbidden(*a, **kw):
        raise AssertionError("native_or_network_forbidden")

    monkeypatch.setattr(trace.base.subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)


def test_exact_trace_difference_and_budget():
    original = [
        "invented",
        "--verbosity",
        "0",
        "--image",
        "<PNG>",
        "--json-schema-file",
        "<SCHEMA>",
    ]
    prior = trace.base.command(original, "<PNG>", "<SCHEMA>")
    current = trace.command(original, "<PNG>", "<SCHEMA>")
    assert [(a, b) for a, b in zip(prior, current, strict=True) if a != b] == [("3", "4")]
    assert trace.LIMITS["calls"] == 1 and trace.LIMITS["seconds"] == 90
    assert trace.LIMITS["white_calls"] == 0 and original[2] == "0"


@pytest.fixture
def invented(tmp_path, monkeypatch):
    source = tmp_path / "sheet.png"
    crop = tmp_path / "crop.png"
    Image.new("RGB", (1280, 360), "white").save(source)
    Image.new("RGB", (320, 330), "white").save(crop)
    config = {
        "base": {
            "cases": [
                {
                    "sheet_path": "sheet.png",
                    "sheet_sha256": trace.base.sha(source),
                    "png_sha256": trace.base.sha(crop),
                    "source_frame": 1,
                    "seconds": 0.2,
                }
            ],
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
    }
    monkeypatch.setattr(trace, "configuration", lambda *a: copy.deepcopy(config))
    monkeypatch.setattr(trace.base, "workers", list)
    plan = trace.prepare(tmp_path)
    folder = tmp_path / trace.QUEUE
    literal = "INVENTED REVIEW ONLY"
    review = {
        "plan_sha256": plan["plan_sha256"],
        "configuration_sha256": plan["configuration_sha256"],
        "decision": "released_for_this_encoder_probe_only",
        "reviewer_thread_id": "01a15713-2572-7544-8329-c229ea2ff0f5",
        "source_message_id": "INVENTED",
        "literal_message": literal,
        "literal_message_sha256": hashlib.sha256(literal.encode()).hexdigest(),
    }
    return tmp_path, folder, review


def test_missing_review_does_not_start(invented):
    root, folder, _ = invented
    with pytest.raises(FileNotFoundError):
        trace.execute(root)
    assert not (folder / "started.json").exists()


@pytest.mark.parametrize("stop_code", [None, "diagnostics_insufficient", "native_timeout"])
def test_single_dispatch_and_original_stdout_parser(invented, monkeypatch, stop_code):
    root, folder, review = invented
    trace.base.write(folder / "technical-release.json", review, exclusive=True)
    calls = []

    def capture(argv, *, seconds, reserve):
        assert 0 < seconds <= 85 and argv[argv.index("--verbosity") + 1] == "4"
        reserve()
        assert json.loads((folder / "checkpoint.json").read_bytes())["calls"] == 1
        calls.append(Path(argv[argv.index("--image") + 1]).parent)
        native = b'{"item_configuration":"absent","state":"no_target","presented_categories":[]}'
        result = trace.base.summarize(native, b"", 0)
        assert result["projected_value"] is False
        return result | {"cleanup_confirmed": True, "stop_code": stop_code}

    monkeypatch.setattr(trace.base, "capture", capture)
    if stop_code:
        with pytest.raises(trace.base.ProbeStop):
            trace.execute(root)
    else:
        trace.execute(root)
    state = json.loads((folder / "checkpoint.json").read_bytes())
    assert state["sealed"] and state["calls"] == len(calls) == 1
    assert (folder / "result-1.json").exists() and not (folder / "reservation-2.json").exists()
    assert not calls[0].exists()
    with pytest.raises(ValueError, match="no_reentry"):
        trace.execute(root)
    assert len(calls) == 1


def test_source_binding_change_refuses_before_marker(invented, monkeypatch):
    root, folder, review = invented
    trace.base.write(folder / "technical-release.json", review, exclusive=True)
    monkeypatch.setattr(trace, "configuration", lambda *a: {"changed": True})
    with pytest.raises(ValueError, match="identity_changed"):
        trace.execute(root)
    assert not (folder / "started.json").exists()

"""Four invented cells only: immutable inputs, bounded budget, no model or network."""

import copy
import hashlib
import json
import socket
from pathlib import Path

import pytest
from PIL import Image

from scripts import vlm_perception_grammar as flow


@pytest.fixture(autouse=True)
def no_native_or_network(monkeypatch):
    def forbidden(*a, **kw):
        raise AssertionError("native_or_network_forbidden")

    monkeypatch.setattr(flow.base.subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)


def test_only_schema_application_differs_with_same_full_prompt():
    original = [
        "native",
        "--verbosity",
        "0",
        "--prompt",
        "OLD",
        "--image",
        "<PNG>",
        "--json-schema-file",
        "<SCHEMA>",
    ]
    constrained = flow.command(original, "<PNG>", "<SCHEMA>", True)
    free = flow.command(original, "<PNG>", "<SCHEMA>", False)
    index = constrained.index("--json-schema-file")
    assert constrained[:index] + constrained[index + 2 :] == free
    assert free[free.index("--prompt") + 1] == flow.PROMPT
    assert all(f'"{a}"' in flow.PROMPT for a in flow.short.ANSWERS)
    assert flow.LIMITS["calls"] == 4 and flow.LIMITS["seconds"] == 180
    assert flow.LIMITS["per_call_seconds"] == 45 and flow.LIMITS["cleanup_seconds"] == 5


@pytest.fixture
def invented(tmp_path, monkeypatch):
    sheet = tmp_path / "sheet.png"
    crop = tmp_path / "crop.png"
    Image.new("RGB", (1280, 360), "white").save(sheet)
    Image.new("RGB", (320, 330), "white").save(crop)
    rows = [
        {
            "alias": alias,
            "source_frame": frame,
            "seconds": seconds,
            "sheet_path": "sheet.png",
            "sheet_sha256": flow.base.sha(sheet),
            "png_sha256": flow.base.sha(crop),
            "expected_answer": expected,
        }
        for alias, frame, seconds, expected in [
            ("positive", 1, 0.2, "yes"),
            ("negative", 3, 2.8, "no"),
        ]
    ]
    config = {
        "pair": {"cases": rows},
        "base": {
            "original_argv": [
                "native",
                "--verbosity",
                "0",
                "--prompt",
                "OLD",
                "--image",
                "<PNG>",
                "--json-schema-file",
                "<SCHEMA>",
            ]
        },
    }
    monkeypatch.setattr(flow, "configuration", lambda *a: copy.deepcopy(config))
    monkeypatch.setattr(flow.base, "workers", list)
    plan = flow.prepare(tmp_path)
    folder = tmp_path / flow.QUEUE
    literal = "INVENTED FOUR CELL REVIEW"
    review = {
        "plan_sha256": plan["plan_sha256"],
        "configuration_sha256": plan["configuration_sha256"],
        "decision": "released_for_this_perception_contrast_only",
        "reviewer_thread_id": "01a15713-2572-7544-8329-c229ea2ff0f5",
        "source_message_id": "INVENTED",
        "literal_message": literal,
        "literal_message_sha256": hashlib.sha256(literal.encode()).hexdigest(),
    }
    calls = []

    def capture(argv, *, seconds, reserve):
        assert 0 < seconds <= 40 and argv[argv.index("--prompt") + 1] == flow.PROMPT
        reserve()
        calls.append(Path(argv[argv.index("--image") + 1]).parent)
        alias = flow.SEQUENCE[len(calls) - 1][0]
        return {
            "cleanup_confirmed": True,
            "stop_code": None,
            "format_status": "valid",
            "answer": "yes" if alias == "positive" else "no",
        }

    monkeypatch.setattr(flow.short, "capture", capture)
    return tmp_path, folder, review, calls, capture, config


def approve(invented):
    _, folder, review, *_ = invented
    flow.base.write(folder / "technical-release.json", review, exclusive=True)


def test_missing_review_does_not_start(invented):
    root, folder, _, calls, *_ = invented
    with pytest.raises(FileNotFoundError):
        flow.execute(root)
    assert not calls and not (folder / "started.json").exists()


def test_four_fixed_cells_and_durable_result_before_cleanup(invented, monkeypatch):
    root, folder, _, calls, *_ = invented
    approve(invented)
    original_rmtree = flow.shutil.rmtree

    def clean(path):
        assert (folder / f"result-{len(calls)}.json").exists()
        original_rmtree(path)

    monkeypatch.setattr(flow.shutil, "rmtree", clean)
    result = flow.execute(root)
    assert result["sealed"] and result["calls"] == len(calls) == 4
    assert [(x["alias"], x["grammar"]) for x in result["operations"]] == list(flow.SEQUENCE)
    assert all(x["diagnostic_comparison"] == "correct" for x in result["operations"])
    assert all(not x.exists() for x in calls)
    before = flow.base.sha(folder / "checkpoint.json")
    with pytest.raises(ValueError, match="no_reentry"):
        flow.execute(root)
    assert before == flow.base.sha(folder / "checkpoint.json") and len(calls) == 4


def test_format_failure_and_abstention_continue_predefined_cells(invented, monkeypatch):
    root, folder, _, calls, capture, *_ = invented
    approve(invented)

    def observed(*a, **kw):
        result = capture(*a, **kw)
        if len(calls) == 1:
            result.update(format_status="invalid", answer=None)
        if len(calls) == 2:
            result.update(answer="uncertain")
        if len(calls) == 4:
            result.update(answer="yes")
        return result

    monkeypatch.setattr(flow.short, "capture", observed)
    result = flow.execute(root)
    assert result["calls"] == 4 and result["stop_code"] == "scope_completed"
    assert [x["diagnostic_comparison"] for x in result["operations"]] == [
        "format_invalid",
        "abstention",
        "correct",
        "incorrect",
    ]
    assert (folder / "result-4.json").exists()


@pytest.mark.parametrize(
    "code",
    [
        "diagnostics_insufficient",
        "native_timeout",
        "native_resource_limit",
        "native_cancelled",
        "cleanup_unconfirmed",
    ],
)
def test_technical_failure_stops_without_reentry(invented, monkeypatch, code):
    root, folder, _, calls, capture, *_ = invented
    approve(invented)

    def failed(*a, **kw):
        return capture(*a, **kw) | {
            "stop_code": code,
            "cleanup_confirmed": code != "cleanup_unconfirmed",
        }

    monkeypatch.setattr(flow.short, "capture", failed)
    with pytest.raises(flow.base.ProbeStop):
        flow.execute(root)
    state = json.loads((folder / "checkpoint.json").read_bytes())
    assert state["calls"] == len(calls) == 1 and state["sealed"] and state["stop_code"] == code
    assert (folder / "result-1.json").exists() and not (folder / "reservation-2.json").exists()
    assert calls[0].exists() is (code == "cleanup_unconfirmed")


def test_source_change_refuses_before_start_marker(invented, monkeypatch):
    root, folder, *_ = invented
    approve(invented)
    monkeypatch.setattr(flow, "configuration", lambda *a: {"changed": True})
    with pytest.raises(ValueError, match="identity_changed"):
        flow.execute(root)
    assert not (folder / "started.json").exists()


def test_pixel_change_consumes_zero_calls_and_seals(invented):
    root, folder, _, calls, *_ = invented
    approve(invented)
    Image.new("RGB", (1280, 360), "black").save(root / "sheet.png")
    with pytest.raises(ValueError, match="sheet_changed"):
        flow.execute(root)
    state = json.loads((folder / "checkpoint.json").read_bytes())
    assert state["calls"] == len(calls) == 0 and state["sealed"]


def test_uncertain_start_marker_prevents_any_dispatch(invented):
    root, folder, _, calls, *_ = invented
    approve(invented)
    flow.base.write(folder / "started.json", {"invented_crash": True}, exclusive=True)
    with pytest.raises(ValueError, match="no_reentry"):
        flow.execute(root)
    assert not calls

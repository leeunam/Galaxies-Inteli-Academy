"""Single invented negative, no native runtime/network/credentials."""

import copy
import hashlib
import json
import socket
from pathlib import Path

import pytest
from PIL import Image

from scripts import vlm_spatial_negative_60 as flow


@pytest.fixture(autouse=True)
def no_native_or_network(monkeypatch):
    def forbidden(*a, **kw):
        raise AssertionError("native_or_network_forbidden")

    monkeypatch.setattr(flow.base.subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)


@pytest.fixture
def invented(tmp_path, monkeypatch):
    sheet = tmp_path / "sheet.png"
    crop = tmp_path / "crop.png"
    Image.new("RGB", (1280, 360), "white").save(sheet)
    Image.new("RGB", (320, 330), "white").save(crop)
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
        "--image-min-tokens",
        "64",
        "--image-max-tokens",
        "128",
    ]
    config = {
        "original_argv": original,
        "reference_tokens": 100,
        "case": {
            "alias": "negative",
            "source_frame": 3,
            "seconds": 2.8,
            "sheet_path": "sheet.png",
            "sheet_sha256": flow.base.sha(sheet),
            "png_sha256": flow.base.sha(crop),
            "expected_answer": "no",
        },
    }
    monkeypatch.setattr(flow, "configuration", lambda *a: copy.deepcopy(config))
    monkeypatch.setattr(flow.base, "workers", list)
    plan = flow.prepare(tmp_path)
    folder = tmp_path / flow.QUEUE
    literal = "INVENTED NEGATIVE REVIEW"
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
        assert 0 < seconds <= 55
        assert argv == flow.prior.command(
            original,
            Path(argv[argv.index("--image") + 1]),
            Path(argv[argv.index("--json-schema-file") + 1]),
        )
        reserve()
        assert json.loads((folder / "checkpoint.json").read_bytes())["calls"] == 1
        calls.append(Path(argv[argv.index("--image") + 1]).parent)
        return {
            "stop_code": None,
            "cleanup_confirmed": True,
            "image_tokens_observed": 1056,
            "format_status": "valid",
            "answer": "no",
        }

    monkeypatch.setattr(flow.prior.prior.short, "capture", capture)
    return tmp_path, folder, review, calls, capture


def approve(invented):
    _, folder, review, *_ = invented
    flow.base.write(folder / "technical-release.json", review, exclusive=True)


def test_new_budget_is_one_negative_60_dispatch_70_global():
    assert flow.LIMITS["calls"] == 1 and flow.LIMITS["seconds"] == 70
    assert flow.LIMITS["per_call_seconds"] == 60 and flow.LIMITS["cleanup_seconds"] == 5
    assert flow.LIMITS["preparation_allowance_seconds"] == 10


def test_missing_review_never_starts(invented):
    root, folder, _, calls, *_ = invented
    with pytest.raises(FileNotFoundError):
        flow.execute(root)
    assert not calls and not (folder / "started.json").exists()


@pytest.mark.parametrize(
    ("answer", "format_status", "expected"),
    [
        ("no", "valid", "correct"),
        ("yes", "valid", "incorrect"),
        ("uncertain", "valid", "abstention"),
        (None, "invalid", "format_invalid"),
    ],
)
def test_single_outcome_seals_without_promotion_or_reentry(
    invented, monkeypatch, answer, format_status, expected
):
    root, folder, _, calls, capture = invented
    approve(invented)

    def observed(*a, **kw):
        return capture(*a, **kw) | {"answer": answer, "format_status": format_status}

    monkeypatch.setattr(flow.prior.prior.short, "capture", observed)
    original = flow.shutil.rmtree

    def clean(path):
        assert (folder / "result-1.json").exists()
        original(path)

    monkeypatch.setattr(flow.shutil, "rmtree", clean)
    state = flow.execute(root)
    assert state["calls"] == len(calls) == 1 and state["sealed"]
    assert state["diagnostic_comparison"] == expected
    assert state["candidates"] == state["released_fields"] == []
    assert not calls[0].exists() and not (folder / "reservation-2.json").exists()
    before = flow.base.sha(folder / "checkpoint.json")
    with pytest.raises(ValueError, match="no_reentry"):
        flow.execute(root)
    assert flow.base.sha(folder / "checkpoint.json") == before and len(calls) == 1


@pytest.mark.parametrize(
    "code",
    [
        "native_timeout",
        "diagnostics_insufficient",
        "visual_budget_not_increased",
        "cleanup_unconfirmed",
    ],
)
def test_failure_or_ineffective_intervention_stays_terminal(invented, monkeypatch, code):
    root, folder, _, calls, capture = invented
    approve(invented)

    def failed(*a, **kw):
        result = capture(*a, **kw)
        if code == "visual_budget_not_increased":
            result["image_tokens_observed"] = 100
        else:
            result.update(stop_code=code, cleanup_confirmed=code != "cleanup_unconfirmed")
        return result

    monkeypatch.setattr(flow.prior.prior.short, "capture", failed)
    with pytest.raises(flow.base.ProbeStop):
        flow.execute(root)
    state = json.loads((folder / "checkpoint.json").read_bytes())
    assert state["sealed"] and state["calls"] == len(calls) == 1 and state["stop_code"] == code
    assert (folder / "result-1.json").exists() and not (folder / "reservation-2.json").exists()
    assert calls[0].exists() is (code == "cleanup_unconfirmed")


def test_changed_binding_refuses_before_start_marker(invented, monkeypatch):
    root, folder, _, calls, *_ = invented
    approve(invented)
    monkeypatch.setattr(flow, "configuration", lambda *a: {"changed": True})
    with pytest.raises(ValueError, match="identity_changed"):
        flow.execute(root)
    assert not calls and not (folder / "started.json").exists()

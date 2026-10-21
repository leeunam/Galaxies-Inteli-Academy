"""Invented processes and pixels only, never models, credentials or network."""

import copy
import hashlib
import json
import socket
from pathlib import Path

import pytest
from PIL import Image

from scripts import vlm_spatial_budget as spatial


def original_argv():
    return [
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
        "--ctx-size",
        "3072",
        "--n-predict",
        "64",
    ]


@pytest.fixture(autouse=True)
def no_native_or_network(monkeypatch):
    def forbidden(*a, **kw):
        raise AssertionError("native_or_network_forbidden")

    monkeypatch.setattr(spatial.base.subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)


def test_only_two_image_budget_values_change_from_fixed_grammar_arm():
    old = spatial.prior.command(original_argv(), "<PNG>", "<SCHEMA>", True)
    new = spatial.command(original_argv(), "<PNG>", "<SCHEMA>")
    changes = [(i, a, b) for i, (a, b) in enumerate(zip(old, new, strict=True)) if a != b]
    assert changes == [
        (old.index("--image-min-tokens") + 1, "64", "1024"),
        (old.index("--image-max-tokens") + 1, "128", "1024"),
    ]
    assert new[new.index("--prompt") + 1] == spatial.prior.PROMPT
    assert "--json-schema-file" in new and spatial.SEQUENCE == ("negative", "positive")
    assert spatial.LIMITS["seconds"] == 100 and spatial.LIMITS["calls"] == 2
    assert spatial.LIMITS["per_call_seconds"] == 45 and spatial.LIMITS["cleanup_seconds"] == 5


@pytest.mark.parametrize("tokens", [101, 1024, 1056])
def test_effective_budget_measures_increase_without_requiring_exact_1024(tokens):
    result = spatial.effective_budget({"stop_code": None, "image_tokens_observed": tokens}, 100)
    assert result["effective_visual_budget"] is True and result["stop_code"] is None


@pytest.mark.parametrize("tokens", [100, 0, None, True])
def test_missing_or_unchanged_intervention_is_terminal(tokens):
    result = spatial.effective_budget({"stop_code": None, "image_tokens_observed": tokens}, 100)
    assert result["effective_visual_budget"] is False
    assert result["stop_code"] == "visual_budget_not_increased"


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
            "sheet_sha256": spatial.base.sha(sheet),
            "png_sha256": spatial.base.sha(crop),
            "expected_answer": answer,
        }
        for alias, frame, seconds, answer in [
            ("positive", 1, 0.2, "yes"),
            ("negative", 3, 2.8, "no"),
        ]
    ]
    config = {
        "inherited_configuration": {
            "pair": {"cases": rows},
            "base": {"original_argv": original_argv()},
        },
        "reference_tokens": {"positive": 100, "negative": 100},
    }
    monkeypatch.setattr(spatial, "configuration", lambda *a: copy.deepcopy(config))
    monkeypatch.setattr(spatial.base, "workers", list)
    plan = spatial.prepare(tmp_path)
    folder = tmp_path / spatial.QUEUE
    literal = "INVENTED SPATIAL REVIEW ONLY"
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
        assert 0 < seconds <= 40
        reserve()
        assert json.loads((folder / "checkpoint.json").read_bytes())["calls"] == len(calls) + 1
        calls.append(Path(argv[argv.index("--image") + 1]).parent)
        return {
            "stop_code": None,
            "cleanup_confirmed": True,
            "image_tokens_observed": 1056,
            "format_status": "valid",
            "answer": "no" if len(calls) == 1 else "yes",
        }

    monkeypatch.setattr(spatial.prior.short, "capture", capture)
    return tmp_path, folder, review, calls, capture


def approve(invented):
    _, folder, review, *_ = invented
    spatial.base.write(folder / "technical-release.json", review, exclusive=True)


def test_missing_review_never_starts(invented):
    root, folder, _, calls, *_ = invented
    with pytest.raises(FileNotFoundError):
        spatial.execute(root)
    assert not calls and not (folder / "started.json").exists()


def test_two_cells_fixed_order_receipt_before_cleanup_and_no_reentry(invented, monkeypatch):
    root, folder, _, calls, *_ = invented
    approve(invented)
    original = spatial.shutil.rmtree

    def clean(path):
        assert (folder / f"result-{len(calls)}.json").exists()
        original(path)

    monkeypatch.setattr(spatial.shutil, "rmtree", clean)
    state = spatial.execute(root)
    assert state["calls"] == len(calls) == 2 and state["sealed"]
    assert [x["alias"] for x in state["operations"]] == ["negative", "positive"]
    assert all(x["diagnostic_comparison"] == "correct" for x in state["operations"])
    assert state["candidates"] == state["released_fields"] == [] and all(
        not x.exists() for x in calls
    )
    before = spatial.base.sha(folder / "checkpoint.json")
    with pytest.raises(ValueError, match="no_reentry"):
        spatial.execute(root)
    assert spatial.base.sha(folder / "checkpoint.json") == before and len(calls) == 2


def test_format_invalid_and_abstention_continue_without_repair(invented, monkeypatch):
    root, folder, _, calls, capture = invented
    approve(invented)

    def outcome(*a, **kw):
        result = capture(*a, **kw)
        return result | (
            {"format_status": "invalid", "answer": None}
            if len(calls) == 1
            else {"answer": "uncertain"}
        )

    monkeypatch.setattr(spatial.prior.short, "capture", outcome)
    state = spatial.execute(root)
    assert state["calls"] == 2 and [x["diagnostic_comparison"] for x in state["operations"]] == [
        "format_invalid",
        "abstention",
    ]
    assert (folder / "result-2.json").exists()


@pytest.mark.parametrize(
    "code",
    [
        "visual_budget_not_increased",
        "native_timeout",
        "diagnostics_insufficient",
        "cleanup_unconfirmed",
    ],
)
def test_first_technical_or_ineffective_intervention_stops(invented, monkeypatch, code):
    root, folder, _, calls, capture = invented
    approve(invented)

    def failure(*a, **kw):
        result = capture(*a, **kw)
        if code == "visual_budget_not_increased":
            result["image_tokens_observed"] = 100
        else:
            result.update(stop_code=code, cleanup_confirmed=code != "cleanup_unconfirmed")
        return result

    monkeypatch.setattr(spatial.prior.short, "capture", failure)
    with pytest.raises(spatial.base.ProbeStop):
        spatial.execute(root)
    state = json.loads((folder / "checkpoint.json").read_bytes())
    assert state["calls"] == len(calls) == 1 and state["sealed"] and state["stop_code"] == code
    assert (folder / "result-1.json").exists() and not (folder / "reservation-2.json").exists()
    assert calls[0].exists() is (code == "cleanup_unconfirmed")


def test_source_change_before_marker_never_dispatches(invented, monkeypatch):
    root, folder, _, calls, *_ = invented
    approve(invented)
    monkeypatch.setattr(spatial, "configuration", lambda *a: {"changed": True})
    with pytest.raises(ValueError, match="identity_changed"):
        spatial.execute(root)
    assert not calls and not (folder / "started.json").exists()

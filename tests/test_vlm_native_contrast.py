"""Invented pixels and model observations; no private dataset, process or network."""

import hashlib
import http.client
import json
import socket
import subprocess
from datetime import datetime
from types import SimpleNamespace

import pytest
from PIL import Image

from scripts import vlm_native_contrast as c


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("contrast_tests_forbid_network_model_and_credential")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(http.client.HTTPSConnection, "request", forbidden)
    monkeypatch.setattr("orchestration.galaxies_orchestration.nim_http.existing_key", forbidden)


def observation(**changes):
    return {
        "stop_code": None,
        "format_status": "valid",
        "answer": "yes",
        "image_tokens_observed": 1075,
        "image_encoder_and_decode_observed": True,
        "cleanup_confirmed": True,
        **changes,
    }


@pytest.fixture
def execution(tmp_path, monkeypatch):
    root = tmp_path / "invented-tree"
    folder = root / c.QUEUE
    (folder / "images").mkdir(parents=True)
    image = Image.new("RGB", (360, 640), "blue")
    cells = []
    for name in c.SEQUENCE:
        alias, representation = name.split("-")
        path = folder / "images" / (name + ".png")
        image.save(path)
        cells.append(
            {
                "name": name,
                "case_role": alias,
                "representation": representation,
                "png_sha256": c.base.sha(path),
                "expected_answer": "no" if alias == "negative" else "yes",
            }
        )
    plan = {
        "plan_sha256": "invented-plan",
        "configuration_sha256": "invented-config",
        "configuration": {
            "cells": cells,
            "expected_tokens": 1075,
            "inherited_configuration": {
                "inherited_configuration": {"base": {"original_argv": ["invented-no-model"]}}
            },
        },
    }
    c.base.write(folder / "checkpoint.json", {"calls": 0, "sealed": False}, exclusive=True)
    monkeypatch.setattr(c, "load", lambda root: plan)
    monkeypatch.setattr(c.prior, "release", lambda folder, plan: "invented-release-not-real")
    monkeypatch.setattr(c.base, "workers", list)
    monkeypatch.setattr(
        c.spatial,
        "command",
        lambda argv, image, schema: ["invented-no-model", str(image), str(schema)],
    )
    state = {
        "clock": 0.0,
        "wall": datetime.fromisoformat("2026-10-21T12:00:00-03:00").timestamp(),
        "calls": [],
        "fault": None,
    }
    monkeypatch.setattr(
        c, "time", SimpleNamespace(monotonic=lambda: state["clock"], time=lambda: state["wall"])
    )

    def capture(argv, *, seconds, reserve):
        assert 0 < seconds <= 55
        reserve()
        number = len(state["calls"]) + 1
        assert (folder / f"reservation-{number}.json").is_file()
        state["calls"].append(argv)
        state["clock"] += 0.1
        if state["fault"]:
            return state["fault"](number)
        return observation()

    monkeypatch.setattr(c.prior.short, "capture", capture)
    return SimpleNamespace(root=root, folder=folder, plan=plan, state=state)


def test_semantic_errors_still_complete_fixed_four_cells_without_promotion(execution):
    x = execution
    result = c.execute(x.root)
    assert result["calls"] == 4 and result["stop_code"] == "scope_completed" and result["sealed"]
    assert result["candidates"] == result["released_fields"] == []
    assert [
        json.loads((x.folder / f"result-{n}.json").read_bytes())["cell"]["name"]
        for n in range(1, 5)
    ] == list(c.SEQUENCE)
    assert (
        json.loads((x.folder / "result-1.json").read_bytes())["diagnostic_comparison"]
        == "incorrect"
    )
    assert not list((x.root / "data/private/media-temp").iterdir())
    with pytest.raises(ValueError, match="consumed_no_reentry"):
        c.execute(x.root)
    assert len(x.state["calls"]) == 4


@pytest.mark.parametrize(
    "bad",
    [
        observation(image_tokens_observed=100),
        observation(image_tokens_observed=1024),
        observation(image_tokens_observed=1076),
        observation(image_tokens_observed=True),
        observation(format_status="invalid", answer=None),
        observation(image_encoder_and_decode_observed=False),
    ],
)
def test_any_technical_mismatch_stops_before_next_cell_and_keeps_receipt(execution, bad):
    x = execution
    x.state["fault"] = lambda number: bad
    result = c.execute(x.root)
    assert result["calls"] == 1 and result["sealed"] and result["stop_code"] != "scope_completed"
    assert (x.folder / "result-1.json").is_file() and not (x.folder / "reservation-2.json").exists()


def test_second_cell_cannot_use_different_token_count(execution):
    x = execution
    x.state["fault"] = lambda number: observation(
        image_tokens_observed=1075 if number == 1 else 1076
    )
    result = c.execute(x.root)
    assert result["calls"] == 2 and result["stop_code"] == "contrast_geometry_token_mismatch"
    assert not (x.folder / "reservation-3.json").exists()


def test_unknown_is_abstention_and_never_repaired(execution):
    x = execution
    x.state["fault"] = lambda number: observation(answer="uncertain")
    result = c.execute(x.root)
    assert result["calls"] == 4
    for n in range(1, 5):
        assert (
            json.loads((x.folder / f"result-{n}.json").read_bytes())["diagnostic_comparison"]
            == "abstention"
        )


@pytest.mark.parametrize("raises", [False, True])
def test_missing_cleanup_ack_retains_own_scratch_and_never_retries(execution, raises):
    x = execution

    def fault(number):
        if raises:
            raise RuntimeError("invented interruption after reservation")
        return observation(cleanup_confirmed=False)

    x.state["fault"] = fault
    result = c.execute(x.root)
    assert result["calls"] == 1 and result["stop_code"] == "contrast_cleanup_unconfirmed"
    assert (x.root / result["preserved_scratch"]).is_dir()
    assert not (x.folder / "reservation-2.json").exists()


def test_global_clock_is_not_reset_for_next_cell(execution):
    x = execution

    def fault(number):
        x.state["clock"] = 261
        return observation()

    x.state["fault"] = fault
    result = c.execute(x.root)
    assert result["calls"] == 1 and result["stop_code"] == "contrast_global_deadline"


def test_expiry_refuses_before_capture(execution):
    x = execution
    x.state["wall"] = datetime.fromisoformat(c.native.RETENTION).timestamp()
    result = c.execute(x.root)
    assert result["calls"] == 0 and result["stop_code"] == "contrast_input_retention_expired"


def test_missing_real_review_refuses_before_started_or_capture(execution, monkeypatch):
    x = execution

    def missing(folder, plan):
        raise FileNotFoundError("invented absent review")

    monkeypatch.setattr(c.prior, "release", missing)
    with pytest.raises(FileNotFoundError):
        c.execute(x.root)
    assert not (x.folder / "started.json").exists() and not x.state["calls"]


def test_prepare_has_four_images_and_zero_reserved_calls(tmp_path, monkeypatch):
    (tmp_path / "data/private").mkdir(parents=True)
    images = {n: c.png_bytes(Image.new("RGB", (360, 640), "red")) for n in c.SEQUENCE}
    config = {
        "cells": [
            {"name": n, "png_sha256": hashlib.sha256(images[n]).hexdigest()} for n in c.SEQUENCE
        ]
    }
    monkeypatch.setattr(c, "configuration", lambda root: config)
    monkeypatch.setattr(c, "inputs", lambda root: (images, []))
    c.prepare(tmp_path)
    folder = tmp_path / c.QUEUE
    assert len(list((folder / "images").iterdir())) == 4
    assert json.loads((folder / "checkpoint.json").read_bytes()) == {"calls": 0, "sealed": False}
    assert (
        not (folder / "technical-release.json").exists() and not (folder / "started.json").exists()
    )
    assert c.load(tmp_path)["configuration"] == config
    (folder / "images/negative-D.png").write_bytes(b"invented tamper")
    with pytest.raises(ValueError, match="prepared_png_changed"):
        c.load(tmp_path)


@pytest.mark.parametrize("source_frame", [1, 3])
def test_derivative_removes_only_fixed_blank_margin_and_preserves_source(tmp_path, source_frame):
    sheet = Image.new("RGB", (1280, 360), "white")
    for index in range(4):
        sheet.paste(Image.new("RGB", (186, 330), "blue"), (index * 320, 25))
    path = tmp_path / "invented-sheet.png"
    sheet.save(path)
    x = (source_frame - 1) * 320
    cell = sheet.crop((x, 25, x + 320, 355))
    case = {
        "source_frame": source_frame,
        "sheet_sha256": c.base.sha(path),
        "png_sha256": hashlib.sha256(c.png_bytes(cell)).hexdigest(),
    }
    before = path.read_bytes()
    raw = c.derived_bytes(path, case)
    with Image.open(c.io.BytesIO(raw)) as derivative:
        assert derivative.mode == "RGB" and derivative.size == (360, 640)
        assert derivative.getpixel((359, 639)) == (0, 0, 255)
    assert path.read_bytes() == before
    assert c.derived_bytes(path, case) == raw


def test_nonblank_fixed_margin_is_terminal_even_if_frozen_hashes_match(tmp_path):
    sheet = Image.new("RGB", (1280, 360), "red")
    path = tmp_path / "invented-sheet.png"
    sheet.save(path)
    case = {
        "source_frame": 1,
        "sheet_sha256": c.base.sha(path),
        "png_sha256": hashlib.sha256(c.png_bytes(sheet.crop((0, 25, 320, 355)))).hexdigest(),
    }
    with pytest.raises(ValueError, match="fixed_blank_margin_changed"):
        c.derived_bytes(path, case)


def test_static_geometry_prediction_is_required_in_addition_to_equal_counts():
    with pytest.raises(c.base.ProbeStop, match="geometry_token_mismatch"):
        c.validate_observation(observation(image_tokens_observed=1056), 1075, 1056)
    assert c.validate_observation(observation(), 1075, 1075) == 1075

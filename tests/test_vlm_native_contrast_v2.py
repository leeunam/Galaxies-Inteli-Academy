"""Invented four-cell fixtures; no media, model, downloader or external service."""

import hashlib
import json
import socket
import subprocess
import sys
from datetime import datetime
from types import SimpleNamespace

import pytest
from PIL import Image

from scripts import vlm_native_contrast_v2 as c

REAL_POPEN = subprocess.Popen


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


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("no_network_or_model")

    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    old = tmp_path / c.frozen.QUEUE
    (old / "images").mkdir(parents=True)
    cells = []
    for name in c.SEQUENCE:
        path = old / "images" / (name + ".png")
        Image.new("RGB", (360, 640), "blue").save(path)
        cells.append(
            {
                "name": name,
                "png_sha256": c.base.sha(path),
                "expected_answer": "no" if name.startswith("negative") else "yes",
            }
        )
    config = {
        "protocol": c.PROTOCOL,
        "namespace": c.durable.NAMESPACE,
        "root_sha256": hashlib.sha256(str(tmp_path.resolve()).encode()).hexdigest(),
        "reviewer_thread_id": c.native.REVIEWER,
        "limits": c.LIMITS,
        "cells": cells,
        "expected_tokens": 1075,
        "sources": {"invented.py": "a" * 64},
        "inherited_configuration": {
            "inherited_configuration": {
                "inherited_configuration": {"base": {"original_argv": ["invented-no-model"]}}
            }
        },
    }
    monkeypatch.setattr(c, "configuration", lambda root: config)
    c.base.write(old / "technical-release.json", {"source_message_id": "invented-old-message"})
    plan = c.prepare(tmp_path)
    calls = []
    fault = {"value": None}

    def capture(argv, *, root, cell, seconds, reserve, popen):
        assert 0 < seconds <= 55 and callable(popen)
        assert root == tmp_path
        reserve()
        calls.append(cell)
        assert (tmp_path / c.QUEUE / f"reservation-{len(calls)}.json").is_file()
        if callable(fault["value"]):
            return fault["value"]()
        return fault["value"] or observation()

    monkeypatch.setattr(
        c,
        "durable",
        SimpleNamespace(
            NAMESPACE=c.durable.NAMESPACE,
            capture=capture,
            inspect=lambda *args: (_ for _ in ()).throw(FileNotFoundError()),
        ),
    )
    monkeypatch.setattr(c.base, "workers", list)
    monkeypatch.setattr(c.spatial, "command", lambda argv, image, schema: ["invented-no-model"])
    return SimpleNamespace(
        root=tmp_path,
        folder=tmp_path / c.QUEUE,
        plan=plan,
        calls=calls,
        fault=fault,
        config=config,
    )


def authorize(x):
    config = x.plan["configuration"]
    bound = {
        "protocol": c.PROTOCOL,
        "namespace": c.durable.NAMESPACE,
        "plan_sha256": x.plan["plan_sha256"],
        "configuration_sha256": x.plan["configuration_sha256"],
        "root_sha256": config["root_sha256"],
        "reviewer_thread_id": c.native.REVIEWER,
        "limits": c.LIMITS,
        "input_hashes": {cell["name"]: cell["png_sha256"] for cell in config["cells"]},
        "retry_allowed": False,
        "external_cost": 0,
    }
    literal = "Invented fixture authorization; no real permission."
    auth = dict(
        bound,
        source_message_id="invented-fresh-message",
        literal_message=literal,
        literal_message_sha256=hashlib.sha256(literal.encode()).hexdigest(),
        decision="authorize_exact_four_cell_v2_once",
    )
    c.base.write(x.folder / "authorization.json", auth, exclusive=True)
    review = dict(
        bound,
        authorization_sha256=c.base.sha(x.folder / "authorization.json"),
        decision="reviewed_exact_v2_plan_and_authorization",
        review_message_id="invented-independent-review",
    )
    c.base.write(x.folder / "review-seal.json", review, exclusive=True)
    return auth, review


def test_prepare_copies_only_frozen_bytes_without_release_or_reservation(prepared):
    x = prepared
    assert c.load(x.root) == x.plan
    assert json.loads((x.folder / "checkpoint.json").read_bytes()) == c.INITIAL
    assert not (x.folder / "authorization.json").exists()
    assert not (x.folder / "review-seal.json").exists()
    for cell in c.SEQUENCE:
        assert (x.folder / "images" / (cell + ".png")).read_bytes() == (
            x.root / c.frozen.QUEUE / "images" / (cell + ".png")
        ).read_bytes()
    with pytest.raises(FileExistsError):
        c.prepare(x.root)


def test_missing_release_refuses_before_any_controller_or_capture_write(prepared):
    x = prepared
    before = {str(p.relative_to(x.root)): p.read_bytes() for p in x.root.rglob("*") if p.is_file()}
    with pytest.raises(FileNotFoundError):
        c.execute(x.root)
    after = {str(p.relative_to(x.root)): p.read_bytes() for p in x.root.rglob("*") if p.is_file()}
    assert before == after and not x.calls
    assert not (x.folder / ".lock").exists() and not (x.folder / "captures").exists()


@pytest.mark.parametrize(
    "file,key,value",
    [
        ("authorization.json", "source_message_id", "invented-old-message"),
        ("authorization.json", "namespace", "issue-4-vlm-native-contrast-v1"),
        ("authorization.json", "root_sha256", "invented-other-root"),
        ("authorization.json", "plan_sha256", "invented-old-plan"),
        ("authorization.json", "configuration_sha256", "invented-other-config"),
        ("authorization.json", "reviewer_thread_id", "invented-other-reviewer"),
        ("authorization.json", "input_hashes", {}),
        ("authorization.json", "limits", {"calls": 5}),
        ("authorization.json", "literal_message_sha256", "invalid"),
        ("authorization.json", "external_cost", 1),
        ("authorization.json", "retry_allowed", True),
        ("review-seal.json", "review_message_id", "invented-fresh-message"),
        ("review-seal.json", "authorization_sha256", "invented-stale-release"),
    ],
)
def test_bad_external_receipts_never_reserve_spawn_or_create_lock(prepared, file, key, value):
    x = prepared
    authorize(x)
    path = x.folder / file
    body = json.loads(path.read_bytes())
    body[key] = value
    c.base.write(path, body)
    with pytest.raises(ValueError, match="authorization_and_review"):
        c.execute(x.root)
    assert not x.calls and not (x.folder / ".lock").exists()
    assert not (x.folder / "started.json").exists()


def test_consumed_authority_digest_is_rejected_even_with_new_seal(prepared, monkeypatch):
    x = prepared
    authorize(x)
    monkeypatch.setattr(
        c, "CONSUMED_AUTH_SHA256", hashlib.sha256(b"invented-fresh-message").hexdigest()
    )
    with pytest.raises(ValueError, match="authorization_and_review"):
        c.execute(x.root)
    assert not x.calls


def test_semantic_error_completes_exact_order_without_promotion_or_reentry(prepared):
    x = prepared
    authorize(x)
    result = c.execute(x.root)
    assert result["calls"] == 4 and result["stop_code"] == "scope_completed"
    assert x.calls == list(c.SEQUENCE)
    assert result["sealed"] and result["retry_allowed"] is False
    assert result["candidates"] == result["released_fields"] == []
    assert (
        json.loads((x.folder / "result-1.json").read_bytes())["diagnostic_comparison"]
        == "incorrect"
    )
    assert not list((x.root / "data/private/media-temp").iterdir())
    with pytest.raises(ValueError, match="consumed_no_reentry"):
        c.execute(x.root)
    assert len(x.calls) == 4


@pytest.mark.parametrize(
    "bad",
    [
        observation(image_tokens_observed=1024),
        observation(image_tokens_observed=1076),
        observation(image_tokens_observed=True),
        observation(format_status="invalid"),
        observation(image_encoder_and_decode_observed=False),
        observation(stop_code="native_timeout"),
        observation(cleanup_confirmed=False),
    ],
)
def test_first_technical_failure_consumes_one_and_closes_remaining(prepared, bad):
    x = prepared
    authorize(x)
    x.fault["value"] = bad
    result = c.execute(x.root)
    assert result["calls"] == 1 and result["sealed"]
    assert result["stop_code"] != "scope_completed"
    assert not (x.folder / "reservation-2.json").exists()
    with pytest.raises(ValueError, match="consumed_no_reentry"):
        c.execute(x.root)


def test_persistence_exception_after_reservation_seals_and_keeps_scratch(prepared):
    x = prepared
    authorize(x)

    def fail():
        raise OSError("invented persistence failure")

    x.fault["value"] = fail
    result = c.execute(x.root)
    assert result["calls"] == 1 and result["stop_code"] == "contrast_cleanup_unconfirmed"
    assert (x.root / result["preserved_scratch"]).is_dir()
    assert not (x.folder / "result-1.json").exists()


def test_retention_expiry_consumes_no_call(prepared, monkeypatch):
    x = prepared
    authorize(x)
    monkeypatch.setattr(
        c.time, "time", lambda: datetime.fromisoformat(c.native.RETENTION).timestamp()
    )
    result = c.execute(x.root)
    assert result["calls"] == 0 and result["stop_code"] == "contrast_input_retention_expired"
    assert not x.calls


def test_inspect_is_read_only_and_tolerates_absent_cells(prepared):
    x = prepared
    assert c.inspect(x.root)["calls"] == 0
    assert all(v["status"] == "absent" for v in c.inspect(x.root)["captures"].values())
    assert not (x.folder / "captures").exists()


def test_internal_launcher_refuses_arbitrary_root_before_popen(prepared):
    x = prepared
    authorize(x)
    launcher = c._launcher(x.root, x.plan, c.release(x.root, x.plan), ["invented"], float("inf"))
    with pytest.raises(RuntimeError, match="launcher_guard"):
        launcher(["invented"])


def test_absolute_deadline_reaches_existing_owner_with_real_python_child(tmp_path):
    reserved, processes = [], []

    def start(*args, **kwargs):
        assert reserved == [True]
        process = REAL_POPEN(*args, **kwargs)
        processes.append(process)
        return c._DeadlineProcess(process, c.time.monotonic() + 0.1)

    result = c.durable.capture(
        [sys.executable, "-B", "-c", "import time; time.sleep(20)"],
        root=tmp_path,
        cell=c.SEQUENCE[0],
        seconds=1,
        reserve=lambda: reserved.append(True),
        popen=start,
    )
    assert result["stop_code"] == "native_timeout"
    assert result["cleanup_confirmed"] and reserved == [True]
    assert all(process.poll() is not None for process in processes)
    assert c.durable.inspect(tmp_path, c.SEQUENCE[0])["terminal"]


def test_global_pre_dispatch_overhead_stops_without_reservation(prepared, monkeypatch):
    x = prepared
    authorize(x)
    wall = c.time.time
    clock = [0.0]
    monkeypatch.setattr(c, "time", SimpleNamespace(monotonic=lambda: clock[0], time=wall))

    def command(*args):
        clock[0] = 261.0
        return ["invented-no-model"]

    monkeypatch.setattr(c.spatial, "command", command)
    result = c.execute(x.root)
    assert result["calls"] == 0 and result["stop_code"] == "contrast_global_deadline"
    assert not x.calls and not (x.folder / "reservation-1.json").exists()


def test_global_deadline_counts_final_checkpoint_persistence(prepared, monkeypatch):
    x = prepared
    authorize(x)
    wall = c.time.time
    clock = [0.0]
    monkeypatch.setattr(c, "time", SimpleNamespace(monotonic=lambda: clock[0], time=wall))
    write = c.base.write

    def delayed(path, value, **kwargs):
        write(path, value, **kwargs)
        if path.name == "checkpoint.json" and value.get("sealed"):
            clock[0] = 261.0

    monkeypatch.setattr(c.base, "write", delayed)
    result = c.execute(x.root)
    assert result["calls"] == 4 and result["stop_code"] == "contrast_global_deadline"
    assert (
        json.loads((x.folder / "checkpoint.json").read_bytes())["stop_code"]
        == "contrast_global_deadline"
    )


def test_real_helper_startup_guard_consumes_once_without_any_process(prepared, monkeypatch):
    from scripts import vlm_durable_capture_v2 as actual

    x = prepared
    authorize(x)
    monkeypatch.setattr(c, "durable", actual)
    before = {
        str(p.relative_to(x.root / c.frozen.QUEUE)): p.read_bytes()
        for p in (x.root / c.frozen.QUEUE).rglob("*")
        if p.is_file()
    }
    result = c.execute(x.root)
    assert result["calls"] == 1 and result["stop_code"] == "native_operation_failed"
    snapshot = actual.inspect(x.root, c.SEQUENCE[0])
    assert snapshot["terminal"] and snapshot["cleanup_confirmed"]
    assert snapshot["observation"]["process_started"] is False
    after = {
        str(p.relative_to(x.root / c.frozen.QUEUE)): p.read_bytes()
        for p in (x.root / c.frozen.QUEUE).rglob("*")
        if p.is_file()
    }
    assert before == after and not (x.folder / "reservation-2.json").exists()


def test_input_or_pin_tamper_after_plan_is_blocked_before_lock(prepared):
    x = prepared
    authorize(x)
    (x.folder / "images" / (c.SEQUENCE[0] + ".png")).write_bytes(b"invented changed input")
    with pytest.raises(ValueError, match="v2_input_changed"):
        c.execute(x.root)
    assert not x.calls and not (x.folder / ".lock").exists()


def test_abstentions_keep_fixed_order_without_repair(prepared):
    x = prepared
    authorize(x)
    x.fault["value"] = observation(answer="uncertain")
    result = c.execute(x.root)
    assert result["calls"] == 4 and x.calls == list(c.SEQUENCE)
    assert all(
        json.loads((x.folder / f"result-{n}.json").read_bytes())["diagnostic_comparison"]
        == "abstention"
        for n in range(1, 5)
    )


def test_inspect_started_reservation_without_terminal_is_uncertain_no_reentry(prepared):
    x = prepared
    c.base.write(x.folder / "started.json", {"invented": "consumed"}, exclusive=True)
    c.base.write(x.folder / "checkpoint.json", {"calls": 1, "sealed": False})
    snapshot = c.inspect(x.root)
    assert snapshot["status"] == "started_outcome_uncertain"
    assert snapshot["no_reentry"] is True and snapshot["remaining_calls"] == 0
    assert all(row.get("terminal") is False for row in snapshot["captures"].values())
    assert not (x.folder / "captures").exists()

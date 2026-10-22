"""Small sequential invented Python children; never visual/model processes."""

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime

import pytest

from scripts import vlm_native225_probe_v2 as p


def child(tokens=240, tail="", answer="no"):
    logs = (
        "encoding mtmd batch, n_chunks = 1 (done = 0, total = 1)\n"
        "mtmd batch encoding done in 1 ms\n"
        f"decoding image batch 1/1, n_tokens_batch = {tokens}\n"
        "image decoded (batch 1/1) in 1 ms\n"
    )
    code = f"import sys,os,signal,time;sys.stderr.write({logs!r});sys.stderr.flush();"
    code += f"sys.stdout.write({json.dumps({'answer': answer})!r});sys.stdout.flush();"
    return [sys.executable, "-B", "-c", code + tail]


class Owner:
    def __init__(self):
        self.children = []

    def __call__(self, argv, **kw):
        assert argv[:3] == [sys.executable, "-B", "-c"]
        process = subprocess.Popen(argv, **kw)
        self.children.append(process)
        return process


def run(tmp_path, **kw):
    owner = Owner()
    result = p._run_invented(
        tmp_path, child(**kw), verify=lambda: True, available_bytes=p.MIN_AVAILABLE, launcher=owner
    )
    assert len(owner.children) == 1 and owner.children[0].poll() is not None
    with pytest.raises(ProcessLookupError):
        os.killpg(owner.children[0].pid, 0)
    return result


def test_authority_and_review_and_release_are_required(monkeypatch):
    monkeypatch.setattr(p, "EXECUTION_RELEASED", False)
    plan = {"plan_sha256": "invented", "execution_released": False}
    with pytest.raises(ValueError, match="authorization_required"):
        p.execute(plan)
    auth = {
        "plan_sha256": "invented",
        "decision": "authorize_native225_once",
        "source_message_id": "invented-human",
    }
    with pytest.raises(ValueError, match="review_required"):
        p.execute(plan, auth)
    review = {
        "plan_sha256": "invented",
        "authorization_sha256": p.base.digest(auth),
        "decision": "reviewed_native225_once",
        "review_message_id": "invented-review",
    }
    with pytest.raises(ValueError, match="not_released"):
        p.execute(plan, auth, review)


def test_exactly_two_argv_values_change():
    original = [
        "runtime",
        "--image-min-tokens",
        "1024",
        "--image-max-tokens",
        "1024",
        "--threads",
        "4",
        "--prompt",
        "unchanged",
    ]
    changed = p.command(original)
    assert sum(a != b for a, b in zip(original, changed, strict=True)) == 2
    assert changed[2] == changed[4] == "225" and original[2] == "1024"


def test_memory_and_authority_refuse_before_spawn(tmp_path):
    for verify, memory in [(lambda: False, p.MIN_AVAILABLE), (lambda: True, 0)]:
        with pytest.raises(ValueError):
            p._run_invented(
                tmp_path,
                [],
                verify=verify,
                available_bytes=memory,
                launcher=lambda *_a, **_k: pytest.fail("spawn"),
            )
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize(
    "tokens,answer,technical,correct",
    [
        (240, "no", True, True),
        (239, "no", False, False),
        (241, "no", False, False),
        (240, "yes", True, False),
        (240, "uncertain", True, False),
    ],
)
def test_strict_tokens_and_semantics_and_single_slot(tmp_path, tokens, answer, technical, correct):
    result = run(tmp_path, tokens=tokens, answer=answer)
    assert result["technical_success"] is technical
    assert result["negative_correct"] is correct
    folder = tmp_path / "data/private" / p.durable.NAMESPACE
    assert not (folder / "scratch").exists()
    state = json.loads((folder / "checkpoint.json").read_text())
    assert state["calls"] == 1 and state["sealed"] and state["remaining_calls"] == 0
    with pytest.raises(FileExistsError):
        run(tmp_path)


@pytest.mark.parametrize("cancel", [False, True])
def test_timeout_or_cancel_seals_without_reuse(tmp_path, cancel):
    owner = Owner()
    tail = "os.kill(os.getppid(),signal.SIGTERM);time.sleep(5)" if cancel else "time.sleep(5)"
    result = p._run_invented(
        tmp_path,
        child(tail=tail),
        verify=lambda: True,
        available_bytes=p.MIN_AVAILABLE,
        launcher=owner,
        seconds=0.15,
    )
    assert not result["technical_success"] and owner.children[0].poll() is not None
    folder = tmp_path / "data/private" / p.durable.NAMESPACE
    assert json.loads((folder / "checkpoint.json").read_text())["sealed"]
    with pytest.raises(FileExistsError):
        run(tmp_path)


def test_terminal_capture_is_durable_before_scratch_cleanup(tmp_path, monkeypatch):
    original = p.shutil.rmtree
    checked = []

    def remove(path):
        state = p.durable.inspect(tmp_path, "negative-N")
        assert state["terminal"] and state["cleanup_confirmed"]
        assert state["observation"]["image_tokens_observed"] == 240
        checked.append(True)
        return original(path)

    monkeypatch.setattr(p.shutil, "rmtree", remove)
    assert run(tmp_path)["technical_success"]
    assert checked == [True]


@pytest.fixture
def production_fake(tmp_path, monkeypatch):
    """The real controller path, exclusively invented files and a Python launcher."""
    operation, source, assets = (tmp_path / n for n in ("operation", "source", "assets"))
    operation.mkdir()
    assets.mkdir()
    hashes = {}
    for name in ("runtime", "model.gguf", "projector.gguf", "libmtmd.so.0.7.0"):
        target = assets / name
        target.write_bytes(("invented-" + name).encode())
        hashes[name] = hashlib.sha256(target.read_bytes()).hexdigest()
    # Exercise the final HF link route without ever reading any real model.
    (assets / "model-link.gguf").symlink_to(assets / "model.gguf")
    folder = source / "data/private/issue-4-vlm-native-contrast-v3"
    (folder / "images").mkdir(parents=True)
    image = folder / "images/negative-N.png"
    image.write_bytes(b"invented-not-a-real-image")
    image_sha = hashlib.sha256(image.read_bytes()).hexdigest()
    argv = [
        str(assets / "runtime"),
        "-m",
        str(assets / "model-link.gguf"),
        "--mmproj",
        str(assets / "projector.gguf"),
        "--image-min-tokens",
        "1024",
        "--image-max-tokens",
        "1024",
        "--image",
        "<PNG>",
        "--json-schema-file",
        "<SCHEMA>",
        "--prompt",
        "invented-prompt",
    ]
    config = {
        "cells": [{"name": "negative-N", "png_sha256": image_sha}],
        "effective_argv_template": argv,
        "base": {
            "runtime_sha256": hashes["runtime"],
            "libmtmd_sha256": hashes["libmtmd.so.0.7.0"],
            "native_model_sha256_previously_verified": {
                "model-link.gguf": hashes["model.gguf"],
                "projector.gguf": hashes["projector.gguf"],
            },
        },
    }
    raw = json.dumps({"configuration": config}).encode()
    (folder / "plan.json").write_bytes(raw)
    monkeypatch.setattr(p, "SOURCE_PLAN_SHA256", hashlib.sha256(raw).hexdigest())
    monkeypatch.setattr(p, "PNG_SHA256", image_sha)
    monkeypatch.setattr(p, "EXECUTION_RELEASED", True)
    monkeypatch.setattr(p, "capsule_preflight", lambda: None)
    monkeypatch.setattr(p, "available_memory", lambda: p.MIN_AVAILABLE + 1024)
    monkeypatch.setattr(p.base, "workers", list)
    instant = datetime.fromisoformat("2026-10-22T00:40:00+00:00").timestamp()
    monkeypatch.setattr(p.time, "time", lambda: instant)
    plan = p.proposal(source, root=operation)
    auth = {
        "plan_sha256": plan["plan_sha256"],
        "decision": "authorize_native225_once",
        "source_message_id": "entirely-invented-human-message",
    }
    review = {
        "plan_sha256": plan["plan_sha256"],
        "authorization_sha256": p.base.digest(auth),
        "decision": "reviewed_native225_once",
        "review_message_id": "entirely-invented-review-message",
    }
    release = operation / "data/private/issue-4-vlm-native225-release-v2"
    release.mkdir(parents=True)
    (release / "authorization.json").write_text(json.dumps(auth))
    (release / "review-seal.json").write_text(json.dumps(review))
    original_popen = subprocess.Popen
    launches = []

    def fake_native(argv, **kwargs):
        assert argv[0] == str(assets / "runtime")
        launches.append(list(argv))
        return original_popen(child(), **kwargs)

    monkeypatch.setattr(p.base.subprocess, "Popen", fake_native)
    return operation, source, assets, image, plan, auth, review, launches


def test_released_controller_wires_the_guarded_capture_with_invented_assets(production_fake):
    operation, _, _, image, plan, auth, review, launches = production_fake
    result = p.execute(plan, auth, review, root=operation)
    assert result["technical_success"] and result["negative_correct"]
    assert len(launches) == 1
    argv = launches[0]
    assert argv[argv.index("--image") + 1] == str(image)
    assert argv[argv.index("--image-min-tokens") + 1] == "225"
    assert argv[argv.index("--image-max-tokens") + 1] == "225"
    assert p.durable.inspect(operation, "negative-N")["terminal"]
    assert image.read_bytes() == b"invented-not-a-real-image"
    with pytest.raises(FileExistsError):
        p.execute(plan, auth, review, root=operation)
    assert len(launches) == 1


@pytest.mark.parametrize(
    "failure",
    [
        "memory",
        "retention",
        "source",
        "png",
        "asset",
        "receipt",
        "workers",
        "deadline",
        "link",
        "retention_window",
        "argv",
        "plan",
    ],
)
def test_production_preflight_refuses_before_any_spawn(production_fake, monkeypatch, failure):
    operation, source, assets, image, plan, auth, review, launches = production_fake
    if failure == "memory":
        monkeypatch.setattr(p, "available_memory", lambda: p.MIN_AVAILABLE - 1)
    elif failure == "retention":
        monkeypatch.setattr(
            p.time, "time", lambda: datetime.fromisoformat(p.RETENTION).timestamp() + 1
        )
    elif failure == "retention_window":
        monkeypatch.setattr(
            p.time, "time", lambda: datetime.fromisoformat(p.RETENTION).timestamp() - 30
        )
    elif failure == "source":
        (source / "data/private/issue-4-vlm-native-contrast-v3/plan.json").write_bytes(b"bad")
    elif failure == "png":
        image.write_bytes(b"changed")
    elif failure == "asset":
        (assets / "projector.gguf").write_bytes(b"changed")
    elif failure == "receipt":
        (operation / "data/private/issue-4-vlm-native225-release-v2/authorization.json").write_text(
            "{}"
        )
    elif failure == "workers":
        monkeypatch.setattr(p.base, "workers", lambda: [123])
    elif failure == "link":
        (assets / "model-link.gguf").unlink()
        (assets / "model-link.gguf").symlink_to(assets / "projector.gguf")
    elif failure == "argv":
        index = plan["argv_template"].index("--image-min-tokens") + 1
        plan["argv_template"][index] = "226"
    elif failure == "plan":
        plan["expected_tokens"] = 239
    else:
        moments = iter([0, 81, 82, 83])
        monkeypatch.setattr(p.time, "monotonic", lambda: next(moments))
    with pytest.raises((ValueError, TimeoutError)):
        p.execute(plan, auth, review, root=operation)
    assert launches == []
    assert not (operation / "data/private" / p.durable.NAMESPACE).exists()


def test_authority_changed_after_reservation_never_spawns(tmp_path):
    attempts = []

    def verify():
        attempts.append(True)
        return len(attempts) < 3

    result = p._run_invented(
        tmp_path,
        child(),
        verify=verify,
        available_bytes=p.MIN_AVAILABLE,
        launcher=lambda *_a, **_k: pytest.fail("spawn"),
    )
    assert not result["technical_success"]
    folder = tmp_path / "data/private" / p.durable.NAMESPACE
    state = json.loads((folder / "checkpoint.json").read_text())
    assert state["calls"] == 1 and state["sealed"] and state["remaining_calls"] == 0


def test_changed_asset_hash_is_rejected_even_with_fresh_invented_receipts(production_fake):
    operation, source, assets, _, _, _, _, launches = production_fake
    (assets / "projector.gguf").write_bytes(b"different-invented-weights")
    plan = p.proposal(source, root=operation)
    auth = {
        "plan_sha256": plan["plan_sha256"],
        "decision": "authorize_native225_once",
        "source_message_id": "another-invented-human",
    }
    review = {
        "plan_sha256": plan["plan_sha256"],
        "authorization_sha256": p.base.digest(auth),
        "decision": "reviewed_native225_once",
        "review_message_id": "another-invented-review",
    }
    release = operation / "data/private/issue-4-vlm-native225-release-v2"
    (release / "authorization.json").write_text(json.dumps(auth))
    (release / "review-seal.json").write_text(json.dumps(review))
    with pytest.raises(ValueError, match="asset_identity_changed"):
        p.execute(plan, auth, review, root=operation)
    assert launches == []


def test_full_useful_budget_is_reserved_instead_of_silently_shortened(tmp_path):
    with pytest.raises(TimeoutError, match="full_dispatch_window_required"):
        p._run_once(
            tmp_path,
            [],
            verify=lambda: True,
            memory_reader=lambda: p.MIN_AVAILABLE,
            launcher=lambda *_a, **_k: pytest.fail("spawn"),
            started=p.time.monotonic() - 21,
        )
    assert not list(tmp_path.iterdir())


def test_memory_drop_between_reservation_and_spawn_seals_without_dispatch(tmp_path):
    readings = iter([p.MIN_AVAILABLE, p.MIN_AVAILABLE, 0])
    result = p._run_once(
        tmp_path,
        child(),
        verify=lambda: True,
        memory_reader=lambda: next(readings),
        launcher=lambda *_a, **_k: pytest.fail("spawn"),
    )
    assert not result["technical_success"]
    state = json.loads(
        (tmp_path / "data/private" / p.durable.NAMESPACE / "checkpoint.json").read_text()
    )
    assert state["calls"] == 1 and state["sealed"] and state["remaining_calls"] == 0


def test_uncertain_child_cleanup_preserves_scratch_and_closes_slot(tmp_path, monkeypatch):
    def uncertain(*_args, **kwargs):
        kwargs["reserve"]()
        return {
            "stop_code": "cleanup_unconfirmed",
            "cleanup_confirmed": False,
            "format_status": "not_assessed_technical_failure",
            "answer": None,
        }

    monkeypatch.setattr(p.durable, "capture", uncertain)
    result = p._run_invented(
        tmp_path,
        [],
        verify=lambda: True,
        available_bytes=p.MIN_AVAILABLE,
        launcher=lambda *_a, **_k: pytest.fail("spawn"),
    )
    assert not result["technical_success"]
    folder = tmp_path / "data/private" / p.durable.NAMESPACE
    assert (folder / "scratch").is_dir()
    assert json.loads((folder / "checkpoint.json").read_text())["sealed"]


def test_asset_blocks_do_not_repeat_worker_enumeration(tmp_path, monkeypatch):
    target = tmp_path / "invented-large.bin"
    target.write_bytes(b"x" * (4 * 1024**2))
    scans = []

    def workers():
        scans.append(True)
        return []

    monkeypatch.setattr(p.base, "workers", workers)
    monkeypatch.setattr(p, "available_memory", lambda: p.MIN_AVAILABLE)
    monkeypatch.setattr(
        p.time, "time", lambda: datetime.fromisoformat("2026-10-22T00:40:00+00:00").timestamp()
    )
    plan = {
        "asset_sha256": {str(target): hashlib.sha256(target.read_bytes()).hexdigest()},
        "asset_references": {str(target): p._asset_reference(target)},
    }
    p._asset_pins(plan, p.time.monotonic() + 10)
    assert scans == [True]


def test_capsule_failure_precedes_slot_and_spawn(production_fake, monkeypatch):
    operation, _, _, _, plan, auth, review, launches = production_fake

    def fail():
        raise PermissionError("invented-devnull-refusal")

    monkeypatch.setattr(p, "capsule_preflight", fail)
    with pytest.raises(PermissionError, match="invented-devnull-refusal"):
        p.execute(plan, auth, review, root=operation)
    assert not launches
    assert not (operation / "data/private" / p.durable.NAMESPACE).exists()


def test_renewed_namespace_and_one_attempt_scope_are_explicit(production_fake):
    _, _, _, _, plan, _, _, _ = production_fake
    assert p.durable.NAMESPACE == "issue-4-vlm-native225-probe-v2"
    assert plan["renewal_scope"] == "one_attempt_only"
    assert plan["capsule"]["ephemeral_dev"] is True
    assert plan["capsule"]["preflight_before_reservation"] is True

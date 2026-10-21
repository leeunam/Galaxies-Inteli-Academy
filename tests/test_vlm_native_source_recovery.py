"""Invented pixels and fake supervisors only; never network, media acquisition or ML."""

import hashlib
import http.client
import json
import socket
import subprocess
import sys
from datetime import datetime
from types import SimpleNamespace

import pytest
from PIL import Image

from scripts import vlm_native_source_frames as frames
from scripts import vlm_native_source_recovery as recovery
from scripts.demo_recovery_policy import RecoveryError, digest, exclusive_json


@pytest.fixture(autouse=True)
def offline_only(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("native_source_tests_forbid_network_processes_or_credentials")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(http.client.HTTPSConnection, "request", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    monkeypatch.setattr("orchestration.galaxies_orchestration.nim_http.existing_key", forbidden)


def invented_case(alias="positive"):
    sample = ("a" if alias == "positive" else "b") * 11
    seconds = [0.2, 1.5, 2.8, 12.0]
    props = {
        "width": 360,
        "height": 640,
        "duration_seconds": 20.0,
        "sampled_frame_seconds": seconds,
    }
    return {
        "alias": alias,
        "sample_id": sample,
        "source_url": "https://www.youtube.com/watch?v=" + sample,
        "source_frame": 1 if alias == "positive" else 3,
        "seconds": 0.2 if alias == "positive" else 2.8,
        "sheet_sha256": "2" * 64,
        "png_sha256": "3" * 64,
        "historical_properties": props,
        "historical_selected_seconds": list(seconds),
        "row": {
            "sample_id": sample,
            "properties": props,
            "sheet_sha256": "2" * 64,
            "sheet_recipe": {"source_batch": "sixty", "source_index": 1},
        },
    }


@pytest.fixture
def operator(tmp_path, monkeypatch):
    root = tmp_path / "invented-tree"
    folder = root / recovery.QUEUE
    folder.mkdir(parents=True)
    config = {"cases": [invented_case(), invented_case("negative")]}
    plan = {"configuration": config, "configuration_sha256": recovery.json_digest(config)}
    checksum = "1" * 64
    monkeypatch.setattr(recovery, "load", lambda root: (plan, checksum))
    monkeypatch.setattr(recovery, "resource_slot", lambda: None)
    text = "Entirely invented technical review, for fake supervisors only."
    review = {
        "protocol": recovery.PROTOCOL,
        "decision": "approved_for_two_source_recoveries_no_generation",
        "plan_sha256": checksum,
        "configuration_sha256": plan["configuration_sha256"],
        "execution_root_sha256": hashlib.sha256(str(root.resolve()).encode()).hexdigest(),
        "reviewer_thread_id": recovery.REVIEWER,
        "source_message_id": "invented_review_source",
        "literal_message": text,
        "literal_message_sha256": hashlib.sha256(text.encode()).hexdigest(),
    }
    exclusive_json(folder / "technical-release.json", review)
    state = {"time": 0.0, "calls": [], "fault": None}

    def runner(run, label, command, plan, base, timeout, *, offline):
        alias, phase = label.split("-", 1)
        case = next(c for c in config["cases"] if c["alias"] == alias)
        assert (run / "receipts" / (alias + "-reserved.json")).is_file()
        state["calls"].append((label, command, timeout, offline))
        assert plan["budgets"]["workspace_bytes"] == 128 * 1024**2
        assert timeout <= (80 if phase == "network" else 20)
        work = run / "scratch" / label
        work.mkdir()
        exclusive_json(run / "receipts" / (label + "-job.json"), {"invented": True})
        if state["fault"] == "cleanup_uncertain":
            (work / "owned-scratch").write_bytes(b"invented")
            raise RecoveryError("cleanup_unconfirmed_keep_scratch")
        exclusive_json(
            run / "receipts" / (label + "-result.json"),
            {"cleanup_confirmed": True, "code": "completed"},
        )
        state["time"] += 0.1
        if phase == "network":
            assert offline is False
            media = run / "scratch" / (alias + "-download") / "media.mp4"
            media.write_bytes(b"invented media, never decoded")
            return json.dumps(
                {
                    "id": case["sample_id"] if state["fault"] != "identity" else "wrong",
                    "webpage_url": case["source_url"],
                    "duration": 20.0,
                    "ext": "mp4",
                }
            ).encode()
        assert offline is True
        if state["fault"]:
            return json.dumps({"error_code": state["fault"]}).encode()
        native = work / "native.png"
        Image.new("RGB", (360, 640), "red").save(native)
        media = run / "scratch" / (alias + "-download") / "media.mp4"
        return json.dumps(
            {
                "alias": alias,
                "sheet_sha256": case["sheet_sha256"],
                "crop_sha256": case["png_sha256"],
                "properties_sha256": recovery.json_digest(case["historical_properties"]),
                "native_pts": case["seconds"],
                "native_size": [360, 640],
                "media_sha256": digest(media),
                "bridge_complete": True,
                "native_sha256": digest(native),
            }
        ).encode()

    return SimpleNamespace(
        root=root,
        folder=folder,
        plan=plan,
        checksum=checksum,
        review=review,
        state=state,
        runner=runner,
        clock=lambda: state["time"],
        wall=lambda: datetime.fromisoformat("2026-10-21T12:00:00-03:00").timestamp(),
    )


def execute(op, **kwargs):
    return recovery.acquire(
        op.root, runner=op.runner, clock=op.clock, wall=kwargs.get("wall", op.wall)
    )


def test_pair_runs_once_in_order_and_keeps_only_verified_native_frames(operator):
    result = execute(operator)
    assert result["status"] == "completed" and result["acquisition_attempts"] == 2
    assert result["cleanup_confirmed"] and result["generations"] == 0
    assert [c[0] for c in operator.state["calls"]] == [
        "positive-network",
        "positive-bridge",
        "negative-network",
        "negative-bridge",
    ]
    run = operator.folder / "run"
    assert sorted(p.name for p in (run / "frames").iterdir()) == ["negative.png", "positive.png"]
    assert not list((run / "scratch").iterdir())
    count = len(operator.state["calls"])
    with pytest.raises(FileExistsError):
        execute(operator)
    assert len(operator.state["calls"]) == count


@pytest.mark.parametrize(
    "code",
    [
        "historical_properties_mismatch",
        "historical_pts_mismatch",
        "historical_sheet_or_crop_mismatch",
        "native_geometry_changed",
        "exact_native_pts_missing",
    ],
)
def test_bridge_rejection_closes_entire_stage_before_second_source(operator, code):
    operator.state["fault"] = code
    result = execute(operator)
    assert result["status"] == "stopped" and result["stop_code"] == code
    assert result["acquisition_attempts"] == 1 and result["verified_frames"] == []
    assert result["cleanup_confirmed"]
    assert len(operator.state["calls"]) == 2
    assert not list((operator.folder / "run/frames").iterdir())


def test_identity_failure_does_not_decode_or_try_second_source(operator):
    operator.state["fault"] = "identity"
    result = execute(operator)
    assert result["stop_code"] == "download_identity_mismatch"
    assert result["acquisition_attempts"] == 1 and len(operator.state["calls"]) == 1


def test_elapsed_budget_does_not_reset_before_bridge_or_next_source(operator):
    original = operator.runner

    def runner(*args, **kwargs):
        result = original(*args, **kwargs)
        operator.state["time"] = 421
        return result

    operator.runner = runner
    result = execute(operator)
    assert result["stop_code"] == "overall_deadline"
    assert result["acquisition_attempts"] == 1 and len(operator.state["calls"]) == 1


def test_symlink_run_refuses_without_touching_existing_target(operator):
    existing = operator.folder / "preexisting-protected"
    existing.mkdir()
    (existing / "sentinel").write_bytes(b"keep")
    (operator.folder / "run").symlink_to(existing, target_is_directory=True)
    with pytest.raises(RecoveryError, match="private_symlink_forbidden"):
        execute(operator)
    assert (existing / "sentinel").read_bytes() == b"keep"
    assert not operator.state["calls"]


def test_uncertain_cleanup_keeps_only_owned_scratch_and_seals(operator):
    operator.state["fault"] = "cleanup_uncertain"
    result = execute(operator)
    assert not result["cleanup_confirmed"]
    assert result["state"] == "sealed" and result["stop_code"] == "cleanup_unconfirmed_keep_scratch"
    assert (operator.folder / "run/scratch/positive-network/owned-scratch").is_file()
    assert len(operator.state["calls"]) == 1


def test_missing_release_and_expiry_refuse_before_run_or_process(operator):
    with pytest.raises(RecoveryError, match="retention_expired"):
        execute(operator, wall=lambda: datetime.fromisoformat(recovery.RETENTION).timestamp())
    assert not (operator.folder / "run").exists()
    (operator.folder / "technical-release.json").unlink()
    with pytest.raises(FileNotFoundError):
        execute(operator)
    assert not operator.state["calls"] and not (operator.folder / "run").exists()


@pytest.mark.parametrize(
    "field",
    [
        "protocol",
        "decision",
        "plan_sha256",
        "configuration_sha256",
        "execution_root_sha256",
        "reviewer_thread_id",
        "literal_message_sha256",
    ],
)
def test_review_bound_to_exact_checkout_plan_and_literal(operator, field):
    review = dict(operator.review, **{field: "invented_wrong_value"})
    (operator.folder / "technical-release.json").write_text(json.dumps(review))
    with pytest.raises(RecoveryError, match="technical_release_required"):
        execute(operator)
    assert not operator.state["calls"] and not (operator.folder / "run").exists()


def test_historical_download_selector_and_no_retry_are_preserved(tmp_path):
    command = recovery.boundary.download_command(
        recovery.source_identity(invented_case()),
        tmp_path,
        "/invented/python",
        "/invented/ffmpeg",
        "single_or_copy_remux",
    )
    assert (
        command[command.index("--format") + 1]
        == "best[height<=720][vcodec!=none][acodec!=none]/bestvideo[height<=720]+bestaudio"
    )
    for name in ["--retries", "--fragment-retries", "--extractor-retries"]:
        assert command[command.index(name) + 1] == "0"
    assert (
        "--ignore-config" in command
        and "--no-plugin-dirs" in command
        and "--no-remote-components" in command
    )
    assert not any("cookie" in x or "proxy" in x for x in command)


def test_existing_guard_creates_bridge_workspace_before_any_child(tmp_path, monkeypatch):
    run = tmp_path / "invented-guard-run"
    for name in ["scratch", "receipts"]:
        (run / name).mkdir(parents=True)

    def refuse_spawn(*args, **kwargs):
        assert (run / "scratch/positive-bridge").is_dir()
        assert (run / "receipts/positive-bridge-job.json").is_file()
        raise OSError("invented spawn refusal; no process created")

    monkeypatch.setattr(recovery.boundary, "sandbox_command", lambda *a, **k: ["invented"])
    monkeypatch.setattr(subprocess, "Popen", refuse_spawn)
    with pytest.raises(OSError, match="invented spawn refusal"):
        recovery.boundary.guarded_command(
            run,
            "positive-bridge",
            ["invented"],
            {"budgets": recovery.BUDGETS},
            {},
            20,
            offline=True,
        )
    assert not recovery.boundary.quiescent_receipts(run)


def test_prepare_never_creates_release_or_run_and_changed_sources_invalidate(tmp_path, monkeypatch):
    (tmp_path / "data/private").mkdir(parents=True)
    monkeypatch.setattr(recovery, "configuration", lambda root: {"invented": True})
    result = recovery.prepare(tmp_path)
    folder = tmp_path / recovery.QUEUE
    assert result["status"] == "prepared_not_released"
    assert sorted(p.name for p in folder.iterdir()) == ["plan.json"]
    monkeypatch.setattr(recovery, "configuration", lambda root: {"invented": False})
    with pytest.raises(RecoveryError, match="execution_configuration_changed"):
        recovery.load(tmp_path)


@pytest.fixture(params=["positive", "negative"])
def pixel_bridge(tmp_path, request):
    case = invented_case(request.param)
    media = tmp_path / "invented.bin"
    media.write_bytes(b"not a media file")
    sheet = tmp_path / "old-sheet.bin"
    sheet.write_bytes(b"frozen sheet bytes")
    crops = []
    for i in range(4):
        p = tmp_path / f"old-crop-{i}.bin"
        p.write_bytes(f"frozen crop {i}".encode())
        crops.append(p)
    case["sheet_sha256"], case["png_sha256"] = (
        digest(sheet),
        digest(crops[case["source_frame"] - 1]),
    )
    state = {
        "props": dict(case["historical_properties"]),
        "seconds": [0.2, 1.5, 2.8, 12.0],
        "native_called": False,
    }

    def native(*args):
        state["native_called"] = True
        assert not (tmp_path / "native.png").exists()
        return Image.new("RGB", (360, 640), "blue")

    kwargs = {
        "legacy": lambda *a: (state["props"], crops),
        "select": lambda *a: (crops, state["seconds"]),
        "cells": lambda *a: (crops, sheet),
        "native": native,
    }
    return SimpleNamespace(
        case=case, media=media, work=tmp_path, state=state, kwargs=kwargs, sheet=sheet, crops=crops
    )


def test_native_is_saved_only_after_full_old_pixel_properties_and_pts_bridge(pixel_bridge):
    b = pixel_bridge
    result = frames.bridge(b.media, b.work, b.case, **b.kwargs)
    assert result["bridge_complete"] and b.state["native_called"]
    assert digest(b.work / "native.png") == result["native_sha256"]


@pytest.mark.parametrize("fault", ["properties", "pts", "other_pts", "sheet", "crop"])
def test_no_native_read_or_saved_on_any_legacy_mismatch(pixel_bridge, fault):
    b = pixel_bridge
    if fault == "properties":
        b.state["props"]["width"] = 720
    elif fault == "pts":
        b.state["seconds"][b.case["source_frame"] - 1] += 0.001
    elif fault == "other_pts":
        b.state["seconds"][1] += 0.001
    elif fault == "sheet":
        b.sheet.write_bytes(b"different")
    else:
        b.crops[b.case["source_frame"] - 1].write_bytes(b"different")
    with pytest.raises(RecoveryError):
        frames.bridge(b.media, b.work, b.case, **b.kwargs)
    assert not b.state["native_called"] and not (b.work / "native.png").exists()


@pytest.mark.parametrize(
    "times,expected", [([0.1, 0.2], True), ([0.199, 0.201], False), ([None], False)]
)
def test_native_uses_exact_pts_never_nearest_substitution(tmp_path, monkeypatch, times, expected):
    class Container:
        streams = SimpleNamespace(video=[object()])

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def decode(self, stream):
            return [
                SimpleNamespace(time=t, to_image=lambda: Image.new("RGB", (360, 640)))
                for t in times
            ]

    monkeypatch.setitem(sys.modules, "av", SimpleNamespace(open=lambda *a: Container()))
    if expected:
        assert frames.exact_frame(tmp_path / "invented", 0.2).size == (360, 640)
    else:
        with pytest.raises(RecoveryError):
            frames.exact_frame(tmp_path / "invented", 0.2)

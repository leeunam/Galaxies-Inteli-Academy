"""Offline tests for the recovery boundary; no media, model or network calls.

Prepared during the reserved VLM window. Execution requires the coordinator's
later local-check slot. All identities and paths below are invented.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.demo_recovery import (
    download_command,
    download_identity,
    guarded_command,
    input_manifest,
    no_other_model_jobs,
    remux_command,
)
from scripts.demo_recovery_policy import (
    ROOT,
    RecoveryError,
    discard_allowed,
    exclusive_json,
    reserve_phase,
    validate_proposal,
    validate_release,
)
from scripts.demo_recovery_process import supervise


def proposals():
    sources = [
        {"alias": name, "video_id": cid, "source_url": "https://www.youtube.com/watch?v=" + cid}
        for name, cid in [
            ("demo_a", "aaaaaaaaaaa"),
            ("demo_b", "bbbbbbbbbbb"),
            ("demo_c", "ccccccccccc"),
        ]
    ]
    base = {"sources": sources}
    plan = {
        "protocol": "demo-recovery-v3",
        "base_plan_sha256": "f" * 64,
        "sources": sources,
        "format_policy": "single_or_copy_remux",
        "input_retention_until": "2026-10-22T02:59:00+00:00",
        "budgets": {
            "per_acquisition_seconds": 180,
            "acquisition_seconds": 600,
            "analysis_seconds": 480,
            "overall_seconds": 1800,
            "file_bytes": 32 * 1024**2,
            "workspace_bytes": 384 * 1024**2,
            "rss_bytes": 3584 * 1024**2,
            "io_bytes": 65536,
            "minimum_free_bytes": 1024**3,
            "remux_seconds": 45,
            "extractor_threads": 4,
        },
    }
    return base, plan


def test_reviewer_must_bind_retention_format_plan_and_code():
    _, plan = proposals()
    release = {
        "protocol": "demo-recovery-technical-release-v1",
        "plan_sha256": "a" * 64,
        "code_sha256": {"scripts/demo_recovery.py": "b" * 64},
        "phases": ["acquire", "analyze", "handoff", "discard"],
        "input_retention_until": plan["input_retention_until"],
        "format_policy": plan["format_policy"],
        "offline_checks_receipt": "invented-check-receipt",
        "technical_review_reference": "invented-review",
    }
    validate_release(release, plan, "a" * 64, {"scripts/demo_recovery.py": "b" * 64}, "acquire")
    release["input_retention_until"] = "2026-10-23T00:00:00+00:00"
    with pytest.raises(RecoveryError, match="release_mismatch"):
        validate_release(release, plan, "a" * 64, {"scripts/demo_recovery.py": "b" * 64}, "acquire")


@pytest.mark.parametrize("mutation", ["url", "duplicate", "budget_bool", "budget_increase"])
def test_fixed_trio_and_upper_budgets_cannot_be_expanded(mutation):
    base, plan = proposals()
    plan = json.loads(json.dumps(plan))
    if mutation == "url":
        plan["sources"][0]["source_url"] = "https://example.invalid/unapproved"
    elif mutation == "duplicate":
        plan["sources"][1] = plan["sources"][0]
    elif mutation == "budget_bool":
        plan["budgets"]["file_bytes"] = True
    else:
        plan["budgets"]["per_acquisition_seconds"] = 181
    with pytest.raises(RecoveryError):
        validate_proposal(plan, base, expected_base_sha="f" * 64)


def test_consumed_phase_and_symlink_receipt_are_never_reused(tmp_path):
    reserve_phase(tmp_path, "acquire", "a" * 64)
    with pytest.raises(RecoveryError, match="consumed"):
        reserve_phase(tmp_path, "acquire", "a" * 64)
    target = tmp_path / "sentinel"
    target.write_text("unchanged")
    link = tmp_path / "receipt.json"
    link.symlink_to(target)
    with pytest.raises(RecoveryError):
        exclusive_json(link, {"invented": True})
    assert target.read_text() == "unchanged"


def test_same_source_not_historical_extension_controls_format_and_remux(tmp_path):
    source = proposals()[0]["sources"][0]
    command = download_command(
        source, tmp_path, Path(sys.executable), Path("/invented/ffmpeg"), "single_or_copy_remux"
    )
    assert command[-1] == source["source_url"]
    assert command[command.index("--retries") + 1] == "0"
    assert command[command.index("--extractor-retries") + 1] == "0"
    assert command[command.index("--fragment-retries") + 1] == "0"
    assert "--cookies" not in command and "--write-info-json" not in command
    remux = remux_command(Path("/invented/ffmpeg"), tmp_path / "in.mkv", tmp_path / "out.mp4")
    assert remux[remux.index("-c") + 1] == "copy"
    assert "libx264" not in remux and "scale" not in remux
    assert "-n" in remux


def test_untrusted_downloader_identity_and_extra_output_rejected():
    source = proposals()[0]["sources"][0]
    body = {
        "id": source["video_id"],
        "webpage_url": source["source_url"],
        "duration": 12.0,
        "ext": "mkv",
    }
    assert download_identity(json.dumps(body).encode(), source)["id"] == source["video_id"]
    body["id"] = "ddddddddddd"
    with pytest.raises(RecoveryError):
        download_identity(json.dumps(body).encode(), source)
    with pytest.raises(RecoveryError):
        download_identity(b"private unstructured output\n{}", source)


def test_inputs_cannot_be_removed_on_handoff_or_before_expiry():
    assert not discard_allowed(handoff_recorded=True, demo_completed=False, now=100, expires=200)
    assert discard_allowed(handoff_recorded=True, demo_completed=True, now=100, expires=200)
    assert discard_allowed(handoff_recorded=False, demo_completed=False, now=201, expires=200)
    assert not discard_allowed(handoff_recorded=False, demo_completed=True, now=100, expires=200)


def test_manifest_checks_physical_bytes_and_refuses_symlink(tmp_path):
    inputs = tmp_path / "inputs"
    inputs.mkdir()
    sources = proposals()[0]["sources"]
    for source in sources:
        (inputs / (source["alias"] + ".mp4")).write_bytes(source["alias"].encode())
    rows = input_manifest(inputs, sources, 100)
    assert len(rows) == 3 and len({row["sha256"] for row in rows}) == 3
    (inputs / "demo_c.mp4").unlink()
    (inputs / "demo_c.mp4").symlink_to(inputs / "demo_a.mp4")
    with pytest.raises(RecoveryError):
        input_manifest(inputs, sources, 100)


def test_resource_slot_refuses_model_process_without_spawning(tmp_path, monkeypatch):
    fake = tmp_path / "4242"
    fake.mkdir()
    (fake / "cmdline").write_bytes(b"python\0-m\0scripts.candidate_features\0")
    original = Path.iterdir
    monkeypatch.setattr(
        Path, "iterdir", lambda value: iter([fake]) if value == Path("/proc") else original(value)
    )
    with pytest.raises(RecoveryError, match="model_resource_slot_busy"):
        no_other_model_jobs()
    (fake / "cmdline").write_bytes(b"python\0-m\0unrelated.invented\0")
    no_other_model_jobs()


def job(tmp_path, code, *, timeout=2, io_bytes=65536):
    return {
        "argv": [sys.executable, "-B", "-c", code],
        "cwd": str(tmp_path),
        "env": {"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1"},
        "timeout": timeout,
        "io_bytes": io_bytes,
        "file_bytes": 1024**2,
        "workspace": str(tmp_path),
        "workspace_bytes": 8 * 1024**2,
        "rss_bytes": 256 * 1024**2,
        "lease": str(tmp_path / "process-lease.json"),
    }


def test_supervisor_bounds_output_before_retaining_it(tmp_path):
    result = supervise(job(tmp_path, "import os; os.write(1,b'x'*1000000)", io_bytes=512))
    assert result["code"] == "output_limit"
    assert result["cleanup_confirmed"]
    assert result["stdout_b64"] == ""


def test_timeout_reaps_session_escaping_grandchild_and_preserves_control(tmp_path):
    control = subprocess.Popen([sys.executable, "-B", "-c", "import time;time.sleep(30)"])
    try:
        pidfile = tmp_path / "own-child.pid"
        code = (
            "import subprocess,sys,time; "
            "p=subprocess.Popen([sys.executable,'-B','-c','import time;time.sleep(30)'],start_new_session=True); "
            f"open({str(pidfile)!r},'w').write(str(p.pid)); "
            "time.sleep(30)"
        )
        result = supervise(job(tmp_path, code, timeout=0.4))
        assert result["code"] == "timeout" and result["cleanup_confirmed"]
        assert not Path("/proc", pidfile.read_text()).exists()
        assert control.poll() is None
    finally:
        control.terminate()
        control.wait(timeout=5)


def test_real_supervisor_cancellation_collects_child(tmp_path):
    specification = job(
        tmp_path,
        "import os,signal,time;os.kill(os.getppid(),signal.SIGTERM);time.sleep(30)",
    )
    result = subprocess.run(
        [sys.executable, "-B", "-m", "scripts.demo_recovery_process"],
        cwd=ROOT,
        input=json.dumps(specification),
        capture_output=True,
        text=True,
        check=False,
        env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1"},
        timeout=10,
    )
    assert result.returncode == 0
    receipt = json.loads(result.stdout)
    assert receipt["code"] == "cancelled_consumed" and receipt["cleanup_confirmed"]


def test_real_file_size_limit_is_enforced_before_workspace_cleanup(tmp_path):
    destination = tmp_path / "oversized.bin"
    specification = job(tmp_path, f"open({str(destination)!r},'wb').write(b'x'*2000000)")
    result = supervise(specification)
    assert result["code"] == "child_failed" and result["cleanup_confirmed"]
    assert destination.stat().st_size <= specification["file_bytes"]


def test_real_offline_capsule_runs_only_a_content_free_child(tmp_path):
    cache = tmp_path / "empty-cache"
    cache.mkdir()
    run = tmp_path / "capsule"
    run.mkdir()
    for name in ("scratch", "receipts"):
        (run / name).mkdir()
    _, plan = proposals()
    base = {"local_analysis_configuration": {"readonly_hf_cache_bind_source": str(cache)}}
    raw = guarded_command(
        run,
        "content-free",
        [sys.executable, "-B", "-c", 'print("capsule_ok")'],
        plan,
        base,
        5,
        offline=True,
    )
    assert raw.strip() == b"capsule_ok"
    receipt = json.loads((run / "receipts/content-free-result.json").read_text())
    assert receipt["cleanup_confirmed"] and receipt["code"] == "completed"


def test_frozen_native_extractor_does_not_request_vlm():
    # Critical static call boundary: the frozen code is not patched to achieve
    # this. No encoder/model import or weight access is needed for this check.
    import ast

    candidate = ast.parse((ROOT / "scripts/candidate_features.py").read_text())
    calls = [
        node
        for node in ast.walk(candidate)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "extract_features"
    ]
    assert len(calls) == 1 and isinstance(calls[0].args[3], ast.Constant)
    assert calls[0].args[3].value is False
    extraction = ast.parse((ROOT / "scripts/pilot_licensed_media.py").read_text())
    function = next(
        node
        for node in extraction.body
        if isinstance(node, ast.FunctionDef) and node.name == "extract_features"
    )
    guards = [
        node
        for node in ast.walk(function)
        if isinstance(node, ast.If)
        and isinstance(node.test, ast.Name)
        and node.test.id == "include_vlm"
    ]
    assert len(guards) == 1
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "extract_visual_attributes"
        for node in ast.walk(guards[0])
    )

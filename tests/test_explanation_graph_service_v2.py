"""Real process containment around an EXPLICITLY INVENTED numerical worker."""

# ruff: noqa: F811

import asyncio
import json
import os
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

import pytest

from scripts.explanation_graph_service_v2 import ROOT, GraphSettings, analyze_via_graph
from tests.test_explanation_evidence import evidence_inputs  # noqa: F401
from tests.test_explanation_session_v2 import invented_data  # noqa: F401
from tests.test_m1_service import serving  # noqa: F401


@pytest.fixture
def graph_settings(tmp_path, invented_data):
    graph_python = os.environ.get("GALAXIES_GRAPH_PYTHON")
    if not graph_python:
        pytest.skip("Explicit isolated graph interpreter required")
    fixture = tmp_path / "INVENTED-evidence.json"
    fixture.write_text(json.dumps(invented_data))
    return GraphSettings(
        Path(graph_python),
        Path(sys.executable),
        tmp_path / "uploads",
        tmp_path / "registry.json",
        tmp_path / "owned-scratch",
        worker_module="tests.native_v2_fixture",
        worker_arguments_extra=("--fixture-json", str(fixture)),
    )


def assert_dead(pids):
    for pid in pids:
        with pytest.raises(ProcessLookupError):
            os.kill(pid, 0)


def test_real_two_environment_service_keeps_original_report_and_reaps(
    graph_settings, invented_data, monkeypatch
):
    monkeypatch.setenv("NVIDIA_API_KEY", "PRIVATE_CREDENTIAL")
    monkeypatch.setenv("HTTPS_PROXY", "PRIVATE_PROXY")
    result = asyncio.run(analyze_via_graph({"brief": "PRIVATE_BRIEF"}, graph_settings))
    assert result["analysis"] == invented_data["report"]
    assert result["orchestration"]["stategraph_executed"]
    assert not result["orchestration"]["native_feature_handoff"]  # invented fixture is honest
    assert not result["orchestration"]["real_provider_verified"]
    assert result["explanation"]["reason_code"] == "transport_not_configured"
    assert any("shap" in row["evidence_id"] for row in result["evidence_packet"]["evidence"])
    assert not list(graph_settings.scratch_root.iterdir())
    assert "PRIVATE" not in json.dumps(result)


@pytest.mark.parametrize("mode", ["crash", "launch_failure"])
def test_abrupt_worker_death_preserves_checkpoint_and_collects_grandchildren(
    graph_settings, invented_data, tmp_path, mode
):
    pids = tmp_path / "pids.json"
    settings = replace(
        graph_settings,
        worker_arguments_extra=graph_settings.worker_arguments_extra
        + ("--mode", mode, "--pid-file", str(pids)),
    )
    result = asyncio.run(analyze_via_graph({}, settings))
    assert result["analysis"] == invented_data["report"]
    assert result["explanation"]["reason_code"] == "explanation_worker_failed"
    assert not list(settings.scratch_root.iterdir())
    if mode == "crash":
        ids = json.loads(pids.read_bytes())
        assert_dead([ids["worker"], ids["child"]])


@pytest.mark.parametrize("cancel", [True, False])
def test_cancellation_or_timeout_collects_live_descendants_and_preserves_control_process(
    graph_settings, tmp_path, cancel
):
    pids = tmp_path / "pids.json"
    settings = replace(
        graph_settings,
        timeout_seconds=20 if cancel else 3,
        worker_arguments_extra=graph_settings.worker_arguments_extra
        + ("--mode", "block", "--pid-file", str(pids)),
    )
    control = subprocess.Popen([sys.executable, "-B", "-c", "import time; time.sleep(90)"])

    async def scenario():
        task = asyncio.create_task(analyze_via_graph({}, settings))
        for _ in range(500):
            if pids.exists():
                break
            await asyncio.sleep(0.01)
        assert pids.exists(), "fixture did not enter its controlled blocking stage"
        if cancel:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            result = await task
            assert result["explanation"]["reason_code"] == "explanation_worker_failed"
        ids = json.loads(pids.read_bytes())
        assert_dead([ids["worker"], ids["child"]])
        assert not list(settings.scratch_root.iterdir())
        assert control.poll() is None

    try:
        asyncio.run(scenario())
    finally:
        control.kill()
        control.wait()


def test_invalid_executable_and_actual_root_worker_fail_safely(graph_settings):
    missing = replace(graph_settings, graph_python=Path("/absent/galaxies-python"))
    assert "orchestration_error" in asyncio.run(analyze_via_graph({}, missing))
    assert not list(graph_settings.scratch_root.iterdir())
    production = replace(
        graph_settings, worker_module="scripts.explanation_worker_v2", worker_arguments_extra=()
    )
    result = asyncio.run(analyze_via_graph({}, production))
    assert result["analysis"]["error"]["code"] == "invalid_request"
    assert result["explanation"]["reason_code"] == "m1_prediction_required"
    assert not result["orchestration"]["native_feature_handoff"]


def test_cancel_during_spawn_retains_handle_and_reaps_before_cleanup(graph_settings, monkeypatch):
    original = asyncio.create_subprocess_exec

    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()
        spawned = []

        async def delayed(*args, **kwargs):
            process = await original(*args, **kwargs)
            spawned.append(process)
            entered.set()
            await release.wait()
            return process

        monkeypatch.setattr(asyncio, "create_subprocess_exec", delayed)
        task = asyncio.create_task(analyze_via_graph({}, graph_settings))
        await entered.wait()
        task.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert spawned[0].returncode is not None
        assert not list(graph_settings.scratch_root.iterdir())

    asyncio.run(scenario())


def test_real_session_all_predictions_unavailable_preserves_reason_and_numbers(
    graph_settings, tmp_path
):
    from tests.native_v2_fixture import public_data

    data = public_data(3)
    report = data["report"]
    report["status"] = "m1_prediction_incomplete"
    report["learned_prediction_available"] = False
    report["ranking"] = {
        "status": "unavailable",
        "reason_code": "incomplete_predictions",
        "value": None,
    }
    for candidate in report["candidates"]:
        candidate["extraction"]["text_status"] = "no_audio_stream"
        candidate["prediction"] = {
            "status": "unavailable",
            "reason_code": "unsupported_text_status",
            "value": None,
        }
        candidate["interval"] = candidate["prediction"].copy()
    fixture = tmp_path / "invented-unavailable.json"
    fixture.write_text(json.dumps(data))
    settings = replace(graph_settings, worker_arguments_extra=("--fixture-json", str(fixture)))
    result = asyncio.run(analyze_via_graph({}, settings))
    assert result["analysis"] == report
    assert result["evidence_packet"] is None
    assert result["explanation"]["reason_code"] == "learned_prediction_unavailable"
    assert not list(settings.scratch_root.iterdir())


def test_interpreters_import_clone_code_without_environment_installation(graph_settings):
    commands = [
        (graph_settings.worker_python, ROOT, "import scripts.m1_service as m; print(m.__file__)"),
        (
            graph_settings.graph_python,
            ROOT / "orchestration",
            "import galaxies_orchestration.integrated_graph_v2 as m; print(m.__file__)",
        ),
    ]
    for python, cwd, code in commands:
        run = subprocess.run(
            [str(python), "-B", "-c", code],
            cwd=cwd,
            capture_output=True,
            text=True,
            env={"PATH": os.defpath, "PYTHONDONTWRITEBYTECODE": "1"},
            timeout=15,
            check=True,
        )
        assert run.stdout.strip().startswith(str(ROOT))


def test_supervisor_sigkill_requires_explicit_lease_verified_recovery(graph_settings, tmp_path):
    from scripts.explanation_supervisor_v2 import identity

    pids = tmp_path / "pids.json"
    settings = replace(
        graph_settings,
        worker_arguments_extra=graph_settings.worker_arguments_extra
        + ("--mode", "block", "--pid-file", str(pids)),
    )

    async def scenario():
        task = asyncio.create_task(analyze_via_graph({}, settings))
        for _ in range(500):
            if pids.exists():
                break
            await asyncio.sleep(0.01)
        assert pids.exists()
        run_dir = next(settings.scratch_root.iterdir())
        lease = json.loads((run_dir / "process-lease.json").read_bytes())
        assert lease["boot_id"] == Path("/proc/sys/kernel/random/boot_id").read_text().strip()
        assert identity(lease["supervisor"]["pid"]) == lease["supervisor"]
        os.kill(lease["supervisor"]["pid"], signal.SIGKILL)
        result = await task
        assert "orchestration_error" in result
        assert run_dir.exists()  # no false cleanup acknowledgement
        # Explicit manual recovery of this test's own group, after PID identity
        # verification, never an automatic action on an ambiguous reused PID.
        assert identity(lease["leader"]["pid"]) == lease["leader"]
        assert os.getpgid(lease["leader"]["pid"]) == lease["pgid"]
        os.killpg(lease["pgid"], signal.SIGKILL)
        children = json.loads(pids.read_bytes())
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if all(
                not Path(f"/proc/{pid}").exists()
                for pid in (children["worker"], children["child"], lease["pgid"])
            ):
                break
            await asyncio.sleep(0.01)
        assert_dead([children["worker"], children["child"], lease["pgid"]])
        shutil.rmtree(run_dir)
        (tmp_path / "manual-recovery.json").write_text(
            json.dumps(
                {
                    "test_only": True,
                    "supervisor_killed": True,
                    "lease_identity_verified": True,
                    "group_terminated": True,
                    "scratch_removed_after_termination": True,
                }
            )
        )
        assert not list(settings.scratch_root.iterdir())

    asyncio.run(scenario())

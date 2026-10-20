"""Offline behavioral checks; all secrets/transports/responses are invented."""

import asyncio
import hashlib
import json
import multiprocessing
import os
import socket
import sys
from pathlib import Path

import pytest

from scripts import nim_dispatch_ledger_v3 as ledger
from scripts import nim_dispatch_plan_v3 as plan
from scripts import nim_dispatch_v3 as dispatch
from scripts import nim_observed_http_worker_v3 as worker
from scripts.nim_dispatch_fakes_v3 import INVENTED_KEY, INVENTED_SECRET, connection_factory
from scripts.nim_dispatch_summary_v3 import validate_summary


@pytest.fixture(autouse=True)
def no_remote_or_credentials(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("offline_test_attempted_remote_or_credential")

    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    # Only guard the old getter, do not invoke it or inspect real env/files.
    from orchestration.galaxies_orchestration import nim_http

    monkeypatch.setattr(nim_http, "existing_key", forbidden)


def test_plan_is_fixed_and_remote_blocked(tmp_path):
    value = plan.verify_plan()
    assert value["max_calls"] == 1
    assert value["http_payload_sha256"] == plan.digest(plan.payload_bytes())
    assert value["endpoint"] == "https://integrate.api.nvidia.com/v1/chat/completions"
    with pytest.raises(ValueError, match="remote_release_absent"):
        worker.remote_exchange(tmp_path, b"x" * 32)
    assert list(tmp_path.iterdir()) == []
    assert plan.ROOT == Path(__file__).resolve().parents[1]


def test_remote_parent_is_blocked_before_reservation(tmp_path, monkeypatch):
    monkeypatch.setattr(dispatch, "LEDGER", tmp_path / "never-created")
    with pytest.raises(ValueError, match="remote_release_absent"):
        asyncio.run(dispatch.execute_released())
    assert list(tmp_path.iterdir()) == []


def test_a_local_zero_cost_boolean_and_seal_are_insufficient(monkeypatch):
    monkeypatch.setattr(plan, "REMOTE_PLAN_SHA256", plan.PLAN_SHA256)
    with pytest.raises(ValueError, match="remote_release_absent"):
        plan.verify_plan(remote=True)


@pytest.mark.parametrize("target", ["plan", "fixture", "source"])
def test_tampered_inputs_refused_before_reservation(tmp_path, monkeypatch, target):
    if target == "plan":
        path = tmp_path / "plan.json"
        path.write_bytes(plan.PLAN.read_bytes() + b" ")
        monkeypatch.setattr(plan, "PLAN", path)
    elif target == "fixture":
        path = tmp_path / "fixture.json"
        path.write_bytes(b'{"private_brief":"entirely invented forbidden value"}')
        monkeypatch.setattr(plan, "FIXTURE", path)
    else:
        # A source hash mismatch, with a sealed synthetic plan copy for the test.
        value = json.loads(plan.PLAN.read_bytes())
        name = next(iter(value["sources_sha256"]))
        value["sources_sha256"][name] = "0" * 64
        path = tmp_path / "plan.json"
        path.write_bytes(plan.canonical(value))
        monkeypatch.setattr(plan, "PLAN", path)
        monkeypatch.setattr(plan, "PLAN_SHA256", plan.digest(path.read_bytes()))
    output = tmp_path / "not_reserved"
    with pytest.raises(ValueError):
        asyncio.run(dispatch.execute_offline("valid", output))
    assert not output.exists()


def test_arbitrary_request_endpoint_and_plan_fields_cannot_be_supplied(tmp_path, monkeypatch):
    value = json.loads(plan.PLAN.read_bytes())
    value["endpoint"] = "https://entirely-invented.invalid/"
    value["payload"] = "invented forbidden brief"
    path = tmp_path / "plan.json"
    path.write_bytes(plan.canonical(value))
    monkeypatch.setattr(plan, "PLAN", path)
    monkeypatch.setattr(plan, "PLAN_SHA256", plan.digest(path.read_bytes()))
    with pytest.raises(ValueError, match="contract_mismatch"):
        plan.verify_plan()


def test_environment_is_literal_and_does_not_read_inherited_values(monkeypatch):
    class UnreadableOS:
        @property
        def environ(self):
            raise AssertionError("must_not_read_inherited_environment")

    monkeypatch.setattr(dispatch, "os", UnreadableOS())
    environment = dispatch.child_environment()
    assert set(environment) == {
        "LANG",
        "LC_ALL",
        "PYTHONNOUSERSITE",
        "PYTHONDONTWRITEBYTECODE",
        "HF_HUB_OFFLINE",
        "TRANSFORMERS_OFFLINE",
        "LANGSMITH_TRACING",
        "LANGCHAIN_TRACING_V2",
        "CUDA_VISIBLE_DEVICES",
        "OMP_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "MKL_NUM_THREADS",
    }


def _reserve_racer(folder, queue):
    try:
        ledger.reserve(folder, "a" * 64, offline=True)
        queue.put("reserved")
    except FileExistsError:
        queue.put("consumed")


def test_competing_processes_get_exactly_one_reservation(tmp_path):
    context = multiprocessing.get_context("fork")
    queue = context.Queue()
    folder = tmp_path / "one-plan-one-ledger"
    processes = [context.Process(target=_reserve_racer, args=(folder, queue)) for _ in range(4)]
    for process in processes:
        process.start()
    for process in processes:
        process.join(5)
        assert process.exitcode == 0
    assert sorted(queue.get(timeout=1) for _ in processes) == ["consumed"] * 3 + ["reserved"]
    assert (folder.stat().st_mode & 0o777) == 0o700
    assert ((folder / "reservation-v3.json").stat().st_mode & 0o777) == 0o600


def test_consumed_directory_without_receipt_cannot_be_reused(tmp_path, monkeypatch):
    folder = tmp_path / "crash"

    def crash(*args):
        raise OSError(INVENTED_SECRET)

    monkeypatch.setattr(ledger, "create", crash)
    with pytest.raises(OSError):
        ledger.reserve(folder, "a" * 64, offline=True)
    assert folder.is_dir() and list(folder.iterdir()) == []
    with pytest.raises(FileExistsError):
        ledger.reserve(folder, "a" * 64, offline=True)


def test_failed_durability_never_starts_child(tmp_path, monkeypatch):
    calls = []

    async def runner(*args, **kwargs):
        calls.append(True)

    def fail_sync(path):
        raise OSError(INVENTED_SECRET)

    monkeypatch.setattr(ledger, "sync_directory", fail_sync)
    with pytest.raises(OSError):
        asyncio.run(dispatch.execute_offline("valid", tmp_path / "reservation", runner=runner))
    assert calls == []


def test_nested_new_directories_and_files_are_synced(tmp_path, monkeypatch):
    actual = ledger.sync_directory
    synced = []

    def record(path):
        synced.append(path)
        actual(path)

    monkeypatch.setattr(ledger, "sync_directory", record)
    folder = tmp_path / "new" / "nested" / "reservation"
    ledger.reserve(folder, "a" * 64, offline=True)
    assert synced == [tmp_path, tmp_path / "new", folder.parent, folder]


def test_no_old_or_remote_ledger_or_symlink_simulations(tmp_path, monkeypatch):
    old = tmp_path / "issue-5-nim-sintetico-unico-v1"
    with pytest.raises(ValueError):
        ledger.reserve(old, "a" * 64, offline=True)
    remote = tmp_path / "remote-v3"
    monkeypatch.setattr(dispatch, "LEDGER", remote)
    with pytest.raises(ValueError):
        asyncio.run(dispatch.execute_offline("valid", remote / "child"))
    target = tmp_path / "real-directory"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError):
        ledger.reserve(link / "simulation", "a" * 64, offline=True)
    assert not old.exists() and not remote.exists() and list(target.iterdir()) == []


def test_nonce_parent_binding_and_exclusive_dispatch(tmp_path, monkeypatch):
    folder, nonce = ledger.reserve(tmp_path / "binding", "a" * 64, offline=True)
    with pytest.raises(ValueError):
        ledger.authorize(folder, b"x" * 32, "a" * 64, offline=True)
    with pytest.raises(ValueError):
        ledger.authorize(folder, nonce, "b" * 64, offline=True)
    with pytest.raises(ValueError):
        ledger.authorize(folder, nonce, "a" * 64, offline=True)  # real getppid differs
    monkeypatch.setattr(os, "getppid", os.getpid)
    ledger.authorize(folder, nonce, "a" * 64, offline=True)
    with pytest.raises(FileExistsError):
        ledger.authorize(folder, nonce, "a" * 64, offline=True)


def test_http_uses_one_fixed_request_and_credential_only_in_header():
    calls = []
    original = connection_factory("valid")

    class Recording(original):
        def __init__(self, *args, **kwargs):
            calls.append((args, kwargs))

        def request(self, method, path, *, body, headers):
            calls.append((method, path, body, headers))

    result = worker.exchange(INVENTED_KEY, factory=Recording)
    assert result["selection_validated"] is True
    assert len(calls) == 2
    args, options = calls[0]
    assert args == ("integrate.api.nvidia.com",)
    assert options["port"] == 443 and options["timeout"] == 45
    assert options["context"].check_hostname is True
    method, path, body, headers = calls[1]
    assert method == "POST" and path == "/v1/chat/completions"
    assert body == plan.payload_bytes()
    assert INVENTED_KEY.encode() not in body
    assert headers == {
        "Authorization": "Bearer " + INVENTED_KEY,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


@pytest.mark.parametrize(
    "case, phase, code",
    [
        ("valid", "rendering", "accepted"),
        ("redirect", "transport", "http_error"),
        ("http_error", "transport", "http_error"),
        ("read_exception", "transport", "response_read_failed"),
        ("send_failure", "transport", "request_failed_outcome_uncertain"),
        ("bad_content_type", "transport", "protocol_rejected"),
        ("compressed", "transport", "protocol_rejected"),
        ("large_content_length", "transport", "protocol_rejected"),
        ("ambiguous_length", "transport", "protocol_rejected"),
        ("bad_transfer_encoding", "transport", "protocol_rejected"),
        ("tokens_limit", "schema", "envelope_schema_invalid"),
        ("bad_status", "transport", "invalid_http_status"),
        ("bad_wire_type", "transport", "invalid_wire_type"),
        ("wire_limit", "transport", "wire_byte_limit"),
        ("wire_unicode", "utf8", "invalid_wire_unicode"),
        ("wire_json", "json", "envelope_json_syntax"),
        ("wire_duplicate", "json", "envelope_duplicate_key"),
        ("content_deep", "json", "json_depth_limit"),
        ("unknown_id", "references", "unknown_evidence_id"),
        ("wrong_hash", "references", "packet_hash_mismatch"),
        ("duplicate_ids", "references", "duplicate_evidence_id"),
        ("secret_fieldname", "schema", "schema_extra_field"),
        ("secret_digest", "references", "packet_hash_mismatch"),
        ("secret_id", "references", "unknown_evidence_id"),
        ("content_extra_secret", "schema", "schema_extra_field"),
        ("envelope_extra_secret", "rendering", "accepted"),
        ("close_failure", "rendering", "accepted"),
    ],
)
def test_fake_http_observes_before_any_output(case, phase, code, capsys):
    result = worker.exchange(INVENTED_KEY, factory=connection_factory(case))
    assert (result["phase"], result["code"]) == (phase, code)
    assert result["selection_validated"] == (code == "accepted")
    serialized = json.dumps(result)
    assert INVENTED_SECRET not in serialized and INVENTED_KEY not in serialized
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize(
    "change",
    [
        {"code": INVENTED_SECRET},
        {"http_status": True},
        {"completion_tokens": 2049},
        {"wire_bytes": 16385},
        {"wire_bytes": 0},
        {"unknown": INVENTED_SECRET},
        {
            "safe_response_projection": {
                "packet_sha256": "a" * 64,
                "evidence_ids": [INVENTED_SECRET],
            }
        },
    ],
)
def test_parent_refuses_untrusted_ipc_fields(change):
    summary = worker.exchange(INVENTED_KEY, factory=connection_factory("valid"))
    summary.update(change)
    with pytest.raises(ValueError):
        validate_summary(summary)


@pytest.mark.parametrize(
    "case, change, projection_change, accepted_by_parent",
    [
        ("valid", {}, None, True),
        ("duplicate_ids", {}, None, True),
        ("unknown_id", {}, None, True),
        ("valid", {}, "duplicate_ids", False),
        ("valid", {}, "none", False),
        ("valid", {"wire_bytes": 0}, None, False),
        ("valid", {"selection_validated": False}, None, False),
        ("valid", {"authority_status": "rejected"}, None, False),
        ("valid", {"authority_status": "not_invoked"}, None, False),
        ("valid", {"code": "duplicate_evidence_id", "phase": "references"}, None, False),
        ("duplicate_ids", {"selection_validated": True}, None, False),
        ("duplicate_ids", {"authority_status": "accepted"}, None, False),
        ("duplicate_ids", {"authority_status": "not_invoked"}, None, False),
        ("duplicate_ids", {"authority_status": "failed_before_result"}, None, False),
        ("duplicate_ids", {}, "unique_ids", False),
        ("duplicate_ids", {}, "none", False),
        ("duplicate_ids", {"http_status": 302}, None, False),
        ("duplicate_ids", {"completion_tokens": None}, None, False),
        ("duplicate_ids", {"wire_bytes": None}, None, False),
        ("duplicate_ids", {"wire_bytes": 0}, None, False),
        ("unknown_id", {}, "unique_ids", False),
    ],
)
def test_parent_ipc_preserves_authority_acceptance_and_duplicate_diagnostics(
    case, change, projection_change, accepted_by_parent, capsys
):
    # Start with actual sealed-authority/v2 results, then corrupt only child IPC.
    # The real parent consumes the bytes through a subprocess, rather than calling
    # a copied uniqueness predicate or only testing validate_summary directly.
    summary = worker.exchange(INVENTED_KEY, factory=connection_factory(case))
    summary.update(change)
    if projection_change == "none":
        summary["safe_response_projection"] = None
    elif projection_change is not None:
        public = json.loads(plan.FIXTURE.read_bytes())
        summary["safe_response_projection"] = {
            "packet_sha256": public["packet_sha256"],
            "evidence_ids": (
                ["c1_prediction", "c1_prediction"]
                if projection_change == "duplicate_ids"
                else ["c1_prediction", "c1_interval"]
            ),
        }
    child_output = json.dumps({"worker_status": "observed", "summary": summary})
    source = "import sys;sys.stdout.write(" + repr(child_output) + ")"
    result = asyncio.run(
        dispatch.bounded_child([sys.executable, "-c", source], b"x" * 32, timeout=3)
    )
    if accepted_by_parent:
        assert result == {"outcome": "observed", "summary": summary}
        assert result["summary"]["selection_validated"] is (case == "valid")
        if case == "duplicate_ids":
            assert result["summary"]["authority_status"] == "rejected"
            assert result["summary"]["safe_response_projection"]["evidence_ids"] == [
                "c1_prediction",
                "c1_prediction",
            ]
    else:
        assert result == {"outcome": "invalid_child_protocol"}
    assert capsys.readouterr() == ("", "")


def test_fake_child_is_observed_consumed_and_never_repeated(tmp_path, capsys):
    folder = tmp_path / "child-valid"
    result = asyncio.run(dispatch.execute_offline("valid", folder))
    assert result["outcome"] == "observed"
    assert result["summary"]["selection_validated"] is True
    assert result["real_requests"] == 0 and result["offline_simulation_only"] is True
    assert {path.name for path in folder.iterdir()} == {
        "reservation-v3.json",
        "dispatch-v3.json",
        "result-v3.json",
    }
    with pytest.raises(FileExistsError):
        asyncio.run(dispatch.execute_offline("valid", folder))
    retained = b"".join(path.read_bytes() for path in folder.iterdir())
    assert INVENTED_SECRET.encode() not in retained and INVENTED_KEY.encode() not in retained
    assert capsys.readouterr() == ("", "")


@pytest.mark.parametrize("case", ["secret_fieldname", "secret_id", "content_deep", "redirect"])
def test_adversarial_fake_child_retains_only_public_projection(tmp_path, case):
    folder = tmp_path / case
    receipt = asyncio.run(dispatch.execute_offline(case, folder))
    assert receipt["outcome"] == "observed"
    assert receipt["summary"]["selection_validated"] is False
    assert receipt["summary"]["safe_response_projection"] is None
    retained = b"".join(path.read_bytes() for path in folder.iterdir())
    assert INVENTED_SECRET.encode() not in retained
    assert hashlib.sha256(INVENTED_SECRET.encode()).hexdigest().encode() not in retained


def test_crash_after_dispatch_is_consumed(tmp_path):
    folder = tmp_path / "crash-after-dispatch"
    result = asyncio.run(dispatch.execute_offline("crash", folder))
    assert result["outcome"] == "child_failed_outcome_uncertain"
    assert (folder / "dispatch-v3.json").exists()
    with pytest.raises(FileExistsError):
        asyncio.run(dispatch.execute_offline("valid", folder))


def test_timeout_kills_child_and_consumes_without_retry(tmp_path):
    folder = tmp_path / "hang"
    result = asyncio.run(dispatch.execute_offline("hang", folder, timeout=1.5))
    assert result["outcome"] == "timeout_outcome_uncertain"
    assert (folder / "result-v3.json").exists()
    with pytest.raises(FileExistsError):
        asyncio.run(dispatch.execute_offline("valid", folder))


def test_cancellation_during_spawn_collects_handle_without_releasing_nonce(tmp_path, monkeypatch):
    async def exercise():
        original = asyncio.create_subprocess_exec
        created, release = asyncio.Event(), asyncio.Event()
        processes = []

        async def delayed_spawn(*args, **kwargs):
            process = await original(*args, **kwargs)
            processes.append(process)
            created.set()
            await release.wait()
            return process

        monkeypatch.setattr(asyncio, "create_subprocess_exec", delayed_spawn)
        marker = tmp_path / "nonce-was-released"
        source = (
            "import sys,pathlib;sys.stdin.buffer.read(32);pathlib.Path("
            + repr(str(marker))
            + ").touch()"
        )
        task = asyncio.create_task(
            dispatch.bounded_child([sys.executable, "-c", source], b"x" * 32, timeout=3)
        )
        await created.wait()
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()  # cancellation during handle recovery must also be safe
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert len(processes) == 1 and processes[0].returncode is not None
        assert not marker.exists()

    asyncio.run(exercise())


def test_timeout_during_spawn_collects_without_dispatch(tmp_path, monkeypatch):
    async def exercise():
        original = asyncio.create_subprocess_exec
        processes = []

        async def delayed_spawn(*args, **kwargs):
            process = await original(*args, **kwargs)
            processes.append(process)
            await asyncio.sleep(0.15)
            return process

        monkeypatch.setattr(asyncio, "create_subprocess_exec", delayed_spawn)
        marker = tmp_path / "never-dispatched"
        source = (
            "import sys,pathlib;sys.stdin.buffer.read(32);pathlib.Path("
            + repr(str(marker))
            + ").touch()"
        )
        result = await dispatch.bounded_child(
            [sys.executable, "-c", source], b"x" * 32, timeout=0.02
        )
        assert result == {"outcome": "timeout_outcome_uncertain"}
        assert len(processes) == 1 and processes[0].returncode is not None
        assert not marker.exists()

    asyncio.run(exercise())


def test_cancellation_after_spawn_kills_and_collects_child(tmp_path, monkeypatch):
    async def exercise():
        original = asyncio.create_subprocess_exec
        processes = []

        async def track(*args, **kwargs):
            process = await original(*args, **kwargs)
            processes.append(process)
            return process

        monkeypatch.setattr(asyncio, "create_subprocess_exec", track)
        marker = tmp_path / "nonce-received"
        source = (
            "import sys,pathlib,time;sys.stdin.buffer.read(32);pathlib.Path("
            + repr(str(marker))
            + ").touch();time.sleep(60)"
        )
        task = asyncio.create_task(
            dispatch.bounded_child([sys.executable, "-c", source], b"x" * 32, timeout=3)
        )
        async with asyncio.timeout(2):
            while not marker.exists():
                await asyncio.sleep(0.01)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert len(processes) == 1 and processes[0].returncode is not None

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "source",
    [
        "import sys;sys.stdout.write('x'*8193)",
        "import sys;sys.stdout.write('entirely-invented-secret')",
        'import sys;sys.stdout.write(\'{"worker_status":"observed","extra":42}\')',
    ],
)
def test_child_protocol_failures_suppressed(source):
    result = asyncio.run(
        dispatch.bounded_child([sys.executable, "-c", source], b"x" * 32, timeout=3)
    )
    assert result == {"outcome": "invalid_child_protocol"}


def test_cancellation_persists_consumption(tmp_path):
    async def exercise():
        entered = asyncio.Event()

        async def runner(*args, **kwargs):
            entered.set()
            await asyncio.Event().wait()

        task = asyncio.create_task(
            dispatch.execute_offline("valid", tmp_path / "cancelled", runner=runner)
        )
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(exercise())
    result = json.loads((tmp_path / "cancelled/result-v3.json").read_bytes())
    assert result["outcome"] == "cancelled_outcome_uncertain"


def test_result_persistence_failure_does_not_make_reservation_reusable(tmp_path, monkeypatch):
    async def runner(*args, **kwargs):
        return {"outcome": "child_failed_outcome_uncertain"}

    def fail_result(*args):
        raise OSError(INVENTED_SECRET)

    monkeypatch.setattr(dispatch, "create", fail_result)
    folder = tmp_path / "failed-result"
    with pytest.raises(OSError):
        asyncio.run(dispatch.execute_offline("valid", folder, runner=runner))
    with pytest.raises(FileExistsError):
        asyncio.run(dispatch.execute_offline("valid", folder, runner=runner))

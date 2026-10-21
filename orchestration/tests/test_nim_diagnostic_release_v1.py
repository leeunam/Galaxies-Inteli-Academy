"""Real PID/PPID, old nonce guard and compiled graph; only fake responses."""

import asyncio
import json
import os
from pathlib import Path

import pytest
from langgraph.graph.state import CompiledStateGraph

from galaxies_orchestration import nim_diagnostic_release_contract_v1 as c
from galaxies_orchestration import nim_diagnostic_release_v1 as attempt
from galaxies_orchestration.nim_graph_contract_v1 import fixture


@pytest.fixture
def root_python():
    value = os.environ.get("GALAXIES_ROOT_PYTHON")
    if not value:
        pytest.skip("Explicit existing root interpreter required")
    return Path(value)


def test_release_preserves_inert_authorization_and_payload():
    from galaxies_orchestration import nim_diagnostic_attempt_contract_v1 as inert
    from galaxies_orchestration.nim_graph_contract_v1 import digest, payload_bytes

    assert inert.AUTHORIZATION_ID is None
    assert inert.verify_plan()["configuration_sha256"] == (
        "67f24c51aa23a306b215dfc78bfbd2b279a1edce0edebf67294dc066c649bff6"
    )
    assert c.AUTHORIZATION_ID == "Sentinel_c3cbbc19ae7c81919fc1361a0256d307"
    config = c.configuration()
    assert config["maximum_graph_work_seconds"] == 43
    assert config["maximum_cleanup_seconds"] == 2
    assert config["maximum_cleanup_drain_seconds"] == 1
    assert config["maximum_cleanup_wait_seconds"] == 1
    assert len(payload_bytes()) == 8576
    assert digest(payload_bytes()) == c.prior.PAYLOAD_SHA256


def test_missing_review_stops_before_reservation_or_spawn(root_python, tmp_path, monkeypatch):
    monkeypatch.setattr(c, "REVIEW", tmp_path / "invented-review.json")

    def forbidden(*args, **kwargs):
        raise AssertionError("unreviewed_release_must_not_have_effects")

    monkeypatch.setattr(c, "reserve", forbidden)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", forbidden)
    with pytest.raises(FileNotFoundError):
        asyncio.run(attempt.execute_remote(root_python))
    assert not list(tmp_path.iterdir())


def fake_review(plan):
    return {
        "protocol": c.PROTOCOL,
        "decision": "approved_for_one_synthetic_attempt",
        "plan_sha256": c.PLAN_SHA256,
        "configuration_sha256": plan["configuration_sha256"],
        "specific_remote_authorization_id": c.AUTHORIZATION_ID,
        "financial_evidence_id": c.prior.FINANCIAL_ID,
        "reviewer_thread_id": c.prior.SUPERVISOR,
        "execution_root_sha256": c.digest(str(c.ROOT.resolve()).encode()),
        "source_message_id": "ENTIRELY_INVENTED_REVIEW",
    }


@pytest.mark.parametrize(
    "field",
    [
        "protocol",
        "plan_sha256",
        "configuration_sha256",
        "specific_remote_authorization_id",
        "financial_evidence_id",
        "execution_root_sha256",
        "source_message_id",
    ],
)
def test_review_mismatch_stops_before_reservation_or_spawn(
    root_python, tmp_path, monkeypatch, field
):
    path = tmp_path / "invented-review.json"
    monkeypatch.setattr(c, "REVIEW", path)
    review = fake_review(c.verify_plan())
    review[field] = "invalid value with spaces" if field == "source_message_id" else "INVENTED"
    path.write_bytes(c.canonical(review))

    def forbidden(*args, **kwargs):
        raise AssertionError("mismatched_review_must_not_have_effects")

    monkeypatch.setattr(c, "reserve", forbidden)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", forbidden)
    with pytest.raises(ValueError, match="technical_review_required"):
        asyncio.run(attempt.execute_remote(root_python))
    assert list(tmp_path.iterdir()) == [path]


def test_invented_review_binds_checkout_and_rejects_symlink_ancestor(tmp_path, monkeypatch):
    target = tmp_path / "invented-review-directory"
    target.mkdir()
    path = target / "invented-review.json"
    monkeypatch.setattr(c, "REVIEW", path)
    path.write_bytes(c.canonical(fake_review(c.verify_plan())))
    assert c.check_review(c.verify_plan()) == c.digest(path.read_bytes())
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    monkeypatch.setattr(c, "REVIEW", link / path.name)
    with pytest.raises(ValueError, match="symlink_forbidden"):
        c.check_review(c.verify_plan())


@pytest.mark.parametrize(
    "case,code",
    [
        ("valid", "accepted"),
        ("wrong_hash", "packet_hash_mismatch"),
        ("too_many_ids", "schema_constraint"),
        ("duplicate_ids", "duplicate_evidence_id"),
        ("scalar_ids", "schema_invalid_type"),
        ("extra_field", "schema_extra_field"),
        ("deep_json", "json_depth_limit"),
        ("http_error", "http_error"),
        ("invalid_wire", "envelope_json_syntax"),
        ("send_failure", "diagnostic_failed"),
    ],
)
def test_bound_fake_attempt_is_once_with_exact_diagnostic(
    root_python, tmp_path, monkeypatch, case, code
):
    original = attempt.build_graph

    def build(worker, selector):
        graph = original(worker, selector)
        assert isinstance(graph, CompiledStateGraph)
        assert [name for name, _ in graph.get_subgraphs()] == ["explain"]
        return graph

    monkeypatch.setattr(attempt, "build_graph", build)
    folder = tmp_path / "invented-attempt"
    receipt = asyncio.run(attempt.simulate(root_python, case, folder))
    assert receipt["outcome"] == "observed"
    assert receipt["worker_cleanup_confirmed"] is True
    assert receipt["worker_cleanup_code"] == "confirmed"
    result = receipt["result"]
    assert result["selection_diagnostic"]["code"] == code
    assert result["legacy_result"]["analysis"] == fixture()["data"]["report"]
    assert result["current_provider"]["real_provider_verified"] is False
    assert result["legacy_result"]["orchestration"]["native_feature_handoff"] is False
    assert receipt["real_http_requests"] == 0
    assert result["current_provider"]["selector_invocations"] == 1
    if case == "send_failure":
        assert result["current_provider"]["transport"]["code"] == "request_failed_outcome_uncertain"
        assert result["selection_diagnostic"]["authority_status"] == "not_invoked"
        assert result["legacy_result"]["explanation"]["reason_code"] == "transport_failed"
    assert json.loads((folder / "reservation-v3.json").read_bytes())["parent_pid"] == os.getpid()
    assert (folder / "dispatch-v3.json").exists()  # original authorize() accepted real PPID
    assert all((path.stat().st_mode & 0o777) == 0o600 for path in folder.iterdir())
    assert (folder.stat().st_mode & 0o777) == 0o700
    with pytest.raises(FileExistsError):
        asyncio.run(attempt.simulate(root_python, "valid", folder))


def test_protected_namespace_and_symlink_never_reserved(root_python, tmp_path):
    for folder in (
        c.LEDGER,
        c.REVIEW.parent,
        c.prior.LEDGER,
        c.prior.REVIEW.parent,
        c.historical.LEDGER,
        c.historical.REVIEW.parent,
        tmp_path / "foreign-checkout/data/private/issue-5-nim-graph-diagnostic-release-v1",
        tmp_path / "foreign-checkout/data/private/issue-5-nim-typed-request-v1-review",
    ):
        with pytest.raises(ValueError):
            asyncio.run(attempt.simulate(root_python, "valid", folder / "invented-child"))
    target = tmp_path / "target"
    target.mkdir()
    link = tmp_path / "link"
    link.symlink_to(target, target_is_directory=True)
    with pytest.raises(ValueError):
        asyncio.run(attempt.simulate(root_python, "valid", link / "invented-child"))
    assert not list(target.iterdir())


@pytest.mark.parametrize("cancel", [False, True])
def test_deadline_or_cancel_reaps_only_worker_and_consumes(
    root_python, tmp_path, monkeypatch, cancel
):
    original = asyncio.create_subprocess_exec
    processes = []
    folder = tmp_path / "blocked"

    async def spawn(*args, **kwargs):
        process = await original(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)

    async def scenario():
        task = asyncio.create_task(
            attempt.simulate(root_python, "hang", folder, timeout=45 if cancel else 1.5)
        )
        if cancel:
            async with asyncio.timeout(5):
                while not (folder / "dispatch-v3.json").exists():
                    await asyncio.sleep(0.01)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        else:
            assert (await task)["outcome"] == "timeout_outcome_uncertain"

    asyncio.run(scenario())
    assert len(processes) == 1 and processes[0].returncode is not None
    assert not Path(f"/proc/{processes[0].pid}").exists()
    assert (folder / "diagnostic-release-result.json").exists()
    with pytest.raises(FileExistsError):
        asyncio.run(attempt.simulate(root_python, "valid", folder))


def test_cancelled_spawn_does_not_release_nonce(root_python, tmp_path, monkeypatch):
    original = asyncio.create_subprocess_exec
    processes = []
    folder = tmp_path / "spawn"

    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()

        async def spawn(*args, **kwargs):
            process = await original(*args, **kwargs)
            processes.append(process)
            entered.set()
            await release.wait()
            return process

        monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
        task = asyncio.create_task(attempt.simulate(root_python, "valid", folder))
        await asyncio.wait_for(entered.wait(), 5)
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(scenario())
    assert len(processes) == 1 and processes[0].returncode is not None
    assert not (folder / "dispatch-v3.json").exists()


@pytest.mark.parametrize("tamper", ["pid", "nonce", "mode"])
def test_original_authorize_rejects_tampered_fake_reservation(
    root_python, tmp_path, monkeypatch, tamper
):
    original = c.reserve
    folder = tmp_path / "invented-tamper"

    def reserve(path, *, offline):
        assert offline is True
        result, nonce = original(path, offline=offline)
        reservation = result / "reservation-v3.json"
        value = json.loads(reservation.read_bytes())
        if tamper == "pid":
            value["parent_pid"] = os.getpid() + 1000000
        elif tamper == "nonce":
            value["nonce_sha256"] = "0" * 64
        else:
            value["offline_simulation_only"] = False
        reservation.write_bytes(c.canonical(value))
        return result, nonce

    monkeypatch.setattr(c, "reserve", reserve)
    receipt = asyncio.run(attempt.simulate(root_python, "valid", folder))
    assert receipt["outcome"] == "failed_outcome_uncertain"
    assert receipt["real_http_requests"] == 0
    assert not (folder / "dispatch-v3.json").exists()


@pytest.mark.parametrize("phase", ["drain", "wait"])
def test_cleanup_timeout_drops_proof_and_keeps_nonce_consumed(
    root_python, tmp_path, monkeypatch, phase
):
    original = attempt.ReleasedProbeWorker

    class NeverCompletes(original):
        async def _cleanup(self):
            async def never(*args):
                await asyncio.Future()

            if phase == "drain":
                monkeypatch.setattr(self.process.stdout, "read", never)
            else:
                process = self.process

                class UnknownExit:
                    @property
                    def returncode(self):
                        return None

                    def __getattr__(self, name):
                        return getattr(process, name)

                self.process = UnknownExit()
            await super()._cleanup()

    monkeypatch.setattr(attempt, "ReleasedProbeWorker", NeverCompletes)
    folder = tmp_path / "invented-cleanup-failure"
    receipt = asyncio.run(attempt.simulate(root_python, "valid", folder, timeout=5))
    assert receipt["outcome"] == "failed_outcome_uncertain"
    assert receipt["result"] is None
    assert receipt["worker_cleanup_confirmed"] is False
    assert receipt["worker_cleanup_code"] == phase + "_unconfirmed"
    assert receipt["real_http_requests"] == 0
    assert (folder / "dispatch-v3.json").exists()
    with pytest.raises(FileExistsError):
        asyncio.run(attempt.simulate(root_python, "valid", folder))


def test_work_and_cleanup_share_one_total_deadline():
    plan = c.verify_plan()
    bound = c.binding(plan, None, "INVENTED", 100.0, 45, offline=True, owner_pid=os.getpid())
    assert bound["work_deadline_monotonic"] == 143.0
    assert bound["deadline_monotonic"] == 145.0
    assert bound["cleanup_drain_timeout_seconds"] == 1.0
    assert bound["cleanup_wait_timeout_seconds"] == 1.0


def test_fractional_binding_uses_same_representable_interval(tmp_path):
    plan = c.verify_plan()
    folder = tmp_path / "invented-fractional-binding"
    folder.mkdir(mode=0o700)
    bound = c.binding(plan, None, "INVENTED", 100000.123, 0.2, offline=True, owner_pid=os.getpid())
    c.create(folder / "diagnostic-release-binding.json", bound)
    assert (
        c.check_binding(folder, plan, None, "INVENTED", offline=True, owner_pid=os.getpid())
        == bound
    )
    interval = bound["deadline_monotonic"] - bound["started_monotonic"]
    assert bound["cleanup_drain_timeout_seconds"] == c.cleanup_budget(interval) / 2

"""Invented metadata and callbacks only; no auth, capsule or model on real paths."""

import json
from pathlib import Path

import pytest

from tests.positive_diagnostic_fake_owner import PRIVATE_OWNER, invented_operator


@pytest.fixture(params=["v2", "v3"])
def operator(tmp_path, monkeypatch, request):
    script = Path(__file__).parents[1] / f"scripts/front1_positive_diagnostic_{request.param}.py"
    with invented_operator(script, tmp_path, monkeypatch) as module:
        yield module


def save(module, name, value):
    module.write_new(module.FOLDER / name, value)


def test_missing_authority_refuses_before_any_native_launch(operator, monkeypatch):
    plan = {"invented": True}
    plan["plan_sha256"] = operator.digest(plan)
    save(operator, "plan.json", plan)
    monkeypatch.setattr(
        operator.owner, "owned_run", lambda *_a, **_k: pytest.fail("launched without authority")
    )
    with pytest.raises(FileNotFoundError):
        operator.operator()
    assert not (operator.FOLDER / "started.json").exists()


def fake_authority_files(operator, monkeypatch):
    """Invented authorities exist exclusively in pytest's disposable folder."""
    image = operator.FOLDER / "invented.png"
    image.write_bytes(b"invented metadata, not model input")
    operator.MODULE.write_text("invented offline operator")
    plan = {
        "prepared_epoch": 1,
        "proposal_sha256": "a" * 64,
        "calls_max": 1,
        "run_seconds_max": 120,
        "call_seconds_max": 80,
        "cases": [{"path": str(image), "png_sha256": operator.sha(image)}],
        "source_sha256": {},
        "predecessor_sha256": {},
        "asset_references": {},
        "asset_fingerprints": {},
        "positive_sheet_path": str(image),
        "positive_sheet_sha256": operator.sha(image),
        "consumed_authorization_ids": ["invented-old-consumed"],
    }
    plan["plan_sha256"] = operator.digest(plan)
    if hasattr(operator, "EXECUTION_ENVELOPE"):
        plan["external_tool_requests"] = [{"invented": "not an executable request"}]
        plan["execution_envelope"] = operator.EXECUTION_ENVELOPE
        plan["capsule_argv"] = ["invented-bwrap-no-dispatch"]
        monkeypatch.setattr(operator, "capsule", lambda: plan["capsule_argv"])
        plan["plan_sha256"] = operator.digest({k: v for k, v in plan.items() if k != "plan_sha256"})
    save(operator, "plan.json", plan)
    message = "Invented test fixture; never approval of any real operation."
    grant = {
        "decision": f"authorize_exact_old_prompt_positive_{operator.NAMESPACE[-2:]}_once",
        "plan_sha256": plan["plan_sha256"],
        "proposal_sha256": plan["proposal_sha256"],
        "calls_max": 1,
        "retry_allowed": False,
        "cost_brl_max": 0,
        "renewed_png_sha256": operator.sha(image),
        "issued_epoch": 2,
        "expires_epoch": 200,
        "human_message": message,
        "human_message_sha256": operator.hashlib.sha256(message.encode()).hexdigest(),
        "authorization_id": "invented-new-only",
    }
    if hasattr(operator, "EXECUTION_ENVELOPE"):
        grant["execution_envelope"] = operator.EXECUTION_ENVELOPE
    save(operator, "authorization.json", grant)
    review = {
        "decision": (
            f"reviewed_exact_old_prompt_positive_{operator.NAMESPACE[-2:]}"
            "_operator_and_authorization"
        ),
        "plan_sha256": plan["plan_sha256"],
        "authorization_file_sha256": operator.sha(operator.FOLDER / "authorization.json"),
        "operator_sha256": operator.sha(operator.MODULE),
        "human_origin_independently_checked": True,
        "source_message_id": "invented-distinct-review",
    }
    if hasattr(operator, "EXECUTION_ENVELOPE"):
        review["execution_envelope"] = operator.EXECUTION_ENVELOPE
    save(operator, "review.json", review)
    slot = {
        "decision": "exclusive_visual_cpu4_slot",
        "source_thread_id": "01a1467e-5da5-7a41-8b43-bfa0da1917f8",
        "plan_sha256": plan["plan_sha256"],
        "expires_epoch": 200,
    }
    if hasattr(operator, "EXECUTION_ENVELOPE"):
        slot["execution_envelope"] = operator.EXECUTION_ENVELOPE
    save(operator, "resource-slot.json", slot)
    monkeypatch.setattr(operator.time, "time", lambda: 100)
    if hasattr(operator, "EXECUTION_ENVELOPE"):
        operator.reserve_external_attempt()
    return grant


@pytest.mark.parametrize(
    "change",
    [
        {"authorization_id": "invented-old-consumed"},
        {"issued_epoch": 0},
        {"calls_max": 3},
        {"renewed_png_sha256": "0" * 64},
        {"retry_allowed": True},
        {"expires_epoch": 50},
    ],
)
def test_consumed_wrong_scope_or_expired_authority_cannot_dispatch(operator, monkeypatch, change):
    grant = fake_authority_files(operator, monkeypatch)
    assert operator.verify()["calls_max"] == 1
    # Corrupt this invented receipt, retaining every real folder untouched.
    path = operator.FOLDER / "authorization.json"
    path.write_text(json.dumps(grant | change))
    with pytest.raises(ValueError):
        operator.verify()


def configure_fake_execution(operator, monkeypatch, *, ready=True):
    plan = {
        "launch_argv": ["invented-python", "-B", "invented-worker"],
        "global_deadline_epoch": operator.time.time() + 600,
        "authorization_id": "invented-callback-only",
        "authorization_file_sha256": "b" * 64,
        "resource_slot_file_sha256": "c" * 64,
        "plan_sha256": "a" * 64,
    }
    monkeypatch.setattr(operator, "verify", lambda: plan)
    monkeypatch.setattr(operator, "actual_argv", lambda: plan["launch_argv"])
    monkeypatch.setattr(operator, "capsule", list)
    monkeypatch.setattr(operator.native, "available_memory", lambda: 7 * 1024**3)
    monkeypatch.setattr(operator.capture.owner, "workers", list)
    monkeypatch.setattr(
        operator.owner.supervisor, "proc_identity", lambda _: {"pid": 999, "start_ticks": 1}
    )
    if ready:
        operator.reserve_preflight(plan)
        save(
            operator,
            "preflight.json",
            {
                "code": "completed",
                "returncode": 0,
                "cleanup_confirmed": True,
                "preflight_reservation_sha256": operator.sha(
                    operator.FOLDER / "preflight-reservation.json"
                ),
            },
        )
    return plan


@pytest.mark.parametrize(
    "accepted,value,status",
    [
        (True, True, "supported_true_diagnostic_only"),
        (False, False, "false_negative_diagnostic_only"),
        (False, "unknown", "abstention_diagnostic_only"),
        (False, True, "unsupported_true_diagnostic_only"),
    ],
)
def test_one_terminal_outcome_seals_without_retry_or_quality(
    operator, monkeypatch, accepted, value, status
):
    configure_fake_execution(operator, monkeypatch)
    calls = []

    def invented(argv, **kwargs):
        calls.append(argv)
        assert argv[-2:] == ["--call", "1"] and kwargs["seconds"] == 80
        save(
            operator,
            "receipt-0001.json",
            {
                "accepted": accepted,
                "value": value,
                "technical_success": True,
                "cleanup_confirmed": True,
            },
        )
        return {
            "code": "completed",
            "returncode": 0 if accepted else 2,
            "cleanup_confirmed": True,
            "seconds": 0.01,
        }

    monkeypatch.setattr(operator.owner, "owned_run", invented)
    assert operator.operator() == (0 if accepted else 2)
    terminal = operator.read_json(operator.FOLDER / "terminal.json")
    assert terminal["status"] == status
    assert terminal["calls_reserved"] == 1 and terminal["pending"] is None
    assert not terminal["audit_released"] and not terminal["B_C_released"]
    with pytest.raises(ValueError, match="already_consumed"):
        operator.operator()
    assert len(calls) == 1


def test_uncertain_owned_failure_remains_consumed_and_pending(operator, monkeypatch):
    configure_fake_execution(operator, monkeypatch)
    monkeypatch.setattr(
        operator.owner,
        "owned_run",
        lambda *_a, **_k: {"code": "timeout", "cleanup_confirmed": False, "seconds": 80},
    )
    with pytest.raises(ValueError, match="owned_call_failed"):
        operator.operator()
    terminal = operator.read_json(operator.FOLDER / "terminal.json")
    assert terminal["pending"] == 1 and terminal["calls_reserved"] == 1
    assert terminal["status"] == "technical_or_uncertain_failure"
    assert not terminal["retry_allowed"]


def test_insufficient_memory_refuses_before_reserving(operator, monkeypatch):
    configure_fake_execution(operator, monkeypatch)
    monkeypatch.setattr(operator.native, "available_memory", lambda: 5 * 1024**3)
    monkeypatch.setattr(
        operator.owner, "owned_run", lambda *_a, **_k: pytest.fail("memory gate bypassed")
    )
    with pytest.raises(ValueError, match="memory_or_other_worker"):
        operator.operator()
    assert not (operator.FOLDER / "started.json").exists()


def test_preflight_clock_cannot_reset_the_global_budget(operator, monkeypatch):
    configure_fake_execution(operator, monkeypatch)
    later = operator.time.time() + 50
    monkeypatch.setattr(operator.time, "time", lambda: later)
    monkeypatch.setattr(
        operator.owner, "owned_run", lambda *_a, **_k: pytest.fail("expired budget dispatched")
    )
    with pytest.raises(ValueError, match="insufficient_global_budget"):
        operator.operator()
    assert not (operator.FOLDER / "started.json").exists()


def test_repeated_preflight_refuses_before_starting_a_child(operator, monkeypatch):
    configure_fake_execution(operator, monkeypatch)
    plan = operator.verify()
    monkeypatch.setattr(operator, "actual_argv", lambda: plan["launch_argv"] + ["--preflight-only"])
    monkeypatch.setattr(
        operator.owner, "owned_run", lambda *_a, **_k: pytest.fail("repeated preflight")
    )
    with pytest.raises(ValueError, match="preflight_already_attempted"):
        operator.operator(True)


def test_nested_capture_namespace_stays_in_the_owned_directory(operator, tmp_path):
    import os

    root = tmp_path / "capture-root"
    expected = root / "data/private" / operator.NAMESPACE / "captures/call-0001"
    expected.parent.parent.mkdir(parents=True, mode=0o700)
    fd = operator.capture._folder(root, 1, create=True)
    os.close(fd)
    assert expected.is_dir()
    assert not (root / "data/private/issue-4-visual-validation-run-v1").exists()


def test_crash_after_durable_preflight_reservation_cannot_reenter(operator, monkeypatch):
    plan = configure_fake_execution(operator, monkeypatch, ready=False)
    monkeypatch.setattr(operator, "actual_argv", lambda: plan["launch_argv"] + ["--preflight-only"])
    calls = []

    def crash(*_args, **_kwargs):
        calls.append(True)
        assert (operator.FOLDER / "preflight-reservation.json").is_file()
        raise RuntimeError("invented_crash_after_reservation")

    monkeypatch.setattr(operator.owner, "owned_run", crash)
    with pytest.raises(RuntimeError, match="invented_crash"):
        operator.operator(True)
    before = (operator.FOLDER / "preflight-reservation.json").read_bytes()
    assert not (operator.FOLDER / "preflight.json").exists()
    with pytest.raises(FileExistsError):
        operator.operator(True)
    assert (operator.FOLDER / "preflight-reservation.json").read_bytes() == before
    assert calls == [True]


def test_concurrent_preflight_reservations_allow_exactly_one_winner(operator, monkeypatch):
    import threading
    from concurrent.futures import ThreadPoolExecutor

    plan = configure_fake_execution(operator, monkeypatch, ready=False)
    barrier = threading.Barrier(2)

    def reserve():
        barrier.wait(timeout=3)
        try:
            operator.reserve_preflight(plan)
            return "reserved"
        except FileExistsError:
            return "consumed"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: reserve(), range(2)))
    assert sorted(results) == ["consumed", "reserved"]
    assert (
        operator.read_json(operator.FOLDER / "preflight-reservation.json")[
            "preflight_attempts_reserved"
        ]
        == 1
    )
    assert not (operator.FOLDER / "preflight.json").exists()


def test_namespace_failure_seals_preflight_without_reserving_a_model(operator, monkeypatch):
    plan = configure_fake_execution(operator, monkeypatch, ready=False)
    monkeypatch.setattr(operator, "actual_argv", lambda: plan["launch_argv"] + ["--preflight-only"])
    calls = []

    def rejected(*_args, **kwargs):
        calls.append(True)
        assert kwargs["seconds"] == 8
        return {
            "code": "child_failed",
            "returncode": 1,
            "cleanup_confirmed": True,
            "seconds": 0.002,
            "stderr": "invented namespace rejection",
            "stdout": "",
        }

    monkeypatch.setattr(operator.owner, "owned_run", rejected)
    with pytest.raises(ValueError, match="no_model_preflight_failed"):
        operator.operator(True)
    proof = operator.read_json(operator.FOLDER / "preflight.json")
    assert proof["code"] == "child_failed" and proof["cleanup_confirmed"]
    assert (
        operator.read_json(operator.FOLDER / "preflight-reservation.json")["model_calls_reserved"]
        == 0
    )
    assert not (operator.FOLDER / "ledger.json").exists()
    with pytest.raises(ValueError, match="preflight_already_attempted"):
        operator.operator(True)
    assert len(calls) == 1


def test_old_prompt_and_ordered_schema_are_bound_to_fixed_argv(operator, tmp_path):
    query = operator.product.specification("state_first")
    scratch = tmp_path / "scratch"
    row = {"path": str(tmp_path / "invented.png")}
    argv = [
        "invented-not-a-model",
        "--image",
        row["path"],
        "--prompt",
        query["prompt"],
        "--json-schema-file",
        str(scratch / "schema.json"),
    ]
    plan = {
        "runtime_template": argv,
        "effective_model_argv": argv,
        "prompt_sha256": operator.hashlib.sha256(query["prompt"].encode()).hexdigest(),
        "schema_sha256": operator.product.ordered_schema_hash(query["schema"]),
    }
    actual, command = operator.configuration(plan, row, scratch)
    assert command == argv and actual == query
    scratch.mkdir(mode=0o700)
    operator.batch.write_runtime_schema(scratch / "schema.json", actual["schema"])
    assert (
        operator.product.ordered_schema_hash(json.loads((scratch / "schema.json").read_bytes()))
        == plan["schema_sha256"]
    )
    plan["effective_model_argv"] = [*argv, "--invented-override"]
    with pytest.raises(ValueError, match="fixed_model_argv"):
        operator.configuration(plan, row, scratch)


def test_private_owner_source_is_never_read_even_when_it_exists(operator):
    import _io
    import builtins
    import io
    import os
    from functools import partial

    assert operator.owner.fixture_origin == "invented_no_private_source"
    assert operator.fixture_intercepted_owner_imports == [str(PRIVATE_OWNER)]
    assert operator.fixture_private_reads == []

    def via_reader(reader):
        with reader(PRIVATE_OWNER, "rb") as stream:
            stream.read(1)

    for read in (
        lambda: PRIVATE_OWNER.read_bytes(),
        partial(via_reader, builtins.open),
        partial(via_reader, io.open),
        lambda: _io.open_code(str(PRIVATE_OWNER)),
        lambda: os.open(PRIVATE_OWNER, os.O_RDONLY),
    ):
        with pytest.raises(AssertionError, match="private_owner_read_forbidden"):
            read()
    assert operator.fixture_private_reads == [str(PRIVATE_OWNER)] * 5


@pytest.mark.parametrize(
    "name", ["plan.json", "authorization.json", "review.json", "resource-slot.json"]
)
def test_v3_requires_explicit_envelope_from_all_parties(operator, monkeypatch, name):
    if not hasattr(operator, "EXECUTION_ENVELOPE"):
        pytest.skip("v3-only external envelope contract")
    fake_authority_files(operator, monkeypatch)
    assert operator.verify()["calls_max"] == 1
    path = operator.FOLDER / name
    value = operator.read_json(path)
    value["execution_envelope"] = dict(
        operator.EXECUTION_ENVELOPE, sandbox_permissions="use_default"
    )
    if name == "plan.json":
        # Preserve valid plan digest while changing the envelope on all parties.
        value["plan_sha256"] = operator.digest(
            {k: v for k, v in value.items() if k != "plan_sha256"}
        )
        for other in ("authorization.json", "review.json", "resource-slot.json"):
            target = operator.FOLDER / other
            body = operator.read_json(target)
            body["plan_sha256"] = value["plan_sha256"]
            target.write_text(json.dumps(body))
    path.write_text(json.dumps(value))
    # Keep unrelated byte bindings current so the envelope gate is exercised.
    review_path = operator.FOLDER / "review.json"
    review = operator.read_json(review_path)
    review["authorization_file_sha256"] = operator.sha(operator.FOLDER / "authorization.json")
    review_path.write_text(json.dumps(review))
    with pytest.raises(ValueError, match="exact_external_envelope_authority_required"):
        operator.verify()


def test_v3_rejects_changed_inner_capsule(operator, monkeypatch):
    if not hasattr(operator, "EXECUTION_ENVELOPE"):
        pytest.skip("v3-only capsule pin")
    fake_authority_files(operator, monkeypatch)
    monkeypatch.setattr(operator, "capsule", lambda: ["invented-without-network-isolation"])
    with pytest.raises(ValueError, match="reviewed_inner_capsule_changed"):
        operator.verify()


def test_v3_memory_gate_precedes_preflight_reservation(operator, monkeypatch):
    if not hasattr(operator, "EXECUTION_ENVELOPE"):
        pytest.skip("v3-only preflight admission")
    plan = configure_fake_execution(operator, monkeypatch, ready=False)
    monkeypatch.setattr(operator, "actual_argv", lambda: plan["launch_argv"] + ["--preflight-only"])
    monkeypatch.setattr(operator.native, "available_memory", lambda: 5 * 1024**3)
    with pytest.raises(ValueError, match="memory_or_other_worker"):
        operator.operator(True)
    assert not (operator.FOLDER / "preflight-reservation.json").exists()


def test_v3_tool_denial_cannot_reuse_external_attempt(operator, monkeypatch):
    if not hasattr(operator, "EXECUTION_ENVELOPE"):
        pytest.skip("v3-only external reservation")
    fake_authority_files(operator, monkeypatch)
    before = (operator.FOLDER / "external-attempt.json").read_bytes()
    assert not (operator.FOLDER / "preflight-reservation.json").exists()
    with pytest.raises(FileExistsError):
        operator.reserve_external_attempt()
    assert (operator.FOLDER / "external-attempt.json").read_bytes() == before
    assert operator.verify()["calls_max"] == 1


def test_failed_preflight_cannot_dispatch_a_model(operator, monkeypatch):
    plan = configure_fake_execution(operator, monkeypatch, ready=False)
    operator.reserve_preflight(plan)
    save(
        operator,
        "preflight.json",
        {"code": "child_failed", "returncode": 1, "cleanup_confirmed": True},
    )
    with pytest.raises(ValueError, match="no_model_preflight_required"):
        operator.operator()
    assert not (operator.FOLDER / "ledger.json").exists()

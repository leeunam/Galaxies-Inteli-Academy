"""Invented metadata and callbacks only; no auth, capsule or model on real paths."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest


@pytest.fixture
def operator(tmp_path, monkeypatch):
    from scripts import visual_validation_batch_v1 as batch
    from scripts import visual_validation_capture_v1 as capture

    before = batch.NAMESPACE, capture.NAMESPACE, list(sys.path)
    spec = importlib.util.spec_from_file_location(
        "invented_one_cell_operator",
        Path(__file__).parents[1] / "scripts/front1_positive_diagnostic.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    folder = tmp_path / "invented-only"
    folder.mkdir(mode=0o700)
    monkeypatch.setattr(module, "FOLDER", folder)
    monkeypatch.setattr(module, "MODULE", folder / "control_worker.py")
    monkeypatch.setattr(module, "ROOT", tmp_path)
    yield module
    batch.NAMESPACE, capture.NAMESPACE = before[:2]
    sys.path[:] = before[2]


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
    save(operator, "plan.json", plan)
    message = "Invented test fixture; never approval of any real operation."
    grant = {
        "decision": "authorize_exact_old_prompt_positive_once",
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
    save(operator, "authorization.json", grant)
    review = {
        "decision": "reviewed_exact_old_prompt_positive_operator_and_authorization",
        "plan_sha256": plan["plan_sha256"],
        "authorization_file_sha256": operator.sha(operator.FOLDER / "authorization.json"),
        "operator_sha256": operator.sha(operator.MODULE),
        "human_origin_independently_checked": True,
        "source_message_id": "invented-distinct-review",
    }
    save(operator, "review.json", review)
    slot = {
        "decision": "exclusive_visual_cpu4_slot",
        "source_thread_id": "01a1467e-5da5-7a41-8b43-bfa0da1917f8",
        "plan_sha256": plan["plan_sha256"],
        "expires_epoch": 200,
    }
    save(operator, "resource-slot.json", slot)
    monkeypatch.setattr(operator.time, "time", lambda: 100)
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


def configure_fake_execution(operator, monkeypatch):
    plan = {
        "launch_argv": ["invented-python", "-B", "invented-worker"],
        "global_deadline_epoch": operator.time.time() + 600,
        "authorization_id": "invented-callback-only",
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
    save(
        operator,
        "preflight.json",
        {
            "code": "completed",
            "returncode": 0,
            "cleanup_confirmed": True,
            "preflight_started_epoch": operator.time.time(),
        },
    )


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
    path = operator.FOLDER / "preflight.json"
    proof = operator.read_json(path)
    path.write_text(json.dumps(proof | {"preflight_started_epoch": operator.time.time() - 50}))
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

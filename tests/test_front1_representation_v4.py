"""Invented panel/authorities/owners only; no private inputs, model or capsule."""

import json
from pathlib import Path

import pytest

from scripts import front1_representation_v4 as panel
from tests.positive_diagnostic_fake_owner import invented_operator


def rows():
    return [
        {
            "alias": f"invented-{i}",
            "call_id": i,
            "kind": "positive" if (i == 1 or i >= 14) else "negative",
            "expected_value": (i == 1 or i >= 14),
            "expected_tokens": 1056,
            "seconds": 0.2,
            "source_frame": 1,
            "admissible_categories": ["garment"],
            "admissible_configurations": ["isolated_physical_item"],
            "control_recipe": {"sample_id": "white", "text": False},
            "png_sha256": "a" * 64,
        }
        for i in range(1, 18)
    ]


def receipt(index, *, value=None, configuration="isolated_physical_item"):
    if value is None:
        value = rows()[index - 1]["expected_value"]
    parsed = {
        "value": value,
        "native": {"presented_categories": ["garment"], "item_configuration": configuration},
    }
    return {
        "call_id": index,
        "value": value,
        "native": parsed["native"],
        "technical_success": True,
        "cleanup_confirmed": True,
        "accepted": panel.accepted_case(rows()[index - 1], parsed, True),
    }


@pytest.fixture
def operator(tmp_path, monkeypatch):
    script = Path(__file__).parents[1] / "scripts/front1_representation_operator_v4.py"
    with invented_operator(script, tmp_path, monkeypatch) as module:
        yield module


def save(op, name, body):
    op.write_new(op.FOLDER / name, body)


def execution(op, monkeypatch, *, ready=True):
    monkeypatch.setattr(op.time, "time", lambda: 100)
    plan = {
        "launch_argv": ["invented-python", "-B", "invented-operator"],
        "global_deadline_epoch": 1800,
        "authorization_id": "invented-not-human-approval",
        "authorization_file_sha256": "b" * 64,
        "resource_slot_file_sha256": "c" * 64,
        "plan_sha256": "d" * 64,
        "cases": rows(),
    }
    monkeypatch.setattr(op, "verify", lambda **_: plan)
    monkeypatch.setattr(op, "actual_argv", lambda: plan["launch_argv"])
    monkeypatch.setattr(op, "capsule", list)
    monkeypatch.setattr(op.native, "available_memory", lambda: 7 * 1024**3)
    monkeypatch.setattr(op.capture.owner, "workers", list)
    monkeypatch.setattr(
        op.owner.supervisor, "proc_identity", lambda _: {"pid": 999, "start_ticks": 1}
    )
    if ready:
        op.reserve_preflight(plan)
        save(
            op,
            "preflight.json",
            {
                "code": "completed",
                "returncode": 0,
                "cleanup_confirmed": True,
                "preflight_reservation_sha256": op.sha(op.FOLDER / "preflight-reservation.json"),
            },
        )
    return plan


def callbacks(
    op, monkeypatch, *, stop_at=None, value="unknown", owned_change=None, advance_clock=False
):
    calls = []

    def owned(argv, **kwargs):
        index = int(argv[-1])
        assert argv[-2] == "--call" and kwargs["seconds"] == 80
        assert (op.FOLDER / f"call-reservation-{index:04d}.json").is_file()
        calls.append(index)
        item = receipt(index, value=value if index == stop_at else None)
        save(op, f"receipt-{index:04d}.json", item)
        if advance_clock:
            monkeypatch.setattr(op.time, "time", lambda: 1550)
        return {
            "code": "completed",
            "returncode": 0,
            "cleanup_confirmed": True,
            "seconds": 0.01,
            "stdout": json.dumps(item),
        } | (owned_change or {})

    monkeypatch.setattr(op.owner, "owned_run", owned)
    return calls


def test_full_panel_requires_all_seventeen_and_never_grants_quality(operator, monkeypatch):
    execution(operator, monkeypatch)
    calls = callbacks(operator, monkeypatch)
    assert operator.operator() == 0
    final = operator.read_json(operator.FOLDER / "terminal.json")
    assert final["status"] == "development_panel_passed_only"
    assert final["calls_reserved"] == final["completed_receipts"] == 17
    assert (
        not final["quality_release"] and not final["audit_released"] and not final["B_C_released"]
    )
    with pytest.raises(ValueError, match="already_consumed"):
        operator.operator()
    assert calls == list(range(1, 18))


@pytest.mark.parametrize(
    "stop_at,value,status",
    [
        (1, "unknown", "perceptual_abstention"),
        (1, False, "perceptual_rejection"),
        (6, True, "perceptual_rejection"),
        (6, "unknown", "perceptual_abstention"),
    ],
)
def test_first_perceptual_failure_seals_without_further_call(
    operator, monkeypatch, stop_at, value, status
):
    execution(operator, monkeypatch)
    calls = callbacks(operator, monkeypatch, stop_at=stop_at, value=value)
    assert operator.operator() == 2
    final = operator.read_json(operator.FOLDER / "terminal.json")
    assert final["calls_reserved"] == stop_at and final["pending"] is None
    assert final["status"] == status and not final["retry_allowed"]
    assert calls == list(range(1, stop_at + 1))


def test_cleanup_uncertain_owner_keeps_pending_even_with_clean_native_receipt(
    operator, monkeypatch
):
    execution(operator, monkeypatch)
    calls = callbacks(
        operator, monkeypatch, owned_change={"code": "timeout", "cleanup_confirmed": False}
    )
    with pytest.raises(ValueError, match="owned_call_failed"):
        operator.operator()
    final = operator.read_json(operator.FOLDER / "terminal.json")
    assert final["pending"] == 1 and final["status"] == "technical_or_uncertain_failure"
    assert calls == [1]


def test_global_deadline_cannot_restart_between_cases(operator, monkeypatch):
    execution(operator, monkeypatch)
    calls = callbacks(operator, monkeypatch, advance_clock=True)
    assert operator.operator() == 2
    final = operator.read_json(operator.FOLDER / "terminal.json")
    assert calls == [1] and final["status"] == "global_budget_exhausted"


def test_preflight_failure_consumes_once_without_model(operator, monkeypatch):
    plan = execution(operator, monkeypatch, ready=False)
    monkeypatch.setattr(operator, "actual_argv", lambda: plan["launch_argv"] + ["--preflight-only"])
    calls = []

    def rejected(*_args, **kwargs):
        calls.append(kwargs["seconds"])
        assert (operator.FOLDER / "preflight-reservation.json").is_file()
        return {"code": "child_failed", "returncode": 1, "cleanup_confirmed": True}

    monkeypatch.setattr(operator.owner, "owned_run", rejected)
    with pytest.raises(ValueError, match="no_model_preflight_failed"):
        operator.operator(True)
    with pytest.raises(ValueError, match="preflight_already_attempted"):
        operator.operator(True)
    assert calls == [8] and not (operator.FOLDER / "ledger.json").exists()


def test_low_memory_blocks_preflight_before_reservation(operator, monkeypatch):
    plan = execution(operator, monkeypatch, ready=False)
    monkeypatch.setattr(operator, "actual_argv", lambda: plan["launch_argv"] + ["--preflight-only"])
    monkeypatch.setattr(operator.native, "available_memory", lambda: 5 * 1024**3)
    with pytest.raises(ValueError, match="memory_or_other_worker"):
        operator.operator(True)
    assert not (operator.FOLDER / "preflight-reservation.json").exists()


def test_partial_accepted_prefix_is_incomplete_not_a_gate_pass():
    result = panel.panel_outcome(rows(), [receipt(1)])
    assert result["status"] == "accepted_prefix_incomplete"
    assert not result["development_panel_passed"] and result["unexecuted_cases"] == 16


def test_no_receipt_after_a_rejected_case_can_be_counted():
    with pytest.raises(ValueError, match="no_dispatch_after_first_failure"):
        panel.panel_outcome(rows(), [receipt(1, value="unknown"), receipt(2)])


def test_boolean_alone_does_not_accept_unsupported_witness():
    item = receipt(1, value=True, configuration="isolated_graphic_item")
    assert not item["accepted"]
    assert panel.classify_case(rows()[0], item) == "perceptual_rejection"


def test_invented_pixels_roundtrip_without_writing_media(tmp_path):
    import io

    from PIL import Image

    target = tmp_path / "invented-sheet.png"
    Image.new("RGB", (1280, 360), "blue").save(target)
    raw = io.BytesIO()
    Image.new("RGB", (320, 330), "blue").save(raw, format="PNG")
    row = {
        "kind": "positive",
        "sheet_path": str(target),
        "sheet_sha256": panel.sha_bytes(target.read_bytes()),
        "source_frame": 1,
        "png_sha256": panel.sha_bytes(raw.getvalue()),
    }
    assert panel.input_bytes(row) == raw.getvalue()
    row["png_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="frozen_input_bytes_changed"):
        panel.input_bytes(row)
    assert list(tmp_path.iterdir()) == [target]


def test_missing_new_authority_refuses_before_any_child(operator):
    plan = {"invented": True}
    plan["plan_sha256"] = operator.digest(plan)
    save(operator, "plan.json", plan)
    with pytest.raises(FileNotFoundError):
        operator.operator()
    assert not (operator.FOLDER / "started.json").exists()


def authority(op, monkeypatch, *, reserve=True):
    """Invented fixtures in disposable pytest storage, never real approval."""
    op.MODULE.write_text("invented offline operator fixture")
    plan = {
        "prepared_epoch": 1,
        "proposal_sha256": "e" * 64,
        "calls_max": 17,
        "run_seconds_max": 1500,
        "call_seconds_max": 80,
        "cases": rows(),
        "panel_sha256": op.digest(rows()),
        "source_sha256": {},
        "predecessor_sha256": {},
        "asset_references": {},
        "asset_fingerprints": {},
        "protected_sheet_sha256": {},
        "consumed_authorization_ids": ["invented-consumed"],
        "execution_envelope": op.EXECUTION_ENVELOPE,
        "external_tool_requests": [{"invented": "not executable"}],
        "capsule_argv": ["invented-capsule-not-executable"],
    }
    plan["plan_sha256"] = op.digest(plan)
    save(op, "plan.json", plan)
    message = "Invented test fixture, not authorization for any real operation."
    grant = {
        "decision": "authorize_exact_representation_v4_panel_once",
        "plan_sha256": plan["plan_sha256"],
        "proposal_sha256": plan["proposal_sha256"],
        "calls_max": 17,
        "retry_allowed": False,
        "cost_brl_max": 0,
        "renewed_panel_sha256": plan["panel_sha256"],
        "issued_epoch": 2,
        "expires_epoch": 1800,
        "human_message": message,
        "human_message_sha256": op.hashlib.sha256(message.encode()).hexdigest(),
        "authorization_id": "invented-fresh",
        "execution_envelope": op.EXECUTION_ENVELOPE,
    }
    save(op, "authorization.json", grant)
    review = {
        "decision": "reviewed_exact_representation_v4_operator_and_authorization",
        "plan_sha256": plan["plan_sha256"],
        "authorization_file_sha256": op.sha(op.FOLDER / "authorization.json"),
        "operator_sha256": op.sha(op.MODULE),
        "human_origin_independently_checked": True,
        "source_message_id": "invented-independent",
        "execution_envelope": op.EXECUTION_ENVELOPE,
    }
    save(op, "review.json", review)
    save(
        op,
        "resource-slot.json",
        {
            "decision": "exclusive_visual_cpu4_slot",
            "source_thread_id": "01a1467e-5da5-7a41-8b43-bfa0da1917f8",
            "plan_sha256": plan["plan_sha256"],
            "expires_epoch": 1800,
            "execution_envelope": op.EXECUTION_ENVELOPE,
        },
    )
    monkeypatch.setattr(op.time, "time", lambda: 100)
    monkeypatch.setattr(op, "capsule", lambda: plan["capsule_argv"])
    if reserve:
        op.reserve_external_attempt()
    assert op.verify(external_attempt=reserve)["calls_max"] == 17
    return grant


@pytest.mark.parametrize(
    "change",
    [
        {"authorization_id": "invented-consumed"},
        {"calls_max": 1},
        {"renewed_panel_sha256": "0" * 64},
        {"issued_epoch": 0},
        {"expires_epoch": 50},
        {"retry_allowed": True},
        {"execution_envelope": {"sandbox_permissions": "use_default"}},
    ],
)
def test_fresh_exact_panel_authority_is_required(operator, monkeypatch, change):
    grant = authority(operator, monkeypatch)
    (operator.FOLDER / "authorization.json").write_text(json.dumps(grant | change))
    review_path = operator.FOLDER / "review.json"
    review = operator.read_json(review_path)
    review["authorization_file_sha256"] = operator.sha(operator.FOLDER / "authorization.json")
    review_path.write_text(json.dumps(review))
    with pytest.raises(ValueError):
        operator.verify()


def test_external_tool_rejection_cannot_reuse_attempt(operator, monkeypatch):
    authority(operator, monkeypatch)
    before = (operator.FOLDER / "external-attempt.json").read_bytes()
    with pytest.raises(FileExistsError):
        operator.reserve_external_attempt()
    assert (operator.FOLDER / "external-attempt.json").read_bytes() == before
    assert operator.read_json(operator.FOLDER / "external-attempt.json")["model_calls_max"] == 17


def test_preflight_crash_keeps_one_durable_reservation(operator, monkeypatch):
    plan = execution(operator, monkeypatch, ready=False)
    monkeypatch.setattr(operator, "actual_argv", lambda: plan["launch_argv"] + ["--preflight-only"])
    calls = []

    def crash(*_args, **_kwargs):
        calls.append(True)
        raise RuntimeError("invented preflight crash")

    monkeypatch.setattr(operator.owner, "owned_run", crash)
    with pytest.raises(RuntimeError):
        operator.operator(True)
    with pytest.raises(FileExistsError):
        operator.operator(True)
    assert calls == [True]


def test_configuration_cannot_silently_reuse_native225(operator, tmp_path):
    query = operator.product.specification("state_first")
    scratch = tmp_path / "scratch"
    row = {"call_id": 1, "path": str(scratch / "input.png")}
    argv = [
        "invented-model-not-executable",
        "--image-min-tokens",
        "1024",
        "--image-max-tokens",
        "1024",
        "--image",
        row["path"],
        "--prompt",
        query["prompt"],
        "--json-schema-file",
        str(scratch / "schema.json"),
    ]
    plan = {
        "runtime_template": argv,
        "effective_model_argvs": [argv],
        "prompt_sha256": operator.hashlib.sha256(query["prompt"].encode()).hexdigest(),
        "schema_sha256": operator.product.ordered_schema_hash(query["schema"]),
    }
    assert operator.configuration(plan, row, scratch)[1] == argv
    argv[argv.index("--image-min-tokens") + 1] = "225"
    with pytest.raises(ValueError, match="fixed_spatial_budget"):
        operator.configuration(plan, row, scratch)


def test_private_owner_is_replaced_before_import(operator):
    assert operator.owner.fixture_origin == "invented_no_private_source"
    assert operator.fixture_private_reads == []


def test_authority_window_must_cover_new_global_budget_before_external_attempt(
    operator, monkeypatch
):
    authority(operator, monkeypatch, reserve=False)
    monkeypatch.setattr(operator.time, "time", lambda: 400)
    with pytest.raises(ValueError, match="full_panel_authority_window_required"):
        operator.reserve_external_attempt()
    assert not (operator.FOLDER / "external-attempt.json").exists()


def test_panel_counts_actual_classes_even_with_sentinel_first():
    result = panel.panel_outcome(rows(), [receipt(i) for i in range(1, 18)])
    assert result["positive_accepted"] == 5 and result["negative_accepted"] == 12
    assert result["development_panel_passed"] and not result["quality_release"]

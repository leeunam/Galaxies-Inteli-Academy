"""Invented pixels/raws only: no native generation, tokenization, cohort or network."""

import copy
import hashlib
import json
import socket
import time
from contextlib import contextmanager

import pytest
from PIL import Image

from scripts import vlm_positive_order_plan as planning
from scripts import vlm_positive_order_run as runner
from scripts import vlm_product_v16 as core
from scripts.private_checkpoint import digest, file_hash
from scripts.vlm_product_v16 import save


@pytest.fixture
def campaign(tmp_path, monkeypatch):
    def denied(*a, **kw):
        raise AssertionError("network_forbidden")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)
    work = tmp_path / "data/private/fixtures"
    work.mkdir(parents=True)
    positives = []
    for i in range(5):
        sheet = work / f"positive-{i}.png"
        Image.new("RGB", (1280, 360), "white").save(sheet)
        cell = work / "crop.png"
        with Image.open(sheet) as image:
            image.crop((0, 25, 320, 355)).save(cell)
        positives.append(
            {
                "kind": "positive",
                "sample_id": f"invented-{i}",
                "source_sample_id": f"invented-video-{i // 2}",
                "source_frame": i % 3 + 1,
                "seconds": [0.2, 1.5, 2.8][i % 3],
                "png_sha256": file_hash(cell),
                "sheet_path": str(sheet.relative_to(tmp_path)),
                "sheet_sha256": file_hash(sheet),
                "expected_value": True,
                "admissible_categories": ["garment"],
                "admissible_configurations": ["hand_holds_hanger_out", "isolated_physical_item"],
            }
        )
    protected = {str(p.relative_to(tmp_path)): file_hash(p) for p in work.glob("*.png")}
    base = {
        "cases": {"positive": positives},
        "ancestor_folders": [],
        "protected_sha256": protected,
        "prior_calls": 1835,
        "prior_acquisitions": 256,
        "prior_seconds": 37568.24201608001,
        "old_unused_calls_closed": 10,
        "new_separate_budget_not_old_balance": True,
    }

    def load_base(*a):
        if any(file_hash(tmp_path / n) != h for n, h in protected.items()):
            raise ValueError("protected_changed")
        return copy.deepcopy(base)

    config = {
        "invented_fixture_only": True,
        "specifications": {v: core.specification(v) for v in core.VARIANTS},
    }
    monkeypatch.setattr(planning, "load_base", load_base)
    monkeypatch.setattr(planning, "configuration", lambda: copy.deepcopy(config))
    monkeypatch.setattr(runner, "configuration", lambda: copy.deepcopy(config))
    monkeypatch.setattr(planning, "no_workers", lambda root: None)
    monkeypatch.setattr(runner, "no_workers", lambda root: None)
    monkeypatch.setattr(runner, "verify_runtime", lambda: None)
    folder = tmp_path / planning.QUEUE
    plan = planning.prepare(None, None, folder, tmp_path)
    calls = []

    def invoke(paths, prompt, scratch, schema, **kwargs):
        state = json.loads((folder / "checkpoint.json").read_bytes())
        entry = state["operations"][-1]
        assert state["calls_reserved"] == len(calls) + 1
        assert entry["unmeasured_reserved_seconds"] > 0
        assert (folder / "reservations" / f"native-{state['calls_reserved']:04d}.json").exists()
        v = entry["variant"]
        spec = core.specification(v)
        assert prompt == spec["prompt"] and schema == spec["schema"] and kwargs["max_tokens"] == 64
        case = next(c for c in positives if c["sample_id"] == entry["sample_id"])
        assert file_hash(paths[0]) == case["png_sha256"]
        calls.append((v, "positive", entry["sample_id"]))
        return {"raw_response": response(v), "runtime_seconds": 0.0, "runtime_peak_rss_mib": 2.0}

    return tmp_path, folder, plan, invoke, calls


def response(variant, config="hand_holds_hanger_out", category="garment"):
    row = core.PROJECTION[config]
    native = {
        "item_configuration": config,
        "state": row["state"],
        "presented_categories": [category] if row["categories"] else [],
    }
    return json.dumps({k: native[k] for k in core.ORDER[variant]})


def grant(campaign, **changes):
    root, folder, plan, *_ = campaign
    state = planning.load(None, None, folder, root)[1]
    text = "invented fixture review, never a real release"
    body = {
        "plan_sha256": plan["plan_sha256"],
        "configuration_sha256": digest(plan["configuration"]),
        "reviewer_thread_id": "01a15713-2572-7544-8329-c229ea2ff0f5",
        "review_message_id": "invented-test-review",
        "decision": "released_for_this_plan_only",
        "message": text,
        "message_sha256": hashlib.sha256(text.encode()).hexdigest(),
    } | changes
    planning.submit_clearance(folder, plan, state, body)
    return body


def test_review_precedes_runtime_and_zero_dispatch(campaign, monkeypatch):
    root, folder, _, invoke, calls = campaign

    def forbidden(*a):
        raise AssertionError("runtime_before_review")

    monkeypatch.setattr(runner, "verify_runtime", forbidden)
    monkeypatch.setattr(runner, "no_workers", forbidden)
    with pytest.raises(ValueError, match="technical_review_required"):
        runner.execute(None, None, folder, root, invoker=invoke)
    state = planning.load(None, None, folder, root)[1]
    assert (
        state["calls_reserved"] == 0
        and not state["operations"]
        and not state["sealed"]
        and not calls
    )


def test_ten_paired_calls_never_approve_anything_and_reentry_is_inert(campaign):
    root, folder, plan, invoke, calls = campaign
    grant(campaign)
    report = runner.execute(None, None, folder, root, invoker=invoke)
    assert calls == planning.sequence(plan) and len(calls) == 10
    assert report["complete"] and report["paired"] == {
        "complete_pairs": 5,
        "required_pairs": 5,
        "state_first_gains": 0,
        "state_first_losses": 0,
    }
    assert all(s["correct_supported_true"] == 5 for s in report["condition_scores"].values())
    assert report["candidate_for_further_development"] == report["released_fields"] == []
    assert report["v16_still_failed"] and report["old_unused_calls_still_closed"] == 10
    assert report["cumulative_calls"] == 1845 and report["cumulative_acquisitions"] == 256
    assert all(
        report[k] is False
        for k in ("test_evaluated", "m1_replaced", "new_blind_audit", "predictive_training_started")
    )
    assert not any(p.is_file() for p in (root / "data/private/media-temp").rglob("*"))
    planning.load(None, None, folder, root)
    before = file_hash(folder / "checkpoint.json")
    with pytest.raises(ValueError, match="consumed_or_uncertain"):
        runner.execute(None, None, folder, root, invoker=invoke)
    assert file_hash(folder / "checkpoint.json") == before and len(calls) == 10


@pytest.mark.parametrize("mode", ["false", "unknown", "unsupported", "wrong_category"])
def test_perceptual_failures_finish_and_true_alone_is_not_support(campaign, mode):
    root, folder, _, invoke, calls = campaign
    grant(campaign)

    def faulty(*a, **kw):
        r = invoke(*a, **kw)
        v, _, sample = calls[-1]
        if v == "state_first" and sample == "invented-0":
            config = {
                "false": "absent",
                "unknown": "unclear",
                "unsupported": "hand_holds_item_out",
                "wrong_category": "isolated_physical_item",
            }[mode]
            r["raw_response"] = response(
                v, config, "cosmetic" if mode == "wrong_category" else "garment"
            )
        return r

    report = runner.execute(None, None, folder, root, invoker=faulty)
    assert len(calls) == 10 and report["complete"]
    assert report["condition_scores"]["state_first"]["correct_supported_true"] == 4
    assert report["paired"]["state_first_losses"] == 1
    assert report["condition_scores"]["state_first"]["true"] == (
        5 if mode in ("unsupported", "wrong_category") else 4
    )
    planning.load(None, None, folder, root)


@pytest.mark.parametrize(
    "mode", ["runtime", "json", "wrong_order", "cancel", "timeout", "rss", "duration"]
)
def test_operational_failure_partial_denominators_seal_once(campaign, mode):
    root, folder, _, invoke, calls = campaign
    grant(campaign)

    def faulty(*a, **kw):
        r = invoke(*a, **kw)
        if len(calls) == 3:
            if mode == "runtime":
                raise RuntimeError("invented")
            if mode == "cancel":
                raise KeyboardInterrupt("invented")
            if mode == "timeout":
                raise TimeoutError("invented")
            if mode == "rss":
                r["runtime_peak_rss_mib"] = 4000
            elif mode == "duration":
                r["runtime_seconds"] = 181
            else:
                r["raw_response"] = "invalid" if mode == "json" else response("item_first")
        return r

    with pytest.raises((RuntimeError, ValueError, KeyboardInterrupt, TimeoutError)):
        runner.execute(None, None, folder, root, invoker=faulty)
    _, state = planning.load(None, None, folder, root)
    report = json.loads((folder / "comparison.json").read_bytes())
    assert state["sealed"] and state["calls_reserved"] == len(calls) == 3
    if mode in ("rss", "duration"):
        raw_path = (
            planning.result_path(folder, state["operations"][-1]).parent / "calls/frame-1.json"
        )
        native = json.loads(raw_path.read_bytes())
        assert native["raw_response"] == response(calls[-1][0])
        assert (
            native["raw_response_sha256"]
            == hashlib.sha256(native["raw_response"].encode()).hexdigest()
        )
    assert not report["complete"] and report["paired"]["complete_pairs"] == 1
    assert sum(s["completed"] for s in report["condition_scores"].values()) == 2
    before = file_hash(folder / "checkpoint.json")
    with pytest.raises(ValueError, match="consumed_or_uncertain"):
        runner.execute(None, None, folder, root, invoker=faulty)
    assert file_hash(folder / "checkpoint.json") == before and len(calls) == 3


@pytest.mark.parametrize(
    "field",
    ["plan_sha256", "configuration_sha256", "reviewer_thread_id", "message_sha256", "decision"],
)
def test_review_is_bound_to_this_new_plan(campaign, field):
    root, folder, _, invoke, calls = campaign
    with pytest.raises(ValueError, match="binding_changed"):
        grant(campaign, **{field: "old-or-wrong"})
    assert not (folder / "technical-clearance.json").exists() and not calls
    with pytest.raises(ValueError, match="technical_review_required"):
        runner.execute(None, None, folder, root, invoker=invoke)


@pytest.mark.parametrize("check", ["no_workers", "verify_runtime"])
def test_startup_failure_after_review_is_terminal_without_reservation(campaign, monkeypatch, check):
    root, folder, _, invoke, calls = campaign
    grant(campaign)

    def fail(*a):
        raise RuntimeError("startup_failure")

    monkeypatch.setattr(runner, check, fail)
    with pytest.raises(RuntimeError, match="startup_failure"):
        runner.execute(None, None, folder, root, invoker=invoke)
    state = planning.load(None, None, folder, root)[1]
    assert state["sealed"] and state["calls_reserved"] == 0 and not calls
    with pytest.raises(ValueError, match="consumed_or_uncertain"):
        runner.execute(None, None, folder, root, invoker=invoke)


def test_budget_expires_before_reservation(campaign, monkeypatch):
    root, folder, plan, invoke, calls = campaign
    grant(campaign)
    clock = {"now": 0.0}

    def expire():
        clock["now"] = 396.0
        return copy.deepcopy(plan["configuration"])

    monkeypatch.setattr(runner, "configuration", expire)
    with pytest.raises(TimeoutError, match="session_budget_exhausted"):
        runner.execute(None, None, folder, root, invoker=invoke, clock=lambda: clock["now"])
    state = planning.load(None, None, folder, root)[1]
    assert (
        state["sealed"]
        and state["new_session_seconds"] == 396
        and state["calls_reserved"] == 0
        and not calls
    )


def test_timeout_after_durable_reservation_charges_180(campaign, monkeypatch):
    root, folder, _, invoke, calls = campaign
    grant(campaign)
    clock = {"now": 0.0}

    @contextmanager
    def measured(seconds):
        state = json.loads((folder / "checkpoint.json").read_bytes())
        if state["calls_reserved"]:
            assert seconds == state["operations"][-1]["unmeasured_reserved_seconds"] == 180
            assert (folder / "reservations/native-0001.json").exists()
        yield

    def timeout(*a, **kw):
        invoke(*a, **kw)
        clock["now"] = 180.0
        raise TimeoutError("after_reservation")

    monkeypatch.setattr(runner, "deadline", measured)
    with pytest.raises(TimeoutError, match="after_reservation"):
        runner.execute(None, None, folder, root, invoker=timeout, clock=lambda: clock["now"])
    state = planning.load(None, None, folder, root)[1]
    assert (
        state["calls_reserved"] == 1
        and state["new_session_seconds"] == 180
        and state["sealed"]
        and len(calls) == 1
    )


def test_uncertain_running_reservation_cannot_resume(campaign):
    root, folder, plan, invoke, calls = campaign
    grant(campaign)
    state = planning.load(None, None, folder, root)[1]
    v, kind, sample = planning.sequence(plan)[0]
    state.update(
        calls_reserved=1,
        new_session_seconds=180.0,
        elapsed_seconds=plan["base"]["prior_seconds"] + 180,
    )
    planning.exclusive(folder / "execution-started.json", planning.start_marker(plan, state))
    state["operations"] = [
        {
            "variant": v,
            "kind": kind,
            "sample_id": sample,
            "status": "running",
            "call_count": 1,
            "seconds": 180.0,
            "unmeasured_reserved_seconds": 180.0,
        }
    ]
    planning.exclusive(
        folder / "reservations/native-0001.json",
        {
            "plan_sha256": plan["plan_sha256"],
            "operation": 1,
            "variant": v,
            "kind": kind,
            "sample_id": sample,
            "frame": 1,
            "number": 1,
        },
    )
    save(folder / "checkpoint.json", state)
    before = file_hash(folder / "checkpoint.json")
    with pytest.raises(ValueError, match="consumed_or_uncertain"):
        runner.execute(None, None, folder, root, invoker=invoke)
    assert not calls and file_hash(folder / "checkpoint.json") == before


@pytest.mark.parametrize("completed_before_crash", [0, 1, 2])
def test_start_marker_prevents_second_execute_even_between_completed_calls(
    campaign, completed_before_crash
):
    root, folder, plan, invoke, calls = campaign
    grant(campaign)
    state = planning.load(None, None, folder, root)[1]
    started = time.monotonic()
    planning.exclusive(folder / "execution-started.json", planning.start_marker(plan, state))
    for i in range(completed_before_crash):
        runner.one(
            folder,
            plan,
            state,
            planning.sequence(plan)[i],
            root,
            invoker=invoke,
            session_started=started,
        )
    planning.load(None, None, folder, root)  # Read-only inspection remains available.
    before = file_hash(folder / "checkpoint.json")
    with pytest.raises(ValueError, match="consumed_or_uncertain"):
        runner.execute(None, None, folder, root, invoker=invoke)
    assert (
        len(calls) == int(completed_before_crash)
        and file_hash(folder / "checkpoint.json") == before
    )


def test_global_clock_charges_startup_and_between_operation_checks(campaign, monkeypatch):
    root, folder, _, invoke, calls = campaign
    grant(campaign)
    clock = {"now": 0.0}
    real_load = runner.load

    def expensive_check(*a):
        if (folder / "execution-started.json").exists():
            clock["now"] += 25
        return real_load(*a)

    def startup():
        clock["now"] += 120

    def measured(*a, **kw):
        r = invoke(*a, **kw)
        clock["now"] += 20
        return r

    monkeypatch.setattr(runner, "load", expensive_check)
    monkeypatch.setattr(runner, "verify_runtime", startup)
    with pytest.raises(TimeoutError, match="session_budget_exhausted"):
        runner.execute(None, None, folder, root, invoker=measured, clock=lambda: clock["now"])
    state = planning.load(None, None, folder, root)[1]
    assert len(calls) == state["calls_reserved"] == 6
    assert state["new_session_seconds"] == 415 and state["session_overhead_seconds"] == 295
    assert state["sealed"] and len(state["operations"]) == 6


def test_returned_raw_is_preserved_when_wall_limit_expires(campaign, monkeypatch):
    root, folder, _, invoke, calls = campaign
    grant(campaign)
    clock = {"now": 0.0}

    @contextmanager
    def cooperative_deadline(seconds):
        yield

    def late(*a, **kw):
        r = invoke(*a, **kw)
        clock["now"] += 181
        return r

    monkeypatch.setattr(runner, "deadline", cooperative_deadline)
    with pytest.raises(ValueError, match="resource_limit"):
        runner.execute(None, None, folder, root, invoker=late, clock=lambda: clock["now"])
    state = planning.load(None, None, folder, root)[1]
    call = json.loads(
        (
            planning.result_path(folder, state["operations"][0]).parent / "calls/frame-1.json"
        ).read_bytes()
    )
    assert state["sealed"] and state["calls_reserved"] == len(calls) == 1
    assert call["raw_response"] == response("item_first") and call["diagnostic_wall_seconds"] == 181


def test_sources_changed_during_reserve_seal_before_dispatch(campaign, monkeypatch):
    root, folder, _plan, invoke, calls = campaign
    grant(campaign)
    monkeypatch.setattr(runner, "configuration", lambda: {"changed": True})
    with pytest.raises(ValueError, match="sources_or_review_changed"):
        runner.execute(None, None, folder, root, invoker=invoke)
    assert not calls and planning.load(None, None, folder, root)[1]["sealed"]


@pytest.mark.parametrize(
    "tamper", ["counter", "acquisition", "images", "raw", "time", "order", "limits", "pixels"]
)
def test_tampering_refuses_next_dispatch(campaign, tamper):
    root, folder, plan, invoke, calls = campaign
    grant(campaign)
    state = planning.load(None, None, folder, root)[1]
    started = time.monotonic()
    planning.exclusive(folder / "execution-started.json", planning.start_marker(plan, state))
    runner.one(
        folder,
        plan,
        state,
        planning.sequence(plan)[0],
        root,
        invoker=invoke,
        session_started=started,
    )
    if tamper == "counter":
        state["calls_reserved"] = 0
    elif tamper == "acquisition":
        save(folder / "reservations/acquisition-0001.json", {})
    elif tamper == "images":
        (folder / "images").mkdir()
    elif tamper == "time":
        state["new_session_seconds"] = 0.0
    elif tamper == "order":
        state["operations"][0]["variant"] = "state_first"
    elif tamper == "pixels":
        (root / plan["base"]["cases"]["positive"][0]["sheet_path"]).write_bytes(b"changed")
    elif tamper == "raw":
        path = planning.result_path(folder, state["operations"][0]).parent / "calls/frame-1.json"
        body = json.loads(path.read_bytes())
        body["raw_response"] = "changed"
        save(path, body)
    else:
        body = json.loads((folder / "plan.json").read_bytes())
        body["limits"]["calls"] = 11
        body["plan_sha256"] = digest({k: v for k, v in body.items() if k != "plan_sha256"})
        save(folder / "plan.json", body)
    save(folder / "checkpoint.json", state)
    with pytest.raises((ValueError, FileNotFoundError)):
        runner.execute(None, None, folder, root, invoker=invoke)
    assert len(calls) == 1


def test_single_queue_and_no_repreparation_or_duplicate_review(campaign):
    root, folder, _, _, calls = campaign
    body = grant(campaign)
    state = planning.load(None, None, folder, root)[1]
    with pytest.raises(ValueError, match="already_consumed"):
        planning.submit_clearance(folder, planning.load(None, None, folder, root)[0], state, body)
    with pytest.raises(ValueError, match="already_prepared_or_consumed"):
        planning.prepare(None, None, folder, root)
    copied = folder.parent / "another-budget"
    with pytest.raises(ValueError, match="single_queue_required"):
        planning.prepare(None, None, copied, root)
    with pytest.raises(ValueError, match="single_queue_required"):
        planning.load(None, None, copied, root)
    assert not calls


@pytest.mark.parametrize(
    "claim", ["candidate", "counts", "pairs", "complete", "old_budget", "training"]
)
def test_report_cannot_invent_support_scope_or_approval_even_rehashed(campaign, claim):
    root, folder, _, invoke, _ = campaign
    grant(campaign)
    runner.execute(None, None, folder, root, invoker=invoke)
    path = folder / "comparison.json"
    report = json.loads(path.read_bytes())
    if claim == "candidate":
        report["candidate_for_further_development"] = ["state_first"]
    elif claim == "counts":
        report["condition_scores"]["state_first"]["correct_supported_true"] = 4
    elif claim == "pairs":
        report["paired"]["state_first_gains"] = 5
    elif claim == "complete":
        report["complete"] = False
    elif claim == "training":
        report["predictive_training_started"] = True
    else:
        report["old_unused_calls_still_closed"] = 0
    report["comparison_sha256"] = digest(
        {k: v for k, v in report.items() if k != "comparison_sha256"}
    )
    save(path, report)
    state = json.loads((folder / "checkpoint.json").read_bytes())
    state["comparison_file_sha256"] = file_hash(path)
    save(folder / "checkpoint.json", state)
    with pytest.raises(ValueError, match="terminal_claim_changed"):
        planning.load(None, None, folder, root)

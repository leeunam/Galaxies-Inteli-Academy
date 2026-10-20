"""Invented fixtures and stubbed model only; no network, private cohort or native generation."""

import copy
import hashlib
import json
import socket

import pytest
from PIL import Image

from scripts import vlm_product_v16 as core
from scripts import vlm_product_v16_plan as planning
from scripts import vlm_product_v16_run as runner
from scripts.private_checkpoint import digest, file_hash
from scripts.vlm_product_v16 import save
from scripts.vlm_prompt_development import render_control
from scripts.vlm_prompt_plan import controls


@pytest.fixture
def campaign(tmp_path, monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("network_forbidden")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)
    work = tmp_path / "data/private/fixtures"
    work.mkdir(parents=True)
    negatives = []
    positives = []
    for row in controls():
        cell = work / "control.png"
        render_control(row, cell)
        negatives.append(
            {
                "kind": "negative",
                "sample_id": row["sample_id"],
                "seconds": 0.0,
                "source_frame": 1,
                "png_sha256": file_hash(cell),
                "expected_value": False,
            }
        )
    for i in range(5):
        sheet = work / f"positive-{i}.png"
        Image.new("RGB", (1280, 360), "white").save(sheet)
        cell = work / "cropped.png"
        with Image.open(sheet) as im:
            im.crop((0, 25, 320, 355)).save(cell)
        positives.append(
            {
                "kind": "positive",
                "sample_id": f"positive-{i}",
                "source_sample_id": f"invented-{i // 2}",
                "source_frame": i % 3 + 1,
                "seconds": [0.2, 1.5, 2.8][i % 3],
                "png_sha256": file_hash(cell),
                "sheet_path": str(sheet.relative_to(tmp_path)),
                "sheet_sha256": file_hash(sheet),
                "expected_value": True,
                "admissible_categories": ["garment"],
                "admissible_configurations": ["hand_holds_hanger_out", "isolated_physical_item"],
                "frozen_inspection": {"invented": True},
            }
        )
    protected = {str(p.relative_to(tmp_path)): file_hash(p) for p in work.glob("*.png")}
    base = {
        "ancestor_folders": [],
        "cases": {"negative": negatives, "positive": positives},
        "protected_sha256": protected,
        "prior_calls": 1811,
        "prior_acquisitions": 256,
        "prior_seconds": 37044.30741882603,
    }

    def load_base(*args):
        if any(file_hash(tmp_path / n) != h for n, h in protected.items()):
            raise ValueError("protected_changed")
        return copy.deepcopy(base)

    config = {
        "fixture": "invented_no_native_gate_claim",
        "specifications": {v: core.specification(v) for v in core.VARIANTS},
    }
    monkeypatch.setattr(planning, "load_base", load_base)
    monkeypatch.setattr(planning, "configuration", lambda: copy.deepcopy(config))
    monkeypatch.setattr(runner, "configuration", lambda: copy.deepcopy(config))
    monkeypatch.setattr(planning, "no_workers", lambda root: None)
    monkeypatch.setattr(runner, "no_workers", lambda root: None)
    monkeypatch.setattr(runner, "verify_runtime", lambda: None)
    folder = tmp_path / "data/private/v16"
    plan = planning.prepare(None, None, folder, tmp_path)
    calls = []

    def invoke(paths, prompt, scratch, schema, **kwargs):
        state = json.loads((folder / "checkpoint.json").read_bytes())
        entry = state["operations"][-1]
        assert (
            state["calls_reserved"] == len(calls) + 1 and entry["unmeasured_reserved_seconds"] > 0
        )
        receipt = folder / "reservations" / f"native-{state['calls_reserved']:04d}.json"
        assert receipt.exists()
        variant = entry["variant"]
        spec = core.specification(variant)
        assert prompt == spec["prompt"] and schema == spec["schema"] and kwargs["max_tokens"] == 64
        assert (
            file_hash(paths[0])
            == planning.case_for(plan, entry["kind"], entry["sample_id"])["png_sha256"]
        )
        calls.append((variant, entry["kind"], entry["sample_id"]))
        return {
            "raw_response": response(
                variant, "hand_holds_hanger_out" if entry["kind"] == "positive" else "absent"
            )
        }

    return tmp_path, folder, plan, invoke, calls


def response(variant, config, category="garment"):
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
    text = "invented fixture-only technical review; never a real authorization"
    body = {
        "plan_sha256": plan["plan_sha256"],
        "configuration_sha256": digest(plan["configuration"]),
        "reviewer_thread_id": "01a15713-2572-7544-8329-c229ea2ff0f5",
        "review_message_id": "invented-fixture-review",
        "decision": "released_for_this_plan_only",
        "message": text,
        "message_sha256": hashlib.sha256(text.encode()).hexdigest(),
    } | changes
    planning.submit_clearance(folder, plan, state, body)
    return body


def test_technical_review_required_before_runtime_or_dispatch(campaign, monkeypatch):
    root, folder, _plan, invoke, calls = campaign

    def forbidden():
        raise AssertionError("runtime_should_not_be_checked_before_review")

    monkeypatch.setattr(runner, "verify_runtime", forbidden)
    with pytest.raises(ValueError, match="technical_review_required"):
        runner.execute(None, None, folder, root, invoker=invoke)
    assert not calls and not json.loads((folder / "checkpoint.json").read_bytes())["operations"]


def test_complete_34_calls_two_conditions_gates_and_sealed_guard(campaign):
    root, folder, plan, invoke, calls = campaign
    grant(campaign)
    report = runner.execute(None, None, folder, root, invoker=invoke)
    assert len(calls) == 34 and report["new_acquisitions_reserved"] == 0
    assert report["cumulative_calls"] == 1845 and report["cumulative_acquisitions"] == 256
    assert report["candidate_for_further_development"] == list(core.VARIANTS)
    assert report["paired"]["negative"] == {
        "same_crops": 12,
        "state_first_gains": 0,
        "state_first_losses": 0,
    }
    assert report["paired"]["positive"]["same_crops"] == 5 and report["released_fields"] == []
    assert all(
        report[k] is False
        for k in ("test_evaluated", "m1_replaced", "new_blind_audit", "predictive_training_started")
    )
    assert (
        calls[:24] == planning.sequence(plan)
        and calls[24:] == planning.sequence(plan, core.VARIANTS)[24:]
    )
    assert planning.load(None, None, folder, root)[1]["sealed"]
    before = file_hash(folder / "checkpoint.json")
    with pytest.raises(ValueError, match="consumed_or_uncertain"):
        runner.execute(None, None, folder, root, invoker=invoke)
    assert file_hash(folder / "checkpoint.json") == before and len(calls) == 34


@pytest.mark.parametrize("bad", [("item_first",), ("state_first",), core.VARIANTS])
def test_negative_blocks_finish_both_and_only_passing_condition_receives_5_positives(campaign, bad):
    root, folder, _plan, invoke, calls = campaign
    grant(campaign)

    def faulty(*args, **kwargs):
        r = invoke(*args, **kwargs)
        v, kind, sample = calls[-1]
        if kind == "negative" and sample == controls()[0]["sample_id"] and v in bad:
            r["raw_response"] = response(v, "unclear")
        return r

    report = runner.execute(None, None, folder, root, invoker=faulty)
    assert len([c for c in calls if c[1] == "negative"]) == 24
    assert len(calls) == 24 + 5 * (2 - len(bad))
    assert {c[0] for c in calls if c[1] == "positive"} == set(core.VARIANTS) - set(bad)
    assert report["candidate_for_further_development"] == [v for v in core.VARIANTS if v not in bad]
    planning.load(None, None, folder, root)


@pytest.mark.parametrize("mode", ["unsupported_configuration", "wrong_category", "unknown"])
def test_positive_value_alone_cannot_pass_frozen_support_and_block_finishes(campaign, mode):
    root, folder, _plan, invoke, calls = campaign
    grant(campaign)

    def faulty(*args, **kwargs):
        r = invoke(*args, **kwargs)
        v, kind, sample = calls[-1]
        if v == "item_first" and kind == "positive" and sample == "positive-0":
            r["raw_response"] = (
                response(v, "hand_holds_item_out")
                if mode == "unsupported_configuration"
                else response(v, "isolated_physical_item", "cosmetic")
                if mode == "wrong_category"
                else response(v, "unclear")
            )
        return r

    report = runner.execute(None, None, folder, root, invoker=faulty)
    assert len(calls) == 34 and report["condition_scores"]["item_first"]["positive"]["correct"] == 4
    assert report["candidate_for_further_development"] == ["state_first"]
    planning.load(None, None, folder, root)


@pytest.mark.parametrize("mode", ["runtime", "json", "unicode", "wrong_order"])
def test_operational_failure_stops_entire_round_and_never_retries(campaign, mode):
    root, folder, _plan, invoke, calls = campaign
    grant(campaign)

    def faulty(*args, **kwargs):
        r = invoke(*args, **kwargs)
        if len(calls) == 3:
            if mode == "runtime":
                raise RuntimeError("invented")
            v = calls[-1][0]
            r["raw_response"] = (
                "invalid"
                if mode == "json"
                else "\ud800"
                if mode == "unicode"
                else response(next(x for x in core.VARIANTS if x != v), "absent")
            )
        return r

    with pytest.raises((ValueError, RuntimeError, UnicodeError)):
        runner.execute(None, None, folder, root, invoker=faulty)
    _plan, state = planning.load(None, None, folder, root)
    assert len(calls) == state["calls_reserved"] == 3 and state["sealed"]
    with pytest.raises(ValueError, match="consumed_or_uncertain"):
        runner.execute(None, None, folder, root, invoker=faulty)
    assert len(calls) == 3


@pytest.mark.parametrize(
    "field",
    ["plan_sha256", "configuration_sha256", "reviewer_thread_id", "message_sha256", "decision"],
)
def test_wrong_clearance_cannot_publish_or_dispatch(campaign, field):
    root, folder, _plan, invoke, calls = campaign
    with pytest.raises(ValueError, match="technical_review_binding_changed"):
        grant(campaign, **{field: "wrong"})
    assert not (folder / "technical-clearance.json").exists()
    with pytest.raises(ValueError, match="technical_review_required"):
        runner.execute(None, None, folder, root, invoker=invoke)
    assert not calls


@pytest.mark.parametrize(
    "tamper",
    ["counter", "acquisition_reservation", "images", "limit", "sources", "receipt", "raw", "time"],
)
def test_tampering_rejected_before_next_dispatch(campaign, monkeypatch, tamper):
    root, folder, plan, invoke, calls = campaign
    grant(campaign)
    state = planning.load(None, None, folder, root)[1]
    runner.one(folder, plan, state, planning.sequence(plan)[0], root, invoker=invoke)
    if tamper == "counter":
        state["acquisitions_reserved"] = 1
    elif tamper == "acquisition_reservation":
        save(folder / "reservations/acquisition-0001.json", {})
    elif tamper == "images":
        (folder / "images").mkdir()
    elif tamper == "limit":
        body = json.loads((folder / "plan.json").read_bytes())
        body["limits"]["calls"] = 35
        body["plan_sha256"] = digest({k: v for k, v in body.items() if k != "plan_sha256"})
        save(folder / "plan.json", body)
    elif tamper == "sources":
        monkeypatch.setattr(planning, "configuration", lambda: {"changed": True})
    elif tamper == "receipt":
        (folder / "reservations/native-0001.json").unlink()
    elif tamper == "raw":
        path = planning.result_path(folder, state["operations"][0]).parent / "calls/frame-1.json"
        body = json.loads(path.read_bytes())
        body["raw_response"] = "changed"
        save(path, body)
    else:
        state["new_session_seconds"] = 0.0
    save(folder / "checkpoint.json", state)
    with pytest.raises((ValueError, FileNotFoundError)):
        runner.execute(None, None, folder, root, invoker=invoke)
    assert len(calls) == 1


def test_changed_positive_pixels_stop_before_any_positive_reservation(campaign):
    root, folder, plan, invoke, calls = campaign
    grant(campaign)

    def change(*args, **kwargs):
        r = invoke(*args, **kwargs)
        if len(calls) == 24:
            (root / plan["base"]["cases"]["positive"][0]["sheet_path"]).write_bytes(b"changed")
        return r

    with pytest.raises(ValueError, match="protected_changed"):
        runner.execute(None, None, folder, root, invoker=change)
    assert len(calls) == 24 and not any(c[1] == "positive" for c in calls)


def test_uncertain_running_entry_is_not_resumed(campaign):
    root, folder, plan, invoke, calls = campaign
    grant(campaign)
    state = planning.load(None, None, folder, root)[1]
    v, kind, sample = planning.sequence(plan)[0]
    state["operations"] = [
        {
            "variant": v,
            "kind": kind,
            "sample_id": sample,
            "status": "running",
            "call_count": 0,
            "seconds": 0.0,
        }
    ]
    save(folder / "checkpoint.json", state)
    with pytest.raises(ValueError, match="consumed_or_uncertain"):
        runner.execute(None, None, folder, root, invoker=invoke)
    assert not calls


def test_reservation_and_clearance_are_exclusive(campaign):
    root, folder, plan, invoke, calls = campaign
    body = grant(campaign)
    state = planning.load(None, None, folder, root)[1]
    with pytest.raises(ValueError, match="already_consumed"):
        planning.submit_clearance(folder, plan, state, body)
    runner.one(folder, plan, state, planning.sequence(plan)[0], root, invoker=invoke)
    with pytest.raises(FileExistsError):
        planning.exclusive(folder / "reservations/native-0001.json", {})
    assert len(calls) == 1


@pytest.mark.parametrize("claim", ["candidate", "scores", "scope", "sampling", "paired"])
def test_rehashed_report_cannot_invent_candidate_scores_or_scope(campaign, claim):
    root, folder, _plan, invoke, _calls = campaign
    grant(campaign)
    runner.execute(None, None, folder, root, invoker=invoke)
    path = folder / "comparison.json"
    report = json.loads(path.read_bytes())
    if claim == "candidate":
        report["candidate_for_further_development"] = []
    elif claim == "scores":
        report["condition_scores"]["item_first"]["negative"]["correct"] = 11
    elif claim == "paired":
        report["paired"]["negative"]["state_first_gains"] = 12
    elif claim == "scope":
        report["causal_scope"] = "historical_cause_proved"
    else:
        report["positive_sampling_unit"] = "five_independent_videos"
    report["comparison_sha256"] = digest(
        {k: v for k, v in report.items() if k != "comparison_sha256"}
    )
    save(path, report)
    state = json.loads((folder / "checkpoint.json").read_bytes())
    state["comparison_file_sha256"] = file_hash(path)
    save(folder / "checkpoint.json", state)
    with pytest.raises(ValueError, match="terminal_scientific_claim_changed"):
        planning.load(None, None, folder, root)


@pytest.mark.parametrize("check", ["no_workers", "verify_runtime"])
def test_post_clearance_startup_failure_seals_once_without_dispatch(campaign, monkeypatch, check):
    root, folder, _plan, invoke, calls = campaign
    grant(campaign)

    def fail(*args):
        raise RuntimeError("invented_startup_check_failure")

    monkeypatch.setattr(runner, check, fail)
    with pytest.raises(RuntimeError, match="startup_check_failure"):
        runner.execute(None, None, folder, root, invoker=invoke)
    _plan, state = planning.load(None, None, folder, root)
    assert state["sealed"] and state["halt_reason"] == "v16_execution_failed_RuntimeError"
    assert state["calls_reserved"] == state["acquisitions_reserved"] == 0 and not calls
    checkpoint = file_hash(folder / "checkpoint.json")
    with pytest.raises(ValueError, match="consumed_or_uncertain"):
        runner.execute(None, None, folder, root, invoker=invoke)
    assert file_hash(folder / "checkpoint.json") == checkpoint and not calls
    assert json.loads((folder / "comparison.json").read_bytes())["new_calls_reserved"] == 0


def test_session_exhaustion_before_reservation_seals_without_invocation(campaign, monkeypatch):
    root, folder, plan, invoke, calls = campaign
    grant(campaign)
    clock = {"now": 0.0}
    original = runner.one

    def timed(*args, **kwargs):
        return original(*args, **kwargs, clock=lambda: clock["now"])

    def expire():
        clock["now"] = 1196.0
        return copy.deepcopy(plan["configuration"])

    monkeypatch.setattr(runner, "one", timed)
    monkeypatch.setattr(runner, "configuration", expire)
    with pytest.raises(TimeoutError, match="session_budget_exhausted"):
        runner.execute(None, None, folder, root, invoker=invoke)
    _, state = planning.load(None, None, folder, root)
    assert state["sealed"] and state["calls_reserved"] == 0 and not calls
    assert state["new_session_seconds"] == 1196.0 and not list((folder / "reservations").glob("*"))
    assert (
        state["operations"][0]["status"] == "failed" and state["operations"][0]["call_count"] == 0
    )
    with pytest.raises(ValueError, match="consumed_or_uncertain"):
        runner.execute(None, None, folder, root, invoker=invoke)
    assert not calls


def test_timeout_after_durable_reservation_consumes_180_and_stops_both_conditions(
    campaign, monkeypatch
):
    from contextlib import contextmanager

    root, folder, _plan, invoke, calls = campaign
    grant(campaign)
    clock = {"now": 0.0}
    original = runner.one
    limits = []

    def timed(*args, **kwargs):
        return original(*args, **kwargs, clock=lambda: clock["now"])

    @contextmanager
    def measured_deadline(seconds):
        limits.append(seconds)
        state = json.loads((folder / "checkpoint.json").read_bytes())
        assert (
            state["calls_reserved"] == 1
            and state["operations"][-1]["unmeasured_reserved_seconds"] == 180.0
        )
        assert (folder / "reservations/native-0001.json").exists()
        yield

    def timeout(*args, **kwargs):
        invoke(*args, **kwargs)
        clock["now"] = 180.0
        raise TimeoutError("invented_after_reservation")

    monkeypatch.setattr(runner, "one", timed)
    monkeypatch.setattr(runner, "deadline", measured_deadline)
    with pytest.raises(TimeoutError, match="after_reservation"):
        runner.execute(None, None, folder, root, invoker=timeout)
    _, state = planning.load(None, None, folder, root)
    assert (
        state["sealed"] and state["calls_reserved"] == 1 and len(calls) == 1 and limits == [180.0]
    )
    assert (
        state["new_session_seconds"] == 180.0
        and state["operations"][0]["unmeasured_reserved_seconds"] == 0
    )
    assert len(list((folder / "reservations").glob("*.json"))) == 1
    checkpoint = file_hash(folder / "checkpoint.json")
    with pytest.raises(ValueError, match="consumed_or_uncertain"):
        runner.execute(None, None, folder, root, invoker=timeout)
    assert len(calls) == 1 and file_hash(folder / "checkpoint.json") == checkpoint


def test_superseded_queue_cannot_run_even_if_its_sources_are_old(campaign):
    root, folder, _plan, invoke, calls = campaign
    planning.exclusive(folder / "superseded-v2.json", {"replacement_queue": "invented-next"})
    with pytest.raises(ValueError, match="superseded_queue_no_dispatch"):
        runner.execute(None, None, folder, root, invoker=invoke)
    assert not calls


def test_replacement_allows_only_one_effective_queue(campaign, monkeypatch):
    root, folder, plan, _invoke, calls = campaign
    old_load = planning.load_base
    effective = "data/private/only-effective"
    monkeypatch.setattr(
        planning,
        "load_base",
        lambda *a: old_load(*a) | {"replacement": {"replacement_queue": effective}},
    )
    with pytest.raises(ValueError, match="single_effective_queue_required"):
        planning.prepare(None, None, folder.parent / "third-queue", root)
    new = planning.prepare(None, None, root / effective, root)
    assert (
        new["limits"]["calls"] == 34 and new["base"]["prior_calls"] == plan["base"]["prior_calls"]
    )
    assert not calls
    copied = folder.parent / "copied-effective-queue"
    copied.mkdir()
    for name in ("plan.json", "checkpoint.json"):
        (copied / name).write_bytes((root / effective / name).read_bytes())
    with pytest.raises(ValueError, match="single_effective_queue_required"):
        runner.execute(None, None, copied, root, invoker=_invoke)
    assert not calls

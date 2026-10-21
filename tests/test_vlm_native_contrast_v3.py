"""Invented bytes and real owned Python children only; no model or global patching."""

import hashlib
import itertools
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime

import pytest

from scripts import vlm_native_contrast_v3 as c


def logs(*, complete=True, tokens=1075):
    text = "encoding mtmd batch, n_chunks = 1 (done = 0, total = 1)\n"
    text += "mtmd batch encoding done in 1 ms\n"
    text += f"decoding image batch 1/1, n_tokens_batch = {tokens}\n"
    if complete:
        text += "image decoded (batch 1/1) in 1 ms\n"
    return text


def python_argv(answer="no", *, complete=True, tokens=1075, tail=""):
    code = "import os,signal,sys,time; "
    code += f"sys.stderr.write({logs(complete=complete, tokens=tokens)!r}); sys.stderr.flush(); "
    if answer is not None:
        raw = json.dumps({"answer": answer}) + "\n"
        code += f"sys.stdout.write({raw!r}); sys.stdout.flush(); "
    return [sys.executable, "-B", "-c", code + tail]


class PythonOnly:
    def __init__(self):
        self.children = []

    def __call__(self, argv, **kwargs):
        assert argv[:3] == [sys.executable, "-B", "-c"]
        process = subprocess.Popen(argv, **kwargs)
        self.children.append(process)
        return process

    def cleaned(self):
        assert self.children
        for child in self.children:
            assert child.returncode is not None and child.poll() is not None
            with pytest.raises(ProcessLookupError):
                os.killpg(child.pid, 0)


def capture(root, argv, *, seconds=75):
    calls, owner = [], PythonOnly()
    value = c.durable.capture(
        argv,
        root=root,
        cell=c.SEQUENCE[0],
        seconds=seconds,
        reserve=lambda: calls.append("reserved"),
        popen=owner,
    )
    assert calls == ["reserved"]
    owner.cleaned()
    return value


def test_v3_accepts_75_and_preserves_original_bytes_and_v2_ceiling(tmp_path):
    value = capture(tmp_path, python_argv())
    assert value["stop_code"] is None and value["answer"] == "no"
    inspected = c.durable.inspect(tmp_path, c.SEQUENCE[0])
    assert inspected["observation"] == value
    assert inspected["terminal"] and inspected["cleanup_confirmed"]
    raw = tmp_path / c.QUEUE / "captures" / c.SEQUENCE[0] / "stdout.bin"
    assert raw.read_bytes() == b'{"answer": "no"}\n'
    assert not (tmp_path / c.previous.QUEUE).exists()
    with pytest.raises(ValueError, match="deadline"):
        c.durable.frozen.capture(
            [],
            root=tmp_path,
            cell=c.SEQUENCE[1],
            seconds=75,
            reserve=lambda: pytest.fail("reserved"),
            popen=PythonOnly(),
        )
    assert not (tmp_path / c.previous.QUEUE).exists()


@pytest.mark.parametrize("seconds", [75.0001, 80, 0, -1, float("nan"), float("inf"), True])
def test_bad_deadline_refuses_before_files_or_reserve(tmp_path, seconds):
    with pytest.raises(ValueError, match="deadline"):
        c.durable.capture(
            [],
            root=tmp_path,
            cell=c.SEQUENCE[0],
            seconds=seconds,
            reserve=lambda: pytest.fail("reserved"),
            popen=PythonOnly(),
        )
    assert list(tmp_path.iterdir()) == []


def test_default_launcher_is_absent(tmp_path):
    with pytest.raises(ValueError, match="release_required"):
        c.durable.capture(
            [],
            root=tmp_path,
            cell=c.SEQUENCE[0],
            seconds=75,
            reserve=lambda: pytest.fail("reserved"),
        )
    assert list(tmp_path.iterdir()) == []


def test_no_reentry_even_after_clean_completion(tmp_path):
    capture(tmp_path, python_argv())
    with pytest.raises(FileExistsError):
        c.durable.capture(
            python_argv(),
            root=tmp_path,
            cell=c.SEQUENCE[0],
            seconds=75,
            reserve=lambda: pytest.fail("second reservation"),
            popen=PythonOnly(),
        )


def test_symlink_cannot_route_capture_into_older_namespace(tmp_path):
    old = tmp_path / c.previous.QUEUE
    old.mkdir(parents=True, mode=0o700)
    (tmp_path / c.QUEUE).symlink_to(old, target_is_directory=True)
    with pytest.raises(OSError):
        c.durable.capture(
            [],
            root=tmp_path,
            cell=c.SEQUENCE[0],
            seconds=75,
            reserve=lambda: pytest.fail("reserved"),
            popen=PythonOnly(),
        )
    assert list(old.iterdir()) == []


def test_timeout_keeps_prefix_inconclusive_and_reaps_child(tmp_path):
    value = capture(
        tmp_path, python_argv(None, complete=False, tail="time.sleep(30)"), seconds=0.15
    )
    assert value["stop_code"] == "native_timeout" and value["answer"] is None
    assert c.durable.inspect(tmp_path, c.SEQUENCE[0])["observation"] == value
    diagnosis = c.phase_diagnostic.diagnose(value)
    assert diagnosis["last_observed_phase"] == "image_decode"
    assert diagnosis["generation_limit_explains_timeout"] is False
    assert diagnosis["image_tokens_total_confirmed"] is None


def test_sigterm_uses_same_owner_and_restores_handler(tmp_path):
    handler = signal.getsignal(signal.SIGTERM)
    value = capture(
        tmp_path,
        python_argv(
            None, complete=False, tail="os.kill(os.getppid(), signal.SIGTERM); time.sleep(30)"
        ),
    )
    assert value["stop_code"] == "native_cancelled"
    assert value["cleanup_confirmed"] and value["answer"] is None
    assert signal.getsignal(signal.SIGTERM) == handler


def test_output_limit_stays_16k_and_unparseable_prefix_is_not_success(tmp_path):
    value = capture(
        tmp_path, python_argv(None, tail="sys.stdout.write('x' * 20000); sys.stdout.flush()")
    )
    assert value["stop_code"] == "output_limit_or_unclosed_pipe"
    assert value["answer"] is None and value["cleanup_confirmed"]
    view = c.durable.inspect(tmp_path, c.SEQUENCE[0])
    assert view["durable_stdout_bytes"] == 16384


@pytest.mark.parametrize(
    "now,retention,expected", [(0, 999, (80, 75)), (320, 999, (340, 15)), (0, 12, (12, 7))]
)
def test_deadline_reserves_cleanup_and_clamps_global_and_retention(now, retention, expected):
    assert c.dispatch_deadline(0, now, retention) == expected


@pytest.mark.parametrize("now,retention", [(335, 999), (340, 999), (0, 5), (0, -1)])
def test_no_dispatch_without_cleanup_margin(now, retention):
    with pytest.raises(c.base.ProbeStop):
        c.dispatch_deadline(0, now, retention)


def test_all_81_answer_combinations_have_no_repeat_or_release():
    for values in itertools.product(("yes", "no", "uncertain"), repeat=4):
        result = c.decision(dict(zip(c.SEQUENCE, values, strict=True)))
        assert result["released_fields"] == [] and result["repeat_authorized"] is False
        assert result["previous_derived_false_positive_preserved"]
        assert result["independent_audit"] is False
        if "uncertain" in values:
            assert result["decision"] == "inconclusive_abstain"
        elif values == ("no", "no", "yes", "yes"):
            assert result["decision"] == "no_native_benefit_demonstrated"
        elif values[1:3] == ("no", "yes"):
            assert result["decision"] == "limited_revealed_pair_support"
        else:
            assert result["decision"] == "hypothesis_not_supported"


def test_partial_comparison_cannot_be_a_scientific_decision():
    with pytest.raises(ValueError):
        c.decision({"negative-D": "yes", "negative-N": "no"})


class Fixture:
    """Only the private loop seam uses invented provenance and Python processes."""

    def __init__(self, root, *, mode="success"):
        self.root, self.mode = root, mode
        self.folder = root / c.QUEUE
        (self.folder / "images").mkdir(parents=True, mode=0o700)
        self.folder.chmod(0o700)
        self.owner, self.names = PythonOnly(), []
        cells = []
        for name in c.SEQUENCE:
            raw = ("invented opaque image bytes:" + name).encode()
            (self.folder / "images" / (name + ".png")).write_bytes(raw)
            cells.append(
                {
                    "name": name,
                    "png_sha256": hashlib.sha256(raw).hexdigest(),
                    "expected_answer": "no" if name.startswith("negative") else "yes",
                }
            )
        config = {
            "cells": cells,
            "effective_argv_template": ["invented", "<PNG>", "<SCHEMA>"],
            "root_sha256": hashlib.sha256(str(root).encode()).hexdigest(),
        }
        self.plan = {"configuration": config, "configuration_sha256": c.base.digest(config)}
        self.plan["plan_sha256"] = c.base.digest(self.plan)
        c.base.write(self.folder / "checkpoint.json", dict(c.INITIAL))

    def launch(self, argv, deadline):
        name = self.plan["configuration"]["cells"][len(self.names)]["name"]
        self.names.append(name)
        answer = "yes" if name != "negative-N" else "no"
        script = python_argv(answer)
        if self.mode == "tokens":
            script = python_argv(answer, tokens=1024)
        elif self.mode == "timeout":
            script = python_argv(None, complete=False, tail="time.sleep(30)")
        elif self.mode == "cancel":
            script = python_argv(
                None, complete=False, tail="os.kill(os.getppid(), signal.SIGTERM); time.sleep(30)"
            )
        elif self.mode == "invalid_json":
            script = python_argv(None, tail="print('not-json')")

        def start(actual, **kwargs):
            assert actual == argv
            child = self.owner(script, **kwargs)
            if self.mode == "timeout":
                return c.previous._DeadlineProcess(child, time.monotonic() + 0.15)
            return child

        return start

    def run(self, *, verify=lambda: True, monotonic=time.monotonic, started=None):
        return c._run(
            self.root,
            self.plan,
            "invented-clearance",
            started=monotonic() if started is None else started,
            verify=verify,
            launcher=self.launch,
            workers=list,
            monotonic=monotonic,
            wall=lambda: datetime.fromisoformat(c.native.RETENTION).timestamp() - 3600,
        )


def test_four_cell_order_diagnosis_and_scientific_gate(tmp_path):
    x = Fixture(tmp_path)
    state = x.run()
    assert state["stop_code"] == "scope_completed" and state["calls"] == 4
    assert x.names == list(c.SEQUENCE)
    assert state["scientific_decision"]["decision"] == "limited_revealed_pair_support"
    assert state["remaining_calls"] == state["slots_closed_without_dispatch"] == 0
    for number in range(1, 5):
        report = c.read_json(x.folder / f"result-{number}.json")
        assert report["phase_diagnostic"]["image_tokens_total_confirmed"] == 1075
        assert report["phase_diagnostic"]["image_decode_complete"]
    x.owner.cleaned()
    with pytest.raises(ValueError, match="no_reentry"):
        x.run()
    assert len(x.owner.children) == 4


@pytest.mark.parametrize(
    "mode,stop",
    [
        ("timeout", "native_timeout"),
        ("cancel", "native_cancelled"),
        ("tokens", "contrast_geometry_token_mismatch"),
        ("invalid_json", "contrast_format_invalid"),
    ],
)
def test_first_technical_failure_seals_all_unused_slots(tmp_path, mode, stop):
    x = Fixture(tmp_path, mode=mode)
    state = x.run()
    assert state["sealed"] and state["calls"] == 1 and state["stop_code"] == stop
    assert state["slots_closed_without_dispatch"] == 3 and state["remaining_calls"] == 0
    assert state["scientific_decision"]["decision"] == "technical_incomplete"
    assert x.names == [c.SEQUENCE[0]]
    x.owner.cleaned()
    if mode == "timeout":
        report = c.read_json(x.folder / "result-1.json")
        assert report["phase_diagnostic"]["last_observed_phase"] == "image_decode"
    with pytest.raises(ValueError, match="no_reentry"):
        x.run()


def test_global_budget_can_close_without_reservation_or_launch(tmp_path):
    x = Fixture(tmp_path)
    state = x.run(monotonic=lambda: 336, started=0)
    assert state["stop_code"] == "contrast_global_deadline"
    assert state["calls"] == 0 and state["slots_closed_without_dispatch"] == 4
    assert not list(x.folder.glob("reservation-*.json")) and x.names == []


def test_lost_authority_refuses_before_lock_or_marker(tmp_path):
    x = Fixture(tmp_path)
    with pytest.raises(ValueError, match="authority_before_lock"):
        x.run(verify=lambda: False)
    assert not (x.folder / ".lock").exists() and not (x.folder / "started.json").exists()
    assert x.names == []


@pytest.mark.parametrize("missing", ["authorization.json", "review-seal.json"])
def test_public_execute_without_both_receipts_never_creates_dispatch_marker(tmp_path, missing):
    x = Fixture(tmp_path)
    other = "review-seal.json" if missing == "authorization.json" else "authorization.json"
    c.base.write(x.folder / other, {"invented": True})
    before = set(x.folder.iterdir())
    with pytest.raises(FileNotFoundError):
        c.execute(tmp_path)
    assert set(x.folder.iterdir()) == before


def receipts(x):
    bound = {
        "protocol": c.PROTOCOL,
        "namespace": c.durable.NAMESPACE,
        "plan_sha256": x.plan["plan_sha256"],
        "configuration_sha256": x.plan["configuration_sha256"],
        "root_sha256": x.plan["configuration"]["root_sha256"],
        "reviewer_thread_id": c.native.REVIEWER,
        "limits": c.LIMITS,
        "input_hashes": {v["name"]: v["png_sha256"] for v in x.plan["configuration"]["cells"]},
        "retry_allowed": False,
        "external_cost": 0,
    }
    literal = "Invented specific fixture permission; not a real authorization."
    auth = dict(
        bound,
        source_message_id="invented-new-user-message",
        literal_message=literal,
        literal_message_sha256=hashlib.sha256(literal.encode()).hexdigest(),
        decision="authorize_exact_four_cell_v3_once",
    )
    review = dict(
        bound,
        review_message_id="invented-independent-review-message",
        decision="reviewed_exact_v3_plan_and_authorization",
    )
    return auth, review


def write_receipts(x, auth, review):
    c.base.write(x.folder / "authorization.json", auth)
    review["authorization_sha256"] = c.base.sha(x.folder / "authorization.json")
    c.base.write(x.folder / "review-seal.json", review)


def test_fresh_bound_invented_receipt_only_validates_no_side_effect(tmp_path):
    x = Fixture(tmp_path)
    write_receipts(x, *receipts(x))
    assert len(c.release(tmp_path, x.plan)) == 64
    assert not (x.folder / ".lock").exists() and not (x.folder / "captures").exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("protocol", "v2"),
        ("namespace", c.previous.durable.NAMESPACE),
        ("plan_sha256", "a" * 64),
        ("configuration_sha256", "b" * 64),
        ("root_sha256", "c" * 64),
        ("reviewer_thread_id", "invented-other-reviewer"),
        ("limits", c.previous.LIMITS),
        ("input_hashes", {}),
        ("retry_allowed", True),
        ("external_cost", 1),
        ("literal_message_sha256", "d" * 64),
        ("decision", "authorize_exact_four_cell_v2_once"),
    ],
)
def test_receipts_cannot_transfer_scope_or_budget(tmp_path, field, value):
    x = Fixture(tmp_path)
    auth, review = receipts(x)
    auth[field] = value
    write_receipts(x, auth, review)
    with pytest.raises(ValueError, match="new_v3_authorization"):
        c.release(tmp_path, x.plan)
    assert not (x.folder / ".lock").exists()


def test_review_must_bind_auth_and_have_a_distinct_message(tmp_path):
    x = Fixture(tmp_path)
    auth, review = receipts(x)
    review["review_message_id"] = auth["source_message_id"]
    write_receipts(x, auth, review)
    with pytest.raises(ValueError, match="new_v3_authorization"):
        c.release(tmp_path, x.plan)


def test_generic_request_literal_cannot_supply_specific_permission(tmp_path):
    x = Fixture(tmp_path)
    auth, review = receipts(x)
    literal = "consegue ver esses 2 gargalos e resolver por favor, preciso mesmo entregar o projeto"
    auth.update(
        literal_message=literal, literal_message_sha256=hashlib.sha256(literal.encode()).hexdigest()
    )
    write_receipts(x, auth, review)
    with pytest.raises(ValueError, match="new_v3_authorization"):
        c.release(tmp_path, x.plan)


def test_cli_does_not_accept_root_model_or_approval_switches():
    command = [sys.executable, "-B", "-m", "scripts.vlm_native_contrast_v3", "--help"]
    result = subprocess.run(command, cwd=c.ROOT, capture_output=True, check=True, timeout=5)
    assert b"prepare,inspect,execute" in result.stdout
    assert all(flag not in result.stdout for flag in (b"--root", b"--model", b"--approve"))

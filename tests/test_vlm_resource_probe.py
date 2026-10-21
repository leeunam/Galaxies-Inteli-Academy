"""Invented bytes and ordinary Python children; no runtime, weights or private media."""

import copy
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime

import pytest

from scripts import vlm_resource_probe as c
from scripts import vlm_resource_telemetry as t


def sample(wall=1.0):
    return {
        "identity": {
            "process_sha256": "a" * 64,
            "boot_sha256": "b" * 64,
            "scope_sha256": "c" * 64,
            "hz": 100,
            "ancestor_distance": 1,
        },
        "process": {"utime": 100, "stime": 50, "minflt": 60, "majflt": 2},
        "memory": {"VmRSS": 1024, "VmSwap": 0},
        "cgroup_cpu": dict(zip(t.CPU_KEYS, (3000000, 2000000, 1000000, 10, 2, 3000), strict=True)),
        "cgroup_status": "available",
        "cgroup_context": {
            "memory_bytes": 10240,
            "swap_bytes": 0,
            "quota_usec": None,
            "period_usec": 100000,
        },
        "psi": {kind: {"some": 1000, "full": 100} for kind in ("cpu", "memory", "io")},
        "wall": wall,
        "read_seconds": 0.001,
        "sampler_prior_cost": {
            "wall_seconds": 0.001,
            "thread_cpu_seconds": 0.0005,
            "read_seconds": 0.0004,
            "write_seconds": 0.0001,
            "fsync_seconds": 0.0005,
            "bytes_read": 100,
            "bytes_written": 100,
            "fsync_count": 1,
        },
    }


def test_stat_uses_fields_after_last_parenthesis_not_process_name():
    fields = ["S"] + [str(n) for n in range(4, 25)]
    raw = ("37 (name with ) parens) " + " ".join(fields)).encode()
    assert t.proc_stat(raw, 37) == {
        "minflt": 10,
        "majflt": 12,
        "utime": 14,
        "stime": 15,
        "start_ticks": 22,
    }
    with pytest.raises(ValueError):
        t.proc_stat(raw, 38)


@pytest.mark.parametrize("raw", [b"-1", b"nan", b"1.0", b"18446744073709551616"])
def test_invalid_counter_is_not_silently_coerced(raw):
    with pytest.raises(ValueError):
        t.integer(raw.decode())


def test_memory_absence_is_unknown_not_zero():
    assert t.memory_status(b"State:\tZ (zombie)\n") == {"VmRSS": None, "VmSwap": None}
    assert t.memory_status(b"VmRSS: 12 kB\nVmSwap: 3 kB\n") == {"VmRSS": 12288, "VmSwap": 3072}
    with pytest.raises(ValueError):
        t.memory_status(b"VmRSS: 12 kB\nVmRSS: 14 kB\n")


def test_pressure_uses_totals_and_rejects_duplicate_or_nonfinite():
    valid = b"some avg10=1.23 avg60=0.30 avg300=0.05 total=100\n"
    assert t.pressure(valid) == {"some": 100, "full": None}
    for raw in (
        valid + valid,
        valid.replace(b"1.23", b"nan"),
        valid.replace(b"total=100", b"total=-1"),
    ):
        with pytest.raises(ValueError):
            t.pressure(raw)


@pytest.mark.parametrize("raw", [b"0::/../other", b"0::/x/./y", b"2:cpu:/x", b"0::/x\n0::/y"])
def test_membership_refuses_namespace_guessing_and_traversal(raw):
    with pytest.raises(ValueError):
        t.membership(raw)


def test_deltas_measure_prefix_child_cpu_and_shared_pressure_separately():
    first, last = sample(), sample(3)
    last["process"].update(utime=300, stime=150, minflt=80, majflt=5)
    last["cgroup_cpu"]["usage_usec"] += 5000000
    last["psi"]["memory"]["some"] += 900
    last["memory"]["VmRSS"] = 0  # gauge may decrease, counters may not
    value = t.deltas(first, last)
    assert value["user_seconds"] == 2 and value["system_seconds"] == 1
    assert value["average_cpu_cores"] == 1.5 and value["major_faults"] == 3
    assert value["shared_cgroup_cpu"]["usage_usec"] == 5000000
    assert value["shared_cgroup_pressure_usec"]["memory"]["some"] == 900
    assert value["exclusive_cgroup_attribution"] is value["per_phase_attribution"] is False


@pytest.mark.parametrize(
    "group,key,value",
    [
        ("identity", "process_sha256", "d" * 64),
        ("identity", "boot_sha256", "d" * 64),
        ("identity", "scope_sha256", "d" * 64),
        ("process", "utime", 99),
        ("cgroup_cpu", "nr_throttled", 1),
        ("cgroup_context", "quota_usec", 400000),
    ],
)
def test_reused_pid_reboot_scope_and_counter_reset_invalidate_comparison(group, key, value):
    first, last = sample(), sample(2)
    last[group][key] = value
    with pytest.raises(ValueError):
        t.deltas(first, last)


def test_prefix_recovery_refuses_corrupt_complete_records_and_never_is_terminal():
    first, last = sample(), sample(2)
    raw = (json.dumps(first) + "\n" + json.dumps(last) + "\n").encode()
    view = t.inspect_bytes(raw + b'{"part', c.durable._json)
    assert view["samples"] == 2 and view["truncated_tail"] and not view["terminal"]
    assert view["delta"]["sampled_seconds"] == 1
    bad = copy.deepcopy(last)
    bad["identity"]["process_sha256"] = "arbitrary-private-string"
    for broken in (json.dumps(bad).encode() + b"\n", raw + b"{}\n", b'{"wall":1,"wall":2}\n'):
        with pytest.raises(ValueError):
            t.inspect_bytes(broken, c.durable._json)
    with pytest.raises(ValueError):
        t.inspect_bytes(b" " * (t.POLICY["maximum_bytes"] + 1), c.durable._json)


def logs(tokens=1075, complete=True):
    value = "encoding mtmd batch, n_chunks = 1 (done = 0, total = 1)\nmtmd batch encoding done in 1 ms\n"
    value += f"decoding image batch 1/1, n_tokens_batch = {tokens}\n"
    return value + ("image decoded (batch 1/1) in 1 ms\n" if complete else "")


def argv(*, raw=b'{"answer":"no"}\n', tail="time.sleep(0.4)", complete=True, tokens=1075):
    script = "import os,signal,sys,time; "
    script += f"os.write(2, {logs(tokens, complete).encode()!r}); os.write(1, {raw!r}); "
    return [sys.executable, "-B", "-c", script + tail]


class PythonOnly:
    def __init__(self):
        self.children = []

    def __call__(self, command, **kwargs):
        assert command[:3] == [sys.executable, "-B", "-c"]
        process = subprocess.Popen(command, **kwargs)
        self.children.append(process)
        return process

    def cleaned(self):
        assert self.children
        for child in self.children:
            assert child.returncode is not None
            with pytest.raises(ProcessLookupError):
                os.killpg(child.pid, 0)


def capture(root, command=None, **kwargs):
    owner, reservations = PythonOnly(), []
    value = c.durable.capture(
        command or argv(),
        root=root,
        cell="negative-D",
        seconds=kwargs.pop("seconds", 75),
        reserve=lambda: reservations.append(1),
        popen=owner,
        **kwargs,
    )
    assert reservations == [1]
    owner.cleaned()
    return value


def test_real_child_sampler_preserves_bytes_and_original_decoder(tmp_path):
    raw = b'  {"answer" : "no"} \n'
    value = capture(tmp_path, argv(raw=raw))
    observation, resources = value["observation"], value["resources"]
    assert observation["stop_code"] is None and observation["answer"] == "no"
    assert resources["status"] == "sampled_prefix" and resources["samples"] >= 2
    assert resources["whole_lifetime_measured"] is False
    assert resources["observed_exit"] and resources["cost"]["fsync_count"] == resources["samples"]
    assert resources["delta"]["per_phase_attribution"] is False
    folder = tmp_path / c.QUEUE / "captures/negative-D"
    assert (folder / "stdout.bin").read_bytes() == raw
    view = c.durable.inspect(tmp_path, "negative-D")
    assert view["observation"] == observation
    assert view["resources"]["samples"] == resources["samples"]
    assert not (tmp_path / c.previous.QUEUE).exists()


def test_blocked_pipes_do_not_block_poll_sampling_or_timeout(tmp_path):
    value = capture(tmp_path, argv(raw=b"", complete=False, tail="time.sleep(30)"), seconds=0.4)
    assert value["observation"]["stop_code"] == "native_timeout"
    assert value["observation"]["cleanup_confirmed"] and value["resources"]["samples"] >= 2
    assert (
        not value["resources"]["observed_exit"]
        and not value["resources"]["whole_lifetime_measured"]
    )
    diagnostic = c.phase_diagnostic.diagnose(value["observation"])
    assert diagnostic["last_observed_phase"] == "image_decode"
    assert diagnostic["image_tokens_total_confirmed"] is None


def test_sigterm_preserves_owner_cleanup_and_handler(tmp_path):
    original = signal.getsignal(signal.SIGTERM)
    value = capture(
        tmp_path, argv(tail="time.sleep(.3); os.kill(os.getppid(), signal.SIGTERM); time.sleep(30)")
    )
    assert value["observation"]["stop_code"] == "native_cancelled"
    assert value["observation"]["cleanup_confirmed"]
    assert signal.getsignal(signal.SIGTERM) == original


def test_metadata_failure_after_spawn_returns_child_to_owner(tmp_path):
    def unavailable(pid):
        assert pid > 0
        os.kill(pid, 0)  # real live child, never a fabricated PID
        raise PermissionError("arbitrary text never projected")

    value = capture(tmp_path, argv(tail="time.sleep(30)"), _source=unavailable)
    assert value["observation"]["stop_code"] == "native_operation_failed"
    assert value["observation"]["cleanup_confirmed"]
    assert (
        value["resources"]["error"] == "permission"
        and value["resources"]["status"] == "inconclusive"
    )
    assert "arbitrary" not in json.dumps(value)


def test_resource_fsync_failure_after_spawn_still_reaps(tmp_path):
    def failed_sync(fd):
        raise OSError("invented disk failure")

    def sampler(directory, **kwargs):
        return t.Sampler(directory, **kwargs, _sync=failed_sync)

    value = capture(tmp_path, argv(tail="time.sleep(30)"), _sampler=sampler)
    assert value["observation"]["cleanup_confirmed"]
    assert value["observation"]["stop_code"] == "native_operation_failed"
    assert value["resources"]["error"] == "persistence"


def test_default_launcher_and_wrong_cell_and_deadline_refuse_before_files(tmp_path):
    for kwargs in (
        {},
        {"popen": PythonOnly(), "seconds": 80},
        {"popen": PythonOnly(), "cell": "negative-N"},
    ):
        supplied = {
            "root": tmp_path,
            "cell": "negative-D",
            "seconds": 75,
            "reserve": lambda: pytest.fail("reserved"),
        }
        supplied.update(kwargs)
        with pytest.raises(ValueError):
            c.durable.capture([], **supplied)
        assert list(tmp_path.iterdir()) == []


def test_no_reentry_or_symlink_to_consumed_namespace(tmp_path):
    capture(tmp_path)
    with pytest.raises(FileExistsError):
        capture(tmp_path)
    other = tmp_path / "other"
    other.mkdir()
    target = other / c.previous.QUEUE
    target.mkdir(parents=True, mode=0o700)
    (other / c.QUEUE).symlink_to(target, target_is_directory=True)
    with pytest.raises(OSError):
        capture(other)
    assert list(target.iterdir()) == []


class Fixture:
    def __init__(self, root, mode="success"):
        self.root, self.mode, self.owner = root, mode, PythonOnly()
        self.folder = root / c.QUEUE
        (self.folder / "images").mkdir(parents=True, mode=0o700)
        self.folder.chmod(0o700)
        raw = b"invented opaque bytes, not a real PNG"
        (self.folder / "images/negative-D.png").write_bytes(raw)
        config = {
            "cells": [
                {
                    "name": "negative-D",
                    "png_sha256": hashlib.sha256(raw).hexdigest(),
                    "expected_answer": "no",
                }
            ],
            "effective_argv_template": ["invented", "<PNG>", "<SCHEMA>"],
            "root_sha256": hashlib.sha256(str(root).encode()).hexdigest(),
        }
        self.plan = {"configuration": config, "configuration_sha256": c.base.digest(config)}
        self.plan["plan_sha256"] = c.base.digest(self.plan)
        c.base.write(self.folder / "checkpoint.json", dict(c.INITIAL))

    def launch(self, command, deadline):
        fake = argv()
        if self.mode == "timeout":
            fake = argv(raw=b"", complete=False, tail="time.sleep(30)")
        elif self.mode == "invalid":
            fake = argv(raw=b"invalid")
        elif self.mode == "tokens":
            fake = argv(tokens=1024)

        def start(actual, **kwargs):
            assert actual == command
            child = self.owner(fake, **kwargs)
            if self.mode == "timeout":
                return c.previous.previous._DeadlineProcess(child, time.monotonic() + 0.4)
            return child

        return start

    def run(self, verify=lambda: True, *, started=None, clock=time.monotonic):
        return c._run(
            self.root,
            self.plan,
            "invented-clearance",
            started=clock() if started is None else started,
            verify=verify,
            launcher=self.launch,
            workers=list,
            monotonic=clock,
            wall=lambda: datetime.fromisoformat(c.native.RETENTION).timestamp() - 3600,
        )


def test_one_probe_seals_and_never_makes_scientific_decision(tmp_path):
    x = Fixture(tmp_path)
    state = x.run()
    assert state["stop_code"] == "scope_completed" and state["calls"] == 1
    assert (
        state["sealed"] and state["remaining_calls"] == state["slots_closed_without_dispatch"] == 0
    )
    assert state["scientific_decision"]["decision"] == "not_a_perceptual_comparison"
    assert state["released_fields"] == [] and not state["retry_allowed"]
    report = c.read_json(x.folder / "result-1.json")
    assert report["resources"]["status"] == "sampled_prefix"
    assert report["phase_diagnostic"]["image_tokens_total_confirmed"] == 1075
    x.owner.cleaned()
    with pytest.raises(ValueError, match="no_reentry"):
        x.run()
    assert len(x.owner.children) == 1


@pytest.mark.parametrize(
    "mode,stop",
    [
        ("timeout", "native_timeout"),
        ("invalid", "contrast_format_invalid"),
        ("tokens", "contrast_geometry_token_mismatch"),
    ],
)
def test_telemetry_does_not_promote_timeout_bad_json_or_wrong_tokens(tmp_path, mode, stop):
    x = Fixture(tmp_path, mode)
    state = x.run()
    assert state["sealed"] and state["calls"] == 1 and state["stop_code"] == stop
    assert state["remaining_calls"] == 0 and state["released_fields"] == []
    x.owner.cleaned()
    assert c.read_json(x.folder / "result-1.json")["resources"]["status"] == "sampled_prefix"


def test_global_budget_exhaustion_consumes_no_dispatch_and_seals(tmp_path):
    x = Fixture(tmp_path)
    state = x.run(started=0, clock=lambda: 96)
    assert state["calls"] == 0 and state["slots_closed_without_dispatch"] == 1 and state["sealed"]
    assert not x.owner.children
    assert c.dispatch_deadline(0, 0, 999) == (80, 75)
    assert c.dispatch_deadline(0, 30, 999) == (100, 65)
    assert c.dispatch_deadline(0, 0, 12) == (12, 7)


@pytest.mark.parametrize("missing", ["authorization.json", "review-seal.json"])
def test_missing_external_authority_before_all_markers(tmp_path, missing):
    x = Fixture(tmp_path)
    other = "review-seal.json" if missing == "authorization.json" else "authorization.json"
    c.base.write(x.folder / other, {"invented": True})
    before = set(x.folder.iterdir())
    with pytest.raises(FileNotFoundError):
        c.execute(tmp_path)
    assert set(x.folder.iterdir()) == before
    with pytest.raises(ValueError, match="authority_before_lock"):
        x.run(verify=lambda: False)
    assert not (x.folder / ".lock").exists() and not (x.folder / "started.json").exists()


def receipts(x):
    bound = {
        "protocol": c.PROTOCOL,
        "namespace": c.durable.NAMESPACE,
        "plan_sha256": x.plan["plan_sha256"],
        "configuration_sha256": x.plan["configuration_sha256"],
        "root_sha256": x.plan["configuration"]["root_sha256"],
        "reviewer_thread_id": c.native.REVIEWER,
        "limits": c.LIMITS,
        "telemetry_policy": t.POLICY,
        "input_hashes": {"negative-D": x.plan["configuration"]["cells"][0]["png_sha256"]},
        "retry_allowed": False,
        "external_cost": 0,
    }
    literal = "Invented one-shot resource probe permission, never a real release."
    auth = dict(
        bound,
        source_message_id="invented-new-specific-message",
        literal_message=literal,
        literal_message_sha256=hashlib.sha256(literal.encode()).hexdigest(),
        decision="authorize_exact_one_dneg_resource_probe_once",
    )
    review = dict(
        bound,
        review_message_id="invented-external-review-message",
        decision="reviewed_exact_resource_probe_plan_and_authorization",
    )
    return auth, review


def write_receipts(x, auth, review):
    c.base.write(x.folder / "authorization.json", auth)
    review["authorization_sha256"] = c.base.sha(x.folder / "authorization.json")
    c.base.write(x.folder / "review-seal.json", review)


def test_receipts_bind_limits_sampler_scope_plan_root_and_external_reviewer(tmp_path):
    x = Fixture(tmp_path)
    auth, review = receipts(x)
    write_receipts(x, auth, review)
    assert len(c.release(tmp_path, x.plan)) == 64
    for field in (
        "limits",
        "telemetry_policy",
        "input_hashes",
        "plan_sha256",
        "root_sha256",
        "reviewer_thread_id",
        "decision",
    ):
        changed = copy.deepcopy(auth)
        changed[field] = "invented-mismatch"
        write_receipts(x, changed, review)
        with pytest.raises(ValueError, match="authorization_and_review"):
            c.release(tmp_path, x.plan)
    assert not (x.folder / ".lock").exists()
    assert (
        "42e1095878209eb8c40056e634c822437a08b6601063bc16d585174a3795e447"
        in c.REJECTED_MESSAGE_SHA256
    )


def test_missing_cgroup_mapping_preserves_child_delta_without_context():
    first, last = sample(), sample(2)
    for value in (first, last):
        value.update(
            cgroup_status="mapping_unproven",
            cgroup_cpu=None,
            cgroup_context=None,
            psi={k: None for k in ("cpu", "memory", "io")},
        )
    last["process"]["utime"] += 50
    value = t.deltas(first, last)
    assert value["user_seconds"] == 0.5 and value["shared_cgroup_cpu"] is None
    assert all(v is None for v in value["shared_cgroup_pressure_usec"].values())
    last["psi"]["cpu"] = {"some": 0, "full": 0}
    with pytest.raises(ValueError):
        t.validate_sample(last)


def test_missing_root_cpu_max_has_no_invented_period_or_quota():
    first, last = sample(), sample(2)
    for value in (first, last):
        value["cgroup_context"].update(quota_usec=None, period_usec=None)
    assert t.deltas(first, last)["sampled_seconds"] == 1


def test_disappearance_after_observed_exit_is_not_zero_sample(tmp_path):
    value = capture(tmp_path, argv(tail="pass"))
    resource = value["resources"]
    assert resource["observed_exit"] and not resource["whole_lifetime_measured"]
    assert resource["samples"] <= 1 and resource["delta"] is None
    assert resource["status"] == "inconclusive"


def test_sampler_cap_closes_owned_process_without_extra_dispatch(tmp_path):
    def exhausted(directory, **kwargs):
        sampler = t.Sampler(directory, **kwargs)
        sampler.bytes = t.POLICY["maximum_bytes"]
        return sampler

    value = capture(tmp_path, argv(tail="time.sleep(30)"), _sampler=exhausted)
    assert value["observation"]["cleanup_confirmed"]
    assert value["observation"]["stop_code"] == "native_operation_failed"
    assert value["resources"]["error"] == "byte_limit"


def test_prepared_inspection_has_no_authorized_balance(tmp_path):
    x = Fixture(tmp_path)
    state = c.inspect(tmp_path)
    assert state["status"] == "prepared_not_authorized"
    assert state["unconsumed_slots"] == 1 and state["remaining_authorized_calls"] == 0
    assert not (x.folder / "started.json").exists()

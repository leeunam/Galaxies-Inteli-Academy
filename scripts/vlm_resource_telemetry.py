"""Bounded Linux metadata sampling for one real owned child; no process owner."""

from __future__ import annotations

import hashlib
import itertools
import json
import math
import os
import re
import stat
import time
from pathlib import Path

POLICY = {
    "interval_seconds": 0.25,
    "maximum_samples": 304,
    "maximum_bytes": 524288,
    "read_limit_bytes": 16384,
    "maximum_sampler_wall_seconds": 3.0,
}
COUNTERS = ("utime", "stime", "minflt", "majflt")
CPU_KEYS = (
    "usage_usec",
    "user_usec",
    "system_usec",
    "nr_periods",
    "nr_throttled",
    "throttled_usec",
)
ERRORS = {
    "unavailable",
    "permission",
    "malformed",
    "identity_changed",
    "scope_changed",
    "counter_reset",
    "sample_limit",
    "byte_limit",
    "persistence",
    "overhead_limit",
}


def integer(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,20}", value):
        raise ValueError("malformed")
    number = int(value)
    if number > 2**64 - 1:
        raise ValueError("malformed")
    return number


def proc_stat(raw, pid):
    text = raw.decode("ascii")
    head, separator, tail = text.rpartition(") ")
    fields = tail.split()
    if not separator or not head.startswith(str(pid) + " (") or len(fields) < 22:
        raise ValueError("malformed")
    if fields[0] not in ("R", "S", "D", "Z", "T", "t", "X", "x", "K", "W", "P", "I"):
        raise ValueError("malformed")
    keys = {"minflt": 7, "majflt": 9, "utime": 11, "stime": 12, "start_ticks": 19}
    return {key: integer(fields[index]) for key, index in keys.items()}


def memory_status(raw):
    values = {}
    for line in raw.decode("ascii").splitlines():
        key, _, value = line.partition(":")
        if key in ("VmRSS", "VmSwap"):
            bits = value.split()
            if key in values or len(bits) != 2 or bits[1] != "kB":
                raise ValueError("malformed")
            values[key] = integer(bits[0]) * 1024
    # Missing memory fields on a zombie are unavailable, never zero.
    return {key: values.get(key) for key in ("VmRSS", "VmSwap")}


def cpu_stat(raw):
    values = {}
    for line in raw.decode("ascii").splitlines():
        bits = line.split()
        if len(bits) != 2 or bits[0] in values:
            raise ValueError("malformed")
        values[bits[0]] = integer(bits[1])
    if not {"usage_usec", "user_usec", "system_usec"} <= values.keys():
        raise ValueError("malformed")
    return {key: values.get(key) for key in CPU_KEYS}


def pressure(raw):
    values = {}
    for line in raw.decode("ascii").splitlines():
        bits = line.split()
        if len(bits) != 5 or bits[0] not in ("some", "full") or bits[0] in values:
            raise ValueError("malformed")
        fields = {}
        for token in bits[1:]:
            key, sep, value = token.partition("=")
            if not sep or key in fields:
                raise ValueError("malformed")
            fields[key] = value
        if set(fields) != {"avg10", "avg60", "avg300", "total"}:
            raise ValueError("malformed")
        averages = [float(fields[k]) for k in ("avg10", "avg60", "avg300")]
        if not all(math.isfinite(v) and 0 <= v <= 100 for v in averages):
            raise ValueError("malformed")
        values[bits[0]] = integer(fields["total"])
    if "some" not in values:
        raise ValueError("malformed")
    # Only cumulative microseconds are retained, not arbitrary kernel strings.
    return {key: values.get(key) for key in ("some", "full")}


def membership(raw):
    lines = raw.decode("ascii").splitlines()
    if len(lines) != 1 or not lines[0].startswith("0::/"):
        raise ValueError("malformed")
    value = lines[0][3:]
    parts = value.split("/")[1:]
    if value != "/" and any(
        not re.fullmatch(r"[A-Za-z0-9_.:@\-]+", p) or p in (".", "..") for p in parts
    ):
        raise ValueError("malformed")
    return value


def read_fixed(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise ValueError("malformed")
        raw = os.read(fd, POLICY["read_limit_bytes"] + 1)
        if len(raw) > POLICY["read_limit_bytes"]:
            raise ValueError("malformed")
        return raw
    finally:
        os.close(fd)


def digest(value):
    return hashlib.sha256(value).hexdigest()


class Source:
    """Fixed proc/cgroup v2 scope. Paths stay in memory, never in telemetry."""

    def __init__(self, pid):
        if type(pid) is not int or pid <= 0:
            raise ValueError("identity_changed")
        self.pid = pid
        self.proc = Path("/proc") / str(pid)
        self.bytes_read = 0
        self.boot = self.read(Path("/proc/sys/kernel/random/boot_id")).strip()
        if not re.fullmatch(rb"[0-9a-f-]{36}", self.boot):
            raise ValueError("malformed")
        self.start = proc_stat(self.read(self.proc / "stat"), pid)["start_ticks"]
        self.member = membership(self.read(self.proc / "cgroup"))
        self.cgroup_ns = os.stat(self.proc / "ns/cgroup").st_ino
        self.hz = os.sysconf("SC_CLK_TCK")
        root = Path("/sys/fs/cgroup")
        self.scope, self.scope_status, distance = None, "mapping_unproven", 0
        target = root / self.member.lstrip("/")
        try:
            # Never walk up from an absent membership path or translate symlinks.
            candidate = root
            for part in target.relative_to(root).parts:
                candidate = candidate / part
                if candidate.is_symlink() or not candidate.is_dir():
                    raise FileNotFoundError
            if not root.is_dir() or root.is_symlink():
                raise FileNotFoundError
            candidate = target
            while not (candidate / "cpu.max").is_file():
                if candidate == root:
                    break  # Root legitimately has no cpu.max.
                candidate = candidate.parent
                distance += 1
                if distance > 64:
                    raise ValueError("malformed")
            # Prove this namespace's PID maps into this exact leaf; discard
            # other IDs and never open another process.
            members = self.read(target / "cgroup.procs").decode("ascii").split()
            if self.pid not in [integer(v) for v in members]:
                raise FileNotFoundError
            self.scope_stat = candidate.stat()
            self.scope = candidate
            self.scope_status = "available"
        except (OSError, ValueError, UnicodeError):
            self.scope = None
        token = (
            f":{self.scope_stat.st_dev}:{self.scope_stat.st_ino}:{distance}"
            if self.scope is not None
            else ":unavailable"
        )
        self.identity = {
            "process_sha256": digest(self.boot + f":{pid}:{self.start}".encode()),
            "boot_sha256": digest(self.boot),
            "scope_sha256": digest(
                self.boot + self.member.encode() + token.encode() + str(self.cgroup_ns).encode()
            ),
            "hz": self.hz,
            "ancestor_distance": distance,
        }

    def read(self, path):
        raw = read_fixed(path)
        self.bytes_read += len(raw)
        return raw

    def snapshot(self):
        before = proc_stat(self.read(self.proc / "stat"), self.pid)
        if (
            self.read(Path("/proc/sys/kernel/random/boot_id")).strip() != self.boot
            or before["start_ticks"] != self.start
        ):
            raise ValueError("identity_changed")
        if (
            membership(self.read(self.proc / "cgroup")) != self.member
            or os.stat(self.proc / "ns/cgroup").st_ino != self.cgroup_ns
        ):
            raise ValueError("scope_changed")
        memory = memory_status(self.read(self.proc / "status"))
        cpu, context, psi = None, None, {kind: None for kind in ("cpu", "memory", "io")}
        if self.scope is not None:
            info = self.scope.stat()
            if (info.st_dev, info.st_ino) != (self.scope_stat.st_dev, self.scope_stat.st_ino):
                raise ValueError("scope_changed")
            cpu = cpu_stat(self.read(self.scope / "cpu.stat"))
            try:
                quota = self.read(self.scope / "cpu.max").decode("ascii").split()
            except FileNotFoundError:
                if self.scope != Path("/sys/fs/cgroup"):
                    raise
                quota = None
            if quota is not None and (len(quota) != 2 or integer(quota[1]) == 0):
                raise ValueError("malformed")
            limit = None if quota is None or quota[0] == "max" else integer(quota[0])
            context = {
                "memory_bytes": integer(self.read(self.scope / "memory.current").decode().strip()),
                "swap_bytes": integer(
                    self.read(self.scope / "memory.swap.current").decode().strip()
                ),
                "quota_usec": limit,
                "period_usec": integer(quota[1]) if quota is not None else None,
            }
            for kind in ("cpu", "memory", "io"):
                try:
                    psi[kind] = pressure(self.read(self.scope / (kind + ".pressure")))
                except FileNotFoundError:
                    pass
        after = proc_stat(self.read(self.proc / "stat"), self.pid)
        if (
            after["start_ticks"] != self.start
            or self.read(Path("/proc/sys/kernel/random/boot_id")).strip() != self.boot
        ):
            raise ValueError("identity_changed")
        if membership(self.read(self.proc / "cgroup")) != self.member:
            raise ValueError("scope_changed")
        if any(after[k] < before[k] for k in COUNTERS):
            raise ValueError("counter_reset")
        return {
            "identity": self.identity,
            "process": {k: after[k] for k in COUNTERS},
            "memory": memory,
            "cgroup_status": self.scope_status,
            "cgroup_cpu": cpu,
            "cgroup_context": context,
            "psi": psi,
        }


def validate_sample(value):
    if type(value) is not dict or set(value) != {
        "identity",
        "process",
        "memory",
        "cgroup_cpu",
        "cgroup_context",
        "cgroup_status",
        "psi",
        "wall",
        "read_seconds",
        "sampler_prior_cost",
    }:
        raise ValueError("malformed")
    cost = value["sampler_prior_cost"]
    expected = {
        "wall_seconds",
        "thread_cpu_seconds",
        "read_seconds",
        "write_seconds",
        "fsync_seconds",
        "bytes_read",
        "bytes_written",
        "fsync_count",
    }
    if (
        type(cost) is not dict
        or set(cost) != expected
        or any(type(n) not in (int, float) or not math.isfinite(n) or n < 0 for n in cost.values())
    ):
        raise ValueError("malformed")
    ident = value["identity"]
    if type(ident) is not dict or set(ident) != {
        "process_sha256",
        "boot_sha256",
        "scope_sha256",
        "hz",
        "ancestor_distance",
    }:
        raise ValueError("malformed")
    for key in ("process_sha256", "boot_sha256", "scope_sha256"):
        if type(ident[key]) is not str or not re.fullmatch(r"[0-9a-f]{64}", ident[key]):
            raise ValueError("malformed")
    if (
        type(ident["hz"]) is not int
        or not 0 < ident["hz"] <= 100000
        or type(ident["ancestor_distance"]) is not int
        or not 0 <= ident["ancestor_distance"] <= 64
    ):
        raise ValueError("malformed")
    for key in ("wall", "read_seconds"):
        if type(value[key]) not in (int, float) or not math.isfinite(value[key]) or value[key] < 0:
            raise ValueError("malformed")
    if value["cgroup_status"] not in ("available", "mapping_unproven"):
        raise ValueError("malformed")
    groups = (
        ("process", COUNTERS, False),
        ("memory", ("VmRSS", "VmSwap"), True),
        ("cgroup_cpu", CPU_KEYS, True),
        ("cgroup_context", ("memory_bytes", "swap_bytes", "quota_usec", "period_usec"), True),
    )
    for group, keys, nullable in groups:
        data = value[group]
        if group.startswith("cgroup_") and value["cgroup_status"] == "mapping_unproven":
            if data is not None:
                raise ValueError("malformed")
            continue
        if type(data) is not dict or set(data) != set(keys):
            raise ValueError("malformed")
        for number in data.values():
            if number is None and nullable:
                continue
            if type(number) is not int or not 0 <= number <= 2**64 - 1:
                raise ValueError("malformed")
    if value["cgroup_cpu"] is not None and any(
        value["cgroup_cpu"][k] is None for k in CPU_KEYS[:3]
    ):
        raise ValueError("malformed")
    if value["cgroup_context"] is not None and (
        any(value["cgroup_context"][k] is None for k in ("memory_bytes", "swap_bytes"))
        or value["cgroup_context"]["period_usec"] == 0
        or (
            value["cgroup_context"]["quota_usec"] is not None
            and value["cgroup_context"]["period_usec"] is None
        )
    ):
        raise ValueError("malformed")
    if type(value["psi"]) is not dict or set(value["psi"]) != {"cpu", "memory", "io"}:
        raise ValueError("malformed")
    if value["cgroup_status"] == "mapping_unproven" and any(
        v is not None for v in value["psi"].values()
    ):
        raise ValueError("malformed")
    for data in value["psi"].values():
        if data is None:
            continue
        if type(data) is not dict or set(data) != {"some", "full"} or data["some"] is None:
            raise ValueError("malformed")
        if any(
            n is not None and (type(n) is not int or not 0 <= n <= 2**64 - 1) for n in data.values()
        ):
            raise ValueError("malformed")


def deltas(first, last):
    for value in (first, last):
        validate_sample(value)
    if first["identity"] != last["identity"]:
        raise ValueError("identity_changed")
    if first["cgroup_status"] != last["cgroup_status"]:
        raise ValueError("scope_changed")
    if first["cgroup_context"] is not None and (
        first["cgroup_context"]["quota_usec"],
        first["cgroup_context"]["period_usec"],
    ) != (last["cgroup_context"]["quota_usec"], last["cgroup_context"]["period_usec"]):
        raise ValueError("scope_changed")
    wall = last["wall"] - first["wall"]
    if wall <= 0:
        raise ValueError("counter_reset")

    def difference(a, b):
        if (a is None) != (b is None):
            raise ValueError("scope_changed")
        if a is None:
            return None
        if b < a:
            raise ValueError("counter_reset")
        return b - a

    proc = {k: difference(first["process"][k], last["process"][k]) for k in COUNTERS}
    cpu = (
        None
        if first["cgroup_cpu"] is None
        else {k: difference(first["cgroup_cpu"][k], last["cgroup_cpu"][k]) for k in CPU_KEYS}
    )
    psi = {}
    for kind in ("cpu", "memory", "io"):
        a, b = first["psi"][kind], last["psi"][kind]
        if (a is None) != (b is None):
            raise ValueError("scope_changed")
        psi[kind] = None if a is None else {k: difference(a[k], b[k]) for k in ("some", "full")}
    hz = first["identity"]["hz"]
    return {
        "sampled_seconds": wall,
        "user_seconds": proc["utime"] / hz,
        "system_seconds": proc["stime"] / hz,
        "average_cpu_cores": (proc["utime"] + proc["stime"]) / hz / wall,
        "minor_faults": proc["minflt"],
        "major_faults": proc["majflt"],
        "shared_cgroup_cpu": cpu,
        "shared_cgroup_pressure_usec": psi,
        "exclusive_cgroup_attribution": False,
        "per_phase_attribution": False,
    }


class Sampler:
    """Synchronous poll observer; its own CPU uses thread_time, not child time."""

    def __init__(self, directory, *, source=Source, _sync=os.fsync):
        self.source_factory, self.source, self.sync = source, None, _sync
        self.fd = os.open(
            "resources.jsonl",
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory,
        )
        try:
            os.fsync(directory)
        except BaseException:
            os.close(self.fd)
            raise
        self.samples, self.bytes, self.error = [], 0, None
        self.cost = {
            "wall_seconds": 0.0,
            "thread_cpu_seconds": 0.0,
            "read_seconds": 0.0,
            "write_seconds": 0.0,
            "fsync_seconds": 0.0,
            "bytes_read": 0,
            "bytes_written": 0,
            "fsync_count": 0,
        }
        self.started = time.monotonic()
        self.ended = False

    def poll(self, process):
        # Existing owner's reader threads do not block its 50 ms polling loop.
        # 250 ms is a minimum spacing, never a guarantee of maximum latency.
        code = process.poll()
        if code is not None:
            self.ended = True
            return code
        now = time.monotonic()
        if (
            self.samples
            and now - self.started - self.samples[-1]["wall"] < POLICY["interval_seconds"]
        ):
            return None
        begin, cpu_begin = now, time.thread_time()
        stage = "read"
        try:
            if len(self.samples) >= POLICY["maximum_samples"]:
                raise ValueError("sample_limit")
            read_begin = time.monotonic()
            if self.source is None:
                self.source = self.source_factory(process.pid)
            value = self.source.snapshot()
            value.update(
                wall=time.monotonic() - self.started,
                read_seconds=time.monotonic() - read_begin,
                sampler_prior_cost=dict(self.cost),
            )
            self.cost["read_seconds"] += value["read_seconds"]
            self.cost["bytes_read"] = self.source.bytes_read
            validate_sample(value)
            if self.samples:
                deltas(self.samples[-1], value)
            raw = (json.dumps(value, separators=(",", ":"), allow_nan=False) + "\n").encode()
            if self.bytes + len(raw) > POLICY["maximum_bytes"]:
                raise ValueError("byte_limit")
            stage = "persistence"
            write_begin = time.monotonic()
            view = memoryview(raw)
            while view:
                count = os.write(self.fd, view)
                if count <= 0:
                    raise OSError("persistence")
                view = view[count:]
            self.cost["write_seconds"] += time.monotonic() - write_begin
            sync_begin = time.monotonic()
            self.sync(self.fd)
            self.cost["fsync_seconds"] += time.monotonic() - sync_begin
            self.cost["fsync_count"] += 1
            self.bytes += len(raw)
            self.cost["bytes_written"] = self.bytes
            self.samples.append(value)
        except Exception as exc:  # noqa: BLE001 -- only fixed categories cross this boundary
            self.error = (
                str(exc)
                if isinstance(exc, ValueError) and str(exc) in ERRORS
                else "permission"
                if isinstance(exc, PermissionError)
                else "unavailable"
                if isinstance(exc, FileNotFoundError)
                else ("persistence" if stage == "persistence" else "unavailable")
                if isinstance(exc, OSError)
                else "malformed"
            )
            raise OSError("resource_metadata_failed") from None
        finally:
            self.cost["wall_seconds"] += time.monotonic() - begin
            self.cost["thread_cpu_seconds"] += time.thread_time() - cpu_begin
        if self.cost["wall_seconds"] > POLICY["maximum_sampler_wall_seconds"]:
            self.error = "overhead_limit"
            raise OSError("resource_metadata_failed")
        return None

    def summary(self):
        return {
            "status": "inconclusive"
            if self.error
            or len(self.samples) < 2
            or self.samples[-1]["cgroup_status"] != "available"
            else "sampled_prefix",
            "error": self.error,
            "samples": len(self.samples),
            "observed_exit": self.ended,
            "whole_lifetime_measured": False,
            "per_phase_attribution": False,
            "maximum_gap_seconds": max(
                (b["wall"] - a["wall"] for a, b in itertools.pairwise(self.samples)), default=None
            ),
            "first_sample_seconds": self.samples[0]["wall"] if self.samples else None,
            "last_sample_seconds": self.samples[-1]["wall"] if self.samples else None,
            "cost": dict(self.cost),
            "cost_excludes_setup_and_close": True,
            "cost_is_lower_bound_on_failure": self.error is not None,
            "delta": deltas(self.samples[0], self.samples[-1])
            if not self.error and len(self.samples) >= 2
            else None,
        }

    def close(self):
        os.close(self.fd)


class ObservedProcess:
    def __init__(self, process, sampler):
        self.process, self.sampler = process, sampler

    def __getattr__(self, name):
        return getattr(self.process, name)

    def poll(self):
        return self.sampler.poll(self.process)


def inspect_bytes(raw, parse):
    """Recover validated complete records; a prefix never certifies completion."""
    if len(raw) > POLICY["maximum_bytes"]:
        raise ValueError("byte_limit")
    parts = raw.split(b"\n")
    truncated = bool(parts[-1])
    records = [parse(line) for line in parts[:-1]]
    if len(records) > POLICY["maximum_samples"]:
        raise ValueError("sample_limit")
    for value in records:
        validate_sample(value)
    for first, last in itertools.pairwise(records):
        deltas(first, last)
    return {
        "status": "provisional_prefix",
        "samples": len(records),
        "truncated_tail": truncated,
        "terminal": False,
        "last_sample_seconds": records[-1]["wall"] if records else None,
        "overhead_through_previous_record": records[-1]["sampler_prior_cost"] if records else None,
        "delta": deltas(records[0], records[-1]) if len(records) >= 2 else None,
    }

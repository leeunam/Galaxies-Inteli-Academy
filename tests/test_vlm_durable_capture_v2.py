"""Real disposable Python children and invented bytes only; no models or network."""

import ctypes
import hashlib
import json
import os
import signal
import subprocess
import sys
import time

import pytest

from scripts import vlm_durable_capture_v2 as durable

LOG = (
    b"encoding mtmd batch, n_chunks = 1 (done = 1, total = 3)\n"
    b"mtmd batch encoding done in 12 ms\n"
    b"decoding image batch 1/1, n_tokens_batch = 1075\n"
    b"image decoded (batch 1/1) in 8 ms\n"
)
CELL = "negative-D"


def folder(root):
    return root / "data/private" / durable.NAMESPACE / "captures" / CELL


def program(raw=b'{"answer":"no"}', stderr=LOG, tail=""):
    return [
        sys.executable,
        "-B",
        "-c",
        f"import os,time;os.write(1,{raw!r});os.write(2,{stderr!r});{tail}",
    ]


def run(root, raw=b'{"answer":"no"}', stderr=LOG, tail="", seconds=2):
    reserved, processes = [], []

    def start(*args, **kwargs):
        assert reserved == [True]
        process = subprocess.Popen(*args, **kwargs)
        processes.append(process)
        return process

    result = durable.capture(
        program(raw, stderr, tail),
        root=root,
        cell=CELL,
        seconds=seconds,
        reserve=lambda: reserved.append(True),
        popen=start,
    )
    assert reserved == [True]
    assert all(process.poll() is not None for process in processes)
    assert result["cleanup_confirmed"]
    return result


@pytest.mark.parametrize(
    "raw",
    [
        b' \n{"answer":"no"}\t',
        b'{"answer":"yes"}',
        b'{"answer":"uncertain"}',
        b"\xff",
        b'{"answer":"no","answer":"yes"}',
        b'prefix {"answer":"yes"}',
    ],
)
def test_original_bytes_parser_and_terminal_result(tmp_path, raw):
    result = run(tmp_path, raw)
    assert (folder(tmp_path) / "stdout.bin").read_bytes() == raw
    snapshot = durable.inspect(tmp_path, CELL)
    assert snapshot["terminal"] and snapshot["observation"] == result
    assert result["image_tokens_observed"] == 1075
    assert result["image_encoder_and_decode_observed"]
    try:
        expected = durable.short.decode(raw)
    except (ValueError, UnicodeError):
        assert result["answer"] is None and result["format_status"] == "invalid"
    else:
        assert result["answer"] == expected and result["format_status"] == "valid"
    assert result["raw_stdout_retained"] and not result["raw_stderr_retained"]
    assert all(p.stat().st_mode & 0o077 == 0 for p in folder(tmp_path).iterdir())


def test_unterminated_stderr_line_is_provisional(tmp_path):
    journal = durable.Journal(tmp_path, CELL)
    try:
        journal.record("stderr", LOG[:-1])
        before = durable.inspect(tmp_path, CELL)
        assert not before["terminal"] and not before["cleanup_confirmed"]
        assert not before["progress"]["image_encoder_and_decode_observed"]
        journal.record("stderr", b"")
        after = durable.inspect(tmp_path, CELL)
        assert after["progress"]["image_tokens_observed"] == 1075
        assert not after["terminal"]
    finally:
        journal.close()


def test_stderr_private_content_never_reaches_durable_files(tmp_path):
    run(tmp_path, stderr=b"PRIVATE_SENTINEL invented-secret\n" + LOG)
    for path in folder(tmp_path).iterdir():
        assert b"PRIVATE_SENTINEL" not in path.read_bytes()


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_oversize_preserves_cap_and_remains_terminal_failure(tmp_path, stream):
    cap = durable.short.base.LIMITS[stream + "_bytes"]
    # Avoid OS argv length limits: generate the invented excess inside the child.
    fd = 1 if stream == "stdout" else 2
    result = run(
        tmp_path, raw=b"", stderr=LOG if fd == 1 else b"", tail=f"os.write({fd},b'x'*{cap + 1})"
    )
    assert result["stop_code"] == "output_limit_or_unclosed_pipe"
    assert result["answer"] is None
    assert (folder(tmp_path) / "stdout.bin").stat().st_size <= durable.short.base.LIMITS[
        "stdout_bytes"
    ]
    assert durable.inspect(tmp_path, CELL)["terminal"]


def test_timeout_keeps_short_prefix_before_eof_and_cleans(tmp_path):
    result = run(tmp_path, tail="time.sleep(20)", seconds=0.2)
    assert result["stop_code"] == "native_timeout"
    assert (folder(tmp_path) / "stdout.bin").read_bytes() == b'{"answer":"no"}'
    assert durable.inspect(tmp_path, CELL)["cleanup_confirmed"]


def test_no_default_launcher_or_old_queue_or_reentry(tmp_path):
    with pytest.raises(ValueError, match="release_required"):
        durable.capture([], root=tmp_path, cell=CELL, seconds=1, reserve=lambda: None)
    assert not (tmp_path / "data").exists()
    run(tmp_path)
    before = {p.name: p.read_bytes() for p in folder(tmp_path).iterdir()}
    with pytest.raises(FileExistsError):
        run(tmp_path)
    assert before == {p.name: p.read_bytes() for p in folder(tmp_path).iterdir()}
    with pytest.raises(ValueError, match="path_rejected"):
        durable.Journal(tmp_path / "data/private/issue-4-vlm-native-contrast-v1", CELL)


def test_symlink_parent_and_result_and_hardlink_rejected(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    linked = tmp_path / "linked"
    linked.symlink_to(target, target_is_directory=True)
    with pytest.raises(OSError):
        durable.Journal(linked, CELL)
    assert not list(target.iterdir())
    run(tmp_path)
    state = folder(tmp_path) / "state.json"
    state.rename(tmp_path / "saved.json")
    state.symlink_to(tmp_path / "saved.json")
    with pytest.raises(OSError):
        durable.inspect(tmp_path, CELL)
    state.unlink()
    os.link(tmp_path / "saved.json", state)
    with pytest.raises(ValueError, match="file_rejected"):
        durable.inspect(tmp_path, CELL)


def test_partial_checkpoint_and_uncommitted_tail_are_never_final(tmp_path):
    journal = durable.Journal(tmp_path, CELL)
    journal.record("stdout", b'{"answer":')
    journal.close()
    directory = folder(tmp_path)
    (directory / ".state.json.pending").write_bytes(b'{"terminal":true')
    with (directory / "stdout.bin").open("ab") as output:
        output.write(b'"yes"}')
    snapshot = durable.inspect(tmp_path, CELL)
    assert snapshot["durable_stdout_bytes"] == len(b'{"answer":')
    assert not snapshot["terminal"] and snapshot["observation"] is None
    with (directory / "stdout.bin").open("r+b") as output:
        output.write(b"!")
    with pytest.raises(ValueError, match="prefix_integrity"):
        durable.inspect(tmp_path, CELL)


def test_persistence_failure_after_spawn_is_cleaned_by_original_owner(tmp_path):
    processes = []

    def start(*args, **kwargs):
        process = subprocess.Popen(*args, **kwargs)
        processes.append(process)
        (folder(tmp_path) / ".state.json.pending").write_bytes(b"injected disk failure")
        return process

    with pytest.raises(OSError, match="durable_capture_failed"):
        durable.capture(
            program(tail="time.sleep(20)"),
            root=tmp_path,
            cell=CELL,
            seconds=1,
            reserve=lambda: None,
            popen=start,
        )
    assert processes and processes[0].poll() is not None
    assert not durable.inspect(tmp_path, CELL)["terminal"]


def controller(root):
    code = (
        "import subprocess,sys;from pathlib import Path;"
        "from scripts.vlm_durable_capture_v2 import capture;"
        f"capture({program(tail='time.sleep(20)')!r},root=Path(sys.argv[1]),"
        f"cell={CELL!r},seconds=3,reserve=lambda:None,popen=subprocess.Popen)"
    )
    return subprocess.Popen(
        [sys.executable, "-B", "-c", code, str(root)],
        cwd=durable.short.base.ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env={**durable.short.base.environment(), "PYTHONDONTWRITEBYTECODE": "1"},
    )


def await_prefix(root, process):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        assert process.poll() is None
        try:
            value = durable.inspect(root, CELL)
            if value["durable_stdout_bytes"]:
                return
        except (FileNotFoundError, json.JSONDecodeError):
            pass
        time.sleep(0.01)
    raise AssertionError("invented_prefix_not_persisted_before_exit")


@pytest.mark.parametrize("sig", [signal.SIGTERM, signal.SIGINT, signal.SIGKILL])
def test_cancellation_or_crash_keeps_prefix_and_never_claims_missing_cleanup(tmp_path, sig):
    # Real adoption is confined to the test process and restored afterwards;
    # this lets the fault injector reap its own orphan, without fake PIDs.
    libc = ctypes.CDLL(None, use_errno=True)
    previous = ctypes.c_int()
    assert libc.prctl(37, ctypes.byref(previous), 0, 0, 0) == 0
    assert libc.prctl(36, 1, 0, 0, 0) == 0
    process = controller(tmp_path)
    lease = None
    try:
        await_prefix(tmp_path, process)
        lease = json.loads((folder(tmp_path) / "process-lease.json").read_bytes())
        process.send_signal(sig)
        process.wait(timeout=8)
        snapshot = durable.inspect(tmp_path, CELL)
        assert snapshot["durable_stdout_bytes"] == len(b'{"answer":"no"}')
        if sig == signal.SIGKILL:
            assert not snapshot["terminal"] and not snapshot["cleanup_confirmed"]
            assert snapshot["observation"] is None
        else:
            assert snapshot["terminal"] and snapshot["cleanup_confirmed"]
            assert snapshot["observation"]["stop_code"] == "native_cancelled"
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        if lease is not None:
            # The crash test alone is the external recovery owner. Verify the
            # real identity before collecting its disposable child group.
            try:
                if durable.supervisor.identity(lease["leader"]["pid"]) == lease["leader"]:
                    os.killpg(lease["pgid"], signal.SIGKILL)
            except ProcessLookupError:
                pass
            except FileNotFoundError:
                pass
            if sig == signal.SIGKILL:
                pid, _ = os.waitpid(lease["leader"]["pid"], 0)
                assert pid == lease["leader"]["pid"]
        assert libc.prctl(36, previous.value, 0, 0, 0) == 0


def test_reader_failure_is_not_silently_a_complete_capture(tmp_path):
    journal = durable.Journal(tmp_path, CELL)

    class Broken:
        def read(self, size):
            raise OSError("invented private failure")

    try:
        assert durable.Stream(Broken(), "stdout", journal).read(4096) == b""
        assert journal.failed.is_set()
        assert not durable.inspect(tmp_path, CELL)["terminal"]
    finally:
        journal.close()


def test_reserved_failure_does_not_spawn_or_allow_reentry(tmp_path):
    spawned = []

    def reserve():
        (folder(tmp_path) / ".state.json.pending").write_bytes(b"injected write failure")

    with pytest.raises(FileExistsError):
        durable.capture(
            [],
            root=tmp_path,
            cell=CELL,
            seconds=1,
            reserve=reserve,
            popen=lambda *a, **k: spawned.append(True),
        )
    assert not spawned
    assert not durable.inspect(tmp_path, CELL)["terminal"]
    with pytest.raises(FileExistsError):
        durable.Journal(tmp_path, CELL)


def test_process_start_failure_has_terminal_sanitized_receipt(tmp_path):
    def fail(*args, **kwargs):
        raise OSError("invented private startup failure")

    result = durable.capture(
        [], root=tmp_path, cell=CELL, seconds=1, reserve=lambda: None, popen=fail
    )
    assert result["stop_code"] == "native_operation_failed"
    assert not result["process_started"] and result["cleanup_confirmed"]
    snapshot = durable.inspect(tmp_path, CELL)
    assert snapshot["terminal"]
    assert "private startup" not in json.dumps(snapshot)


@pytest.mark.parametrize(
    "change",
    [
        {"terminal": "true"},
        {"cleanup_confirmed": True},
        {"phase": "private unknown"},
        {"stdout_bytes": True},
        {"progress": {"private": "PRIVATE_SENTINEL"}},
        {"unexpected": "PRIVATE_SENTINEL"},
    ],
)
def test_corrupted_state_cannot_be_projected(tmp_path, change):
    journal = durable.Journal(tmp_path, CELL)
    journal.close()
    path = folder(tmp_path) / "state.json"
    state = json.loads(path.read_bytes())
    state.update(change)
    path.write_text(json.dumps(state))
    with pytest.raises(ValueError):
        durable.inspect(tmp_path, CELL)


@pytest.mark.parametrize(
    "raw",
    [b'{"terminal":false,"terminal":true}', b"x" * (durable.STATE_LIMIT + 1), b'{"terminal":NaN}'],
)
def test_duplicate_oversize_and_nonfinite_metadata_rejected(tmp_path, raw):
    journal = durable.Journal(tmp_path, CELL)
    journal.close()
    (folder(tmp_path) / "state.json").write_bytes(raw)
    with pytest.raises(ValueError):
        durable.inspect(tmp_path, CELL)


def test_rehashed_final_answer_still_requires_original_parser_and_process_receipt(tmp_path):
    run(tmp_path)
    directory = folder(tmp_path)
    original = (directory / "result.json").read_bytes()
    value = json.loads(original)
    value["answer"] = "yes"
    changed = json.dumps(value).encode()
    (directory / "result.json").write_bytes(changed)
    state = json.loads((directory / "state.json").read_bytes())
    state["result_sha256"] = hashlib.sha256(changed).hexdigest()
    (directory / "state.json").write_text(json.dumps(state))
    with pytest.raises(ValueError):
        durable.inspect(tmp_path, CELL)
    (directory / "result.json").write_bytes(original)
    state["result_sha256"] = hashlib.sha256(original).hexdigest()
    (directory / "state.json").write_text(json.dumps(state))
    (directory / "process-lease.json").unlink()
    with pytest.raises(FileNotFoundError):
        durable.inspect(tmp_path, CELL)


def test_tokens_must_match_frozen_observation_parser(tmp_path):
    run(tmp_path)
    directory = folder(tmp_path)
    value = json.loads((directory / "result.json").read_bytes())
    value["image_tokens_observed"] = 999
    raw = json.dumps(value).encode()
    (directory / "result.json").write_bytes(raw)
    state = json.loads((directory / "state.json").read_bytes())
    state["result_sha256"] = hashlib.sha256(raw).hexdigest()
    state["progress"]["image_tokens_observed"] = 999
    (directory / "state.json").write_text(json.dumps(state))
    with pytest.raises(ValueError):
        durable.inspect(tmp_path, CELL)

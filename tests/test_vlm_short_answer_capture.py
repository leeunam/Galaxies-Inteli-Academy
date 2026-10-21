"""Invented byte streams only; no native runtime or network."""

import io
import json
import socket

import pytest

from scripts import vlm_short_answer_capture as short

LOG = (
    b"encoding mtmd batch, n_chunks = 1 (done = 1, total = 3)\n"
    b"mtmd batch encoding done in 12 ms\n"
    b"decoding image batch 1/1, n_tokens_batch = 100\n"
    b"image decoded (batch 1/1) in 8 ms\n"
)


@pytest.fixture(autouse=True)
def no_native_or_network(monkeypatch):
    def forbidden(*a, **kw):
        raise AssertionError("native_or_network_forbidden")

    monkeypatch.setattr(short.base.subprocess, "Popen", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket, "getaddrinfo", forbidden)
    monkeypatch.setattr(short.base.os, "killpg", lambda *a: None)


def run(raw, stderr=LOG, code=0):
    class Fake:
        pid = 99999999
        returncode = code
        stdout = io.BytesIO(raw)

        def __init__(self):
            self.stderr = io.BytesIO(stderr)

        def poll(self):
            return code

        def wait(self, timeout=None):
            return code

    calls = []

    def factory(*args, **kwargs):
        assert calls == ["reserved"]
        return Fake()

    result = short.capture(
        ["invented"], seconds=1, reserve=lambda: calls.append("reserved"), popen=factory
    )
    assert calls == ["reserved"] and result["cleanup_confirmed"]
    return result


@pytest.mark.parametrize("answer", short.ANSWERS)
def test_valid_short_contract_uses_original_stdout_bytes(answer):
    raw = b" \n" + json.dumps({"answer": answer}).encode() + b"\t"
    result = run(raw)
    assert result["answer"] == answer and result["format_status"] == "valid"
    assert result["stop_code"] is None and result["image_tokens_observed"] == 100
    assert "native" not in result and "projected_value" not in result


@pytest.mark.parametrize(
    "raw",
    [
        b"",
        b'{"answer":"yes","answer":"yes"}',
        b'{"answer":true}',
        b'{"answer":"YES"}',
        b'{"answer":"unknown"}',
        b'{"answer":["yes"]}',
        b'{"answer":"yes","private":"PRIVATE_SENTINEL"}',
        b'["yes"]',
        b'prefix {"answer":"yes"}',
        b'{"answer":"yes"} suffix',
        b'```json\n{"answer":"yes"}\n```',
        b'{"answer":NaN}',
        b"\xff",
        b'{"item_configuration":"absent","state":"no_target","presented_categories":[]}',
    ],
)
def test_format_failure_is_an_outcome_without_repair_or_technical_stop(raw):
    result = run(raw)
    assert result["format_status"] == "invalid" and result["answer"] is None
    assert result["stop_code"] is None and result["image_encoder_and_decode_observed"]
    assert "PRIVATE_SENTINEL" not in json.dumps(result)
    assert result["raw_stdout_retained"] is result["raw_stderr_retained"] is False


def test_stderr_never_repairs_short_stdout():
    result = run(b"PRIVATE_SENTINEL", LOG + b'\n{"answer":"yes"}')
    assert result["format_status"] == "invalid" and result["answer"] is None
    assert "PRIVATE_SENTINEL" not in json.dumps(result)


@pytest.mark.parametrize(
    ("stderr", "code", "expected"),
    [
        (b"", 0, "diagnostics_insufficient"),
        (b"Failed to encode mtmd batch, res = -7\n", 1, "encoder_failed"),
        (LOG, 1, "native_failed_unknown_stage"),
    ],
)
def test_technical_failures_remain_terminal(stderr, code, expected):
    result = run(b'{"answer":"yes"}', stderr, code)
    assert result["stop_code"] == expected
    assert result["format_status"] == "not_assessed_technical_failure" and result["answer"] is None


def test_tee_is_byte_transparent_and_bounded():
    raw = b"x" * (short.base.LIMITS["stdout_bytes"] + 5)
    tee = short.Tee(io.BytesIO(raw))
    observed = b"".join(iter(lambda: tee.read(4096), b""))
    assert observed == raw and len(tee.data) == short.base.LIMITS["stdout_bytes"]
    tee.close()


def test_oversize_stdout_remains_terminal():
    result = run(b"x" * (short.base.LIMITS["stdout_bytes"] + 1))
    assert result["stop_code"] == "output_limit_or_unclosed_pipe"
    assert result["format_status"] == "not_assessed_technical_failure"

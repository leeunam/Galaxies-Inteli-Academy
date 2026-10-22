"""Owned tiny Python children only; no native runtime, image, model or network."""

import hashlib
import json
import os
import subprocess
import sys

import pytest

from scripts import visual_validation_capture_v1 as capture
from scripts.visual_validation_sidecar_v1 import build_sidecar

PNG = hashlib.sha256(b"invented-png-identity").hexdigest()


def response(kind):
    if kind == "relation":
        return {"answer": "yes"}
    if kind == "product_visible_early":
        return {"state": "no_target", "item_configuration": "absent", "presented_categories": []}
    return {kind: kind == "person_visible"}


def child(raw, *, tokens=240, tail="", complete=True):
    logs = (
        "encoding mtmd batch, n_chunks = 1 (done = 0, total = 1)\n"
        "mtmd batch encoding done in 1 ms\n"
        f"decoding image batch 1/1, n_tokens_batch = {tokens}\n"
    )
    if complete:
        logs += "image decoded (batch 1/1) in 1 ms\n"
    code = (
        f"import sys,time,os,signal;sys.stderr.write({logs!r});sys.stderr.flush();"
        f"sys.stdout.write({raw!r});sys.stdout.flush();" + tail
    )
    return [sys.executable, "-B", "-c", code]


def run(
    root,
    call_id=1,
    kind="person_visible",
    *,
    raw=None,
    tokens=240,
    complete=True,
    tail="",
    seconds=1,
):
    launches, reserved = [], []

    def launcher(argv, **kwargs):
        assert argv[:3] == [sys.executable, "-B", "-c"]
        process = subprocess.Popen(argv, **kwargs)
        launches.append(process)
        return process

    result = capture._capture_invented(
        child(
            json.dumps(response(kind)) if raw is None else raw,
            tokens=tokens,
            complete=complete,
            tail=tail,
        ),
        root=root,
        call_id=call_id,
        kind=kind,
        png_sha256=PNG,
        expected_tokens=240,
        reserve=lambda: reserved.append(True),
        launcher=launcher,
        seconds=seconds,
    )
    assert reserved == [True] and len(launches) == 1
    assert launches[0].poll() is not None
    with pytest.raises(ProcessLookupError):
        os.killpg(launches[0].pid, 0)
    return result


@pytest.mark.parametrize("kind", capture.KINDS)
def test_all_explicit_parsers_have_durable_capture_before_return(tmp_path, kind):
    result = run(tmp_path, kind=kind)
    assert result["technical_success"] and result["cleanup_confirmed"]
    assert result["image_tokens_observed"] == 240
    stored = capture.read_capture(tmp_path, 1, kind=kind, png_sha256=PNG, expected_tokens=240)
    assert stored["result"] == result
    with pytest.raises(FileExistsError):
        run(tmp_path, kind=kind)


@pytest.mark.parametrize(
    "raw",
    [
        'prefix {"person_visible":true}',
        '{"person_visible":true} suffix',
        '{"person_visible":true,"person_visible":false}',
        '{"person_visible":NaN}',
    ],
)
def test_no_repair_or_duplicate_or_nonfinite_acceptance(tmp_path, raw):
    result = run(tmp_path, raw=raw)
    assert not result["technical_success"] and result["stop_code"] == "attribute_schema_invalid"


@pytest.mark.parametrize("tokens,complete", [(239, True), (241, True), (240, False)])
def test_tokens_and_complete_encoder_remain_required(tmp_path, tokens, complete):
    assert not run(tmp_path, tokens=tokens, complete=complete)["technical_success"]


@pytest.mark.parametrize(
    "tail", ["time.sleep(5)", "os.kill(os.getppid(),signal.SIGTERM);time.sleep(5)"]
)
def test_timeout_or_cancel_keeps_owned_child_cleanup_and_irreversible_marker(tmp_path, tail):
    result = run(tmp_path, tail=tail, seconds=0.1)
    assert not result["technical_success"] and result["cleanup_confirmed"]
    with pytest.raises(FileExistsError):
        run(tmp_path)


def test_output_cap_is_a_failure_with_only_bounded_prefix_retained(tmp_path):
    result = run(tmp_path, raw="x" * 20000)
    assert not result["technical_success"]
    raw = tmp_path / "data/private" / capture.NAMESPACE / "captures/call-0001/stdout.bin"
    assert raw.stat().st_size == 16384


def test_no_authorization_or_source_activation_can_create_a_real_run(tmp_path):
    with pytest.raises(ValueError, match="authorization_required"):
        capture.dispatch(root=tmp_path)
    with pytest.raises(ValueError, match="technical_review_required"):
        capture.dispatch(root=tmp_path, authorization={"invented": True})
    with pytest.raises(ValueError, match="not_released"):
        capture.dispatch(root=tmp_path, authorization={"invented": True}, technical_review={})
    assert not list(tmp_path.iterdir())


def test_sidecar_binds_every_capture_preserves_temporal_evidence_and_never_releases(tmp_path):
    mapping = {}
    for i, kind in enumerate(capture.KINDS[:3], 1):
        run(tmp_path, call_id=i, kind=kind)
        mapping[kind] = {"call_id": i, "expected_tokens": 240}
    case = {
        "alias": "invented-case",
        "partition": "train",
        "media_sha256": PNG,
        "frame_seconds": [0.2],
        "frame_sha256": [PNG],
    }
    sidecar = build_sidecar(case, [mapping], root=tmp_path, candidate_sha256=PNG)
    assert sidecar["parsed"]["product_visible_early"] == {"value": False, "frames": [1]}
    assert sidecar["parsed"]["scene"] == {"value": "unknown", "frames": []}
    assert not sidecar["approved_for_training"] and sidecar["released_fields"] == []
    assert sidecar["quality_release_sha256"] is None
    assert sidecar["capture_origin"] == "injected_unreleased"
    assert sidecar["native_execution_verified"] is False
    assert sidecar["native_product_declarations"][0]["support_independently_reviewed"] is False
    case["partition"] = "test"
    with pytest.raises(ValueError, match="training_only"):
        build_sidecar(case, [mapping], root=tmp_path, candidate_sha256=PNG)


def test_durable_raw_tampering_and_swapped_binding_are_rejected(tmp_path):
    run(tmp_path)
    with pytest.raises(ValueError, match="binding_changed"):
        capture.read_capture(tmp_path, 1, kind="screen_text", png_sha256=PNG, expected_tokens=240)
    path = tmp_path / "data/private" / capture.NAMESPACE / "captures/call-0001/stdout.bin"
    path.write_bytes(b'{"person_visible":false}')
    with pytest.raises(ValueError, match="raw_changed"):
        capture.read_capture(
            tmp_path, 1, kind="person_visible", png_sha256=PNG, expected_tokens=240
        )


def test_cancellation_during_terminal_fsync_stops_the_caller(tmp_path, monkeypatch):
    original = capture.Journal.finish

    def finish(journal, result):
        stored = original(journal, result)
        os.kill(os.getpid(), __import__("signal").SIGTERM)
        return stored

    monkeypatch.setattr(capture.Journal, "finish", finish)
    with pytest.raises(KeyboardInterrupt):
        run(tmp_path)
    saved = capture.read_capture(
        tmp_path, 1, kind="person_visible", png_sha256=PNG, expected_tokens=240
    )
    assert saved["result"]["cleanup_confirmed"]
    with pytest.raises(FileExistsError):
        run(tmp_path)


def test_rehashed_wrong_numeric_type_is_not_accepted(tmp_path):
    run(tmp_path)
    folder = tmp_path / "data/private" / capture.NAMESPACE / "captures/call-0001"
    result = json.loads((folder / "result.json").read_bytes())
    result["runtime_seconds"] = True
    raw = json.dumps(result).encode()
    (folder / "result.json").write_bytes(raw)
    state = json.loads((folder / "state.json").read_bytes())
    state["result_sha256"] = hashlib.sha256(raw).hexdigest()
    (folder / "state.json").write_text(json.dumps(state))
    with pytest.raises(ValueError, match="result_types"):
        capture.read_capture(
            tmp_path, 1, kind="person_visible", png_sha256=PNG, expected_tokens=240
        )

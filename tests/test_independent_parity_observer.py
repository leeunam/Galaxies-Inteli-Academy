"""Invented values only: instrumentation preserves returned values and RNG state."""

import copy
import random
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import independent_parity_observer as observer
from scripts.candidate_features import CandidateFeatures
from scripts.training_manifest import PredictorInputs


def frame(file, name, **values):
    return SimpleNamespace(
        f_code=SimpleNamespace(co_filename="/invented/scripts/" + file, co_name=name),
        f_locals=values,
    )


@pytest.mark.parametrize("completed", [True, False])
def test_native_feature_gate_is_observed_without_substitution(monkeypatch, completed):
    rows = []
    monkeypatch.setattr(observer, "emit", rows.append)
    inputs = PredictorInputs(
        sector="beleza",
        duration_seconds=1.5,
        aspect_ratio_height_over_width=1.5,
        text_status="extracted",
        text_embedding=tuple([0.1234567890123456] * 384),
    )
    feature = CandidateFeatures(
        status="completed" if completed else "unavailable",
        reason_code=None if completed else "unsupported_language",
        inputs=inputs,
        extractor_config_sha256="a" * 64,
    )
    before = feature.model_dump_json()
    observer.observe(
        frame("candidate_features.py", "_extract_one", work=Path("/invented/0/beleza")),
        "return",
        feature,
    )
    assert feature.model_dump_json() == before
    assert rows[0]["status"] == feature.status and rows[0]["reason"] == feature.reason_code
    assert rows[0]["predictor_inputs_sha256"] == observer.semantic(inputs)


def test_audio_digest_reads_original_values_without_redecoding(monkeypatch):
    rows = []
    monkeypatch.setattr(observer, "emit", rows.append)
    audio = {
        "decoded_audio_float32_16khz_sha256": "b" * 64,
        "audio_status": "transcribed",
        "audio_rms": 0.125,
        "audio_duration_seconds": 1.5,
        "transcript": "Invented phrase",
        "speech_segments": [
            {
                "start": 0.0,
                "end": 1.25,
                "text": "Invented phrase",
                "avg_logprob": -0.1234567890123456,
                "no_speech_prob": 0.01234567890123456,
            }
        ],
        "asr_language": "pt",
        "asr_language_probability": 0.9876543210987654,
    }
    before = copy.deepcopy(audio)
    observer.observe(frame("audio_features.py", "extract_audio"), "return", audio)
    assert audio == before and rows[0]["digests"]["audio"] == "b" * 64
    assert rows[0]["digests"]["segments"] == observer.semantic(before["speech_segments"])


def test_observer_failure_and_exception_return_cannot_replace_model_output(monkeypatch):
    rows = []
    monkeypatch.setattr(observer, "emit", rows.append)
    returned = object()  # invented unsupported observation, not a model call
    assert (
        observer.observe(frame("experiment_a_artifact.py", "predict_views"), "return", returned)
        is None
    )
    assert rows[-1]["kind"] == "observation_error"
    observer.observe(frame("candidate_features.py", "_extract_one"), "return", None)
    assert rows[-1]["return_absent_or_exception"] is True


def test_reading_already_imported_generators_preserves_state():
    import numpy as np

    before = (random.getstate(), observer.semantic(np.random.get_state()))
    result = observer.state_snapshot()
    assert (random.getstate(), observer.semantic(np.random.get_state())) == before
    assert result["rng"]["python"] == observer.semantic(before[0])
    assert "ctranslate2_internal" in result["rng_unreadable"]


def test_subprocess_timeout_constructor_is_not_a_process_spawn(monkeypatch):
    import subprocess
    import sys

    rows = []
    monkeypatch.setattr(observer, "emit", rows.append)
    sys.setprofile(observer.observe)
    try:
        error = subprocess.TimeoutExpired("invented", 0.05)
    finally:
        sys.setprofile(None)
    assert error.timeout == 0.05 and rows == []


def test_native_input_binding_detects_swapped_prediction_inputs():
    from scripts.independent_parity_operator import verify_input_bindings

    rows = [
        {
            "function": "_extract_one",
            "event": "return",
            "position": i,
            "feature_sha256": str(i) * 64,
            "predictor_inputs_sha256": str(i + 3) * 64,
        }
        for i in range(3)
    ]
    rows.append(
        {
            "function": "extract_candidates",
            "event": "return",
            "feature_items_sha256": [str(i) * 64 for i in range(3)],
            "predictor_items_sha256": [str(i + 3) * 64 for i in range(3)],
        }
    )
    rows += [
        {"function": "predict_views", "event": "call", "input_items_sha256": [str(i + 3) * 64]}
        for i in range(3)
    ]
    verify_input_bindings(rows)
    rows[-1]["input_items_sha256"] = ["3" * 64]
    with pytest.raises(AssertionError):
        verify_input_bindings(rows)


def test_same_pid_startups_have_distinct_exclusive_traces(tmp_path):
    import os

    rng_before = random.getstate()
    first, generation_a = observer.open_trace(str(tmp_path), "invented", 123)
    second, generation_b = observer.open_trace(str(tmp_path), "invented", 123)
    try:
        os.write(first, b"first interpreter\n")
        os.write(second, b"second interpreter\n")
    finally:
        os.close(first)
        os.close(second)
    assert (generation_a, generation_b) == (0, 1)
    assert (tmp_path / "invented-123-0.jsonl").read_bytes() == b"first interpreter\n"
    assert (tmp_path / "invented-123-1.jsonl").read_bytes() == b"second interpreter\n"
    assert random.getstate() == rng_before

"""Invented sanitized timings only; no historical data, process, model or host reads."""

from copy import deepcopy

import pytest

from scripts.vlm_performance_comparison import compare


def fixture(*, completed=3, partial=False):
    events = [
        {"kind": "encoder_start", "values": [1, 1, 3]},
        {"kind": "encoder_done", "values": [100]},
    ]
    for index in range(1, completed + 1):
        events += [
            {"kind": "decode_start", "values": [index, 3, 128]},
            {"kind": "decode_done", "values": [index, 3, 10 * index]},
        ]
    if partial:
        events.append({"kind": "decode_start", "values": [completed + 1, 3, 128]})
    return {
        "input_sha256": "a" * 64,
        "command_sha256": "b" * 64,
        "observation": {
            "events": events,
            "runtime_seconds": 1.0,
            "stdout_bytes": 0,
            "cleanup_confirmed": True,
            "stop_code": "native_timeout" if partial else None,
        },
    }


def test_common_completed_work_excludes_pending_and_remaining_batches():
    old, new = fixture(), fixture(completed=2, partial=True)
    new["observation"]["events"][1]["values"] = [150]
    new["observation"]["events"][3]["values"][2] = 20
    new["observation"]["events"][5]["values"][2] = 40
    result = compare(old, new)
    assert result["encoder_ratio"] == pytest.approx(1.5)
    assert result["common_decode_reference_seconds"] == 0.03
    assert result["common_decode_candidate_seconds"] == 0.06
    assert result["common_decode_ratio"] == 2
    assert result["common_completed_tokens"] == 256
    assert result["candidate_phase"]["image_tokens_in_started_batches"] == 384
    assert result["candidate_phase"]["image_tokens_total_confirmed"] is None
    assert result["whole_capture_runtime_ratio"] is None
    assert result["historical_resource_cause_established"] is False
    assert result["new_execution_authorized"] is False


def test_complete_captures_allow_whole_runtime_ratio_without_causal_claim():
    old, new = fixture(), fixture()
    new["observation"]["runtime_seconds"] = 2
    result = compare(old, new)
    assert result["whole_capture_runtime_ratio"] == 2
    assert result["common_decode_ratio"] == 1
    assert result["historical_resource_cause_established"] is False


@pytest.mark.parametrize("key", ["input_sha256", "command_sha256"])
def test_different_input_or_effective_command_refuses_comparison(key):
    old, new = fixture(), fixture()
    new[key] = "c" * 64
    with pytest.raises(ValueError):
        compare(old, new)


@pytest.mark.parametrize(
    "change", ["tokens", "batch_total", "phase_order", "cleanup", "prefix_stdout"]
)
def test_incomparable_or_nonterminal_evidence_is_rejected(change):
    old, new = fixture(), fixture(completed=2, partial=True)
    observation = new["observation"]
    if change == "tokens":
        observation["events"][2]["values"][2] = 64
    elif change == "batch_total":
        for event in observation["events"]:
            if event["kind"].startswith("decode_"):
                event["values"][1] = 4
    elif change == "phase_order":
        observation["events"][2:4] = reversed(observation["events"][2:4])
    elif change == "cleanup":
        observation["cleanup_confirmed"] = False
    else:
        observation["stdout_bytes"] = 1
    with pytest.raises(ValueError):
        compare(old, new)


def test_zero_timer_rounding_never_creates_infinity():
    old, new = fixture(), fixture()
    old["observation"]["events"][1]["values"] = [0]
    for event in old["observation"]["events"]:
        if event["kind"] == "decode_done":
            event["values"][2] = 0
    result = compare(old, new)
    assert result["encoder_ratio"] is None and result["common_decode_ratio"] is None
    assert all(batch["ratio"] is None for batch in result["common_completed_batches"])


def test_timeout_before_encoder_has_no_invented_completed_work():
    old, new = fixture(), fixture(completed=0, partial=True)
    new["observation"]["events"] = []
    result = compare(old, new)
    assert result["encoder_ratio"] is None and result["common_decode_ratio"] is None
    assert result["common_completed_batches"] == []


def test_no_mutation_and_no_arbitrary_identity_text_is_projected():
    old, new = fixture(), fixture()
    before = deepcopy((old, new))
    compare(old, new)
    assert before == (old, new)
    new["input_sha256"] = old["input_sha256"] = "arbitrary text"
    with pytest.raises(ValueError):
        compare(old, new)


def test_incomplete_reference_is_not_a_completion_baseline():
    with pytest.raises(ValueError):
        compare(fixture(completed=1, partial=True), fixture())


def test_timeout_after_image_decode_still_has_no_whole_capture_ratio():
    old, new = fixture(), fixture()
    new["observation"]["stop_code"] = "native_timeout"
    result = compare(old, new)
    assert result["candidate_phase"]["image_decode_complete"]
    assert result["common_decode_ratio"] == 1
    assert result["whole_capture_runtime_ratio"] is None


def test_reference_timeout_after_decode_is_not_a_complete_capture_baseline():
    old, new = fixture(), fixture()
    old["observation"]["stop_code"] = "native_timeout"
    with pytest.raises(ValueError):
        compare(old, new)

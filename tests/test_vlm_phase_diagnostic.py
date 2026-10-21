"""Invented event sequences and argv only; no native process, media or network."""

import copy

import pytest

from scripts import vlm_phase_diagnostic as phase
from scripts import vlm_spatial_budget as spatial

ENCODER = [
    {"kind": "encoder_start", "values": [1, 1, 3]},
    {"kind": "encoder_done", "values": [10]},
]
IMAGE = ENCODER + [
    {"kind": "decode_start", "values": [1, 2, 128]},
    {"kind": "decode_done", "values": [1, 2, 3]},
    {"kind": "decode_start", "values": [2, 2, 17]},
    {"kind": "decode_done", "values": [2, 2, 4]},
]


def observation(events, *, stop="native_timeout", elapsed=0.050, stdout=0):
    return {
        "events": copy.deepcopy(events),
        "runtime_seconds": elapsed,
        "stop_code": stop,
        "stdout_bytes": stdout,
        "cleanup_confirmed": True,
    }


@pytest.mark.parametrize(
    "events,expected",
    [
        ([], "before_encoder_observation"),
        (ENCODER[:1], "image_encoder"),
        (ENCODER, "after_encoder_before_image_decode_observation"),
        (IMAGE[:3], "image_decode"),
        (IMAGE[:4], "image_decode"),
        (IMAGE[:5], "image_decode"),
        (IMAGE, "after_image_decode_not_further_localized"),
    ],
)
def test_timeout_localizes_observed_phase_without_inventing_the_missing_stage(events, expected):
    result = phase.diagnose(observation(events))
    assert result["last_observed_phase"] == expected
    assert not result["answer_quality_assessed"] and not result["new_execution_authorized"]
    if expected in (
        "image_encoder",
        "image_decode",
        "after_encoder_before_image_decode_observation",
    ):
        assert result["generation_limit_explains_timeout"] is False
    else:
        assert result["generation_limit_explains_timeout"] is None


def test_started_batch_tokens_never_become_completed_total():
    partial = phase.diagnose(observation(IMAGE[:-1]))
    assert partial["image_batches_started"] == 2 and partial["image_batches_completed"] == 1
    assert partial["image_tokens_in_started_batches"] == 145
    assert partial["image_tokens_in_completed_batches"] == 128
    assert partial["image_tokens_total_confirmed"] is None
    assert not partial["image_decode_complete"]
    assert partial["known_phase_seconds"] == 0.013
    assert partial["remaining_time_not_localized_seconds"] == pytest.approx(0.037)
    complete = phase.diagnose(observation(IMAGE))
    assert complete["image_tokens_total_confirmed"] == 145
    assert complete["known_phase_seconds"] == 0.017


def test_post_image_timeout_does_not_claim_generation_is_the_cause():
    result = phase.diagnose(observation(IMAGE, stdout=3))
    assert result["generation_limit_explains_timeout"] is None
    assert result["remaining_time_not_localized_seconds"] == pytest.approx(0.033)


def test_completed_capture_does_not_evaluate_answer_quality():
    value = observation(IMAGE, stop=None, stdout=12)
    value["answer"] = "PRIVATE_SENTINEL"
    result = phase.diagnose(value)
    assert result["termination"] == "completed" and result["image_decode_complete"]
    assert "PRIVATE_SENTINEL" not in str(result)


@pytest.mark.parametrize(
    "bad_events",
    [
        IMAGE[1:],
        IMAGE[::2],
        IMAGE + IMAGE,
        ENCODER + [IMAGE[-1]],
        ENCODER + [{"kind": "decode_start", "values": [2, 2, 128]}],
        IMAGE[:4] + [{"kind": "decode_start", "values": [2, 3, 17]}],
        IMAGE[:3] + [{"kind": "decode_done", "values": [2, 2, 3]}],
        [{"kind": "encoder_start", "values": [True, 1, 3]}],
        [{"kind": "encoder_start", "values": [1, 3, 1]}],
        [{"kind": "PRIVATE_SENTINEL", "values": [1]}],
        ENCODER + [{"kind": "decode_start", "values": [1, 1, 0]}],
    ],
)
def test_broken_or_fabricated_stage_prefix_fails_closed(bad_events):
    with pytest.raises(phase.InvalidPhaseEvidence, match="^invalid_phase_evidence$"):
        phase.diagnose(observation(bad_events))


@pytest.mark.parametrize(
    "change",
    [
        {"runtime_seconds": -1},
        {"runtime_seconds": float("nan")},
        {"runtime_seconds": True},
        {"runtime_seconds": 0.001},
        {"cleanup_confirmed": False},
        {"stop_code": "output_limit_or_unclosed_pipe"},
        {"stdout_bytes": True},
        {"events": "PRIVATE_SENTINEL"},
    ],
)
def test_truncated_collection_or_inconsistent_duration_has_no_phase_conclusion(change):
    with pytest.raises(phase.InvalidPhaseEvidence):
        phase.diagnose(observation(IMAGE) | change)


def test_empty_prefix_is_not_zero_encoder_time_or_success():
    result = phase.diagnose(observation([]))
    assert result["encoder_seconds_reported"] is None
    assert result["image_tokens_total_confirmed"] is None
    with pytest.raises(phase.InvalidPhaseEvidence):
        phase.diagnose(observation([], stop=None))
    with pytest.raises(phase.InvalidPhaseEvidence):
        phase.diagnose(observation(IMAGE[:-1], stdout=12))


def test_effective_command_replaces_inherited_contract_before_use():
    inherited = [
        "invented-runtime",
        "-m",
        "invented-model",
        "--mmproj",
        "invented-projector",
        "--n-gpu-layers",
        "0",
        "--no-mmproj-offload",
        "--ctx-size",
        "3072",
        "--n-predict",
        "64",
        "--threads",
        "4",
        "--threads-batch",
        "4",
        "--batch-size",
        "128",
        "--ubatch-size",
        "128",
        "--image-min-tokens",
        "64",
        "--image-max-tokens",
        "128",
        "--temp",
        "0",
        "--seed",
        "42",
        "--verbosity",
        "0",
        "--image",
        "<PNG>",
        "--prompt",
        "INVENTED OLD LONG CONTRACT",
        "--json-schema-file",
        "<SCHEMA>",
    ]
    original = list(inherited)
    effective = spatial.command(inherited, "invented.png", "invented-schema.json")
    assert inherited == original
    assert "INVENTED OLD LONG CONTRACT" not in effective
    assert effective[effective.index("--prompt") + 1] == spatial.prior.PROMPT
    assert effective[effective.index("--image") + 1] == "invented.png"
    assert effective[effective.index("--json-schema-file") + 1] == "invented-schema.json"
    assert spatial.prior.SCHEMA["properties"] == {"answer": {"enum": ["yes", "no", "uncertain"]}}
    for flag, expected in [
        ("--n-predict", "64"),
        ("--ctx-size", "3072"),
        ("--batch-size", "128"),
        ("--ubatch-size", "128"),
        ("--image-min-tokens", "1024"),
        ("--image-max-tokens", "1024"),
        ("--verbosity", "4"),
    ]:
        assert effective.count(flag) == 1 and effective[effective.index(flag) + 1] == expected
    assert not {"--ignore-eos", "--jinja", "--chat-template", "--reverse-prompt"} & set(effective)

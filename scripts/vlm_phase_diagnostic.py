"""Read-only phase diagnosis from terminal, bounded single-image mtmd events.

No launcher, queue, budget, model or acceptance gate is changed. Durations label
reported intervals; the remainder is not attributed to generation or overhead.
"""

import math


class InvalidPhaseEvidence(ValueError):
    def __init__(self):
        super().__init__("invalid_phase_evidence")


def require(condition):
    if not condition:
        raise InvalidPhaseEvidence


def diagnose(observation):
    """Classify only successful captures or clean technical timeouts.

    Input must already come from a verified terminal capture, with complete
    bounded stderr collection. Prefixes of *image processing* are valid evidence
    of an interrupted stage; incomplete journal files are not inputs here.
    """
    require(type(observation) is dict)
    events = observation.get("events")
    elapsed = observation.get("runtime_seconds")
    stop = observation.get("stop_code")
    require(type(events) is list and len(events) <= 4096)
    require(type(elapsed) in (int, float) and math.isfinite(elapsed) and elapsed >= 0)
    require(stop in (None, "native_timeout") and observation.get("cleanup_confirmed") is True)
    require(type(observation.get("stdout_bytes")) is int and observation["stdout_bytes"] >= 0)

    phase = "before_encoder_observation"
    encoder_ms = None
    completed_ms = 0
    started_batches = completed_batches = 0
    started_tokens = completed_tokens = 0
    total_batches = pending = None
    lengths = {"encoder_start": 3, "encoder_done": 1, "decode_start": 3, "decode_done": 3}
    for event in events:
        require(type(event) is dict and set(event) == {"kind", "values"})
        kind, values = event["kind"], event["values"]
        require(type(kind) is str and kind in lengths)
        require(type(values) is list and len(values) == lengths[kind])
        require(all(type(value) is int and 0 <= value <= 10000000 for value in values))
        if kind == "encoder_start":
            require(phase == "before_encoder_observation" and values[0] == 1)
            require(values[1] <= values[2] and values[2] > 0)
            phase = "image_encoder"
        elif kind == "encoder_done":
            require(phase == "image_encoder")
            encoder_ms = values[0]
            phase = "after_encoder_before_image_decode_observation"
        elif kind == "decode_start":
            require(encoder_ms is not None and pending is None)
            require(phase in ("after_encoder_before_image_decode_observation", "image_decode"))
            index, total, tokens = values
            require(index == started_batches + 1 and index <= total and tokens > 0)
            require(total_batches is None or total_batches == total)
            total_batches = total
            pending = values
            started_batches += 1
            started_tokens += tokens
            phase = "image_decode"
        else:
            require(phase == "image_decode" and pending is not None)
            require(values[:2] == pending[:2])
            completed_batches += 1
            completed_tokens += pending[2]
            completed_ms += values[2]
            pending = None
            if completed_batches == total_batches:
                phase = "after_image_decode_not_further_localized"

    complete = total_batches is not None and completed_batches == total_batches
    # A technical success cannot claim complete image processing from a prefix.
    require(stop is not None or complete)
    # In this pinned single-turn runtime, answer generation follows eval_message;
    # an unfinished image plus answer bytes is inconsistent evidence for this diagnosis.
    if not complete:
        require(observation["stdout_bytes"] == 0)
    known_seconds = ((encoder_ms or 0) + completed_ms) / 1000
    # Each runtime timer is rounded to integer milliseconds. Do not turn a
    # contradictory duration into a negative or invented remaining budget.
    rounding_seconds = (completed_batches + int(encoder_ms is not None)) / 1000
    require(known_seconds <= elapsed + rounding_seconds)
    before_generation = phase in (
        "image_encoder",
        "after_encoder_before_image_decode_observation",
        "image_decode",
    )
    return {
        "schema": "vlm-terminal-phase-diagnostic-v1",
        "termination": "timeout" if stop == "native_timeout" else "completed",
        "last_observed_phase": phase,
        "encoder_seconds_reported": None if encoder_ms is None else encoder_ms / 1000,
        "image_decode_seconds_completed": completed_ms / 1000,
        "image_batches_started": started_batches,
        "image_batches_completed": completed_batches,
        "image_batches_total_announced": total_batches,
        "image_tokens_in_started_batches": started_tokens,
        "image_tokens_in_completed_batches": completed_tokens,
        "image_tokens_total_confirmed": completed_tokens if complete else None,
        "image_decode_complete": complete,
        "known_phase_seconds": known_seconds,
        "runtime_seconds": elapsed,
        "remaining_time_not_localized_seconds": max(0.0, elapsed - known_seconds),
        "generation_limit_explains_timeout": False
        if stop == "native_timeout" and before_generation
        else None,
        "answer_quality_assessed": False,
        "new_execution_authorized": False,
    }

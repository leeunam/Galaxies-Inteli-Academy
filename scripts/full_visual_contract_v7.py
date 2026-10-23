"""Structural contract for synthetic seven-field VLM sidecars.

This module never certifies perceptual content. Its outputs remain unreleased.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any

from scripts.channel_partitions import ExperimentError
from scripts.visual_attributes import FIELDS, FORMATS, SCENES

SCHEMA_VERSION = "front1-seven-field-sidecar-v7"
DATA_KIND_SYNTHETIC = "synthetic"
DATA_KIND_OBSERVED_UNRELEASED = "observed_unreleased"
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_CREATIVE_DURATION_SECONDS = 60.0
IDENTITY_KEYS = (
    "cohort_sha256",
    "partition_sha256",
    "configuration_sha256",
    "candidate_sha256",
)
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
IDENTIFIER_RE = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
BOOLEAN_FIELDS = frozenset(FIELDS[:5])
ATTRIBUTE_KEYS = frozenset(FIELDS)
SIDECAR_KEYS = {
    "schema_version",
    "data_kind",
    "sample_id",
    "partition",
    "channel_id",
    "identities",
    "input_frame_seconds",
    "input_frame_sha256",
    "attributes",
    "quality_accepted",
    "release_emitted",
}


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ExperimentError(code)


def is_sha256(value: Any) -> bool:
    return type(value) is str and SHA256_RE.fullmatch(value) is not None


def is_identifier(value: Any) -> bool:
    return type(value) is str and IDENTIFIER_RE.fullmatch(value) is not None


def _pairs_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        require(key not in result, "v7_duplicate_json_key")
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    raise ExperimentError("v7_nonfinite_json_value")


def parse_json(raw: bytes | str) -> Any:
    require(type(raw) in (bytes, str), "v7_json_type_invalid")
    try:
        byte_count = len(raw) if type(raw) is bytes else len(raw.encode("utf-8"))
        require(byte_count <= MAX_JSON_BYTES, "v7_json_too_large")
        return json.loads(
            raw,
            object_pairs_hook=_pairs_no_duplicates,
            parse_constant=_reject_constant,
        )
    except ExperimentError:
        raise
    except (UnicodeError, ValueError, RecursionError, OverflowError):
        raise ExperimentError("v7_json_invalid") from None


def _identity_map(value: Any) -> dict[str, str]:
    require(type(value) is dict and set(value) == set(IDENTITY_KEYS), "v7_identities_invalid")
    require(all(is_sha256(value[key]) for key in IDENTITY_KEYS), "v7_identities_invalid")
    return dict(value)


def _timeline(seconds: Any, hashes: Any) -> tuple[tuple[float, ...], tuple[str, ...]]:
    require(
        type(seconds) is list and 1 <= len(seconds) <= 4,
        "v7_frame_count_invalid",
    )
    require(type(hashes) is list and len(hashes) == len(seconds), "v7_frame_hash_count_invalid")
    require(all(_valid_second(value) for value in seconds), "v7_frame_time_invalid")
    require(seconds == sorted(set(seconds)), "v7_frame_time_order_invalid")
    require(all(is_sha256(value) for value in hashes), "v7_frame_hash_invalid")
    return tuple(float(value) for value in seconds), tuple(hashes)


def _valid_second(value: Any) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value) and 0 <= value <= MAX_CREATIVE_DURATION_SECONDS
    except OverflowError:
        return False


def _normalize_value(field: str, value: Any) -> str:
    if field in BOOLEAN_FIELDS:
        require(type(value) is bool or value == "unknown", "v7_boolean_value_invalid")
        return "unknown" if value == "unknown" else ("true" if value else "false")
    choices = SCENES if field == "scene" else FORMATS
    require(type(value) is str and value in choices, "v7_enum_value_invalid")
    return value


def _checked_attributes(attributes: Any, seconds: tuple[float, ...]) -> dict[str, str]:
    require(type(attributes) is dict and set(attributes) == ATTRIBUTE_KEYS, "v7_attributes_invalid")
    normalized = {}
    for field in FIELDS:
        evidence = attributes[field]
        require(
            type(evidence) is dict and set(evidence) == {"value", "frames"},
            "v7_attribute_evidence_invalid",
        )
        value = _normalize_value(field, evidence["value"])
        frames = evidence["frames"]
        require(type(frames) is list, "v7_frame_evidence_invalid")
        require(
            all(type(frame) is int and 1 <= frame <= len(seconds) for frame in frames),
            "v7_frame_evidence_invalid",
        )
        require(len(frames) == len(set(frames)), "v7_duplicate_frame_evidence")
        if value == "unknown":
            require(frames == [], "v7_unknown_must_not_claim_frames")
        else:
            require(bool(frames), "v7_known_value_requires_frames")
        if field == "product_visible_early":
            require(
                all(seconds[frame - 1] <= 3 for frame in frames),
                "v7_early_product_frame_after_three_seconds",
            )
        normalized[field] = value
    return normalized


@dataclass(frozen=True)
class CheckedSidecarV7:
    sample_id: str
    partition: str
    channel_id: str
    data_kind: str
    identities: dict[str, str]
    frame_seconds: tuple[float, ...]
    frame_sha256: tuple[str, ...]
    attributes: dict[str, str]
    quality_accepted: bool = False
    release_emitted: bool = False


def check_sidecar_v7(
    value: Any,
    *,
    expected_sample_id: str | None = None,
    expected_partition: str | None = None,
    expected_channel_id: str | None = None,
    expected_identities: dict[str, str] | None = None,
) -> CheckedSidecarV7:
    """Check one declaration structurally; the result is never a quality release."""
    if type(value) in (bytes, str):
        value = parse_json(value)
    require(type(value) is dict and set(value) == SIDECAR_KEYS, "v7_sidecar_shape_invalid")
    require(
        type(value["schema_version"]) is str and value["schema_version"] == SCHEMA_VERSION,
        "v7_sidecar_schema_mismatch",
    )
    require(
        type(value["data_kind"]) is str
        and value["data_kind"] in (DATA_KIND_SYNTHETIC, DATA_KIND_OBSERVED_UNRELEASED),
        "v7_data_kind_invalid",
    )
    require(
        type(value["quality_accepted"]) is bool and value["quality_accepted"] is False,
        "v7_quality_must_remain_unreleased",
    )
    require(
        type(value["release_emitted"]) is bool and value["release_emitted"] is False,
        "v7_quality_must_remain_unreleased",
    )
    require(value["release_emitted"] is False, "v7_release_must_remain_unreleased")
    require(is_identifier(value["sample_id"]), "v7_sample_id_invalid")
    require(
        type(value["partition"]) is str and value["partition"] in ("train", "validation"),
        "v7_partition_invalid",
    )
    require(is_identifier(value["channel_id"]), "v7_channel_id_invalid")
    require(
        expected_sample_id is None or value["sample_id"] == expected_sample_id,
        "v7_sample_id_mismatch",
    )
    require(
        expected_partition is None or value["partition"] == expected_partition,
        "v7_partition_mismatch",
    )
    require(
        expected_channel_id is None or value["channel_id"] == expected_channel_id,
        "v7_channel_id_mismatch",
    )
    identities = _identity_map(value["identities"])
    require(
        expected_identities is None or identities == expected_identities,
        "v7_identity_mismatch",
    )
    seconds, hashes = _timeline(value["input_frame_seconds"], value["input_frame_sha256"])
    attributes = _checked_attributes(value["attributes"], seconds)
    return CheckedSidecarV7(
        sample_id=value["sample_id"],
        partition=value["partition"],
        channel_id=value["channel_id"],
        data_kind=value["data_kind"],
        identities=identities,
        frame_seconds=seconds,
        frame_sha256=hashes,
        attributes=attributes,
    )


def make_synthetic_sidecar(
    *,
    sample_id: str,
    partition: str,
    channel_id: str,
    identities: dict[str, str],
    frame_seconds: list[float],
    frame_sha256: list[str],
    attributes: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Small-fixture helper; the explicit synthetic kind can never be promoted."""
    value = {
        "schema_version": SCHEMA_VERSION,
        "data_kind": DATA_KIND_SYNTHETIC,
        "sample_id": sample_id,
        "partition": partition,
        "channel_id": channel_id,
        "identities": dict(identities),
        "input_frame_seconds": list(frame_seconds),
        "input_frame_sha256": list(frame_sha256),
        "attributes": attributes,
        "quality_accepted": False,
        "release_emitted": False,
    }
    check_sidecar_v7(value)
    return value


def normalize_attributes(value: Any, **expected: Any) -> dict[str, str]:
    """Return canonical strings for all seven fields after structural checks."""
    checked = check_sidecar_v7(value, **expected)
    require(checked.data_kind == DATA_KIND_SYNTHETIC, "v7_synthetic_input_required")
    return dict(checked.attributes)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

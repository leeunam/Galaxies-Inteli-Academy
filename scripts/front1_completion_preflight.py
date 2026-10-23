"""Read-only structural preflight for the original seven-field VLM contract.

This module checks metadata consistency only. It never establishes perception
quality, authenticates actors, creates a quality release, or authorizes work.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

from scripts.visual_attributes import FIELDS as REQUIRED_FIELDS

SCHEMA = "front1-completion-prerequisites-v1"
MAX_PACKAGE_BYTES = 2 * 1024 * 1024
HASH_RE = re.compile(r"[0-9a-f]{64}\Z")
OPAQUE_ID_RE = re.compile(r"[A-Za-z0-9_.:-]{1,128}\Z")
IDENTITY_KEYS = (
    "cohort_sha256",
    "partition_sha256",
    "configuration_sha256",
    "candidate_sha256",
    "release_sha256",
    "plan_sha256",
    "audit_sha256",
    "annotations_sha256",
    "selection_sha256",
)
SIDECAR_IDENTITY_KEYS = (
    "cohort_sha256",
    "partition_sha256",
    "configuration_sha256",
    "candidate_sha256",
    "release_sha256",
)
REVIEW_BOUND_KEYS = (
    *IDENTITY_KEYS,
    "exclusions_sha256",
    "audit_predictions_sha256",
    "gate_sha256",
)
PACKAGE_KEYS = {
    "schema",
    "required_fields",
    "released_fields",
    "identities",
    "training_ids",
    "validation_ids",
    "sidecars",
    "audit_rows",
    "exclusions_sha256",
    "audit_predictions_sha256",
    "gate_sha256",
    "independent_review",
}
REVIEW_KEYS = {
    "creator_id",
    "annotator_id",
    "reviewer_id",
    "origin_evidence_sha256",
    "annotations_sealed_before_predictions",
    "annotations_sealed_epoch",
    "predictions_revealed_epoch",
    "reviewed_epoch",
    "bound_sha256",
}


class _InvalidPackage(Exception):
    def __init__(self, code: str):
        self.code = code


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise _InvalidPackage(code)


def _sha(value: Any) -> bool:
    return isinstance(value, str) and HASH_RE.fullmatch(value) is not None


def _opaque_id(value: Any) -> bool:
    return isinstance(value, str) and OPAQUE_ID_RE.fullmatch(value) is not None


def _exact_keys(value: Any, keys: set[str], code: str) -> dict[str, Any]:
    _require(type(value) is dict and set(value) == keys, code)
    return value


def _ordered_unique_strings(value: Any, allowed: tuple[str, ...], code: str) -> tuple[str, ...]:
    _require(type(value) is list, code)
    _require(all(type(item) is str for item in value), code)
    result = tuple(value)
    _require(len(result) == len(set(result)), code)
    _require(result == tuple(field for field in allowed if field in set(result)), code)
    _require(set(result) <= set(allowed), code)
    return result


def _identity_map(value: Any, *, keys: tuple[str, ...], code: str) -> dict[str, str]:
    identities = _exact_keys(value, set(keys), code)
    _require(all(_sha(identities[key]) for key in keys), code)
    return identities


def _validate_split_ids(package: dict[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    training = package["training_ids"]
    validation = package["validation_ids"]
    _require(type(training) is list and len(training) == 203, "training_ids_count")
    _require(type(validation) is list and len(validation) == 66, "validation_ids_count")
    _require(all(_opaque_id(item) for item in training), "training_ids_invalid")
    _require(all(_opaque_id(item) for item in validation), "validation_ids_invalid")
    train_ids, validation_ids = tuple(training), tuple(validation)
    _require(len(set(train_ids)) == 203, "training_ids_duplicate")
    _require(len(set(validation_ids)) == 66, "validation_ids_duplicate")
    _require(not set(train_ids).intersection(validation_ids), "split_ids_overlap")
    return train_ids, validation_ids


def _validate_sidecars(
    rows: Any,
    training_ids: tuple[str, ...],
    validation_ids: tuple[str, ...],
    identities: dict[str, str],
) -> None:
    _require(type(rows) is list and len(rows) == 269, "sidecars_count")
    expected_partitions = {sample: "train" for sample in training_ids}
    expected_partitions.update({sample: "validation" for sample in validation_ids})
    observed = []
    sidecar_keys = {
        "sample_id",
        "partition",
        "sector",
        "channel_id",
        "features_sha256",
        "run_sha256",
        "identities",
    }
    for row in rows:
        row = _exact_keys(row, sidecar_keys, "sidecar_shape")
        sample_id, partition = row["sample_id"], row["partition"]
        _require(_opaque_id(sample_id), "sidecar_sample_id_invalid")
        _require(partition in ("train", "validation"), "sidecar_partition_invalid")
        _require(row["sector"] in ("moda", "beleza"), "sidecar_sector_invalid")
        _require(_opaque_id(row["channel_id"]), "sidecar_channel_id_invalid")
        _require(_sha(row["features_sha256"]) and _sha(row["run_sha256"]), "sidecar_hash_invalid")
        sidecar_ids = _identity_map(
            row["identities"], keys=SIDECAR_IDENTITY_KEYS, code="sidecar_identity_shape"
        )
        _require(
            all(sidecar_ids[key] == identities[key] for key in SIDECAR_IDENTITY_KEYS),
            "sidecar_identity_mismatch",
        )
        observed.append((sample_id, partition))
    _require(len({sample for sample, _ in observed}) == 269, "sidecar_duplicate")
    _require({sample for sample, _ in observed} == set(expected_partitions), "sidecar_membership")
    _require(
        all(expected_partitions[sample] == partition for sample, partition in observed),
        "sidecar_partition_mismatch",
    )


def _validate_audit_rows(
    rows: Any,
    training_ids: tuple[str, ...],
    identities: dict[str, str],
    sidecars_by_id: dict[str, dict[str, Any]],
) -> None:
    _require(type(rows) is list and len(rows) == 32, "audit_rows_count")
    keys = {
        "sample_id",
        "partition",
        "sector",
        "channel_id",
        "features_sha256",
        "annotation_sha256",
        "release_sha256",
    }
    samples, channels, sectors, metadata_rows = [], [], [], []
    for row in rows:
        row = _exact_keys(row, keys, "audit_row_shape")
        _require(_opaque_id(row["sample_id"]), "audit_sample_id_invalid")
        _require(row["partition"] == "train", "audit_not_training_only")
        _require(_opaque_id(row["channel_id"]), "audit_channel_id_invalid")
        _require(row["sector"] in ("moda", "beleza"), "audit_sector_invalid")
        _require(
            _sha(row["features_sha256"]) and _sha(row["annotation_sha256"]), "audit_hash_invalid"
        )
        _require(row["release_sha256"] == identities["release_sha256"], "audit_release_mismatch")
        sidecar = sidecars_by_id.get(row["sample_id"])
        _require(
            sidecar is not None
            and sidecar["features_sha256"] == row["features_sha256"]
            and sidecar["sector"] == row["sector"]
            and sidecar["channel_id"] == row["channel_id"],
            "audit_sidecar_binding_mismatch",
        )
        samples.append(row["sample_id"])
        channels.append(row["channel_id"])
        sectors.append(row["sector"])
        metadata_rows.append({key: row[key] for key in sorted(keys)})
    _require(len(set(samples)) == 32, "audit_sample_duplicate")
    _require(set(samples) <= set(training_ids), "audit_sample_outside_training")
    _require(len(set(channels)) == 32, "audit_channel_duplicate")
    _require(sectors.count("moda") == 16 and sectors.count("beleza") == 16, "audit_sector_counts")
    _require(
        _metadata_digest(metadata_rows) == identities["audit_sha256"], "audit_identity_mismatch"
    )
    annotations = [
        {"sample_id": row["sample_id"], "annotation_sha256": row["annotation_sha256"]}
        for row in rows
    ]
    _require(
        _metadata_digest(annotations) == identities["annotations_sha256"],
        "annotation_identity_mismatch",
    )


def _metadata_digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


def _validate_review(package: dict[str, Any], identities: dict[str, str]) -> None:
    review = _exact_keys(package["independent_review"], REVIEW_KEYS, "independent_review_shape")
    actors = (review["creator_id"], review["annotator_id"], review["reviewer_id"])
    _require(all(_opaque_id(actor) for actor in actors), "independent_review_actor_invalid")
    _require(len(set(actors)) == 3, "independent_review_actors_not_distinct")
    _require(_sha(review["origin_evidence_sha256"]), "independent_origin_evidence_missing")
    _require(
        review["annotations_sealed_before_predictions"] is True, "annotations_not_sealed_blindly"
    )
    times = (
        review["annotations_sealed_epoch"],
        review["predictions_revealed_epoch"],
        review["reviewed_epoch"],
    )
    _require(
        all(type(value) in (int, float) and math.isfinite(value) for value in times),
        "review_timestamps_invalid",
    )
    _require(times[0] < times[1] < times[2], "review_temporal_order_invalid")
    bound = _identity_map(
        review["bound_sha256"], keys=REVIEW_BOUND_KEYS, code="independent_review_binding_shape"
    )
    expected = {key: identities[key] for key in IDENTITY_KEYS}
    expected.update(
        exclusions_sha256=package["exclusions_sha256"],
        audit_predictions_sha256=package["audit_predictions_sha256"],
        gate_sha256=package["gate_sha256"],
    )
    _require(bound == expected, "independent_review_binding_mismatch")


def evaluate_completion_prerequisites(package: dict[str, Any]) -> dict[str, Any]:
    """Return structural blockers; even a complete metadata packet accepts no quality."""
    blockers: list[str] = []
    required = tuple(REQUIRED_FIELDS)
    released: tuple[str, ...] = ()
    identities: dict[str, str] = {}
    missing = list(required)
    try:
        package = _exact_keys(package, PACKAGE_KEYS, "package_shape")
        _require(package["schema"] == SCHEMA, "schema_version_mismatch")
        required = _ordered_unique_strings(
            package["required_fields"], REQUIRED_FIELDS, "required_fields_invalid"
        )
        _require(required == tuple(REQUIRED_FIELDS), "required_fields_incomplete")
        released = _ordered_unique_strings(
            package["released_fields"], required, "released_fields_invalid"
        )
        missing = [field for field in required if field not in released]
        identities = _identity_map(
            package["identities"], keys=IDENTITY_KEYS, code="identities_invalid"
        )
        for key in ("exclusions_sha256", "audit_predictions_sha256", "gate_sha256"):
            _require(_sha(package[key]), f"{key}_invalid")
        train_ids, validation_ids = _validate_split_ids(package)
        _validate_sidecars(package["sidecars"], train_ids, validation_ids, identities)
        sidecars_by_id = {row["sample_id"]: row for row in package["sidecars"]}
        _validate_audit_rows(package["audit_rows"], train_ids, identities, sidecars_by_id)
        _validate_review(package, identities)
        if missing:
            blockers.append("required_fields_not_released")
    except _InvalidPackage as error:
        blockers.append(error.code)
    status = "prerequisites_present" if not blockers and not missing else "blocked"
    return {
        "schema": SCHEMA,
        "status": status,
        "required_fields": list(required),
        "released_fields": list(released),
        "missing_fields": missing,
        "blockers": blockers,
        "quality_accepted": False,
        "quality_release_emitted": False,
        "native_execution_authorized": False,
        "holdout_authorized": False,
        "independent_origin_verified": False,
        "front1_complete": False,
    }


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise _InvalidPackage("duplicate_json_key")
        result[key] = value
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        raw = args.package.read_bytes()
        _require(len(raw) <= MAX_PACKAGE_BYTES, "package_too_large")
        package = json.loads(raw.decode("utf-8"), object_pairs_hook=_strict_object)
        result = evaluate_completion_prerequisites(package)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result["status"] == "prerequisites_present" else 2
    except _InvalidPackage as error:
        result = evaluate_completion_prerequisites({})
        result["blockers"] = [error.code]
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 2
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError):
        result = evaluate_completion_prerequisites({})
        result["blockers"] = ["package_read_failed"]
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

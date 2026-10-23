"""Synthetic, source-bound seven-field data path; never a quality release.

The cached-B import is deliberately lazy. Observed caches are rejected before
their validator, target-bearing objects, index, or sidecar paths are touched.
"""

from __future__ import annotations

import hashlib
import math
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError, model_validator

from scripts.channel_partitions import ExperimentError, FrozenContract, digest
from scripts.full_visual_contract_v7 import (
    DATA_KIND_OBSERVED_UNRELEASED,
    DATA_KIND_SYNTHETIC,
    FIELDS,
    IDENTITY_KEYS,
    MAX_CREATIVE_DURATION_SECONDS,
    check_sidecar_v7,
    is_identifier,
    is_sha256,
    parse_json,
    require,
)
from scripts.full_visual_contract_v7 import (
    SCHEMA_VERSION as SIDECAR_SCHEMA,
)
from scripts.visual_attributes import FIELDS as CANONICAL_FIELDS

SCHEMA_VERSION = "front1-seven-field-data-v7-manifest-v1"
INDEX_SCHEMA_VERSION = "front1-seven-field-sidecar-index-v1"
RUN_SCHEMA_VERSION = "front1-seven-field-run-v7"
B_REPRESENTATION = "b_cached_clip_audio_905_v1_no_vlm_no_imputation"
MAX_METADATA_BYTES = 2 * 1024 * 1024
MANIFEST_KEYS = {
    "schema_version",
    "data_kind",
    "identities",
    "source_versions",
    "index_ref",
    "index_sha256",
    "split_sha256",
    "quality_accepted",
    "release_emitted",
}
INDEX_KEYS = {"schema_version", "data_kind", "entries", "quality_accepted", "release_emitted"}
INDEX_ENTRY_KEYS = {
    "sample_id",
    "partition",
    "channel_id",
    "features_ref",
    "run_ref",
    "features_sha256",
    "run_sha256",
}
RUN_KEYS = {
    "schema_version",
    "data_kind",
    "sample_id",
    "partition",
    "channel_id",
    "identities",
    "status",
    "temporary_directory_removed",
    "features_sha256",
    "quality_accepted",
    "release_emitted",
}


def _b_contract():
    """Import the historical B module only after the synthetic boundary passes."""
    from scripts import experiment_b_data

    return experiment_b_data


def source_versions() -> dict[str, str]:
    root = Path(__file__).resolve().parents[1]
    script_hashes = {}
    for name in (
        "channel_partitions.py",
        "experiment_a_data.py",
        "experiment_b_data.py",
        "training_manifest.py",
        "empirical_baseline.py",
        "visual_attributes.py",
        "full_visual_contract_v7.py",
        "full_visual_data_v7.py",
    ):
        raw = (root / "scripts" / name).read_bytes()
        script_hashes[name] = hashlib.sha256(raw).hexdigest()
    return {
        "manifest_schema": SCHEMA_VERSION,
        "sidecar_schema": SIDECAR_SCHEMA,
        "run_schema": RUN_SCHEMA_VERSION,
        "b_representation": B_REPRESENTATION,
        "channel_partitions.py_sha256": script_hashes["channel_partitions.py"],
        "experiment_a_data.py_sha256": script_hashes["experiment_a_data.py"],
        "experiment_b_data.py_sha256": script_hashes["experiment_b_data.py"],
        "training_manifest.py_sha256": script_hashes["training_manifest.py"],
        "empirical_baseline.py_sha256": script_hashes["empirical_baseline.py"],
        "visual_attributes.py_sha256": script_hashes["visual_attributes.py"],
        "full_visual_contract_v7.py_sha256": script_hashes["full_visual_contract_v7.py"],
        "full_visual_data_v7.py_sha256": script_hashes["full_visual_data_v7.py"],
        "canonical_fields_sha256": digest(list(CANONICAL_FIELDS)),
    }


class V7Manifest(FrozenContract):
    schema_version: Literal["front1-seven-field-data-v7-manifest-v1"] = SCHEMA_VERSION
    data_kind: Literal["synthetic", "observed_unreleased"]
    identities: dict[str, str]
    source_versions: dict[str, str]
    index_ref: str
    index_sha256: str
    split_sha256: dict[str, str]
    quality_accepted: Literal[False]
    release_emitted: Literal[False]

    @model_validator(mode="before")
    @classmethod
    def explicit_false_flags(cls, value: Any) -> Any:
        _require_false_flags(value, ("quality_accepted", "release_emitted"))
        return value

    @model_validator(mode="after")
    def exact_declarations(self):
        if (
            set(self.identities) != set(IDENTITY_KEYS)
            or any(not is_sha256(self.identities[key]) for key in IDENTITY_KEYS)
            or set(self.source_versions) != set(source_versions())
            or any(type(value) is not str or not value for value in self.source_versions.values())
            or not _safe_relative_text(self.index_ref)
            or not is_sha256(self.index_sha256)
            or set(self.split_sha256) != {"train", "validation"}
            or any(not is_sha256(value) for value in self.split_sha256.values())
        ):
            raise ExperimentError("v7_manifest_declaration_invalid")
        return self


class V7PredictorInputs(FrozenContract):
    """Synthetic seven-field inputs; values are explicit strings, unknown stays unknown."""

    b: Any
    attributes: dict[str, str]
    data_kind: Literal["synthetic"] = DATA_KIND_SYNTHETIC
    quality_accepted: Literal[False]
    release_emitted: Literal[False]

    @model_validator(mode="before")
    @classmethod
    def explicit_false_flags(cls, value: Any) -> Any:
        _require_false_flags(value, ("quality_accepted", "release_emitted"))
        return value

    @model_validator(mode="after")
    def exact_attributes(self):
        if (
            set(self.attributes) != set(FIELDS)
            or any(type(value) is not str for value in self.attributes.values())
            or self.quality_accepted is not False
            or self.release_emitted is not False
        ):
            raise ExperimentError("v7_predictor_attributes_invalid")
        for field in FIELDS:
            value = self.attributes[field]
            choices = ("true", "false", "unknown") if field in FIELDS[:5] else ()
            if field in FIELDS[:5]:
                if value not in choices:
                    raise ExperimentError("v7_predictor_boolean_invalid")
            elif field == "scene":
                from scripts.visual_attributes import SCENES

                if value not in SCENES:
                    raise ExperimentError("v7_predictor_scene_invalid")
            else:
                from scripts.visual_attributes import FORMATS

                if value not in FORMATS:
                    raise ExperimentError("v7_predictor_format_invalid")
        return self


class V7SourceRecord(FrozenContract):
    sample_id: str
    partition: Literal["train", "validation"]
    channel_id: str
    features_sha256: str
    run_sha256: str
    identities: dict[str, str]
    frame_seconds: tuple[float, ...]
    frame_sha256: tuple[str, ...]
    data_kind: Literal["synthetic"] = DATA_KIND_SYNTHETIC
    quality_accepted: Literal[False]
    release_emitted: Literal[False]

    @model_validator(mode="before")
    @classmethod
    def explicit_false_flags(cls, value: Any) -> Any:
        _require_false_flags(value, ("quality_accepted", "release_emitted"))
        return value

    @model_validator(mode="after")
    def valid_source(self):
        if (
            not is_identifier(self.sample_id)
            or not is_identifier(self.channel_id)
            or not is_sha256(self.features_sha256)
            or not is_sha256(self.run_sha256)
            or set(self.identities) != set(IDENTITY_KEYS)
            or any(not is_sha256(value) for value in self.identities.values())
            or len(self.frame_seconds) != len(self.frame_sha256)
            or not 1 <= len(self.frame_seconds) <= 4
            or any(type(value) not in (int, float) for value in self.frame_seconds)
            or any(not _valid_frame_second(value) for value in self.frame_seconds)
            or tuple(self.frame_seconds) != tuple(sorted(set(self.frame_seconds)))
            or any(not is_sha256(value) for value in self.frame_sha256)
        ):
            raise ExperimentError("v7_source_record_invalid")
        return self


@dataclass(frozen=True)
class V7DevelopmentData:
    cached: Any
    train: tuple[V7PredictorInputs, ...]
    validation: tuple[V7PredictorInputs, ...]
    manifest: V7Manifest
    manifest_sha256: str
    source_records: tuple[V7SourceRecord, ...]
    source_manifest_path: Path | None = None
    sidecar_root: Path | None = None
    opened_paths: tuple[Path, ...] = ()
    loader_verified: bool = False
    data_kind: str = DATA_KIND_SYNTHETIC
    quality_accepted: bool = False
    release_emitted: bool = False


def _safe_relative_text(value: Any) -> bool:
    if type(value) is not str or not value or "\x00" in value:
        return False
    path = Path(value)
    return not path.is_absolute() and ".." not in path.parts and "." not in path.parts


def _valid_frame_second(value: Any) -> bool:
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value) and 0 <= value <= MAX_CREATIVE_DURATION_SECONDS
    except OverflowError:
        return False


def _require_false_flags(value: Any, names: tuple[str, ...]) -> None:
    if isinstance(value, FrozenContract):
        value = value.model_dump()
    require(type(value) is dict, "v7_quality_flag_type_invalid")
    for name in names:
        require(
            type(value.get(name)) is bool and value[name] is False,
            "v7_quality_must_remain_unreleased",
        )


def _safe_path(root: Path, relative: str) -> Path:
    require(_safe_relative_text(relative), "v7_path_rejected")
    try:
        root = Path(root).resolve(strict=True)
        candidate = root / relative
        resolved = candidate.resolve(strict=True)
    except (OSError, ValueError, RuntimeError):
        raise ExperimentError("v7_path_rejected") from None
    require(resolved.is_relative_to(root), "v7_path_rejected")
    current = root
    for part in Path(relative).parts:
        current = current / part
        require(not current.is_symlink(), "v7_path_rejected")
    return resolved


def _read_bounded(path: Path, opened: list[Path], *, root: Path | None = None) -> bytes:
    path = Path(path)
    if root is not None:
        path = _safe_path(root, str(path))
    else:
        require(
            "\x00" not in os.fspath(path) and path.is_absolute() and not path.is_symlink(),
            "v7_explicit_path_required",
        )
        try:
            path = path.resolve(strict=True)
        except (OSError, ValueError, RuntimeError):
            raise ExperimentError("v7_file_open_failed") from None
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        raise ExperimentError("v7_file_open_failed") from None
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode), "v7_regular_file_required")
        raw = stream.read(MAX_METADATA_BYTES + 1)
    require(len(raw) <= MAX_METADATA_BYTES, "v7_file_too_large")
    opened.append(path)
    return raw


def _object(value: Any, keys: set[str], error: str) -> dict[str, Any]:
    require(type(value) is dict and set(value) == keys, error)
    return value


def _expected_identities(cached: Any) -> dict[str, str]:
    base = cached.base
    return {
        "cohort_sha256": base.cohort_sha256,
        "partition_sha256": base.manifest.manifest_sha256,
        "configuration_sha256": digest(
            {"extractor_config": base.extractor_config, "b_representation": B_REPRESENTATION}
        ),
        "candidate_sha256": digest(
            {
                "manifest_schema": SCHEMA_VERSION,
                "sidecar_schema": SIDECAR_SCHEMA,
                "b_representation": B_REPRESENTATION,
                "fields": list(FIELDS),
                "source_versions": source_versions(),
            }
        ),
    }


def _cached_ids_channels(
    cached: Any,
) -> tuple[list[tuple[str, str, str, Any]], list[tuple[str, str, str, Any]]]:
    pairs = []
    for partition in ("train", "validation"):
        split = getattr(cached.base, partition)
        inputs = getattr(cached, partition)
        require(
            len(split.sample_ids) == len(split.channel_ids) == len(inputs),
            "v7_cached_alignment_mismatch",
        )
        pairs.append(
            [
                (sample_id, partition, channel_id, b_input)
                for sample_id, channel_id, b_input in zip(
                    split.sample_ids, split.channel_ids, inputs, strict=True
                )
            ]
        )
    return pairs[0], pairs[1]


def feature_names() -> tuple[str, ...]:
    b = _b_contract()
    names = (*b.FEATURE_NAMES, *(f"vlm_{field}" for field in FIELDS))
    require(len(b.FEATURE_NAMES) == 905 and len(names) == 912, "v7_feature_width_mismatch")
    require(names[:905] == b.FEATURE_NAMES, "v7_prefix_contract_mismatch")
    return names


def categorical_indices() -> tuple[int, ...]:
    b = _b_contract()
    return (*b.CATEGORICAL_INDICES, *range(905, 912))


def feature_matrix(inputs: Any) -> list[list[Any]]:
    values = tuple(V7PredictorInputs.model_validate(value) for value in inputs)
    require(
        all(value.data_kind == DATA_KIND_SYNTHETIC for value in values),
        "v7_synthetic_input_required",
    )
    b = _b_contract()
    prefix = b.feature_matrix(tuple(b.BInputs.model_validate(value.b) for value in values))
    matrix = [
        row + [value.attributes[field] for field in FIELDS]
        for row, value in zip(prefix, values, strict=True)
    ]
    require(all(len(row) == 912 for row in matrix), "v7_feature_width_mismatch")
    return matrix


def _split_digest(
    cached: Any,
    partition: str,
    inputs: tuple[V7PredictorInputs, ...],
    source_records: tuple[V7SourceRecord, ...],
    identities: dict[str, str],
    versions: dict[str, str],
) -> str:
    split = getattr(cached.base, partition)
    cached_inputs = getattr(cached, partition)
    records = [record for record in source_records if record.partition == partition]
    require(
        tuple(record.sample_id for record in records) == split.sample_ids,
        "v7_source_order_mismatch",
    )
    return digest(
        {
            "schema_version": SCHEMA_VERSION,
            "partition": partition,
            "cached_b_feature_inputs_sha256": digest(
                {
                    "sample_ids": list(split.sample_ids),
                    "channel_ids": list(split.channel_ids),
                    "inputs": [value.model_dump(mode="json") for value in cached_inputs],
                }
            ),
            "identities": identities,
            "source_versions": versions,
            "sample_ids": list(split.sample_ids),
            "inputs": [
                {"attributes": {field: value.attributes[field] for field in FIELDS}}
                for value in inputs
            ],
            "sidecars": [record.model_dump(mode="json") for record in records],
        }
    )


def _validate_data_structure(data: V7DevelopmentData) -> None:
    if (
        getattr(
            getattr(getattr(data.cached, "base", None), "manifest", None),
            "data_kind",
            None,
        )
        != DATA_KIND_SYNTHETIC
    ):
        raise ExperimentError("seven_field_observed_quality_boundary_unavailable")
    require(data.data_kind == DATA_KIND_SYNTHETIC, "v7_synthetic_data_required")
    require(
        type(data.quality_accepted) is bool
        and data.quality_accepted is False
        and type(data.release_emitted) is bool
        and data.release_emitted is False,
        "v7_quality_must_remain_unreleased",
    )
    manifest = V7Manifest.model_validate(data.manifest)
    source_records = tuple(V7SourceRecord.model_validate(record) for record in data.source_records)
    require(manifest.data_kind == DATA_KIND_SYNTHETIC, "v7_synthetic_manifest_required")
    require(
        manifest.quality_accepted is False and manifest.release_emitted is False,
        "v7_quality_must_remain_unreleased",
    )
    identities = _expected_identities(data.cached)
    require(manifest.identities == identities, "v7_cached_identity_mismatch")
    require(manifest.source_versions == source_versions(), "v7_source_version_mismatch")
    b = _b_contract()
    b.validate_data(data.cached)
    train_expected, validation_expected = _cached_ids_channels(data.cached)
    all_expected = train_expected + validation_expected
    require(len(source_records) == len(all_expected), "v7_source_count_mismatch")
    require(
        tuple((r.sample_id, r.partition, r.channel_id) for r in source_records)
        == tuple((sample, part, channel) for sample, part, channel, _ in all_expected),
        "v7_source_alignment_mismatch",
    )
    require(
        all(record.identities == identities for record in source_records),
        "v7_source_identity_mismatch",
    )
    require(
        all(
            all(second <= b_input.a.duration_seconds for second in record.frame_seconds)
            for record, (_sample, _part, _channel, b_input) in zip(
                source_records, all_expected, strict=True
            )
        ),
        "v7_frame_after_creative_duration",
    )
    for part, expected in (("train", train_expected), ("validation", validation_expected)):
        values = tuple(V7PredictorInputs.model_validate(value) for value in getattr(data, part))
        require(len(values) == len(expected), "v7_predictor_count_mismatch")
        require(
            tuple(value.b for value in values) == tuple(row[3] for row in expected),
            "v7_cached_b_input_alignment_mismatch",
        )
        require(
            all(
                value.data_kind == DATA_KIND_SYNTHETIC
                and value.quality_accepted is False
                and value.release_emitted is False
                for value in values
            ),
            "v7_quality_must_remain_unreleased",
        )
        require(
            _split_digest(
                data.cached, part, values, source_records, identities, manifest.source_versions
            )
            == manifest.split_sha256[part],
            "v7_split_digest_mismatch",
        )
        feature_matrix(values)


def validate_data(data: V7DevelopmentData) -> None:
    """Validate in memory and re-open verified synthetic sources before trusting them."""
    _validate_data_structure(data)
    if data.loader_verified:
        reload_data(data)


def _manifest_from_raw(raw: bytes) -> tuple[dict[str, Any], V7Manifest]:
    parsed = parse_json(raw)
    require(type(parsed) is dict, "v7_manifest_invalid")
    # Reject observed data before validating paths, hashes, flags, or cached targets.
    if parsed.get("data_kind") == DATA_KIND_OBSERVED_UNRELEASED:
        raise ExperimentError("seven_field_observed_quality_boundary_unavailable")
    require(parsed.get("data_kind") == DATA_KIND_SYNTHETIC, "v7_synthetic_data_required")
    _object(parsed, MANIFEST_KEYS, "v7_manifest_shape_invalid")
    try:
        manifest = V7Manifest.model_validate(parsed)
    except (ValidationError, ExperimentError):
        raise ExperimentError("v7_manifest_invalid") from None
    return parsed, manifest


def load_data(
    cached: Any,
    manifest_path: Path,
    *,
    sidecar_root: Path,
) -> tuple[V7DevelopmentData, tuple[Path, ...]]:
    """Load only explicitly indexed synthetic train/validation sidecars."""
    # Observed caches fail before manifest IO, cache validation, or target access.
    if (
        getattr(getattr(getattr(cached, "base", None), "manifest", None), "data_kind", None)
        != DATA_KIND_SYNTHETIC
    ):
        raise ExperimentError("seven_field_observed_quality_boundary_unavailable")

    opened: list[Path] = []
    raw_manifest = _read_bounded(Path(manifest_path), opened)
    _, manifest = _manifest_from_raw(raw_manifest)
    require(manifest.identities == _expected_identities(cached), "v7_cached_identity_mismatch")
    versions = source_versions()
    require(manifest.source_versions == versions, "v7_source_version_mismatch")

    index_path = _safe_path(Path(sidecar_root), manifest.index_ref)
    raw_index = _read_bounded(index_path, opened)
    require(
        hashlib.sha256(raw_index).hexdigest() == manifest.index_sha256, "v7_index_hash_mismatch"
    )
    index = parse_json(raw_index)
    _object(index, INDEX_KEYS, "v7_index_shape_invalid")
    require(index["schema_version"] == INDEX_SCHEMA_VERSION, "v7_index_schema_mismatch")
    require(index["data_kind"] == DATA_KIND_SYNTHETIC, "v7_synthetic_data_required")
    require(
        index["quality_accepted"] is False and index["release_emitted"] is False,
        "v7_quality_must_remain_unreleased",
    )
    entries = index["entries"]
    require(type(entries) is list, "v7_index_entries_invalid")

    train_expected, validation_expected = _cached_ids_channels(cached)
    expected_rows = train_expected + validation_expected
    require(len(entries) == len(expected_rows), "v7_index_count_mismatch")
    expected_triplets = [
        (sample, partition, channel) for sample, partition, channel, _ in expected_rows
    ]
    for entry, triplet in zip(entries, expected_triplets, strict=True):
        _object(entry, INDEX_ENTRY_KEYS, "v7_index_entry_invalid")
        require(
            (entry["sample_id"], entry["partition"], entry["channel_id"]) == triplet,
            "v7_index_membership_or_order_mismatch",
        )
        require(
            _safe_relative_text(entry["features_ref"]) and _safe_relative_text(entry["run_ref"]),
            "v7_path_rejected",
        )
        require(
            is_sha256(entry["features_sha256"]) and is_sha256(entry["run_sha256"]),
            "v7_index_hash_invalid",
        )

    predictors_by_partition: dict[str, list[V7PredictorInputs]] = {"train": [], "validation": []}
    source_records: list[V7SourceRecord] = []
    for entry, (_sample, partition, channel_id, b_input) in zip(
        entries, expected_rows, strict=True
    ):
        features_path = _safe_path(Path(sidecar_root), entry["features_ref"])
        run_path = _safe_path(Path(sidecar_root), entry["run_ref"])
        features_raw = _read_bounded(features_path, opened)
        run_raw = _read_bounded(run_path, opened)
        require(
            hashlib.sha256(features_raw).hexdigest() == entry["features_sha256"],
            "v7_features_hash_mismatch",
        )
        require(hashlib.sha256(run_raw).hexdigest() == entry["run_sha256"], "v7_run_hash_mismatch")
        # Parse only after raw-byte hashes have been checked.
        features = parse_json(features_raw)
        run = parse_json(run_raw)
        if type(features) is dict and features.get("data_kind") == DATA_KIND_OBSERVED_UNRELEASED:
            raise ExperimentError("seven_field_observed_quality_boundary_unavailable")
        checked = check_sidecar_v7(
            features,
            expected_sample_id=entry["sample_id"],
            expected_partition=partition,
            expected_channel_id=channel_id,
            expected_identities=manifest.identities,
        )
        require(
            checked.data_kind == DATA_KIND_SYNTHETIC,
            "seven_field_observed_quality_boundary_unavailable",
        )
        _object(run, RUN_KEYS, "v7_run_shape_invalid")
        require(run["schema_version"] == RUN_SCHEMA_VERSION, "v7_run_schema_mismatch")
        require(run["data_kind"] == DATA_KIND_SYNTHETIC, "v7_synthetic_data_required")
        require(
            run["sample_id"] == entry["sample_id"]
            and run["partition"] == partition
            and run["channel_id"] == channel_id,
            "v7_run_alignment_mismatch",
        )
        require(run["identities"] == manifest.identities, "v7_identity_mismatch")
        require(run["status"] == "completed", "v7_run_incomplete")
        require(run["temporary_directory_removed"] is True, "v7_temporary_directory_not_removed")
        require(run["features_sha256"] == entry["features_sha256"], "v7_run_features_hash_mismatch")
        require(
            run["quality_accepted"] is False and run["release_emitted"] is False,
            "v7_quality_must_remain_unreleased",
        )
        predictor = V7PredictorInputs(
            b=b_input,
            attributes=checked.attributes,
            quality_accepted=False,
            release_emitted=False,
        )
        predictors_by_partition[partition].append(predictor)
        source_records.append(
            V7SourceRecord(
                sample_id=checked.sample_id,
                partition=partition,
                channel_id=checked.channel_id,
                features_sha256=entry["features_sha256"],
                run_sha256=entry["run_sha256"],
                identities=checked.identities,
                frame_seconds=checked.frame_seconds,
                frame_sha256=checked.frame_sha256,
                quality_accepted=False,
                release_emitted=False,
            )
        )

    data = V7DevelopmentData(
        cached=cached,
        train=tuple(predictors_by_partition["train"]),
        validation=tuple(predictors_by_partition["validation"]),
        manifest=manifest,
        manifest_sha256=hashlib.sha256(raw_manifest).hexdigest(),
        source_records=tuple(source_records),
        source_manifest_path=Path(manifest_path).resolve(),
        sidecar_root=Path(sidecar_root).resolve(),
        opened_paths=tuple(opened),
        loader_verified=True,
    )
    _validate_data_structure(data)
    require(
        _split_digest(
            cached, "train", data.train, data.source_records, manifest.identities, versions
        )
        == manifest.split_sha256["train"],
        "v7_split_digest_mismatch",
    )
    require(
        _split_digest(
            cached,
            "validation",
            data.validation,
            data.source_records,
            manifest.identities,
            versions,
        )
        == manifest.split_sha256["validation"],
        "v7_split_digest_mismatch",
    )
    return data, tuple(opened)


def reload_data(data: V7DevelopmentData) -> V7DevelopmentData:
    """Reopen and rehash a previously loaded synthetic dataset's explicit sources."""
    require(data.loader_verified, "v7_manual_dataset_has_no_reloadable_sources")
    require(
        data.source_manifest_path is not None and data.sidecar_root is not None,
        "v7_source_paths_missing",
    )
    reloaded, _ = load_data(
        data.cached,
        data.source_manifest_path,
        sidecar_root=data.sidecar_root,
    )
    require(
        reloaded.manifest.model_dump() == data.manifest.model_dump()
        and reloaded.manifest_sha256 == data.manifest_sha256
        and reloaded.source_records == data.source_records
        and reloaded.train == data.train
        and reloaded.validation == data.validation,
        "v7_reloaded_dataset_mismatch",
    )
    return reloaded


def split_digest(data: V7DevelopmentData, partition: Literal["train", "validation"]) -> str:
    require(partition in ("train", "validation"), "v7_split_invalid")
    return _split_digest(
        data.cached,
        partition,
        getattr(data, partition),
        data.source_records,
        data.manifest.identities,
        data.manifest.source_versions,
    )

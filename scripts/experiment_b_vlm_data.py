"""B-VLM adds only perceptually released categorical signals to the exact B-cache prefix."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import model_validator

from scripts.channel_partitions import Digest, ExperimentError, FrozenContract, digest
from scripts.experiment_b_data import (
    CATEGORICAL_INDICES as B_CATEGORICAL_INDICES,
)
from scripts.experiment_b_data import FEATURE_NAMES as B_FEATURE_NAMES
from scripts.experiment_b_data import BDevelopmentData, BInputs
from scripts.experiment_b_data import feature_matrix as b_matrix
from scripts.experiment_b_data import load_data as load_b_data
from scripts.experiment_b_data import split_digest as b_split_digest
from scripts.experiment_b_data import validate_data as validate_b_data
from scripts.experiment_b_vlm_extract import POLICY, load_queue
from scripts.experiment_b_vlm_quality import FIELDS, GATE, checked_sidecar, normalized
from scripts.private_checkpoint import file_hash
from scripts.visual_attributes import FORMATS, SCENES

REPRESENTATION = "b_cached_905_plus_released_vlm_cells_v1"
OPTIONS = {
    **{field: ("true", "false", "unknown") for field in FIELDS[:3]},
    "scene": SCENES,
    "format": tuple(v for v in FORMATS if v != "application"),
}


class QualityRelease(FrozenContract):
    gate: Literal["b-vlm-blind-assisted-sector-gate-v1"] = GATE
    status: Literal["released_columns"]
    released_fields: tuple[str, ...]
    retained_values: dict[str, tuple[str, ...]]
    columns: dict
    human_review: Literal[False]
    general_perception_accuracy_validated: Literal[False]
    predictive_outcomes_used: Literal[False]
    plan_sha256: Digest
    input_policy: Literal["contact-sheet-cell-320x330-v1"] = POLICY
    annotations_sha256: Digest
    audit_sidecars_sha256: dict[str, Digest]
    source_sha256: Digest
    release_sha256: Digest

    @model_validator(mode="after")
    def integrity(self):
        expected = tuple(f for f in FIELDS if f in self.released_fields)
        if (
            not expected
            or self.released_fields != expected
            or set(self.columns) != set(FIELDS)
            or expected != tuple(field for field in FIELDS if self.columns[field]["released"])
            or set(self.retained_values) != set(expected)
            or len(self.audit_sidecars_sha256) != 32
            or any(
                not values
                or "unknown" in values
                or len(set(values)) != len(values)
                or not set(values) <= set(OPTIONS[field])
                for field, values in self.retained_values.items()
            )
            or self.release_sha256 != digest(self.model_dump(exclude={"release_sha256"}))
        ):
            raise ExperimentError("invalid_vlm_quality_release")
        for field in expected:
            column = self.columns[field]
            sectors = column["sectors"]
            if (
                tuple(column["retained_values"]) != self.retained_values[field]
                or set(sectors) != {"moda", "beleza"}
                or any(
                    s["samples"] != 16
                    or s["known"] < 12
                    or s["known"] > 16
                    or s["correct_value_and_evidence"] / s["known"] < 0.9
                    or s["evidence_not_supported_by_blind_annotation"] != 0
                    for s in sectors.values()
                )
            ):
                raise ExperimentError("vlm_column_did_not_pass_sector_gate")
            support = {
                value: sum(s["predicted_value_support"].get(value, 0) for s in sectors.values())
                for value in self.retained_values[field]
            }
            if (
                any(n < 3 for n in support.values())
                or len(support) < 2
                or field in FIELDS[:3]
                and any(
                    s["predicted_value_support"].get(value, 0) < 1
                    for s in sectors.values()
                    for value in ("true", "false")
                )
            ):
                raise ExperimentError("vlm_column_without_value_support")
        return self


class VLMInputs(FrozenContract):
    b: BInputs
    attributes: dict[str, str]

    @model_validator(mode="after")
    def values(self):
        if not self.attributes or any(
            field not in OPTIONS or value not in OPTIONS[field]
            for field, value in self.attributes.items()
        ):
            raise ExperimentError("invalid_vlm_predictor_attributes")
        return self


@dataclass(frozen=True)
class VLMDevelopmentData:
    cached: BDevelopmentData
    train: tuple[VLMInputs, ...]
    validation: tuple[VLMInputs, ...]
    release: QualityRelease
    vlm_config: dict

    @property
    def base(self):
        return self.cached.base


def feature_names(release):
    release = QualityRelease.model_validate(release)
    return (*B_FEATURE_NAMES, *(f"vlm_{field}" for field in release.released_fields))


def categorical_indices(release):
    return (*B_CATEGORICAL_INDICES, *range(905, len(feature_names(release))))


def feature_matrix(inputs, release):
    release = QualityRelease.model_validate(release)
    values = tuple(VLMInputs.model_validate(v) for v in inputs)
    for value in values:
        if set(value.attributes) != set(release.released_fields) or any(
            v != "unknown" and v not in release.retained_values[field]
            for field, v in value.attributes.items()
        ):
            raise ExperimentError("vlm_attributes_not_released_for_this_bundle")
    prefix = b_matrix(tuple(v.b for v in values))
    return [
        b + [v.attributes[field] for field in release.released_fields]
        for b, v in zip(prefix, values, strict=True)
    ]


def validate_data(data):
    validate_b_data(data.cached)
    if data.release.source_sha256 != file_hash(
        Path(__file__).with_name("experiment_b_vlm_quality.py")
    ):
        raise ExperimentError("vlm_quality_gate_source_changed")
    for part in ("train", "validation"):
        values = tuple(VLMInputs.model_validate(v) for v in getattr(data, part))
        if tuple(v.b for v in values) != getattr(data.cached, part):
            raise ExperimentError("vlm_development_alignment_mismatch")
        feature_matrix(values, data.release)


def split_digest(data, part):
    return digest(
        {
            "cached_split": b_split_digest(data.cached, part),
            "quality_release": data.release.release_sha256,
            "vlm_config": data.vlm_config,
            "inputs": [v.model_dump() for v in getattr(data, part)],
        }
    )


def load_data(parent, cohort, queue, release_path, root):
    # Anchored metadata and full completion are checked before any development labels.
    plan, state = load_queue(parent, cohort, queue, root)
    completed = {e["sample_id"]: e for e in state["entries"] if e["status"] == "completed"}
    if (
        state["halt_reason"]
        or len(state["entries"]) != 269
        or set(completed) != {r["sample_id"] for r in plan["rows"]}
    ):
        raise ExperimentError("vlm_requires_complete_269_development_sidecars")
    release = QualityRelease.model_validate_json(release_path.read_bytes())
    if (
        release.plan_sha256 != plan["plan_sha256"]
        or set(release.audit_sidecars_sha256) != set(plan["audit_sample_ids"])
        or release.source_sha256
        != file_hash(Path(__file__).with_name("experiment_b_vlm_quality.py"))
        or any(
            completed[s]["files_sha256"]["features.json"] != h
            for s, h in release.audit_sidecars_sha256.items()
        )
    ):
        raise ExperimentError("vlm_quality_release_not_bound_to_this_extraction")
    cached, opened = load_b_data(
        cohort,
        root,
        parent=parent,
        expected_cohort_sha256=plan["cohort_sha256"],
        expected_partition_sha256=plan["partition_sha256"],
    )
    rows = {r["sample_id"]: r for r in plan["rows"]}

    def load(part):
        result = []
        for sample, b in zip(
            getattr(cached.base, part).sample_ids, getattr(cached, part), strict=True
        ):
            directory = queue / "sessions" / sample
            path = directory / "features.json"
            run_path = directory / "run.json"
            raw, run_raw = path.read_bytes(), run_path.read_bytes()
            expected = completed[sample]["files_sha256"]
            if (
                hashlib.sha256(raw).hexdigest() != expected["features.json"]
                or hashlib.sha256(run_raw).hexdigest() != expected["run.json"]
            ):
                raise ExperimentError("vlm_session_evidence_changed_while_loading")
            sidecar = json.loads(raw)
            run = json.loads(run_raw)
            parsed, _ = checked_sidecar(sidecar, rows[sample], plan["config"])
            if (
                run["status"] != "completed"
                or run["temporary_directory_removed"] is not True
                or run["media_fingerprint"]["sha256"] != sidecar["reacquired_media_sha256"]
            ):
                raise ExperimentError("vlm_sidecar_session_provenance_mismatch")
            attributes = {}
            for field in release.released_fields:
                value = normalized(field, parsed[field]["value"])
                attributes[field] = value if value in release.retained_values[field] else "unknown"
            result.append(VLMInputs(b=b, attributes=attributes))
            opened.extend((path, run_path))
        return tuple(result)

    data = VLMDevelopmentData(cached, load("train"), load("validation"), release, plan["config"])
    validate_data(data)
    return data, opened

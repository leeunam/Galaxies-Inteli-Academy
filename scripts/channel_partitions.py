"""Freeze metadata-only channel/duplicate partitions, without reading outcomes."""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, TypeAdapter, model_validator

Partition = Literal["train", "validation", "test"]
DataKind = Literal["synthetic", "unvalidated"]
PARTITIONS = ("train", "validation", "test")
FRACTIONS = (0.6, 0.2, 0.2)
SECTORS = ("moda", "beleza")
Identifier = Annotated[str, StringConstraints(pattern=r"^[A-Za-z0-9_-]{1,100}$")]
Digest = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class ExperimentError(ValueError):
    """Fixed error code; never includes private records or labels."""


class FrozenContract(BaseModel):
    model_config = ConfigDict(
        strict=True, extra="forbid", frozen=True, revalidate_instances="always", allow_inf_nan=False
    )


class Reference(FrozenContract):
    sample_id: Identifier
    channel_id: Identifier
    sector: Literal["moda", "beleza"]
    media_sha256: Digest
    duplicate_group: Identifier | None = None


class Assignment(Reference):
    partition: Partition
    group_id: Digest


class SectorSupport(FrozenContract):
    sector: Literal["moda", "beleza"]
    samples: int = Field(ge=0)
    channels: int = Field(ge=0)


class PartitionSupport(FrozenContract):
    partition: Partition
    samples: int = Field(gt=0)
    channels: int = Field(gt=0)
    independent_groups: int = Field(gt=0)
    sectors: tuple[SectorSupport, ...]


class PartitionManifest(FrozenContract):
    schema_version: Literal["channel-partitions-v1"] = "channel-partitions-v1"
    algorithm: Literal["channel-duplicates-stratified-v1"] = "channel-duplicates-stratified-v1"
    seed: int = Field(ge=0, le=2**32 - 1)
    data_kind: DataKind
    real_results_available: Literal[False] = False
    target_fractions: tuple[float, float, float] = FRACTIONS
    metadata_sha256: Digest
    assignments: tuple[Assignment, ...] = Field(min_length=3)
    support: tuple[PartitionSupport, ...]
    warnings: tuple[str, ...]
    manifest_sha256: Digest

    @model_validator(mode="after")
    def integrity(self):
        references = [_reference(row) for row in self.assignments]
        expected = _partition(references, self.seed)
        if (
            self.target_fractions != FRACTIONS
            or self.assignments != expected
            or self.metadata_sha256 != digest([row.model_dump() for row in references])
            or self.support != _support(expected)
            or self.warnings != _warnings(expected)
            or self.manifest_sha256 != digest(self.model_dump(exclude={"manifest_sha256"}))
        ):
            raise ExperimentError("partition_manifest_mismatch")
        return self


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _reference(row: Assignment) -> Reference:
    return Reference.model_validate(row.model_dump(include=set(Reference.model_fields)))


@dataclass
class _Group:
    group_id: str
    rows: list[Reference]
    channels: set[str]
    sector_channels: dict[str, set[str]]


def _groups(rows: list[Reference]) -> list[_Group]:
    parents = {row.channel_id: row.channel_id for row in rows}

    def find(channel):
        while parents[channel] != channel:
            parents[channel] = parents[parents[channel]]
            channel = parents[channel]
        return channel

    anchors = {}
    for row in rows:
        keys = [("hash", row.media_sha256)]
        if row.duplicate_group is not None:
            keys.append(("duplicate", row.duplicate_group))
        for key in keys:
            if key in anchors:
                left, right = find(row.channel_id), find(anchors[key])
                parents[max(left, right)] = min(left, right)
            else:
                anchors[key] = row.channel_id
    members = defaultdict(list)
    for row in rows:
        members[find(row.channel_id)].append(row)
    result = []
    for group_rows in members.values():
        channels = {row.channel_id for row in group_rows}
        result.append(
            _Group(
                group_id=digest(sorted(channels)),
                rows=group_rows,
                channels=channels,
                sector_channels={
                    sector: {r.channel_id for r in group_rows if r.sector == sector}
                    for sector in SECTORS
                },
            )
        )
    return sorted(result, key=lambda group: group.group_id)


def _partition(rows: list[Reference], seed: int) -> tuple[Assignment, ...]:
    if len({row.sample_id for row in rows}) != len(rows):
        raise ExperimentError("duplicate_sample_id")
    groups = _groups(rows)
    if len(groups) < 3:
        raise ExperimentError("insufficient_independent_groups")
    strata = defaultdict(list)
    for group in groups:
        strata[tuple(s for s in SECTORS if group.sector_channels[s])].append(group)
    allocation, sparse = {}, []
    for profile in sorted(strata):
        members = strata[profile]
        if len(members) < 3:
            sparse.extend(members)
            continue
        members.sort(key=lambda g: (-len(g.channels), digest([seed, g.group_id])))
        total = sum(len(g.channels) for g in members)
        counts = dict.fromkeys(PARTITIONS, 0)
        for index, group in enumerate(members):
            empty = [p for p in PARTITIONS if counts[p] == 0]
            choices = empty if len(members) - index == len(empty) else PARTITIONS
            selected = min(
                choices,
                key=lambda p: (
                    (counts[p] + len(group.channels) - FRACTIONS[PARTITIONS.index(p)] * total) ** 2
                    - (counts[p] - FRACTIONS[PARTITIONS.index(p)] * total) ** 2,
                    digest([seed, group.group_id, p]),
                ),
            )
            allocation[group.group_id] = selected
            counts[selected] += len(group.channels)
    # At most two groups for each of three sector profiles: <= 3**6 candidates.
    # Exact enumeration of sparse strata preserves sector coverage whenever feasible.
    candidates = []
    for choices in itertools.product(PARTITIONS, repeat=len(sparse)):
        candidate = allocation | {g.group_id: p for g, p in zip(sparse, choices, strict=True)}
        if set(candidate.values()) == set(PARTITIONS):
            candidates.append(candidate)
    selected = min(candidates, key=lambda candidate: _score(groups, candidate, seed))
    return tuple(
        sorted(
            (
                Assignment(
                    **row.model_dump(), group_id=group.group_id, partition=selected[group.group_id]
                )
                for group in groups
                for row in group.rows
            ),
            key=lambda row: row.sample_id,
        )
    )


def _score(groups, allocation, seed):
    populations = [{g.group_id: len(g.channels) for g in groups}]
    populations += [{g.group_id: len(g.sector_channels[s]) for g in groups} for s in SECTORS]
    missing, loss = 0, 0.0
    for index, population in enumerate(populations):
        total = sum(population.values())
        if not total:
            continue
        for partition, fraction in zip(PARTITIONS, FRACTIONS, strict=True):
            count = sum(
                size for group, size in population.items() if allocation[group] == partition
            )
            missing += int(index > 0 and count == 0)
            loss += (count - fraction * total) ** 2 / total
    return missing, loss, digest([seed, sorted(allocation.items())])


def _support(assignments):
    return tuple(
        PartitionSupport(
            partition=partition,
            samples=sum(row.partition == partition for row in assignments),
            channels=len({row.channel_id for row in assignments if row.partition == partition}),
            independent_groups=len(
                {row.group_id for row in assignments if row.partition == partition}
            ),
            sectors=tuple(
                SectorSupport(
                    sector=sector,
                    samples=sum(
                        row.partition == partition and row.sector == sector for row in assignments
                    ),
                    channels=len(
                        {
                            row.channel_id
                            for row in assignments
                            if row.partition == partition and row.sector == sector
                        }
                    ),
                )
                for sector in SECTORS
            ),
        )
        for partition in PARTITIONS
    )


def _warnings(assignments):
    warnings = []
    for sector in SECTORS:
        groups = {row.group_id for row in assignments if row.sector == sector}
        if len(groups) < 5:
            warnings.append(f"few_independent_groups:{sector}")
        for partition in PARTITIONS:
            if not any(row.sector == sector and row.partition == partition for row in assignments):
                warnings.append(f"sector_absent:{sector}:{partition}")
    channels = defaultdict(set)
    for row in assignments:
        channels[row.group_id].add(row.channel_id)
    if any(len(value) > 1 for value in channels.values()):
        warnings.append("duplicates_join_channels")
    return tuple(sorted(warnings))


def create_partitions(records: list, *, seed=42, data_kind: DataKind = "unvalidated"):
    references = TypeAdapter(list[Reference]).validate_python(records)
    # Validate seed/kind before running the deterministic splitter.
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise ExperimentError("invalid_partition_seed")
    if data_kind not in ("synthetic", "unvalidated"):
        raise ExperimentError("invalid_data_kind")
    references.sort(key=lambda row: row.sample_id)
    assignments = _partition(references, seed)
    body = {
        "schema_version": "channel-partitions-v1",
        "algorithm": "channel-duplicates-stratified-v1",
        "seed": seed,
        "data_kind": data_kind,
        "real_results_available": False,
        "target_fractions": FRACTIONS,
        "metadata_sha256": digest([row.model_dump() for row in references]),
        "assignments": assignments,
        "support": _support(assignments),
        "warnings": _warnings(assignments),
    }
    serialized = {
        **body,
        "assignments": [row.model_dump() for row in assignments],
        "support": [row.model_dump() for row in body["support"]],
    }
    return PartitionManifest(**body, manifest_sha256=digest(serialized))


def save_new_json(path: Path, value: FrozenContract):
    """Atomic publication with mode 0600; an existing file is never replaced."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(value.model_dump_json())
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    except FileExistsError:
        raise ExperimentError("output_already_exists") from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def load_partitions(path: Path) -> PartitionManifest:
    with Path(path).open("rb") as handle:
        raw = handle.read(16 * 1024 * 1024 + 1)
    if len(raw) > 16 * 1024 * 1024:
        raise ExperimentError("manifest_too_large")
    return PartitionManifest.model_validate_json(raw)


def freeze_partitions(records: list, path: Path, *, seed=42, data_kind: DataKind = "unvalidated"):
    manifest = create_partitions(records, seed=seed, data_kind=data_kind)
    save_new_json(path, manifest)
    return manifest

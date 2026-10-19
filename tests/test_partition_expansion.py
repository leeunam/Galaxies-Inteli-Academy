import hashlib
import json

import pytest
from pydantic import ValidationError

from scripts.channel_partitions import (
    ExperimentError,
    PartitionManifest,
    append_development_partitions,
    create_partitions,
    digest,
    new_channel_partition,
)
from scripts.empirical_baseline import fit_baseline
from tests.test_channel_partitions import references


def additions():
    return [
        {
            "sample_id": f"new_{i}",
            "channel_id": f"new_channel_{i // 2}",
            "sector": "moda" if i % 2 else "beleza",
            "media_sha256": hashlib.sha256(f"new_{i}".encode()).hexdigest(),
        }
        for i in range(20)
    ]


def test_extension_preserves_old_assignments_and_never_adds_test():
    parent = create_partitions(references(), data_kind="synthetic")
    old_bytes = parent.model_dump_json()
    expanded = append_development_partitions(parent, additions())
    old = {r.sample_id: r for r in parent.assignments}
    assert {r.sample_id: r for r in expanded.assignments if r.sample_id in old} == old
    assert [r for r in expanded.assignments if r.partition == "test"] == [
        r for r in parent.assignments if r.partition == "test"
    ]
    for row in expanded.assignments:
        if row.sample_id not in old:
            assert row.partition == new_channel_partition(row.channel_id)
    assert append_development_partitions(parent, list(reversed(additions()))) == expanded
    assert PartitionManifest.model_validate_json(expanded.model_dump_json()) == expanded
    assert parent.model_dump_json() == old_bytes
    assert "extension" not in parent.model_dump()
    assert parent.manifest_sha256 == digest(parent.model_dump(exclude={"manifest_sha256"}))
    targets = [
        {"sample_id": r.sample_id, "view_count": 100}
        for r in expanded.assignments
        if r.partition == "train"
    ]
    assert fit_baseline(expanded, targets).partition_manifest_sha256 == expanded.manifest_sha256


@pytest.mark.parametrize("field", ["sample_id", "channel_id", "media_sha256", "duplicate_group"])
def test_old_ids_channels_and_duplicate_links_are_forbidden(field):
    rows = references()
    rows[0]["duplicate_group"] = "old_group"
    parent = create_partitions(rows)
    added = additions()
    added[0][field] = rows[0][field]
    with pytest.raises(ExperimentError, match="invalid_partition_additions"):
        append_development_partitions(parent, added)


def test_cross_partition_republications_are_rejected_without_moving_channels():
    parent = create_partitions(references())
    added = additions()
    first = next(r for r in added if new_channel_partition(r["channel_id"]) == "train")
    second = next(r for r in added if new_channel_partition(r["channel_id"]) == "validation")
    first["duplicate_group"] = second["duplicate_group"] = "new_duplicate"
    with pytest.raises(ExperimentError, match="duplicate_crosses_frozen_partition"):
        append_development_partitions(parent, added)


@pytest.mark.parametrize("change", ["partition", "sector", "missing", "parent", "new_partition"])
def test_forged_extension_rejected_even_after_checksum_recomputation(change):
    parent = create_partitions(references())
    expanded = append_development_partitions(parent, additions())
    data = expanded.model_dump(mode="json")
    old_ids = {r.sample_id for r in parent.assignments}
    old = next(r for r in data["assignments"] if r["sample_id"] in old_ids)
    if change == "partition":
        old["partition"] = "test" if old["partition"] != "test" else "train"
    elif change == "sector":
        old["sector"] = "moda" if old["sector"] == "beleza" else "beleza"
    elif change == "missing":
        data["assignments"].remove(old)
    elif change == "parent":
        data["extension"]["parent"]["manifest_sha256"] = "0" * 64
    else:
        next(r for r in data["assignments"] if r["sample_id"] not in old_ids)["partition"] = "test"
    data["manifest_sha256"] = digest({k: v for k, v in data.items() if k != "manifest_sha256"})
    with pytest.raises((ExperimentError, ValidationError)):
        PartitionManifest.model_validate_json(json.dumps(data))

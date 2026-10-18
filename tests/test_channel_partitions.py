import copy
import hashlib
import json
import os

import pytest
from pydantic import ValidationError

from scripts.channel_partitions import (
    ExperimentError,
    PartitionManifest,
    create_partitions,
    digest,
    freeze_partitions,
    load_partitions,
)


def references(count=10):
    return [
        {
            "sample_id": f"{sector}_{channel}_{sample}",
            "channel_id": f"channel_{sector}_{channel}",
            "sector": sector,
            "media_sha256": hashlib.sha256(f"{sector}_{channel}_{sample}".encode()).hexdigest(),
        }
        for sector in ("moda", "beleza")
        for channel in range(count)
        for sample in range(2)
    ]


def test_split_is_by_channel_and_stratified_approximately_60_20_20():
    manifest = create_partitions(references(), data_kind="synthetic")
    assert len(manifest.assignments) == 40
    assert manifest.real_results_available is False
    assert manifest.data_kind == "synthetic"
    for support, channels in zip(manifest.support, (12, 4, 4), strict=True):
        assert support.channels == channels
        assert support.samples == channels * 2
        assert all(sector.channels == channels // 2 for sector in support.sectors)
    seen = {}
    for row in manifest.assignments:
        assert seen.setdefault(row.channel_id, row.partition) == row.partition


def test_order_independence_and_explicit_seed():
    rows = references()
    original = create_partitions(rows, data_kind="synthetic")
    assert create_partitions(list(reversed(rows)), data_kind="synthetic") == original
    other = create_partitions(rows, seed=43, data_kind="synthetic")
    assert other.metadata_sha256 == original.metadata_sha256
    assert other.assignments != original.assignments
    assert other.manifest_sha256 != original.manifest_sha256


def test_prolific_channel_does_not_turn_channel_split_into_row_split():
    rows = references()
    original = create_partitions(rows)
    for index in range(100):
        rows.append(
            {
                **rows[0],
                "sample_id": f"extra_{index}",
                "media_sha256": hashlib.sha256(f"extra_{index}".encode()).hexdigest(),
            }
        )
    expanded = create_partitions(rows)
    expected = {row.channel_id: row.partition for row in original.assignments}
    assert all(row.partition == expected[row.channel_id] for row in expanded.assignments)


def test_hash_and_recognized_duplicate_chains_join_entire_channels():
    rows = references()
    # moda_0 <-> beleza_0 by hash; beleza_0 <-> beleza_1 by known republication.
    first = next(row for row in rows if row["sample_id"] == "moda_0_0")
    second = next(row for row in rows if row["sample_id"] == "beleza_0_0")
    third = next(row for row in rows if row["sample_id"] == "beleza_0_1")
    fourth = next(row for row in rows if row["sample_id"] == "beleza_1_0")
    second["media_sha256"] = first["media_sha256"]
    third["duplicate_group"] = fourth["duplicate_group"] = "known_republication"
    manifest = create_partitions(rows)
    joined = [
        row
        for row in manifest.assignments
        if row.channel_id
        in {
            "channel_moda_0",
            "channel_beleza_0",
            "channel_beleza_1",
        }
    ]
    assert len({row.partition for row in joined}) == 1
    assert len({row.group_id for row in joined}) == 1
    assert "duplicates_join_channels" in manifest.warnings


def test_sparse_mixed_sector_groups_cover_all_splits_when_feasible():
    rows = references(2)
    rows += [
        {
            "sample_id": f"mixed_{sector}_{index}",
            "channel_id": f"mixed_{index}",
            "sector": sector,
            "media_sha256": hashlib.sha256(f"mixed_{sector}_{index}".encode()).hexdigest(),
        }
        for sector in ("moda", "beleza")
        for index in range(2)
    ]
    manifest = create_partitions(rows)
    assert not any(warning.startswith("sector_absent") for warning in manifest.warnings)
    assert len({row.partition for row in manifest.assignments}) == 3


def test_tiny_groups_are_disclosed_and_never_split_into_rows():
    manifest = create_partitions(references(3))
    assert "few_independent_groups:moda" in manifest.warnings
    assert "few_independent_groups:beleza" in manifest.warnings
    assert all(support.channels == 2 for support in manifest.support)
    with pytest.raises(ExperimentError, match="insufficient_independent_groups"):
        create_partitions([row for row in references(1)])


def test_one_duplicate_component_cannot_supply_three_partitions():
    rows = references(5)
    for row in rows:
        row["duplicate_group"] = "all_are_republications"
    with pytest.raises(ExperimentError, match="insufficient_independent_groups"):
        create_partitions(rows)


@pytest.mark.parametrize(
    "change",
    [
        {"view_count": 100},
        {"sector": "other"},
        {"channel_id": ""},
        {"media_sha256": "invalid"},
        {"duplicate_group": ""},
    ],
)
def test_partition_input_rejects_outcomes_and_invalid_audit_fields(change):
    rows = references()
    rows[0] |= change
    with pytest.raises(ValidationError):
        create_partitions(rows)


@pytest.mark.parametrize("seed", [True, 1.5, -1, 2**32])
def test_invalid_seed_is_not_coerced(seed):
    with pytest.raises(ExperimentError, match="invalid_partition_seed"):
        create_partitions(references(), seed=seed)


def test_sample_ids_must_be_unique():
    rows = references()
    rows.append(copy.deepcopy(rows[0]))
    with pytest.raises(ExperimentError, match="duplicate_sample_id"):
        create_partitions(rows)


def test_freeze_round_trip_is_private_and_refuses_overwrite(tmp_path):
    path = tmp_path / "manifest.json"
    manifest = freeze_partitions(references(), path, data_kind="synthetic")
    assert load_partitions(path) == manifest
    assert os.stat(path).st_mode & 0o777 == 0o600
    before = path.read_bytes()
    with pytest.raises(ExperimentError, match="output_already_exists"):
        freeze_partitions(references(), path, seed=99)
    assert path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [path]


def test_manifest_rejects_tampering_even_with_recomputed_checksum(tmp_path):
    path = tmp_path / "manifest.json"
    manifest = freeze_partitions(references(), path)
    data = manifest.model_dump(mode="json")
    data["assignments"][0]["partition"] = (
        "test" if data["assignments"][0]["partition"] != "test" else "train"
    )
    data["manifest_sha256"] = digest({k: v for k, v in data.items() if k != "manifest_sha256"})
    path.write_text(json.dumps(data))
    with pytest.raises(ValidationError, match="partition_manifest_mismatch"):
        load_partitions(path)


def test_data_kind_never_claims_a_real_eligible_corpus():
    manifest = create_partitions(references())
    assert manifest.data_kind == "unvalidated"
    with pytest.raises(ExperimentError, match="invalid_data_kind"):
        create_partitions(references(), data_kind="eligible_real")
    data = manifest.model_dump(mode="json")
    data["real_results_available"] = True
    with pytest.raises(ValidationError):
        PartitionManifest.model_validate_json(json.dumps(data))

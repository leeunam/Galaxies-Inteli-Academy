"""Invented fixture shared by offline and explicitly synthetic service demos."""

import hashlib

from scripts.channel_partitions import create_partitions
from scripts.empirical_baseline import BaselineArtifact, fit_baseline


def synthetic_dataset(channels_per_sector=10):
    references, outcomes = [], {}
    for sector, views in (("moda", (0, 8)), ("beleza", (99, 9999))):
        for channel in range(channels_per_sector):
            for index, count in enumerate(views):
                sample_id = f"synthetic_{sector}_{channel}_{index}"
                references.append(
                    {
                        "sample_id": sample_id,
                        "channel_id": f"synthetic_{sector}_{channel}",
                        "sector": sector,
                        "media_sha256": hashlib.sha256(sample_id.encode()).hexdigest(),
                    }
                )
                outcomes[sample_id] = count
    return references, outcomes


def build_synthetic_baseline() -> BaselineArtifact:
    """Build only from invented constants, without loading files or held-out labels."""
    references, outcomes = synthetic_dataset()
    manifest = create_partitions(references, data_kind="synthetic")
    return fit_baseline(
        manifest,
        [
            {"sample_id": row.sample_id, "view_count": outcomes[row.sample_id]}
            for row in manifest.assignments
            if row.partition == "train"
        ],
    )

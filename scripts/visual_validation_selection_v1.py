"""Prospective training-only selection, without images, outcomes or model calls."""

import hashlib
from collections import Counter, defaultdict

from scripts.visual_validation_contract_v1 import (
    PROPOSAL_SHA256,
    commitment,
    digest,
    identifier,
    is_sha,
    require,
    timeline,
    write_new,
)

PROTOCOL = "front1-visual-audit-20261021-v1"
ROW_KEYS = {
    "sample_id",
    "channel_id",
    "sector",
    "partition",
    "media_sha256",
    "frame_seconds",
    "frame_sha256",
}


def order_hash(*components):
    return hashlib.sha256(b"\0".join(s.encode() for s in components)).hexdigest()


def select_training(metadata, exclusions):
    """Only an explicit training projection is accepted; never filter a mixed corpus."""
    require(
        type(metadata) is dict
        and set(metadata) == {"schema", "cohort_size", "split_counts", "source_sha256", "rows"},
        "visual_training_projection_required",
    )
    require(
        metadata["schema"] == "visual-audit-training-metadata-v1"
        and metadata["cohort_size"] == 300
        and metadata["split_counts"] == {"train": 203, "validation": 66, "test": 31}
        and is_sha(metadata["source_sha256"]),
        "visual_training_lineage_required",
    )
    rows = metadata["rows"]
    require(type(rows) is list and len(rows) == 203, "visual_training_203_required")
    require(
        type(exclusions) is dict
        and set(exclusions) == {"sample_ids", "channel_ids", "media_sha256", "source_sha256"},
        "visual_exclusions_required",
    )
    for key in ("sample_ids", "channel_ids", "media_sha256"):
        require(
            type(exclusions[key]) is list and len(exclusions[key]) == len(set(exclusions[key])),
            "visual_invalid_exclusions",
        )
    sources = exclusions["source_sha256"]
    require(
        type(sources) is dict and sources and all(is_sha(h) for h in sources.values()),
        "visual_exclusion_provenance_required",
    )
    require(
        all(identifier(s) for s in exclusions["sample_ids"] + exclusions["channel_ids"])
        and all(is_sha(h) for h in exclusions["media_sha256"]),
        "visual_invalid_exclusions",
    )
    seen, by_sector = set(), {s: defaultdict(list) for s in ("beleza", "moda")}
    for row in rows:
        require(
            type(row) is dict and row.get("partition") == "train",
            "visual_mixed_or_reserved_metadata_refused",
        )
        require(set(row) == ROW_KEYS, "visual_outcomes_or_unexpected_metadata")
        require(
            identifier(row["sample_id"])
            and identifier(row["channel_id"])
            and row["sector"] in by_sector
            and is_sha(row["media_sha256"]),
            "visual_training_row_invalid",
        )
        timeline(row["frame_seconds"], row["frame_sha256"])
        require(row["sample_id"] not in seen, "visual_duplicate_training_id")
        seen.add(row["sample_id"])
        if (
            row["sample_id"] in exclusions["sample_ids"]
            or row["channel_id"] in exclusions["channel_ids"]
            or row["media_sha256"] in exclusions["media_sha256"]
        ):
            continue
        by_sector[row["sector"]][row["channel_id"]].append(row)
    selected, used = [], set()
    for sector in ("beleza", "moda"):
        channels = by_sector[sector]
        before = len(selected)
        for channel in sorted(channels, key=lambda c: (order_hash(PROTOCOL, sector, c), c)):
            if channel in used:
                continue
            row = min(
                channels[channel],
                key=lambda r: (order_hash(PROTOCOL, r["sample_id"]), r["sample_id"]),
            )
            alias = "case-" + order_hash(PROTOCOL, "annotation", row["sample_id"])[:24]
            selected.append(dict(row, alias=alias))
            used.add(channel)
            if len(selected) - before == 16:
                break
        require(len(selected) - before == 16, "visual_insufficient_unrevealed_channels")
    value = {
        "schema": "visual-audit-selection-v1",
        "protocol": PROTOCOL,
        "proposal_sha256": PROPOSAL_SHA256,
        "training_projection_sha256": digest(metadata),
        "exclusions_sha256": digest(exclusions),
        "exclusion_source_sha256": dict(sources),
        "rows": selected,
        "audit_calls_exact": 3 * sum(len(r["frame_seconds"]) for r in selected),
        "independent_exclusion_review_required": True,
        "execution_authorized": False,
    }
    return value | {"selection_sha256": digest(value)}


def annotation_packet(selection, *, requirement="assisted_review_allowed"):
    commitment(selection, "selection_sha256")
    rows = selection["rows"]
    require(
        len(rows) == 32
        and Counter(r["sector"] for r in rows) == {"beleza": 16, "moda": 16}
        and len({r["channel_id"] for r in rows}) == 32,
        "visual_selection_shape",
    )
    require(
        requirement in ("assisted_review_allowed", "human_required"),
        "visual_annotation_requirement",
    )
    value = {
        "schema": "visual-annotator-packet-v1",
        "selection_sha256": selection["selection_sha256"],
        "annotation_requirement": requirement,
        "items": [
            {
                "alias": r["alias"],
                "frame_seconds": r["frame_seconds"],
                "frame_sha256": r["frame_sha256"],
            }
            for r in rows
        ],
    }
    return value | {"packet_sha256": digest(value)}


def seal_selection(selection, directory):
    commitment(selection, "selection_sha256")
    return write_new(directory / "selection.json", selection)

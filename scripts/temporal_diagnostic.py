"""Outcome-free development cut for a retrospective earlier-to-later experiment.

No IO, labels, features, fit or holdout loader. This plan never rewrites the
channel-partition manifest and cannot establish availability at publication.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from scripts.channel_partitions import Digest, ExperimentError, FrozenContract, Identifier, digest


class TemporalRow(FrozenContract):
    sample_id: Identifier
    channel_id: Identifier
    sector: Literal["moda", "beleza"]
    source_partition: Literal["train", "validation"]
    duplicate_component: Digest
    published_at_utc: str
    observed_at_utc: str


def _utc(value):
    try:
        date = datetime.fromisoformat(value)
        if date.tzinfo is None or date.utcoffset().total_seconds() != 0:
            raise ValueError
        return date.astimezone(UTC)
    except (ValueError, TypeError, AttributeError, OverflowError):
        raise ExperimentError("temporal_requires_explicit_utc") from None


def _support(rows):
    return {
        "samples": len(rows),
        "channels": len({r.channel_id for r in rows}),
        "duplicate_components": len({r.duplicate_component for r in rows}),
        "by_sector": {
            sector: {
                "samples": sum(r.sector == sector for r in rows),
                "channels": len({r.channel_id for r in rows if r.sector == sector}),
            }
            for sector in ("moda", "beleza")
        },
        "by_source_partition": {
            p: sum(r.source_partition == p for r in rows) for p in ("train", "validation")
        },
        "by_channel": {
            c: sum(r.channel_id == c for r in rows) for c in sorted({r.channel_id for r in rows})
        },
        "publication_range_utc": [
            min((_utc(r.published_at_utc) for r in rows), default=None),
            max((_utc(r.published_at_utc) for r in rows), default=None),
        ],
        "observation_range_utc": [
            min((_utc(r.observed_at_utc) for r in rows), default=None),
            max((_utc(r.observed_at_utc) for r in rows), default=None),
        ],
        "age_bands_days": {
            f"[{lower},{upper})": sum(
                lower
                <= (_utc(r.observed_at_utc) - _utc(r.published_at_utc)).total_seconds() / 86400
                < upper
                for r in rows
            )
            for lower, upper in ((30, 32), (32, 34), (34, 37))
        },
    }


def plan_temporal_diagnostic(rows, *, cutoff_utc, separate_channels=False):
    """Require an explicit predeclared cut; never choose a cut by errors or labels.

    Rows from train and validation may be used in a SEPARATE diagnostic. Original
    partition assignments remain intact. Crossing duplicate components are
    purged from the earlier fit side, preserving the later evaluation side.
    Channel overlap is reported, or purged too when predeclared explicitly.
    """
    if type(separate_channels) is not bool:
        raise ExperimentError("invalid_temporal_channel_policy")
    rows = tuple(TemporalRow.model_validate(r) for r in rows)
    ids = tuple(r.sample_id for r in rows)
    if not rows or ids != tuple(sorted(set(ids))):
        raise ExperimentError("temporal_requires_sorted_development_ids")
    cutoff = _utc(cutoff_utc)
    for r in rows:
        age = (_utc(r.observed_at_utc) - _utc(r.published_at_utc)).total_seconds() / 86400
        if not 30 <= age < 37:
            raise ExperimentError("temporal_target_age_mismatch")
    before = tuple(r for r in rows if _utc(r.published_at_utc) < cutoff)
    after = tuple(r for r in rows if _utc(r.published_at_utc) >= cutoff)
    duplicate_overlap = {r.duplicate_component for r in before} & {
        r.duplicate_component for r in after
    }
    channel_overlap = {r.channel_id for r in before} & {r.channel_id for r in after}
    excluded = tuple(
        r
        for r in before
        if r.duplicate_component in duplicate_overlap
        or (separate_channels and r.channel_id in channel_overlap)
    )
    excluded_ids = {r.sample_id for r in excluded}
    fit = tuple(r for r in before if r.sample_id not in excluded_ids)
    remaining_overlap = sorted({r.channel_id for r in fit} & {r.channel_id for r in after})
    reasons = []
    for name, subset in (("earlier_fit", fit), ("later_evaluation", after)):
        if not subset:
            reasons.append(f"empty:{name}")
        for sector in ("moda", "beleza"):
            if not any(r.sector == sector for r in subset):
                reasons.append(f"sector_without_support:{name}:{sector}")
    historical_available = bool(fit and after) and max(_utc(r.observed_at_utc) for r in fit) < min(
        _utc(r.published_at_utc) for r in after
    )
    value = {
        "schema_version": "retrospective-temporal-plan-v1",
        "cutoff_utc": cutoff.isoformat(),
        "cut_policy": "published_before_cut_fit_at_or_after_cut_evaluate",
        "channel_policy": "purge_crossing_from_fit" if separate_channels else "overlap_reported",
        "duplicate_policy": "purge_crossing_components_from_fit",
        "development_metadata_sha256": digest([r.model_dump() for r in rows]),
        "fit_ids": [r.sample_id for r in fit],
        "evaluation_ids": [r.sample_id for r in after],
        "excluded_earlier_ids": sorted(excluded_ids),
        "support": {"earlier_fit": _support(fit), "later_evaluation": _support(after)},
        "crossing_channels_before_purge": sorted(channel_overlap),
        "remaining_overlapping_channels": remaining_overlap,
        "crossing_duplicate_components": len(duplicate_overlap),
        "support_status": "blocked_support" if reasons else "plan_only_requires_fit_and_evaluation",
        "support_blockers": reasons,
        "earlier_labels_observed_before_first_later_publication": historical_available,
        "prospective_backtest": False,
        "original_partitions_rewritten": False,
        "fit_executed": False,
        "evaluation_executed": False,
        "limitations": [
            "single_snapshot_publication_and_exposure_age_confounded",
            "historical_channel_statistics_and_original_metadata_not_reconstructed",
            "cannot_isolate_temporal_drift",
            "not_independent_final_holdout",
            "support_and_dates_are_not_an_earlier_to_later_model_evaluation",
        ],
    }
    for support in value["support"].values():
        for field in ("publication_range_utc", "observation_range_utc"):
            support[field] = [v.isoformat() if v is not None else None for v in support[field]]
    return value | {"plan_sha256": digest(value)}

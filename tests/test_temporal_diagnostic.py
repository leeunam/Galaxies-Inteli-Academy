"""Invented dates only: planning does not count as a fitted temporal diagnosis."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from scripts.channel_partitions import ExperimentError, digest
from scripts.temporal_diagnostic import TemporalRow, plan_temporal_diagnostic


def rows():
    origin = datetime(2026, 9, 1, tzinfo=UTC)
    return tuple(
        TemporalRow(
            sample_id=f"s{i}",
            channel_id=f"c{i % 4}",
            sector="moda" if i % 2 else "beleza",
            source_partition="train" if i < 4 else "validation",
            duplicate_component=digest(f"group{i}"),
            published_at_utc=(origin + timedelta(days=i)).isoformat(),
            observed_at_utc=(origin + timedelta(days=i + 32)).isoformat(),
        )
        for i in range(8)
    )


def test_strict_chronological_fit_and_later_eval_keep_cut_ties_later():
    data = rows()
    before = tuple(r.model_dump() for r in data)
    p = plan_temporal_diagnostic(data, cutoff_utc="2026-09-05T00:00:00Z")
    assert p["fit_ids"] == ["s0", "s1", "s2", "s3"]
    assert p["evaluation_ids"] == ["s4", "s5", "s6", "s7"]
    assert p["remaining_overlapping_channels"] == ["c0", "c1", "c2", "c3"]
    assert p["support"]["earlier_fit"]["samples"] == 4
    assert p["support"]["later_evaluation"]["by_sector"]["moda"]["samples"] == 2
    assert not p["earlier_labels_observed_before_first_later_publication"]
    assert not p["prospective_backtest"]
    assert not p["fit_executed"] and not p["evaluation_executed"]
    assert tuple(r.model_dump() for r in data) == before
    assert p["plan_sha256"] == digest({k: v for k, v in p.items() if k != "plan_sha256"})


def test_duplicate_purge_removes_earlier_group_and_never_later_rows():
    data = list(rows())
    data[-1] = data[-1].model_copy(update={"duplicate_component": data[0].duplicate_component})
    p = plan_temporal_diagnostic(data, cutoff_utc="2026-09-05T00:00:00+00:00")
    assert p["excluded_earlier_ids"] == ["s0"]
    assert p["crossing_duplicate_components"] == 1
    assert "s0" not in p["fit_ids"] and "s7" in p["evaluation_ids"]


def test_separating_channels_reports_no_support_rather_than_relaxing_cut():
    p = plan_temporal_diagnostic(rows(), cutoff_utc="2026-09-05T00:00:00Z", separate_channels=True)
    assert p["fit_ids"] == []
    assert p["remaining_overlapping_channels"] == []
    assert p["support_status"] == "blocked_support"
    assert "empty:earlier_fit" in p["support_blockers"]


@pytest.mark.parametrize("cutoff", ["2026-08-01T00:00:00Z", "2026-10-01T00:00:00Z"])
def test_empty_side_is_explicit_and_not_an_evaluation(cutoff):
    p = plan_temporal_diagnostic(rows(), cutoff_utc=cutoff)
    assert p["support_status"] == "blocked_support"
    assert any(reason.startswith("empty:") for reason in p["support_blockers"])


@pytest.mark.parametrize("cutoff", ["2026-09-05", "2026-09-05T00:00:00-03:00", "invalid"])
def test_naive_or_non_utc_cutoffs_rejected(cutoff):
    with pytest.raises(ExperimentError, match="temporal_requires_explicit_utc"):
        plan_temporal_diagnostic(rows(), cutoff_utc=cutoff)


def test_test_partition_outcomes_and_unsorted_ids_cannot_enter_metadata_contract():
    data = rows()
    for changes in ({"source_partition": "test"}, {"view_count": 13}):
        with pytest.raises(ValidationError):
            TemporalRow.model_validate(data[0].model_dump() | changes)
    with pytest.raises(ExperimentError, match="sorted_development_ids"):
        plan_temporal_diagnostic(data[::-1], cutoff_utc="2026-09-05T00:00:00Z")


def test_original_target_horizon_stays_30_to_less_than_37_and_no_file_io(monkeypatch):
    data = rows()
    wrong = data[0].model_copy(update={"observed_at_utc": "2026-10-08T00:00:00Z"})
    with pytest.raises(ExperimentError, match="temporal_target_age_mismatch"):
        plan_temporal_diagnostic((wrong, *data[1:]), cutoff_utc="2026-09-05T00:00:00Z")

    def fail(*a, **kw):
        raise AssertionError("unexpected file access")

    monkeypatch.setattr("builtins.open", fail)
    p = plan_temporal_diagnostic(data, cutoff_utc="2026-09-05T00:00:00Z")
    assert p["support"]["earlier_fit"]["age_bands_days"]["[32,34)"] == 4

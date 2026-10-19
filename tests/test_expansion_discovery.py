import copy
import json
from datetime import UTC, datetime, timedelta

import pytest

from scripts.channel_partitions import Reference, create_partitions
from scripts.expand_reference_pool import (
    QUERIES,
    AuditedClient,
    bind_checkpoint,
    discover,
    ordered_candidates,
    validate_parent_metadata,
)
from scripts.observed_baseline import freeze_cohort
from scripts.private_checkpoint import save
from tests.test_observed_baseline import pilot_records

NOW = datetime(2026, 10, 19, tzinfo=UTC)


def candidate(i, channel=None, views=100):
    return {
        "audit": {
            "video_id": f"video_{i:05d}",
            "channel_id": channel or f"channel_{i}",
            "published_at_utc": (NOW - timedelta(days=33)).isoformat(),
            "observed_at_utc": NOW.isoformat(),
        },
        "metadata": {"duration_iso8601": "PT30S"},
        "curation": {"youtube_license": "youtube"},
        "target": {"view_count_observed": views},
    }


def test_order_is_invariant_to_outcomes_language_titles_and_input_order():
    rows = [candidate(i, channel=f"channel_{i // 3}") for i in range(12)]
    expected = [r["audit"]["video_id"] for r in ordered_candidates(rows, set(), set())]
    changed = copy.deepcopy(rows)
    for i, row in enumerate(changed):
        row["target"]["view_count_observed"] = (i + 1) * 1_000_000
        row["curation"].update(title="maquiagem", declared_audio_language="pt-BR")
    actual = ordered_candidates(list(reversed(changed)), set(), set())
    assert [r["audit"]["video_id"] for r in actual] == expected
    assert len({r["audit"]["channel_id"] for r in actual[:4]}) == 4


def test_old_channels_controls_invalid_age_and_unavailable_counts_are_filtered():
    rows = [candidate(i) for i in range(6)]
    rows[3]["audit"]["published_at_utc"] = (NOW - timedelta(days=37)).isoformat()
    rows[4]["target"]["view_count_observed"] = None
    rows[5]["metadata"]["duration_iso8601"] = "PT61S"
    result = ordered_candidates(rows, {rows[1]["audit"]["video_id"]}, {"channel_0"})
    assert result == [rows[2]]


def test_channels_allocated_and_old_channels_filtered_before_statistics(tmp_path, monkeypatch):
    class Client:
        def __init__(self):
            self.calls = []

        def get(self, resource, params):
            assert resource == "search" and params["order"] == "date"
            self.calls.append((resource, params))
            return {
                "items": [
                    {"id": {"videoId": "new"}, "snippet": {"channelId": "new_channel"}},
                    {"id": {"videoId": "old"}, "snippet": {"channelId": "test_channel"}},
                    {"id": {"videoId": "control"}, "snippet": {"channelId": "control_channel"}},
                ]
            }, NOW.isoformat()

    def collect(client, channels, pages, **kwargs):
        assert channels == ["new_channel"]
        allocation = json.loads((tmp_path / "channel-allocation.json").read_bytes())
        assert allocation["allocation_before_outcomes"]
        assert set(allocation["channel_allocation"]) == {"new_channel"}
        assert pages == 2
        return {"records": [candidate(0, "new_channel")], "channels": []}

    monkeypatch.setattr("scripts.expand_reference_pool.collect", collect)
    result = discover(Client(), {"test_channel"}, {"control"}, tmp_path, NOW)
    assert result["candidates"] == 1
    assert result["calls"] == len(QUERIES) <= 20
    assert result["selection_uses_views"] is False


def test_equal_size_stale_manifest_is_rejected_before_collection(tmp_path):
    records, _ = pilot_records()
    release = freeze_cohort(records, tmp_path / "parent", source_snapshot_sha256="a" * 64)
    references = [r.model_dump(include=set(Reference.model_fields)) for r in release.records]
    manifest = create_partitions(references, data_kind="observed_pilot")
    validate_parent_metadata(release, manifest)
    references[0]["media_sha256"] = "f" * 64
    stale = create_partitions(references, data_kind="observed_pilot")
    assert len(stale.assignments) == len(release.records)
    with pytest.raises(ValueError, match="parent_cohort_partition_mismatch"):
        validate_parent_metadata(release, stale)


def test_resume_refuses_changed_parent_protocol_without_modifying_checkpoint(tmp_path):
    provenance = {
        "cohort_sha256": "a" * 64,
        "partition_sha256": "b" * 64,
        "protocol_sha256": "c" * 64,
    }
    bind_checkpoint(tmp_path, provenance, resume=False)
    original = (tmp_path / "parent.json").read_bytes()
    bind_checkpoint(tmp_path, provenance, resume=True)
    for key in provenance:
        with pytest.raises(ValueError, match="expansion_checkpoint_parent_mismatch"):
            bind_checkpoint(tmp_path, provenance | {key: "d" * 64}, resume=True)
        assert (tmp_path / "parent.json").read_bytes() == original
    with pytest.raises(ValueError, match="expansion_checkpoint_already_exists"):
        bind_checkpoint(tmp_path, provenance, resume=False)


def test_cached_calls_preserve_observation_and_do_not_reset_total_request_budget(tmp_path):
    (tmp_path / "calls").mkdir()
    call = {
        "resource": "search",
        "params": {"q": "look"},
        "received_at_utc": NOW.isoformat(),
        "response": {"items": []},
    }
    save(tmp_path / "calls/0001.json", call)
    client = AuditedClient("synthetic", tmp_path, max_calls=1)
    # The base client refuses the next request before it could access the network.
    assert client.get("search", {"q": "look"}) == ({"items": []}, NOW.isoformat())
    with pytest.raises(RuntimeError, match="API request budget reached"):
        client.get("search", {"q": "maquiagem"})
    assert len(client.calls) == 1
    assert json.loads((tmp_path / "calls/0001.json").read_bytes()) == call


def test_failed_requests_also_consume_persisted_budget(tmp_path, monkeypatch):
    (tmp_path / "calls").mkdir()
    seen = []

    def fail(*args):
        seen.append(True)
        raise RuntimeError("Network failure while querying YouTube search")

    monkeypatch.setattr("scripts.collect_channel_metadata.Client.get", fail)
    client = AuditedClient("synthetic", tmp_path, max_calls=1)
    with pytest.raises(RuntimeError, match="Network failure"):
        client.get("search", {"q": "look"})
    restored = AuditedClient("synthetic", tmp_path, max_calls=1)
    with pytest.raises(RuntimeError, match="API request budget reached"):
        restored.get("search", {"q": "look"})
    assert seen == [True]
    assert restored.attempts[0]["status"] == "failed"


def test_http429_is_terminal_across_resume_before_any_network_call(tmp_path, monkeypatch):
    (tmp_path / "calls").mkdir()
    seen = []

    def fail(*args):
        seen.append(True)
        raise RuntimeError("YouTube search returned HTTP 429")

    monkeypatch.setattr("scripts.collect_channel_metadata.Client.get", fail)
    client = AuditedClient("synthetic", tmp_path, max_calls=3)
    with pytest.raises(RuntimeError, match="HTTP 429"):
        client.get("search", {"q": "look"})
    with pytest.raises(ValueError, match="source_stopped_http_429"):
        AuditedClient("synthetic", tmp_path, max_calls=3)
    assert seen == [True]
    assert client.attempts[0]["stop_reason"] == "http_429"
    # Explicit recovery records the operator's decision; it never resets the budget.
    resumed = AuditedClient("synthetic", tmp_path, max_calls=3, source_recovered=True)
    assert len(resumed.attempts) == 1 and seen == [True]
    assert json.loads((tmp_path / "source-state.json").read_bytes())[
        "operator_confirmed_source_recovery"
    ]


def test_legacy_http429_checkpoint_is_also_terminal(tmp_path):
    (tmp_path / "calls").mkdir()
    save(tmp_path / "failure.json", {"reason": "YouTube search returned HTTP 429"})
    with pytest.raises(ValueError, match="source_stopped_http_429"):
        AuditedClient("synthetic", tmp_path)


def test_only_new_requests_are_paced_cache_does_not_wait(tmp_path, monkeypatch):
    (tmp_path / "calls").mkdir()
    events = []

    def get(client, resource, params):
        events.append("request")
        call = {
            "resource": resource,
            "params": params,
            "received_at_utc": NOW.isoformat(),
            "response": {},
        }
        client.calls.append(call)
        return {}, NOW.isoformat()

    monkeypatch.setattr("scripts.collect_channel_metadata.Client.get", get)
    monkeypatch.setattr("scripts.expand_reference_pool.time.monotonic", lambda: 1.0)
    monkeypatch.setattr("scripts.expand_reference_pool.time.sleep", lambda n: events.append(n))
    client = AuditedClient("synthetic", tmp_path, request_interval_seconds=2.0)
    client.get("search", {"q": "look"})
    client.get("search", {"q": "look"})
    client.get("search", {"q": "batom"})
    assert events == ["request", 2.0, "request"]

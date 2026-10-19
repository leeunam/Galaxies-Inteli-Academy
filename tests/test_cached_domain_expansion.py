import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from scripts.cached_domain_expansion import discover
from scripts.channel_partitions import new_channel_partition
from scripts.expand_reference_pool import QUERIES
from scripts.private_checkpoint import digest, file_hash, save
from scripts.targeted_expansion import migrate


def fixture(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    pool = tmp_path / "data/private/pool"
    pool.mkdir(parents=True)
    save(tmp_path / "data/private/vinte-candidatos-20261017-v2.records.json", [])
    now = datetime(2026, 10, 19, tzinfo=UTC)
    window = [(now - timedelta(days=d)).isoformat() for d in (37, 30)]
    save(
        pool / "candidates.json",
        {
            "records": [{"audit": {"video_id": "already_observed"}}],
            "window": window,
            "channel_allocation": {"existing": new_channel_partition("existing")},
        },
    )
    addon = tmp_path / "addon.md"
    addon.write_text("synthetic")
    parent = SimpleNamespace(
        records=[SimpleNamespace(sample_id="reserved_id", channel_id="reserved_channel")]
    )
    call = {
        "resource": "search",
        "params": {
            "part": "snippet",
            "type": "video",
            "q": "maquiagem",
            "order": "date",
            "maxResults": 50,
            "publishedAfter": window[0],
            "publishedBefore": window[1],
            "videoDuration": "short",
            "relevanceLanguage": "pt",
            "regionCode": "BR",
            "fields": "items(id/videoId,snippet/channelId)",
        },
        "response": {
            "items": [
                {"id": {"videoId": vid}, "snippet": {"channelId": ch}}
                for vid, ch in (
                    ("reserved_id", "reserved_channel"),
                    ("other_reserved_channel_video", "reserved_channel"),
                    ("already_observed", "existing"),
                    ("new00000001", "new_channel"),
                    ("new00000002", "new_channel2"),
                )
            ]
        },
    }
    for i, query in enumerate(QUERIES, 1):
        call["params"]["q"] = query
        save(pool / "calls" / f"{i:04d}.json", call)
    call["params"]["q"] = QUERIES[0]

    class Client:
        def __init__(self):
            self.calls = []
            self.attempts = []
            self.views = 100
            self.cached = {}

        def get(self, resource, params):
            assert resource == "videos"  # No new searches.
            assert set(params["id"].split(",")) == {"new00000001", "new00000002"}
            self.cached[digest([resource, params])] = True
            allocation = json.loads((pool / "cached-domain/channel-allocation.json").read_bytes())
            assert allocation["allocation_before_outcomes"]
            assert allocation["channel_allocation"]["existing"] == new_channel_partition("existing")
            items = []
            for i, vid in enumerate(params["id"].split(",")):
                ch = "new_channel" + ("2" if vid.endswith("2") else "")
                assert allocation["channel_allocation"][ch] == new_channel_partition(ch)
                items.append(
                    {
                        "id": vid,
                        "snippet": {
                            "channelId": ch,
                            "publishedAt": (now - timedelta(days=33)).isoformat(),
                        },
                        "contentDetails": {"duration": "PT30S"},
                        "statistics": {"viewCount": str(self.views + i)},
                        "status": {"license": "youtube"},
                    }
                )
            return {"items": items}, now.isoformat()

    return pool, addon, parent, Client(), call


def test_cached_domain_excludes_observed_ids_and_reserved_channels_before_statistics(
    tmp_path, monkeypatch
):
    pool, addon, parent, client, _ = fixture(tmp_path, monkeypatch)
    result = discover(client, parent, pool, addon)
    assert len(result["records"]) == 2
    assert result["new_search_requests"] == 0 and not result["selection_uses_views"]
    assert len(result["cached_search_sources"]) == len(QUERIES)
    client.views = 9999999
    again = discover(client, parent, pool, addon)
    assert [r["audit"] for r in result["records"]] == [r["audit"] for r in again["records"]]


def test_cached_domain_rejects_changed_allocation_before_request(tmp_path, monkeypatch):
    pool, addon, parent, client, _ = fixture(tmp_path, monkeypatch)
    discover(client, parent, pool, addon)
    path = pool / "cached-domain/channel-allocation.json"
    state = json.loads(path.read_bytes())
    state["channel_allocation"]["existing"] = "test"
    save(path, state)
    with pytest.raises(ValueError, match="allocation_changed"):
        discover(client, parent, pool, addon)


def test_cached_domain_refuses_other_window_queries(tmp_path, monkeypatch):
    pool, addon, parent, client, call = fixture(tmp_path, monkeypatch)
    call["params"]["publishedBefore"] = "2000-01-01T00:00:00Z"
    save(pool / "calls/0001.json", call)
    with pytest.raises(ValueError, match="no_frozen_domain_searches"):
        discover(client, parent, pool, addon)


@pytest.mark.parametrize(
    ("key", "value"),
    [("pageToken", "next"), ("regionCode", "US"), ("type", "channel"), ("maxResults", 5)],
)
def test_cached_domain_refuses_other_search_signatures(tmp_path, monkeypatch, key, value):
    pool, addon, parent, client, call = fixture(tmp_path, monkeypatch)
    call["params"][key] = value
    save(pool / "calls/0001.json", call)
    with pytest.raises(ValueError, match="no_frozen_domain_searches"):
        discover(client, parent, pool, addon)


@pytest.mark.parametrize("changed", ["source", "discovery"])
def test_migration_checks_discovery_receipt_and_cached_source_hashes(
    tmp_path, monkeypatch, changed
):
    pool, addon, parent, client, _ = fixture(tmp_path, monkeypatch)
    discover(client, parent, pool, addon)
    before = file_hash(pool / "candidates.json")
    save(
        pool / "extraction/checkpoint.json",
        {"halt_reason": None, "selection_sha256": before, "videos": []},
    )
    if changed == "source":
        save(pool / "calls/0001.json", {"changed": True})
    else:
        path = pool / "cached-domain/candidates.json"
        data = json.loads(path.read_bytes())
        data["remaining_language_priority"] = False
        save(path, data)
    with pytest.raises(
        ValueError, match="cached_search_source_changed|cached_discovery_receipt_changed"
    ):
        migrate(pool, addon, namespace="cached-domain")
    assert file_hash(pool / "candidates.json") == before


def test_partial_discovery_recreates_receipt_from_exact_cached_responses(tmp_path, monkeypatch):
    pool, addon, parent, client, _ = fixture(tmp_path, monkeypatch)
    original_save = save

    def fail_receipt(path, value):
        if path.name == "discovery-receipt.json":
            raise OSError("synthetic receipt failure")
        original_save(path, value)

    monkeypatch.setattr("scripts.cached_domain_expansion.save", fail_receipt)
    with pytest.raises(OSError):
        discover(client, parent, pool, addon)
    before = file_hash(pool / "cached-domain/candidates.json")
    monkeypatch.setattr("scripts.cached_domain_expansion.save", original_save)
    result = discover(client, parent, pool, addon)
    assert file_hash(pool / "cached-domain/candidates.json") == before
    assert len(result["records"]) == 2
    assert (
        json.loads((pool / "cached-domain/discovery-receipt.json").read_bytes())["discovery_sha256"]
        == before
    )

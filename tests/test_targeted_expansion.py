import copy

import pytest

from scripts.channel_partitions import new_channel_partition
from scripts.targeted_expansion import migrated_plan


def fixtures():
    old = {
        "records": [
            {"audit": {"video_id": f"old{i}"}, "target": {"view_count_observed": i}}
            for i in range(3)
        ],
        "channel_allocation": {"old_new_channel": new_channel_partition("old_new_channel")},
    }
    new = {
        "records": [{"audit": {"video_id": "targeted"}, "target": {"view_count_observed": 999}}],
        "channel_allocation": old["channel_allocation"]
        | {"targeted_channel": new_channel_partition("targeted_channel")},
        "parent_selection_sha256": "a" * 64,
        "addon_sha256": "b" * 64,
    }
    state = {
        "halt_reason": None,
        "videos": [{"video_id": "old1", "review": {"decision": "included"}}],
    }
    return old, new, state


def test_new_domain_candidates_go_after_frozen_attempts_before_untried_broad_pool():
    old, new, state = fixtures()
    before = copy.deepcopy(old)
    child = migrated_plan(old, new, state)
    assert [r["audit"]["video_id"] for r in child["records"]] == [
        "old1",
        "targeted",
        "old0",
        "old2",
    ]
    assert child["records"][0] == old["records"][1]
    assert old == before
    new["records"][0]["target"]["view_count_observed"] = 1
    other = migrated_plan(old, new, state)
    assert [r["audit"]["video_id"] for r in other["records"]] == [
        r["audit"]["video_id"] for r in child["records"]
    ]


@pytest.mark.parametrize("change", ["duplicate", "partition", "pending", "halt"])
def test_migration_rejects_refreshed_observation_partition_change_and_pending_work(change):
    old, new, state = fixtures()
    if change == "duplicate":
        new["records"][0]["audit"]["video_id"] = "old0"
    if change == "partition":
        new["channel_allocation"]["old_new_channel"] = "test"
    if change == "pending":
        state["videos"][0].pop("review")
    if change == "halt":
        state["halt_reason"] = "http_access_denied_or_rate_limited"
    with pytest.raises(ValueError):
        migrated_plan(old, new, state)


def test_migration_recovers_after_queue_update_before_checkpoint_without_api(tmp_path, monkeypatch):
    import json

    from scripts.private_checkpoint import file_hash, save
    from scripts.targeted_expansion import migrate

    pool = tmp_path / "data/private/pool"
    (pool / "targeted").mkdir(parents=True)
    (pool / "extraction").mkdir()
    addon = tmp_path / "addon.md"
    addon.write_text("synthetic approved adaptation")
    old, new, state = fixtures()
    save(pool / "candidates.json", old)
    parent_hash = file_hash(pool / "candidates.json")
    new.update(parent_selection_sha256=parent_hash, addon_sha256=file_hash(addon))
    save(pool / "targeted/candidates.json", new)
    state["selection_sha256"] = parent_hash
    save(pool / "extraction/checkpoint.json", state)
    original_save = save
    failed = []

    def fail(path, value):
        if path == pool / "extraction/checkpoint.json" and not failed:
            failed.append(True)
            raise OSError("synthetic interruption")
        original_save(path, value)

    monkeypatch.setattr("scripts.targeted_expansion.save", fail)
    with pytest.raises(OSError, match="synthetic interruption"):
        migrate(pool, addon)
    assert file_hash(pool / "candidates.json") != parent_hash
    assert (
        json.loads((pool / "extraction/checkpoint.json").read_bytes())["selection_sha256"]
        == parent_hash
    )
    monkeypatch.setattr("scripts.targeted_expansion.save", original_save)
    summary = migrate(pool, addon)
    assert summary["attempts_preserved"] == 1 and summary["new_candidates_prioritized"] == 1
    assert json.loads((pool / "extraction/checkpoint.json").read_bytes())[
        "selection_sha256"
    ] == file_hash(pool / "candidates.json")
    assert migrate(pool, addon) == summary


def test_topic_search_filters_old_channels_before_any_statistics_and_freezes_new_allocation(
    tmp_path, monkeypatch
):
    import json
    from datetime import UTC, datetime, timedelta
    from types import SimpleNamespace

    from scripts.private_checkpoint import save
    from scripts.targeted_expansion import QUERIES, discover

    root = tmp_path
    pool = root / "data/private/pool"
    pool.mkdir(parents=True)
    monkeypatch.chdir(root)
    save(root / "data/private/vinte-candidatos-20261017-v2.records.json", [])
    now = datetime(2026, 10, 19, tzinfo=UTC)
    save(
        pool / "candidates.json",
        {
            "records": [],
            "window": [
                (now - timedelta(days=37)).isoformat(),
                (now - timedelta(days=30)).isoformat(),
            ],
            "channel_allocation": {},
        },
    )
    addon = root / "addon.md"
    addon.write_text("synthetic")
    parent = SimpleNamespace(
        records=[SimpleNamespace(sample_id="old_test_id", channel_id="old_test_channel")]
    )

    class Client:
        def __init__(self):
            self.cached = {}
            self.calls = []
            self.attempts = []

        def get(self, resource, params):
            self.calls.append({"resource": resource, "params": params})
            self.attempts.append({"resource": resource})
            if resource == "search":
                i = len([a for a in self.attempts if a["resource"] == "search"])
                assert params["topicId"] in {"/m/032tl", "/m/041xxh"} and params["order"] == "date"
                return {
                    "items": [
                        {
                            "id": {"videoId": f"new{i:08d}"},
                            "snippet": {"channelId": f"new_channel{i}"},
                        },
                        {
                            "id": {"videoId": "old_test_id"},
                            "snippet": {"channelId": "old_test_channel"},
                        },
                    ]
                }, now.isoformat()
            assert resource == "videos" and "old_test_id" not in params["id"]
            allocation = json.loads((pool / "targeted/channel-allocation.json").read_bytes())
            assert allocation["allocation_before_outcomes"]
            items = []
            for vid in params["id"].split(","):
                i = int(vid[3:])
                channel = f"new_channel{i}"
                assert allocation["channel_allocation"][channel] == new_channel_partition(channel)
                items.append(
                    {
                        "id": vid,
                        "snippet": {
                            "channelId": channel,
                            "publishedAt": (now - timedelta(days=33)).isoformat(),
                            "title": "synthetic",
                        },
                        "contentDetails": {"duration": "PT30S"},
                        "statistics": {"viewCount": "100"},
                        "status": {"license": "youtube"},
                    }
                )
            return {"items": items}, now.isoformat()

    client = Client()
    result = discover(client, parent, pool, addon)
    assert len(result["records"]) == len(QUERIES) == 8
    assert not result["selection_uses_views"]

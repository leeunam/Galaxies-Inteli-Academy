import copy
import json
from datetime import UTC, datetime, timedelta

from scripts.expand_reference_pool import QUERIES, discover, ordered_candidates

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

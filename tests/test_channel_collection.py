import pytest

from scripts import collect_channel_metadata as collector
from scripts.collect_channel_metadata import channel_filter, collect, normalize_video


def test_channel_urls_are_parsed_without_requesting_arbitrary_hosts():
    assert channel_filter("https://www.youtube.com/@example/shorts") == {"forHandle": "@example"}
    for ref in [
        "https://youtube.com.evil.test/@example",
        "http://youtube.com/@example",
        "https://name:secret@youtube.com/@example",
        "https://youtube.com/watch?v=example",
    ]:
        with pytest.raises(ValueError):
            channel_filter(ref)


def test_outcomes_and_audit_are_separate_and_missing_likes_are_not_zero():
    item = {
        "id": "abc12345678",
        "snippet": {"channelId": "channel-a", "publishedAt": "2026-09-14T00:00:00Z"},
        "statistics": {"viewCount": "0"},
        "contentDetails": {"duration": "PT30S"},
    }
    row = normalize_video(item, "2026-10-17T00:00:00Z")
    assert row["target"]["view_count_observed"] == 0
    assert row["diagnostics"]["like_count_observed"] is None
    assert row["audit"]["channel_id"] == "channel-a"
    assert "channel_id" not in row["metadata"]
    assert "tags" not in str(row)


def test_collection_reports_partial_pagination_and_unavailable_video():
    class FakeClient:
        def __init__(self):
            self.calls = []

        def get(self, resource, params):
            self.calls.append({"resource": resource})
            if resource == "channels":
                return {
                    "items": [
                        {
                            "id": "channel-a",
                            "contentDetails": {"relatedPlaylists": {"uploads": "uploads"}},
                        }
                    ]
                }, "now"
            if resource == "playlistItems":
                return {
                    "items": [{"contentDetails": {"videoId": "missing"}}],
                    "nextPageToken": "next",
                }, "now"
            return {"items": []}, "now"

    result = collect(FakeClient(), ["https://youtube.com/@example"], pages_per_channel=1)
    assert result["channels"][0]["coverage_partial"]
    assert result["unavailable_video_ids"] == ["missing"]
    assert result["records"] == []


def test_existing_output_stops_before_reading_key_or_spending_quota(tmp_path, monkeypatch):
    output = tmp_path / "data/private/existing.json"
    output.parent.mkdir(parents=True)
    output.write_text("previous evidence")
    monkeypatch.setattr(collector, "ROOT", tmp_path)
    monkeypatch.setattr(
        "sys.argv", ["collector", "https://youtube.com/@example", "--output", str(output)]
    )

    def forbidden_key_read():
        raise AssertionError("Existing output must be rejected before accessing credentials")

    monkeypatch.setattr(collector, "api_key", forbidden_key_read)
    with pytest.raises(SystemExit) as exc:
        collector.main()
    assert exc.value.code == 2
    assert output.read_text() == "previous evidence"

from datetime import UTC, datetime

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


WINDOW = (datetime(2026, 9, 11, tzinfo=UTC), datetime(2026, 9, 18, tzinfo=UTC))


class UploadClient:
    def __init__(self, pages, videos=()):
        self.pages = iter(pages)
        self.videos = list(videos)
        self.calls = []

    def get(self, resource, params):
        self.calls.append({"resource": resource, "params": params})
        if resource == "channels":
            body = {
                "items": [
                    {
                        "id": "channel-a",
                        "contentDetails": {"relatedPlaylists": {"uploads": "uploads"}},
                    }
                ]
            }
        elif resource == "playlistItems":
            body = next(self.pages)
        else:
            body = {"items": self.videos}
        return body, "2026-10-18T00:00:00Z"


def uploaded(video_id, published=None):
    # Addition time is deliberately unrelated to the video's publication date.
    return {
        "snippet": {"publishedAt": "2050-01-01T00:00:00Z"},
        "contentDetails": {"videoId": video_id, "videoPublishedAt": published},
    }


def video(video_id, published="2026-09-15T00:00:00Z"):
    return {
        "id": video_id,
        "snippet": {"channelId": "channel-a", "publishedAt": published},
        "contentDetails": {"duration": "PT30S"},
        "statistics": {"viewCount": "0"},
    }


def test_upload_date_window_skips_known_outcomes_and_uses_video_publication():
    client = UploadClient(
        [
            {
                "items": [
                    uploaded("known", "2026-09-15T00:00:00Z"),
                    uploaded("start", "2026-09-11T00:00:00Z"),
                    uploaded("end", "2026-09-18T00:00:00Z"),
                    uploaded("inside", "2026-09-15T00:00:00Z"),
                    uploaded("future", "2026-09-19T00:00:00Z"),
                    uploaded("missing"),
                    uploaded("naive", "2026-09-15T00:00:00"),
                ]
            }
        ],
        [video("end", "2026-09-18T00:00:00Z"), video("inside")],
    )
    result = collect(
        client,
        ["https://youtube.com/@example"],
        1,
        publication_window=WINDOW,
        existing_video_ids={"known"},
    )
    request = next(c for c in client.calls if c["resource"] == "videos")
    assert set(request["params"]["id"].split(",")) == {"inside", "end"}
    assert {r["audit"]["video_id"] for r in result["records"]} == {"inside", "end"}
    assert result["filtered_playlist_items"] == {
        "existing": 1,
        "outside_window": 2,
        "missing_publication": 2,
    }
    assert not result["training_partition_created"]


def test_an_old_page_does_not_prove_that_the_remaining_uploads_are_old():
    client = UploadClient(
        [
            {"items": [uploaded("old", "2020-01-01T00:00:00Z")], "nextPageToken": "next"},
            {"items": [uploaded("inside", "2026-09-15T00:00:00Z")]},
        ],
        [video("inside")],
    )
    result = collect(client, ["https://youtube.com/@example"], 2, publication_window=WINDOW)
    assert len(result["records"]) == 1
    assert result["channels"][0]["pages_read"] == 2
    assert not result["channels"][0]["coverage_partial"]
    assert client.calls[2]["params"]["pageToken"] == "next"


def test_authoritative_video_date_is_checked_without_calling_it_unavailable():
    client = UploadClient(
        [{"items": [uploaded("changed", "2026-09-15T00:00:00Z")]}],
        [video("changed", "2026-01-01T00:00:00Z")],
    )
    result = collect(client, ["https://youtube.com/@example"], 1, publication_window=WINDOW)
    assert result["records"] == []
    assert result["unavailable_video_ids"] == []
    assert result["incompatible_publication_video_ids"] == ["changed"]


def test_known_observations_are_not_refetched_even_without_a_date_filter():
    client = UploadClient([{"items": [uploaded("known")]}])
    result = collect(client, ["https://youtube.com/@example"], 1, existing_video_ids={"known"})
    assert [c["resource"] for c in client.calls] == ["channels", "playlistItems"]
    assert result["records"] == []


@pytest.mark.parametrize(
    "bounds",
    [
        (datetime(2026, 9, 11), WINDOW[1]),
        (WINDOW[1], WINDOW[0]),
        (WINDOW[0],),
    ],
)
def test_invalid_publication_bounds_are_rejected_before_requests(bounds):
    client = UploadClient([])
    with pytest.raises(ValueError):
        collect(client, ["https://youtube.com/@example"], 1, publication_window=bounds)
    assert not client.calls


@pytest.mark.parametrize("pages", [0, 6, True])
def test_invalid_page_limits_are_rejected_before_requests(pages):
    client = UploadClient([])
    with pytest.raises(ValueError):
        collect(client, ["https://youtube.com/@example"], pages)
    assert not client.calls


def test_api_failure_is_not_retried_or_converted_to_an_empty_success():
    class FailedClient(UploadClient):
        def get(self, resource, params):
            if resource == "playlistItems":
                self.calls.append({"resource": resource})
                raise RuntimeError("YouTube playlistItems returned HTTP 403")
            return super().get(resource, params)

    client = FailedClient([])
    with pytest.raises(RuntimeError, match="HTTP 403"):
        collect(client, ["https://youtube.com/@example"], 5, publication_window=WINDOW)
    assert len(client.calls) == 2

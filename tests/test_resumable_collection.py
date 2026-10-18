import json

import pytest

from scripts import resumable_channel_collection as collector

CHANNEL = "UC" + "a" * 22
REFERENCES = ["https://youtube.com/@example"]
IDS = ["abcdefghijk", "12345678901", "zyxwvutsrqp"]


class API:
    def __init__(self, fail_at=None):
        self.calls = []
        self.fail_at = fail_at

    def get(self, resource, params):
        self.calls.append((resource, params))
        if len(self.calls) == self.fail_at:
            raise RuntimeError("Network failure; signed URL and secret must never be persisted")
        if resource == "channels":
            body = {
                "items": [
                    {"id": CHANNEL, "contentDetails": {"relatedPlaylists": {"uploads": "uploads"}}}
                ]
            }
        elif resource == "playlistItems":
            ids = IDS[:2] if "pageToken" not in params else IDS[1:]
            body = {"items": [{"contentDetails": {"videoId": v}} for v in ids]}
            if "pageToken" not in params:
                body["nextPageToken"] = "page-2"
        else:
            body = {
                "items": [
                    {
                        "id": v,
                        "snippet": {
                            "channelId": CHANNEL,
                            "publishedAt": "2026-09-14T00:00:00Z",
                            "title": "Title",
                        },
                        "contentDetails": {"duration": "PT30S"},
                        "statistics": {"viewCount": "5"},
                    }
                    for v in params["id"].split(",")
                    if v != IDS[2]
                ]
            }
        return body, "2026-10-17T00:00:00Z"


@pytest.fixture
def checkpoint(tmp_path, monkeypatch):
    monkeypatch.setattr(collector, "ROOT", tmp_path)
    return tmp_path / "data/private/checkpoint.json"


def run(api, checkpoint, **kwargs):
    return collector.collect_resumable(
        api, REFERENCES, 2, checkpoint, detail_batch_size=1, **kwargs
    )


def test_budget_resume_keeps_pages_and_deduplicates_details(checkpoint):
    first = run(API(), checkpoint, max_calls=2)
    assert first["request_count"] == first["invocation_requests"] == 2
    assert first["details_partial"] and first["channels"][0]["coverage_partial"]
    api = API()
    final = run(api, checkpoint, resume=True, max_calls=4)
    assert [r for r, _ in api.calls] == ["playlistItems", "videos", "videos", "videos"]
    assert final["request_count"] == 6
    assert final["status"] == "metadata_complete_within_page_limit"
    assert len(final["records"]) == 2 and final["unavailable_video_ids"] == [IDS[2]]
    assert not final["channels"][0]["coverage_partial"]
    assert final["channels"][0]["observed_publication_interval"] == [
        "2026-09-14T00:00:00Z",
        "2026-09-14T00:00:00Z",
    ]
    assert run(API(), checkpoint, resume=True)["invocation_requests"] == 0
    saved = checkpoint.read_text()
    assert "response" not in saved and "signed URL" not in saved
    assert checkpoint.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("fail_at", [3, 5])
def test_network_interruption_preserves_every_completed_unit(checkpoint, fail_at):
    with pytest.raises(RuntimeError):
        run(API(fail_at), checkpoint)
    saved = json.loads(checkpoint.read_text())
    assert saved["status"] == "interrupted_partial"
    assert saved["request_count"] == fail_at
    api = API()
    final = run(api, checkpoint, resume=True)
    assert final["status"] == "metadata_complete_within_page_limit"
    assert not any(r == "channels" for r, _ in api.calls)
    if fail_at == 5:
        assert [p["id"] for r, p in api.calls if r == "videos"] == sorted(IDS)[1:]


def test_fresh_call_and_incompatible_resume_do_not_spend_quota(checkpoint):
    run(API(), checkpoint, max_calls=1)
    api = API()
    with pytest.raises(ValueError, match="requires --resume"):
        run(api, checkpoint)
    with pytest.raises(ValueError, match="Incompatible"):
        collector.collect_resumable(api, REFERENCES, 1, checkpoint, resume=True)
    state = json.loads(checkpoint.read_text())
    state["protocol"] = "future-protocol"
    checkpoint.write_text(json.dumps(state))
    with pytest.raises(ValueError, match="Incompatible"):
        run(api, checkpoint, resume=True)
    assert api.calls == []


def test_page_limit_reports_partial_even_when_details_are_done(checkpoint):
    result = collector.collect_resumable(API(), REFERENCES, 1, checkpoint)
    assert result["channels"][0]["coverage_partial"]
    assert result["channels"][0]["pages_read"] == 1
    assert not result["details_partial"]


@pytest.mark.parametrize("options", [{"max_calls": 0}, {"detail_batch_size": 51}])
def test_invalid_limits_stop_before_requests(checkpoint, options):
    api = API()
    with pytest.raises(ValueError):
        collector.collect_resumable(api, REFERENCES, 2, checkpoint, **options)
    assert api.calls == []

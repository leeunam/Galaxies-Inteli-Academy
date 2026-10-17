"""Bounded channel-URL metadata collector. No audiovisual download, tags or training.

Records keep grouping/dates in audit and outcomes outside predictor inputs.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def channel_filter(reference: str) -> dict[str, str]:
    if re.fullmatch(r"UC[A-Za-z0-9_-]{22}", reference):
        return {"id": reference}
    parsed = urllib.parse.urlparse(reference)
    if parsed.scheme != "https" or parsed.hostname not in {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
    }:
        raise ValueError("Use an HTTPS YouTube channel URL with @handle or /channel/UC...")
    if parsed.username or parsed.password or parsed.port:
        raise ValueError("Channel URLs must not contain credentials or a custom port")
    parts = urllib.parse.unquote(parsed.path).strip("/").split("/")
    if parts[0].startswith("@") and len(parts[0]) > 1:
        return {"forHandle": parts[0]}
    if len(parts) >= 2 and parts[0] == "channel" and re.fullmatch(r"UC[A-Za-z0-9_-]{22}", parts[1]):
        return {"id": parts[1]}
    if len(parts) >= 2 and parts[0] == "user" and parts[1]:
        return {"forUsername": parts[1]}
    raise ValueError("Unrecognized channel reference; use its @handle or canonical channel ID")


def api_key() -> str:
    if value := os.environ.get("YOUTUBE_API_KEY"):
        return value
    for line in (ROOT / ".env").read_text().splitlines():
        name, sep, value = line.strip().partition("=")
        if sep and name.strip() == "YOUTUBE_API_KEY":
            value = value.strip().strip('"').strip("'")
            if value:
                return value
    raise ValueError("Configure YOUTUBE_API_KEY locally; never pass it on the command line")


class Client:
    def __init__(self, key: str, max_calls: int = 30):
        self.key = key
        self.max_calls = max_calls
        self.calls = []

    def get(self, resource: str, params: dict) -> tuple[dict, str]:
        if len(self.calls) >= self.max_calls:
            raise RuntimeError("API request budget reached")
        url = "https://www.googleapis.com/youtube/v3/" + resource
        request = urllib.request.Request(
            url + "?" + urllib.parse.urlencode(params),
            headers={"X-Goog-Api-Key": self.key, "Accept": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                body = json.load(response)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"YouTube {resource} returned HTTP {exc.code}") from None
        except (urllib.error.URLError, TimeoutError):
            raise RuntimeError(f"Network failure while querying YouTube {resource}") from None
        observed = datetime.now(UTC).isoformat()
        self.calls.append(
            {"resource": resource, "params": params, "received_at_utc": observed, "response": body}
        )
        return body, observed


def normalize_video(item: dict, observed: str) -> dict:
    snippet, stats = item["snippet"], item.get("statistics", {})
    return {
        "audit": {
            "video_id": item["id"],
            "channel_id": snippet["channelId"],
            "source_url": "https://www.youtube.com/watch?v=" + item["id"],
            "published_at_utc": snippet["publishedAt"],
            "observed_at_utc": observed,
        },
        "curation": {
            "title": snippet.get("title"),
            "declared_audio_language": snippet.get("defaultAudioLanguage"),
            "youtube_license": item.get("status", {}).get("license"),
            "sector_status": "unverified",
            "format_status": "unverified",
        },
        "metadata": {"duration_iso8601": item["contentDetails"]["duration"]},
        "target": {
            "view_count_observed": int(stats["viewCount"]) if "viewCount" in stats else None
        },
        "diagnostics": {
            "like_count_observed": int(stats["likeCount"]) if "likeCount" in stats else None
        },
        "audiovisual_features_status": "not_extracted",
    }


def collect(client: Client, references: list[str], pages_per_channel: int) -> dict:
    filters = [channel_filter(ref) for ref in references]
    video_ids, channels, seen_channels = set(), [], set()
    for ref, criteria in zip(references, filters, strict=True):
        body, _ = client.get(
            "channels",
            {
                "part": "contentDetails",
                **criteria,
                "fields": "items(id,contentDetails/relatedPlaylists/uploads)",
            },
        )
        if not body.get("items"):
            raise ValueError("Channel reference returned no accessible channel")
        channel = body["items"][0]
        if channel["id"] in seen_channels:
            continue
        seen_channels.add(channel["id"])
        playlist = channel["contentDetails"]["relatedPlaylists"]["uploads"]
        token, pages = None, 0
        for _ in range(pages_per_channel):
            params = {
                "part": "contentDetails",
                "playlistId": playlist,
                "maxResults": 50,
                "fields": "items(contentDetails/videoId),nextPageToken",
            }
            if token:
                params["pageToken"] = token
            body, _ = client.get("playlistItems", params)
            video_ids.update(x["contentDetails"]["videoId"] for x in body.get("items", []))
            pages += 1
            token = body.get("nextPageToken")
            if not token:
                break
        channels.append(
            {
                "channel_reference": ref,
                "channel_id": channel["id"],
                "pages_read": pages,
                "coverage_partial": bool(token),
            }
        )
    ids, records = sorted(video_ids), []
    for start in range(0, len(ids), 50):
        body, observed = client.get(
            "videos",
            {
                "part": "snippet,contentDetails,statistics,status",
                "id": ",".join(ids[start : start + 50]),
                "fields": "items(id,snippet(publishedAt,channelId,title,defaultAudioLanguage),contentDetails(duration),statistics(viewCount,likeCount),status(license))",
            },
        )
        records.extend(normalize_video(item, observed) for item in body.get("items", []))
    return {
        "status": "metadata_only",
        "channels": channels,
        "records": records,
        "unavailable_video_ids": sorted(video_ids - {r["audit"]["video_id"] for r in records}),
        "api_calls": client.calls,
        "request_count": len(client.calls),
        "training_partition_created": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("channels", nargs="+")
    parser.add_argument("--pages-per-channel", type=int, default=1, choices=range(1, 6))
    parser.add_argument("--max-api-calls", type=int, default=30)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # Validate every reference before reading credentials or making any request.
    for reference in args.channels:
        channel_filter(reference)
    private_root = (ROOT / "data").resolve()
    output = args.output.resolve()
    if not output.is_relative_to(private_root / "private") and not output.is_relative_to(
        private_root / "raw"
    ):
        parser.error("Output must be inside data/private or data/raw")
    if output.exists():
        parser.error("Output already exists; choose a fresh path before spending API quota")
    output.parent.mkdir(parents=True, exist_ok=True)
    if not os.access(output.parent, os.W_OK):
        parser.error("Output directory is not writable")
    key = api_key()
    result = collect(Client(key, args.max_api_calls), args.channels, args.pages_per_channel)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if key in payload:
        raise ValueError("Unexpected secret in response; output was not written")
    with output.open("x") as f:
        f.write(payload)
    print(
        json.dumps(
            {
                "status": result["status"],
                "channels": len(result["channels"]),
                "video_records": len(result["records"]),
                "api_requests": result["request_count"],
                "partial_channel_coverage": sum(c["coverage_partial"] for c in result["channels"]),
            }
        )
    )


if __name__ == "__main__":
    main()

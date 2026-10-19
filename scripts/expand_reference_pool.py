"""Bounded expansion discovery; freeze new channels before requesting their outcomes."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from scripts.channel_partitions import load_partitions, new_channel_partition
from scripts.collect_channel_metadata import Client, api_key, collect
from scripts.observed_baseline import CohortRelease
from scripts.private_checkpoint import digest, file_hash, private_path, save

QUERIES = (
    "look",
    "roupa",
    "vestido",
    "moda feminina",
    "moda masculina",
    "provador",
    "acessórios",
    "calçados",
    "maquiagem",
    "batom",
    "skincare",
    "cosmético",
    "perfume",
    "base maquiagem",
    "cuidados cabelo",
    "tutorial maquiagem",
)


def ordered_candidates(records, excluded_ids, excluded_channels):
    """Eligibility never uses the magnitude of views; hash/round-robin order only."""
    groups = defaultdict(dict)
    for row in records:
        audit = row["audit"]
        vid, channel = audit["video_id"], audit["channel_id"]
        if vid in excluded_ids or channel in excluded_channels:
            continue
        age = (
            datetime.fromisoformat(audit["observed_at_utc"])
            - datetime.fromisoformat(audit["published_at_utc"])
        ).total_seconds() / 86400
        match = re.fullmatch(
            r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", row["metadata"]["duration_iso8601"]
        )
        seconds = (
            sum(float(v or 0) * f for v, f in zip(match.groups(), (3600, 60, 1))) if match else 0
        )
        count = row["target"]["view_count_observed"]
        if (
            not 0 < seconds <= 60
            or not 30 <= age < 37
            or type(count) is not int
            or not 0 <= count <= 2**63 - 1
        ):
            continue
        if row["curation"].get("youtube_license") not in ("youtube", "creativeCommon"):
            continue
        previous = groups[channel].get(vid)
        if previous is None or audit["observed_at_utc"] < previous["audit"]["observed_at_utc"]:
            groups[channel][vid] = row
    channels = sorted(groups, key=lambda ch: digest(["expansion300-channel-order-v1", ch]))
    ordered = {
        ch: sorted(
            groups[ch].values(),
            key=lambda r: digest(["expansion300-video-order-v1", r["audit"]["video_id"]]),
        )
        for ch in channels
    }
    return [
        ordered[ch][i]
        for i in range(max((len(v) for v in ordered.values()), default=0))
        for ch in channels
        if i < len(ordered[ch])
    ]


def discover(client, old_channels, old_ids, destination, now):
    window = now - timedelta(days=37), now - timedelta(days=30)
    state = {
        "protocol": "expansion300-discovery-v1",
        "status": "discovering",
        "window": [d.isoformat() for d in window],
        "queries": QUERIES,
        "max_requests": 300,
        "max_search_requests": 20,
        "order": "date",
        "selection_uses_views": False,
        "records": [],
    }
    seeds = set()
    for query in QUERIES:
        body, _ = client.get(
            "search",
            {
                "part": "snippet",
                "type": "video",
                "q": query,
                "order": "date",
                "maxResults": 50,
                "publishedAfter": window[0].isoformat(),
                "publishedBefore": window[1].isoformat(),
                "videoDuration": "short",
                "relevanceLanguage": "pt",
                "regionCode": "BR",
                "fields": "items(id/videoId,snippet/channelId)",
            },
        )
        seeds.update(
            item["snippet"]["channelId"]
            for item in body.get("items", [])
            if item["snippet"]["channelId"] not in old_channels
            and item["id"]["videoId"] not in old_ids
        )
    channels = sorted(seeds, key=lambda ch: digest(["expansion300-channel-order-v1", ch]))[:80]
    if not channels:
        raise ValueError("no_new_seed_channels")
    # This file is published BEFORE collect requests any video statistics.
    state["channel_allocation"] = {ch: new_channel_partition(ch) for ch in channels}
    state["allocation_before_outcomes"] = True
    save(destination / "channel-allocation.json", state)
    result = collect(client, channels, 2, publication_window=window, existing_video_ids=old_ids)
    rows = ordered_candidates(result["records"], old_ids, old_channels)
    state.update(
        status="completed",
        records=rows,
        calls=len(client.calls),
        channels=result["channels"],
        candidates=len(rows),
    )
    save(destination / "candidates.json", state)
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = Path.cwd()
    output = private_path(args.output, root)
    if output.exists():
        parser.error("use a fresh output directory")
    parent = CohortRelease.model_validate_json((args.parent / "cohort.json").read_bytes())
    manifest = load_partitions(args.parent / "partitions.json")
    assert len(parent.records) == len(manifest.assignments) == 200
    old_channels = {r.channel_id for r in parent.records}
    old_ids = {r.sample_id for r in parent.records}
    # Original pilot controls are outside the frozen 200; use only their identities.
    controls = json.loads(
        (root / "data/private/vinte-candidatos-20261017-v2.records.json").read_bytes()
    )
    old_ids |= {r["audit"]["video_id"] for r in controls}
    output.mkdir(parents=True, mode=0o700)
    (output / "calls").mkdir(mode=0o700)
    save(
        output / "parent.json",
        {
            "cohort_sha256": parent.release_sha256,
            "partition_sha256": manifest.manifest_sha256,
            "protocol_sha256": file_hash(root / "docs/issue-3-expansao-300-protocolo.md"),
        },
    )

    class AuditedClient(Client):
        def get(self, resource, params):
            result = super().get(resource, params)
            save(output / "calls" / f"{len(self.calls):04d}.json", self.calls[-1])
            return result

    client = AuditedClient(api_key(), max_calls=300)
    try:
        state = discover(client, old_channels, old_ids, output, datetime.now(UTC))
        print(
            json.dumps(
                {
                    "status": state["status"],
                    "new_channels": len(state["channel_allocation"]),
                    "candidates": state["candidates"],
                    "api_calls": state["calls"],
                }
            )
        )
    except (RuntimeError, ValueError, OSError, KeyError) as exc:
        save(output / "failure.json", {"type": type(exc).__name__, "calls": len(client.calls)})
        print(
            json.dumps(
                {"status": "failed", "reason": type(exc).__name__, "calls": len(client.calls)}
            )
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

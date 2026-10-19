"""Discover directly from frozen domain search IDs without new search requests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.channel_partitions import load_partitions, new_channel_partition
from scripts.collect_channel_metadata import api_key, normalize_video
from scripts.expand_reference_pool import (
    QUERIES,
    AuditedClient,
    ordered_candidates,
    validate_parent_metadata,
)
from scripts.observed_baseline import CohortRelease
from scripts.private_checkpoint import digest, file_hash, private_path, save
from scripts.targeted_expansion import migrate


def discover(client, parent, pool, addon):
    old = json.loads((pool / "candidates.json").read_bytes())
    excluded_channels = {r.channel_id for r in parent.records}
    excluded_ids = {r.sample_id for r in parent.records} | {
        r["audit"]["video_id"] for r in old["records"]
    }
    controls = json.loads(
        (Path.cwd() / "data/private/vinte-candidatos-20261017-v2.records.json").read_bytes()
    )
    excluded_ids |= {r["audit"]["video_id"] for r in controls}
    channels = {}
    sources = []
    source_queries = []
    for path in sorted((pool / "calls").glob("*.json")):
        call = json.loads(path.read_bytes())
        params = call["params"]
        expected = {
            "part": "snippet",
            "type": "video",
            "q": params.get("q"),
            "order": "date",
            "maxResults": 50,
            "publishedAfter": old["window"][0],
            "publishedBefore": old["window"][1],
            "videoDuration": "short",
            "relevanceLanguage": "pt",
            "regionCode": "BR",
            "fields": "items(id/videoId,snippet/channelId)",
        }
        if call["resource"] != "search" or params.get("q") not in QUERIES or params != expected:
            continue
        sources.append({"file": path.name, "sha256": file_hash(path)})
        source_queries.append(params["q"])
        for item in call["response"].get("items", []):
            vid = item.get("id", {}).get("videoId")
            channel = item.get("snippet", {}).get("channelId")
            if not vid or not channel or vid in excluded_ids or channel in excluded_channels:
                continue
            if vid in channels and channels[vid] != channel:
                raise ValueError("cached_search_channel_disagreement")
            channels[vid] = channel
    if len(source_queries) != len(QUERIES) or set(source_queries) != set(QUERIES):
        raise ValueError("no_frozen_domain_searches")
    allocation = old["channel_allocation"] | {
        ch: new_channel_partition(ch) for ch in channels.values()
    }
    target = pool / "cached-domain"
    target.mkdir(mode=0o700, exist_ok=True)
    recovering = (target / "candidates.json").exists() and not (
        target / "discovery-receipt.json"
    ).exists()
    provenance = {
        "parent_selection_sha256": file_hash(pool / "candidates.json"),
        "addon_sha256": file_hash(addon),
        "cached_search_sources": sources,
    }
    allocation_path = target / "channel-allocation.json"
    frozen = provenance | {
        "allocation_before_outcomes": True,
        "channel_allocation": allocation,
    }
    if allocation_path.exists() and json.loads(allocation_path.read_bytes()) != frozen:
        raise ValueError("cached_domain_allocation_changed")
    save(allocation_path, frozen)
    rows = []
    ids = sorted(channels)
    for start in range(0, len(ids), 50):
        selected = ids[start : start + 50]
        params = {
            "part": "snippet,contentDetails,statistics,status",
            "id": ",".join(selected),
            "fields": "items(id,snippet(publishedAt,channelId,title,defaultAudioLanguage),contentDetails(duration),statistics(viewCount,likeCount),status(license))",
        }
        if recovering and digest(["videos", params]) not in client.cached:
            raise ValueError("partial_discovery_recovery_requires_cached_response")
        body, observed = client.get("videos", params)
        for item in body.get("items", []):
            vid = item.get("id")
            if vid not in selected or item.get("snippet", {}).get("channelId") != channels[vid]:
                continue
            rows.append(normalize_video(item, observed))
    result = provenance | {
        "protocol": "cached-domain-expansion-v1",
        "records": ordered_candidates(rows, excluded_ids, excluded_channels),
        "channel_allocation": allocation,
        "window": old["window"],
        "selection_uses_views": False,
        "remaining_language_priority": True,
        "new_search_requests": 0,
        "successful_calls_total": len(client.calls),
        "request_attempts_total": len(client.attempts),
    }
    if recovering:
        if json.loads((target / "candidates.json").read_bytes()) != result:
            raise ValueError("partial_discovery_changed")
    else:
        save(target / "candidates.json", result)
    save(
        target / "discovery-receipt.json",
        provenance | {"discovery_sha256": file_hash(target / "candidates.json")},
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["discover", "migrate"])
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--pool", type=Path, required=True)
    parser.add_argument(
        "--addon", type=Path, default=Path("docs/issue-3-expansao-300-aditivo-cache-dominio.md")
    )
    args = parser.parse_args()
    pool = private_path(args.pool, Path.cwd())
    parent = CohortRelease.model_validate_json((args.parent / "cohort.json").read_bytes())
    validate_parent_metadata(parent, load_partitions(args.parent / "partitions.json"))
    if args.operation == "migrate":
        print(json.dumps(migrate(pool, args.addon, namespace="cached-domain")))
        return
    if (pool / "cached-domain/discovery-receipt.json").exists():
        raise ValueError("cached_domain_discovery_already_completed")
    client = AuditedClient(api_key(), pool, max_calls=300)
    result = discover(client, parent, pool, args.addon)
    print(
        json.dumps(
            {
                "new_domain_candidates": len(result["records"]),
                "attempts_total": len(client.attempts),
                "new_search_requests": 0,
            }
        )
    )


if __name__ == "__main__":
    main()

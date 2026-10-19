"""Outcome-independent topic/hashtag discovery and audited migration of the new pool."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from scripts.channel_partitions import load_partitions, new_channel_partition
from scripts.collect_channel_metadata import api_key, normalize_video
from scripts.expand_reference_pool import (
    AuditedClient,
    ordered_candidates,
    validate_parent_metadata,
)
from scripts.observed_baseline import CohortRelease
from scripts.private_checkpoint import digest, file_hash, lock, private_path, save

QUERIES = (
    ("moda", "#modafeminina #shorts", "/m/032tl"),
    ("beleza", "#maquiagem #shorts", "/m/041xxh"),
    ("moda", "#lookdodia #shorts", "/m/032tl"),
    ("beleza", "#skincare #shorts", "/m/041xxh"),
    ("moda", "provador roupas", "/m/032tl"),
    ("beleza", "perfume cosmético", "/m/041xxh"),
    ("moda", "moda masculina", "/m/032tl"),
    ("beleza", "cuidados cabelo", "/m/041xxh"),
)


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
    hints = {}
    channels = {}
    after, before = old["window"]
    for sector, query, topic in QUERIES:
        params = {
            "part": "snippet",
            "type": "video",
            "q": query,
            "topicId": topic,
            "order": "date",
            "maxResults": 50,
            "publishedAfter": after,
            "publishedBefore": before,
            "videoDuration": "short",
            "relevanceLanguage": "pt",
            "regionCode": "BR",
            "fields": "items(id/videoId,snippet/channelId)",
        }
        key = digest(["search", params])
        if (
            key not in client.cached
            and sum(a["resource"] == "search" for a in client.attempts) >= 28
        ):
            raise RuntimeError("search_attempt_budget_reached")
        body, _ = client.get("search", params)
        for item in body.get("items", []):
            vid = item.get("id", {}).get("videoId")
            channel = item.get("snippet", {}).get("channelId")
            if not vid or not channel or vid in excluded_ids or channel in excluded_channels:
                continue
            hints.setdefault(vid, set()).add(sector)
            channels[vid] = channel
    allocation = old["channel_allocation"] | {
        ch: new_channel_partition(ch) for ch in channels.values()
    }
    target = pool / "targeted"
    target.mkdir(mode=0o700, exist_ok=True)
    save(
        target / "channel-allocation.json",
        {
            "parent_selection_sha256": file_hash(pool / "candidates.json"),
            "addon_sha256": file_hash(addon),
            "allocation_before_outcomes": True,
            "channel_allocation": allocation,
        },
    )
    rows = []
    ids = sorted(channels)
    for start in range(0, len(ids), 50):
        selected = ids[start : start + 50]
        body, observed = client.get(
            "videos",
            {
                "part": "snippet,contentDetails,statistics,status",
                "id": ",".join(selected),
                "fields": "items(id,snippet(publishedAt,channelId,title,defaultAudioLanguage),contentDetails(duration),statistics(viewCount,likeCount),status(license))",
            },
        )
        for item in body.get("items", []):
            if (
                item.get("id") not in selected
                or item.get("snippet", {}).get("channelId") != channels[item["id"]]
            ):
                continue
            row = normalize_video(item, observed)
            row["curation"]["targeted_sector_hints"] = sorted(hints[item["id"]])
            rows.append(row)
    rows = ordered_candidates(rows, excluded_ids, excluded_channels)
    result = {
        "protocol": "targeted-expansion-v1",
        "parent_selection_sha256": file_hash(pool / "candidates.json"),
        "addon_sha256": file_hash(addon),
        "records": rows,
        "channel_allocation": allocation,
        "window": old["window"],
        "selection_uses_views": False,
        "successful_calls_total": len(client.calls),
        "request_attempts_total": len(client.attempts),
    }
    save(target / "candidates.json", result)
    return result


def migrated_plan(old, new, state):
    if (
        state["halt_reason"]
        or state.get("cleanup_pending")
        or any("review" not in v for v in state["videos"])
    ):
        raise ValueError("finish_current_batch_before_migration")
    old_map = {r["audit"]["video_id"]: r for r in old["records"]}
    new_ids = {r["audit"]["video_id"] for r in new["records"]}
    if len(new_ids) != len(new["records"]) or new_ids & set(old_map):
        raise ValueError("targeted_duplicate_or_refreshed_observation")
    if any(
        new["channel_allocation"].get(ch) != part for ch, part in old["channel_allocation"].items()
    ):
        raise ValueError("channel_allocation_changed")
    for ch, part in new["channel_allocation"].items():
        if part != new_channel_partition(ch):
            raise ValueError("channel_allocation_changed")
    attempted = {v["video_id"] for v in state["videos"]}
    if not attempted <= set(old_map):
        raise ValueError("attempt_not_in_parent_selection")
    prefix = [r for r in old["records"] if r["audit"]["video_id"] in attempted]
    suffix = [r for r in old["records"] if r["audit"]["video_id"] not in attempted]
    result = {
        **old,
        "protocol": "expansion300-targeted-child-v1",
        "records": prefix + new["records"] + suffix,
        "channel_allocation": new["channel_allocation"],
        "parent_selection_sha256": new["parent_selection_sha256"],
        "targeted_addon_sha256": new["addon_sha256"],
        "targeted_candidates": len(new["records"]),
    }
    if any(r != old_map[r["audit"]["video_id"]] for r in prefix):
        raise ValueError("frozen_attempt_changed")
    return result


def migrate(pool, addon):
    with lock(pool / "extraction/.lock"):
        old_path = pool / "candidates.json"
        state_path = pool / "extraction/checkpoint.json"
        receipt = pool / "targeted/migration.json"
        current_state = json.loads(state_path.read_bytes())
        if receipt.exists():
            previous = json.loads(receipt.read_bytes())
            if previous["child_selection_sha256"] != file_hash(old_path) or current_state[
                "selection_sha256"
            ] != file_hash(old_path):
                raise ValueError("completed_selection_migration_changed")
            return previous
        archive = pool / "candidates-before-targeted.json"
        before_path = pool / "extraction/checkpoint-before-targeted.json"
        parent_path = archive if archive.exists() else old_path
        old = json.loads(parent_path.read_bytes())
        state = json.loads(before_path.read_bytes()) if before_path.exists() else current_state
        new = json.loads((pool / "targeted/candidates.json").read_bytes())
        parent_hash = file_hash(parent_path)
        if (
            new["parent_selection_sha256"] != parent_hash
            or state["selection_sha256"] != parent_hash
            or new["addon_sha256"] != file_hash(addon)
        ):
            raise ValueError("targeted_migration_parent_mismatch")
        result = migrated_plan(old, new, state)
        child_path = pool / "targeted/selection-child.json"
        if child_path.exists():
            if json.loads(child_path.read_bytes()) != result:
                raise ValueError("targeted_child_changed")
        else:
            save(child_path, result)
        child_hash = file_hash(child_path)
        if file_hash(old_path) not in {parent_hash, child_hash}:
            raise ValueError("current_selection_changed")
        mutable = {
            "selection_sha256",
            "previous_selection_sha256",
            "selection_migration_addon_sha256",
        }
        if {k: v for k, v in current_state.items() if k not in mutable} != {
            k: v for k, v in state.items() if k not in mutable
        }:
            raise ValueError("checkpoint_changed_during_migration")
        if current_state["selection_sha256"] not in {parent_hash, child_hash}:
            raise ValueError("checkpoint_selection_changed")
        if not archive.exists():
            save(archive, old)
        if file_hash(archive) != parent_hash:
            raise ValueError("selection_archive_not_identical")
        if not before_path.exists():
            save(before_path, state)
        journal = {
            "parent_selection_sha256": parent_hash,
            "child_selection_sha256": child_hash,
            "before_checkpoint_sha256": file_hash(before_path),
            "addon_sha256": file_hash(addon),
        }
        pending = pool / "targeted/migration-pending.json"
        if pending.exists() and json.loads(pending.read_bytes()) != journal:
            raise ValueError("migration_journal_changed")
        save(pending, journal)
        save(old_path, result)
        if file_hash(old_path) != child_hash:
            raise ValueError("child_selection_serialization_mismatch")
        updated = state | {
            "previous_selection_sha256": parent_hash,
            "selection_sha256": child_hash,
            "selection_migration_addon_sha256": file_hash(addon),
        }
        save(state_path, updated)
        summary = journal | {
            "attempts_preserved": len(state["videos"]),
            "new_candidates_prioritized": len(new["records"]),
            "candidates": len(result["records"]),
            "migrated_at_utc": datetime.now(UTC).isoformat(),
        }
        save(receipt, summary)
        return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["discover", "migrate"])
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--pool", type=Path, required=True)
    parser.add_argument(
        "--addon", type=Path, default=Path("docs/issue-3-expansao-300-aditivo-descoberta.md")
    )
    args = parser.parse_args()
    pool = private_path(args.pool, Path.cwd())
    parent = CohortRelease.model_validate_json((args.parent / "cohort.json").read_bytes())
    validate_parent_metadata(parent, load_partitions(args.parent / "partitions.json"))
    if args.operation == "migrate":
        print(json.dumps(migrate(pool, args.addon)))
        return
    if (pool / "targeted/candidates.json").exists():
        raise ValueError("targeted_discovery_already_completed")
    client = AuditedClient(api_key(), pool, max_calls=300)
    result = discover(client, parent, pool, args.addon)
    print(
        json.dumps(
            {
                "new_targeted_candidates": len(result["records"]),
                "successful_calls_total": len(client.calls),
                "attempts_total": len(client.attempts),
            }
        )
    )


if __name__ == "__main__":
    main()

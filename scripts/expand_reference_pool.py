"""Bounded expansion discovery; freeze new channels before requesting their outcomes."""

from __future__ import annotations

import argparse
import json
import re
import time
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

from scripts.channel_partitions import Reference, load_partitions, new_channel_partition
from scripts.channel_partitions import digest as partition_digest
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


def validate_parent_metadata(parent, manifest):
    references = [r.model_dump(include=set(Reference.model_fields)) for r in parent.records]
    assigned = [r.model_dump(include=set(Reference.model_fields)) for r in manifest.assignments]
    if references != assigned or manifest.metadata_sha256 != partition_digest(references):
        raise ValueError("parent_cohort_partition_mismatch")


def bind_checkpoint(output, provenance, *, resume):
    """A resume must never overwrite the ancestry of the cached API responses."""
    path = output / "parent.json"
    if resume:
        if not path.is_file() or json.loads(path.read_bytes()) != provenance:
            raise ValueError("expansion_checkpoint_parent_mismatch")
    elif path.exists():
        raise ValueError("expansion_checkpoint_already_exists")
    else:
        save(path, provenance)


class AuditedClient(Client):
    """Reuse exact requests and their original observations within the total budget."""

    def __init__(
        self, key, output, *, max_calls=300, source_recovered=False, request_interval_seconds=2.0
    ):
        super().__init__(key, max_calls=max_calls)
        self.output = output
        self.request_interval_seconds = request_interval_seconds
        self.last_request_started = None
        self.calls = [
            json.loads(path.read_bytes()) for path in sorted((output / "calls").glob("*.json"))
        ]
        if len(self.calls) > max_calls:
            raise ValueError("expansion_request_budget_exceeded")
        self.cached = {digest([call["resource"], call["params"]]): call for call in self.calls}
        self.attempt_path = output / "request-attempts.json"
        self.attempts = (
            json.loads(self.attempt_path.read_bytes())
            if self.attempt_path.exists()
            else [
                {"resource": call["resource"], "params": call["params"], "status": "completed"}
                for call in self.calls
            ]
        )
        if len(self.attempts) > max_calls:
            raise ValueError("expansion_request_budget_exceeded")
        self.source_state_path = output / "source-state.json"
        if self.source_state_path.exists():
            halted = json.loads(self.source_state_path.read_bytes())["halted"]
        else:
            failure = output / "failure.json"
            reason = json.loads(failure.read_bytes()).get("reason", "") if failure.exists() else ""
            halted = bool(re.search(r"returned HTTP 429$", reason)) or any(
                a.get("stop_reason") == "http_429" or a.get("reason") == "HTTP429"
                for a in self.attempts
            )
        if halted and not source_recovered:
            raise ValueError("source_stopped_http_429")
        if source_recovered:
            save(
                self.source_state_path,
                {
                    "halted": False,
                    "operator_confirmed_source_recovery": True,
                    "confirmed_at_utc": datetime.now(UTC).isoformat(),
                    "attempts_already_consumed": len(self.attempts),
                },
            )

    def get(self, resource, params):
        cached = self.cached.get(digest([resource, params]))
        if cached is not None:
            return cached["response"], cached["received_at_utc"]
        if len(self.attempts) >= self.max_calls:
            raise RuntimeError("API request budget reached")
        if self.last_request_started is not None:
            time.sleep(
                max(
                    0.0,
                    self.request_interval_seconds - (time.monotonic() - self.last_request_started),
                )
            )
        attempt = {"resource": resource, "params": params, "status": "started"}
        self.attempts.append(attempt)
        save(self.attempt_path, self.attempts)
        self.last_request_started = time.monotonic()
        try:
            result = super().get(resource, params)
        except (RuntimeError, ValueError, OSError) as exc:
            attempt["status"] = "failed"
            if re.search(r"returned HTTP 429$", str(exc)):
                attempt["stop_reason"] = "http_429"
                save(
                    self.source_state_path,
                    {"halted": True, "reason": "http_429", "attempts_consumed": len(self.attempts)},
                )
            save(self.attempt_path, self.attempts)
            raise
        save(self.output / "calls" / f"{len(self.calls):04d}.json", self.calls[-1])
        attempt["status"] = "completed"
        save(self.attempt_path, self.attempts)
        self.cached[digest([resource, params])] = self.calls[-1]
        return result


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
    parser.add_argument("--resume", action="store_true")
    parser.add_argument(
        "--source-recovered",
        action="store_true",
        help="Operator explicitly confirms source recovery after a terminal stop",
    )
    args = parser.parse_args()
    root = Path.cwd()
    output = private_path(args.output, root)
    if output.exists() and not args.resume:
        parser.error("use a fresh output directory")
    if args.resume and not output.is_dir():
        parser.error("resume requires an existing checkpoint")
    if args.source_recovered and not args.resume:
        parser.error("source recovery requires an existing checkpoint and --resume")
    parent = CohortRelease.model_validate_json((args.parent / "cohort.json").read_bytes())
    manifest = load_partitions(args.parent / "partitions.json")
    validate_parent_metadata(parent, manifest)
    if len(parent.records) != 200:
        raise ValueError("expansion_requires_frozen_200_parent")
    old_channels = {r.channel_id for r in parent.records}
    old_ids = {r.sample_id for r in parent.records}
    # Original pilot controls are outside the frozen 200; use only their identities.
    controls = json.loads(
        (root / "data/private/vinte-candidatos-20261017-v2.records.json").read_bytes()
    )
    old_ids |= {r["audit"]["video_id"] for r in controls}
    output.mkdir(parents=True, mode=0o700, exist_ok=args.resume)
    (output / "calls").mkdir(mode=0o700, exist_ok=args.resume)
    bind_checkpoint(
        output,
        {
            "cohort_sha256": parent.release_sha256,
            "partition_sha256": manifest.manifest_sha256,
            "protocol_sha256": file_hash(root / "docs/issue-3-expansao-300-protocolo.md"),
        },
        resume=args.resume,
    )

    client = AuditedClient(api_key(), output, max_calls=300, source_recovered=args.source_recovered)
    try:
        now = (
            datetime.fromisoformat(client.calls[0]["params"]["publishedBefore"])
            + timedelta(days=30)
            if client.calls
            else datetime.now(UTC)
        )
        state = discover(client, old_channels, old_ids, output, now)
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
        message = str(exc)
        reason = (
            message
            if re.fullmatch(
                r"YouTube [A-Za-z]+ returned HTTP \d{3}|Network failure while querying YouTube [A-Za-z]+|API request budget reached",
                message,
            )
            else type(exc).__name__
        )
        save(
            output / "failure.json",
            {
                "type": type(exc).__name__,
                "reason": reason,
                "completed_calls": len(client.calls),
                "request_attempts": len(client.attempts),
            },
        )
        print(
            json.dumps(
                {
                    "status": "failed",
                    "reason": reason,
                    "completed_calls": len(client.calls),
                    "request_attempts": len(client.attempts),
                }
            )
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

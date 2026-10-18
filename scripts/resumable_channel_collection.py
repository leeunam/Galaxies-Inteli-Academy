"""Checkpointed metadata collection, isolated from the legacy raw-response collector."""

from __future__ import annotations

import json
import re
from pathlib import Path

from scripts.collect_channel_metadata import ROOT, channel_filter, normalize_video
from scripts.private_checkpoint import digest, lock, private_path, save

PROTOCOL = "channel-checkpoint-v1"
VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}")


def configuration(references, pages_per_channel, detail_batch_size):
    if not 1 <= len(references) <= 30 or not 1 <= pages_per_channel <= 5:
        raise ValueError("Use 1–30 channels and 1–5 pages per channel")
    if not 1 <= detail_batch_size <= 50:
        raise ValueError("Detail batch size must be 1–50")
    return {
        "filters": [channel_filter(ref) for ref in references],
        "pages_per_channel": pages_per_channel,
        "detail_batch_size": detail_batch_size,
    }


def load_checkpoint(path, config, resume):
    if path.exists() != resume:
        raise ValueError("Existing checkpoint requires --resume; resume requires an existing file")
    if resume:
        state = json.loads(path.read_text())
        if (
            state.get("protocol") != PROTOCOL
            or state.get("config") != config
            or state.get("config_sha256") != digest(config)
        ):
            raise ValueError("Incompatible checkpoint protocol or channel configuration")
        channels = state.get("channels")
        if not isinstance(channels, list) or len(channels) != len(config["filters"]):
            raise ValueError("Invalid checkpoint channels")
        if (
            not isinstance(state.get("request_count"), int)
            or state["request_count"] < 0
            or not isinstance(state.get("records"), dict)
            or not isinstance(state.get("detail_ids"), list)
        ):
            raise ValueError("Invalid checkpoint progress")
        ids = state.get("video_ids")
        if (
            not isinstance(ids, list)
            or len(ids) != len(set(ids))
            or not all(isinstance(v, str) and VIDEO_ID.fullmatch(v) for v in ids)
            or not set(state["detail_ids"]) <= set(ids)
            or not set(state["records"]) <= set(state["detail_ids"])
        ):
            raise ValueError("Invalid checkpoint video IDs")
        for channel in channels:
            if (
                not isinstance(channel, dict)
                or not isinstance(channel.get("pages_read"), int)
                or not 0 <= channel["pages_read"] <= config["pages_per_channel"]
                or not isinstance(channel.get("done"), bool)
            ):
                raise ValueError("Invalid checkpoint page progress")
        return state
    return {
        "protocol": PROTOCOL,
        "config": config,
        "config_sha256": digest(config),
        "channels": [{"pages_read": 0, "done": False} for _ in config["filters"]],
        "video_ids": [],
        "detail_ids": [],
        "records": {},
        "request_count": 0,
        "status": "pending",
        "training_partition_created": False,
    }


def summary(state, invocation_requests=0):
    records = list(state["records"].values())
    channels = []
    for channel in state["channels"]:
        dates = [
            r["audit"]["published_at_utc"]
            for r in records
            if r["audit"]["channel_id"] == channel.get("channel_id")
        ]
        channels.append(
            {
                **channel,
                "coverage_partial": not channel.get("exhausted", False),
                "observed_publication_interval": [min(dates), max(dates)] if dates else None,
            }
        )
    return {
        "status": state["status"],
        "channels": channels,
        "records": records,
        "request_count": state["request_count"],
        "invocation_requests": invocation_requests,
        "unavailable_video_ids": sorted(set(state["detail_ids"]) - set(state["records"])),
        "details_partial": set(state["detail_ids"]) != set(state["video_ids"]),
        "training_partition_created": False,
    }


def collect_resumable(
    client,
    references,
    pages_per_channel,
    checkpoint: Path,
    *,
    resume=False,
    max_calls=30,
    detail_batch_size=50,
):
    config = configuration(references, pages_per_channel, detail_batch_size)
    if not 1 <= max_calls <= 100:
        raise ValueError("Invocation request budget must be 1–100")
    checkpoint = private_path(checkpoint, ROOT, raw=True)
    with lock(checkpoint.with_suffix(checkpoint.suffix + ".lock")):
        state = load_checkpoint(checkpoint, config, resume)
        used = 0

        def get(resource, params):
            nonlocal used
            if used >= max_calls:
                return None
            used += 1
            state["request_count"] += 1
            save(checkpoint, state)  # Count even failed requests; never persist raw responses.
            return client.get(resource, params)

        save(checkpoint, state)
        try:
            for index, criteria in enumerate(config["filters"]):
                channel = state["channels"][index]
                if "channel_id" not in channel:
                    response = get(
                        "channels",
                        {
                            "part": "contentDetails",
                            **criteria,
                            "fields": "items(id,contentDetails/relatedPlaylists/uploads)",
                        },
                    )
                    if response is None:
                        break
                    body, _ = response
                    if not body.get("items"):
                        raise ValueError("Channel returned no accessible channel")
                    item = body["items"][0]
                    channel.update(
                        channel_id=item["id"],
                        playlist_id=item["contentDetails"]["relatedPlaylists"]["uploads"],
                    )
                    # Aliases for the same channel share the first channel's progress.
                    previous = next(
                        (
                            c
                            for c in state["channels"][:index]
                            if c.get("channel_id") == channel["channel_id"]
                        ),
                        None,
                    )
                    if previous is not None:
                        channel.update(previous)
                    save(checkpoint, state)
                while not channel["done"]:
                    params = {
                        "part": "contentDetails",
                        "playlistId": channel["playlist_id"],
                        "maxResults": 50,
                        "fields": "items(contentDetails/videoId),nextPageToken",
                    }
                    if channel.get("next_page_token"):
                        params["pageToken"] = channel["next_page_token"]
                    response = get("playlistItems", params)
                    if response is None:
                        break
                    body, _ = response
                    ids = [item["contentDetails"]["videoId"] for item in body.get("items", [])]
                    if not all(VIDEO_ID.fullmatch(v) for v in ids):
                        raise ValueError("Invalid API video ID")
                    state["video_ids"] = sorted(set(state["video_ids"]) | set(ids))
                    channel["pages_read"] += 1
                    channel["next_page_token"] = body.get("nextPageToken")
                    channel["exhausted"] = not channel["next_page_token"]
                    channel["done"] = (
                        channel["exhausted"] or channel["pages_read"] >= pages_per_channel
                    )
                    save(checkpoint, state)
            pending = sorted(set(state["video_ids"]) - set(state["detail_ids"]))
            for start in range(0, len(pending), detail_batch_size):
                batch = pending[start : start + detail_batch_size]
                response = get(
                    "videos",
                    {
                        "part": "snippet,contentDetails,statistics,status",
                        "id": ",".join(batch),
                        "fields": "items(id,snippet(publishedAt,channelId,title,defaultAudioLanguage),contentDetails(duration),statistics(viewCount,likeCount),status(license))",
                    },
                )
                if response is None:
                    break
                body, observed = response
                normalized = [normalize_video(item, observed) for item in body.get("items", [])]
                if any(r["audit"]["video_id"] not in batch for r in normalized):
                    raise ValueError("Unexpected video in details response")
                state["records"].update({r["audit"]["video_id"]: r for r in normalized})
                state["detail_ids"] = sorted(set(state["detail_ids"]) | set(batch))
                save(checkpoint, state)
            state["status"] = (
                "metadata_complete_within_page_limit"
                if all(c["done"] for c in state["channels"])
                and set(state["video_ids"]) == set(state["detail_ids"])
                else "budget_exhausted_partial"
            )
        except BaseException:
            state["status"] = "interrupted_partial"
            save(checkpoint, state)
            raise
        state["channels"] = summary(state)["channels"]
        save(checkpoint, state)
        return summary(state, used)

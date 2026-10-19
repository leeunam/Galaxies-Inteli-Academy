"""Development-only, resumable local VLM sidecars from committed contact-sheet pixels."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import time
from importlib.metadata import version
from pathlib import Path

from scripts.channel_partitions import digest, load_partitions
from scripts.expansion_media import deadline
from scripts.experiment_a_artifact import ExperimentArtifact as AArtifact
from scripts.experiment_b_data import validate_cohort_boundary
from scripts.experiment_b_vlm_network import TransientDNSFailure, dns_preflight
from scripts.gguf_visual_attributes import RUNTIME, model_manifest
from scripts.pilot_licensed_media import frames_and_properties, run_session, select_vlm_samples
from scripts.private_checkpoint import file_hash, lock, private_path, save
from scripts.retrain_expansion import reserved_guard
from scripts.vlm_frame_evidence import (
    NORMALIZATION_POLICY,
    VLMOutputError,
    extract_visual_attributes,
)

POLICY = "contact-sheet-cell-320x330-v1"
PROTOCOL = "b-vlm-sidecar-queue-v3-dns-ledger"
AUDIT_PROTOCOL = "b-vlm-audit32-v1"
TIME_BUDGET = 27 * 3600
PRIOR_BUDGET_SHA256 = "516808bc0f1b4dc423b8b71585c7da33bae21c282218574650e6b07f538b60ec"
PRIOR_ACQUISITIONS = 21
ACQUISITION_LIMIT = 300
DNS_RETRY_LIMIT = 10
DNS_BACKOFF_SECONDS = 5
SOURCES = (
    "scripts/experiment_b_vlm_extract.py",
    "scripts/experiment_b_data.py",
    "scripts/experiment_a_artifact.py",
    "scripts/channel_partitions.py",
    "scripts/observed_baseline.py",
    "scripts/pilot_licensed_media.py",
    "scripts/pilot_youtube_media.py",
    "scripts/gguf_visual_attributes.py",
    "scripts/visual_attributes.py",
    "scripts/prepare_gguf_vlm.py",
    "scripts/private_checkpoint.py",
    "scripts/retrain_expansion.py",
    "scripts/expansion_media.py",
    "scripts/vlm_frame_evidence.py",
    "scripts/experiment_b_vlm_network.py",
    "docs/issue-4-experimento-b-vlm-protocolo.md",
    "docs/issue-4-experimento-b-vlm-identidade.md",
    "docs/issue-4-experimento-b-vlm-deduplicacao.md",
    "docs/issue-4-experimento-b-vlm-dns.md",
    "uv.lock",
)


def configuration(root):
    return {
        "input_policy": POLICY,
        "output_normalization": NORMALIZATION_POLICY,
        "model": model_manifest(),
        "runtime_sha256": file_hash(RUNTIME),
        "sources_sha256": {name: file_hash(root / name) for name in SOURCES},
        "packages": {name: version(name) for name in ("av", "Pillow", "yt-dlp", "psutil")},
    }


def audit_sample(assignments):
    result = []
    for sector in ("beleza", "moda"):
        candidates = [r for r in assignments if r.partition == "train" and r.sector == sector]
        result.extend(
            sorted(
                candidates,
                key=lambda r: digest({"protocol": AUDIT_PROTOCOL, "sample_id": r.sample_id}),
            )[:16]
        )
    if len(result) != 32:
        raise ValueError("requires_16_training_audit_samples_per_sector")
    return tuple(r.sample_id for r in result)


def anchored_metadata(parent, cohort, root):
    anchor = AArtifact.model_validate_json(
        (root / "artifacts/issue-3-experimento-a-300-v1/artifact.json").read_bytes()
    )
    validate_cohort_boundary(
        parent,
        cohort,
        expected_cohort_sha256=anchor.cohort_sha256,
        expected_partition_sha256=anchor.partition_manifest_sha256,
    )
    return load_partitions(cohort / "partitions.json"), anchor


def sheet_label(annotation, sample, index, second):
    batch = annotation.get("source_batch")
    if batch == "sixty":
        return f"{annotation['source_index']} / frame {index + 1} @ {second:.3f}s"
    if batch in {"full", "fullv3", "fullv4", "fullv5", "fullv6"}:
        return f"pool {annotation['source_index']} / frame {index + 1} @ {second:.3f}s"
    if batch is None:
        return f"{sample} / {index + 1} @ {second:.3f}s"
    raise ValueError("unsupported_frozen_sheet_recipe")


def prior_budget(path, root):
    if path is None:
        raise ValueError("explicit_prior_budget_required_for_v2")
    path = private_path(path, root)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != PRIOR_BUDGET_SHA256:
        raise ValueError("prior_budget_receipt_not_frozen_provenance")
    body = json.loads(raw)
    seconds, acquisitions = 0.0, 0
    for entry in body["entries"]:
        source = private_path(root / entry["path"], root)
        source_raw = source.read_bytes()
        if hashlib.sha256(source_raw).hexdigest() != entry["sha256"]:
            raise ValueError("prior_budget_evidence_changed")
        record = json.loads(source_raw)
        if entry["seconds_field"] not in {"elapsed_seconds", "total_seconds"}:
            raise ValueError("invalid_prior_budget_field")
        elapsed = record[entry["seconds_field"]]
        count = len(record["entries"]) if entry["seconds_field"] == "elapsed_seconds" else 1
        if (
            type(elapsed) not in (int, float)
            or not math.isfinite(elapsed)
            or elapsed < 0
            or elapsed != entry["seconds"]
            or count != entry["acquisitions"]
        ):
            raise ValueError("prior_budget_accounting_mismatch")
        prior_offset = entry.get("prior_elapsed_seconds", 0.0)
        if prior_offset and prior_offset != seconds:
            raise ValueError("prior_budget_cumulative_offset_mismatch")
        seconds += elapsed - prior_offset
        acquisitions += count
    if (
        body["schema_version"] != "b-vlm-prior-budget-v1"
        or seconds != body["elapsed_seconds"]
        or acquisitions != body["acquisitions"]
        or acquisitions != PRIOR_ACQUISITIONS
        or body["acquisition_limit"] != ACQUISITION_LIMIT
        or seconds >= TIME_BUDGET
    ):
        raise ValueError("invalid_or_exhausted_prior_budget")
    return {
        "path": str(path.relative_to(root.resolve())),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "elapsed_seconds": seconds,
        "acquisitions": acquisitions,
        "acquisition_limit": body["acquisition_limit"],
    }


def prepare(parent, cohort, folder, root, *, budget_receipt=None):
    """No models, labels, outcomes or network; select dev before opening features."""
    manifest, anchor = anchored_metadata(parent, cohort, root)
    previous = prior_budget(budget_receipt, root)
    audit = audit_sample(manifest.assignments)
    selected = {r.sample_id: r for r in manifest.assignments if r.partition != "test"}
    if len(selected) != 269:
        raise ValueError("requires_269_development_rows")
    index = json.loads((cohort / "evidence-index.json").read_bytes())
    rows = []
    for sample in (*audit, *sorted(set(selected) - set(audit))):
        row, entry = selected[sample], index[sample]
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", sample):
            raise ValueError("invalid_youtube_sample_id")
        relative = Path(entry["features_ref"])
        path = (root / relative).resolve()
        if relative.is_absolute() or not path.is_relative_to((root / "data/private").resolve()):
            raise ValueError("unsafe_development_feature_path")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry["curation"]["features_sha256"]:
            raise ValueError("frozen_development_features_changed")
        features = json.loads(raw)
        annotation = entry["curation"]
        sheet_label(annotation, sample, 0, 0.2)  # Refuse unsupported recipe before network.
        if not re.fullmatch(r"[a-f0-9]{64}", annotation.get("contact_sheet_sha256", "")):
            raise ValueError("frozen_contact_sheet_hash_required")
        rows.append(
            {
                "sample_id": sample,
                "sector": row.sector,
                "partition": row.partition,
                "media_sha256": row.media_sha256,
                "features_ref": str(relative),
                "features_sha256": annotation["features_sha256"],
                "properties": features["properties"],
                "sheet_sha256": annotation["contact_sheet_sha256"],
                "sheet_recipe": {
                    k: annotation[k] for k in ("source_batch", "source_index") if k in annotation
                },
                "audit": sample in audit,
            }
        )
    body = {
        "protocol": PROTOCOL,
        "cohort_sha256": anchor.cohort_sha256,
        "partition_sha256": anchor.partition_manifest_sha256,
        "config": configuration(root),
        "prior_budget": previous,
        "audit_sample_ids": audit,
        "rows": rows,
        "labels_used": False,
        "test_evaluated": False,
    }
    body["plan_sha256"] = digest(body)
    with lock(folder / ".lock"):
        if any(p.name != ".lock" for p in folder.iterdir()):
            raise ValueError("queue_output_already_exists")
        save(folder / "plan.json", body)
        save(
            folder / "checkpoint.json",
            {
                "plan_sha256": body["plan_sha256"],
                "elapsed_seconds": previous["elapsed_seconds"] if previous else 0.0,
                "prior_acquisitions": previous["acquisitions"] if previous else 0,
                "acquisition_limit": previous["acquisition_limit"] if previous else 269,
                "halt_reason": None,
                "dns_retries_used": 0,
                "entries": [],
            },
        )
    return body


def verified_cells(paths, seconds, row, scratch):
    """The Qwen inputs are crops of the hashed PNG, never unverified 512px JPEGs."""
    from PIL import Image, ImageDraw

    if not 1 <= len(paths) == len(seconds) <= 4:
        raise ValueError("invalid_vlm_sample_count")
    sheet = Image.new("RGB", (320 * len(paths), 360), "white")
    draw = ImageDraw.Draw(sheet)
    for i, (path, second) in enumerate(zip(paths, seconds, strict=True)):
        with Image.open(path) as picture:
            picture.thumbnail((320, 330))
            sheet.paste(picture, (320 * i, 25))
        draw.text(
            (320 * i + 4, 4),
            sheet_label(row["sheet_recipe"], row["sample_id"], i, second),
            fill="black",
        )
    committed = scratch / "committed-sheet.png"
    sheet.save(committed)
    if file_hash(committed) != row["sheet_sha256"]:
        raise ValueError("frozen_contact_sheet_pixels_mismatch")
    # Decode the actual hashed file; crop order and dimensions are part of POLICY.
    cells = []
    with Image.open(committed) as verified:
        if verified.size != (320 * len(paths), 360) or verified.mode != "RGB":
            raise ValueError("invalid_committed_sheet_dimensions")
        for i in range(len(paths)):
            path = scratch / f"vlm-cell-{i + 1}.png"
            verified.crop((320 * i, 25, 320 * (i + 1), 355)).save(path)
            cells.append(path)
    return cells, committed


def extract_row(media, scratch, row, config, audit_destination, *, vlm=extract_visual_attributes):
    properties, frames = frames_and_properties(media, scratch)
    if properties != row["properties"]:
        raise ValueError("frozen_frame_properties_mismatch")
    paths, seconds = select_vlm_samples(frames, properties)
    cells, sheet = verified_cells(paths, seconds, row, scratch)
    input_hashes = [file_hash(p) for p in cells]
    if row["audit"]:
        audit_destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with audit_destination.open("xb") as output:
            audit_destination.chmod(0o600)
            output.write(sheet.read_bytes())
    result = vlm(cells, seconds, scratch)
    if result["approved_for_training"] is not False:
        raise ValueError("automatic_training_approval_forbidden")
    return {
        "schema_version": "experiment-b-vlm-sidecar-v1",
        "sample_id": row["sample_id"],
        "input_policy": POLICY,
        "config_sha256": digest(config),
        "shared_features_sha256": row["features_sha256"],
        "frozen_media_sha256": row["media_sha256"],
        "reacquired_media_sha256": file_hash(media),
        "frozen_sheet_sha256": row["sheet_sha256"],
        "input_png_sha256": input_hashes,
        "properties": properties,
        "vlm": result,
        "training_approved": False,
        "test_evaluated": False,
    }


def load_queue(parent, cohort, folder, root):
    manifest, anchor = anchored_metadata(parent, cohort, root)
    plan = json.loads((folder / "plan.json").read_bytes())
    state = json.loads((folder / "checkpoint.json").read_bytes())
    selected = {r.sample_id: r for r in manifest.assignments if r.partition != "test"}
    if (
        plan["protocol"] != PROTOCOL
        or digest({k: v for k, v in plan.items() if k != "plan_sha256"}) != plan["plan_sha256"]
        or state["plan_sha256"] != plan["plan_sha256"]
        or plan["config"] != configuration(root)
        or plan["cohort_sha256"] != anchor.cohort_sha256
        or plan["partition_sha256"] != anchor.partition_manifest_sha256
        or tuple(plan["audit_sample_ids"]) != audit_sample(manifest.assignments)
        or len(plan["rows"]) != len(selected)
        or {r["sample_id"] for r in plan["rows"]} != set(selected)
        or any(
            selected[r["sample_id"]].partition != r["partition"]
            or selected[r["sample_id"]].sector != r["sector"]
            or selected[r["sample_id"]].media_sha256 != r["media_sha256"]
            or r["audit"] != (r["sample_id"] in plan["audit_sample_ids"])
            for r in plan["rows"]
        )
    ):
        raise ValueError("vlm_checkpoint_or_configuration_changed")
    ids = [e["sample_id"] for e in state["entries"]]
    if len(ids) != len(set(ids)) or not set(ids) <= set(selected):
        raise ValueError("invalid_vlm_checkpoint_entries")
    previous = plan["prior_budget"]
    if previous is None:
        raise ValueError("explicit_prior_budget_required_for_v2")
    if prior_budget(root / previous["path"], root) != previous:
        raise ValueError("prior_budget_receipt_changed")
    if (
        not math.isfinite(state["elapsed_seconds"])
        or state["elapsed_seconds"] < (previous["elapsed_seconds"] if previous else 0)
        or state["prior_acquisitions"] != (previous["acquisitions"] if previous else 0)
        or state["acquisition_limit"] != (previous["acquisition_limit"] if previous else 269)
        or attempt_count(state) + state["prior_acquisitions"] > state["acquisition_limit"]
    ):
        raise ValueError("vlm_cumulative_budget_mismatch")
    accounted = previous["elapsed_seconds"] if previous else 0.0
    retries = 0
    for entry in state["entries"]:
        attempts = entry.get("attempts", [])
        if not 1 <= len(attempts) <= 2:
            raise ValueError("invalid_vlm_attempt_ledger")
        if entry["status"] in {"completed", "failed"} and (
            attempts[-1]["status"] != entry["status"]
        ):
            raise ValueError("vlm_entry_attempt_status_mismatch")
        retries += len(attempts) - 1
        for index, attempt in enumerate(attempts):
            if attempt["status"] not in {"running", "completed", "failed"}:
                raise ValueError("invalid_vlm_attempt_status")
            if attempt["status"] != "running" and (
                type(attempt["seconds"]) not in (int, float)
                or not math.isfinite(attempt["seconds"])
                or attempt["seconds"] < 0
            ):
                raise ValueError("invalid_vlm_attempt_elapsed")
            if index == 0 and len(attempts) == 2:
                archived = folder / "failed-attempts" / entry["sample_id"] / "1/run.json"
                if (
                    attempt["status"] != "failed"
                    or attempt["reason"] != "temporary_network_dns_failure"
                    or attempt["cleanup"] is not True
                    or attempt["dns_preflight_positive"] is not True
                    or file_hash(archived) != attempt["run_sha256"]
                ):
                    raise ValueError("invalid_vlm_dns_recovery_provenance")
        if entry["status"] not in {"running", "completed", "failed"}:
            raise ValueError("invalid_vlm_checkpoint_status")
        elapsed = entry.get("seconds", 0.0) if entry["status"] == "running" else entry["seconds"]
        if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError("invalid_vlm_checkpoint_elapsed_time")
        accounted += elapsed
    if (
        type(state["dns_retries_used"]) is not int
        or retries != state["dns_retries_used"]
        or retries > DNS_RETRY_LIMIT
    ):
        raise ValueError("invalid_vlm_dns_retry_counter")
    if not math.isclose(state["elapsed_seconds"], accounted, rel_tol=0, abs_tol=1e-8):
        raise ValueError("vlm_checkpoint_time_not_accounted_by_entries")
    for row in plan["rows"]:
        relative = Path(row["features_ref"])
        path = (root / relative).resolve()
        if relative.is_absolute() or not path.is_relative_to((root / "data/private").resolve()):
            raise ValueError("unsafe_development_feature_path")
        if file_hash(path) != row["features_sha256"]:
            raise ValueError("frozen_development_features_changed")
    for entry in state["entries"]:
        if entry["status"] == "completed":
            if set(entry["files_sha256"]) != {"features.json", "run.json"}:
                raise ValueError("incomplete_vlm_evidence_hashes")
            for name, expected in entry["files_sha256"].items():
                if (
                    name not in {"features.json", "run.json"}
                    or file_hash(folder / "sessions" / entry["sample_id"] / name) != expected
                ):
                    raise ValueError("completed_vlm_evidence_changed")
    return plan, state


def attempt_count(state):
    return sum(max(1, len(e.get("attempts", []))) for e in state["entries"])


def session_with_dns_recovery(
    destination, scratch, extractor, downloader, *, source, model, entry, state, folder, persist
):
    """One narrow, accounted recovery; never retry VLM, identity, auth or generic DNS."""
    entry["attempts"] = []
    for index in range(2):
        attempt = {"status": "running"}
        entry["attempts"].append(attempt)
        entry["status"] = "running"
        persist()
        started = time.monotonic()
        try:
            result = run_session(
                destination, scratch, extractor, downloader, source=source, model_manifest=model
            )
        except BaseException as exc:
            record = destination / "run.json"
            run = json.loads(record.read_bytes()) if record.exists() else {}
            reason = str(exc) if re.fullmatch(r"[a-z_]+", str(exc)) else type(exc).__name__
            attempt.update(
                status="failed",
                reason=reason,
                cleanup=run.get("temporary_directory_removed") is True,
                seconds=time.monotonic() - started,
            )
            if record.exists():
                attempt["run_sha256"] = file_hash(record)
            if isinstance(exc, TransientDNSFailure):
                attempt["diagnostic_sha256"] = exc.diagnostic_sha256
            persist()
            eligible = (
                isinstance(exc, TransientDNSFailure)
                and index == 0
                and attempt["cleanup"]
                and state.get("dns_retries_used", 0) < DNS_RETRY_LIMIT
                and state.get("prior_acquisitions", 0) + attempt_count(state)
                < state.get("acquisition_limit", ACQUISITION_LIMIT)
            )
            if not eligible:
                raise
            time.sleep(DNS_BACKOFF_SECONDS)
            attempt["dns_preflight_positive"] = dns_preflight()
            persist()
            if not attempt["dns_preflight_positive"]:
                raise
            archived = folder / "failed-attempts" / source["sample_id"] / "1"
            archived.parent.mkdir(parents=True, exist_ok=True)
            destination.rename(archived)
            state["dns_retries_used"] = state.get("dns_retries_used", 0) + 1
            # Reservation and counter are persisted by the next iteration before network.
        else:
            attempt.update(
                status="completed",
                cleanup=result.get("temporary_directory_removed") is True,
                seconds=time.monotonic() - started,
            )
            persist()
            return result
    raise AssertionError("unreachable_dns_attempt_state")


def run(parent, cohort, folder, root, *, max_videos, downloader=None, extractor=extract_row):
    if not 1 <= max_videos <= 269:
        raise ValueError("vlm_batch_limit_must_be_1_to_269")
    with lock(folder / ".lock"):
        plan, state = load_queue(parent, cohort, folder, root)
        if state["halt_reason"]:
            raise ValueError("vlm_queue_halted_no_automatic_retry")
        if any(e["status"] == "running" for e in state["entries"]):
            state["halt_reason"] = "interrupted_session_requires_audit"
            save(folder / "checkpoint.json", state)
            raise ValueError(state["halt_reason"])
        scratch = root / "data/private/media-temp"
        if list(scratch.glob("galaxies-media-*")):
            raise ValueError("temporary_session_pending")
        from scripts.prepare_gguf_vlm import prepare as prepare_runtime

        prepare_runtime(offline=True)
        if downloader is None:
            import imageio_ffmpeg

            from scripts.experiment_b_vlm_network import download_video

            ffmpeg = Path(imageio_ffmpeg.get_ffmpeg_exe())
            downloader = lambda media, sample: download_video(media, sample, ffmpeg)
        done = {e["sample_id"] for e in state["entries"]}
        used = 0
        for row in plan["rows"]:
            if row["sample_id"] in done:
                continue
            if used >= max_videos:
                break
            if attempt_count(state) + state.get("prior_acquisitions", 0) >= state.get(
                "acquisition_limit", 269
            ):
                state["halt_reason"] = "vlm_acquisition_budget"
                save(folder / "checkpoint.json", state)
                break
            if state["elapsed_seconds"] >= TIME_BUDGET:
                state["halt_reason"] = "vlm_total_time_budget"
                save(folder / "checkpoint.json", state)
                break
            sample = row["sample_id"]
            destination = folder / "sessions" / sample
            if destination.exists():
                raise ValueError("interrupted_vlm_output_requires_audit")
            entry = {"sample_id": sample, "status": "running"}
            state["entries"].append(entry)
            save(folder / "checkpoint.json", state)
            audit_destination = folder / "audit-sheets" / f"{sample}.png"
            started = time.monotonic()
            prior_elapsed = state["elapsed_seconds"]

            def persist(entry=entry, started=started, prior_elapsed=prior_elapsed):
                entry["seconds"] = time.monotonic() - started
                state["elapsed_seconds"] = prior_elapsed + entry["seconds"]
                save(folder / "checkpoint.json", state)

            try:
                with deadline(TIME_BUDGET - state["elapsed_seconds"]):
                    result = session_with_dns_recovery(
                        destination,
                        scratch,
                        lambda media, work, current=row, audit=audit_destination: extractor(
                            media, work, current, plan["config"], audit
                        ),
                        lambda media, selected=sample: downloader(media, selected),
                        source={
                            "sample_id": sample,
                            "purpose": PROTOCOL,
                            "outcomes_supplied": False,
                        },
                        model={"vlm": plan["config"]["model"]},
                        entry=entry,
                        state=state,
                        folder=folder,
                        persist=persist,
                    )
                if result["temporary_directory_removed"] is not True:
                    raise ValueError("vlm_cleanup_unconfirmed")
                entry.update(
                    status="completed",
                    files_sha256={
                        name: file_hash(destination / name)
                        for name in ("features.json", "run.json")
                    },
                    cleanup=True,
                )
            except BaseException as exc:
                reason = str(exc) if re.fullmatch(r"[a-z_]+", str(exc)) else type(exc).__name__
                if reason == "media_time_budget":
                    reason = "vlm_total_time_budget"
                record = destination / "run.json"
                result = json.loads(record.read_bytes()) if record.exists() else {}
                entry.update(
                    status="failed",
                    reason=reason,
                    cleanup=result.get("temporary_directory_removed") is True,
                )
                if entry.get("attempts") and entry["attempts"][-1]["status"] == "completed":
                    entry["attempts"][-1].update(status="failed", reason=reason)
                if isinstance(exc, VLMOutputError):
                    save(destination / "rejected-vlm.json", exc.evidence)
                    entry["rejected_vlm_sha256"] = file_hash(destination / "rejected-vlm.json")
                state["halt_reason"] = reason
                if not isinstance(exc, Exception):
                    raise
            finally:
                persist()
            used += 1
            print(json.dumps({"stage": "vlm_extraction", **entry}), flush=True)
            if state["halt_reason"]:
                break
        return {
            "completed": sum(e["status"] == "completed" for e in state["entries"]),
            "target": 269,
            "elapsed_seconds": state["elapsed_seconds"],
            "halt_reason": state["halt_reason"],
            "test_evaluated": False,
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("prepare", "inspect", "run"))
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--cohort-dir", type=Path, required=True)
    parser.add_argument("--queue", type=Path, required=True)
    parser.add_argument("--max-videos", type=int, default=1)
    parser.add_argument("--prior-budget", type=Path)
    args = parser.parse_args()
    root = Path.cwd()
    folder = private_path(args.queue, root)
    with reserved_guard(args.parent, root):
        if args.operation == "prepare":
            plan = prepare(
                args.parent, args.cohort_dir, folder, root, budget_receipt=args.prior_budget
            )
            report = {"rows": len(plan["rows"]), "audit": 32, "plan_sha256": plan["plan_sha256"]}
        elif args.operation == "inspect":
            with lock(folder / ".lock"):
                plan, state = load_queue(args.parent, args.cohort_dir, folder, root)
                report = {
                    "rows": len(plan["rows"]),
                    "completed": sum(e["status"] == "completed" for e in state["entries"]),
                    "halt_reason": state["halt_reason"],
                }
        else:
            report = run(args.parent, args.cohort_dir, folder, root, max_videos=args.max_videos)
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()

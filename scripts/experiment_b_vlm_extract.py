"""Development-only, resumable local VLM sidecars from committed contact-sheet pixels."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from importlib.metadata import version
from pathlib import Path

from scripts.channel_partitions import digest, load_partitions
from scripts.expansion_media import deadline
from scripts.experiment_a_artifact import ExperimentArtifact as AArtifact
from scripts.experiment_b_data import validate_cohort_boundary
from scripts.gguf_visual_attributes import RUNTIME, extract_visual_attributes, model_manifest
from scripts.pilot_licensed_media import frames_and_properties, run_session, select_vlm_samples
from scripts.pilot_youtube_media import download_video
from scripts.private_checkpoint import file_hash, lock, private_path, save
from scripts.retrain_expansion import reserved_guard

POLICY = "contact-sheet-cell-320x330-v1"
PROTOCOL = "b-vlm-sidecar-queue-v1"
AUDIT_PROTOCOL = "b-vlm-audit32-v1"
TIME_BUDGET = 27 * 3600
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
    "docs/issue-4-experimento-b-vlm-protocolo.md",
    "docs/issue-4-experimento-b-vlm-identidade.md",
    "uv.lock",
)


def configuration(root):
    return {
        "input_policy": POLICY,
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


def prepare(parent, cohort, folder, root):
    """No models, labels, outcomes or network; select dev before opening features."""
    manifest, anchor = anchored_metadata(parent, cohort, root)
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
                "elapsed_seconds": 0.0,
                "halt_reason": None,
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
    result = vlm(cells, seconds, scratch)
    if result["approved_for_training"] is not False:
        raise ValueError("automatic_training_approval_forbidden")
    if row["audit"]:
        audit_destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with audit_destination.open("xb") as output:
            audit_destination.chmod(0o600)
            output.write(sheet.read_bytes())
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

            ffmpeg = Path(imageio_ffmpeg.get_ffmpeg_exe())
            downloader = lambda media, sample: download_video(media, sample, ffmpeg)
        done = {e["sample_id"] for e in state["entries"]}
        used = 0
        for row in plan["rows"]:
            if row["sample_id"] in done:
                continue
            if used >= max_videos:
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
            try:
                with deadline(TIME_BUDGET - state["elapsed_seconds"]):
                    result = run_session(
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
                        model_manifest={"vlm": plan["config"]["model"]},
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
                audit_destination.unlink(missing_ok=True)
                state["halt_reason"] = reason
                if not isinstance(exc, Exception):
                    raise
            finally:
                entry["seconds"] = time.monotonic() - started
                state["elapsed_seconds"] += entry["seconds"]
                save(folder / "checkpoint.json", state)
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
    args = parser.parse_args()
    root = Path.cwd()
    folder = private_path(args.queue, root)
    with reserved_guard(args.parent, root):
        if args.operation == "prepare":
            plan = prepare(args.parent, args.cohort_dir, folder, root)
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

"""Develop once on revealed training images, freeze, and audit fresh training channels."""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path

from PIL import Image

from scripts.expansion_media import deadline
from scripts.experiment_b_vlm_extract import session_with_dns_recovery, verified_cells
from scripts.experiment_b_vlm_network import download_video
from scripts.experiment_b_vlm_quality import evaluate_gate, validate_fields
from scripts.gguf_visual_attributes import invoke_local_vlm
from scripts.pilot_licensed_media import frames_and_properties, select_vlm_samples
from scripts.prepare_gguf_vlm import prepare as prepare_runtime
from scripts.private_checkpoint import digest, file_hash, lock, private_path, save
from scripts.retrain_expansion import reserved_guard
from scripts.vlm_per_frame import BOOLEAN_FIELDS, extract, verify
from scripts.vlm_revision_plan import (
    ACQUISITION_LIMIT,
    BASE_ACQUISITIONS,
    CALL_LIMIT,
    OLD,
    TIME_LIMIT,
    load,
    persist,
    prepare,
    runnable,
)


def seconds_for(row):
    props = row["properties"]
    return select_vlm_samples(list(range(len(props["sampled_frame_seconds"]))), props)[1]


def clean_workspace(root):
    scratch = root / "data/private/media-temp"
    if list(scratch.glob("galaxies-media-*")) or list(scratch.glob("galaxies-inference-*")):
        raise ValueError("revision_temporary_session_requires_audit")


def crops(sheet, scratch, row):
    if file_hash(sheet) != row["sheet_sha256"]:
        raise ValueError("revision_sheet_commitment_mismatch")
    seconds = seconds_for(row)
    paths = []
    with Image.open(sheet) as picture:
        if picture.size != (320 * len(seconds), 360) or picture.mode != "RGB":
            raise ValueError("revision_sheet_dimensions_mismatch")
        for index in range(len(seconds)):
            path = scratch / f"frame-{index + 1}.png"
            picture.crop((320 * index, 25, 320 * (index + 1), 355)).save(path)
            paths.append(path)
    return paths, seconds


def acquire_row(media, scratch, row, image):
    properties, frames = frames_and_properties(media, scratch)
    if properties != row["properties"]:
        raise ValueError("revision_frozen_properties_mismatch")
    selected, seconds = select_vlm_samples(frames, properties)
    cells, sheet = verified_cells(selected, seconds, row, scratch)
    image.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    with image.open("xb") as output:
        image.chmod(0o600)
        output.write(sheet.read_bytes())
    return {
        "sample_id": row["sample_id"],
        "group": row["group"],
        "sheet_sha256": file_hash(image),
        "properties": properties,
        "frozen_media_sha256": row["media_sha256"],
        "reacquired_media_sha256": file_hash(media),
        "input_png_sha256": [file_hash(p) for p in cells],
        "input_frame_seconds": seconds,
        "labels_used": False,
        "test_evaluated": False,
    }


def acquire(parent, cohort, folder, root, *, group, limit, downloader=None):
    if group not in ("development", "audit") or not 1 <= limit <= 32:
        raise ValueError("invalid_revision_acquisition_batch")
    with lock(folder / ".lock"):
        plan, state = load(parent, cohort, folder, root)
        runnable(state)
        clean_workspace(root)
        if downloader is None:
            import imageio_ffmpeg

            ffmpeg = Path(imageio_ffmpeg.get_ffmpeg_exe())
            downloader = lambda media, sample: download_video(media, sample, ffmpeg)
        done = {e["sample_id"] for e in state["entries"]}
        used = 0
        for row in plan["rows"]:
            if row["group"] != group or row["sample_id"] in done:
                continue
            if used >= limit:
                break
            if (
                BASE_ACQUISITIONS + sum(len(e["attempts"]) for e in state["entries"])
                >= ACQUISITION_LIMIT
            ):
                raise ValueError("revision_acquisition_budget_exhausted")
            destination = folder / "sessions" / row["sample_id"]
            if destination.exists():
                raise ValueError("revision_interrupted_acquisition_output")
            entry = {
                "sample_id": row["sample_id"],
                "status": "running",
                "attempts": [{"status": "running"}],
            }
            state["entries"].append(entry)
            started = time.monotonic()
            checkpoint = lambda entry=entry, started=started: persist(
                folder, state, entry, started, time.monotonic
            )
            checkpoint()
            try:
                with deadline(TIME_LIMIT - state["elapsed_seconds"]):
                    result = session_with_dns_recovery(
                        destination,
                        root / "data/private/media-temp",
                        lambda media, scratch, current=row: acquire_row(
                            media,
                            scratch,
                            current,
                            folder / "images" / f"{current['sample_id']}.png",
                        ),
                        lambda media, sample=row["sample_id"]: downloader(media, sample),
                        source={
                            "sample_id": row["sample_id"],
                            "purpose": "perceptual_revision_identity_only",
                        },
                        model={"vlm_called": False},
                        entry=entry,
                        state=state,
                        folder=folder,
                        persist=checkpoint,
                    )
                if result["temporary_directory_removed"] is not True:
                    raise ValueError("revision_cleanup_unconfirmed")
                entry.update(
                    status="completed",
                    cleanup=True,
                    files_sha256={
                        name: file_hash(destination / name)
                        for name in ("features.json", "run.json")
                    },
                )
            except BaseException as exc:
                entry.update(status="failed", reason=type(exc).__name__)
                if entry["attempts"][-1]["status"] == "completed":
                    entry["attempts"][-1]["status"] = "failed"
                state["halt_reason"] = str(exc)
                raise
            finally:
                checkpoint()
            used += 1
            print(
                json.dumps(
                    {
                        "stage": "revision_acquisition",
                        "group": group,
                        "completed": len(state["entries"]),
                        "dns_retries": state["dns_retries_used"],
                    }
                ),
                flush=True,
            )
        return state


def result_path(folder, candidate, sample):
    return folder / "inferences" / candidate / sample / "result.json"


def checked_result(folder, plan, row, candidate):
    path = result_path(folder, candidate, row["sample_id"])
    body = json.loads(path.read_bytes())
    if (
        body["sample_id"] != row["sample_id"]
        or body["group"] != row["group"]
        or body["plan_sha256"] != plan["plan_sha256"]
        or body["config_sha256"] != digest(plan["config"])
        or body["sheet_sha256"] != row["sheet_sha256"]
        or body["vlm"]["candidate"] != candidate
        or body["vlm"]["input_frame_seconds"] != seconds_for(row)
    ):
        raise ValueError("incompatible_revision_perception_result")
    parsed = verify(body["vlm"], path.parent / "calls")
    identity = json.loads((folder / "sessions" / row["sample_id"] / "features.json").read_bytes())
    if body["vlm"]["input_png_sha256"] != identity["input_png_sha256"]:
        raise ValueError("revision_perception_input_pixels_changed")
    return parsed


def scoring(folder, plan, root):
    annotations = json.loads((root / OLD / "blind-annotations-v3.json").read_bytes())
    if file_hash(root / OLD / "blind-annotations-v3.json") != plan["old_annotations_sha256"]:
        raise ValueError("revision_development_annotations_changed")
    rows = [r for r in plan["rows"] if r["group"] == "development"]
    truth = {a["sample_id"]: a["fields"] for a in annotations["rows"]}
    if set(truth) != {r["sample_id"] for r in rows}:
        raise ValueError("revision_development_alignment_mismatch")
    scores, hashes = {}, {}
    for candidate in ("A", "B"):
        correct = unsupported = known = 0
        hashes[candidate] = {}
        for row in rows:
            parsed = checked_result(folder, plan, row, candidate)
            hashes[candidate][row["sample_id"]] = file_hash(
                result_path(folder, candidate, row["sample_id"])
            )
            for field in BOOLEAN_FIELDS:
                p, a = parsed[field], truth[row["sample_id"]][field]
                if p["value"] == "unknown":
                    continue
                known += 1
                support = bool(p["frames"]) and set(p["frames"]) <= set(a["frames"])
                unsupported += not support
                correct += p["value"] == a["value"] and support
        scores[candidate] = {
            "correct": correct,
            "unsupported": unsupported,
            "known": known,
            "pairs": 96,
            "native_calls": sum(len(seconds_for(r)) for r in rows) * (1 if candidate == "A" else 3),
        }
    choice = min(
        scores,
        key=lambda c: (
            -scores[c]["correct"],
            scores[c]["unsupported"],
            -scores[c]["known"],
            scores[c]["native_calls"],
            c,
        ),
    )
    body = {
        "plan_sha256": plan["plan_sha256"],
        "config_sha256": digest(plan["config"]),
        "candidate": choice,
        "development_scores": scores,
        "development_results_sha256": hashes,
        "new_audit_used_for_selection": False,
        "predictive_outcomes_used": False,
    }
    body["selection_sha256"] = digest(body)
    return body


def selection(folder, plan, root):
    if not (folder / "selection.json").is_file():
        raise ValueError("revision_audit_requires_frozen_candidate")
    stored = json.loads((folder / "selection.json").read_bytes())
    if stored != scoring(folder, plan, root):
        raise ValueError("revision_selection_or_sources_changed")
    return stored


def infer(parent, cohort, folder, root, *, group, candidate, limit, invoker=invoke_local_vlm):
    if group not in ("development", "audit") or candidate not in ("A", "B") or not 1 <= limit <= 32:
        raise ValueError("invalid_revision_inference_batch")
    with lock(folder / ".lock"):
        plan, state = load(parent, cohort, folder, root)
        runnable(state)
        clean_workspace(root)
        if group == "audit" and candidate != selection(folder, plan, root)["candidate"]:
            raise ValueError("revision_audit_requires_frozen_candidate")
        prepare_runtime(offline=True)
        acquired = {e["sample_id"] for e in state["entries"] if e["status"] == "completed"}
        done = {(e["sample_id"], e["candidate"]) for e in state["inferences"]}
        used = 0
        for row in plan["rows"]:
            if row["group"] != group or (row["sample_id"], candidate) in done:
                continue
            if used >= limit:
                break
            if row["sample_id"] not in acquired:
                raise ValueError("revision_verified_image_required")
            path = result_path(folder, candidate, row["sample_id"])
            if path.parent.exists():
                raise ValueError("revision_interrupted_inference_output")
            entry = {
                "sample_id": row["sample_id"],
                "candidate": candidate,
                "status": "running",
                "call_count": 0,
            }
            state["inferences"].append(entry)
            started = time.monotonic()
            checkpoint = lambda entry=entry, started=started: persist(
                folder, state, entry, started, time.monotonic
            )
            checkpoint()

            def counted(*args, entry=entry, checkpoint=checkpoint, **kwargs):
                if state["calls_reserved"] >= CALL_LIMIT:
                    raise ValueError("revision_native_call_budget_exhausted")
                entry["call_count"] += 1
                state["calls_reserved"] += 1
                checkpoint()
                return invoker(*args, **kwargs)

            try:
                with deadline(TIME_LIMIT - state["elapsed_seconds"]):
                    scratch_root = root / "data/private/media-temp"
                    scratch_root.mkdir(parents=True, exist_ok=True)
                    with tempfile.TemporaryDirectory(
                        prefix="galaxies-inference-", dir=scratch_root
                    ) as work:
                        cells, seconds = crops(
                            folder / "images" / f"{row['sample_id']}.png", Path(work), row
                        )
                        result = extract(
                            cells,
                            seconds,
                            Path(work),
                            candidate=candidate,
                            evidence_dir=path.parent / "calls",
                            invoker=counted,
                        )
                    save(
                        path,
                        {
                            "sample_id": row["sample_id"],
                            "group": group,
                            "plan_sha256": plan["plan_sha256"],
                            "config_sha256": digest(plan["config"]),
                            "sheet_sha256": row["sheet_sha256"],
                            "vlm": result,
                        },
                    )
                    checked_result(folder, plan, row, candidate)
                entry.update(status="completed", result_sha256=file_hash(path))
            except BaseException as exc:
                entry.update(status="failed", reason=type(exc).__name__)
                state["halt_reason"] = str(exc)
                raise
            finally:
                checkpoint()
            used += 1
            print(
                json.dumps(
                    {
                        "stage": "revision_inference",
                        "group": group,
                        "candidate": candidate,
                        "completed": len(state["inferences"]),
                        "calls_reserved": state["calls_reserved"],
                    }
                ),
                flush=True,
            )
        return state


def freeze(parent, cohort, folder, root):
    with lock(folder / ".lock"):
        plan, state = load(parent, cohort, folder, root)
        runnable(state)
        if (folder / "selection.json").exists():
            raise ValueError("revision_selection_already_frozen")
        expected = {
            (r["sample_id"], c)
            for r in plan["rows"]
            if r["group"] == "development"
            for c in ("A", "B")
        }
        complete = {
            (e["sample_id"], e["candidate"])
            for e in state["inferences"]
            if e["status"] == "completed"
        }
        if complete != expected:
            raise ValueError("revision_requires_complete_development_pairs")
        body = scoring(folder, plan, root)
        save(folder / "selection.json", body)
        return body


def publish(parent, cohort, folder, root, annotations_path):
    with lock(folder / ".lock"):
        plan, state = load(parent, cohort, folder, root)
        runnable(state)
        chosen = selection(folder, plan, root)
        raw = annotations_path.read_bytes()
        annotations = json.loads(raw)
        rows = [r for r in plan["rows"] if r["group"] == "audit"]
        if (
            set(annotations)
            != {
                "schema_version",
                "plan_sha256",
                "blind_to_vlm_outputs",
                "blind_to_outcomes",
                "human_review",
                "rows",
            }
            or annotations["schema_version"] != "b-vlm-blind-annotations-v1"
            or annotations["plan_sha256"] != plan["plan_sha256"]
            or annotations["blind_to_vlm_outputs"] is not True
            or annotations["blind_to_outcomes"] is not True
            or annotations["human_review"] is not False
            or [a["sample_id"] for a in annotations["rows"]] != [r["sample_id"] for r in rows]
        ):
            raise ValueError("revision_fixed_blind_annotations_required")
        complete = {
            (e["sample_id"], e["candidate"])
            for e in state["inferences"]
            if e["status"] == "completed"
        }
        observations, hashes = [], {}
        for row, annotation in zip(rows, annotations["rows"], strict=True):
            if (
                set(annotation) != {"sample_id", "sheet_sha256", "fields"}
                or annotation["sheet_sha256"] != row["sheet_sha256"]
                or file_hash(folder / "images" / f"{row['sample_id']}.png") != row["sheet_sha256"]
                or (row["sample_id"], chosen["candidate"]) not in complete
            ):
                raise ValueError("revision_blind_image_or_inference_mismatch")
            validate_fields(annotation["fields"], seconds_for(row))
            parsed = checked_result(folder, plan, row, chosen["candidate"])
            observations.append(
                {"sector": row["sector"], "predicted": parsed, "annotated": annotation["fields"]}
            )
            hashes[row["sample_id"]] = file_hash(
                result_path(folder, chosen["candidate"], row["sample_id"])
            )
        proof = evaluate_gate(observations) | {
            "plan_sha256": plan["plan_sha256"],
            "selection_sha256": chosen["selection_sha256"],
            "annotations_sha256": digest(annotations),
            "annotations_file_sha256": file_hash(annotations_path),
            "audit_results_sha256": hashes,
            "candidate_fields": list(BOOLEAN_FIELDS),
            "source_config_sha256": digest(plan["config"]),
            "predictive_training_started": False,
            "test_evaluated": False,
            "m1_replaced": False,
        }
        proof["release_sha256"] = digest(proof)
        output = folder / "quality-release.json"
        if output.exists():
            raise ValueError("revision_quality_already_published")
        save(output, proof)
        state["halt_reason"] = (
            "audit_completed_columns_released"
            if proof["released_fields"]
            else "quality_gate_no_columns_released"
        )
        state["quality_release_sha256"] = file_hash(output)
        save(folder / "checkpoint.json", state)
        return proof


def dispose(parent, cohort, folder, root):
    with lock(folder / ".lock"):
        plan, state = load(parent, cohort, folder, root)
        if state["halt_reason"] not in (
            "audit_completed_columns_released",
            "quality_gate_no_columns_released",
        ):
            raise ValueError("revision_completed_gate_required_for_disposal")
        if (
            state["images_disposed"]
            or file_hash(folder / "quality-release.json") != state["quality_release_sha256"]
        ):
            raise ValueError("revision_disposal_or_quality_evidence_changed")
        images = {r["sample_id"]: r["sheet_sha256"] for r in plan["rows"]}
        for sample, expected in images.items():
            if file_hash(folder / "images" / f"{sample}.png") != expected:
                raise ValueError("revision_disposal_image_changed")
        receipt = {
            "plan_sha256": plan["plan_sha256"],
            "quality_release_sha256": state["quality_release_sha256"],
            "images": images,
            "videos_retained": False,
        }
        save(folder / "image-disposal.json", receipt)
        for sample in images:
            (folder / "images" / f"{sample}.png").unlink()
        state["images_disposed"] = True
        state["disposal_sha256"] = file_hash(folder / "image-disposal.json")
        save(folder / "checkpoint.json", state)
        return {"images_removed": len(images), "temporary_media_retained": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation",
        choices=("prepare", "inspect", "acquire", "infer", "freeze", "publish", "dispose"),
    )
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--cohort-dir", type=Path, required=True)
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--group", choices=("development", "audit"), default="development")
    parser.add_argument("--candidate", choices=("A", "B"), default="A")
    parser.add_argument("--limit", type=int, default=1)
    parser.add_argument("--annotations", type=Path)
    args = parser.parse_args()
    root = Path.cwd()
    folder = private_path(args.folder, root)
    with reserved_guard(args.parent, root):
        if args.operation == "prepare":
            plan = prepare(args.parent, args.cohort_dir, folder, root)
            report = {"plan_sha256": plan["plan_sha256"], "training_images": len(plan["rows"])}
        elif args.operation == "inspect":
            _, state = load(args.parent, args.cohort_dir, folder, root)
            report = {
                "acquisitions": len(state["entries"]),
                "inferences": len(state["inferences"]),
                "calls_reserved": state["calls_reserved"],
                "halt_reason": state["halt_reason"],
            }
        elif args.operation == "acquire":
            state = acquire(
                args.parent, args.cohort_dir, folder, root, group=args.group, limit=args.limit
            )
            report = {"completed_acquisitions": len(state["entries"]), "test_evaluated": False}
        elif args.operation == "infer":
            state = infer(
                args.parent,
                args.cohort_dir,
                folder,
                root,
                group=args.group,
                candidate=args.candidate,
                limit=args.limit,
            )
            report = {"completed_inferences": len(state["inferences"]), "test_evaluated": False}
        elif args.operation == "freeze":
            chosen = freeze(args.parent, args.cohort_dir, folder, root)
            report = {
                "candidate": chosen["candidate"],
                "development_scores": chosen["development_scores"],
                "selection_sha256": chosen["selection_sha256"],
            }
        elif args.operation == "dispose":
            report = dispose(args.parent, args.cohort_dir, folder, root)
        else:
            if args.annotations is None:
                parser.error("--annotations required for publish")
            proof = publish(
                args.parent, args.cohort_dir, folder, root, private_path(args.annotations, root)
            )
            report = {
                "released_fields": proof["released_fields"],
                "release_sha256": proof["release_sha256"],
            }
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()

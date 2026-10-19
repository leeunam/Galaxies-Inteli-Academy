"""V8 development against cached V7 on exactly the 64 revealed training cases."""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from scripts.expansion_media import deadline
from scripts.experiment_b_vlm_extract import session_with_dns_recovery
from scripts.experiment_b_vlm_network import download_video
from scripts.experiment_b_vlm_quality import evaluate_gate, normalized, validate_fields
from scripts.gguf_visual_attributes import invoke_local_vlm
from scripts.prepare_gguf_vlm import prepare as prepare_runtime
from scripts.private_checkpoint import digest, file_hash, lock, private_path, save
from scripts.retrain_expansion import reserved_guard
from scripts.vlm_explicit_presence import extract, verify
from scripts.vlm_per_frame import BOOLEAN_FIELDS
from scripts.vlm_prompt_plan import (
    ACQUISITION_LIMIT,
    BASE_ACQUISITIONS,
    CALL_LIMIT,
    FONT,
    PREVIOUS,
    TIME_LIMIT,
    load,
    persist,
    prepare,
    prior,
    result_path,
    runnable,
)
from scripts.vlm_revision import (
    acquire_row,
    clean_workspace,
    crops,
    seconds_for,
)
from scripts.vlm_revision import (
    checked_result as previous_result,
)


def render_control(row, path):
    image = Image.new("RGB", (320, 330), "black" if row["sample_id"] == "black" else "white")
    draw = ImageDraw.Draw(image)
    if row["text"]:
        font = ImageFont.truetype(str(FONT), row["size"])
        draw.text((8, row["y"]), "ABC123", font=font, fill=(row["gray"],) * 3)
    elif row["sample_id"] == "lines":
        for y in range(20, 320, 24):
            draw.line((12, y, 308, y), fill="black", width=2)
    elif row["sample_id"] == "shapes":
        draw.ellipse((20, 20, 130, 130), outline="black", width=5)
        draw.rectangle((160, 170, 300, 300), outline="black", width=5)
    image.save(path)


def checked_identity(folder, row, root):
    current = json.loads((folder / "sessions" / row["sample_id"] / "features.json").read_bytes())
    previous = json.loads(
        (root / PREVIOUS / "sessions" / row["sample_id"] / "features.json").read_bytes()
    )
    run = json.loads((folder / "sessions" / row["sample_id"] / "run.json").read_bytes())
    if (
        current["sample_id"] != row["sample_id"]
        or current["properties"] != row["properties"]
        or current["sheet_sha256"] != row["sheet_sha256"]
        or current["input_frame_seconds"] != seconds_for(row)
        or current["input_png_sha256"] != previous["input_png_sha256"]
        or run["status"] != "completed"
        or run["temporary_directory_removed"] is not True
    ):
        raise ValueError("v8_original_pixels_or_times_changed")
    return current


def checked_result(folder, plan, row, root):
    path = result_path(folder, row["sample_id"])
    body = json.loads(path.read_bytes())
    identity = checked_identity(folder, row, root)
    if (
        body["sample_id"] != row["sample_id"]
        or body["plan_sha256"] != plan["plan_sha256"]
        or body["config_sha256"] != digest(plan["config"])
        or body["sheet_sha256"] != row["sheet_sha256"]
        or body["vlm"]["input_png_sha256"] != identity["input_png_sha256"]
        or body["vlm"]["input_frame_seconds"] != seconds_for(row)
    ):
        raise ValueError("v8_result_identity_changed")
    return verify(body["vlm"], path.parent / "calls")


def require_controls(state):
    if len(state["controls"]) != 12 or any(e["status"] != "completed" for e in state["controls"]):
        raise ValueError("v8_complete_controls_required")


def acquire(parent, cohort, folder, root, *, limit, downloader=None):
    if not 1 <= limit <= 64:
        raise ValueError("v8_invalid_batch_size")
    with lock(folder / ".lock"):
        plan, state = load(parent, cohort, folder, root)
        runnable(state)
        clean_workspace(root)
        require_controls(state)
        if downloader is None:
            import imageio_ffmpeg

            ffmpeg = Path(imageio_ffmpeg.get_ffmpeg_exe())
            downloader = lambda media, sample: download_video(media, sample, ffmpeg)
        done = {e["sample_id"] for e in state["entries"]}
        used = 0
        for row in plan["rows"]:
            if row["sample_id"] in done:
                continue
            if used >= limit:
                break
            if (
                BASE_ACQUISITIONS + sum(len(e["attempts"]) for e in state["entries"])
                >= ACQUISITION_LIMIT
            ):
                raise ValueError("v8_acquisition_budget_exhausted")
            destination = folder / "sessions" / row["sample_id"]
            if destination.exists():
                raise ValueError("v8_interrupted_acquisition_output")
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
                            folder / "images" / (current["sample_id"] + ".png"),
                        ),
                        lambda media, sample=row["sample_id"]: downloader(media, sample),
                        source={
                            "sample_id": row["sample_id"],
                            "purpose": "v8_revealed_development_identity_only",
                        },
                        model={"vlm_called": False},
                        entry=entry,
                        state=state,
                        folder=folder,
                        persist=checkpoint,
                    )
                if result["temporary_directory_removed"] is not True:
                    raise ValueError("v8_cleanup_unconfirmed")
                checked_identity(folder, row, root)
                entry.update(
                    status="completed",
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
                        "stage": "v8_acquisition",
                        "completed": len(state["entries"]),
                        "dns_retries": state["dns_retries_used"],
                    }
                ),
                flush=True,
            )
    return state


def _one_inference(folder, plan, state, row, root, *, control, invoker):
    path = result_path(folder, row["sample_id"], control)
    if path.parent.exists():
        raise ValueError("v8_interrupted_inference_output")
    entry = {"sample_id": row["sample_id"], "status": "running", "call_count": 0}
    state["controls" if control else "inferences"].append(entry)
    started = time.monotonic()
    checkpoint = lambda: persist(folder, state, entry, started, time.monotonic)
    checkpoint()

    def counted(*args, **kwargs):
        if state["calls_reserved"] >= CALL_LIMIT:
            raise ValueError("v8_native_call_budget_exhausted")
        state["calls_reserved"] += 1
        entry["call_count"] += 1
        checkpoint()
        return invoker(*args, **kwargs)

    try:
        with deadline(TIME_LIMIT - state["elapsed_seconds"]):
            scratch = root / "data/private/media-temp"
            scratch.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(
                prefix="galaxies-inference-v8-", dir=scratch
            ) as temporary:
                work = Path(temporary)
                if control:
                    cell = work / "control.png"
                    render_control(row, cell)
                    cells, seconds = [cell], [0.2]
                    entry["input_png_sha256"] = file_hash(cell)
                else:
                    identity = checked_identity(folder, row, root)
                    cells, seconds = crops(
                        folder / "images" / (row["sample_id"] + ".png"), work, row
                    )
                    if [file_hash(c) for c in cells] != identity["input_png_sha256"]:
                        raise ValueError("v8_crop_pixels_changed")
                result = extract(
                    cells, seconds, work, evidence_dir=path.parent / "calls", invoker=counted
                )
            body = {
                "sample_id": row["sample_id"],
                "plan_sha256": plan["plan_sha256"],
                "config_sha256": digest(plan["config"]),
                "vlm": result,
            }
            if not control:
                body["sheet_sha256"] = row["sheet_sha256"]
            save(path, body)
            if control:
                verify(result, path.parent / "calls")
                if result["input_png_sha256"] != [entry["input_png_sha256"]]:
                    raise ValueError("v8_control_identity_changed")
            else:
                checked_result(folder, plan, row, root)
            entry.update(status="completed", result_sha256=file_hash(path))
    except BaseException as exc:
        entry.update(status="failed", reason=type(exc).__name__)
        state["halt_reason"] = str(exc)
        raise
    finally:
        checkpoint()


def infer(parent, cohort, folder, root, *, limit, control=False, invoker=invoke_local_vlm):
    if not 1 <= limit <= (12 if control else 64):
        raise ValueError("v8_invalid_batch_size")
    with lock(folder / ".lock"):
        plan, state = load(parent, cohort, folder, root)
        runnable(state)
        clean_workspace(root)
        if not control:
            require_controls(state)
        prepare_runtime(offline=True)
        done = {e["sample_id"] for e in state["controls" if control else "inferences"]}
        acquired = {e["sample_id"] for e in state["entries"] if e["status"] == "completed"}
        used = 0
        for row in plan["config"]["controls"] if control else plan["rows"]:
            if row["sample_id"] in done:
                continue
            if used >= limit:
                break
            if not control and row["sample_id"] not in acquired:
                raise ValueError("v8_verified_image_required")
            _one_inference(folder, plan, state, row, root, control=control, invoker=invoker)
            used += 1
            print(
                json.dumps(
                    {
                        "stage": "v8_controls" if control else "v8_development",
                        "completed": len(state["controls" if control else "inferences"]),
                        "calls_reserved": state["calls_reserved"],
                    }
                ),
                flush=True,
            )
    return state


def metrics(observations):
    result = {}
    for field in BOOLEAN_FIELDS:
        sectors = {}
        for sector in ("beleza", "moda", "all"):
            rows = [o for o in observations if sector == "all" or o["sector"] == sector]
            known = correct = value_correct = unsupported = 0
            support = Counter()
            confusion = Counter()
            positive = Counter()
            absent = Counter()
            for observation in rows:
                p, a = observation["predicted"][field], observation["annotated"][field]
                pv, av = normalized(field, p["value"]), normalized(field, a["value"])
                support[pv] += 1
                confusion[(av, pv)] += 1
                if pv != "unknown":
                    known += 1
                    value_correct += pv == av
                    ok = bool(p["frames"]) and set(p["frames"]) <= set(a["frames"])
                    unsupported += not ok
                    correct += pv == av and ok
                if type(a["value"]) is bool:
                    target = positive if a["value"] else absent
                    for index in a["frames"]:
                        target[normalized(field, observation["per_frame"][index - 1][field])] += 1
            sectors[sector] = {
                "samples": len(rows),
                "known": known,
                "unknown": len(rows) - known,
                "correct_value_only": value_correct,
                "correct_value_and_evidence": correct,
                "unsupported_evidence": unsupported,
                "agreement": correct / known if known else None,
                "predicted_value_support": dict(support),
                "confusion": [
                    {"annotated": a, "predicted": p, "count": n}
                    for (a, p), n in sorted(confusion.items())
                ],
                "annotated_positive_frames": dict(positive),
                "annotated_absent_frames": dict(absent),
            }
        result[field] = sectors
    return result


def compare(parent, cohort, folder, root):
    with lock(folder / ".lock"):
        plan, state = load(parent, cohort, folder, root)
        if state["halt_reason"] == "development_comparison_completed":
            if file_hash(folder / "comparison.json") != state["comparison_file_sha256"]:
                raise ValueError("v8_comparison_changed")
            return json.loads((folder / "comparison.json").read_bytes())
        runnable(state)
        clean_workspace(root)
        require_controls(state)
        expected = {r["sample_id"] for r in plan["rows"]}
        if {e["sample_id"] for e in state["inferences"] if e["status"] == "completed"} != expected:
            raise ValueError("v8_complete_64_required")
        previous, _ = prior(parent, cohort, root)
        truth = {}
        for group, ref in plan["annotations"].items():
            rows = json.loads((root / ref).read_bytes())["rows"]
            wanted = [r for r in plan["rows"] if r["group"] == group]
            if [a["sample_id"] for a in rows] != [r["sample_id"] for r in wanted]:
                raise ValueError("v8_annotation_order_changed")
            for row, annotation in zip(wanted, rows, strict=True):
                if annotation["sheet_sha256"] != row["sheet_sha256"]:
                    raise ValueError("v8_annotation_image_changed")
                validate_fields(annotation["fields"], seconds_for(row))
                truth[row["sample_id"]] = annotation["fields"]
        observations = {"v8": [], "v7_A": [], "v7_B_old32": []}
        hashes = {}
        for row in plan["rows"]:
            identity = checked_identity(folder, row, root)
            predicted = checked_result(folder, plan, row, root)
            current = json.loads(result_path(folder, row["sample_id"]).read_bytes())["vlm"]
            cached = previous_result(root / PREVIOUS, previous, row, "A")
            cached_body = json.loads(
                (root / PREVIOUS / "inferences/A" / row["sample_id"] / "result.json").read_bytes()
            )["vlm"]
            if (
                current["input_png_sha256"] != cached_body["input_png_sha256"]
                or current["input_frame_seconds"] != cached_body["input_frame_seconds"]
                or identity["input_png_sha256"] != current["input_png_sha256"]
            ):
                raise ValueError("v8_paired_inputs_changed")
            base = {
                "sample_id": row["sample_id"],
                "origin": row["group"],
                "sector": row["sector"],
                "annotated": truth[row["sample_id"]],
            }
            observations["v8"].append(
                base | {"predicted": predicted, "per_frame": current["per_frame"]}
            )
            observations["v7_A"].append(
                base | {"predicted": cached, "per_frame": cached_body["per_frame"]}
            )
            hashes[row["sample_id"]] = file_hash(result_path(folder, row["sample_id"]))
            if row["group"] == "development":
                b = previous_result(root / PREVIOUS, previous, row, "B")
                raw = json.loads(
                    (
                        root / PREVIOUS / "inferences/B" / row["sample_id"] / "result.json"
                    ).read_bytes()
                )["vlm"]
                observations["v7_B_old32"].append(
                    base | {"predicted": b, "per_frame": raw["per_frame"]}
                )
        scores = {}
        gates = {}
        for version, rows in observations.items():
            scores[version] = {"all_available": metrics(rows)}
            gates[version] = {}
            for group in ("development", "audit"):
                part = [o for o in rows if o["origin"] == group]
                if part:
                    scores[version][group] = metrics(part)
                    gates[version][group] = evaluate_gate(part)
        ready = [
            f
            for f in BOOLEAN_FIELDS
            if all(f in gates["v8"][g]["released_fields"] for g in ("development", "audit"))
        ]
        control_scores = {}
        for field in BOOLEAN_FIELDS:
            counts = Counter()
            for row in plan["config"]["controls"]:
                body = json.loads(result_path(folder, row["sample_id"], True).read_bytes())
                value = verify(
                    body["vlm"], result_path(folder, row["sample_id"], True).parent / "calls"
                )[field]["value"]
                actual = row["text"] if field == "screen_text" else False
                counts[normalized(field, value)] += 1
                counts["correct"] += value == actual
            control_scores[field] = dict(counts)
        proof = {
            "status": "development_only_comparison_complete",
            "plan_sha256": plan["plan_sha256"],
            "metrics": scores,
            "original_gate_by_origin": gates,
            "fields_ready_for_future_blind_audit": ready,
            "released_fields": [],
            "controls": control_scores,
            "result_sha256": hashes,
            "same_pixels_and_times": True,
            "new_blind_audit": False,
            "general_perception_accuracy_validated": False,
            "predictive_training_started": False,
            "test_evaluated": False,
            "m1_replaced": False,
        }
        proof["comparison_sha256"] = digest(proof)
        output = folder / "comparison.json"
        if output.exists():
            if digest(json.loads(output.read_bytes())) != digest(proof):
                raise ValueError("v8_interrupted_comparison_changed")
        else:
            save(output, proof)
        state["comparison_file_sha256"] = file_hash(output)
        state["halt_reason"] = "development_comparison_completed"
        save(folder / "checkpoint.json", state)
        return proof


def dispose(parent, cohort, folder, root):
    with lock(folder / ".lock"):
        plan, state = load(parent, cohort, folder, root)
        if state["halt_reason"] != "development_comparison_completed":
            raise ValueError("v8_completed_comparison_required")
        if file_hash(folder / "comparison.json") != state["comparison_file_sha256"]:
            raise ValueError("v8_comparison_changed")
        images = {r["sample_id"]: r["sheet_sha256"] for r in plan["rows"]}
        if state["images_disposed"]:
            return {"images_removed": len(images), "temporary_media_retained": False}
        if "cleanup_pending" not in state:
            for sample, sha in images.items():
                if file_hash(folder / "images" / (sample + ".png")) != sha:
                    raise ValueError("v8_disposal_image_changed")
            receipt = {
                "images": images,
                "plan_sha256": plan["plan_sha256"],
                "comparison_file_sha256": state["comparison_file_sha256"],
            }
            journal = folder / "image-disposal.json"
            if journal.exists():
                if json.loads(journal.read_bytes()) != receipt:
                    raise ValueError("v8_disposal_evidence_changed")
            else:
                save(journal, receipt)
            state.update(cleanup_pending=list(images), disposal_sha256=file_hash(journal))
            save(folder / "checkpoint.json", state)
        for sample in list(state["cleanup_pending"]):
            image = folder / "images" / (sample + ".png")
            if image.exists() and file_hash(image) != images[sample]:
                raise ValueError("v8_disposal_image_changed")
            image.unlink(missing_ok=True)
            state["cleanup_pending"].remove(sample)
            save(folder / "checkpoint.json", state)
        state["images_disposed"] = True
        save(folder / "checkpoint.json", state)
        return {"images_removed": len(images), "temporary_media_retained": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "operation",
        choices=("prepare", "controls", "acquire", "infer", "compare", "dispose", "inspect"),
    )
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--cohort-dir", type=Path, required=True)
    parser.add_argument("--folder", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=1)
    args = parser.parse_args()
    root = Path.cwd()
    folder = private_path(args.folder, root)
    with reserved_guard(args.parent, root):
        common = (args.parent, args.cohort_dir, folder, root)
        if args.operation == "prepare":
            report = {"plan_sha256": prepare(*common)["plan_sha256"], "revealed_training_cases": 64}
        elif args.operation in ("controls", "infer"):
            state = infer(*common, limit=args.limit, control=args.operation == "controls")
            report = {"calls_reserved": state["calls_reserved"], "test_evaluated": False}
        elif args.operation == "acquire":
            report = {"acquisitions": len(acquire(*common, limit=args.limit)["entries"])}
        elif args.operation == "compare":
            proof = compare(*common)
            report = {
                "comparison_sha256": proof["comparison_sha256"],
                "ready_fields": proof["fields_ready_for_future_blind_audit"],
                "released_fields": [],
            }
        elif args.operation == "dispose":
            report = dispose(*common)
        else:
            _, state = load(*common)
            report = {
                "acquisitions": len(state["entries"]),
                "controls": len(state["controls"]),
                "inferences": len(state["inferences"]),
                "calls_reserved": state["calls_reserved"],
                "halt_reason": state["halt_reason"],
            }
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()

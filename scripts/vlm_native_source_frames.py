"""Offline frame bridge only; no downloader, credential getter or model invocation."""

from __future__ import annotations

import argparse
import json

from scripts import vlm_native_source_recovery as recovery
from scripts.demo_recovery_policy import RecoveryError, digest, read_json


def exact_frame(media, seconds):
    import av

    with av.open(str(media)) as container:
        stream = container.streams.video[0]
        previous = None
        for frame in container.decode(stream):
            if frame.time is None or (previous is not None and float(frame.time) < previous):
                raise RecoveryError("native_pts_invalid")
            value = float(frame.time)
            if value == seconds:
                picture = frame.to_image()
                if picture.mode != "RGB" or picture.size != (360, 640):
                    raise RecoveryError("native_geometry_changed")
                return picture
            if value > seconds:
                break
            previous = value
    raise RecoveryError("exact_native_pts_missing")


def bridge(media, work, case, *, legacy=None, select=None, cells=None, native=None):
    # Imports have no execution path to ASR/CLIP/Qwen; only these old image functions run.
    if legacy is None:
        from scripts.experiment_b_vlm_extract import verified_cells
        from scripts.pilot_licensed_media import frames_and_properties, select_vlm_samples

        legacy, select, cells = frames_and_properties, select_vlm_samples, verified_cells
    native = exact_frame if native is None else native
    props, paths = legacy(media, work)
    if props != case["historical_properties"]:
        raise RecoveryError("historical_properties_mismatch")
    selected, seconds = select(paths, props)
    index = case["source_frame"] - 1
    if (
        seconds != case["historical_selected_seconds"]
        or len(seconds) != 4
        or seconds[index] != case["seconds"]
    ):
        raise RecoveryError("historical_pts_mismatch")
    try:
        crops, sheet = cells(selected, seconds, case["row"], work)
    except ValueError:
        raise RecoveryError("historical_sheet_or_crop_mismatch") from None
    if digest(sheet) != case["sheet_sha256"] or digest(crops[index]) != case["png_sha256"]:
        raise RecoveryError("historical_sheet_or_crop_mismatch")
    picture = native(media, case["seconds"])
    if picture.mode != "RGB" or picture.size != (360, 640):
        raise RecoveryError("native_geometry_changed")
    destination = work / "native.png"
    if destination.exists() or destination.is_symlink():
        raise RecoveryError("native_destination_exists")
    # No native PNG exists before ALL old properties/PTS/pixels have passed.
    with destination.open("xb") as output:
        picture.save(output, format="PNG")
    return {
        "alias": case["alias"],
        "sheet_sha256": digest(sheet),
        "crop_sha256": digest(crops[index]),
        "properties_sha256": recovery.json_digest(props),
        "native_pts": case["seconds"],
        "native_size": [360, 640],
        "media_sha256": digest(media),
        "bridge_complete": True,
        "native_sha256": digest(destination),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-sha256", required=True)
    parser.add_argument("--alias", choices=["positive", "negative"], required=True)
    args = parser.parse_args()
    try:
        plan, checksum = recovery.load()
        run = recovery.ROOT / recovery.QUEUE / "run"
        intent = read_json(run / "intent.json")
        reservation = read_json(run / "receipts" / (args.alias + "-reserved.json"))
        network = read_json(run / "receipts" / (args.alias + "-network-result.json"))
        if (
            checksum != args.plan_sha256
            or intent["plan_sha256"] != checksum
            or reservation["plan_sha256"] != checksum
            or not network["cleanup_confirmed"]
            or network["code"] != "completed"
        ):
            raise RecoveryError("bridge_parent_binding_invalid")
        case = next(c for c in plan["configuration"]["cases"] if c["alias"] == args.alias)
        folder = run / "scratch" / (args.alias + "-download")
        found = [p for p in folder.glob("media.*") if p.suffix in {".mp4", ".webm", ".mkv"}]
        if len(found) != 1 or found[0].is_symlink():
            raise RecoveryError("bridge_media_identity_invalid")
        value = bridge(found[0], run / "scratch" / (args.alias + "-bridge"), case)
        print(json.dumps(value, allow_nan=False))
    except Exception as exc:  # noqa: BLE001 -- only finite static failure codes cross stdout
        known = {
            "historical_properties_mismatch",
            "historical_pts_mismatch",
            "historical_sheet_or_crop_mismatch",
            "native_geometry_changed",
            "exact_native_pts_missing",
            "native_pts_invalid",
        }
        code = (
            str(exc) if type(exc) is RecoveryError and str(exc) in known else "native_bridge_failed"
        )
        print(json.dumps({"error_code": code}))


if __name__ == "__main__":
    main()

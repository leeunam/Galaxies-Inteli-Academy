"""Recheck the same three pilot files; preserve original hypotheses and require human ASR reference."""

import argparse
import gc
import hashlib
import json
import time

from scripts.asr_quality import distance, normalize
from scripts.gguf_visual_attributes import extract_visual_attributes, model_manifest
from scripts.pilot_licensed_media import (
    MODELS,
    ROOT,
    frames_and_properties,
    prepare_models,
    select_vlm_samples,
)
from scripts.pilot_youtube_media import download_video, private_path, run_batch, validate_candidates


def extract_quality(media, scratch, models, original):
    import av
    from faster_whisper import WhisperModel
    from faster_whisper.audio import decode_audio

    properties, paths = frames_and_properties(media, scratch)
    selected_paths, selected_seconds = select_vlm_samples(paths, properties)
    print(
        json.dumps({"stage": "quality_frames_ready", "paths": [str(p) for p in selected_paths]}),
        flush=True,
    )
    started = time.perf_counter()
    with av.logging.Capture(local=True) as warnings:
        audio = decode_audio(str(media), sampling_rate=16000)
    duration = len(audio) / 16000
    audio_sha256 = hashlib.sha256(audio.tobytes()).hexdigest()
    model = WhisperModel(str(models["asr"]), device="cpu", compute_type="int8", cpu_threads=4)

    def serialize(segments):
        return [
            {
                "start": s.start,
                "end": s.end,
                "text": s.text.strip(),
                "avg_logprob": s.avg_logprob,
                "no_speech_prob": s.no_speech_prob,
                "compression_ratio": s.compression_ratio,
            }
            for s in segments
        ]

    baseline, _ = model.transcribe(audio, language="pt", beam_size=1, vad_filter=True)
    baseline_speech = serialize(baseline)
    baseline_text = " ".join(s["text"] for s in baseline_speech).strip()
    segments, info = model.transcribe(
        audio,
        language="pt",
        beam_size=5,
        temperature=0,
        condition_on_previous_text=False,
        vad_filter=False,
    )
    speech = serialize(segments)
    transcript = " ".join(s["text"] for s in speech).strip()
    del model, audio
    gc.collect()
    asr_seconds = time.perf_counter() - started
    started = time.perf_counter()
    vlm = extract_visual_attributes(selected_paths, selected_seconds, scratch)
    old, new = normalize(baseline_text), normalize(transcript)
    return {
        "schema_version": "pilot-quality-v4-qwen-gguf",
        "properties": properties,
        "audio_duration_seconds": duration,
        "decoded_audio_float32_16khz_sha256": audio_sha256,
        "audio_decode_warnings": [
            {"level": level, "decoder": decoder, "message": message.strip()}
            for level, decoder, message in warnings
            if level <= av.logging.WARNING
        ],
        "transcript": transcript,
        "speech_segments": speech,
        "replayed_baseline": {
            "transcript": baseline_text,
            "speech_segments": baseline_speech,
            "beam_size": 1,
            "vad_filter": True,
        },
        "original_snapshot_normalized_equal_to_replayed_baseline": normalize(original["transcript"])
        == old,
        "asr_parameters": {
            "model_revision": "same_pinned_small",
            "language_requested": "pt",
            "beam_size": 5,
            "temperature": 0,
            "condition_on_previous_text": False,
            "vad_filter": False,
            "language_returned": info.language,
        },
        "asr_comparison": {
            "normalized_equal": old == new,
            "word_edit_distance": distance(old.split(), new.split()),
            "interpretation": "configuration_disagreement_not_accuracy",
        },
        "asr_validation_status": "requires_comparison_to_reviewed_reference",
        "vlm": vlm,
        "approved_for_training": False,
        "timings_seconds": {"asr": asr_seconds, "vlm": time.perf_counter() - started},
    }


def main():
    from pathlib import Path

    import imageio_ffmpeg

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, required=True)
    parser.add_argument("--original-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--vlm-engine", choices=["qwen-gguf"], default="qwen-gguf")
    args = parser.parse_args()
    candidates = validate_candidates(json.loads(private_path(args.candidates).read_text()))
    original_root, output = private_path(args.original_root), private_path(args.output)
    if output.exists() and any(output.iterdir()):
        parser.error("Use a fresh output directory")
    originals = {
        r["audit"]["video_id"]: json.loads(
            (original_root / r["audit"]["video_id"] / "features.json").read_text()
        )
        for r in candidates
    }
    hashes = {
        r["audit"]["video_id"]: json.loads(
            (original_root / r["audit"]["video_id"] / "run.json").read_text()
        )["media_fingerprint"]["sha256"]
        for r in candidates
    }
    models = prepare_models(True)
    manifest = {"asr": {"repo": MODELS["asr"][0], "revision": MODELS["asr"][1]}}
    manifest["vlm"] = model_manifest()
    ffmpeg = Path(imageio_ffmpeg.get_ffmpeg_exe())
    current = {}

    def download(path, video_id):
        current["video_id"] = video_id
        result = download_video(path, video_id, ffmpeg)
        result["matches_original_pilot"] = result["sha256"] == hashes[video_id]
        result["original_file_sha256"] = hashes[video_id]
        result["comparison_scope"] = (
            "Both ASR configurations run on this same decoded audio; old container identity is not presumed"
        )
        return result

    result = run_batch(
        candidates,
        output,
        ROOT / "data/private/media-temp",
        lambda media, scratch: extract_quality(
            media, scratch, models, originals[current["video_id"]]
        ),
        download,
        model_manifest=manifest,
    )
    print(json.dumps({"completed": result["completed"], "failed": result["failed"]}), flush=True)


if __name__ == "__main__":
    main()

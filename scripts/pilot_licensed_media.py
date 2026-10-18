"""Experimental fixture pilot, not a YouTube downloader or a training-data importer.

The licensed Commons fixture is old and horizontal: NEVER add it to the Shorts
training sample. All audiovisual files live inside the disposable session.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import resource
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = {
    "media_url": "https://upload.wikimedia.org/wikipedia/commons/8/81/%22A_moda_faz_parte_da_vida_de_todo_mundo%22%2C_defende_a_modelo_Carol_Ribeiro.webm",
    "source_page": "https://commons.wikimedia.org/w/index.php?curid=103214103&oldid=1030751044",
    "youtube_reference": "https://www.youtube.com/watch?v=34w5_poZ2WM",
    "author": "tvbrasil",
    "license": "CC BY 3.0",
    "license_url": "https://creativecommons.org/licenses/by/3.0/",
    "sha1": "f14859b90f9c27c8356408a507242d2cf44202b8",
    "size_bytes": 25950197,
    "training_eligible": False,
    "exclusion_reason": "Technical fixture: 2017 publication, horizontal; outside target cohort.",
}
MODELS = {
    "asr": ("Systran/faster-whisper-small", "536b0662742c02347bc0e980a01041f333bce120"),
    "text": (
        "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "e8f8c211226b894fcb81acc59f3b34ba3efd5f42",
    ),
    "clip": ("openai/clip-vit-base-patch32", "3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268"),
    "vlm": (
        "HuggingFaceTB/SmolVLM2-500M-Video-Instruct",
        "7b375e1b73b11138ff12fe22c8f2822d8fe03467",
    ),
}


def validate_vlm_answer(answer: str) -> tuple[str, object]:
    """Reject malformed attributes; schema acceptance is not perception accuracy."""
    try:
        parsed = json.loads(answer)
    except json.JSONDecodeError:
        return "invalid_json", None
    boolean_keys = {
        "person_visible",
        "product_visible_early",
        "product_closeup",
        "demonstration",
        "screen_text",
    }
    expected = boolean_keys | {"scene", "format"}
    if not isinstance(parsed, dict) or set(parsed) != expected:
        return "invalid_schema", parsed
    for key, item in parsed.items():
        if not isinstance(item, dict) or set(item) != {"value", "frames"}:
            return "invalid_schema", parsed
        value, frames = item["value"], item["frames"]
        if not isinstance(frames, list) or any(
            type(i) is not int or not 1 <= i <= 4 for i in frames
        ):
            return "invalid_schema", parsed
        if key in boolean_keys and type(value) is not bool and value != "unknown":
            return "invalid_schema", parsed
        if key not in boolean_keys and (not isinstance(value, str) or not value.strip()):
            return "invalid_schema", parsed
        if value != "unknown" and not frames:
            return "missing_frame_evidence", parsed
        if key == "product_visible_early" and any(i > 3 for i in frames):
            return "invalid_early_frame_evidence", parsed
    return "schema_valid_requires_perception_review", parsed


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    staged = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", dir=path.parent, suffix=".tmp", delete=False
        ) as f:
            staged = Path(f.name)
            json.dump(value, f, ensure_ascii=False, indent=2, allow_nan=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(staged, path)
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)


def acquire_fixture(destination: Path) -> dict:
    request = urllib.request.Request(
        FIXTURE["media_url"], headers={"User-Agent": "Galaxies-Academic-Pilot/0.1"}
    )
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(request, timeout=30) as response, destination.open("xb") as f:
        if urllib.parse.urlparse(response.geturl()).hostname != "upload.wikimedia.org":
            raise ValueError("Unexpected fixture host")
        while chunk := response.read(1024 * 1024):
            size += len(chunk)
            if size > 32 * 1024 * 1024:
                raise ValueError("Fixture byte limit exceeded")
            sha1.update(chunk)
            sha256.update(chunk)
            f.write(chunk)
    if size != FIXTURE["size_bytes"] or sha1.hexdigest() != FIXTURE["sha1"]:
        raise ValueError("Fixture does not match the licensed snapshot")
    return {"size_bytes": size, "sha1": sha1.hexdigest(), "sha256": sha256.hexdigest()}


def prepare_models(include_vlm: bool) -> dict[str, Path]:
    from huggingface_hub import snapshot_download

    prepared = {}
    for name, (repo, revision) in MODELS.items():
        if name == "vlm" and not include_vlm:
            continue
        print(json.dumps({"stage": "prepare_model", "model": name}), flush=True)
        weight = "*.safetensors"
        if name == "asr":
            weight = "model.bin"
        elif name == "clip":
            weight = "pytorch_model.bin"
        prepared[name] = Path(
            snapshot_download(
                repo,
                revision=revision,
                allow_patterns=["*.json", "*.txt", "*.model", "*.jinja", weight],
            )
        )
    return prepared


def frames_and_properties(media: Path, work: Path) -> tuple[dict, list[Path]]:
    import av
    import numpy as np

    with av.open(str(media)) as container:
        stream = container.streams.video[0]
        duration = (
            float(stream.duration * stream.time_base)
            if stream.duration
            else container.duration / 1e6
        )
        if not 0 < duration <= 60:
            raise ValueError("Fixture duration is outside pilot limits")
        targets = sorted(
            {
                min(x, max(0, duration - 0.05))
                for x in [0.2, 1.5, 2.8, 0.3 * duration, 0.6 * duration, 0.9 * duration]
            }
        )
        paths, positions, brightness, saturation = [], [], [], []
        target_index = 0
        for frame in container.decode(stream):
            timestamp = float(frame.time or 0)
            if target_index >= len(targets):
                break
            if timestamp < targets[target_index]:
                continue
            picture = frame.to_image()
            picture.thumbnail((512, 512))
            path = work / f"frame_{target_index:02d}.jpg"
            picture.save(path)
            paths.append(path)
            positions.append(timestamp)
            brightness.append(float(np.asarray(picture.convert("L")).mean() / 255))
            saturation.append(float(np.asarray(picture.convert("HSV"))[:, :, 1].mean() / 255))
            target_index += 1
        if len(paths) != len(targets):
            raise ValueError("Could not decode all fixed sample frames")
        return {
            "duration_seconds": duration,
            "width": stream.width,
            "height": stream.height,
            "sampled_frame_seconds": positions,
            "brightness_mean_0_1": float(np.mean(brightness)),
            "saturation_mean_0_1": float(np.mean(saturation)),
        }, paths


def extract_features(media: Path, work: Path, models: dict[str, Path], include_vlm: bool) -> dict:
    import av
    import numpy as np
    import torch
    from faster_whisper import WhisperModel
    from faster_whisper.audio import decode_audio
    from PIL import Image
    from sentence_transformers import SentenceTransformer
    from transformers import CLIPModel, CLIPProcessor

    torch.set_num_threads(4)
    timings = {}
    t = time.perf_counter()
    properties, frame_paths = frames_and_properties(media, work)
    timings["frames"] = time.perf_counter() - t
    print(
        json.dumps(
            {"stage": "frames_ready", "count": len(frame_paths), "temporary_directory": str(work)}
        ),
        flush=True,
    )
    t = time.perf_counter()
    with av.logging.Capture(local=True) as decoder_messages:
        audio = decode_audio(str(media), sampling_rate=16000)
    audio_seconds = len(audio) / 16000
    decode_warnings = [
        {"level": level, "decoder": decoder, "message": message.strip()}
        for level, decoder, message in decoder_messages
        if level <= av.logging.WARNING
    ]
    rms = float(np.sqrt(np.mean(audio.astype(np.float64) ** 2)))
    model = WhisperModel(str(models["asr"]), device="cpu", compute_type="int8", cpu_threads=4)
    segments, info = model.transcribe(audio, language="pt", beam_size=1, vad_filter=True)
    speech = [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segments]
    transcript = " ".join(s["text"] for s in speech).strip()
    del model, audio
    gc.collect()
    timings["asr"] = time.perf_counter() - t
    print(json.dumps({"stage": "asr_complete", "segments": len(speech)}), flush=True)
    t = time.perf_counter()
    text_embedding = None
    if transcript:
        model = SentenceTransformer(str(models["text"]), device="cpu", local_files_only=True)
        model.max_seq_length = 128
        token_ids = model.tokenizer.encode(transcript, add_special_tokens=False, verbose=False)
        chunks = [
            model.tokenizer.decode(token_ids[i : i + 126]) for i in range(0, len(token_ids), 126)
        ]
        text_embedding = model.encode(chunks, convert_to_numpy=True).mean(axis=0).tolist()
        del model
    gc.collect()
    timings["text_embedding"] = time.perf_counter() - t
    t = time.perf_counter()
    # This official, revision-pinned CLIP repository provides a .bin checkpoint.
    # PyTorch's restricted weights-only loader is kept enabled.
    model = CLIPModel.from_pretrained(
        str(models["clip"]), local_files_only=True, use_safetensors=False, weights_only=True
    ).eval()
    processor = CLIPProcessor.from_pretrained(
        str(models["clip"]), local_files_only=True, use_fast=False
    )
    vectors = []
    for path in frame_paths:
        with Image.open(path) as im:
            batch = processor(images=im.convert("RGB"), return_tensors="pt")
        with torch.inference_mode():
            vectors.append(model.get_image_features(**batch).float().numpy()[0])
    image_embedding = np.stack(vectors).mean(axis=0).tolist()
    del model, processor, vectors
    gc.collect()
    timings["clip"] = time.perf_counter() - t
    result = {
        "properties": properties,
        "audio_rms": rms,
        "audio_duration_seconds": audio_seconds,
        "audio_decode_warnings": decode_warnings,
        "transcript": transcript,
        "speech_segments": speech,
        "asr_language": info.language,
        "text_embedding": text_embedding,
        "text_features_status": "extracted" if transcript else "no_speech_detected",
        "image_embedding": image_embedding,
        "timings_seconds": timings,
        "vlm": {"status": "not_requested"},
    }
    if include_vlm:
        from transformers import AutoModelForImageTextToText, AutoProcessor

        t = time.perf_counter()
        processor = AutoProcessor.from_pretrained(str(models["vlm"]), local_files_only=True)
        if hasattr(processor, "image_processor"):
            processor.image_processor.do_image_splitting = False
            processor.image_processor.size = {"longest_edge": 512}
        model = AutoModelForImageTextToText.from_pretrained(
            str(models["vlm"]),
            local_files_only=True,
            torch_dtype=torch.float32,
            use_safetensors=True,
            attn_implementation="eager",
        ).eval()
        # Fixed early samples plus 60%: nearest decoded frames, no full video upload.
        if len(frame_paths) < 5:
            raise ValueError("Insufficient sample frames for the fixed VLM pilot")
        indices = [0, 1, 2, 4]
        prompt = (
            "Inspect only these four chronological frames. Return JSON with keys "
            "person_visible, product_visible_early, product_closeup, demonstration, "
            "screen_text, scene, format. For each key use "
            '{"value": ..., "frames": [1-based frame numbers]}. Use "unknown" '
            "when not observable. Do not infer speech, emotion, ethnicity, performance or views."
        )
        images = []
        for index in indices:
            with Image.open(frame_paths[index]) as im:
                images.append(im.convert("RGB").copy())
        messages = [
            {
                "role": "user",
                "content": [{"type": "image"} for _ in images] + [{"type": "text", "text": prompt}],
            }
        ]
        text = processor.apply_chat_template(messages, add_generation_prompt=True)
        inputs = processor(text=text, images=images, return_tensors="pt")
        if max(inputs["pixel_values"].shape[-2:]) > 512:
            raise ValueError("Processor expanded images beyond the pilot pixel budget")
        with torch.inference_mode():
            generated = model.generate(**inputs, max_new_tokens=192, do_sample=False)
        answer = processor.batch_decode(
            generated[:, inputs["input_ids"].shape[1] :], skip_special_tokens=True
        )[0]
        status, parsed = validate_vlm_answer(answer)
        result["vlm"] = {
            "status": status,
            "raw_response": answer,
            "parsed": parsed,
            "input_frame_seconds": [properties["sampled_frame_seconds"][i] for i in indices],
        }
        timings["vlm"] = time.perf_counter() - t
        del model, processor, images, inputs, generated
        gc.collect()
    if (text_embedding is not None and len(text_embedding) != 384) or len(image_embedding) != 512:
        raise ValueError("Unexpected embedding dimension")
    return result


def run_session(
    output: Path, scratch_root: Path, extractor, downloader=acquire_fixture, source=None
) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    scratch_root.mkdir(parents=True, exist_ok=True)
    state = {
        "status": "started",
        "source": FIXTURE if source is None else source,
        "training_eligible": False,
        "models": {k: {"repo": v[0], "revision": v[1]} for k, v in MODELS.items()},
        "memory_measurement": "cumulative_parent_process_peak_excludes_downloader_children",
    }
    scratch = None
    started = time.perf_counter()
    try:
        with tempfile.TemporaryDirectory(prefix="galaxies-media-", dir=scratch_root) as folder:
            scratch = Path(folder)
            media = scratch / "input.media"
            state["media_fingerprint"] = downloader(media)
            features = extractor(media, scratch)
            atomic_json(output / "features.json", features)
        state["status"] = "completed"
    except BaseException as exc:
        state["status"] = "failed"
        state["error_type"] = type(exc).__name__
        raise
    finally:
        state["temporary_directory_removed"] = scratch is not None and not scratch.exists()
        state["total_seconds"] = time.perf_counter() - started
        state["process_peak_rss_mib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        atomic_json(output / "run.json", state)
    return state


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--with-vlm", action="store_true")
    args = parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Use a fresh output directory to preserve previous evidence")
    models = prepare_models(args.with_vlm)
    result = run_session(
        args.output,
        ROOT / "data/private/media-temp",
        lambda media, folder: extract_features(media, folder, models, args.with_vlm),
    )
    print(
        json.dumps(
            {
                k: result[k]
                for k in [
                    "status",
                    "temporary_directory_removed",
                    "total_seconds",
                    "process_peak_rss_mib",
                ]
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()

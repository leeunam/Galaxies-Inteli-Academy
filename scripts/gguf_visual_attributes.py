"""Local, pinned Qwen GGUF adapter with bounded CPU/RAM and independent validation."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import threading
import time
from pathlib import Path

from scripts.visual_attributes import FORMATS, SCENES, validate_vlm_answer

ROOT = Path(__file__).resolve().parents[1]
REVISION = "52d6c8ffea26cc873ac5ad116f8631268d7eb503"
MODEL_DIR = (
    ROOT / "data/cache/huggingface/hub/models--Qwen--Qwen3-VL-2B-Instruct-GGUF/snapshots" / REVISION
)
RUNTIME = ROOT / "data/cache/llama-cpp/b11716/llama-b11716/llama-mtmd-cli"
MODEL_FILE = "Qwen3VL-2B-Instruct-Q4_K_M.gguf"
PROJECTOR_FILE = "mmproj-Qwen3VL-2B-Instruct-Q8_0.gguf"
HASHES = {
    MODEL_FILE: "089d75c52f4b7ffc56ba998ffc50aae89fcafc755f9e7208aacca281dca6c2ae",
    PROJECTOR_FILE: "f9a68fabba69c3b81e153367b2c7521030b0fa8bb0de400c9599c8e6725f9c82",
}
QUALITY_POLICY = "visual-quality-gate-v1"
WITHHELD_ATTRIBUTES = {
    "product_closeup": "Ambiguous framing rubric in the pilot; not validated for training",
    "demonstration": "False positive for holding a cosmetic; application perception not validated",
}


def apply_quality_policy(model_parsed):
    """Withhold failed attributes for every video, without changing the raw model answer."""
    parsed = json.loads(json.dumps(model_parsed))
    for key, item in parsed.items():
        if key in WITHHELD_ATTRIBUTES or item["value"] == "unknown":
            parsed[key] = {"value": "unknown", "frames": []}
    return parsed


def model_manifest():
    return {
        "repo": "Qwen/Qwen3-VL-2B-Instruct-GGUF",
        "revision": REVISION,
        "files_sha256": HASHES,
        "runtime": "llama.cpp b11716 (797de63b2), Linux x64 CPU",
        "llm_quantization": "Q4_K_M",
        "vision_quantization": "Q8_0",
        "image_max_tokens": 128,
    }


def attribute_schema(frame_seconds):
    booleans = {
        "person_visible",
        "product_visible_early",
        "product_closeup",
        "demonstration",
        "screen_text",
    }
    properties = {}
    for key in [
        "person_visible",
        "product_visible_early",
        "product_closeup",
        "demonstration",
        "screen_text",
        "scene",
        "format",
    ]:
        options = (
            [True, False, "unknown"]
            if key in booleans
            else list(SCENES if key == "scene" else FORMATS)
        )
        allowed_frames = [
            i
            for i, seconds in enumerate(frame_seconds, 1)
            if key != "product_visible_early" or seconds <= 3
        ]
        if not allowed_frames:
            options = ["unknown"]
        properties[key] = {
            "type": "object",
            "properties": {
                "value": {"enum": options},
                "frames": {
                    "type": "array",
                    "items": {"enum": allowed_frames} if allowed_frames else {"type": "integer"},
                    "maxItems": len(allowed_frames),
                },
            },
            "required": ["value", "frames"],
            "additionalProperties": False,
        }
    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


def extract_json_output(text: str, frame_seconds) -> tuple[dict, str]:
    decoder = json.JSONDecoder()
    for offset, character in enumerate(text):
        if character != "{":
            continue
        try:
            parsed, _ = decoder.raw_decode(text[offset:])
        except json.JSONDecodeError:
            continue
        status, _ = validate_vlm_answer(json.dumps(parsed), frame_seconds)
        if status == "schema_valid_requires_perception_review":
            return parsed, status
    raise ValueError("No complete valid attribute object in model output")


def invoke_local_vlm(frame_paths, prompt, work, schema=None, max_tokens=320):
    import psutil

    if not 1 <= len(frame_paths) <= 4:
        raise ValueError("Local pilot accepts one to four frames")
    if not all(p.is_file() for p in [RUNTIME, MODEL_DIR / MODEL_FILE, MODEL_DIR / PROJECTOR_FILE]):
        raise ValueError("Prepare the pinned local GGUF runtime and weights first")
    command = [
        str(RUNTIME),
        "-m",
        str(MODEL_DIR / MODEL_FILE),
        "--mmproj",
        str(MODEL_DIR / PROJECTOR_FILE),
        "--n-gpu-layers",
        "0",
        "--no-mmproj-offload",
        "--ctx-size",
        "3072",
        "--n-predict",
        str(max_tokens),
        "--threads",
        "4",
        "--threads-batch",
        "4",
        "--batch-size",
        "128",
        "--ubatch-size",
        "128",
        "--image-min-tokens",
        "64",
        "--image-max-tokens",
        "128",
        "--temp",
        "0",
        "--seed",
        "42",
        "--verbosity",
        "0",
        "--log-colors",
        "off",
        "--no-log-prefix",
        "--no-log-timestamps",
        "--image",
        ",".join(str(p) for p in frame_paths),
        "--prompt",
        prompt,
    ]
    if schema is not None:
        schema_path = work / "vlm-schema.json"
        schema_path.write_text(json.dumps(schema))
        command += ["--json-schema-file", str(schema_path)]
    started = time.perf_counter()
    process = subprocess.Popen(
        command,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    stop = threading.Event()
    measurements = {"peak_rss_mib": 0.0, "memory_limit_exceeded": False}

    def monitor():
        try:
            child = psutil.Process(process.pid)
        except psutil.NoSuchProcess:
            return
        while not stop.wait(0.1):
            try:
                rss = child.memory_info().rss / 1024**2
                measurements["peak_rss_mib"] = max(measurements["peak_rss_mib"], rss)
                if rss > 3.3 * 1024:
                    measurements["memory_limit_exceeded"] = True
                    os.killpg(process.pid, signal.SIGKILL)
                    return
            except (psutil.NoSuchProcess, ProcessLookupError):
                return

    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    try:
        stdout, stderr = process.communicate(timeout=180)
    except BaseException:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
        process.communicate()
        raise
    finally:
        stop.set()
        thread.join(timeout=2)
    if measurements["memory_limit_exceeded"]:
        raise RuntimeError("local_vlm_memory_limit_exceeded")
    if process.returncode:
        raise RuntimeError("local_vlm_runtime_failed")
    return {
        "raw_response": (stdout + "\n" + stderr).strip(),
        "runtime_seconds": time.perf_counter() - started,
        "runtime_peak_rss_mib": measurements["peak_rss_mib"],
        "rss_sampling_interval_seconds": 0.1,
    }


def extract_visual_attributes(frame_paths, frame_seconds, work):
    timeline = "; ".join(
        f"frame {i} = {seconds:.3f} seconds" for i, seconds in enumerate(frame_seconds, 1)
    )
    prompt = (
        "Inspect only these chronological video samples: " + timeline + ". "
        "Return the JSON object specified by the schema. Each value must cite the 1-based frames "
        "where it is visible. Use unknown and an empty frames array when uncertain. "
        "person_visible: visible human face or body; garments without a wearer are not people. "
        "product_visible_early: a displayed cosmetic, applicator, garment or fashion accessory in "
        "samples at or before 3 seconds. Incidental clothing worn by a speaker alone does not count. "
        "product_closeup: a product shown close enough to inspect its detail; a face alone is insufficient. "
        "demonstration: visible application or use, such as a brush touching skin; holding a package alone "
        "is not application. screen_text: presence of text, not OCR transcription. "
        "scene: indoor, outdoor, graphic, mixed or unknown. "
        "format: reaction for a split-screen reacting presenter; application for visible use; "
        "product_showcase for displayed items; talking_head for a presenter; mixed, other or unknown. "
        "When reaction and application coexist, use reaction. Do not infer audio, views, emotion or intent."
    )
    output = invoke_local_vlm(frame_paths, prompt, work, attribute_schema(frame_seconds))
    parsed, status = extract_json_output(output["raw_response"], frame_seconds)
    return {
        "schema_version": "visual-attributes-v5-qwen-gguf-cpu128",
        "status": status,
        "model_parsed": parsed,
        "parsed": apply_quality_policy(parsed),
        "quality_policy": QUALITY_POLICY,
        "withheld_attributes": WITHHELD_ATTRIBUTES,
        "input_frame_seconds": frame_seconds,
        "model": model_manifest(),
        "approved_for_training": False,
        "evidence_scope": "sampled still frames; valid schema requires perception review",
        **output,
    }

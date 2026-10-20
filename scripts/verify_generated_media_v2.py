"""Explicit offline integration probe: generated media, real production extraction.

No feature fixture, model training, download, VLM, provider or holdout access.
Uses an already installed eSpeak NG shared library for synthetic Portuguese
speech, and the existing bundled FFmpeg. Never plays audio on a device.
"""

from __future__ import annotations

import argparse
import asyncio
import ctypes
import ctypes.util
import hashlib
import json
import os
import subprocess
import sys
import time
import wave
from pathlib import Path
from tempfile import TemporaryDirectory

import imageio_ffmpeg
from fastmcp import Client
from fastmcp.client.transports import StdioTransport

from scripts.creative_analysis import analyze_creatives
from scripts.creative_registry import CreativeRegistry
from scripts.explanation_graph_service_v2 import ROOT, GraphSettings, analyze_via_graph
from scripts.m1_handoff_v2 import M1_A200_SHA256
from scripts.m1_service import M1Settings

SYNTHETIC_SPEECH = (
    "Este vídeo foi criado apenas para verificar um programa de computador. "
    "Estamos usando uma cena simples e uma voz gerada nesta máquina. "
    "Não há nenhuma campanha real. O objetivo é conferir a transcrição em português "
    "e a limpeza dos arquivos temporários."
)


def synthesize_local_speech(destination):
    library = ctypes.util.find_library("espeak-ng")
    if library is None:
        raise RuntimeError("local_speech_library_unavailable")
    engine = ctypes.CDLL(library)
    engine.espeak_Initialize.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
    engine.espeak_Initialize.restype = ctypes.c_int
    engine.espeak_SetVoiceByName.argtypes = [ctypes.c_char_p]
    engine.espeak_SetVoiceByName.restype = ctypes.c_int
    engine.espeak_Synth.argtypes = [
        ctypes.c_void_p,
        ctypes.c_size_t,
        ctypes.c_uint,
        ctypes.c_int,
        ctypes.c_uint,
        ctypes.c_uint,
        ctypes.POINTER(ctypes.c_uint),
        ctypes.c_void_p,
    ]
    engine.espeak_Synth.restype = ctypes.c_int
    chunks = []
    callback_type = ctypes.CFUNCTYPE(
        ctypes.c_int, ctypes.POINTER(ctypes.c_short), ctypes.c_int, ctypes.c_void_p
    )

    @callback_type
    def receive(samples, count, events):
        if samples and count > 0:
            chunks.append(ctypes.string_at(samples, count * ctypes.sizeof(ctypes.c_short)))
        return 0

    engine.espeak_SetSynthCallback.argtypes = [callback_type]
    # Synchronous PCM callback output (2), no audio output device.
    rate = engine.espeak_Initialize(2, 0, None, 0)
    if not 8000 <= rate <= 48000:
        raise RuntimeError("local_speech_initialization_failed")
    try:
        engine.espeak_SetSynthCallback(receive)
        if engine.espeak_SetVoiceByName(b"pt-br") != 0:
            raise RuntimeError("local_portuguese_voice_unavailable")
        text = ctypes.create_string_buffer(SYNTHETIC_SPEECH.encode("utf-8"))
        uid = ctypes.c_uint()
        # UTF-8 text, character position, and end pause.
        if engine.espeak_Synth(text, len(text), 0, 1, 0, 0x1001, ctypes.byref(uid), None) != 0:
            raise RuntimeError("local_speech_synthesis_failed")
        engine.espeak_Synchronize()
    finally:
        engine.espeak_Terminate()
    raw = b"".join(chunks)
    duration = len(raw) / (2 * rate)
    if not 2 <= duration < 55:
        raise RuntimeError("generated_speech_duration_invalid")
    with wave.open(str(destination), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(rate)
        output.writeframes(raw)
    return duration


def generate_cases(folder):
    speech = folder / "generated-pt.wav"
    duration = synthesize_local_speech(speech)
    silence = folder / "generated-silence.wav"
    with wave.open(str(silence), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16000)
        output.writeframes(bytes(32000))
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cases = (
        ("no-audio", "black", 1.0, None),
        ("silence", "gray", 1.0, silence),
        ("synthetic-pt-speech", "blue", duration, speech),
    )
    for name, color, seconds, audio in cases:
        destination = folder / "uploads" / f"{name}.mp4"
        destination.parent.mkdir(exist_ok=True)
        args = [
            ffmpeg,
            "-nostdin",
            "-hide_banner",
            "-loglevel",
            "error",
            "-n",
            "-f",
            "lavfi",
            "-i",
            f"color=c={color}:s=96x160:r=10",
        ]
        if audio is not None:
            args += ["-i", str(audio), "-c:a", "aac", "-shortest"]
        else:
            args += ["-an"]
        args += [
            "-t",
            str(seconds),
            "-c:v",
            "mpeg4",
            "-q:v",
            "5",
            "-pix_fmt",
            "yuv420p",
            "-map_metadata",
            "-1",
            str(destination),
        ]
        subprocess.run(
            args,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
            timeout=60,
            env={"PATH": os.defpath, "OMP_NUM_THREADS": "2"},
        )
    return [name for name, _, _, _ in cases]


def emit(stage):
    print(json.dumps({"stage": stage, "media_kind": "locally_generated_synthetic"}), flush=True)


async def verify_native_cancellation(payload, settings):
    """Observe the real extractor in our leased group, then cancel and reap it."""
    task = asyncio.create_task(analyze_via_graph(payload, settings))
    observed = None
    deadline = time.monotonic() + 30
    try:
        while time.monotonic() < deadline and not task.done():
            for run in settings.scratch_root.iterdir():
                lease_file = run / "process-lease.json"
                if not lease_file.exists():
                    continue
                lease = json.loads(lease_file.read_bytes())
                for process in Path("/proc").iterdir():
                    if not process.name.isdigit():
                        continue
                    try:
                        fields = (process / "stat").read_text().rsplit(")", 1)[1].split()
                        if int(fields[2]) != lease["pgid"]:
                            continue
                        command = (process / "cmdline").read_bytes().split(b"\0")
                        if b"scripts.candidate_features" in command:
                            observed = (int(process.name), lease["pgid"])
                            break
                    except (FileNotFoundError, ProcessLookupError, PermissionError):
                        continue
                if observed:
                    break
            if observed:
                break
            await asyncio.sleep(0.02)
        if not observed:
            raise RuntimeError("native_extractor_not_observed_for_cancellation")
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        else:
            raise RuntimeError("native_cancellation_not_propagated")
        if list(settings.scratch_root.iterdir()):
            raise RuntimeError("native_cancellation_scratch_remaining")
        try:
            os.kill(observed[0], 0)
        except ProcessLookupError:
            pass
        else:
            raise RuntimeError("native_extractor_not_reaped")
        try:
            os.killpg(observed[1], 0)
        except ProcessLookupError:
            pass
        else:
            raise RuntimeError("native_group_not_reaped")
        return {
            "real_extractor_observed": True,
            "cancelled": True,
            "group_reaped": True,
            "scratch_cleaned": True,
        }
    finally:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


async def verify(args):
    args.output_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    with TemporaryDirectory(prefix="generated-native-", dir=args.output_dir) as name:
        folder = Path(name)
        cases = generate_cases(folder)
        registry = CreativeRegistry(folder / "uploads", folder / "registry.json")
        ids = []
        for case in cases:
            registered = registry.register(
                {
                    "campaign_id": "generated-native-integration",
                    "sector": "moda",
                    "relative_path": case + ".mp4",
                }
            )
            if registered["status"] != "registered":
                raise RuntimeError("generated_media_registration_failed")
            ids.append(registered["creative_id"])
        payload = {
            "campaign_id": "generated-native-integration",
            "creative_ids": ids,
            "sector": "moda",
            "objective": "divulgacao",
            "brief": "Somente prova sintética local",
        }
        m1 = M1Settings(args.model_dir, args.cohort_dir, folder / "original-scratch")
        settings = GraphSettings(
            args.graph_python,
            Path(sys.executable),
            registry.uploads_root,
            registry.registry_file,
            folder / "supervised-scratch",
            m1=m1,
            evidence_root=args.evidence_root,
            minimum_similarity=0.5,
        )
        emit("original_production_analysis")
        started = time.monotonic()
        original = analyze_creatives(payload, registry, m1=m1)
        original_seconds = time.monotonic() - started
        (args.output_dir / "original-checkpoint.json").write_text(json.dumps(original, indent=2))
        if original.get("model_artifact_sha256") != M1_A200_SHA256:
            raise RuntimeError("native_model_unavailable")
        if any(
            c["extraction"]["status"] != "completed"
            and c["prediction"].get("reason_code")
            not in ("unsupported_language", "language_inconclusive")
            for c in original["candidates"]
        ):
            raise RuntimeError("native_extraction_incomplete")
        emit("python_production_stategraph")
        direct = await analyze_via_graph(payload, settings)
        (args.output_dir / "graph-checkpoint.json").write_text(json.dumps(direct, indent=2))
        if direct.get("analysis") != original:
            raise RuntimeError("python_numeric_parity_failed")
        emit("mcp_stdio_production_stategraph")
        transport = StdioTransport(
            command=sys.executable,
            args=[
                "-B",
                "-m",
                "scripts.explanation_graph_mcp_v2",
                "--graph-python",
                str(args.graph_python),
                "--uploads-root",
                str(registry.uploads_root),
                "--registry",
                str(registry.registry_file),
                "--scratch-root",
                str(settings.scratch_root),
                "--m1-model-dir",
                str(args.model_dir),
                "--m1-cohort-dir",
                str(args.cohort_dir),
                "--evidence-root",
                str(args.evidence_root),
                "--minimum-similarity",
                "0.5",
            ],
            cwd=str(ROOT),
            env={"PYTHONDONTWRITEBYTECODE": "1"},
            keep_alive=False,
            log_file=args.output_dir / "mcp-stderr.txt",
        )
        async with Client(transport) as client:
            reply = await client.call_tool(
                "analyze_creatives_with_explanation", {"payload": payload}
            )
            if reply.is_error or reply.structured_content != direct:
                raise RuntimeError("mcp_parity_failed")
        ready = sum(c["prediction"]["status"] == "estimated" for c in original["candidates"])
        facts = direct["evidence_packet"]["evidence"] if direct["evidence_packet"] else []
        shap_facts = sum("_shap_" in row["evidence_id"] for row in facts)
        if ready and (
            shap_facts != 4 * ready
            or direct["explanation"]["reason_code"] != "transport_not_configured"
        ):
            raise RuntimeError("native_evidence_missing")
        if not ready and direct["explanation"]["reason_code"] != "learned_prediction_unavailable":
            raise RuntimeError("unavailable_prediction_status_mismatch")
        if list(m1.scratch_root.iterdir()) or list(settings.scratch_root.iterdir()):
            raise RuntimeError("native_scratch_not_cleaned")
        emit("production_extractor_cancellation")
        cancellation = await verify_native_cancellation(payload, settings)
        summary = {
            "media_kind": "locally_generated_synthetic",
            "feature_extraction": "real_production",
            "feature_fixtures_used": False,
            "cases": [
                {
                    "case": case,
                    "media_sha256": hashlib.sha256(
                        (registry.uploads_root / (case + ".mp4")).read_bytes()
                    ).hexdigest(),
                    "text_status": candidate["extraction"]["text_status"],
                    "prediction_status": candidate["prediction"]["status"],
                    "reason_code": candidate["prediction"].get("reason_code"),
                }
                for case, candidate in zip(cases, original["candidates"], strict=True)
            ],
            "native_model": "M1/A200",
            "python_numeric_equal_original": True,
            "mcp_equal_python": True,
            "stategraph_executed": True,
            "native_shap_facts": shap_facts,
            "train_index_queried_candidates": ready,
            "comparable_matches": sum("_reference_" in row["evidence_id"] for row in facts),
            "queries_without_matches": sum(
                "_references_missing" in row["evidence_id"] for row in facts
            ),
            "original_seconds": original_seconds,
            "provider_calls": 0,
            "vlm_calls": 0,
            "downloads": 0,
            "holdout_opened": False,
            "synthetic_speech_sha256": hashlib.sha256(SYNTHETIC_SPEECH.encode()).hexdigest(),
            "real_media_demo": False,
            "adherence_status": "not_evaluated",
            "scratch_cleaned": True,
            "native_cancellation": cancellation,
        }
        (args.output_dir / "generated-native-result.json").write_text(
            json.dumps(
                {"summary": summary, "original_analysis": original, "integrated_result": direct},
                indent=2,
            )
        )
    emit("generated_media_removed")
    print(json.dumps(summary), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for item in ("model-dir", "cohort-dir", "evidence-root", "graph-python", "output-dir"):
        parser.add_argument("--" + item, type=Path, required=True)
    asyncio.run(verify(parser.parse_args()))

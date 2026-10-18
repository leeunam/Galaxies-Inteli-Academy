"""Silent, unforced ASR evidence for curation; never a human/dialect certification."""

from __future__ import annotations

import math
from pathlib import Path


def language_status(language: str, probability: float, segments: list[dict]) -> str:
    """Conservative triage fixed before the batch; probabilities aren't calibrated.

    Portuguese still needs review for Brazilian usage. Empty/short/low-confidence
    output cannot establish either a language or an absence of speech.
    """
    if not math.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError("Invalid language probability")
    usable = [
        s
        for s in segments
        if s["text"].strip()
        and s["end"] > s["start"] >= 0
        and s["avg_logprob"] >= -1
        and s["no_speech_prob"] < 0.6
    ]
    words = sum(len(s["text"].split()) for s in usable)
    seconds = sum(s["end"] - s["start"] for s in usable)
    if probability < 0.85 or words < 5 or seconds < 2:
        return "inconclusive"
    return "portuguese_detected_review_locale" if language == "pt" else "other_language_detected"


def audit_audio(media: Path, model) -> dict:
    """Decode locally without an audio output device; model loaded by the caller."""
    from faster_whisper.audio import decode_audio

    audio = decode_audio(str(media), sampling_rate=16000)
    segments, info = model.transcribe(
        audio,
        language=None,
        beam_size=1,
        vad_filter=True,
        condition_on_previous_text=False,
        temperature=0,
        language_detection_segments=3,
        language_detection_threshold=0.95,
    )
    speech = [
        {
            "start": s.start,
            "end": s.end,
            "text": s.text.strip(),
            "avg_logprob": s.avg_logprob,
            "no_speech_prob": s.no_speech_prob,
        }
        for s in segments
    ]
    return {
        "schema_version": "language-audit-v1",
        "method": "local_unforced_asr_with_vad",
        "forced_language": None,
        "human_listening": False,
        "dialect_certified": False,
        "language": info.language,
        "language_probability": info.language_probability,
        "language_probabilities": info.all_language_probs,
        "audio_seconds": len(audio) / 16000,
        "vad_seconds": info.duration_after_vad,
        "segments": speech,
        "transcript": " ".join(s["text"] for s in speech),
        "triage_status": language_status(info.language, info.language_probability, speech),
    }

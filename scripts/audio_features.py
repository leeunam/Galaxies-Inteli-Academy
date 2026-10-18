"""Shared reference/candidate ASR policy; missing audio is not confirmed silence."""

from pathlib import Path


def extract_audio(media: Path, model, *, has_audio: bool) -> dict:
    import hashlib

    import numpy as np
    from faster_whisper.audio import decode_audio

    base = {
        "audio_status": "no_audio_stream",
        "audio_rms": None,
        "audio_duration_seconds": 0.0,
        "decoded_audio_float32_16khz_sha256": None,
        "asr_language": None,
        "asr_language_probability": None,
        "transcript": "",
        "speech_segments": [],
    }
    if not has_audio:
        return base
    audio = decode_audio(str(media), sampling_rate=16000)
    if len(audio) == 0 or not np.isfinite(audio).all():
        raise ValueError("Invalid decoded audio")
    segments, info = model.transcribe(
        audio,
        language=None,
        beam_size=1,
        vad_filter=True,
        temperature=0,
        condition_on_previous_text=False,
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
    transcript = " ".join(s["text"] for s in speech).strip()
    return base | {
        "audio_status": "transcribed" if transcript else "no_speech_detected_by_asr",
        "audio_rms": float(np.sqrt(np.mean(audio.astype(np.float64) ** 2))),
        "audio_duration_seconds": len(audio) / 16000,
        "decoded_audio_float32_16khz_sha256": hashlib.sha256(audio.tobytes()).hexdigest(),
        "asr_language": info.language,
        "asr_language_probability": info.language_probability,
        "transcript": transcript,
        "speech_segments": speech,
    }

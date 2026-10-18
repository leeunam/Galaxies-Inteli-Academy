from types import SimpleNamespace

import numpy as np
import pytest

from scripts.audio_features import extract_audio


def test_missing_audio_never_invokes_asr_or_fills_text_from_metadata(tmp_path):
    result = extract_audio(tmp_path / "missing", None, has_audio=False)
    assert result["audio_status"] == "no_audio_stream"
    assert result["transcript"] == ""
    assert result["asr_language"] is None
    assert result["audio_rms"] is None


@pytest.mark.parametrize("speech", [True, False])
def test_same_unforced_policy_and_pcm_hash_for_references_and_candidates(
    monkeypatch, tmp_path, speech
):
    import faster_whisper.audio

    audio = np.zeros(32000, dtype=np.float32)
    monkeypatch.setattr(faster_whisper.audio, "decode_audio", lambda *a, **kw: audio)

    class Model:
        def transcribe(self, data, **options):
            assert options["language"] is None
            assert options["temperature"] == 0
            assert options["vad_filter"] is True
            assert options["condition_on_previous_text"] is False
            segments = (
                [
                    SimpleNamespace(
                        start=0.0, end=1.0, text=" fala real ", avg_logprob=-0.2, no_speech_prob=0.1
                    )
                ]
                if speech
                else []
            )
            return iter(segments), SimpleNamespace(language="pt", language_probability=0.99)

    first = extract_audio(tmp_path / "reference.mp4", Model(), has_audio=True)
    second = extract_audio(tmp_path / "unpublished.mp4", Model(), has_audio=True)
    assert first == second
    assert len(first["decoded_audio_float32_16khz_sha256"]) == 64
    assert first["audio_status"] == ("transcribed" if speech else "no_speech_detected_by_asr")
    assert first["transcript"] == ("fala real" if speech else "")


@pytest.mark.parametrize(
    "audio", [np.array([], dtype=np.float32), np.array([np.nan], dtype=np.float32)]
)
def test_invalid_audio_is_failure_not_confirmed_silence(monkeypatch, tmp_path, audio):
    import faster_whisper.audio

    monkeypatch.setattr(faster_whisper.audio, "decode_audio", lambda *a, **kw: audio)
    with pytest.raises(ValueError, match="Invalid decoded audio"):
        extract_audio(tmp_path / "invalid.mp4", None, has_audio=True)

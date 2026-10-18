from types import SimpleNamespace

import pytest

from scripts.language_audit import audit_audio, language_status


def speech(text="Este produto deixa o cabelo bem bonito"):
    return [{"text": text, "start": 0, "end": 4, "avg_logprob": -0.2, "no_speech_prob": 0.1}]


def test_portuguese_is_not_dialect_confirmation():
    assert language_status("pt", 0.99, speech()) == "portuguese_detected_review_locale"


def test_english_is_not_mapped_to_portuguese():
    assert (
        language_status("en", 0.99, speech("These clothes look very nice on you"))
        == "other_language_detected"
    )


@pytest.mark.parametrize(
    "probability,segments", [(0.84, speech()), (0.99, []), (0.99, speech("Olá"))]
)
def test_insufficient_evidence_is_unknown(probability, segments):
    assert language_status("pt", probability, segments) == "inconclusive"


def test_hallucination_like_segments_do_not_confirm_language():
    row = speech()[0]
    assert language_status("pt", 0.99, [{**row, "no_speech_prob": 0.9}]) == "inconclusive"
    assert language_status("pt", 0.99, [{**row, "avg_logprob": -2}]) == "inconclusive"


@pytest.mark.parametrize("probability", [float("nan"), float("inf"), -1, 2])
def test_invalid_probability_rejected(probability):
    with pytest.raises(ValueError):
        language_status("pt", probability, speech())


def test_audit_runs_unforced_and_never_claims_human_or_dialect_confirmation(monkeypatch, tmp_path):
    import faster_whisper.audio

    monkeypatch.setattr(faster_whisper.audio, "decode_audio", lambda *args, **kwargs: [0.0] * 64000)

    class Model:
        def transcribe(self, audio, **options):
            assert options["language"] is None
            assert options["vad_filter"] is True
            return iter([SimpleNamespace(**speech()[0])]), SimpleNamespace(
                language="pt",
                language_probability=0.99,
                all_language_probs=[("pt", 0.99)],
                duration_after_vad=4.0,
            )

    result = audit_audio(tmp_path / "not_played.mp4", Model())
    assert result["forced_language"] is None
    assert not result["human_listening"]
    assert not result["dialect_certified"]
    assert result["triage_status"] == "portuguese_detected_review_locale"

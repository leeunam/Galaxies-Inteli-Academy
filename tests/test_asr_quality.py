import pytest

from scripts.asr_quality import evaluate_references, normalize, transcript_errors


def test_asr_metrics_preserve_lexical_errors_and_handle_empty_reference():
    assert normalize("Olá, TÁ!") == "olá tá"
    errors = transcript_errors("Eu gosto de maquiagem", "Eu gosto maquiagem")
    assert errors["wer"] == 0.25
    assert transcript_errors("tá", "está")["wer"] == 1
    assert transcript_errors("", "inventado")["wer"] is None
    assert not transcript_errors("", "inventado")["empty_reference_match"]


def test_no_accuracy_without_listened_reference_and_aggregate_by_word_count():
    with pytest.raises(ValueError):
        evaluate_references([], {})
    hypotheses = {
        "a": {"transcript": "a", "replayed_baseline": {"transcript": "a"}},
        "b": {"transcript": "a b c", "replayed_baseline": {"transcript": "a b c"}},
    }
    refs = [
        {
            "video_id": "a",
            "text": "b",
            "audio_type": "speech",
            "reviewer": "test",
            "listened": False,
        }
    ]
    with pytest.raises(ValueError):
        evaluate_references(refs, hypotheses)
    refs[0]["listened"] = True
    refs.append(
        {
            "video_id": "b",
            "text": "a b c",
            "audio_type": "speech",
            "reviewer": "test",
            "listened": True,
        }
    )
    result = evaluate_references(refs, hypotheses)
    assert result["totals"]["diagnostic"]["wer"] == 0.25
    refs[1]["audio_type"] = "vocal_unspecified"
    assert evaluate_references(refs, hypotheses)["totals"]["diagnostic"]["wer"] == 0.25
    refs[1]["uncertain_spans"] = [[0.1, 0.3]]
    result = evaluate_references(refs, hypotheses)
    assert result["videos"][1]["status"] == "excluded_uncertain_reference"

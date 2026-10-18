import pytest

from scripts.curation_audit import curation_decision, extract_curation, validate_curation


def observation(sector, item):
    return {
        "sector": {"value": sector, "frames": [] if sector == "unknown" else [1]},
        "advertised_item": {"value": item, "frames": [] if item == "unknown" else [1]},
    }


@pytest.mark.parametrize(
    "sector,item,expected",
    [
        ("moda", "clothing", "content_supported"),
        ("beleza", "cosmetic", "content_supported"),
        ("beleza", "storage_accessory", "exclude_storage_accessory"),
        ("unknown", "unknown", "inconclusive"),
        ("moda", "cosmetic", "inconclusive"),
    ],
)
def test_content_rule_does_not_use_titles_or_outcomes(sector, item, expected):
    parsed = validate_curation(observation(sector, item), 2)
    assert curation_decision(parsed) == expected


@pytest.mark.parametrize("frames", [[], [0], [True], [3], [1, 1]])
def test_known_claim_requires_actual_unique_frame_evidence(frames):
    parsed = observation("beleza", "cosmetic")
    parsed["advertised_item"]["frames"] = frames
    with pytest.raises(ValueError):
        validate_curation(parsed, 2)


def test_invalid_model_output_is_preserved_and_abstains(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "scripts.curation_audit.invoke_local_vlm",
        lambda *a, **kw: {"raw_response": "{truncated", "runtime_seconds": 1.0},
    )
    result = extract_curation([tmp_path / "frame.png"], [0.2], tmp_path)
    assert result["status"] == "invalid_curation_output"
    assert result["raw_response"] == "{truncated"
    assert result["decision"] == "inconclusive"
    assert result["parsed"] is None
    assert result["human_review"] is False

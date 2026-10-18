import pytest

from scripts.creative_analysis import determine_mode


@pytest.mark.parametrize(
    "creative_ids, expected",
    [
        (["a"], "individual"),
        (["a", "b"], "comparative"),
        (["a", "b", "c", "d", "e"], "comparative"),
    ],
)
def test_determine_mode_accepts_valid_ids(creative_ids, expected):
    assert determine_mode(creative_ids) == expected


@pytest.mark.parametrize(
    "creative_ids",
    [
        [],
        ["a", "a"],
        ["a", "b", "c", "d", "e", "f"],
    ],
)
def test_determine_mode_rejects_invalid_ids(creative_ids):
    with pytest.raises(ValueError):
        determine_mode(creative_ids)

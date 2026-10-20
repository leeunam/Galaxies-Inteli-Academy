"""Invented review bindings; no native model, private images or network."""

import copy
import json

import pytest

from scripts.vlm_product_v11 import CATEGORIES, OTHER_CUES, POSITIVE_CUES, decode


@pytest.mark.parametrize("cue", POSITIVE_CUES)
@pytest.mark.parametrize("category", CATEGORIES)
def test_each_positive_cue_and_category(cue, category):
    body = {
        "state": "presented_target",
        "presented_categories": [category],
        "presentation_cue": cue,
    }
    if cue == "worn_detail_focus" and category != "garment":
        with pytest.raises(ValueError):
            decode(json.dumps(body))
    else:
        assert decode(json.dumps(body)) == (body, True)


@pytest.mark.parametrize("state,cue", OTHER_CUES.items())
def test_negative_and_ambiguous_mapping(state, cue):
    body = {"state": state, "presented_categories": [], "presentation_cue": cue}
    assert decode(json.dumps(body))[1] == ("unknown" if state == "uncertain" else False)


@pytest.mark.parametrize(
    "change",
    [
        {"presentation_cue": "incidental"},
        {"presentation_cue": True},
        {"presentation_cue": ["held_display"]},
        {"presentation_cue": "invented"},
        {"state": "uncertain"},
        {"presented_categories": []},
        {"presented_categories": ["garment", "garment"]},
        {"presented_categories": ["invented"]},
        {"extra": 1},
    ],
)
def test_schema_valid_shape_is_not_enough_for_contradiction(change):
    body = {
        "state": "presented_target",
        "presented_categories": ["garment"],
        "presentation_cue": "held_display",
    }
    with pytest.raises(ValueError):
        decode(json.dumps(body | change))


def test_duplicate_cue_and_trailing_content_rejected():
    raw = '{"state":"no_target","presented_categories":[],"presentation_cue":"absent"}'
    assert decode(raw)[1] is False
    for invalid in (raw + "{}", raw.replace('"absent"', '"absent","presentation_cue":"absent"')):
        with pytest.raises(ValueError):
            decode(invalid)


def test_no_implicit_boolean_or_null_cue():
    for value in (None, False, 1, {}, []):
        with pytest.raises(ValueError):
            decode(
                json.dumps(
                    {"state": "no_target", "presented_categories": [], "presentation_cue": value}
                )
            )


def test_all_categories_and_one_cue_are_bounded():
    body = {
        "state": "presented_target",
        "presented_categories": list(CATEGORIES),
        "presentation_cue": "worn_detail_focus",
    }
    assert decode(json.dumps(body))[1] is True
    before = copy.deepcopy(body)
    decode(json.dumps(body))
    assert body == before

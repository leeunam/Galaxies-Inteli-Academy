"""Invented positive review records only; no native model, media or private cases."""

import copy

import pytest

from scripts.vlm_product_v12 import save
from scripts.vlm_product_v12_review import METHOD, expected_entries, validate_review


@pytest.fixture
def review_panel(tmp_path):
    plan = {"plan_sha256": "fixture-plan", "base": {"preinspection_sha256": "fixture-inspection"}}
    state = {"selected_variant": "E", "operations": []}
    for i in range(8):
        sample = f"fixture-{i}"
        state["operations"].append(
            {"kind": "preserved", "sample_id": sample, "status": "completed"}
        )
        save(
            tmp_path / "results/preserved" / sample / "result.json",
            {
                "vlm": {
                    "variant": "E",
                    "input_png_sha256": ["fixture-pixels"],
                    "input_frame_seconds": [0.2],
                    "intermediate": [
                        {
                            "state": "presented_target",
                            "presented_categories": ["garment"],
                            "presentation_cue": "held_display",
                        }
                    ],
                }
            },
        )
    body = {
        "method": METHOD,
        "phase": "phase1",
        "plan_sha256": plan["plan_sha256"],
        "variant": "E",
        "preinspection_sha256": plan["base"]["preinspection_sha256"],
        "entries": {
            k: v | {"supported": True, "note": "invented visible support"}
            for k, v in expected_entries(tmp_path, plan, state, "phase1").items()
        },
    }
    return tmp_path, plan, state, body


def test_review_binds_selected_variant_and_all_positives(review_panel):
    folder, plan, state, body = review_panel
    assert validate_review(body, folder, plan, state, "phase1")
    for variant in ("R", "RE", None):
        altered = copy.deepcopy(body)
        altered["variant"] = variant
        with pytest.raises(ValueError, match="lineage"):
            validate_review(altered, folder, plan, state, "phase1")
    changed_state = state | {"selected_variant": "R"}
    with pytest.raises(ValueError, match="selected_variant"):
        expected_entries(folder, plan, changed_state, "phase1")


@pytest.mark.parametrize("support", [False, "unknown"])
def test_one_unsupported_cue_fails_entire_review(review_panel, support):
    folder, plan, state, body = review_panel
    body["entries"][next(iter(body["entries"]))]["supported"] = support
    assert not validate_review(body, folder, plan, state, "phase1")

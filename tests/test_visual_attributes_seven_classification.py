"""Synthetic prompt/domain checks, independent of hosted perception quality."""

import ast
import hashlib
import json
from pathlib import Path

import pytest

from scripts import visual_attributes_seven as seven
from scripts.visual_attributes import FIELDS

PARAGRAPH = (
    "For the five boolean fields, false means the feature is visibly absent in the supplied samples, "
    "not unknown. Use unknown only when the supplied pixels do not let you determine presence or "
    "absence. Judge these still samples, not unobserved moments of the full video. For a known false "
    "value, cite the frames where that absence is observable. Do not invent a product, person, action "
    "or evidence to avoid unknown. Emit true and false as JSON booleans without quotation marks; only "
    "unknown is a string. Evaluate each field independently before returning the seven-field object."
)
ORIGINAL_ASTS = {
    "validate_timeline": "34287c8fde05fb6c43aa7494b097406d6834862728609b0f2cc082200b3bf0df",
    "parse_attributes": "1d4489558d565b70a0b5e85e922e0852b9ca8a991ccdd4b20eb88562da73ed0e",
    "build_schema": "76ed04ba20e7fe6491d7ca2d74e834fbfdd27c5c78b5630803a0b6e172a88be3",
    "build_generation_schema": "9c2e3d3b4288e3c1e7bcf52eef4f0aefd6fff2eeca2ca492e332b86cb9b1267d",
    "build_prompt": "9463cad025eb8a7032e25e14e10c78e5b64d559d4da663cbeba9ebea14c78c63",
    "build_typed_generation_schema": "e9f78348f171f14bc5b6485035e139aa10d9d0d9931b4b640f25d5c435bd9af8",
}


def test_all_preexisting_function_asts_unchanged():
    current = {
        node.name: hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()
        for node in ast.parse(Path(seven.__file__).read_text()).body
        if isinstance(node, ast.FunctionDef) and node.name in ORIGINAL_ASTS
    }
    assert current == ORIGINAL_ASTS


@pytest.mark.parametrize("timeline", [[0.2], [0, 2, 4, 60], [4]])
def test_candidate_appends_exact_fixed_paragraph_to_original(timeline):
    assert seven.build_classification_prompt(timeline) == seven.build_prompt(timeline) + (
        "\n\n" + PARAGRAPH
    )


@pytest.mark.parametrize("timeline", [[], [True], [4, 3], [0, 0], [float("nan")]])
def test_candidate_retains_timeline_validation(timeline):
    with pytest.raises(ValueError, match="seven_invalid_frame_timeline"):
        seven.build_classification_prompt(timeline)


@pytest.mark.parametrize("value", [True, False, "unknown", "true", "false", 0, 1, None])
def test_candidate_keeps_boolean_unknown_domain_and_evidence(value):
    seven.build_classification_prompt([0.2])
    answer = {field: {"value": False, "frames": [1]} for field in FIELDS[:5]}
    answer.update(
        scene={"value": "graphic", "frames": [1]}, format={"value": "other", "frames": [1]}
    )
    answer["screen_text"] = {"value": value, "frames": [] if value == "unknown" else [1]}
    raw = json.dumps(answer)
    if type(value) is bool or value == "unknown":
        assert seven.parse_attributes(raw, [0.2]) == answer
    else:
        with pytest.raises(ValueError):
            seven.parse_attributes(raw, [0.2])


def test_candidate_never_forces_unknown_to_false():
    answer = {field: {"value": "unknown", "frames": []} for field in FIELDS}
    seven.build_classification_prompt([4])
    assert seven.parse_attributes(json.dumps(answer), [4]) == answer

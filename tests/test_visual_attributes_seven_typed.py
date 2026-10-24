"""Invented typed-profile cases; no transport or perception claims."""

import ast
import copy
import hashlib
import json
from pathlib import Path

import pytest

from scripts import visual_attributes_seven as seven
from scripts.visual_attributes import FIELDS

LEGACY_AST_SHA256 = {
    "validate_timeline": "34287c8fde05fb6c43aa7494b097406d6834862728609b0f2cc082200b3bf0df",
    "parse_attributes": "1d4489558d565b70a0b5e85e922e0852b9ca8a991ccdd4b20eb88562da73ed0e",
    "build_schema": "76ed04ba20e7fe6491d7ca2d74e834fbfdd27c5c78b5630803a0b6e172a88be3",
    "build_generation_schema": "9c2e3d3b4288e3c1e7bcf52eef4f0aefd6fff2eeca2ca492e332b86cb9b1267d",
    "build_prompt": "9463cad025eb8a7032e25e14e10c78e5b64d559d4da663cbeba9ebea14c78c63",
}


def answer():
    values = dict.fromkeys(FIELDS[:5], False)
    values.update(scene="graphic", format="other")
    return {field: {"value": value, "frames": [1]} for field, value in values.items()}


def test_old_function_asts_are_unchanged():
    tree = ast.parse(Path(seven.__file__).read_text())
    current = {
        node.name: hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in LEGACY_AST_SHA256
    }
    assert current == LEGACY_AST_SHA256


def test_typed_shape_changes_only_five_boolean_value_schemas():
    simple = seven.build_generation_schema([0.2])
    typed = seven.build_typed_generation_schema([0.2])
    for field in FIELDS[:5]:
        value = typed["properties"][field]["properties"]["value"]
        assert value == {"anyOf": [{"type": "boolean"}, {"type": "string", "enum": ["unknown"]}]}
        typed["properties"][field]["properties"]["value"] = simple["properties"][field][
            "properties"
        ]["value"]
    assert typed == simple
    assert seven.build_generation_schema([0.2]) == simple


@pytest.mark.parametrize(
    "value", [True, False, "unknown", 0, 1, 1.0, "true", "false", None, [], {}, "OCR"]
)
@pytest.mark.parametrize("field", FIELDS)
def test_simple_and_typed_have_equivalent_json_domain(field, value):
    jsonschema = pytest.importorskip("jsonschema")
    validators = [
        jsonschema.Draft202012Validator(builder([0.2]))
        for builder in (seven.build_generation_schema, seven.build_typed_generation_schema)
    ]
    item = answer()
    item[field]["value"] = value
    assert validators[0].is_valid(item) is validators[1].is_valid(item)


@pytest.mark.parametrize(
    "case", ["unknown_evidence", "known_empty", "duplicates", "early", "coercion"]
)
def test_typed_superset_does_not_repair_strict_parser_failures(case):
    jsonschema = pytest.importorskip("jsonschema")
    item = answer()
    times = [4] if case == "early" else [0.2]
    if case == "unknown_evidence":
        item["screen_text"] = {"value": "unknown", "frames": [1]}
    elif case == "known_empty":
        item["screen_text"]["frames"] = []
    elif case == "duplicates":
        times = [0.2, 1]
        item["screen_text"]["frames"] = [1, 1]
    elif case == "coercion":
        item["screen_text"]["value"] = "false"
    before = copy.deepcopy(item)
    validator = jsonschema.Draft202012Validator(seven.build_typed_generation_schema(times))
    assert validator.is_valid(item) is (case != "coercion")
    with pytest.raises(ValueError):
        seven.parse_attributes(json.dumps(item), times)
    assert item == before


@pytest.mark.parametrize("times", [[], [True], [4, 3], [0, 0], [float("nan")]])
def test_typed_builder_retains_original_timeline_validation(times):
    with pytest.raises(ValueError, match="seven_invalid_frame_timeline"):
        seven.build_typed_generation_schema(times)

"""Invented evidence-coupled generation cases; no provider or quality claims."""

import ast
import copy
import hashlib
import json
from pathlib import Path

import jsonschema
import pytest

from scripts import visual_attributes_seven as seven
from scripts.visual_attributes import FIELDS, FORMATS, SCENES

ORIGINAL_FUNCTIONS = {
    "validate_timeline": {
        "source_sha256": "6c6c15107276939d2043f71095f7565d62d51e7b35babb969ac9a0d4ab0600a0",
        "ast_sha256": "34287c8fde05fb6c43aa7494b097406d6834862728609b0f2cc082200b3bf0df",
    },
    "parse_attributes": {
        "source_sha256": "9ae959ff561d2fded8d0d01cb36680d68cf1a9a3babce9bde388abc8b6e08f95",
        "ast_sha256": "1d4489558d565b70a0b5e85e922e0852b9ca8a991ccdd4b20eb88562da73ed0e",
    },
    "build_schema": {
        "source_sha256": "090d1b27cc63531a1059784ba55b1f029cbd30cbf1f05266db19678aeb1dbdc9",
        "ast_sha256": "76ed04ba20e7fe6491d7ca2d74e834fbfdd27c5c78b5630803a0b6e172a88be3",
    },
    "build_generation_schema": {
        "source_sha256": "61d5b4227dc5386e392832415216da98dbe8ea3c6c81a86c0cb48d5f957eb15b",
        "ast_sha256": "9c2e3d3b4288e3c1e7bcf52eef4f0aefd6fff2eeca2ca492e332b86cb9b1267d",
    },
    "build_prompt": {
        "source_sha256": "79927d55b2e4ce098b919979f9f7f2f08fad172c6b96b267d43391b15d3b6281",
        "ast_sha256": "9463cad025eb8a7032e25e14e10c78e5b64d559d4da663cbeba9ebea14c78c63",
    },
    "build_typed_generation_schema": {
        "source_sha256": "34564550d8dfaa591bd2a7d08546d2547a0009c2e5d0aae99445616d62b8c814",
        "ast_sha256": "e9f78348f171f14bc5b6485035e139aa10d9d0d9931b4b640f25d5c435bd9af8",
    },
    "build_classification_prompt": {
        "source_sha256": "2869fab03eb7ed7804f0f00bf647df09510ba4083083674f16cf7aaaa1d75729",
        "ast_sha256": "ef9d54fc4a2c2f1685bc825ace3f8d679acc0727b15c7bfc5c97facbd5301a6f",
    },
}


def answer():
    values = dict.fromkeys(FIELDS[:5], False)
    values.update(scene="graphic", format="other")
    return {field: {"value": value, "frames": [1]} for field, value in values.items()}


def validator(times):
    schema = seven.build_evidence_generation_schema(times)
    jsonschema.Draft202012Validator.check_schema(schema)
    return jsonschema.Draft202012Validator(schema)


def test_all_existing_function_asts_and_source_bytes_are_unchanged():
    source = Path(seven.__file__).read_text()
    actual = {
        node.name: {
            "source_sha256": hashlib.sha256(
                ast.get_source_segment(source, node).encode()
            ).hexdigest(),
            "ast_sha256": hashlib.sha256(
                ast.dump(node, include_attributes=False).encode()
            ).hexdigest(),
        }
        for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef) and node.name in ORIGINAL_FUNCTIONS
    }
    assert actual == ORIGINAL_FUNCTIONS
    assert set(actual) == set(ORIGINAL_FUNCTIONS)


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize(
    "unknown,frames,valid",
    [(False, [], False), (False, [1], True), (True, [], True), (True, [1], False)],
)
def test_known_requires_evidence_and_unknown_requires_empty_without_coercion(
    field, unknown, frames, valid
):
    item = answer()
    if unknown:
        item[field]["value"] = "unknown"
    item[field]["frames"] = frames
    before = copy.deepcopy(item)
    assert validator([0.2]).is_valid(item) is valid
    if valid:
        assert seven.parse_attributes(json.dumps(item), [0.2]) == item
    else:
        with pytest.raises(ValueError):
            seven.parse_attributes(json.dumps(item), [0.2])
    assert item == before


@pytest.mark.parametrize("field", FIELDS[:5])
@pytest.mark.parametrize("value", [True, False, "unknown", "true", "false", 0, 1, None, "OCR"])
def test_boolean_values_have_explicit_types(field, value):
    item = answer()
    item[field] = {"value": value, "frames": [] if value == "unknown" else [1]}
    assert validator([0.2]).is_valid(item) is (type(value) is bool or value == "unknown")


@pytest.mark.parametrize("field,choices", [("scene", SCENES), ("format", FORMATS)])
def test_category_known_values_keep_the_original_closed_domain(field, choices):
    for value in (*choices, True, False, 0, "invented"):
        item = answer()
        item[field] = {"value": value, "frames": [] if value == "unknown" else [1]}
        assert validator([0.2]).is_valid(item) is (type(value) is str and value in choices)


def test_early_boundary_no_known_choice_and_other_frames_are_unchanged():
    times = [0, 3, 3.01, 60]
    schema = seven.build_evidence_generation_schema(times)
    for field in FIELDS:
        known, unknown = schema["properties"][field]["anyOf"]
        assert known["properties"]["frames"]["items"]["enum"] == (
            [1, 2] if field == "product_visible_early" else [1, 2, 3, 4]
        )
        assert unknown["properties"]["value"] == {"type": "string", "enum": ["unknown"]}
    for frame in (1, 2, 3, 4):
        item = answer()
        item["product_visible_early"]["frames"] = [frame]
        assert validator(times).is_valid(item) is (frame <= 2)
    only_unknown = seven.build_evidence_generation_schema([3.01])["properties"][
        "product_visible_early"
    ]
    assert "anyOf" not in only_unknown
    assert only_unknown["properties"]["value"] == {"type": "string", "enum": ["unknown"]}
    item = answer()
    assert not validator([4]).is_valid(item)
    item["product_visible_early"] = {"value": "unknown", "frames": []}
    assert validator([4]).is_valid(item)
    assert seven.parse_attributes(json.dumps(item), [4]) == item


def test_duplicate_frames_remain_an_independent_parser_rejection():
    item = answer()
    item["screen_text"]["frames"] = [1, 1]
    assert validator([0.2, 1]).is_valid(item)
    with pytest.raises(ValueError):
        seven.parse_attributes(json.dumps(item), [0.2, 1])


def test_minimal_keywords_closed_objects_and_frame_caps():
    schema = seven.build_evidence_generation_schema([0.2, 1])
    assert schema["required"] == list(FIELDS)
    assert schema["additionalProperties"] is False
    forbidden = {
        "oneOf",
        "const",
        "uniqueItems",
        "$schema",
        "if",
        "then",
        "else",
        "dependencies",
        "dependentSchemas",
        "dependentRequired",
    }

    def walk(value):
        if isinstance(value, dict):
            assert not forbidden.intersection(value)
            if value.get("type") == "object":
                assert value["additionalProperties"] is False
                assert set(value["required"]) == set(value["properties"])
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(schema)
    for defect in (
        "extra_top",
        "extra_field",
        "missing_field",
        "missing_value",
        "missing_frames",
        "invalid_index",
        "too_many",
        "float_index",
    ):
        item = answer()
        if defect == "extra_top":
            item["extra"] = {}
        elif defect == "extra_field":
            item["screen_text"]["extra"] = 1
        elif defect == "missing_field":
            del item["scene"]
        elif defect == "missing_value":
            del item["scene"]["value"]
        elif defect == "missing_frames":
            del item["scene"]["frames"]
        else:
            item["screen_text"]["frames"] = {
                "invalid_index": [3],
                "too_many": [1, 2, 1],
                "float_index": [1.2],
            }[defect]
        assert not validator([0.2, 1]).is_valid(item)


@pytest.mark.parametrize(
    "times", [[], [True], [4, 3], [0, 0], [float("nan")], [float("inf")], [-1], [61]]
)
def test_original_timeline_validation(times):
    with pytest.raises(ValueError, match="seven_invalid_frame_timeline"):
        seven.build_evidence_generation_schema(times)

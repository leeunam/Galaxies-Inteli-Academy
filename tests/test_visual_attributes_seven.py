"""Invented contract probes; none are perception evidence or model calls."""

import copy
import json

import pytest

from scripts.visual_attributes import FIELDS, FORMATS, SCENES
from scripts.visual_attributes_seven import build_prompt, build_schema, parse_attributes

TIMES = [0, 3, 3.001, 60]


def attributes():
    return {
        "person_visible": {"value": True, "frames": [1]},
        "product_visible_early": {"value": False, "frames": [2]},
        "product_closeup": {"value": False, "frames": [4]},
        "demonstration": {"value": True, "frames": [3, 4]},
        "screen_text": {"value": False, "frames": [1]},
        "scene": {"value": "mixed", "frames": [1, 4]},
        "format": {"value": "application", "frames": [3]},
    }


def parse(value, times=TIMES):
    return parse_attributes(json.dumps(value), times)


def test_complete_values_and_frame_order_are_preserved_without_quality_claims():
    value = attributes()
    value["scene"]["frames"] = [4, 1]
    before = copy.deepcopy(value)
    assert parse(value) == before
    assert parse_attributes(json.dumps(value).encode(), TIMES) == before
    assert value == before
    assert set(parse(value)) == set(FIELDS)
    assert parse(value)["format"]["value"] == "application"


@pytest.mark.parametrize("field", ["product_closeup", "demonstration"])
@pytest.mark.parametrize("value", [True, False, "unknown"])
def test_previously_withheld_fields_keep_every_valid_option(field, value):
    answer = attributes()
    answer[field] = {"value": value, "frames": [] if value == "unknown" else [4]}
    assert parse(answer)[field] == answer[field]


def test_invented_http200_failure_rejects_ocr_and_unknown_frames_independently():
    # Equivalent failure shapes to the control; no original response or media read.
    answer = attributes()
    answer["screen_text"] = {"value": "ABC123", "frames": [1]}
    answer["person_visible"] = {"value": "unknown", "frames": [1]}
    with pytest.raises(ValueError):
        parse(answer)
    answer["person_visible"] = {"value": "unknown", "frames": []}
    with pytest.raises(ValueError):
        parse(answer)
    answer["screen_text"] = {"value": True, "frames": [1]}
    answer["person_visible"] = {"value": "unknown", "frames": [1]}
    before = copy.deepcopy(answer)
    with pytest.raises(ValueError, match="seven_unknown_requires_empty_frames"):
        parse(answer)
    assert answer == before


@pytest.mark.parametrize("field", FIELDS)
def test_each_field_is_required_and_requires_exact_evidence_shape(field):
    answer = attributes()
    del answer[field]
    with pytest.raises(ValueError):
        parse(answer)
    answer = attributes()
    answer[field]["extra"] = "anything"
    with pytest.raises(ValueError):
        parse(answer)
    answer[field] = [True, [1]]
    with pytest.raises(ValueError):
        parse(answer)


@pytest.mark.parametrize("field", FIELDS)
@pytest.mark.parametrize("frames", [[], [0], [5], [True], [1.0], [1, 1], "1", None, [-1]])
def test_each_known_field_rejects_invalid_evidence(field, frames):
    answer = attributes()
    answer[field]["frames"] = frames
    with pytest.raises(ValueError):
        parse(answer)


@pytest.mark.parametrize("field", FIELDS)
def test_unknown_requires_empty_frames_for_every_field(field):
    answer = attributes()
    answer[field] = {"value": "unknown", "frames": [1]}
    with pytest.raises(ValueError):
        parse(answer)
    answer[field]["frames"] = []
    assert parse(answer)[field] == {"value": "unknown", "frames": []}


@pytest.mark.parametrize("field", FIELDS[:5])
@pytest.mark.parametrize("value", [0, 1, 1.0, "true", "false", "yes", None, [], {}])
def test_boolean_fields_are_real_booleans_or_unknown(field, value):
    answer = attributes()
    answer[field]["value"] = value
    with pytest.raises(ValueError):
        parse(answer)


@pytest.mark.parametrize("field,options", [("scene", SCENES), ("format", FORMATS)])
def test_all_original_categorical_options_remain_valid(field, options):
    for value in options:
        answer = attributes()
        answer[field] = {"value": value, "frames": [] if value == "unknown" else [1]}
        assert parse(answer)[field]["value"] == value
    for value in (True, 1, "json", "APPLICATION", None, [], {}):
        answer[field] = {"value": value, "frames": [1]}
        with pytest.raises(ValueError):
            parse(answer)


@pytest.mark.parametrize(
    "raw",
    [
        '{"scene": {}, "scene": {}}',
        '{"x": {"value": true, "value": false}}',
        '{"x": NaN}',
        '{"x": Infinity}',
        '{"x": -Infinity}',
        '{"x": 1e999}',
        'prefix {"x":1}',
        "```json\n{}\n```",
        "{} {}",
        "{} trailing",
        "{",
        "[]",
        "null",
        b"\xff",
        "\ud800",
        {"not": "raw JSON"},
    ],
)
def test_strict_single_complete_finite_json(raw):
    with pytest.raises(ValueError):
        parse_attributes(raw, TIMES)


def test_duplicate_keys_and_trailing_content_cannot_hide_inside_valid_answer():
    raw = json.dumps(attributes())
    duplicate = raw.replace('"value": true', '"value": false, "value": true', 1)
    for invalid in (duplicate, raw + raw, "Here: " + raw, raw + " trailing"):
        with pytest.raises(ValueError):
            parse_attributes(invalid, TIMES)
    assert parse_attributes(" \n" + raw + "\t", TIMES) == attributes()


@pytest.mark.parametrize(
    "times",
    [
        [],
        [0, 1, 2, 3, 4],
        (0,),
        None,
        [True],
        ["0"],
        [float("nan")],
        [float("inf")],
        [float("-inf")],
        [10**400],
        [-0.01],
        [60.01],
        [1, 0],
        [1, 1.0],
    ],
)
def test_invalid_timeline_rejected_by_every_entry_point(times):
    for operation in (build_schema, build_prompt):
        with pytest.raises(ValueError, match="seven_invalid_frame_timeline"):
            operation(times)
    with pytest.raises(ValueError, match="seven_invalid_frame_timeline"):
        parse_attributes(json.dumps(attributes()), times)


def test_three_second_boundary_and_no_early_sample():
    answer = attributes()
    assert parse(answer)["product_visible_early"]["frames"] == [2]
    answer["product_visible_early"]["frames"] = [3]
    with pytest.raises(ValueError):
        parse(answer)
    answer = {field: {"value": "unknown", "frames": []} for field in FIELDS}
    for field in ("product_closeup", "demonstration"):
        answer[field] = {"value": True, "frames": [1]}
    assert parse(answer, [3.001]) == answer
    answer["product_visible_early"] = {"value": False, "frames": [1]}
    with pytest.raises(ValueError):
        parse(answer, [3.001])


def schema_cases():
    cases = [(attributes(), True)]
    for field in FIELDS:
        for item, valid in (
            ({"value": "unknown", "frames": []}, True),
            ({"value": "unknown", "frames": [1]}, False),
            ({"value": attributes()[field]["value"], "frames": []}, False),
            ({"value": attributes()[field]["value"], "frames": [1, 1]}, False),
            ({"value": attributes()[field]["value"], "frames": [0]}, False),
            ({"value": attributes()[field]["value"], "frames": [5]}, False),
            ({"value": attributes()[field]["value"], "frames": [True]}, False),
            ({"value": "invented enum or OCR", "frames": [1]}, False),
        ):
            answer = attributes()
            answer[field] = item
            cases.append((answer, valid))
        missing = attributes()
        del missing[field]
        cases.append((missing, False))
    for field in FIELDS[:5]:
        for value in (True, False):
            answer = attributes()
            answer[field] = {"value": value, "frames": [1]}
            cases.append((answer, True))
    for field, choices in (("scene", SCENES), ("format", FORMATS)):
        for value in choices[:-1]:
            answer = attributes()
            answer[field] = {"value": value, "frames": [1]}
            cases.append((answer, True))
    cases.append((attributes() | {"views": 12}, False))
    late = attributes()
    late["product_visible_early"]["frames"] = [3]
    cases.append((late, False))
    return cases


def test_schema_matches_structural_corpus_with_installed_jsonschema():
    jsonschema = pytest.importorskip("jsonschema")
    schema = build_schema(TIMES)
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)
    for answer, expected in schema_cases():
        assert validator.is_valid(answer) is expected, answer
        if expected:
            assert parse(answer) == answer
        else:
            with pytest.raises(ValueError):
                parse(answer)


def test_jsonschema_numeric_semantics_do_not_replace_strict_parser():
    jsonschema = pytest.importorskip("jsonschema")
    from jsonschema.validators import extend

    schema = build_schema(TIMES)
    answer = attributes()
    answer["screen_text"]["frames"] = [1.0]
    # Standard JSON Schema treats 1.0 as integer; installed grammar needs its own preflight.
    assert jsonschema.Draft202012Validator(schema).is_valid(answer)
    strict = extend(
        jsonschema.Draft202012Validator,
        type_checker=jsonschema.Draft202012Validator.TYPE_CHECKER.redefine(
            "integer", lambda checker, instance: type(instance) is int
        ),
    )
    assert not strict(schema).is_valid(answer)
    with pytest.raises(ValueError):
        parse(answer)


def test_schema_without_early_frames_only_allows_unknown_for_that_field():
    jsonschema = pytest.importorskip("jsonschema")
    validator = jsonschema.Draft202012Validator(build_schema([4, 60]))
    answer = {field: {"value": "unknown", "frames": []} for field in FIELDS}
    answer["product_closeup"] = {"value": False, "frames": [2]}
    answer["demonstration"] = {"value": True, "frames": [1]}
    assert validator.is_valid(answer)
    assert parse(answer, [4, 60]) == answer
    answer["product_visible_early"] = {"value": False, "frames": [1]}
    assert not validator.is_valid(answer)


def test_prompt_explicitly_names_seven_fields_types_and_original_rubrics():
    prompt = build_prompt(TIMES)
    assert all(field in prompt for field in FIELDS)
    assert "JSON true, JSON false" in prompt
    assert "never transcribe OCR" in prompt
    assert "holding a package alone is not application" in prompt
    assert "a face alone is insufficient" in prompt
    assert "Incidental clothing worn by a speaker alone does not count" in prompt
    assert "Do not infer audio, views, emotion or intent" in prompt
    assert "frame 2 = 3 seconds" in prompt
    assert "frame 3 = 3.001 seconds" in prompt

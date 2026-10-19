import json

import pytest
from PIL import Image

from scripts.private_checkpoint import file_hash
from scripts.vlm_per_frame import (
    BOOLEAN_FIELDS,
    aggregate,
    extract,
    parse_output,
    specification,
    verify,
)


def values(person=False, product=False, text=False):
    return dict(zip(BOOLEAN_FIELDS, (person, product, text), strict=True))


def test_positive_evidence_is_frame_local_and_late_product_is_excluded():
    parsed = aggregate([values(False, False, "unknown"), values(True, True, True)], [0.2, 4.0])
    assert parsed["person_visible"] == {"value": True, "frames": [2]}
    assert parsed["screen_text"] == {"value": True, "frames": [2]}
    assert parsed["product_visible_early"] == {"value": False, "frames": [1]}
    assert all(
        parsed[f] == {"value": "unknown", "frames": []}
        for f in ("scene", "format", "product_closeup", "demonstration")
    )


def test_unknown_is_never_filled_as_false_and_presence_wins():
    answer = aggregate(
        [values("unknown", False, False), values(False, "unknown", True)], [0.2, 2.8]
    )
    assert answer["person_visible"] == {"value": "unknown", "frames": []}
    assert answer["product_visible_early"] == {"value": "unknown", "frames": []}
    assert answer["screen_text"] == {"value": True, "frames": [2]}
    assert aggregate([values()], [4.0])["product_visible_early"] == {
        "value": "unknown",
        "frames": [],
    }
    assert aggregate([values(), values()], [0.2, 2.8])["person_visible"] == {
        "value": False,
        "frames": [1, 2],
    }


@pytest.mark.parametrize(
    "seconds", [[], [0.2, 0.2], [2, 1], [-1], [float("nan")], [True], [0, 1, 2, 3, 4]]
)
def test_invalid_timeline_is_refused(seconds):
    with pytest.raises(ValueError):
        aggregate([values() for _ in seconds], seconds)


@pytest.mark.parametrize(
    "raw",
    [
        '{"person_visible":1}',
        '{"person_visible":null}',
        '{"person_visible":"false"}',
        '{"person_visible":true,"person_visible":false}',
        '{"person_visible":true,"extra":false}',
        '{"wrapper":{"person_visible":true}}',
        'before {"person_visible":true}',
        '{"person_visible":true} after',
        '```json\n{"person_visible":true}\n```',
        '{"person_visible":true} {"person_visible":false}',
        '{"person_visible":',
    ],
)
def test_no_json_repairs_or_ambiguous_answers(raw):
    with pytest.raises(ValueError):
        parse_output(raw, ["person_visible"])


@pytest.mark.parametrize("candidate,expected_calls", [("A", 2), ("B", 6)])
def test_raw_capture_one_image_per_call_and_reproducible_derivation(
    tmp_path, candidate, expected_calls
):
    cells = []
    for index, color in enumerate(("black", "white")):
        p = tmp_path / f"image-{index}.png"
        Image.new("RGB", (320, 330), color).save(p)
        cells.append(p)
    calls = []

    def invoker(paths, prompt, work, schema, *, max_tokens):
        assert len(paths) == 1 and "views" in prompt and "schema" in prompt
        calls.append(paths)
        flag = paths[0] == cells[1]
        return {
            "raw_response": json.dumps({k: flag for k in schema["properties"]}),
            "runtime_seconds": 0.1,
        }

    result = extract(
        cells,
        [0.2, 4.0],
        tmp_path,
        candidate=candidate,
        evidence_dir=tmp_path / "calls",
        invoker=invoker,
    )
    assert len(calls) == len(result["calls"]) == expected_calls
    assert result["input_png_sha256"] == [file_hash(p) for p in cells]
    assert verify(result, tmp_path / "calls") == result["parsed"]
    assert result["parsed"]["product_visible_early"] == {"value": False, "frames": [1]}
    first = tmp_path / "calls/frame-1-group-1.json"
    first.write_bytes(first.read_bytes() + b" ")
    with pytest.raises(ValueError):
        verify(result, tmp_path / "calls")


def test_rejected_raw_response_is_preserved_before_parser_error(tmp_path):
    image = tmp_path / "input.png"
    Image.new("RGB", (320, 330)).save(image)
    with pytest.raises(ValueError):
        extract(
            [image],
            [0.2],
            tmp_path,
            candidate="A",
            evidence_dir=tmp_path / "calls",
            invoker=lambda *a, **kw: {"raw_response": "{incomplete"},
        )
    record = json.loads((tmp_path / "calls/frame-1-group-1.json").read_bytes())
    assert record["status"] == "failed" and record["raw_response"] == "{incomplete"


def test_candidate_specs_are_fixed_and_do_not_request_frame_indices():
    assert len(specification("A")) == 1 and len(specification("B")) == 3
    assert specification("A")[0]["max_tokens"] == 96
    assert all(s["max_tokens"] == 64 for s in specification("B"))
    assert all(
        "frames" not in s["schema"]["properties"] for c in ("A", "B") for s in specification(c)
    )


@pytest.mark.parametrize(
    "mode,size,fmt",
    [("L", (320, 330), "PNG"), ("RGB", (320, 320), "PNG"), ("RGB", (320, 330), "JPEG")],
)
def test_invalid_image_contract_prevents_any_model_call(tmp_path, mode, size, fmt):
    image = tmp_path / "input.image"
    Image.new(mode, size).save(image, format=fmt)
    with pytest.raises(ValueError, match="input_pixels"):
        extract(
            [image],
            [0.2],
            tmp_path,
            candidate="A",
            evidence_dir=tmp_path / "calls",
            invoker=lambda *a, **kw: pytest.fail("invalid image reached model"),
        )

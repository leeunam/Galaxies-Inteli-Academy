import copy
import json

import pytest
from PIL import Image

from scripts import vlm_product_v14 as module
from scripts.private_checkpoint import digest
from scripts.vlm_product_v13 import specification as parent_specification


@pytest.mark.parametrize(
    "variant,expected",
    [
        ("R", "08432adbfee0b4ae4af793e5caa4826b7e1d48da8b6e9774b82078a6a132a325"),
    ],
)
def test_exact_approved_text_and_fixed_parent_contract(variant, expected):
    parent = parent_specification("R")
    before = copy.deepcopy(parent)
    spec = module.specification(variant)
    assert parent == before and parent_specification("R") == before
    assert digest(spec["prompt"]) == expected
    assert spec["fields"] == parent["fields"] and spec["max_tokens"] == 64
    assert (
        digest(spec["schema"]) == "4b5c9f3a78cef507d7855d84d1a940daadbdc801bd5359713d29c07b1c31c034"
    )
    assert len(spec["schema"]["oneOf"]) == 7


@pytest.mark.parametrize("variant", ["", "E", "RE", "cache_v11", "new", None, 1])
def test_undeclared_variants_rejected(variant):
    with pytest.raises(ValueError):
        module.specification(variant)


@pytest.mark.parametrize(
    "values,expected",
    [
        ([False, False, False, True], False),
        ([False, True, False, False], True),
        ([False, "unknown", False, False], "unknown"),
    ],
)
@pytest.mark.parametrize("variant", ["R"])
def test_reserved_before_invocation_and_unchanged_temporal_rules(
    tmp_path, values, expected, variant
):
    cells = []
    for i in range(4):
        cell = tmp_path / f"input-{i}.png"
        Image.new("RGB", (320, 330), "white").save(cell)
        cells.append(cell)
    reservations, invocations = [], []
    evidence = tmp_path / "calls"

    def invoke(*args, **kwargs):
        index = len(invocations) + 1
        assert reservations == list(range(1, index + 1))
        assert json.loads((evidence / f"frame-{index}.json").read_bytes())["status"] == "running"
        invocations.append(index)
        v = values[index - 1]
        return {
            "raw_response": json.dumps(
                {
                    "state": "presented_target"
                    if v is True
                    else "uncertain"
                    if v == "unknown"
                    else "no_target",
                    "presented_categories": ["garment"] if v is True else [],
                    "presentation_cue": "held_display"
                    if v is True
                    else "uncertain"
                    if v == "unknown"
                    else "absent",
                }
            )
        }

    result = module.extract(
        cells,
        [0.2, 1.5, 2.8, 5.0],
        tmp_path,
        variant=variant,
        evidence_dir=evidence,
        reserve=reservations.append,
        invoker=invoke,
    )
    assert module.verify(result, evidence)[module.FIELD]["value"] == expected
    assert result["approved_for_training"] is False
    assert all(f["person_visible"] == f["screen_text"] == "unknown" for f in result["per_frame"])


@pytest.mark.parametrize(
    "raw",
    [
        '{"state":"presented_target","presented_categories":[]}',
        '{"state":"no_target","presented_categories":["garment"]}',
        '{"state":"no_target","state":"no_target","presented_categories":[]}',
        "invalid",
        "\ud800",
    ],
)
def test_failed_raw_is_preserved_without_repair_or_retry(tmp_path, raw):
    cell = tmp_path / "cell.png"
    Image.new("RGB", (320, 330)).save(cell)
    calls, reserved = [], []

    def invoke(*args, **kwargs):
        calls.append(True)
        return {"raw_response": raw}

    evidence = tmp_path / "calls"
    with pytest.raises((ValueError, UnicodeError)):
        module.extract(
            [cell],
            [0.2],
            tmp_path,
            variant="R",
            evidence_dir=evidence,
            reserve=reserved.append,
            invoker=invoke,
        )
    assert calls == [True] and reserved == [1]
    receipt = json.loads((evidence / "frame-1.json").read_bytes())
    assert receipt["status"] == "failed" and receipt["raw_response"] == raw
    with pytest.raises(FileExistsError):
        module.extract(
            [cell],
            [0.2],
            tmp_path,
            variant="R",
            evidence_dir=evidence,
            reserve=reserved.append,
            invoker=invoke,
        )
    assert len(calls) == 1


def test_pixels_must_not_change_during_invocation(tmp_path):
    cell = tmp_path / "cell.png"
    Image.new("RGB", (320, 330)).save(cell)

    def invoke(*args, **kwargs):
        Image.new("RGB", (320, 330), "white").save(cell)
        return {
            "raw_response": '{"state":"no_target","presented_categories":[],"presentation_cue":"absent"}'
        }

    with pytest.raises(ValueError, match="pixels_changed"):
        module.extract(
            [cell],
            [0.2],
            tmp_path,
            variant="R",
            evidence_dir=tmp_path / "calls",
            reserve=lambda _: None,
            invoker=invoke,
        )


def test_entire_semantic_domain_and_all_raw_mutations():
    from jsonschema import Draft202012Validator

    from scripts.vlm_product_v14_grammar import probes

    schema = module.specification()["schema"]
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    rows = probes()
    domain = [r for r in rows if r["group"] == "finite_domain"]
    assert len(domain) == 9548 and sum(r["expected"] for r in domain) == 16
    for row in domain:
        assert validator.is_valid(json.loads(row["raw"])) == row["expected"]
    for row in rows:
        if row["group"] == "raw_mutation" and row["raw"].startswith('{"presentation_cue"'):
            continue  # Native grammar fixes key order; the semantic decoder does not.
        try:
            module.decode(row["raw"])
            accepted = True
        except ValueError:
            accepted = False
        assert accepted == row["expected"]


def test_R_contradiction_preserved_and_not_accepted(tmp_path):
    raw = '{"state":"no_target","presented_categories":[],"presentation_cue":"incidental"}'
    test_failed_raw_is_preserved_without_repair_or_retry(tmp_path, raw)


@pytest.mark.parametrize("cue", ["held_display", "isolated_display", "visible_use"])
@pytest.mark.parametrize("category", ["cosmetic", "applicator", "garment", "accessory"])
def test_each_category_remains_available_for_its_single_item(category, cue):
    body = {
        "state": "presented_target",
        "presented_categories": [category],
        "presentation_cue": cue,
    }
    assert module.decode(json.dumps(body)) == (body, True)


def test_v13_multicategory_raw_is_preserved_and_rejected_before_mapping(tmp_path):
    raw = (
        '{"state":"presented_target","presented_categories":["garment","cosmetic"],'
        '"presentation_cue":"worn_detail_focus"}'
    )
    from scripts.vlm_product_v13 import decode as old_decode

    assert old_decode(raw)[1] is True
    test_failed_raw_is_preserved_without_repair_or_retry(tmp_path, raw)


def test_worn_cannot_borrow_the_garment_cue_for_cosmetic():
    with pytest.raises(ValueError):
        module.decode(
            '{"state":"presented_target","presented_categories":["cosmetic"],'
            '"presentation_cue":"worn_detail_focus"}'
        )
    body, value = module.decode(
        '{"state":"presented_target","presented_categories":["garment"],'
        '"presentation_cue":"worn_detail_focus"}'
    )
    assert value is True and body["presented_categories"] == ["garment"]

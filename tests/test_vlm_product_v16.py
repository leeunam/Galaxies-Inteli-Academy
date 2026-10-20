"""Invented pixels/responses only; actual native preflight is separately recorded."""

import copy
import json

import pytest
from PIL import Image

from scripts import vlm_product_v16 as m
from scripts.private_checkpoint import digest
from scripts.vlm_product_v15 import specification as previous_specification


def raw(native, variant):
    return json.dumps({k: native[k] for k in m.ORDER[variant]}, separators=(",", ":"))


def test_only_properties_serialization_and_neutral_common_prompt_change():
    a, b = (m.specification(v) for v in m.VARIANTS)
    assert a["prompt"] == b["prompt"]
    assert a["prompt"] == previous_specification()["prompt"].replace(m.OLD_RETURN, m.COMMON_RETURN)
    assert "in that order" not in a["prompt"]
    assert a["max_tokens"] == b["max_tokens"] == 64
    assert a["schema"] == b["schema"] == previous_specification()["schema"]
    assert digest(a["schema"]) == digest(b["schema"])
    assert m.ordered_schema_hash(a["schema"]) != m.ordered_schema_hash(b["schema"])
    for spec, v in ((a, m.VARIANTS[0]), (b, m.VARIANTS[1])):
        for branch in spec["schema"]["oneOf"]:
            assert list(branch["properties"]) == m.ORDER[v]
            assert branch["required"] == m.ORDER["item_first"]


@pytest.mark.parametrize("variant", m.VARIANTS)
def test_finite_domain_schema_decoder_and_grammar_expectations(variant):
    from jsonschema import Draft202012Validator

    from scripts.vlm_product_v16_grammar import probes

    validator = Draft202012Validator(m.specification(variant)["schema"])
    rows = probes(variant)
    finite = [r for r in rows if r["group"] == "finite_domain"]
    assert len(rows) == 13703 and len(finite) == 13640
    valid = [r for r in finite if r["expected"]]
    assert len(valid) == 22
    assert len({digest(m.project(json.loads(r["raw"]))) for r in valid}) == 16
    for row in finite:
        assert validator.is_valid(json.loads(row["raw"])) == row["expected"]
    for row in rows:
        try:
            m.decode(row["raw"], variant)
            accepted = True
        except ValueError:
            accepted = False
        assert accepted == row["expected"]


@pytest.mark.parametrize("variant", m.VARIANTS)
@pytest.mark.parametrize(
    "values,expected",
    [
        ([False, False, False, True], False),
        ([False, True, False, False], True),
        ([False, "unknown", False, False], "unknown"),
    ],
)
def test_receipts_raw_native_projection_and_original_temporal_policy(
    tmp_path, variant, values, expected
):
    cells = []
    for i in range(4):
        path = tmp_path / f"{i}.png"
        Image.new("RGB", (320, 330)).save(path)
        cells.append(path)
    calls = []
    reservations = []

    def invoke(paths, prompt, work, schema, **kwargs):
        i = len(calls) + 1
        assert reservations == list(range(1, i + 1))
        assert (
            json.loads((tmp_path / "calls" / f"frame-{i}.json").read_bytes())["status"] == "running"
        )
        calls.append(i)
        value = values[i - 1]
        native = {
            "item_configuration": "hand_holds_hanger_out"
            if value is True
            else "unclear"
            if value == "unknown"
            else "absent",
            "state": "presented_target"
            if value is True
            else "uncertain"
            if value == "unknown"
            else "no_target",
            "presented_categories": ["garment"] if value is True else [],
        }
        assert (
            prompt == m.specification(variant)["prompt"]
            and schema == m.specification(variant)["schema"]
            and kwargs["max_tokens"] == 64
        )
        return {"raw_response": raw(native, variant)}

    result = m.extract(
        cells,
        [0.2, 1.5, 2.8, 5.0],
        tmp_path,
        variant=variant,
        evidence_dir=tmp_path / "calls",
        reserve=reservations.append,
        invoker=invoke,
    )
    assert m.verify(result, tmp_path / "calls")[m.FIELD]["value"] == expected
    assert result["presentation_cue_source"] == m.CUE_PROVENANCE
    assert not result["approved_for_training"]
    bad = copy.deepcopy(result)
    bad["native_intermediate"][0]["item_configuration"] = "incidental"
    with pytest.raises(ValueError):
        m.verify(bad, tmp_path / "calls")


@pytest.mark.parametrize("variant", m.VARIANTS)
def test_wrong_native_order_rejected_and_preserved_without_retry(tmp_path, variant):
    other = next(v for v in m.VARIANTS if v != variant)
    native = {"item_configuration": "absent", "state": "no_target", "presented_categories": []}
    response = raw(native, other)
    cell = tmp_path / "input.png"
    Image.new("RGB", (320, 330)).save(cell)
    calls = []

    def invoke(*a, **k):
        calls.append(1)
        return {"raw_response": response}

    with pytest.raises(ValueError, match="serialization_order"):
        m.extract(
            [cell],
            [0.0],
            tmp_path,
            variant=variant,
            evidence_dir=tmp_path / "calls",
            reserve=lambda i: None,
            invoker=invoke,
        )
    receipt = json.loads((tmp_path / "calls/frame-1.json").read_bytes())
    assert receipt["raw_response"] == response and receipt["status"] == "failed"
    with pytest.raises(FileExistsError):
        m.extract(
            [cell],
            [0.0],
            tmp_path,
            variant=variant,
            evidence_dir=tmp_path / "calls",
            reserve=lambda i: None,
            invoker=invoke,
        )
    assert calls == [1]


@pytest.mark.parametrize("variant", ["R", "", None, 1, "new"])
def test_unknown_condition_rejected(variant):
    with pytest.raises(ValueError):
        m.specification(variant)


def test_positive_selection_is_fixed_existing_held_support_and_dependent_crops():
    assert len(m.POSITIVE_SELECTION) == 5
    assert len({(x[0], x[1]) for x in m.POSITIVE_SELECTION}) == 5
    assert len({x[0] for x in m.POSITIVE_SELECTION}) == 3
    assert sum("hand_holds_hanger_out" in x[2] for x in m.POSITIVE_SELECTION) == 4
    assert sum("hand_pulls_worn_fabric_out" in x[2] for x in m.POSITIVE_SELECTION) == 1

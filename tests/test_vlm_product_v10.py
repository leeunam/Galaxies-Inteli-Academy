import copy
import json

import pytest
from PIL import Image

from scripts import vlm_product_v10 as module
from scripts.vlm_product_states import specification as v9_specification


def test_only_approved_paragraph_is_added_and_parent_unchanged():
    parent = v9_specification("structured")
    before = copy.deepcopy(parent)
    spec = module.specification()
    assert spec["prompt"].replace(module.INSERTION, "", 1) == parent["prompt"]
    assert spec["prompt"].count(module.INSERTION) == 1
    assert {k: v for k, v in spec.items() if k != "prompt"} == {
        k: v for k, v in parent.items() if k != "prompt"
    }
    assert parent == before and module.specification() == spec


@pytest.mark.parametrize(
    "values,expected",
    [
        ([False, False, False, True], False),
        ([False, True, False, False], True),
        ([False, "unknown", False, False], "unknown"),
    ],
)
def test_reserved_before_invocation_and_unchanged_temporal_rules(tmp_path, values, expected):
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
                }
            )
        }

    result = module.extract(
        cells,
        [0.2, 1.5, 2.8, 5.0],
        tmp_path,
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
            [cell], [0.2], tmp_path, evidence_dir=evidence, reserve=reserved.append, invoker=invoke
        )
    assert calls == [True] and reserved == [1]
    receipt = json.loads((evidence / "frame-1.json").read_bytes())
    assert receipt["status"] == "failed" and receipt["raw_response"] == raw
    with pytest.raises(FileExistsError):
        module.extract(
            [cell], [0.2], tmp_path, evidence_dir=evidence, reserve=reserved.append, invoker=invoke
        )
    assert len(calls) == 1


def test_pixels_must_not_change_during_invocation(tmp_path):
    cell = tmp_path / "cell.png"
    Image.new("RGB", (320, 330)).save(cell)

    def invoke(*args, **kwargs):
        Image.new("RGB", (320, 330), "white").save(cell)
        return {"raw_response": '{"state":"no_target","presented_categories":[]}'}

    with pytest.raises(ValueError, match="pixels_changed"):
        module.extract(
            [cell],
            [0.2],
            tmp_path,
            evidence_dir=tmp_path / "calls",
            reserve=lambda _: None,
            invoker=invoke,
        )

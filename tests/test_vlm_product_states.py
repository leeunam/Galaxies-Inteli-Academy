import copy
import json

import pytest
from PIL import Image

from scripts import vlm_product_states as module


def test_product_states_keep_original_temporal_evidence(tmp_path):
    cells = []
    for i in range(4):
        path = tmp_path / f"frame-{i}.png"
        Image.new("RGB", (320, 330)).save(path)
        cells.append(path)
    answers = iter(
        [
            {"state": "incidental_only", "presented_categories": []},
            {"state": "presented_target", "presented_categories": ["cosmetic", "accessory"]},
            {"state": "uncertain", "presented_categories": []},
            {"state": "presented_target", "presented_categories": ["garment"]},
        ]
    )

    def invoke(*args, **kwargs):
        return {"raw_response": json.dumps(next(answers))}

    evidence = tmp_path / "calls"
    result = module.extract(
        cells,
        [0.2, 1.5, 2.8, 30.0],
        tmp_path,
        variant="structured",
        evidence_dir=evidence,
        invoker=invoke,
    )
    parsed = module.verify(result, evidence)
    assert parsed["product_visible_early"] == {"value": True, "frames": [2]}
    assert parsed["person_visible"] == {"value": "unknown", "frames": []}
    assert result["intermediate"][1]["presented_categories"] == ["cosmetic", "accessory"]


@pytest.mark.parametrize(
    "raw",
    [
        '{"state":"presented_target","presented_categories":[]}',
        '{"state":"no_target","presented_categories":["garment"]}',
        '{"state":"presented_target","presented_categories":["cosmetic","cosmetic"]}',
        '{"state":"presented_target","presented_categories":["shoe"]}',
        '{"state":"no_target","state":"uncertain","presented_categories":[]}',
        '{"state":"no_target","presented_categories":[],"explanation":"empty"}',
        '{"state":false,"presented_categories":[]}',
        '{"state":"yes","presented_categories":[]}',
        '["no_target",[]]',
    ],
)
def test_structured_contradictions_are_rejected_without_repair(raw):
    with pytest.raises(ValueError):
        module.decode(raw, "structured")


def test_invalid_native_answer_is_retained_once_without_repair(tmp_path):
    image = tmp_path / "image.png"
    Image.new("RGB", (320, 330)).save(image)
    calls = []
    raw = '{"state":"presented_target","presented_categories":[]}'

    def invoke(*args, **kwargs):
        calls.append(True)
        return {"raw_response": raw}

    evidence = tmp_path / "calls"
    with pytest.raises(ValueError):
        module.extract(
            [image], [0.2], tmp_path, variant="structured", evidence_dir=evidence, invoker=invoke
        )
    receipt = json.loads((evidence / "frame-1.json").read_bytes())
    assert receipt["raw_response"] == raw and receipt["status"] == "failed"
    assert len(calls) == 1


def test_changed_pixels_halt_and_keep_the_response(tmp_path):
    image = tmp_path / "image.png"
    Image.new("RGB", (320, 330), "black").save(image)

    def invoke(paths, *args, **kwargs):
        Image.new("RGB", (320, 330), "white").save(paths[0])
        return {"raw_response": '{"state":"no_target","presented_categories":[]}'}

    evidence = tmp_path / "calls"
    with pytest.raises(ValueError, match="pixels_changed"):
        module.extract(
            [image], [0.2], tmp_path, variant="structured", evidence_dir=evidence, invoker=invoke
        )
    call = json.loads((evidence / "frame-1.json").read_bytes())
    assert call["status"] == "failed" and "raw_response" in call


def test_control_contrasts_change_only_the_declared_factor():
    baseline = module.baseline_specification()[1]
    enum_only = module.specification("enum_false_first")
    enum_only["schema"]["properties"][module.FIELD]["enum"] = [True, False, "unknown"]
    assert enum_only == baseline
    examples = module.specification("examples_false_first")
    assert examples["schema"] == baseline["schema"]
    positive = json.dumps({module.FIELD: True}) + " for visible presence"
    negative = json.dumps({module.FIELD: False}) + " for absence"
    assert (
        examples["prompt"].replace(negative + ", " + positive, positive + ", " + negative)
        == baseline["prompt"]
    )
    neutral = module.specification("neutral_key")
    neutral["fields"] = [module.FIELD]
    neutral["schema"]["properties"] = {module.FIELD: neutral["schema"]["properties"]["answer"]}
    neutral["schema"]["required"] = [module.FIELD]
    neutral["prompt"] = neutral["prompt"].replace(json.dumps("answer"), json.dumps(module.FIELD))
    assert neutral == baseline


@pytest.mark.parametrize("variant", module.VARIANTS)
def test_every_variant_supports_unknown_without_coercion_and_binds_raw_calls(tmp_path, variant):
    image = tmp_path / "image.png"
    Image.new("RGB", (320, 330)).save(image)
    raw = (
        json.dumps({"state": "uncertain", "presented_categories": []})
        if variant == "structured"
        else json.dumps({"answer" if variant == "neutral_key" else module.FIELD: "unknown"})
    )
    evidence = tmp_path / "calls"
    result = module.extract(
        [image],
        [0.2],
        tmp_path,
        variant=variant,
        evidence_dir=evidence,
        invoker=lambda *a, **k: {"raw_response": raw},
    )
    assert module.verify(result, evidence)[module.FIELD] == {"value": "unknown", "frames": []}
    changed = copy.deepcopy(result)
    changed["parsed"][module.FIELD] = {"value": True, "frames": [1]}
    with pytest.raises(ValueError, match="derivation_changed"):
        module.verify(changed, evidence)


def test_incompatible_pixels_never_reach_the_invoker(tmp_path):
    image = tmp_path / "image.png"
    Image.new("RGB", (360, 640)).save(image)

    def forbidden(*args, **kwargs):
        raise AssertionError("incompatible pixels reached the model")

    with pytest.raises(ValueError, match="pixels_changed"):
        module.extract(
            [image],
            [0.2],
            tmp_path,
            variant="structured",
            evidence_dir=tmp_path / "calls",
            invoker=forbidden,
        )


@pytest.mark.parametrize("raw", [None, {"state": "no_target"}, chr(0xD800)])
def test_unusable_native_raw_is_saved_before_encoding_or_parsing(tmp_path, raw):
    image = tmp_path / "image.png"
    Image.new("RGB", (320, 330)).save(image)
    evidence = tmp_path / "calls"
    with pytest.raises(ValueError):
        module.extract(
            [image],
            [0.2],
            tmp_path,
            variant="structured",
            evidence_dir=evidence,
            invoker=lambda *a, **k: {"raw_response": raw},
        )
    receipt = json.loads((evidence / "frame-1.json").read_bytes())
    assert receipt["raw_response"] == raw and receipt["status"] == "failed"

import copy
import json

import pytest
from PIL import Image

from scripts import vlm_explicit_presence as module
from scripts.private_checkpoint import save


def test_literal_contract_and_successful_text_probe_prompt_are_preserved():
    specs = module.specification()
    assert [s["fields"] for s in specs] == [[f] for f in module.BOOLEAN_FIELDS]
    for spec in specs:
        field = spec["fields"][0]
        for value in (True, False, "unknown"):
            assert json.dumps({field: value}) in spec["prompt"]
    assert specs[2]["prompt"] == (
        "Does this image contain any written letters or numbers? Detect presence, even if "
        'the words cannot be read. Return exactly one JSON object: {"screen_text": true} for '
        'visible letters or numbers, {"screen_text": false} for no text, or '
        '{"screen_text": "unknown"} if unsure. Do not transcribe the words.'
    )


def test_frame_local_perception_preserves_single_late_person_and_early_product(tmp_path):
    cells = []
    seconds = [0.2, 1.5, 2.8, 35.72]
    for i in range(4):
        path = tmp_path / f"{i}.png"
        Image.new("RGB", (320, 330)).save(path)
        cells.append(path)
    count = 0

    def invoke(paths, prompt, work, schema, **kwargs):
        nonlocal count
        field = next(iter(schema["properties"]))
        frame = count // 3
        value = (frame == 3) if field == "person_visible" else frame == 0
        if field == "screen_text":
            value = "unknown"
        count += 1
        return {"raw_response": json.dumps({field: value})}

    evidence = tmp_path / "calls"
    result = module.extract(cells, seconds, tmp_path, evidence_dir=evidence, invoker=invoke)
    parsed = module.verify(result, evidence)
    assert count == 12
    assert parsed["person_visible"] == {"value": True, "frames": [4]}
    assert parsed["product_visible_early"] == {"value": True, "frames": [1]}
    assert parsed["screen_text"] == {"value": "unknown", "frames": []}
    corrupted = copy.deepcopy(result)
    corrupted["parsed"]["person_visible"]["frames"] = [1]
    with pytest.raises(ValueError, match="derivation_changed"):
        module.verify(corrupted, evidence)


@pytest.mark.parametrize(
    "raw", ['{"person_visible":true,"person_visible":false}', "prefix {}", '{"person_visible":1}']
)
def test_failed_raw_response_is_retained_and_not_retried(tmp_path, raw):
    path = tmp_path / "frame.png"
    Image.new("RGB", (320, 330)).save(path)
    calls = 0

    def invoke(*args, **kwargs):
        nonlocal calls
        calls += 1
        return {"raw_response": raw}

    evidence = tmp_path / "calls"
    with pytest.raises(ValueError):
        module.extract([path], [0.2], tmp_path, evidence_dir=evidence, invoker=invoke)
    stored = json.loads((evidence / "frame-1-group-1.json").read_bytes())
    assert stored["raw_response"] == raw and stored["status"] == "failed" and calls == 1


def test_bad_pixels_stop_before_model_and_changed_call_is_rejected(tmp_path):
    bad = tmp_path / "bad.png"
    Image.new("RGB", (360, 640)).save(bad)

    def forbidden(*args, **kwargs):
        raise AssertionError("model called for incompatible pixels")

    with pytest.raises(ValueError, match="pixels_changed"):
        module.extract(
            [bad], [0.2], tmp_path, evidence_dir=tmp_path / "bad-calls", invoker=forbidden
        )
    good = tmp_path / "good.png"
    Image.new("RGB", (320, 330)).save(good)

    def invoke(paths, prompt, work, schema, **kwargs):
        return {"raw_response": json.dumps({f: False for f in schema["properties"]})}

    evidence = tmp_path / "calls"
    result = module.extract([good], [0.2], tmp_path, evidence_dir=evidence, invoker=invoke)
    path = evidence / "frame-1-group-3.json"
    changed = json.loads(path.read_bytes())
    changed["input_png_sha256"] = "f" * 64
    save(path, changed)
    with pytest.raises(ValueError, match="call_evidence_changed"):
        module.verify(result, evidence)


def test_pixels_mutated_during_call_halt_and_preserve_raw_output(tmp_path):
    image = tmp_path / "frame.png"
    Image.new("RGB", (320, 330), "black").save(image)
    calls = 0

    def invoke(paths, *args, **kwargs):
        nonlocal calls
        calls += 1
        Image.new("RGB", (320, 330), "white").save(paths[0])
        return {"raw_response": '{"person_visible":false}'}

    evidence = tmp_path / "calls"
    with pytest.raises(ValueError, match="pixels_changed"):
        module.extract([image], [0.2], tmp_path, evidence_dir=evidence, invoker=invoke)
    stored = json.loads((evidence / "frame-1-group-1.json").read_bytes())
    assert calls == 1 and stored["status"] == "failed"
    assert stored["raw_response"] == '{"person_visible":false}'

import copy
import json

import pytest
from PIL import Image

from scripts import vlm_product_v15 as module
from scripts.private_checkpoint import digest


def test_exact_approved_contract_and_projection():
    spec = module.specification()
    assert (
        digest(spec["prompt"]) == "5896b5bf3c9e053c09da1179e11737e0d5b782b524cd179346a94bece1d23d36"
    )
    assert (
        digest(spec["schema"]) == "1ee90e85d7204bbf21c86c7146852fb84fc433e26cc41a7949a90660cf54bfd3"
    )
    assert (
        digest(module.PROJECTION)
        == "958f8d2f25e00d581f3d8bcc80278d78fabd10b6595124451b59c1c2f525adf0"
    )
    assert spec["max_tokens"] == 64 and len(spec["schema"]["oneOf"]) == 10


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
                    "item_configuration": "hand_holds_item_out"
                    if v is True
                    else "unclear"
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

    from scripts.vlm_product_v15_grammar import probes

    schema = module.specification()["schema"]
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    rows = probes()
    domain = [r for r in rows if r["group"] == "finite_domain"]
    assert len(domain) == 13640 and sum(r["expected"] for r in domain) == 22
    for row in domain:
        assert validator.is_valid(json.loads(row["raw"])) == row["expected"]
    for row in rows:
        if row["group"] == "raw_mutation" and row["raw"].startswith(
            '{"state":"no_target","item_configuration"'
        ):
            continue  # Native grammar fixes key order; the semantic decoder does not.
        try:
            module.decode(row["raw"])
            accepted = True
        except ValueError:
            accepted = False
        assert accepted == row["expected"]


def test_old_native_output_is_not_repaired(tmp_path):
    raw = '{"state":"presented_target","presented_categories":["garment"],"presentation_cue":"held_display"}'
    test_failed_raw_is_preserved_without_repair_or_retry(tmp_path, raw)


def test_22_native_objects_project_to_all_16_old_semantic_objects():
    from scripts.vlm_product_v15_grammar import probes

    valid = [
        json.loads(r["raw"]) for r in probes() if r["group"] == "finite_domain" and r["expected"]
    ]
    assert len(valid) == 22
    projected = {digest(module.project(v)) for v in valid}
    assert len(projected) == 16
    for native in valid:
        assert module.decode(json.dumps(native))[0] == native


@pytest.mark.parametrize("tamper", ["native", "derived", "source", "projection"])
def test_native_and_derived_provenance_are_verified(tmp_path, tamper):
    cell = tmp_path / "cell.png"
    Image.new("RGB", (320, 330)).save(cell)
    native = {
        "item_configuration": "hand_holds_hanger_out",
        "state": "presented_target",
        "presented_categories": ["garment"],
    }
    result = module.extract(
        [cell],
        [0.2],
        tmp_path,
        evidence_dir=tmp_path / "calls",
        reserve=lambda i: None,
        invoker=lambda *a, **k: {"raw_response": json.dumps(native)},
    )
    assert module.verify(result, tmp_path / "calls")[module.FIELD]["value"] is True
    changed = copy.deepcopy(result)
    if tamper == "native":
        changed["native_intermediate"][0]["item_configuration"] = "hand_holds_item_out"
    elif tamper == "derived":
        changed["intermediate"][0]["presentation_cue"] = "visible_use"
    elif tamper == "source":
        changed["presentation_cue_source"] = "independent_visual_observation"
    else:
        changed["projection_sha256"] = "changed"
    with pytest.raises(ValueError):
        module.verify(changed, tmp_path / "calls")

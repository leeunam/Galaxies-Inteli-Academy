import copy
import json
import shutil

import pytest
from PIL import Image

from scripts import vlm_per_frame as legacy
from scripts import vlm_prompt_development as module
from scripts import vlm_prompt_plan as planning
from scripts.private_checkpoint import digest, file_hash, save


@pytest.fixture
def campaign(tmp_path, monkeypatch):
    old = {
        "plan_sha256": "a" * 64,
        "cohort_sha256": "b" * 64,
        "partition_sha256": "c" * 64,
        "config": {"frozen": True},
        "rows": [],
    }
    previous = tmp_path / planning.PREVIOUS
    (previous / "images").mkdir(parents=True)
    cache_work = tmp_path / "cache-work"
    cache_work.mkdir()
    annotations = {g: [] for g in ("development", "audit")}

    def invoke(paths, prompt, work, schema, **kwargs):
        with Image.open(paths[0]) as image:
            value = image.getpixel((0, 0)) == (255, 255, 255)
        return {
            "raw_response": json.dumps(
                {
                    f: (value if paths[0].name != "control.png" or f == "screen_text" else False)
                    for f in schema["properties"]
                }
            )
        }

    for group in ("development", "audit"):
        for i in range(32):
            sample = f"{'dv' if group == 'development' else 'au'}{i:09d}"
            sheet = previous / "images" / (sample + ".png")
            positive = i % 2 == 0
            Image.new("RGB", (1280, 360), "white" if positive else "black").save(sheet)
            row = {
                "sample_id": sample,
                "group": group,
                "partition": "train",
                "sector": "beleza" if i < 16 else "moda",
                "channel_id": sample,
                "media_sha256": digest(sample),
                "sheet_sha256": file_hash(sheet),
                "properties": {
                    "duration_seconds": 6,
                    "sampled_frame_seconds": [0.2, 1.5, 2.8, 4.0],
                },
            }
            old["rows"].append(row)
            cells, seconds = module.crops(sheet, cache_work, row)
            identity = {
                "sample_id": sample,
                "group": group,
                "properties": row["properties"],
                "sheet_sha256": row["sheet_sha256"],
                "input_png_sha256": [file_hash(p) for p in cells],
                "input_frame_seconds": seconds,
            }
            save(previous / "sessions" / sample / "features.json", identity)
            for candidate in ("A", "B") if group == "development" else ("A",):
                path = previous / "inferences" / candidate / sample / "result.json"
                result = legacy.extract(
                    cells,
                    seconds,
                    cache_work,
                    candidate=candidate,
                    evidence_dir=path.parent / "calls",
                    invoker=invoke,
                )
                save(
                    path,
                    {
                        "sample_id": sample,
                        "group": group,
                        "plan_sha256": old["plan_sha256"],
                        "config_sha256": digest(old["config"]),
                        "sheet_sha256": row["sheet_sha256"],
                        "vlm": result,
                    },
                )
            fields = {
                f: {
                    "value": positive,
                    "frames": [1, 2, 3] if f == "product_visible_early" else [1, 2, 3, 4],
                }
                for f in legacy.BOOLEAN_FIELDS
            }
            fields |= {f: {"value": "unknown", "frames": []} for f in ("scene", "format")}
            annotations[group].append(
                {"sample_id": sample, "sheet_sha256": row["sheet_sha256"], "fields": fields}
            )
    for group, path in planning.ANNOTATIONS.items():
        save(tmp_path / path, {"rows": annotations[group]})
    monkeypatch.setattr(planning, "prior", lambda *args: (old, {}))
    monkeypatch.setattr(module, "prior", lambda *args: (old, {}))
    monkeypatch.setattr(
        planning,
        "configuration",
        lambda *args: {"controls": planning.controls(), "specification": module.extract.__module__},
    )
    monkeypatch.setattr(module, "prepare_runtime", lambda **kwargs: None)

    def render(row, path):
        Image.new("RGB", (320, 330), "white" if row["text"] else "black").save(path)

    monkeypatch.setattr(module, "render_control", render)

    def acquire_row(media, scratch, row, image):
        image.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(previous / "images" / (row["sample_id"] + ".png"), image)
        return json.loads((previous / "sessions" / row["sample_id"] / "features.json").read_bytes())

    monkeypatch.setattr(module, "acquire_row", acquire_row)

    def download(media, sample):
        media.write_bytes(sample.encode())
        return {"sha256": file_hash(media)}

    folder = tmp_path / "data/private/v8"
    plan = planning.prepare(None, None, folder, tmp_path)
    return tmp_path, folder, plan, old, invoke, download


def controls_and_acquire(campaign, limit=64):
    root, folder, _plan, _old, invoke, download = campaign
    module.infer(None, None, folder, root, limit=12, control=True, invoker=invoke)
    module.acquire(None, None, folder, root, limit=limit, downloader=download)


def test_complete_paired_development_resumption_budget_and_disposal(campaign):
    root, folder, _plan, _old, invoke, download = campaign
    with pytest.raises(ValueError, match="complete_controls_required"):
        module.acquire(None, None, folder, root, limit=1, downloader=download)
    controls_and_acquire(campaign)
    module.infer(None, None, folder, root, limit=1, invoker=invoke)
    with pytest.raises(ValueError, match="complete_64_required"):
        module.compare(None, None, folder, root)
    module.infer(None, None, folder, root, limit=64, invoker=invoke)
    proof = module.compare(None, None, folder, root)
    assert proof["same_pixels_and_times"] and not proof["new_blind_audit"]
    assert proof["released_fields"] == []
    assert proof["fields_ready_for_future_blind_audit"] == list(legacy.BOOLEAN_FIELDS)
    for version in ("v8", "v7_A"):
        for field in legacy.BOOLEAN_FIELDS:
            assert (
                proof["metrics"][version]["all_available"][field]["all"][
                    "correct_value_and_evidence"
                ]
                == 64
            )
    _, state = planning.load(None, None, folder, root)
    assert (
        state["calls_reserved"] == 804
        and len(state["entries"]) == 64
        and state["elapsed_seconds"] > planning.BASE_SECONDS
    )
    before = file_hash(folder / "checkpoint.json")
    with pytest.raises(ValueError, match="halted_no_automatic_retry"):
        module.infer(None, None, folder, root, limit=1, invoker=invoke)
    assert file_hash(folder / "checkpoint.json") == before
    assert module.dispose(None, None, folder, root)["images_removed"] == 64
    planning.load(None, None, folder, root)
    assert not list((folder / "images").glob("*.png"))
    assert not list((root / "data/private/media-temp").glob("galaxies-*"))


def test_checkpoint_cannot_reset_prior_budget_or_duplicate_operations(campaign):
    _root, folder, plan, *_ = campaign
    original = json.loads((folder / "checkpoint.json").read_bytes())
    for field, value in (
        ("prior_acquisitions", 0),
        ("prior_native_calls", 0),
        ("elapsed_seconds", 0),
        ("calls_reserved", 1),
    ):
        state = copy.deepcopy(original)
        state[field] = value
        with pytest.raises(ValueError, match="cumulative_budget_changed"):
            planning.validate_state(plan, state, folder)
    state = copy.deepcopy(original)
    state["controls"] = [{"sample_id": "unknown"}]
    with pytest.raises(ValueError, match="invalid_ledger_keys"):
        planning.validate_state(plan, state, folder)


def test_different_pixels_or_times_stop_before_inference(campaign):
    root, folder, plan, _old, _invoke, _download = campaign
    controls_and_acquire(campaign, limit=1)
    row = plan["rows"][0]
    sidecar = folder / "sessions" / row["sample_id"] / "features.json"
    changed = json.loads(sidecar.read_bytes())
    changed["input_frame_seconds"][0] = 0.21
    save(sidecar, changed)
    state = json.loads((folder / "checkpoint.json").read_bytes())
    state["entries"][0]["files_sha256"]["features.json"] = file_hash(sidecar)
    save(folder / "checkpoint.json", state)
    calls = []

    def forbidden(*args, **kwargs):
        calls.append(True)
        raise AssertionError("model used changed inputs")

    with pytest.raises(ValueError, match="original_pixels_or_times_changed"):
        module.infer(None, None, folder, root, limit=1, invoker=forbidden)
    assert not calls
    state = json.loads((folder / "checkpoint.json").read_bytes())
    assert state["halt_reason"] and state["inferences"][0]["status"] == "failed"
    assert state["calls_reserved"] == 36
    assert not list((root / "data/private/media-temp").glob("galaxies-*"))


def test_failed_model_call_halts_without_replacing_unknown_and_cleans(campaign):
    root, folder, _plan, _old, _invoke, _download = campaign
    controls_and_acquire(campaign, limit=1)
    calls = []

    def malformed(*args, **kwargs):
        calls.append(True)
        return {"raw_response": "not JSON"}

    with pytest.raises(ValueError):
        module.infer(None, None, folder, root, limit=1, invoker=malformed)
    _, state = planning.load(None, None, folder, root)
    assert state["calls_reserved"] == 37 and len(calls) == 1 and state["halt_reason"]
    assert not list((root / "data/private/media-temp").glob("galaxies-*"))
    with pytest.raises(ValueError, match="halted_no_automatic_retry"):
        module.infer(None, None, folder, root, limit=1, invoker=malformed)


def test_group_metrics_do_not_fill_unannotated_frames_or_hide_unknown():
    fields = {
        f: {"value": True, "frames": [4] if f == "person_visible" else [1]}
        for f in legacy.BOOLEAN_FIELDS
    }
    predictions = copy.deepcopy(fields)
    predictions["screen_text"] = {"value": "unknown", "frames": []}
    row = {
        "sector": "moda",
        "predicted": predictions,
        "annotated": fields,
        "per_frame": [{f: "unknown" for f in legacy.BOOLEAN_FIELDS} for _ in range(4)],
    }
    row["per_frame"][3]["person_visible"] = True
    m = module.metrics([row])
    assert m["person_visible"]["all"]["annotated_positive_frames"] == {"true": 1}
    assert m["person_visible"]["all"]["annotated_absent_frames"] == {}
    assert m["screen_text"]["all"]["unknown"] == 1 and m["screen_text"]["all"]["known"] == 0


def test_plan_rows_annotations_and_partition_flags_cannot_change(campaign):
    root, folder, plan, *_ = campaign
    for change in ("row", "annotations", "partition"):
        changed = copy.deepcopy(plan)
        if change == "row":
            changed["rows"][0]["sample_id"] = "reserved000"
        elif change == "annotations":
            changed["annotations"]["audit"] = "data/private/RESERVED.json"
        else:
            changed["partition_sha256"] = "0" * 64
        changed["plan_sha256"] = digest({k: v for k, v in changed.items() if k != "plan_sha256"})
        state = json.loads((folder / "checkpoint.json").read_bytes())
        state["plan_sha256"] = changed["plan_sha256"]
        save(folder / "plan.json", changed)
        save(folder / "checkpoint.json", state)
        with pytest.raises(ValueError, match="plan_or_frozen_inputs_changed"):
            planning.load(None, None, folder, root)


def test_fabricated_previous_receipt_is_refused_before_new_activity(tmp_path, monkeypatch):
    monkeypatch.setattr(planning, "load_previous", lambda *args: ({}, {}))
    path = tmp_path / planning.PREVIOUS / "final-verification.json"
    save(path, {})
    with pytest.raises(ValueError, match="previous_receipts_changed"):
        planning.prior(None, None, tmp_path)


def test_comparison_recovers_file_written_before_checkpoint_without_new_calls(
    campaign, monkeypatch
):
    root, folder, _plan, _old, invoke, _download = campaign
    controls_and_acquire(campaign)
    module.infer(None, None, folder, root, limit=64, invoker=invoke)
    original = module.save

    def crash(path, body):
        if (
            path.name == "checkpoint.json"
            and body.get("halt_reason") == "development_comparison_completed"
        ):
            raise RuntimeError("simulated comparison checkpoint crash")
        return original(path, body)

    monkeypatch.setattr(module, "save", crash)
    with pytest.raises(RuntimeError, match="checkpoint crash"):
        module.compare(None, None, folder, root)
    assert (folder / "comparison.json").is_file()
    monkeypatch.setattr(module, "save", original)
    proof = module.compare(None, None, folder, root)
    assert module.compare(None, None, folder, root) == json.loads(
        (folder / "comparison.json").read_bytes()
    )
    assert proof["released_fields"] == []
    _, state = planning.load(None, None, folder, root)
    assert (
        state["calls_reserved"] == 804
        and state["halt_reason"] == "development_comparison_completed"
    )


def test_disposal_recovers_after_unlink_before_progress_checkpoint(campaign, monkeypatch):
    root, folder, plan, _old, invoke, _download = campaign
    controls_and_acquire(campaign)
    module.infer(None, None, folder, root, limit=64, invoker=invoke)
    module.compare(None, None, folder, root)
    doomed = folder / "images" / (plan["rows"][2]["sample_id"] + ".png")
    original = type(doomed).unlink

    def crash(path, *args, **kwargs):
        output = original(path, *args, **kwargs)
        if path == doomed:
            raise OSError("simulated disposal crash after unlink")
        return output

    monkeypatch.setattr(type(doomed), "unlink", crash)
    with pytest.raises(OSError, match="disposal crash"):
        module.dispose(None, None, folder, root)
    _, state = planning.load(None, None, folder, root)
    assert not state["images_disposed"] and doomed.stem in state["cleanup_pending"]
    assert not doomed.exists()
    monkeypatch.setattr(type(doomed), "unlink", original)
    module.dispose(None, None, folder, root)
    assert module.dispose(None, None, folder, root)["images_removed"] == 64
    _, state = planning.load(None, None, folder, root)
    assert (
        state["images_disposed"]
        and state["cleanup_pending"] == []
        and state["calls_reserved"] == 804
    )


def test_quality_errors_in_controls_are_recorded_without_changing_frozen_prompt(campaign):
    root, folder, _plan, _old, _invoke, download = campaign

    def uncertain(paths, prompt, work, schema, **kwargs):
        return {"raw_response": json.dumps({f: "unknown" for f in schema["properties"]})}

    module.infer(None, None, folder, root, limit=12, control=True, invoker=uncertain)
    state = module.acquire(None, None, folder, root, limit=1, downloader=download)
    assert len(state["entries"]) == 1 and state["calls_reserved"] == 36

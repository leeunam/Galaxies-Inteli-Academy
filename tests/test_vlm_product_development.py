import json

import pytest
from PIL import Image

from scripts import vlm_explicit_presence as cached
from scripts import vlm_per_frame as legacy
from scripts import vlm_product_development as module
from scripts import vlm_product_plan as planning
from scripts.private_checkpoint import digest, file_hash, save
from scripts.vlm_prompt_development import render_control


@pytest.fixture
def campaign(tmp_path, monkeypatch):
    previous = tmp_path / planning.PREVIOUS
    old = {
        "plan_sha256": "a" * 64,
        "cohort_sha256": "b" * 64,
        "partition_sha256": "c" * 64,
        "rows": [],
        "annotations": {},
        "config": {},
    }
    truth = {}
    sheets = tmp_path / "fixtures"
    sheets.mkdir()
    work = tmp_path / "work"
    work.mkdir()

    def cache_invoke(paths, prompt, work, schema, **kwargs):
        with Image.open(paths[0]) as image:
            value = image.getpixel((0, 0)) == (255, 255, 255)
        return {"raw_response": json.dumps({f: value for f in schema["properties"]})}

    for group in ("development", "audit"):
        annotations = []
        negatives = {0, 1, 2} if group == "development" else {0, 1, 2, 16, 17}
        for i in range(32):
            sample = f"{group}-{i}"
            positive = i not in negatives
            truth[sample] = positive
            sheet = sheets / (sample + ".png")
            Image.new("RGB", (1280, 360), "white" if positive else "black").save(sheet)
            row = {
                "sample_id": sample,
                "group": group,
                "partition": "train",
                "sector": "beleza" if i < 16 else "moda",
                "channel_id": sample,
                "sheet_sha256": file_hash(sheet),
                "media_sha256": digest(sample),
                "properties": {
                    "duration_seconds": 6,
                    "sampled_frame_seconds": [0.2, 1.5, 2.8, 4.0],
                },
            }
            old["rows"].append(row)
            cells, seconds = module.crops(sheet, work, row)
            identity = {
                "sample_id": sample,
                "properties": row["properties"],
                "sheet_sha256": row["sheet_sha256"],
                "input_frame_seconds": seconds,
                "input_png_sha256": [file_hash(p) for p in cells],
            }
            save(previous / "sessions" / sample / "features.json", identity)
            save(
                previous / "sessions" / sample / "run.json",
                {"status": "completed", "temporary_directory_removed": True},
            )
            path = previous / "inferences" / sample / "result.json"
            body = cached.extract(
                cells, seconds, work, evidence_dir=path.parent / "calls", invoker=cache_invoke
            )
            save(path, {"sample_id": sample, "sheet_sha256": row["sheet_sha256"], "vlm": body})
            for candidate in ("A", "B") if group == "development" else ("A",):
                path = (
                    tmp_path / planning.LEGACY / "inferences" / candidate / sample / "result.json"
                )
                body = legacy.extract(
                    cells,
                    seconds,
                    work,
                    candidate=candidate,
                    evidence_dir=path.parent / "calls",
                    invoker=cache_invoke,
                )
                save(path, {"sample_id": sample, "sheet_sha256": row["sheet_sha256"], "vlm": body})
            fields = {
                f: {"value": positive, "frames": [1, 2, 3] if f == module.FIELD else [1, 2, 3, 4]}
                for f in legacy.BOOLEAN_FIELDS
            }
            fields |= {f: {"value": "unknown", "frames": []} for f in ("scene", "format")}
            annotations.append(
                {"sample_id": sample, "sheet_sha256": row["sheet_sha256"], "fields": fields}
            )
        ref = f"data/private/{group}-annotations.json"
        old["annotations"][group] = ref
        save(tmp_path / ref, {"rows": annotations})
    for row in planning.controls():
        image = work / "control.png"
        render_control(row, image)
        path = previous / "control-results" / row["sample_id"] / "result.json"
        body = cached.extract(
            [image], [0.0], work, evidence_dir=path.parent / "calls", invoker=cache_invoke
        )
        save(path, {"sample_id": row["sample_id"], "vlm": body})
    monkeypatch.setattr(planning, "prior", lambda *args: (old, {}))
    monkeypatch.setattr(
        planning,
        "configuration",
        lambda *args: {
            "controls": planning.controls(),
            "specifications": {v: planning.specification(v) for v in module.VARIANTS},
        },
    )
    monkeypatch.setattr(module, "prepare_runtime", lambda **kwargs: None)

    def acquire_row(media, scratch, row, image):
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes((sheets / (row["sample_id"] + ".png")).read_bytes())
        return json.loads((previous / "sessions" / row["sample_id"] / "features.json").read_bytes())

    monkeypatch.setattr(module, "acquire_row", acquire_row)

    def download(media, sample):
        media.write_bytes(sample.encode())
        return {"sha256": file_hash(media)}

    def invoke(paths, prompt, work, schema, **kwargs):
        with Image.open(paths[0]) as image:
            positive = image.getpixel((0, 0)) == (255, 255, 255)
        if paths[0].name == "control.png":
            positive = False
        if "state" in schema["properties"]:
            return {
                "raw_response": json.dumps(
                    {
                        "state": "presented_target" if positive else "no_target",
                        "presented_categories": ["cosmetic"] if positive else [],
                    }
                )
            }
        return {"raw_response": json.dumps({next(iter(schema["properties"])): False})}

    folder = tmp_path / "data/private/v9"
    plan = planning.prepare(None, None, folder, tmp_path)
    return tmp_path, folder, plan, invoke, download


def test_complete_product_campaign_preserves_cached_fields_and_seals(campaign, monkeypatch):
    root, folder, plan, invoke, download = campaign
    module.run_controls(None, None, folder, root, limit=48, invoker=invoke)
    module.acquire(None, None, folder, root, limit=64, downloader=download)
    assert len(planning.load(None, None, folder, root)[1]["entries"]) == 16
    module.infer(None, None, folder, root, limit=64, invoker=invoke)
    module.acquire(None, None, folder, root, limit=64, downloader=download)
    module.infer(None, None, folder, root, limit=64, invoker=invoke)
    proof = module.compare(None, None, folder, root)
    assert proof["evaluated_cases"] == 64 and proof["released_fields"] == []
    assert proof["same_pixels_and_times"] and proof["person_text_cache_preserved"]
    assert (
        proof["metrics"]["v9"]["all_available"][module.FIELD]["all"]["correct_value_and_evidence"]
        == 64
    )
    state = planning.load(None, None, folder, root)[1]
    assert state["calls_reserved"] == 304 and len(state["entries"]) == 64
    image = folder / "images" / (plan["rows"][2]["sample_id"] + ".png")
    unlink = type(image).unlink

    def crash(path, *args, **kwargs):
        output = unlink(path, *args, **kwargs)
        if path == image:
            raise OSError("disposal interrupted after unlink")
        return output

    monkeypatch.setattr(type(image), "unlink", crash)
    with pytest.raises(OSError, match="interrupted"):
        module.dispose(None, None, folder, root)
    assert image.name[:-4] in planning.load(None, None, folder, root)[1]["cleanup_pending"]
    monkeypatch.setattr(type(image), "unlink", unlink)
    assert module.dispose(None, None, folder, root)["images_removed"] == 64
    assert not list((folder / "images").glob("*.png"))
    before = file_hash(folder / "checkpoint.json")
    with pytest.raises(ValueError, match="halted"):
        module.infer(None, None, folder, root, limit=1, invoker=invoke)
    assert file_hash(folder / "checkpoint.json") == before


def test_even_rehashed_results_cannot_change_original_timestamps(campaign):
    root, folder, _plan, invoke, download = campaign
    module.run_controls(None, None, folder, root, limit=48, invoker=invoke)
    module.acquire(None, None, folder, root, limit=16, downloader=download)
    module.infer(None, None, folder, root, limit=1, invoker=invoke)
    state = json.loads((folder / "checkpoint.json").read_bytes())
    entry = state["inferences"][0]
    path = planning.result_path(folder, entry["sample_id"])
    body = json.loads(path.read_bytes())
    body["vlm"]["input_frame_seconds"][0] = 0.21
    save(path, body)
    entry["result_sha256"] = file_hash(path)
    save(folder / "checkpoint.json", state)
    with pytest.raises(ValueError, match="original_pixels_or_times_changed"):
        planning.load(None, None, folder, root)


def test_unknown_in_absence_controls_stops_before_any_media(campaign):
    root, folder, _plan, invoke, _download = campaign

    def uncertain(paths, prompt, work, schema, **kwargs):
        if "state" in schema["properties"]:
            return {"raw_response": '{"state":"uncertain","presented_categories":[]}'}
        return invoke(paths, prompt, work, schema, **kwargs)

    module.run_controls(None, None, folder, root, limit=48, invoker=uncertain)

    def forbidden(*args, **kwargs):
        raise AssertionError("media access despite failed absence controls")

    with pytest.raises(ValueError, match="halted"):
        module.acquire(None, None, folder, root, limit=64, downloader=forbidden)
    proof = module.compare(None, None, folder, root)
    assert (
        proof["evaluated_cases"] == 0 and proof["stop_reason"] == "product_controls_absence_failed"
    )
    assert proof["controls"]["structured"] == {"unknown": 12, "correct": 0}
    assert module.dispose(None, None, folder, root)["images_removed"] == 0
    state = planning.load(None, None, folder, root)[1]
    assert not state["entries"] and state["calls_reserved"] == 48 and state["images_disposed"]


def test_budget_plan_and_ledger_cannot_reset_or_change_cohort(campaign):
    root, folder, plan, _invoke, _download = campaign
    initial = json.loads((folder / "checkpoint.json").read_bytes())
    for key, value in (
        ("prior_native_calls", 0),
        ("prior_acquisitions", 0),
        ("elapsed_seconds", 0),
        ("calls_reserved", 1),
        ("acquisition_limit", 999),
    ):
        changed = dict(initial, **{key: value})
        save(folder / "checkpoint.json", changed)
        with pytest.raises(ValueError, match="cumulative_budget_changed"):
            planning.load(None, None, folder, root)
    save(folder / "checkpoint.json", initial)
    changed = json.loads(json.dumps(plan))
    changed["rows"][0]["partition"] = "test"
    changed["plan_sha256"] = digest({k: v for k, v in changed.items() if k != "plan_sha256"})
    initial["plan_sha256"] = changed["plan_sha256"]
    save(folder / "plan.json", changed)
    save(folder / "checkpoint.json", initial)
    with pytest.raises(ValueError, match="plan_or_frozen_inputs_changed"):
        planning.load(None, None, folder, root)


def test_constant_false_candidate_stops_at_the_revealed_pilot(campaign):
    root, folder, _plan, invoke, download = campaign
    module.run_controls(None, None, folder, root, limit=48, invoker=invoke)
    module.acquire(None, None, folder, root, limit=64, downloader=download)
    module.infer(
        None,
        None,
        folder,
        root,
        limit=64,
        invoker=lambda *a, **k: {"raw_response": '{"state":"no_target","presented_categories":[]}'},
    )
    state = planning.load(None, None, folder, root)[1]
    assert state["halt_reason"] == "product_pilot_failed" and len(state["inferences"]) == 16
    with pytest.raises(ValueError, match="halted"):
        module.acquire(None, None, folder, root, limit=64, downloader=download)
    proof = module.compare(None, None, folder, root)
    assert proof["evaluated_cases"] == 16 and proof["pilot"]["continue"] is False
    assert module.dispose(None, None, folder, root)["images_removed"] == 16


def test_failed_raw_call_is_reserved_and_retained_without_retry(campaign):
    root, folder, _plan, _invoke, _download = campaign
    calls = []

    def malformed(*args, **kwargs):
        calls.append(True)
        return {"raw_response": "not JSON"}

    with pytest.raises(ValueError):
        module.run_controls(None, None, folder, root, limit=48, invoker=malformed)
    state = planning.load(None, None, folder, root)[1]
    assert state["calls_reserved"] == 1 and state["controls"][0]["status"] == "failed"
    assert len(calls) == 1 and not list((root / "data/private/media-temp").glob("galaxies-*"))
    proof = module.compare(None, None, folder, root)
    assert len(proof["native_receipt_sha256"]) == 1 and proof["evaluated_cases"] == 0
    assert module.dispose(None, None, folder, root)["images_removed"] == 0
    with pytest.raises(ValueError, match="halted"):
        module.run_controls(None, None, folder, root, limit=48, invoker=malformed)
    assert len(calls) == 1


def test_comparison_recovers_after_receipt_before_checkpoint(campaign, monkeypatch):
    root, folder, _plan, _invoke, _download = campaign

    def negative_or_unknown(paths, prompt, work, schema, **kwargs):
        if "state" in schema["properties"]:
            return {"raw_response": '{"state":"uncertain","presented_categories":[]}'}
        return {"raw_response": json.dumps({next(iter(schema["properties"])): False})}

    module.run_controls(None, None, folder, root, limit=48, invoker=negative_or_unknown)
    original = module.save

    def crash(path, body):
        if path.name == "checkpoint.json" and body.get("halt_reason") == "product_report_sealed":
            raise OSError("comparison checkpoint interrupted")
        return original(path, body)

    monkeypatch.setattr(module, "save", crash)
    with pytest.raises(OSError, match="interrupted"):
        module.compare(None, None, folder, root)
    monkeypatch.setattr(module, "save", original)
    proof = module.compare(None, None, folder, root)
    assert module.compare(None, None, folder, root) == proof
    assert planning.load(None, None, folder, root)[1]["calls_reserved"] == 48


def test_sealed_comparison_needs_its_canonical_digest_before_disposal(campaign):
    root, folder, _plan, invoke, _download = campaign

    def uncertain(paths, prompt, work, schema, **kwargs):
        if "state" in schema["properties"]:
            return {"raw_response": '{"state":"uncertain","presented_categories":[]}'}
        return invoke(paths, prompt, work, schema, **kwargs)

    module.run_controls(None, None, folder, root, limit=48, invoker=uncertain)
    module.compare(None, None, folder, root)
    path = folder / "comparison.json"
    report = json.loads(path.read_bytes())
    report["evaluated_cases"] = 64
    save(path, report)
    state = json.loads((folder / "checkpoint.json").read_bytes())
    state["comparison_file_sha256"] = file_hash(path)
    save(folder / "checkpoint.json", state)
    for operation in (module.compare, module.dispose):
        with pytest.raises(ValueError, match="comparison_evidence_changed"):
            operation(None, None, folder, root)


def test_identity_failure_keeps_the_terminal_acquisition_receipt(campaign, monkeypatch):
    root, folder, _plan, invoke, download = campaign
    module.run_controls(None, None, folder, root, limit=48, invoker=invoke)

    def fail(*args, **kwargs):
        raise ValueError("simulated_identity_failure")

    monkeypatch.setattr(module, "checked_identity", fail)
    with pytest.raises(ValueError, match="identity_failure"):
        module.acquire(None, None, folder, root, limit=1, downloader=download)
    state = planning.load(None, None, folder, root)[1]
    entry = state["entries"][0]
    path = folder / "sessions" / entry["sample_id"] / "run.json"
    assert entry["attempts"][-1]["run_sha256"] == file_hash(path)
    module.compare(None, None, folder, root)
    assert module.dispose(None, None, folder, root)["images_removed"] == 1

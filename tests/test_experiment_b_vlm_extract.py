import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image, ImageDraw

from scripts import experiment_b_vlm_extract as module
from scripts.private_checkpoint import file_hash


def sheet_fixture(tmp_path):
    paths = []
    for i, color in enumerate(("red", "blue")):
        path = tmp_path / f"original-{i}.jpg"
        Image.new("RGB", (288, 512), color).save(path)
        paths.append(path)
    seconds = [0.2, 2.8]
    row = {
        "sample_id": "abcdefghijk",
        "sheet_recipe": {"source_batch": "fullv5", "source_index": 42},
    }
    sheet = Image.new("RGB", (640, 360), "white")
    draw = ImageDraw.Draw(sheet)
    for i, (path, second) in enumerate(zip(paths, seconds)):
        with Image.open(path) as picture:
            picture.thumbnail((320, 330))
            sheet.paste(picture, (i * 320, 25))
        draw.text((320 * i + 4, 4), f"pool 42 / frame {i + 1} @ {second:.3f}s", fill="black")
    target = tmp_path / "frozen.png"
    sheet.save(target)
    row["sheet_sha256"] = file_hash(target)
    return row, paths, seconds, sheet


def test_inputs_are_exact_crops_of_committed_sheet_without_annotation_pixels(tmp_path):
    row, paths, seconds, original = sheet_fixture(tmp_path)
    cells, sheet = module.verified_cells(paths, seconds, row, tmp_path)
    assert file_hash(sheet) == row["sheet_sha256"]
    for i, path in enumerate(cells):
        with Image.open(path) as actual:
            assert actual.format == "PNG" and actual.size == (320, 330)
            assert actual.tobytes() == original.crop((320 * i, 25, 320 * (i + 1), 355)).tobytes()
            # White padding is included; black text at y=4 cannot enter the input.
            assert actual.getpixel((300, 0)) == (255, 255, 255)
            assert actual.getpixel((10, 10)) != (255, 255, 255)


@pytest.mark.parametrize("change", ["hash", "pixel", "time", "label"])
def test_any_commitment_change_is_refused_before_cells_exist(tmp_path, change):
    row, paths, seconds, _ = sheet_fixture(tmp_path)
    if change == "hash":
        row["sheet_sha256"] = "0" * 64
    elif change == "pixel":
        Image.new("RGB", (288, 512), "green").save(paths[0])
    elif change == "time":
        seconds[0] = 1.5
    else:
        row["sheet_recipe"]["source_index"] = 43
    with pytest.raises(ValueError, match="frozen_contact_sheet_pixels_mismatch"):
        module.verified_cells(paths, seconds, row, tmp_path)
    assert not list(tmp_path.glob("vlm-cell-*.png"))


@pytest.mark.parametrize("mismatch", ["properties", "sheet"])
def test_mismatch_never_invokes_vlm_or_publishes_audit_image(tmp_path, monkeypatch, mismatch):
    row, paths, seconds, _ = sheet_fixture(tmp_path)
    props = {"duration_seconds": 10, "sampled_frame_seconds": seconds}
    row |= {"properties": props, "audit": True}
    monkeypatch.setattr(module, "frames_and_properties", lambda *a: (props.copy(), paths))
    monkeypatch.setattr(module, "select_vlm_samples", lambda *a: (paths, seconds))
    if mismatch == "properties":
        row["properties"] = props | {"duration_seconds": 11}
    else:
        row["sheet_sha256"] = "0" * 64
    called = []
    with pytest.raises(ValueError, match="frozen_"):
        module.extract_row(
            tmp_path / "media",
            tmp_path,
            row,
            {},
            tmp_path / "audit.png",
            vlm=lambda *a: called.append(a),
        )
    assert not called and not (tmp_path / "audit.png").exists()


def test_different_container_is_explicit_but_qwen_receives_only_committed_pixels(
    tmp_path, monkeypatch
):
    row, paths, seconds, original = sheet_fixture(tmp_path)
    media = tmp_path / "media"
    media.write_bytes(b"new container")
    props = {"duration_seconds": 10, "sampled_frame_seconds": seconds}
    row |= {
        "properties": props,
        "audit": True,
        "features_sha256": "a" * 64,
        "media_sha256": "b" * 64,
    }
    monkeypatch.setattr(module, "frames_and_properties", lambda *a: (props, paths))
    monkeypatch.setattr(module, "select_vlm_samples", lambda *a: (paths, seconds))
    seen = []

    def vlm(cells, actual_seconds, scratch):
        assert actual_seconds == seconds
        for i, cell in enumerate(cells):
            with Image.open(cell) as picture:
                assert (
                    picture.tobytes() == original.crop((320 * i, 25, 320 * (i + 1), 355)).tobytes()
                )
            seen.append(file_hash(cell))
        return {"approved_for_training": False}

    result = module.extract_row(media, tmp_path, row, {}, tmp_path / "audit.png", vlm=vlm)
    assert result["input_png_sha256"] == seen
    assert result["frozen_media_sha256"] != result["reacquired_media_sha256"]
    assert result["input_policy"] == module.POLICY
    assert result["training_approved"] is False
    assert file_hash(tmp_path / "audit.png") == row["sheet_sha256"]


def test_audit_ids_are_training_only_balanced_deterministic_and_label_blind():
    rows = [
        SimpleNamespace(sample_id=f"{sector}-{i}", sector=sector, partition="train")
        for sector in ("moda", "beleza")
        for i in range(25)
    ]
    reserved = SimpleNamespace(sample_id="reserved", sector="moda", partition="test")
    selected = module.audit_sample(rows + [reserved])
    assert selected == module.audit_sample(list(reversed(rows)) + [reserved])
    assert len(selected) == 32 and "reserved" not in selected
    assert sum(s.startswith("moda-") for s in selected) == 16


def test_checkpoint_halt_prevents_any_runtime_or_network_call(tmp_path, monkeypatch):
    monkeypatch.setattr(module, "load_queue", lambda *a: ({}, {"halt_reason": "blocked"}))
    with pytest.raises(ValueError, match="no_automatic_retry"):
        module.run(tmp_path, tmp_path, tmp_path / "queue", tmp_path, max_videos=1)


def test_real_session_cleanup_and_checkpoint_on_source_failure(tmp_path, monkeypatch):
    row = {"sample_id": "abcdefghijk"}
    state = {"halt_reason": None, "elapsed_seconds": 0.0, "entries": []}
    plan = {"rows": [row], "config": {"model": {}}}
    monkeypatch.setattr(module, "load_queue", lambda *a: (plan, state))
    monkeypatch.setattr("scripts.prepare_gguf_vlm.prepare", lambda **kw: {})
    calls = []

    def downloader(media, sample):
        calls.append(sample)
        media.write_bytes(b"partial private video")
        raise RuntimeError("http_access_denied_or_rate_limited")

    result = module.run(
        tmp_path,
        tmp_path,
        tmp_path / "queue",
        tmp_path,
        max_videos=1,
        downloader=downloader,
    )
    assert calls == [row["sample_id"]]
    assert result["completed"] == 0
    assert result["halt_reason"] == "http_access_denied_or_rate_limited"
    entry = state["entries"][0]
    assert entry["status"] == "failed" and entry["cleanup"] is True
    assert not list((tmp_path / "data/private/media-temp").glob("galaxies-media-*"))
    assert json.loads((tmp_path / "queue/checkpoint.json").read_bytes()) == state


@pytest.mark.parametrize(
    "batch,expected",
    [("sixty", "5 / frame"), ("full", "pool 5 / frame"), (None, "abcdefghijk / 1")],
)
def test_legacy_sheet_recipe_labels_are_explicit(batch, expected):
    annotation = {"source_index": 5}
    if batch:
        annotation["source_batch"] = batch
    assert module.sheet_label(annotation, "abcdefghijk", 0, 0.2).startswith(expected)
    with pytest.raises(ValueError, match="unsupported_frozen_sheet_recipe"):
        module.sheet_label({"source_batch": "new_unsupported"}, "abcdefghijk", 0, 0.2)


@pytest.mark.parametrize("corrupt_hash", [False, True])
def test_prepare_selects_development_before_opening_evidence_and_never_copies_outcomes(
    tmp_path, monkeypatch, corrupt_hash
):
    import hashlib

    rows = [
        SimpleNamespace(
            sample_id=f"sample{i:05d}",
            sector="moda" if i % 2 else "beleza",
            partition="train" if i < 203 else "validation",
            media_sha256="a" * 64,
        )
        for i in range(269)
    ]
    rows += [SimpleNamespace(sample_id="reserved000", partition="test")]
    anchor = SimpleNamespace(cohort_sha256="b" * 64, partition_manifest_sha256="c" * 64)
    monkeypatch.setattr(
        module, "anchored_metadata", lambda *a: (SimpleNamespace(assignments=rows), anchor)
    )
    monkeypatch.setattr(module, "configuration", lambda *a: {"fixture": True})
    monkeypatch.setattr(
        module,
        "prior_budget",
        lambda *a: {
            "path": "fixture",
            "elapsed_seconds": 12.5,
            "acquisitions": 17,
            "acquisition_limit": 286,
        },
    )
    private = tmp_path / "data/private"
    private.mkdir(parents=True)
    index = {"reserved000": {"features_ref": "reserved.json"}}
    for row in rows[:-1]:
        path = private / f"{row.sample_id}.json"
        path.write_text(
            json.dumps(
                {"properties": {"duration_seconds": 10}, "transcript": "NOT COPIED", "target": 999}
            )
        )
        index[row.sample_id] = {
            "features_ref": str(path.relative_to(tmp_path)),
            "curation": {
                "features_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "contact_sheet_sha256": "d" * 64,
            },
        }
    if corrupt_hash:
        index[rows[0].sample_id]["curation"]["features_sha256"] = "0" * 64
    (private / "evidence-index.json").write_text(json.dumps(index))
    original = Path.open
    opened = []

    def checked(path, *args, **kwargs):
        assert path.name not in {"reserved.json", "records.json", "predictor-inputs.json"}
        opened.append(path)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", checked)
    queue = private / "queue"
    if corrupt_hash:
        with pytest.raises(ValueError, match="frozen_development_features_changed"):
            module.prepare(private, private, queue, tmp_path)
        assert not (queue / "plan.json").exists()
    else:
        plan = module.prepare(private, private, queue, tmp_path)
        assert len(plan["rows"]) == 269
        assert len(plan["audit_sample_ids"]) == 32
        assert all(r["partition"] != "test" for r in plan["rows"])
        assert plan["labels_used"] is False
        assert "NOT COPIED" not in json.dumps(plan)
        assert "target" not in json.dumps(plan) and "transcript" not in json.dumps(plan)
        loaded, state = module.load_queue(private, private, queue, tmp_path)
        assert loaded["plan_sha256"] == plan["plan_sha256"] and state["entries"] == []
        reset = dict(state, elapsed_seconds=20)
        checkpoint = queue / "checkpoint.json"
        checkpoint.write_text(json.dumps(reset))
        with pytest.raises(ValueError, match="time_not_accounted"):
            module.load_queue(private, private, queue, tmp_path)
        checkpoint.write_text(json.dumps(state))
        changed = private / f"{rows[0].sample_id}.json"
        changed.write_bytes(changed.read_bytes() + b" ")
        with pytest.raises(ValueError, match="frozen_development_features_changed"):
            module.load_queue(private, private, queue, tmp_path)


def test_total_deadline_cancels_current_session_cleans_up_and_never_starts_next(
    tmp_path, monkeypatch
):
    import time

    state = {"halt_reason": None, "elapsed_seconds": 0.0, "entries": []}
    plan = {
        "rows": [{"sample_id": "abcdefghijk"}, {"sample_id": "lmnopqrstuv"}],
        "config": {"model": {}},
    }
    monkeypatch.setattr(module, "load_queue", lambda *a: (plan, state))
    monkeypatch.setattr("scripts.prepare_gguf_vlm.prepare", lambda **kw: {})
    monkeypatch.setattr(module, "TIME_BUDGET", 0.05)
    calls = []

    def downloader(media, sample):
        calls.append(sample)
        media.write_bytes(b"partial private bytes")
        time.sleep(0.2)
        pytest.fail("deadline did not interrupt the acquisition")

    report = module.run(
        tmp_path, tmp_path, tmp_path / "queue", tmp_path, max_videos=2, downloader=downloader
    )
    assert calls == ["abcdefghijk"]
    assert report["halt_reason"] == "vlm_total_time_budget"
    assert state["entries"][0]["cleanup"] is True
    assert len(state["entries"]) == 1
    assert not list((tmp_path / "data/private/media-temp").glob("galaxies-media-*"))


def test_prior_budget_carries_elapsed_time_and_attempts_and_refuses_changed_receipts(
    tmp_path, monkeypatch
):
    private = tmp_path / "data/private"
    private.mkdir(parents=True)
    checkpoint = private / "old-checkpoint.json"
    checkpoint.write_text(json.dumps({"elapsed_seconds": 12.5, "entries": [{} for _ in range(17)]}))
    receipt = private / "prior-budget.json"
    body = {
        "schema_version": "b-vlm-prior-budget-v1",
        "elapsed_seconds": 12.5,
        "acquisitions": 17,
        "acquisition_limit": 286,
        "entries": [
            {
                "path": str(checkpoint.relative_to(tmp_path)),
                "sha256": file_hash(checkpoint),
                "seconds_field": "elapsed_seconds",
                "seconds": 12.5,
                "acquisitions": 17,
            }
        ],
    }
    receipt.write_text(json.dumps(body))
    monkeypatch.setattr(module, "PRIOR_BUDGET_SHA256", file_hash(receipt))
    previous = module.prior_budget(receipt, tmp_path)
    assert previous["elapsed_seconds"] == 12.5 and previous["acquisitions"] == 17
    assert previous["acquisition_limit"] == 286
    body["elapsed_seconds"] = 0
    receipt.write_text(json.dumps(body))
    with pytest.raises(ValueError, match="not_frozen_provenance"):
        module.prior_budget(receipt, tmp_path)
    body["elapsed_seconds"] = 12.5
    receipt.write_text(json.dumps(body))
    checkpoint.write_bytes(checkpoint.read_bytes() + b" ")
    with pytest.raises(ValueError, match="evidence_changed"):
        module.prior_budget(receipt, tmp_path)


def test_cumulative_acquisition_limit_stops_before_another_download(tmp_path, monkeypatch):
    state = {
        "halt_reason": None,
        "elapsed_seconds": 0.0,
        "entries": [],
        "prior_acquisitions": 286,
        "acquisition_limit": 286,
    }
    plan = {"rows": [{"sample_id": "abcdefghijk"}], "config": {"model": {}}}
    monkeypatch.setattr(module, "load_queue", lambda *a: (plan, state))
    monkeypatch.setattr("scripts.prepare_gguf_vlm.prepare", lambda **kw: {})
    report = module.run(
        tmp_path,
        tmp_path,
        tmp_path / "queue",
        tmp_path,
        max_videos=1,
        downloader=lambda *a: pytest.fail("download despite exhausted quota"),
    )
    assert report["halt_reason"] == "vlm_acquisition_budget" and not state["entries"]


def test_invalid_vlm_response_is_persisted_privately_and_stops_without_retry(tmp_path, monkeypatch):
    from scripts.vlm_frame_evidence import VLMOutputError

    state = {"halt_reason": None, "elapsed_seconds": 0.0, "entries": []}
    plan = {
        "rows": [{"sample_id": "abcdefghijk"}, {"sample_id": "lmnopqrstuv"}],
        "config": {"model": {}},
    }
    monkeypatch.setattr(module, "load_queue", lambda *a: (plan, state))
    monkeypatch.setattr("scripts.prepare_gguf_vlm.prepare", lambda **kw: {})
    evidence = {"raw_response": "{synthetic incomplete", "schema_version": "vlm-rejected-output-v1"}
    calls = []

    def downloader(media, sample):
        calls.append(sample)
        media.write_bytes(b"synthetic media")
        return {"sha256": file_hash(media)}

    def extractor(*args):
        raise VLMOutputError(evidence)

    report = module.run(
        tmp_path,
        tmp_path,
        tmp_path / "queue",
        tmp_path,
        max_videos=2,
        downloader=downloader,
        extractor=extractor,
    )
    assert calls == ["abcdefghijk"] and report["completed"] == 0
    assert report["halt_reason"] == "vlm_invalid_output_after_evidence_deduplication"
    path = tmp_path / "queue/sessions/abcdefghijk/rejected-vlm.json"
    assert json.loads(path.read_bytes()) == evidence
    assert path.stat().st_mode & 0o777 == 0o600
    assert state["entries"][0]["cleanup"] is True
    assert state["entries"][0]["rejected_vlm_sha256"] == file_hash(path)


@pytest.mark.parametrize("folder", ["queue-v2", "different/location"])
def test_v2_always_requires_frozen_prior_budget_even_in_another_folder(
    tmp_path, monkeypatch, folder
):
    monkeypatch.setattr(module, "anchored_metadata", lambda *a: (None, None))
    with pytest.raises(ValueError, match="explicit_prior_budget_required"):
        module.prepare(tmp_path, tmp_path, tmp_path / folder, tmp_path)


def test_fabricated_empty_prior_receipt_cannot_reset_cumulative_budget(tmp_path):
    private = tmp_path / "data/private"
    private.mkdir(parents=True)
    receipt = private / "fabricated.json"
    receipt.write_text(
        json.dumps(
            {
                "schema_version": "b-vlm-prior-budget-v1",
                "entries": [],
                "elapsed_seconds": 0,
                "acquisitions": 0,
                "acquisition_limit": 269,
            }
        )
    )
    with pytest.raises(ValueError, match="not_frozen_provenance"):
        module.prior_budget(receipt, tmp_path)

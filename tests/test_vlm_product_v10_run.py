"""Invented media/outputs only; no network, native model, private data or holdout."""

import copy
import json
import socket
from contextlib import contextmanager

import pytest
from PIL import Image

from scripts import vlm_product_v10_plan as planning
from scripts import vlm_product_v10_run as module
from scripts.private_checkpoint import digest, file_hash
from scripts.vlm_per_frame import BOOLEAN_FIELDS, aggregate
from scripts.vlm_product_v10 import save
from scripts.vlm_prompt_development import render_control
from scripts.vlm_prompt_plan import controls
from scripts.vlm_revision import crops


@pytest.fixture
def campaign(tmp_path, monkeypatch):
    def denied(*args, **kwargs):
        raise AssertionError("network_forbidden")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket, "getaddrinfo", denied)
    work = tmp_path / "work"
    work.mkdir()
    preserved = tmp_path / "data/private/old-preserved"
    source = tmp_path / "data/private/fixtures"
    source.mkdir(parents=True)
    rows, truth, inputs, cached, references = [], {}, {}, {}, {}
    first = [f"preserved-{i}" for i in range(8)]
    second = [f"negative-{i}" for i in range(8)] + [f"beauty-{i}" for i in range(4)]
    for i, sample in enumerate(first + second):
        positive = not sample.startswith("negative")
        sector = "moda" if sample in first or sample in second[6:8] else "beleza"
        sheet = source / f"{sample}.png"
        Image.new("RGB", (1280, 360), "white" if positive else "black").save(sheet)
        row = {
            "sample_id": sample,
            "partition": "train",
            "sector": sector,
            "group": "development" if i % 2 else "audit",
            "sheet_sha256": file_hash(sheet),
            "media_sha256": digest(sample),
            "properties": {"duration_seconds": 6, "sampled_frame_seconds": [0.2, 1.5, 2.8, 4.0]},
        }
        rows.append(row)
        if sample in first:
            image = preserved / "images" / sheet.name
            image.parent.mkdir(parents=True, exist_ok=True)
            image.write_bytes(sheet.read_bytes())
        cells, seconds = crops(sheet, work, row)
        inputs[sample] = {"png_sha256": [file_hash(c) for c in cells], "seconds": seconds}
        frames = [{f: positive for f in BOOLEAN_FIELDS} for _ in cells]
        baseline = {
            "input_png_sha256": inputs[sample]["png_sha256"],
            "input_frame_seconds": seconds,
            "per_frame": frames,
            "parsed": aggregate(frames, seconds),
        }
        cached[sample] = baseline
        truth[sample] = {
            f: {"value": positive, "frames": [1, 2, 3] if f == module.FIELD else [1, 2, 3, 4]}
            for f in BOOLEAN_FIELDS
        }
        truth[sample].update({f: {"value": "unknown", "frames": []} for f in ("scene", "format")})
        old = copy.deepcopy(baseline)
        if sample in first[:5]:
            for frame in old["per_frame"]:
                frame[module.FIELD] = False
            old["parsed"] = aggregate(old["per_frame"], seconds)
        path = preserved / "old-results" / sample / "result.json"
        save(path, {"vlm": old})
        references[sample] = {"path": str(path.relative_to(tmp_path)), "sha256": file_hash(path)}
    for row in controls():
        cell = work / "control.png"
        render_control(row, cell)
        inputs[row["sample_id"]] = {"png_sha256": [file_hash(cell)], "seconds": [0.0]}
    protected = {
        str(p.relative_to(tmp_path)): file_hash(p)
        for directory in (preserved, source)
        for p in directory.rglob("*")
        if p.is_file()
    }
    base = {
        "ancestor_folders": [
            str(preserved.relative_to(tmp_path)),
            "data/private/old-2",
            "data/private/old-3",
        ],
        "preserved_folder": str(preserved.relative_to(tmp_path)),
        "prior_calls": 1666,
        "prior_acquisitions": 256,
        "prior_seconds": 34792.30414601901,
        "phase1_ids": first,
        "phase2_ids": second,
        "rows": rows,
        "truth": truth,
        "inputs": inputs,
        "v9_references": references,
        "protected_sha256": protected,
    }

    def load_base(*args):
        if any(file_hash(tmp_path / n) != h for n, h in protected.items()):
            raise ValueError("protected_evidence_changed")
        return copy.deepcopy(base)

    monkeypatch.setattr(planning, "load_base", load_base)
    monkeypatch.setattr(
        planning,
        "configuration",
        lambda: {"fixture": "frozen", "specification": module.configuration()["specification"]},
    )
    # Capture the real configuration before replacing the runner alias.
    config = planning.configuration()
    monkeypatch.setattr(module, "configuration", lambda: copy.deepcopy(config))
    monkeypatch.setattr(planning, "configuration", lambda: copy.deepcopy(config))
    monkeypatch.setattr(planning, "no_workers", lambda root: None)
    monkeypatch.setattr(module, "no_workers", lambda root: None)
    monkeypatch.setattr(module, "verify_runtime", lambda: None)
    monkeypatch.setattr(
        module,
        "cached_result",
        lambda root, row, candidate=None: copy.deepcopy(cached[row["sample_id"]]),
    )

    def acquire(media, scratch, row, image):
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes((source / image.name).read_bytes())
        expected = inputs[row["sample_id"]]
        return {
            "sample_id": row["sample_id"],
            "properties": row["properties"],
            "sheet_sha256": row["sheet_sha256"],
            "input_png_sha256": expected["png_sha256"],
            "input_frame_seconds": expected["seconds"],
        }

    monkeypatch.setattr(module, "acquire_row", acquire)
    folder = tmp_path / "data/private/v10"
    plan = planning.prepare(None, None, folder, tmp_path)
    calls, downloads = [], []

    def invoke(paths, prompt, work, schema, **kwargs):
        state = json.loads((folder / "checkpoint.json").read_bytes())
        assert state["calls_reserved"] == len(calls) + 1
        assert (folder / "reservations" / f"native-{state['calls_reserved']:04d}.json").exists()
        assert state["operations"][-1]["unmeasured_reserved_seconds"] > 0
        assert state["new_session_seconds"] <= 1800
        assert prompt == planning.specification()["prompt"] and kwargs["max_tokens"] == 64
        calls.append(file_hash(paths[0]))
        with Image.open(paths[0]) as image:
            positive = paths[0].name != "control.png" and image.getpixel((0, 0)) == (255, 255, 255)
        return {
            "raw_response": json.dumps(
                {
                    "state": "presented_target" if positive else "no_target",
                    "presented_categories": ["garment"] if positive else [],
                }
            )
        }

    def download(media, sample):
        state = json.loads((folder / "checkpoint.json").read_bytes())
        assert state["calls_reserved"] >= 44
        assert (
            folder / "reservations" / f"acquisition-{state['acquisitions_reserved']:04d}.json"
        ).exists()
        downloads.append(sample)
        media.write_bytes(b"invented media")
        return {"sha256": file_hash(media)}

    return tmp_path, folder, plan, invoke, download, calls, downloads


def test_complete_two_phases_92_calls_12_downloads_and_preservation(campaign):
    root, folder, plan, invoke, download, calls, downloads = campaign
    report = module.execute(None, None, folder, root, invoker=invoke, downloader=download)
    assert len(calls) == 92 and downloads == plan["base"]["phase2_ids"]
    assert report["evaluated_cases"] == 20 and report["phase1_passed"]
    assert report["panel_descriptive_readiness"] and report["released_fields"] == []
    assert report["cumulative_calls"] == 1758 and report["cumulative_acquisitions"] == 268
    assert report["paired"]["v9"] == {"same_cases": 20, "gains": 5, "losses": 0}
    assert report["paired"]["v7_B_old32"]["same_cases"] == 10
    assert report["person_text_cache_preserved"] and not report["test_evaluated"]
    assert len(list((root / plan["base"]["preserved_folder"] / "images").glob("*.png"))) == 8
    assert not list((folder / "images").glob("*.png"))
    assert json.loads((folder / "disposal.json").read_bytes())["completed"]
    assert planning.load(None, None, folder, root)[1]["sealed"]
    before = file_hash(folder / "checkpoint.json")
    with pytest.raises(ValueError, match="consumed_or_uncertain"):
        module.execute(None, None, folder, root, invoker=invoke, downloader=download)
    assert file_hash(folder / "checkpoint.json") == before and len(calls) == 92


@pytest.mark.parametrize("stage", ["controls", "preserved"])
def test_quality_failure_finishes_block_and_blocks_next_phase(campaign, stage):
    root, folder, _plan, invoke, download, calls, downloads = campaign

    def bad(*args, **kwargs):
        result = invoke(*args, **kwargs)
        if stage == "controls" and len(calls) == 1:
            result["raw_response"] = '{"state":"uncertain","presented_categories":[]}'
        if stage == "preserved" and 12 < len(calls) <= 16:
            result["raw_response"] = '{"state":"incidental_only","presented_categories":[]}'
        return result

    report = module.execute(None, None, folder, root, invoker=bad, downloader=download)
    assert len(calls) == (12 if stage == "controls" else 44)
    assert report["evaluated_cases"] == (0 if stage == "controls" else 8)
    assert report["stop_reason"] == f"v10_{stage}_quality_failed"
    assert not report["phase1_passed"] and not report["panel_descriptive_readiness"]
    assert not downloads and report["released_fields"] == []
    planning.load(None, None, folder, root)


@pytest.mark.parametrize("mode", ["runtime", "json", "unicode"])
def test_native_failure_consumes_once_keeps_raw_and_never_retries(campaign, mode):
    root, folder, _plan, invoke, download, calls, downloads = campaign

    def bad(*args, **kwargs):
        result = invoke(*args, **kwargs)
        if len(calls) == 3:
            if mode == "runtime":
                raise RuntimeError("invented_failure")
            result["raw_response"] = "invalid" if mode == "json" else "\ud800"
        return result

    with pytest.raises((ValueError, RuntimeError, UnicodeError)):
        module.execute(None, None, folder, root, invoker=bad, downloader=download)
    plan, state = planning.load(None, None, folder, root)
    assert len(calls) == state["calls_reserved"] == 3 and not downloads
    last = state["operations"][-1]
    receipt = json.loads(
        (
            planning.result_path(folder, "control", last["sample_id"]).parent / "calls/frame-1.json"
        ).read_bytes()
    )
    assert receipt["status"] == "failed"
    if mode != "runtime":
        assert receipt["raw_response"] == ("invalid" if mode == "json" else "\ud800")
    with pytest.raises(ValueError, match="consumed_or_uncertain"):
        module.execute(None, None, folder, root, invoker=bad, downloader=download)
    assert state["sealed"] and len(calls) == 3 and plan["limits"]["calls"] == 92


@pytest.mark.parametrize("mode", ["download", "identity"])
def test_phase2_failure_stops_before_any_additional_inference(campaign, monkeypatch, mode):
    root, folder, _plan, invoke, download, calls, downloads = campaign

    def bad_download(*args):
        result = download(*args)
        if mode == "download":
            raise RuntimeError("invented_download_failure")
        return result

    original = module.acquire_row
    if mode == "identity":

        def bad_identity(*args):
            body = original(*args)
            body["input_frame_seconds"] = [0.2, 1.5, 2.9, 4.0]
            return body

        monkeypatch.setattr(module, "acquire_row", bad_identity)
    with pytest.raises((ValueError, RuntimeError)):
        module.execute(None, None, folder, root, invoker=invoke, downloader=bad_download)
    _, state = planning.load(None, None, folder, root)
    assert len(calls) == state["calls_reserved"] == 44
    assert len(downloads) == state["acquisitions_reserved"] == 1
    assert state["sealed"]
    assert json.loads((folder / "comparison.json").read_bytes())["evaluated_cases"] == 8
    assert not list((root / "data/private/media-temp").glob("galaxies-*"))


def test_uncertain_operation_is_not_resumed(campaign):
    root, folder, plan, invoke, download, calls, downloads = campaign
    state = json.loads((folder / "checkpoint.json").read_bytes())
    state["operations"].append(
        {
            "kind": "control",
            "sample_id": controls()[0]["sample_id"],
            "status": "running",
            "call_count": 0,
            "seconds": 0.0,
        }
    )
    save(folder / "checkpoint.json", state)
    with pytest.raises(ValueError, match="consumed_or_uncertain"):
        module.execute(None, None, folder, root, invoker=invoke, downloader=download)
    assert not calls and not downloads
    with pytest.raises(ValueError, match="already_consumed"):
        planning.prepare(None, None, folder, root)
    assert state["plan_sha256"] == plan["plan_sha256"]


@pytest.mark.parametrize(
    "tamper", ["plan_limit", "source", "reservation", "raw", "counter", "time", "pixels"]
)
def test_tampering_is_detected_before_further_dispatch(campaign, monkeypatch, tamper):
    root, folder, plan, invoke, download, calls, downloads = campaign
    state = json.loads((folder / "checkpoint.json").read_bytes())
    module.one(
        folder,
        plan,
        state,
        "control",
        controls()[0]["sample_id"],
        root,
        invoker=invoke,
        downloader=download,
    )
    if tamper == "plan_limit":
        body = json.loads((folder / "plan.json").read_bytes())
        body["limits"]["calls"] = 93
        body["plan_sha256"] = digest({k: v for k, v in body.items() if k != "plan_sha256"})
        state["plan_sha256"] = body["plan_sha256"]
        save(folder / "plan.json", body)
    elif tamper == "source":
        monkeypatch.setattr(planning, "configuration", lambda: {"changed": True})
    elif tamper == "reservation":
        (folder / "reservations/native-0001.json").unlink()
    elif tamper == "raw":
        p = (
            planning.result_path(folder, "control", controls()[0]["sample_id"]).parent
            / "calls/frame-1.json"
        )
        body = json.loads(p.read_bytes())
        body["raw_response"] = "modified"
        save(p, body)
    elif tamper == "counter":
        state["calls_reserved"] = state["operations"][0]["call_count"] = 0
    elif tamper == "time":
        state["new_session_seconds"] = 0
    else:
        p = (
            root
            / plan["base"]["preserved_folder"]
            / "images"
            / f"{plan['base']['phase1_ids'][0]}.png"
        )
        p.write_bytes(b"modified")
    save(folder / "checkpoint.json", state)
    with pytest.raises((ValueError, FileNotFoundError)):
        module.execute(None, None, folder, root, invoker=invoke, downloader=download)
    assert len(calls) == 1 and not downloads


def test_remaining_deadline_is_shared_and_conservatively_persisted(campaign, monkeypatch):
    root, folder, plan, _invoke, download, _calls, _downloads = campaign
    state = json.loads((folder / "checkpoint.json").read_bytes())
    state["operations"] = [{"seconds": 1740.0}]
    clock = [0.0]
    limits = []

    @contextmanager
    def deadline(seconds):
        limits.append(seconds)
        yield

    monkeypatch.setattr(module, "deadline", deadline)

    def invoke(*args, **kwargs):
        on_disk = json.loads((folder / "checkpoint.json").read_bytes())
        assert 1740 <= on_disk["new_session_seconds"] <= 1800
        assert on_disk["operations"][-1]["unmeasured_reserved_seconds"] == limits[-1]
        clock[0] += 10
        return {"raw_response": '{"state":"presented_target","presented_categories":["garment"]}'}

    module.one(
        folder,
        plan,
        state,
        "preserved",
        plan["base"]["phase1_ids"][0],
        root,
        invoker=invoke,
        downloader=download,
        clock=lambda: clock[0],
    )
    assert limits == [55, 45, 35, 25]
    assert (
        state["new_session_seconds"] == 1780
        and state["operations"][-1]["unmeasured_reserved_seconds"] == 0
    )


def test_cleanup_journal_cannot_target_preserved_images(campaign):
    root, folder, plan, invoke, download, _calls, _downloads = campaign

    def unknown(*args, **kwargs):
        result = invoke(*args, **kwargs)
        result["raw_response"] = '{"state":"uncertain","presented_categories":[]}'
        return result

    module.execute(None, None, folder, root, invoker=unknown, downloader=download)
    old = (
        root / plan["base"]["preserved_folder"] / "images" / f"{plan['base']['phase1_ids'][0]}.png"
    )
    before = file_hash(old)
    journal = json.loads((folder / "disposal.json").read_bytes())
    journal["images"] = {"../../old-preserved/images/" + old.name: before}
    save(folder / "disposal.json", journal)
    state = planning.load(None, None, folder, root)[1]
    with pytest.raises(ValueError, match="cleanup_scope"):
        module.dispose_new_images(folder, plan, state)
    assert file_hash(old) == before


def test_native_reservation_is_exclusive(campaign):
    _root, folder, _plan, *_rest = campaign
    planning.reserve_record(folder, "native", 1, {"invented": True})
    before = file_hash(folder / "reservations/native-0001.json")
    with pytest.raises(FileExistsError):
        planning.reserve_record(folder, "native", 1, {"invented": False})
    assert file_hash(folder / "reservations/native-0001.json") == before


def test_cleanup_recovers_after_unlink_without_touching_old_images(campaign, monkeypatch):
    root, folder, plan, invoke, download, calls, _downloads = campaign
    original = type(folder).unlink
    interrupted = []

    def unlink(path, *args, **kwargs):
        result = original(path, *args, **kwargs)
        if path.parent == folder / "images" and not interrupted:
            interrupted.append(True)
            raise OSError("invented_interruption_after_unlink")
        return result

    monkeypatch.setattr(type(folder), "unlink", unlink)
    with pytest.raises(OSError, match="after_unlink"):
        module.execute(None, None, folder, root, invoker=invoke, downloader=download)
    plan, state = planning.load(None, None, folder, root)
    assert state["sealed"] and len(calls) == 92
    assert module.dispose_new_images(folder, plan, state)["completed"]
    assert len(list((root / plan["base"]["preserved_folder"] / "images").glob("*.png"))) == 8
    assert not list((folder / "images").glob("*.png"))


def test_even_rehashed_terminal_report_cannot_release_or_change_consumption(campaign):
    root, folder, _plan, invoke, download, calls, _downloads = campaign

    def unknown(*args, **kwargs):
        result = invoke(*args, **kwargs)
        result["raw_response"] = '{"state":"uncertain","presented_categories":[]}'
        return result

    module.execute(None, None, folder, root, invoker=unknown, downloader=download)
    report = json.loads((folder / "comparison.json").read_bytes())
    report["released_fields"] = [module.FIELD]
    report["comparison_sha256"] = digest(
        {k: v for k, v in report.items() if k != "comparison_sha256"}
    )
    save(folder / "comparison.json", report)
    state = json.loads((folder / "checkpoint.json").read_bytes())
    state["comparison_file_sha256"] = file_hash(folder / "comparison.json")
    save(folder / "checkpoint.json", state)
    with pytest.raises(ValueError, match="terminal_scope_changed"):
        planning.load(None, None, folder, root)
    assert len(calls) == 12

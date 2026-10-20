"""Invented media/outputs only; no network, native model, private data or holdout."""

import copy
import json
import socket

import pytest
from PIL import Image

from scripts import vlm_product_v15_plan as planning
from scripts import vlm_product_v15_run as module
from scripts.private_checkpoint import digest, file_hash
from scripts.vlm_per_frame import BOOLEAN_FIELDS, aggregate
from scripts.vlm_product_v15 import save
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
    second = []
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
    control_references = {}
    for row in controls():
        cell = work / "control.png"
        render_control(row, cell)
        inputs[row["sample_id"]] = {"png_sha256": [file_hash(cell)], "seconds": [0.0]}
        reference = source / "controls" / row["sample_id"] / "result.json"
        save(
            reference,
            {
                "vlm": {
                    "input_png_sha256": [file_hash(cell)],
                    "input_frame_seconds": [0.0],
                    "parsed": {module.FIELD: {"value": row["sample_id"] != "black", "frames": [1]}},
                }
            },
        )
        control_references[row["sample_id"]] = {
            "path": str(reference.relative_to(tmp_path)),
            "sha256": file_hash(reference),
        }
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
        "prior_calls": 1799,
        "prior_acquisitions": 256,
        "prior_seconds": 36786.75786307302,
        "phase1_ids": first,
        "phase2_ids": second,
        "rows": rows,
        "truth": truth,
        "inputs": inputs,
        "v9_references": references,
        "v10_references": {n: references[n] for n in first},
        "v11_control_references": control_references,
        "v13_control_references": control_references,
        "v14_control_references": control_references,
        "v14_references": {n: references[n] for n in first},
        "v13_references": {n: references[n] for n in first[:4]},
        "preinspection_sha256": digest("invented inspection"),
        "protected_sha256": protected,
    }

    def load_base(*args):
        if any(file_hash(tmp_path / n) != h for n, h in protected.items()):
            raise ValueError("protected_evidence_changed")
        return copy.deepcopy(base)

    monkeypatch.setattr(planning, "load_base", load_base)
    monkeypatch.setattr(planning, "native_preflight", lambda: {"fixture": "invented native proof"})
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

    folder = tmp_path / "data/private/v15"
    plan = planning.prepare(None, None, folder, tmp_path)
    calls, downloads = [], []

    def invoke(paths, prompt, work, schema, **kwargs):
        state = json.loads((folder / "checkpoint.json").read_bytes())
        assert state["calls_reserved"] == len(calls) + 1
        assert (folder / "reservations" / f"native-{state['calls_reserved']:04d}.json").exists()
        assert state["operations"][-1]["unmeasured_reserved_seconds"] > 0
        assert state["new_session_seconds"] <= 1200
        assert prompt == planning.specification()["prompt"] and kwargs["max_tokens"] == 64
        calls.append(file_hash(paths[0]))
        with Image.open(paths[0]) as image:
            positive = paths[0].name != "control.png" and image.getpixel((0, 0)) == (255, 255, 255)
        return {
            "raw_response": json.dumps(
                {
                    "state": "presented_target" if positive else "no_target",
                    "presented_categories": ["garment"] if positive else [],
                    "item_configuration": "hand_holds_item_out" if positive else "absent",
                }
            )
        }

    def download(*args):
        raise AssertionError("acquisition_forbidden")

    return tmp_path, folder, plan, invoke, download, calls, downloads


def review(campaign, phase, supported=True):
    from scripts.vlm_product_v15_review import METHOD, expected_entries, submit_review

    root, folder, plan, *_ = campaign
    state = planning.load(None, None, folder, root)[1]
    body = {
        "method": METHOD,
        "phase": phase,
        "plan_sha256": plan["plan_sha256"],
        "preinspection_sha256": plan["base"]["preinspection_sha256"],
        "entries": {
            k: v | {"supported": supported, "note": "invented visual support"}
            for k, v in expected_entries(folder, plan, state, phase).items()
        },
    }
    submit_review(folder, plan, state, phase, body)
    return body


def complete(campaign, *, invoker=None):
    root, folder, _plan, invoke, _download, *_ = campaign
    for _ in range(3):
        report = module.execute(None, None, folder, root, invoker=invoker or invoke)
        if report["status"] != "v15_awaiting_cue_review":
            return report
        review(campaign, report["phase"])
    raise AssertionError("review loop did not terminate")


@pytest.mark.parametrize("mode", ["runtime", "json", "unicode"])
def test_native_failure_consumes_once_keeps_raw_and_never_retries(campaign, mode):
    root, folder, _plan, invoke, _download, calls, downloads = campaign

    def bad(*args, **kwargs):
        result = invoke(*args, **kwargs)
        if len(calls) == 3:
            if mode == "runtime":
                raise RuntimeError("invented_failure")
            result["raw_response"] = "invalid" if mode == "json" else "\ud800"
        return result

    with pytest.raises((ValueError, RuntimeError, UnicodeError)):
        module.execute(None, None, folder, root, invoker=bad)
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
        module.execute(None, None, folder, root, invoker=bad)
    assert state["sealed"] and len(calls) == 3 and plan["limits"]["calls"] == 44


def test_uncertain_operation_is_not_resumed(campaign):
    root, folder, plan, invoke, _download, calls, downloads = campaign
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
        module.execute(None, None, folder, root, invoker=invoke)
    assert not calls and not downloads
    with pytest.raises(ValueError, match="already_consumed"):
        planning.prepare(None, None, folder, root)
    assert state["plan_sha256"] == plan["plan_sha256"]


@pytest.mark.parametrize(
    "tamper", ["plan_limit", "source", "reservation", "raw", "counter", "time", "pixels"]
)
def test_tampering_is_detected_before_further_dispatch(campaign, monkeypatch, tamper):
    root, folder, plan, invoke, _download, calls, downloads = campaign
    state = json.loads((folder / "checkpoint.json").read_bytes())
    module.one(
        folder,
        plan,
        state,
        "control",
        controls()[0]["sample_id"],
        root,
        invoker=invoke,
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
        module.execute(None, None, folder, root, invoker=invoke)
    assert len(calls) == 1 and not downloads


def test_native_reservation_is_exclusive(campaign):
    _root, folder, _plan, *_rest = campaign
    planning.reserve_record(folder, "native", 1, {"invented": True})
    before = file_hash(folder / "reservations/native-0001.json")
    with pytest.raises(FileExistsError):
        planning.reserve_record(folder, "native", 1, {"invented": False})
    assert file_hash(folder / "reservations/native-0001.json") == before


def test_even_rehashed_terminal_report_cannot_release_or_change_consumption(campaign):
    root, folder, _plan, invoke, _download, calls, _downloads = campaign

    def unknown(*args, **kwargs):
        result = invoke(*args, **kwargs)
        result["raw_response"] = (
            '{"state":"uncertain","presented_categories":[],"item_configuration":"unclear"}'
        )
        return result

    module.execute(None, None, folder, root, invoker=unknown)
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


def test_cue_review_pause_has_no_acquisition_or_native_retry(campaign):
    root, folder, _plan, invoke, _download, calls, downloads = campaign
    report = module.execute(None, None, folder, root, invoker=invoke)
    assert report == {"status": "v15_awaiting_cue_review", "phase": "phase1"}
    assert len(calls) == 44 and not downloads
    assert module.execute(None, None, folder, root, invoker=invoke) == report
    assert len(calls) == 44 and not downloads
    review(campaign, "phase1", supported=False)
    final = module.execute(None, None, folder, root, invoker=invoke)
    assert final["stop_reason"] == "v15_phase1_quality_failed_configuration_support"
    assert final["phase1_value_and_frames_passed"] and not final["phase1_passed"]
    assert len(calls) == 44 and not downloads


@pytest.mark.parametrize(
    "tamper",
    [
        "missing",
        "cue",
        "configuration",
        "source",
        "projection",
        "categories",
        "pixels",
        "time",
        "result",
        "plan",
        "method",
        "support",
    ],
)
def test_visual_review_cannot_omit_or_rebind_predictions(campaign, tamper):
    from scripts.vlm_product_v15_review import METHOD, expected_entries, submit_review

    root, folder, plan, invoke, _download, calls, downloads = campaign
    module.execute(None, None, folder, root, invoker=invoke)
    state = planning.load(None, None, folder, root)[1]
    body = {
        "method": METHOD,
        "phase": "phase1",
        "plan_sha256": plan["plan_sha256"],
        "preinspection_sha256": plan["base"]["preinspection_sha256"],
        "entries": {
            k: v | {"supported": True, "note": "invented support"}
            for k, v in expected_entries(folder, plan, state, "phase1").items()
        },
    }
    key = next(iter(body["entries"]))
    entry = body["entries"][key]
    if tamper == "missing":
        del body["entries"][key]
    elif tamper == "plan":
        body["plan_sha256"] = "changed"
    elif tamper == "method":
        body["method"] = "blind_certified"
    else:
        field, value = {
            "cue": ("derived_cue", "visible_use"),
            "configuration": ("item_configuration", "hand_holds_hanger_out"),
            "source": ("presentation_cue_source", "independent"),
            "projection": ("projection_sha256", "changed"),
            "categories": ("categories", ["cosmetic"]),
            "pixels": ("input_png_sha256", "changed"),
            "time": ("seconds", 0.21),
            "result": ("result_sha256", "changed"),
            "support": ("supported", 1),
        }[tamper]
        entry[field] = value
    with pytest.raises(ValueError):
        submit_review(folder, plan, state, "phase1", body)
    assert not (folder / "cue-review-phase1.json").exists()
    assert len(calls) == 44 and not downloads


def test_review_is_exclusive_and_hash_checked_before_dispatch(campaign):
    from scripts.vlm_product_v15_review import submit_review

    root, folder, plan, invoke, _download, calls, downloads = campaign
    module.execute(None, None, folder, root, invoker=invoke)
    body = review(campaign, "phase1")
    state = planning.load(None, None, folder, root)[1]
    with pytest.raises(ValueError, match="already_consumed"):
        submit_review(folder, plan, state, "phase1", body)
    path = folder / "cue-review-phase1.json"
    body["entries"][next(iter(body["entries"]))]["supported"] = False
    save(path, body)
    with pytest.raises(ValueError, match="review_changed"):
        module.execute(None, None, folder, root, invoker=invoke)
    assert len(calls) == 44 and not downloads


def test_missing_native_grammar_proof_blocks_prepare(campaign, monkeypatch):
    root, folder, *_ = campaign

    def failed():
        raise ValueError("native_preflight_unavailable")

    # Restore the real configuration path, with the native gate made unavailable.
    from scripts.vlm_product_v15_plan import SOURCES

    monkeypatch.setattr(
        planning, "configuration", lambda: {"sources": SOURCES, "native_preflight": failed()}
    )
    other = folder.parent / "blocked-preflight"
    with pytest.raises(ValueError, match="native_preflight_unavailable"):
        planning.prepare(None, None, other, root)
    assert not (other / "checkpoint.json").exists()


def test_controls_compare_only_matching_cached_inputs(campaign):
    report = complete(campaign)
    comparison = report["control_comparison"]
    assert comparison["counts"]["cache_v11"]["false_correct"] == 1
    assert comparison["counts"]["v15_R"]["false_correct"] == 12
    assert comparison["paired_v15_R_vs_cache_v11"] == {"same_cases": 12, "gains": 11, "losses": 0}
    assert comparison["v12_accepted_results"] == 0
    assert comparison["unavailable_video_caches"] == {"v11": 0, "v12": 0}
    assert comparison["paired_v15_R_vs_cache_v13_R"]["same_cases"] == 12
    assert report["paired"]["v13"] == {"same_cases": 4, "gains": 4, "losses": 0}


def test_complete_only_44_calls_zero_acquisition_and_preservation(campaign):
    root, folder, _plan, invoke, _download, calls, downloads = campaign
    report = complete(campaign)
    assert len(calls) == 44 and not downloads
    assert report["evaluated_cases"] == 8 and report["phase1_passed"]
    assert not report["panel_descriptive_readiness"] and report["released_fields"] == []
    assert report["cumulative_calls"] == 1843 and report["cumulative_acquisitions"] == 256
    assert report["paired"]["v14"] == {"same_cases": 8, "gains": 5, "losses": 0}
    assert report["person_text_cache_preserved"] and not report["test_evaluated"]
    assert not (folder / "images").exists() and not (folder / "sessions").exists()
    assert planning.load(None, None, folder, root)[1]["sealed"]
    with pytest.raises(ValueError, match="consumed_or_uncertain"):
        module.execute(None, None, folder, root, invoker=invoke)
    assert len(calls) == 44


@pytest.mark.parametrize("stage", ["control", "preserved"])
def test_quality_failure_finishes_block_and_legacy_failure_still_requires_review(campaign, stage):
    root, folder, _plan, invoke, _download, calls, downloads = campaign

    def bad(*args, **kwargs):
        result = invoke(*args, **kwargs)
        if (stage == "control" and len(calls) == 1) or (
            stage == "preserved" and 12 < len(calls) <= 16
        ):
            result["raw_response"] = (
                '{"item_configuration":"unclear","state":"uncertain","presented_categories":[]}'
            )
        return result

    report = module.execute(None, None, folder, root, invoker=bad)
    if stage == "preserved":
        assert report["status"] == "v15_awaiting_cue_review"
        review(campaign, "phase1")
        report = module.execute(None, None, folder, root, invoker=bad)
        assert "legacy_value_and_frames" in report["stop_reason"]
    else:
        assert report["stop_reason"] == "v15_controls_quality_failed"
    assert len(calls) == (12 if stage == "control" else 44) and not downloads
    assert not report["phase1_passed"]
    planning.load(None, None, folder, root)


@pytest.mark.parametrize("tamper", ["counter", "reservation", "directory", "operation"])
def test_any_acquisition_path_is_rejected_before_dispatch(campaign, tamper):
    root, folder, plan, invoke, _download, calls, downloads = campaign
    state = json.loads((folder / "checkpoint.json").read_bytes())
    if tamper == "counter":
        state["acquisitions_reserved"] = 1
        save(folder / "checkpoint.json", state)
    elif tamper == "reservation":
        path = folder / "reservations/acquisition-0001.json"
        save(path, {"unauthorized": True})
    elif tamper == "directory":
        (folder / "sessions").mkdir()
    else:
        with pytest.raises(ValueError):
            module.one(
                folder,
                plan,
                state,
                "acquisition",
                plan["base"]["phase1_ids"][0],
                root,
                invoker=invoke,
            )
        return
    with pytest.raises(ValueError):
        module.execute(None, None, folder, root, invoker=invoke)
    assert not calls and not downloads

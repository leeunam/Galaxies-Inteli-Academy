import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from PIL import Image

from scripts import vlm_revision as module
from scripts import vlm_revision_plan as planning
from scripts.private_checkpoint import digest, file_hash, save
from scripts.vlm_per_frame import BOOLEAN_FIELDS


def assignments():
    old, rows = [], []
    for i in range(32):
        sample = f"dv{i:09d}"
        old.append(sample)
        rows.append(
            SimpleNamespace(
                sample_id=sample,
                channel_id=f"old-{i}",
                media_sha256=digest(sample),
                sector="beleza" if i < 16 else "moda",
                partition="train",
            )
        )
    for sector in ("beleza", "moda"):
        for i in range(48):
            sample = f"{'be' if sector == 'beleza' else 'mo'}{i:09d}"
            rows.append(
                SimpleNamespace(
                    sample_id=sample,
                    channel_id=f"new-{sector}-{i // 2}",
                    media_sha256=digest(sample),
                    sector=sector,
                    partition="train",
                )
            )
    return old, rows


def test_fresh_sample_is_training_only_excludes_old_channels_and_samples_channels_first():
    old, rows = assignments()

    class Reserved:
        sample_id = "reserved000"
        partition = "test"

        def __getattr__(self, name):
            raise AssertionError("reserved properties accessed during sampling")

    selected = planning.fresh_sample(rows + [Reserved()], old)
    assert selected == planning.fresh_sample(list(reversed(rows)) + [Reserved()], old)
    lookup = {r.sample_id: r for r in rows}
    channels = {lookup[s].channel_id for s in selected}
    assert len(selected) == len(channels) == 32 and not set(selected) & set(old)
    assert sum(lookup[s].sector == "beleza" for s in selected) == 16
    expanded = rows + [
        SimpleNamespace(
            sample_id=f"extra-{i}",
            channel_id="new-beleza-0",
            media_sha256=digest(f"extra-{i}"),
            sector="beleza",
            partition="train",
        )
        for i in range(100)
    ]
    lookup.update({r.sample_id: r for r in expanded})
    assert {lookup[s].channel_id for s in planning.fresh_sample(expanded, old)} == channels


def test_old_channel_or_duplicate_media_cannot_enter_new_audit():
    old, rows = assignments()
    selected = planning.fresh_sample(rows, old)
    by_id = {r.sample_id: r for r in rows}
    by_id[selected[0]].channel_id = rows[0].channel_id
    by_id[selected[1]].media_sha256 = rows[0].media_sha256
    revised = planning.fresh_sample(rows, old)
    assert selected[0] not in revised and selected[1] not in revised
    with pytest.raises(ValueError, match="fresh_training_channels"):
        planning.fresh_sample(rows[:32], old)


def test_prior_budget_refuses_fabricated_provenance(tmp_path):
    folder = tmp_path / planning.OLD
    folder.mkdir(parents=True)
    (folder / "final-verification.json").write_text("{}")
    with pytest.raises(ValueError, match="previous_vlm_final_evidence_changed"):
        planning.prior(tmp_path)


def test_prepare_opens_only_selected_training_evidence(tmp_path, monkeypatch):
    old, rows = assignments()
    rows.append(SimpleNamespace(sample_id="reserved000", partition="test"))
    old_folder = tmp_path / planning.OLD
    old_folder.mkdir(parents=True)
    for name in (
        "blind-annotations-v3.json",
        "quality-release-v3.json",
        "final-verification.json",
        "queue-v3/checkpoint.json",
    ):
        path = old_folder / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}")
    (old_folder / "queue-v3/plan.json").write_text(
        json.dumps({"audit_sample_ids": old, "config": {"sources_sha256": {}}})
    )
    private = tmp_path / "data/private/fixture"
    private.mkdir(parents=True)
    index = {"reserved000": {"features_ref": "data/private/RESERVED.json"}}
    for r in rows[:-1]:
        path = private / f"{r.sample_id}.json"
        path.write_text(
            json.dumps(
                {
                    "properties": {
                        "duration_seconds": 5,
                        "sampled_frame_seconds": [0.2, 1.5, 2.8, 3.0],
                    },
                    "transcript": "MUST NOT ENTER PLAN",
                    "target": 9999,
                }
            )
        )
        index[r.sample_id] = {
            "features_ref": str(path.relative_to(tmp_path)),
            "curation": {"features_sha256": file_hash(path), "contact_sheet_sha256": "b" * 64},
        }
    (private / "evidence-index.json").write_text(json.dumps(index))
    script_dir = tmp_path / "scripts"
    script_dir.mkdir()
    for name in (
        "experiment_b_vlm_quality.py",
        "experiment_b_vlm_data.py",
        "experiment_b_vlm_artifact.py",
        "train_experiment_b_vlm.py",
    ):
        (script_dir / name).write_text("# frozen fixture")
    anchor = SimpleNamespace(cohort_sha256="c" * 64, partition_manifest_sha256="d" * 64)
    monkeypatch.setattr(
        planning, "anchored_metadata", lambda *a: (SimpleNamespace(assignments=rows), anchor)
    )
    monkeypatch.setattr(planning, "prior", lambda *a: {"frozen_file_sha256": {}})
    monkeypatch.setattr(planning, "configuration", lambda *a: {"synthetic": True})
    opened = []
    original = Path.open

    def checked(path, *args, **kwargs):
        assert path.name not in {"RESERVED.json", "records.json", "predictor-inputs.json"}
        opened.append(path)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", checked)
    folder = tmp_path / "data/private/revision"
    plan = planning.prepare(private, private, folder, tmp_path)
    assert len(plan["rows"]) == 64 and all(r["partition"] == "train" for r in plan["rows"])
    assert "MUST NOT ENTER PLAN" not in json.dumps(plan) and "target" not in json.dumps(plan)
    loaded, state = planning.load(private, private, folder, tmp_path)
    assert loaded == plan and state["elapsed_seconds"] == planning.BASE_SECONDS
    state["elapsed_seconds"] = 0
    with pytest.raises(ValueError, match="cumulative_budget_changed"):
        planning.validate_state(plan, state, folder)


@pytest.fixture
def lifecycle(tmp_path, monkeypatch):
    folder = tmp_path / "data/private/revision"
    (folder / "images").mkdir(parents=True)
    plan = {"plan_sha256": "a" * 64, "config": {"synthetic": True}, "rows": []}
    state = {
        "plan_sha256": plan["plan_sha256"],
        "entries": [],
        "inferences": [],
        "prior_acquisitions": 54,
        "acquisition_limit": 128,
        "elapsed_seconds": planning.BASE_SECONDS,
        "dns_retries_used": 0,
        "calls_reserved": 0,
        "halt_reason": None,
        "images_disposed": False,
    }
    annotations = {"development": [], "audit": []}
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    for group in ("development", "audit"):
        for i in range(32):
            sample = f"{'dv' if group == 'development' else 'au'}{i:09d}"
            sheet = folder / "images" / f"{sample}.png"
            positive = i % 2 == 0
            Image.new("RGB", (1280, 360), "white" if positive else "black").save(sheet)
            row = {
                "sample_id": sample,
                "sector": "beleza" if i < 16 else "moda",
                "partition": "train",
                "group": group,
                "sheet_sha256": file_hash(sheet),
                "properties": {
                    "duration_seconds": 6,
                    "sampled_frame_seconds": [0.2, 1.5, 2.8, 4.0],
                },
            }
            plan["rows"].append(row)
            paths, _seconds = module.crops(sheet, scratch, row)
            session = folder / "sessions" / sample
            session.mkdir(parents=True)
            save(session / "features.json", {"input_png_sha256": [file_hash(p) for p in paths]})
            save(session / "run.json", {"temporary_directory_removed": True, "status": "completed"})
            state["entries"].append(
                {
                    "sample_id": sample,
                    "status": "completed",
                    "seconds": 0.0,
                    "attempts": [{"status": "completed", "seconds": 0.0}],
                    "files_sha256": {
                        n: file_hash(session / n) for n in ("features.json", "run.json")
                    },
                }
            )
            fields = {
                f: {
                    "value": positive,
                    "frames": [1, 2, 3] if f == "product_visible_early" else [1, 2, 3, 4],
                }
                for f in BOOLEAN_FIELDS
            }
            fields |= {
                "scene": {"value": "unknown", "frames": []},
                "format": {"value": "unknown", "frames": []},
            }
            annotations[group].append(
                {"sample_id": sample, "sheet_sha256": row["sheet_sha256"], "fields": fields}
            )
    old_folder = tmp_path / planning.OLD
    old_folder.mkdir(parents=True)
    save(old_folder / "blind-annotations-v3.json", {"rows": annotations["development"]})
    plan["old_annotations_sha256"] = file_hash(old_folder / "blind-annotations-v3.json")
    annotation_path = folder / "blind.json"
    save(
        annotation_path,
        {
            "schema_version": "b-vlm-blind-annotations-v1",
            "plan_sha256": plan["plan_sha256"],
            "blind_to_vlm_outputs": True,
            "blind_to_outcomes": True,
            "human_review": False,
            "rows": annotations["audit"],
        },
    )

    def load(*args):
        planning.validate_state(plan, state, folder)
        return plan, state

    monkeypatch.setattr(module, "load", load)
    monkeypatch.setattr(module, "prepare_runtime", lambda **kwargs: None)

    def invoker(paths, prompt, work, schema, **kwargs):
        assert len(paths) == 1
        with Image.open(paths[0]) as image:
            value = image.getpixel((0, 0)) == (255, 255, 255)
        return {
            "raw_response": json.dumps({f: value for f in schema["properties"]}),
            "runtime_seconds": 0.01,
        }

    return folder, plan, state, annotation_path, invoker


def test_complete_develop_freeze_blind_gate_and_disposal_flow(lifecycle, tmp_path):
    folder, plan, state, annotations, invoker = lifecycle
    module.infer(
        None, None, folder, tmp_path, group="development", candidate="A", limit=1, invoker=invoker
    )
    with pytest.raises(ValueError, match="complete_development_pairs"):
        module.freeze(None, None, folder, tmp_path)
    module.infer(
        None, None, folder, tmp_path, group="development", candidate="A", limit=32, invoker=invoker
    )
    module.infer(
        None, None, folder, tmp_path, group="development", candidate="B", limit=32, invoker=invoker
    )
    frozen = module.freeze(None, None, folder, tmp_path)
    assert frozen["candidate"] == "A" and all(
        v["correct"] == 96 for v in frozen["development_scores"].values()
    )
    with pytest.raises(ValueError, match="requires_frozen_candidate"):
        module.infer(
            None, None, folder, tmp_path, group="audit", candidate="B", limit=1, invoker=invoker
        )
    module.infer(
        None, None, folder, tmp_path, group="audit", candidate="A", limit=32, invoker=invoker
    )
    proof = module.publish(None, None, folder, tmp_path, annotations)
    assert proof["released_fields"] == list(BOOLEAN_FIELDS)
    assert state["calls_reserved"] == 640 and proof["test_evaluated"] is False
    assert state["halt_reason"] == "audit_completed_columns_released"
    with pytest.raises(ValueError, match="halted_no_automatic_retry"):
        module.infer(
            None, None, folder, tmp_path, group="audit", candidate="A", limit=1, invoker=invoker
        )
    assert module.dispose(None, None, folder, tmp_path)["images_removed"] == 64
    planning.validate_state(plan, state, folder)
    assert not list((folder / "images").glob("*.png"))


def test_invalid_inference_stops_without_retry_and_retains_raw_before_validation(
    lifecycle, tmp_path
):
    folder, _, state, _, _ = lifecycle
    with pytest.raises(ValueError):
        module.infer(
            None,
            None,
            folder,
            tmp_path,
            group="development",
            candidate="A",
            limit=32,
            invoker=lambda *a, **kw: {"raw_response": "{incomplete"},
        )
    assert state["calls_reserved"] == 1 and state["halt_reason"]
    assert state["inferences"][0]["status"] == "failed"
    raw = folder / "inferences/A/dv000000000/calls/frame-1-group-1.json"
    assert json.loads(raw.read_bytes())["raw_response"] == "{incomplete"
    assert not list((tmp_path / "data/private/media-temp").glob("galaxies-inference-*"))


def test_audit_without_freeze_or_pending_media_never_starts_model(lifecycle, tmp_path, monkeypatch):
    folder, _, _, _, invoker = lifecycle
    monkeypatch.setattr(
        module, "prepare_runtime", lambda **kw: pytest.fail("model prepared before gate")
    )
    with pytest.raises(ValueError, match="requires_frozen_candidate"):
        module.infer(
            None, None, folder, tmp_path, group="audit", candidate="A", limit=1, invoker=invoker
        )
    (tmp_path / "data/private/media-temp/galaxies-media-pending").mkdir(parents=True)
    with pytest.raises(ValueError, match="temporary_session_requires_audit"):
        module.infer(
            None,
            None,
            folder,
            tmp_path,
            group="development",
            candidate="A",
            limit=1,
            invoker=invoker,
        )


@pytest.mark.parametrize(
    "change", ["time_reset", "call_reset", "attempt_status", "missing_run_hash", "image_pixel"]
)
def test_checkpoint_and_image_corruption_are_refused(lifecycle, change):
    folder, plan, state, _, _ = lifecycle
    bad = copy.deepcopy(state)
    if change == "time_reset":
        bad["elapsed_seconds"] = 0
    elif change == "call_reset":
        bad["calls_reserved"] = True
    elif change == "attempt_status":
        bad["entries"][0]["attempts"][0]["status"] = "failed"
    elif change == "missing_run_hash":
        del bad["entries"][0]["files_sha256"]["run.json"]
    else:
        (folder / "images/dv000000000.png").write_bytes(b"changed image")
    with pytest.raises(ValueError):
        planning.validate_state(plan, bad, folder)


def test_source_failure_cleans_real_session_and_prevents_second_download(tmp_path, monkeypatch):
    folder = tmp_path / "data/private/revision"
    plan = {"rows": [{"sample_id": "dv000000000", "group": "development"}]}
    state = {
        "entries": [],
        "inferences": [],
        "halt_reason": None,
        "images_disposed": False,
        "elapsed_seconds": planning.BASE_SECONDS,
        "prior_acquisitions": 54,
        "acquisition_limit": 128,
        "dns_retries_used": 0,
    }
    monkeypatch.setattr(module, "load", lambda *a: (plan, state))
    calls = []

    def fail(media, sample):
        media.write_bytes(b"partial private input")
        calls.append(sample)
        raise RuntimeError("http_access_denied_or_rate_limited")

    with pytest.raises(RuntimeError):
        module.acquire(None, None, folder, tmp_path, group="development", limit=32, downloader=fail)
    assert calls == ["dv000000000"] and state["halt_reason"]
    assert state["entries"][0]["attempts"][0]["cleanup"] is True
    assert not list((tmp_path / "data/private/media-temp").glob("galaxies-media-*"))

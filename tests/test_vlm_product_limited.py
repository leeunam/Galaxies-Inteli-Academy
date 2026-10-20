"""Synthetic queues only; no real media, weights, network or reserved test."""

import copy
import json

import pytest

from scripts.private_checkpoint import file_hash, save
from tests.test_vlm_product_development import campaign  # noqa: F401
from tests.test_vlm_product_recovery import interrupted, recovery_queue  # noqa: F401


def test_property_differences_keep_exact_values_and_list_positions():
    from scripts.vlm_product_limited import property_differences

    old = {"width": 720, "seconds": [0.2, 1.5], "removed": True}
    new = {"width": 720, "seconds": [0.2, 1.50001], "added": "x"}
    assert property_differences(old, new) == [
        {
            "path": ["added"],
            "frozen_present": False,
            "observed_present": True,
            "frozen": None,
            "observed": "x",
        },
        {
            "path": ["removed"],
            "frozen_present": True,
            "observed_present": False,
            "frozen": True,
            "observed": None,
        },
        {
            "path": ["seconds", 1],
            "frozen_present": True,
            "observed_present": True,
            "frozen": 1.5,
            "observed": 1.50001,
        },
    ]
    assert property_differences(old, copy.deepcopy(old)) == []


@pytest.fixture
def limited_queue(recovery_queue, monkeypatch):  # noqa: F811
    from scripts import vlm_product_limited as limited
    from scripts import vlm_product_limited_plan as planning
    from scripts import vlm_product_recovery as recovery
    from scripts import vlm_product_recovery_compare as comparison

    root, old, recovery_folder, recovery_plan, invoke, download = recovery_queue
    recovery.acquire(None, None, recovery_folder, root, limit=1, downloader=download)
    recovery.infer(None, None, recovery_folder, root, limit=1, invoker=invoke)
    target = recovery_plan["pending_ids"][8]
    original = recovery.acquire_row

    def acquire(media, work, row, image):
        if row["sample_id"] == target:
            raise ValueError("revision_frozen_properties_mismatch")
        return original(media, work, row, image)

    monkeypatch.setattr(recovery, "acquire_row", acquire)
    with pytest.raises(ValueError, match="frozen_properties"):
        recovery.acquire(None, None, recovery_folder, root, limit=8, downloader=download)
    comparison.compare(None, None, recovery_folder, root)
    current = json.loads((recovery_folder / "checkpoint.json").read_bytes())
    monkeypatch.setattr(planning, "BASE_SECONDS", current["elapsed_seconds"])
    monkeypatch.setattr(
        planning, "RECOVERY_CHECKPOINT_SHA", file_hash(recovery_folder / "checkpoint.json")
    )
    monkeypatch.setattr(planning, "no_workers", lambda root: None)
    monkeypatch.setattr(limited, "no_workers", lambda root: None)
    monkeypatch.setattr(limited, "verify_runtime", lambda: None)
    folder = root / "data/private/limited"
    plan = planning.prepare(None, None, recovery_folder, folder, root)
    row = next(r for r in plan["rows"] if r["sample_id"] == target)

    def properties(media, work):
        assert media.is_file()
        observed = copy.deepcopy(row["properties"])
        observed["duration_seconds"] += 0.25
        return observed, []

    monkeypatch.setattr(limited, "frames_and_properties", properties)
    return root, old, recovery_folder, folder, plan, invoke, download


def test_diagnostic_then_exactly_28_calls_preserves_sealed_queues(limited_queue):
    from scripts import vlm_product_limited as limited
    from scripts import vlm_product_limited_compare as comparison
    from scripts import vlm_product_limited_plan as planning

    root, old, recovery, folder, plan, invoke, download = limited_queue
    before = {
        str(p): file_hash(p)
        for base in (old, recovery)
        for p in base.rglob("*")
        if p.is_file() and p.name != ".lock"
    }
    downloads, calls = [], []

    def downloader(media, sample):
        state = json.loads((folder / "checkpoint.json").read_bytes())
        assert state["diagnostic"]["status"] == "running"
        downloads.append(sample)
        return download(media, sample)

    state = limited.diagnose(None, None, folder, root, downloader=downloader)
    assert state["diagnostic"]["status"] == "completed"
    observed = json.loads((folder / "diagnostic/observed-properties.json").read_bytes())
    features = json.loads((folder / "diagnostic/features.json").read_bytes())
    assert (
        observed["properties"]["duration_seconds"]
        == features["frozen_properties"]["duration_seconds"] + 0.25
    )
    assert features["properties_equal"] is False
    assert features["identity_approved"] is False and features["vlm_called"] is False
    assert observed["media_sha256"] == features["media_sha256"]
    assert "decoder_versions" in observed and "failed_recovery_media_sha256" in features

    def invoker(*args, **kwargs):
        state = json.loads((folder / "checkpoint.json").read_bytes())
        assert state["calls_reserved"] == len(calls) + 1
        assert state["inferences"][-1]["call_count"] == len(calls) % 4 + 1
        calls.append(True)
        return invoke(*args, **kwargs)

    state = limited.infer(None, None, folder, root, invoker=invoker)
    assert len(calls) == 28 and downloads == [plan["diagnostic_id"]]
    assert [e["sample_id"] for e in state["inferences"]] == plan["inference_ids"]
    report = comparison.compare(None, None, folder, root)
    assert report["evaluated_cases"] == 41
    assert report["cumulative_acquisitions"] == 256
    assert report["cumulative_native_reservations"] == 1666
    assert report["released_fields"] == []
    assert comparison.compare(None, None, folder, root) == report
    assert {
        str(p): file_hash(p)
        for base in (old, recovery)
        for p in base.rglob("*")
        if p.is_file() and p.name != ".lock"
    } == before
    assert len(list((recovery / "images").glob("*.png"))) == 8
    assert not list((root / "data/private/media-temp").glob("galaxies-*"))
    assert planning.load(None, None, folder, root)[1]["halt_reason"] == "limited_report_sealed"
    for operation in (limited.diagnose, limited.infer):
        with pytest.raises(ValueError, match="halted"):
            operation(None, None, folder, root)


@pytest.mark.parametrize("stage", ["download", "native", "json"])
def test_failures_consume_once_and_stop_without_retry(limited_queue, stage):
    from scripts import vlm_product_limited as limited
    from scripts import vlm_product_limited_compare as comparison
    from scripts import vlm_product_limited_plan as planning

    root, _old, _recovery, folder, _plan, _invoke, download = limited_queue
    calls = []

    def fail(*args, **kwargs):
        calls.append(True)
        if stage == "json":
            return {"raw_response": "not JSON"}
        raise TimeoutError("synthetic_timeout")

    if stage == "download":
        operation, args = limited.diagnose, {"downloader": fail}
    else:
        limited.diagnose(None, None, folder, root, downloader=download)
        operation, args = limited.infer, {"invoker": fail}
    with pytest.raises((ValueError, TimeoutError)):
        operation(None, None, folder, root, **args)
    state = planning.load(None, None, folder, root)[1]
    assert len(calls) == 1
    assert state["calls_reserved"] == (0 if stage == "download" else 1)
    assert state["diagnostic"] is not None
    for operation in (limited.diagnose, limited.infer):
        with pytest.raises(ValueError, match="halted"):
            operation(None, None, folder, root)
    assert comparison.compare(None, None, folder, root)["evaluated_cases"] == 34
    assert not list((root / "data/private/media-temp").glob("galaxies-*"))


def test_inference_before_diagnostic_is_forbidden(limited_queue):
    from scripts import vlm_product_limited as limited

    root, _old, _recovery, folder, _plan, _invoke, _download = limited_queue
    with pytest.raises(ValueError, match="diagnostic_required"):
        limited.infer(None, None, folder, root)
    assert not (folder / "inferences").exists()


@pytest.mark.parametrize("tamper", ["image", "old_receipt", "new_source", "budget", "order"])
def test_tampering_is_rejected_before_operations(limited_queue, monkeypatch, tamper):
    from scripts import vlm_product_limited_plan as planning

    root, _old, recovery, folder, plan, _invoke, _download = limited_queue
    if tamper == "image":
        (recovery / "images" / (plan["inference_ids"][0] + ".png")).write_bytes(b"changed")
    elif tamper == "old_receipt":
        p = recovery / "comparison.json"
        p.write_bytes(p.read_bytes() + b" ")
    elif tamper == "new_source":
        monkeypatch.setattr(planning, "configuration", dict)
    else:
        state = json.loads((folder / "checkpoint.json").read_bytes())
        if tamper == "budget":
            state["elapsed_seconds"] = 0
        else:
            state["inferences"] = [{"sample_id": plan["diagnostic_id"]}]
        save(folder / "checkpoint.json", state)
    with pytest.raises(ValueError):
        planning.load(None, None, folder, root)


def test_observed_properties_survive_comparison_failure(limited_queue, monkeypatch):
    from scripts import vlm_product_limited as limited

    root, _old, _recovery, folder, _plan, _invoke, download = limited_queue

    def fail(*args):
        assert (folder / "diagnostic/observed-properties.json").is_file()
        raise RuntimeError("synthetic_comparison_failure")

    monkeypatch.setattr(limited, "property_differences", fail)
    with pytest.raises(RuntimeError):
        limited.diagnose(None, None, folder, root, downloader=download)
    assert (folder / "diagnostic/observed-properties.json").is_file()
    assert json.loads((folder / "checkpoint.json").read_bytes())["diagnostic"]["status"] == "failed"


@pytest.mark.parametrize("same_bytes", [True, False])
def test_equal_properties_do_not_approve_identity_and_hashes_link_actual_runs(
    limited_queue, monkeypatch, same_bytes
):
    from scripts import vlm_product_limited as limited

    root, old, recovery, folder, plan, _invoke, download = limited_queue
    row = next(r for r in plan["rows"] if r["sample_id"] == plan["diagnostic_id"])
    monkeypatch.setattr(
        limited, "frames_and_properties", lambda *a: (copy.deepcopy(row["properties"]), [])
    )

    def downloader(media, sample):
        if same_bytes:
            return download(media, sample)
        media.write_bytes(b"different diagnostic media bytes")
        return {"sha256": file_hash(media)}

    limited.diagnose(None, None, folder, root, downloader=downloader)
    features = json.loads((folder / "diagnostic/features.json").read_bytes())
    for key, base in (("original_v9", old), ("failed_recovery", recovery)):
        run = base / "sessions" / row["sample_id"] / "run.json"
        assert (
            features[key + "_media_sha256"]
            == json.loads(run.read_bytes())["media_fingerprint"]["sha256"]
        )
        assert features[key + "_run_sha256"] == file_hash(run)
    assert features["same_bytes_as_original_v9"] is same_bytes
    assert features["same_bytes_as_failed_recovery"] is same_bytes
    assert features["identity_approved"] is False
    assert features["properties_equal"] is True and features["differences"] == []
    assert features["retrospective_limit"] == (
        "same_failed_download_bytes_with_recorded_decoder"
        if same_bytes
        else "current_download_only_prior_properties_not_reconstructed"
    )


def test_interrupted_operation_cannot_be_automatically_resumed(limited_queue):
    from scripts import vlm_product_limited as limited

    root, _old, _recovery, folder, plan, _invoke, _download = limited_queue
    state = json.loads((folder / "checkpoint.json").read_bytes())
    state["diagnostic"] = {"sample_id": plan["diagnostic_id"], "status": "running", "seconds": 0.0}
    save(folder / "checkpoint.json", state)
    for operation in (limited.diagnose, limited.infer):
        with pytest.raises(ValueError, match="interrupted"):
            operation(None, None, folder, root)
    assert json.loads((folder / "checkpoint.json").read_bytes()) == state


@pytest.mark.parametrize("tamper", ["version", "raw", "counter"])
def test_failed_native_receipt_and_reservation_are_immutable(limited_queue, tamper):
    from scripts import vlm_product_limited as limited
    from scripts import vlm_product_limited_plan as planning

    root, _old, _recovery, folder, plan, _invoke, download = limited_queue
    limited.diagnose(None, None, folder, root, downloader=download)
    with pytest.raises(ValueError):
        limited.infer(
            None, None, folder, root, invoker=lambda *a, **k: {"raw_response": "not JSON"}
        )
    if tamper == "counter":
        path = folder / "checkpoint.json"
        body = json.loads(path.read_bytes())
        body["calls_reserved"] = 0
    else:
        path = planning.result_path(folder, plan["inference_ids"][0]).parent / "calls/frame-1.json"
        body = json.loads(path.read_bytes())
        body["schema_version" if tamper == "version" else "raw_response"] = "changed"
    save(path, body)
    with pytest.raises(ValueError):
        planning.load(None, None, folder, root)


def test_output_cannot_be_nested_in_a_sealed_queue(limited_queue):
    from scripts import vlm_product_limited_plan as planning

    root, _old, recovery, _folder, _plan, _invoke, _download = limited_queue
    nested = recovery / "forbidden-new-folder"
    with pytest.raises(ValueError, match="separate"):
        planning.prepare(None, None, recovery, nested, root)
    assert not nested.exists()


def test_native_calls_share_remaining_time_instead_of_resetting_it(limited_queue, monkeypatch):
    from contextlib import contextmanager
    from types import SimpleNamespace

    from scripts import vlm_product_limited as limited
    from scripts import vlm_product_limited_plan as planning

    root, _old, _recovery, folder, _plan, invoke, download = limited_queue
    state = limited.diagnose(None, None, folder, root, downloader=download)
    monkeypatch.setattr(limited, "TIME_LIMIT", state["elapsed_seconds"] + 5)
    now = [0.0]
    budgets = []
    monkeypatch.setattr(limited, "time", SimpleNamespace(monotonic=lambda: now[0]))

    @contextmanager
    def deadline(seconds):
        budgets.append(seconds)
        yield

    monkeypatch.setattr(limited, "deadline", deadline)

    def invoker(*args, **kwargs):
        now[0] += 2
        return invoke(*args, **kwargs)

    with pytest.raises(TimeoutError):
        limited.infer(None, None, folder, root, invoker=invoker)
    assert budgets == pytest.approx([5, 3, 1])
    state = planning.load(None, None, folder, root)[1]
    assert state["calls_reserved"] == 4
    assert state["inferences"][0]["seconds"] == 6
    assert state["halt_reason"] == "limited_inference_failed_TimeoutError"


@pytest.mark.parametrize("tamper", [None, "binary", "link", "weight"])
def test_runtime_verification_is_readonly_and_rejects_changes(tmp_path, monkeypatch, tamper):
    import io
    import tarfile

    from scripts import vlm_product_limited as limited

    cache = tmp_path / "runtime"
    installed = cache / "release"
    installed.mkdir(parents=True)
    binary = installed / "cli"
    binary.write_bytes(b"installed runtime")
    link = installed / "alias"
    link.symlink_to("cli")
    archive = cache / "runtime.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        info = tarfile.TarInfo("release/cli")
        info.size = binary.stat().st_size
        bundle.addfile(info, io.BytesIO(binary.read_bytes()))
        info = tarfile.TarInfo("release/alias")
        info.type = tarfile.SYMTYPE
        info.linkname = "cli"
        bundle.addfile(info)
    weights = tmp_path / "weights"
    weights.mkdir()
    weight = weights / "model.gguf"
    weight.write_bytes(b"weights")
    monkeypatch.setattr(limited, "RUNTIME", binary)
    monkeypatch.setattr(limited, "MODEL_DIR", weights)
    monkeypatch.setattr(limited, "HASHES", {"model.gguf": file_hash(weight)})
    monkeypatch.setattr(limited, "ARCHIVE_SHA256", file_hash(archive))
    if tamper == "binary":
        binary.write_bytes(b"changed")
    if tamper == "link":
        link.unlink()
        link.symlink_to("../elsewhere")
    if tamper == "weight":
        weight.write_bytes(b"changed")
    before = {str(p): (p.lstat().st_mtime_ns, p.lstat().st_size) for p in tmp_path.rglob("*")}
    if tamper:
        with pytest.raises((ValueError, FileNotFoundError)):
            limited.verify_runtime()
    else:
        limited.verify_runtime()
    assert {
        str(p): (p.lstat().st_mtime_ns, p.lstat().st_size) for p in tmp_path.rglob("*")
    } == before


@pytest.mark.parametrize("concurrent", [False, True])
def test_worker_guard_excludes_own_wrappers_but_rejects_other_workers(
    tmp_path, monkeypatch, concurrent
):
    from types import SimpleNamespace

    from scripts import vlm_product_limited_plan as planning

    parent = planning.psutil.Process().parents()[0].pid
    unrelated = max(p.pid for p in planning.psutil.process_iter()) + 100000
    workers = [
        SimpleNamespace(
            pid=parent,
            info={
                "name": "rtk",
                "cmdline": ["rtk", "proxy", "python", "-m", "scripts.vlm_product_limited"],
            },
        )
    ]
    if concurrent:
        workers.append(
            SimpleNamespace(
                pid=unrelated,
                info={
                    "name": "python",
                    "cmdline": ["python", "-m", "scripts.vlm_product_recovery"],
                },
            )
        )
    monkeypatch.setattr(planning.psutil, "process_iter", lambda *a: workers)
    if concurrent:
        with pytest.raises(ValueError, match="concurrent_worker"):
            planning.no_workers(tmp_path)
    else:
        planning.no_workers(tmp_path)

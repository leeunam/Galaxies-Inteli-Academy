"""Synthetic interrupted campaign; no real media, labels, weights or network."""

import json

import pytest

from scripts import vlm_product_development as original
from scripts import vlm_product_plan as original_plan
from scripts.private_checkpoint import file_hash, save
from tests.test_vlm_product_development import campaign  # noqa: F401


@pytest.fixture
def interrupted(campaign, monkeypatch):  # noqa: F811
    root, old, _plan, invoke, download = campaign
    original.run_controls(None, None, old, root, limit=48, invoker=invoke)
    original.acquire(None, None, old, root, limit=64, downloader=download)
    original.infer(None, None, old, root, limit=16, invoker=invoke)
    original.acquire(None, None, old, root, limit=64, downloader=download)
    original.infer(None, None, old, root, limit=17, invoker=invoke)
    calls = []

    def interrupt(*args, **kwargs):
        calls.append(True)
        if len(calls) == 4:
            raise RuntimeError("synthetic_external_interruption")
        return invoke(*args, **kwargs)

    with pytest.raises(RuntimeError):
        original.infer(None, None, old, root, limit=1, invoker=interrupt)
    state = json.loads((old / "checkpoint.json").read_bytes())
    sample = state["inferences"][-1]["sample_id"]
    path = old / "inferences/structured" / sample / "calls/frame-4.json"
    raw = json.loads(path.read_bytes())
    raw.pop("error_type")
    raw["status"] = "running"
    save(path, raw)
    delta = 34439.12766741601 - state["elapsed_seconds"]
    state["inferences"][-1]["seconds"] += delta
    state["elapsed_seconds"] += delta
    save(old / "checkpoint.json", state)
    original.compare(None, None, old, root)
    original.dispose(None, None, old, root)
    save(old / "final-verification.json", {"protected_sha256": {}})
    return root, old, invoke, download


def test_recovery_reuses_three_raw_and_calls_only_the_missing_frame(interrupted, monkeypatch):
    from scripts import vlm_product_recovery as recovery
    from scripts import vlm_product_recovery_plan as planning

    root, old, invoke, download = interrupted
    monkeypatch.setattr(planning, "SEALED_FINAL_SHA", file_hash(old / "final-verification.json"))
    monkeypatch.setattr(recovery, "prepare_runtime", lambda **kwargs: None)
    monkeypatch.setattr(recovery, "acquire_row", original.acquire_row)
    folder = root / "data/private/recovery"
    plan = planning.prepare(None, None, old, folder, root)
    before = {str(p): file_hash(p) for p in old.rglob("*.json")}
    recovery.acquire(None, None, folder, root, limit=1, downloader=download)
    invoked = []

    def counted(paths, *args, **kwargs):
        invoked.append(file_hash(paths[0]))
        return invoke(paths, *args, **kwargs)

    state = recovery.infer(None, None, folder, root, limit=1, invoker=counted)
    assert state["calls_reserved"] == 1 and len(invoked) == 1
    first = plan["pending_ids"][0]
    prior = old / "inferences/structured" / first / "calls"
    current = folder / "inferences/structured" / first / "calls"
    for i in (1, 2, 3):
        assert (prior / f"frame-{i}.json").read_bytes() == (
            current / f"frame-{i}.json"
        ).read_bytes()
    assert invoked[0] == json.loads((prior / "frame-4.json").read_bytes())["input_png_sha256"]
    assert {str(p): file_hash(p) for p in old.rglob("*.json")} == before
    assert original_plan.load(None, None, old, root)[1]["halt_reason"] == "product_report_sealed"


@pytest.fixture
def recovery_queue(interrupted, monkeypatch):
    from scripts import vlm_product_recovery as recovery
    from scripts import vlm_product_recovery_plan as planning

    root, old, invoke, download = interrupted
    monkeypatch.setattr(planning, "SEALED_FINAL_SHA", file_hash(old / "final-verification.json"))
    monkeypatch.setattr(recovery, "prepare_runtime", lambda **kwargs: None)
    monkeypatch.setattr(recovery, "acquire_row", original.acquire_row)
    folder = root / "data/private/recovery"
    plan = planning.prepare(None, None, old, folder, root)
    return root, old, folder, plan, invoke, download


def test_complete_recovery_compares_64_with_exact_budget_and_disposes(recovery_queue):
    from scripts import vlm_product_recovery as recovery
    from scripts import vlm_product_recovery_compare as comparison
    from scripts import vlm_product_recovery_plan as planning

    root, old, folder, _plan, invoke, download = recovery_queue
    prior = file_hash(old / "checkpoint.json")
    recovery.acquire(None, None, folder, root, limit=31, downloader=download)
    state = recovery.infer(None, None, folder, root, limit=31, invoker=invoke)
    assert state["calls_reserved"] == 121 and len(state["entries"]) == 31
    report = comparison.compare(None, None, folder, root)
    assert report["evaluated_cases"] == 64 and report["released_fields"] == []
    assert report["cumulative_acquisitions"] == 277
    assert report["cumulative_native_reservations"] == 1758
    assert (
        report["metrics"]["v9"]["all_available"][recovery.FIELD]["all"][
            "correct_value_and_evidence"
        ]
        == 64
    )
    assert comparison.compare(None, None, folder, root) == report
    assert comparison.dispose(None, None, folder, root)["images_removed"] == 31
    assert comparison.dispose(None, None, folder, root)["images_removed"] == 31
    assert planning.load(None, None, folder, root)[1]["images_disposed"]
    assert not list((folder / "images").glob("*.png"))
    assert file_hash(old / "checkpoint.json") == prior
    before = file_hash(folder / "checkpoint.json")
    for operation, extra in (
        (recovery.acquire, {"downloader": download}),
        (recovery.infer, {"invoker": invoke}),
    ):
        with pytest.raises(ValueError, match="halted"):
            operation(None, None, folder, root, limit=1, **extra)
    assert file_hash(folder / "checkpoint.json") == before


@pytest.mark.parametrize("stage", ["download", "native", "bad_json"])
def test_failed_attempt_is_reserved_and_not_automatically_retried(recovery_queue, stage):
    from scripts import vlm_product_recovery as recovery
    from scripts import vlm_product_recovery_compare as comparison
    from scripts import vlm_product_recovery_plan as planning

    root, _old, folder, _plan, _invoke, download = recovery_queue
    calls = []

    def fail(*args, **kwargs):
        calls.append(True)
        if stage == "bad_json":
            return {"raw_response": "not JSON"}
        raise TimeoutError("synthetic_timeout")

    operation = recovery.acquire if stage == "download" else recovery.infer
    extra = {"downloader": fail} if stage == "download" else {"invoker": fail}
    if stage != "download":
        recovery.acquire(None, None, folder, root, limit=1, downloader=download)
    with pytest.raises((TimeoutError, ValueError)):
        operation(None, None, folder, root, limit=1, **extra)
    state = planning.load(None, None, folder, root)[1]
    assert len(state["entries"]) == 1 and len(calls) == 1
    assert state["calls_reserved"] == (0 if stage == "download" else 1)
    with pytest.raises(ValueError, match="halted"):
        operation(None, None, folder, root, limit=1, **extra)
    assert len(calls) == 1
    assert comparison.compare(None, None, folder, root)["evaluated_cases"] == 33
    comparison.dispose(None, None, folder, root)
    assert not list((root / "data/private/media-temp").glob("galaxies-*"))


@pytest.mark.parametrize("tamper", ["budget", "order", "pins", "old_partial", "sheet"])
def test_recovery_rejects_reset_order_and_pixel_or_receipt_changes(recovery_queue, tamper):
    from scripts import vlm_product_recovery as recovery
    from scripts import vlm_product_recovery_plan as planning

    root, old, folder, plan, _invoke, download = recovery_queue
    recovery.acquire(None, None, folder, root, limit=1, downloader=download)
    if tamper == "old_partial":
        path = old / "inferences/structured" / plan["pending_ids"][0] / "calls/frame-1.json"
        path.write_bytes(path.read_bytes() + b" ")
    elif tamper == "sheet":
        path = folder / "images" / (plan["pending_ids"][0] + ".png")
        path.write_bytes(b"tampered")
    elif tamper == "pins":
        path = old / "checkpoint.json"
        path.write_bytes(path.read_bytes() + b" ")
    else:
        path = folder / "checkpoint.json"
        state = json.loads(path.read_bytes())
        if tamper == "budget":
            state["elapsed_seconds"] = 0
        else:
            state["entries"][0]["sample_id"] = plan["pending_ids"][1]
        save(path, state)
    with pytest.raises(ValueError):
        planning.load(None, None, folder, root)


def test_downloader_has_zero_retries_and_stops_after_one_process(tmp_path, monkeypatch):
    from scripts import vlm_product_recovery_network as network

    calls = []

    class Failed:
        returncode = 1

        def communicate(self, timeout):
            assert timeout == 180
            return "", "HTTP Error 403: Forbidden"

    def process(command, **kwargs):
        calls.append(command)
        for flag in ("--retries", "--fragment-retries", "--extractor-retries"):
            assert command[command.index(flag) + 1] == "0"
        assert kwargs["start_new_session"] is True
        return Failed()

    monkeypatch.setattr(network.subprocess, "Popen", process)
    monkeypatch.setattr(network.imageio_ffmpeg, "get_ffmpeg_exe", lambda: "/public/ffmpeg")
    with pytest.raises(RuntimeError):
        network.download_video(tmp_path / "media", "synthetic")
    assert len(calls) == 1


def test_inference_without_acquisition_is_rejected(recovery_queue):
    from scripts import vlm_product_recovery as recovery
    from scripts import vlm_product_recovery_plan as planning

    root, _old, folder, _plan, invoke, download = recovery_queue
    recovery.acquire(None, None, folder, root, limit=1, downloader=download)
    recovery.infer(None, None, folder, root, limit=1, invoker=invoke)
    state = json.loads((folder / "checkpoint.json").read_bytes())
    state["entries"] = []
    save(folder / "checkpoint.json", state)
    with pytest.raises(ValueError, match="inference_without_completed_acquisition"):
        planning.load(None, None, folder, root)


@pytest.mark.parametrize("tamper", ["traversal", "unknown", "report"])
def test_terminal_corruption_is_rejected_before_any_unlink(recovery_queue, monkeypatch, tamper):
    from scripts import vlm_product_recovery as recovery
    from scripts import vlm_product_recovery_compare as comparison
    from scripts.private_checkpoint import digest

    root, _old, folder, _plan, _invoke, download = recovery_queue
    recovery.acquire(None, None, folder, root, limit=1, downloader=download)

    def fail(*args, **kwargs):
        raise TimeoutError("synthetic")

    with pytest.raises(TimeoutError):
        recovery.infer(None, None, folder, root, limit=1, invoker=fail)
    comparison.compare(None, None, folder, root)
    image = next((folder / "images").glob("*.png"))
    original_unlink = type(image).unlink

    def crash(path, *a, **kw):
        if path == image:
            raise OSError("synthetic_disposal_interruption")
        return original_unlink(path, *a, **kw)

    monkeypatch.setattr(type(image), "unlink", crash)
    with pytest.raises(OSError):
        comparison.dispose(None, None, folder, root)
    monkeypatch.setattr(type(image), "unlink", original_unlink)
    state = json.loads((folder / "checkpoint.json").read_bytes())
    if tamper == "report":
        path = folder / "comparison.json"
        report = json.loads(path.read_bytes())
        report["evaluated_cases"] = 64
        report["comparison_sha256"] = digest(
            {k: v for k, v in report.items() if k != "comparison_sha256"}
        )
        save(path, report)
        state["comparison_file_sha256"] = file_hash(path)
    else:
        state["cleanup_pending"] = ["../private-canary" if tamper == "traversal" else "unknown"]
    save(folder / "checkpoint.json", state)
    with pytest.raises(ValueError):
        comparison.dispose(None, None, folder, root)
    assert image.exists()


def test_interrupted_disposal_resumes_idempotently(recovery_queue, monkeypatch):
    from scripts import vlm_product_recovery as recovery
    from scripts import vlm_product_recovery_compare as comparison

    root, _old, folder, _plan, _invoke, download = recovery_queue
    recovery.acquire(None, None, folder, root, limit=1, downloader=download)

    def fail(*a, **kw):
        raise TimeoutError("synthetic")

    with pytest.raises(TimeoutError):
        recovery.infer(None, None, folder, root, limit=1, invoker=fail)
    comparison.compare(None, None, folder, root)
    image = next((folder / "images").glob("*.png"))
    unlink = type(image).unlink

    def crash(path, *a, **kw):
        result = unlink(path, *a, **kw)
        if path == image:
            raise OSError("synthetic_after_unlink")
        return result

    monkeypatch.setattr(type(image), "unlink", crash)
    with pytest.raises(OSError):
        comparison.dispose(None, None, folder, root)
    monkeypatch.setattr(type(image), "unlink", unlink)
    assert comparison.dispose(None, None, folder, root)["images_removed"] == 1
    assert comparison.dispose(None, None, folder, root)["images_removed"] == 1


def test_old_lock_blocks_new_operations_before_calls(recovery_queue):
    from scripts import vlm_product_recovery as recovery
    from scripts.private_checkpoint import lock

    root, old, folder, _plan, _invoke, download = recovery_queue
    before = file_hash(folder / "checkpoint.json")
    with lock(old / ".lock"), pytest.raises(ValueError, match="locked"):
        recovery.acquire(None, None, folder, root, limit=1, downloader=download)
    assert file_hash(folder / "checkpoint.json") == before


@pytest.mark.parametrize("tamper", ["missing", "extra", "hash"])
def test_failed_native_receipts_must_match_reserved_calls(recovery_queue, tamper):
    from scripts import vlm_product_recovery as recovery
    from scripts import vlm_product_recovery_plan as planning

    root, _old, folder, plan, _invoke, download = recovery_queue
    recovery.acquire(None, None, folder, root, limit=1, downloader=download)

    def malformed(*a, **kw):
        return {"raw_response": "not JSON"}

    with pytest.raises(ValueError):
        recovery.infer(None, None, folder, root, limit=1, invoker=malformed)
    calls = folder / "inferences/structured" / plan["pending_ids"][0] / "calls"
    path = calls / "frame-4.json"
    if tamper == "missing":
        path.unlink()
    elif tamper == "extra":
        (calls / "frame-5.json").write_bytes(path.read_bytes())
    else:
        body = json.loads(path.read_bytes())
        body["raw_response_sha256"] = "0" * 64
        save(path, body)
    with pytest.raises(ValueError):
        planning.load(None, None, folder, root)


def test_budget_stop_before_native_is_not_counted_as_an_invocation(recovery_queue, monkeypatch):
    from scripts import vlm_product_recovery as recovery
    from scripts import vlm_product_recovery_plan as planning

    root, _old, folder, _plan, _invoke, download = recovery_queue
    state = recovery.acquire(None, None, folder, root, limit=1, downloader=download)
    monkeypatch.setattr(recovery, "TIME_LIMIT", state["elapsed_seconds"])

    def forbidden(*a, **kw):
        raise AssertionError("native call beyond time budget")

    with pytest.raises(recovery.UnreservedBudgetStop):
        recovery.infer(None, None, folder, root, limit=1, invoker=forbidden)
    assert planning.load(None, None, folder, root)[1]["calls_reserved"] == 0

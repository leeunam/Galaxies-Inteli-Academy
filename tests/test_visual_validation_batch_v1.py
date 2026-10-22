"""Synthetic files and tiny owned Python children; never native model or network."""

import copy
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest
from PIL import Image

from scripts import visual_validation_batch_v1 as batch
from scripts.visual_validation_batch_sidecar_v1 import build_batch_sidecar
from scripts.visual_validation_contract_v1 import digest, load_proposal, read_json, write_new
from scripts.visual_validation_selection_v1 import annotation_packet, select_training
from tests.test_visual_validation_preparation_v1 import exclusions, metadata


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cfg_digest(configuration):
    body = {k: v for k, v in configuration.items() if k != "configuration_sha256"}
    configuration["configuration_sha256"] = digest(body)
    return configuration


def runtime(root):
    directory = root / "fake-assets"
    directory.mkdir()
    files = [directory / n for n in ("runtime", "model.gguf", "projector.gguf", "libmtmd.so")]
    for p in files:
        p.write_bytes(("invented-file-" + p.name).encode())
    template = [
        str(files[0]),
        "-m",
        str(files[1]),
        "--mmproj",
        str(files[2]),
        "--image",
        "<PNG>",
        "--json-schema-file",
        "<SCHEMA>",
        "--prompt",
        "<PROMPT>",
    ]
    for key, value in {
        "--image-min-tokens": "225",
        "--image-max-tokens": "225",
        "--threads": "4",
        "--threads-batch": "4",
        "--seed": "42",
        "--temp": "0",
        "--n-predict": "64",
        "--ctx-size": "3072",
    }.items():
        template.extend((key, value))
    return template, {str(p): sha(p) for p in files}


def make_job(path, call_id, stage, alias, kind, *, frame=1):
    return {
        "call_id": call_id,
        "stage": stage,
        "alias": alias,
        "frame_index": frame,
        "kind": kind,
        "input_path": str(path),
        "input_png_sha256": sha(path),
        "expected_tokens": 240,
        "use_until_epoch": time.time() + 1800,
    }


def auth():
    now = time.time()
    return {
        "schema": "visual-validation-authorization-v1",
        "decision": "authorize_bounded_visual_validation",
        "proposal_sha256": batch.PROPOSAL_SHA256,
        "source_message_id": "invented-human-only",
        "max_model_calls": 397,
        "max_acquisitions": 32,
        "max_global_seconds": 39600,
        "max_cost_brl": 0,
        "retry_allowed": False,
        "issued_epoch": now - 1,
        "use_until_epoch": now + 39000,
        "renew_native_positive_once": True,
    }


def review(configuration, authorization, root):
    return {
        "decision": "approved_visual_validation_stage",
        "proposal_sha256": batch.PROPOSAL_SHA256,
        "authorization_sha256": digest(authorization),
        "configuration_sha256": configuration["configuration_sha256"],
        "execution_root_sha256": batch.root_digest(root),
        "stage": configuration["stage"],
        "geometry_proof_sha256": configuration["geometry_proof_sha256"],
        "source_message_id": "invented-review-only",
        "external_80_second_watchdog_verified": True,
    }


class Recorder:
    def __init__(self, *, failure=None, tail=""):
        self.children = []
        self.failure, self.tail = failure, tail
        self.proposal = load_proposal()

    def __call__(self, argv, **kwargs):
        assert Path(argv[0]).name == "runtime"  # Never a native executable in this test.
        if self.failure == "startup":
            raise PermissionError("entirely invented startup failure")
        prompt = argv[argv.index("--prompt") + 1]
        if prompt == self.proposal["development"]["positive_question"]:
            value = {"answer": "yes"}
        elif prompt == self.proposal["candidate"]["person"]["prompt"]:
            value = {"person_visible": True}
        elif prompt == self.proposal["candidate"]["text"]["prompt"]:
            value = {"screen_text": False}
        elif self.failure == "unknown":
            value = {
                "state": "uncertain",
                "item_configuration": "unclear",
                "presented_categories": [],
            }
        else:
            value = {
                "state": "no_target",
                "item_configuration": "absent",
                "presented_categories": [],
            }
        logs = (
            "encoding mtmd batch, n_chunks = 1 (done = 0, total = 1)\n"
            "mtmd batch encoding done in 1 ms\n"
            "decoding image batch 1/1, n_tokens_batch = 240\n"
            "image decoded (batch 1/1) in 1 ms\n"
        )
        code = (
            f"import sys,time,os,signal;sys.stderr.write({logs!r});sys.stderr.flush();"
            f"sys.stdout.write({json.dumps(value)!r});sys.stdout.flush();" + self.tail
        )
        process = subprocess.Popen([sys.executable, "-B", "-c", code], **kwargs)
        self.children.append(process)
        return process


@pytest.fixture
def prepared(tmp_path):
    template, assets = runtime(tmp_path)
    folder = tmp_path / "data/private" / batch.NAMESPACE
    folder.mkdir(parents=True, mode=0o700)
    inputs = folder / "inputs"
    inputs.mkdir(mode=0o700)
    jobs = []
    for i, row in enumerate(load_proposal()["development"]["product_negative_controls"]):
        path = inputs / (row["sample_id"] + ".png")
        Image.new("RGB", (320, 330), (i, i, i)).save(path)
        jobs.append(make_job(path, i + 1, "development", row["sample_id"], "product_visible_early"))
    path = inputs / "native-positive.png"
    Image.new("RGB", (360, 640), "green").save(path)
    jobs.append(make_job(path, 13, "development", "native-positive", "relation"))
    configuration = batch.prepare_configuration(
        tmp_path,
        stage="development",
        jobs=jobs,
        runtime_template=template,
        assets=assets,
        data_kind="synthetic",
    )
    authorization = auth()
    technical = review(configuration, authorization, tmp_path)
    write_new(folder / "authorization.json", authorization)
    write_new(folder / "review-development.json", technical)
    recorder = Recorder()
    services = batch.Services(
        recorder, lambda: None, lambda: 7 * 1024**3, list, synthetic_only=True
    )
    return tmp_path, configuration, authorization, technical, services, recorder


def execute(context, call_id=1):
    root, configuration, _, _, services, _ = context
    return batch._dispatch_invented(configuration, call_id, root=root, services=services)


def test_native_public_entry_cannot_read_configuration_or_create_a_run(tmp_path):
    with pytest.raises(ValueError, match="not_released"):
        batch.dispatch_one(None, 1, root=tmp_path)
    assert not list(tmp_path.iterdir())
    assert batch.main(["--configuration", "does-not-exist.json", "--call-id", "1"]) == 2


def test_bound_invented_call_reserves_persists_and_never_retries(prepared):
    root, _configuration, _, _, _, recorder = prepared
    receipt = execute(prepared)
    assert receipt["accepted"] and receipt["data_kind"] == "synthetic"
    assert receipt["native_execution_verified"] is False
    assert len(recorder.children) == 1 and recorder.children[0].poll() is not None
    assert batch.read_dispatch_receipt(root, 1) == receipt
    state = batch.validate_state(
        read_json(root / "data/private" / batch.NAMESPACE / "global-ledger.json")
    )
    assert state["calls_reserved"] == 1 and state["pending"] is None
    with pytest.raises(ValueError, match="consumed_or_out_of_order"):
        execute(prepared)
    assert len(recorder.children) == 1


@pytest.mark.parametrize(
    "fault", ["approval", "review", "expired", "lease", "memory", "asset", "input", "watchdog"]
)
def test_admission_faults_never_launch_or_reserve(prepared, fault):
    root, configuration, authorization, technical, services, recorder = prepared
    folder = root / "data/private" / batch.NAMESPACE
    if fault == "approval":
        (folder / "authorization.json").unlink()
    elif fault == "review":
        technical["configuration_sha256"] = "0" * 64
    elif fault == "expired":
        authorization["use_until_epoch"] = time.time() - 10
    elif fault == "lease":
        configuration["jobs"][0]["use_until_epoch"] = time.time() - 1
        cfg_digest(configuration)
        technical["configuration_sha256"] = configuration["configuration_sha256"]
    elif fault == "memory":
        services.available_memory = lambda: 6 * 1024**3 - 1
    elif fault == "asset":
        Path(next(iter(configuration["assets"]))).write_bytes(b"changed invented asset")
    elif fault == "input":
        Path(configuration["jobs"][0]["input_path"]).write_bytes(b"changed invented image")
    else:
        technical["external_80_second_watchdog_verified"] = False
    if fault in ("review", "lease", "watchdog"):
        (folder / "review-development.json").write_text(json.dumps(technical))
    if fault == "expired":
        (folder / "authorization.json").write_text(json.dumps(authorization))
    with pytest.raises((ValueError, OSError)):
        execute(prepared)
    assert recorder.children == [] and not (folder / "global-ledger.json").exists()


@pytest.mark.parametrize("failure", ["startup", "unknown"])
def test_startup_or_perceptual_failure_closes_the_grant(prepared, failure):
    root, _, _, _, _, recorder = prepared
    recorder.failure = failure
    result = execute(prepared)
    assert result["accepted"] is False
    state = batch.inspect_state(root)
    assert state["calls_reserved"] == 1 and state["status"] == "sealed"
    with pytest.raises(ValueError, match="sealed_or_uncertain"):
        execute(prepared, 2)
    assert all(p.poll() is not None for p in recorder.children)


def test_approval_changed_during_preflight_leaves_marker_and_no_child(prepared):
    root, _, authorization, _, services, recorder = prepared
    folder = root / "data/private" / batch.NAMESPACE

    def change():
        authorization["source_message_id"] = "changed-invented-reference"
        (folder / "authorization.json").write_text(json.dumps(authorization))

    services.preflight = change
    with pytest.raises(ValueError, match="receipt_or_source_changed"):
        execute(prepared)
    assert recorder.children == []
    assert batch.inspect_state(root)["status"] == "uncertain"
    assert batch.inspect_state(root)["unaccounted_capture_markers"] == 1


def test_real_python_child_interruption_closes_the_batch_and_is_collected(prepared):
    root, _, _, _, _, recorder = prepared
    recorder.tail = "os.kill(os.getppid(),signal.SIGTERM);time.sleep(5)"
    result = execute(prepared)
    assert not result["accepted"] and result["cleanup_confirmed"]
    assert all(p.poll() is not None for p in recorder.children)
    assert batch.inspect_state(root)["status"] == "sealed"


def complete_development(context):
    for i in range(1, 14):
        assert execute(context, i)["accepted"]


def audit_context(context):
    root, development, authorization, _, services, recorder = context
    path = root / "data/private" / batch.NAMESPACE / "inputs/audit-invented.png"
    Image.new("RGB", (320, 330), "white").save(path)
    data = metadata()
    for row in data["rows"]:
        row["frame_sha256"] = [sha(path), sha(path)]
    selected = select_training(data, exclusions())
    jobs = []
    for row in selected["rows"]:
        for frame in range(1, 3):
            for kind in ("person_visible", "product_visible_early", "screen_text"):
                jobs.append(
                    make_job(path, 14 + len(jobs), "audit", row["alias"], kind, frame=frame)
                )
    configuration = batch.prepare_configuration(
        root,
        stage="audit",
        jobs=jobs,
        runtime_template=development["runtime_template"],
        assets=development["assets"],
        data_kind="synthetic",
        selection=selected,
    )
    packet = annotation_packet(selected)
    committed = {
        "schema": "visual-blind-annotation-commitment-v1",
        "selection_sha256": selected["selection_sha256"],
        "packet_sha256": packet["packet_sha256"],
        "annotations_file_sha256": "a" * 64,
        "annotations_content_sha256": "b" * 64,
        "sample_count": 32,
        "declared_origin": "assisted",
        "annotation_requirement": "assisted_review_allowed",
        "execution_authorized": False,
    }
    committed["commitment_sha256"] = digest(committed)
    technical = review(configuration, authorization, root) | {
        "annotation_commitment_sha256": committed["commitment_sha256"],
        "exclusions_independently_verified": True,
        "annotation_origin_independently_verified": True,
        "development_independently_reviewed": True,
    }
    folder = root / "data/private" / batch.NAMESPACE
    write_new(folder / "review-audit.json", technical)
    write_new(folder / "annotation-commitment.json", committed)
    # Invalid content deliberately traps any attempt by the model executor to read GT.
    (folder / "annotations-private.json").write_bytes(b"DO NOT READ PRIVATE GT IN EXECUTOR")
    return (root, configuration, authorization, technical, services, recorder), selected, committed


def test_blind_dispatch_has_no_gt_access_and_sidecar_retains_synthetic_provenance(prepared):
    complete_development(prepared)
    context, selected, _ = audit_context(prepared)
    root, configuration, _, _, _, recorder = context
    for i in (14, 15, 16):
        assert execute(context, i)["accepted"]
    row = selected["rows"][0]
    case = {
        k: row[k] for k in ("alias", "partition", "media_sha256", "frame_seconds", "frame_sha256")
    }
    # Only the first frame has been captured: an incomplete case must not be accepted.
    calls = [
        {
            kind: {"call_id": 14 + i, "expected_tokens": 240}
            for i, kind in enumerate(("person_visible", "product_visible_early", "screen_text"))
        }
    ]
    with pytest.raises(ValueError, match="frame_count"):
        build_batch_sidecar(
            case, calls, root=root, candidate_sha256=configuration["candidate_sha256"]
        )
    for i in (17, 18, 19):
        assert execute(context, i)["accepted"]
    calls.append(
        {
            kind: {"call_id": 17 + i, "expected_tokens": 240}
            for i, kind in enumerate(("person_visible", "product_visible_early", "screen_text"))
        }
    )
    sidecar = build_batch_sidecar(
        case, calls, root=root, candidate_sha256=configuration["candidate_sha256"]
    )
    assert sidecar["data_kind"] == "synthetic" and not sidecar["native_execution_verified"]
    assert not sidecar["approved_for_training"] and sidecar["quality_release_sha256"] is None
    assert all(p.poll() is not None for p in recorder.children)
    changed = copy.deepcopy(case)
    changed["frame_seconds"] = [0.2, 2.0]
    with pytest.raises(ValueError, match="candidate_changed"):
        build_batch_sidecar(
            changed, calls, root=root, candidate_sha256=configuration["candidate_sha256"]
        )


def test_annotation_provenance_human_requirement_and_hash_are_not_bypassed(prepared):
    context, _, committed = audit_context(prepared)
    root, configuration, _, technical, _, _ = context
    batch.verify_annotation_commitment(configuration, technical, committed)
    for key in (
        "annotation_origin_independently_verified",
        "exclusions_independently_verified",
        "development_independently_reviewed",
    ):
        with pytest.raises(ValueError):
            batch.verify_annotation_commitment(configuration, technical | {key: False}, committed)
    human = {k: v for k, v in committed.items() if k != "commitment_sha256"}
    human["annotation_requirement"] = "human_required"
    human["commitment_sha256"] = digest(human)
    with pytest.raises(ValueError, match="human_annotations_required"):
        batch.verify_annotation_commitment(
            configuration,
            technical | {"annotation_commitment_sha256": human["commitment_sha256"]},
            human,
        )
    assert batch.inspect_state(root)["calls_reserved"] == 0


def test_global_counters_397_32_and_time_close_without_any_process(tmp_path):
    state = batch.initial_state(auth(), tmp_path, 100, "synthetic")
    for i in range(13):
        entry = batch.reserve_event(state, "development", f"dev-{i}", 100)
        batch.finish_event(state, entry, seconds=1, accepted=True)
    for i in range(32):
        entry = batch.reserve_event(state, "acquisition", f"acq-{i}", 100)
        batch.finish_event(state, entry, seconds=1, accepted=True)
    with pytest.raises(ValueError, match="acquisition_budget"):
        batch.reserve_event(state, "acquisition", "acq-overflow", 100)
    for i in range(384):
        entry = batch.reserve_event(state, "audit", f"audit-{i}", 100)
        batch.finish_event(state, entry, seconds=1, accepted=True)
    batch.validate_state(state)
    assert (
        state["calls_reserved"] == 397 and state["acquisitions_reserved"] == 32 and state["sealed"]
    )
    with pytest.raises(ValueError):
        batch.reserve_event(state, "audit", "overflow", 100)


def test_uncertain_operation_keeps_full_charge_and_blocks_next_effect(tmp_path):
    state = batch.initial_state(auth(), tmp_path, 100, "synthetic")
    entry = batch.reserve_event(state, "development", "model-1", 100)
    assert state["charged_seconds"] == 80 and state["pending"] == "model-1"
    with pytest.raises(ValueError, match="uncertain"):
        batch.reserve_event(state, "development", "model-2", 101)
    batch.finish_event(state, entry, seconds=81, accepted=True)
    assert state["sealed"] and state["charged_seconds"] == 81 and not entry["accepted"]
    state = batch.initial_state(auth(), tmp_path, 100, "synthetic")
    with pytest.raises(ValueError, match="global_deadline"):
        batch.reserve_event(state, "development", "late", 39700)


def test_configuration_root_and_source_rebinding_are_refused(prepared, tmp_path):
    _, configuration, _, _, _, recorder = prepared
    other = tmp_path / "other"
    other.mkdir()
    with pytest.raises(ValueError):
        batch.validate_configuration(configuration, other, allow_synthetic=True)
    changed = copy.deepcopy(configuration)
    changed["source_files_sha256"][next(iter(changed["source_files_sha256"]))] = "0" * 64
    cfg_digest(changed)
    with pytest.raises(ValueError):
        batch.validate_configuration(changed, prepared[0], allow_synthetic=True)
    assert not recorder.children


def test_memory_drop_after_reservation_cannot_spawn(prepared):
    root, _, _, _, services, recorder = prepared
    ledger = root / "data/private" / batch.NAMESPACE / "global-ledger.json"

    def memory():
        consumed = ledger.exists() and read_json(ledger)["calls_reserved"] == 1
        return 5 * 1024**3 if consumed else 7 * 1024**3

    services.available_memory = memory
    result = execute(prepared)
    assert result["accepted"] is False and result["cleanup_confirmed"]
    assert recorder.children == []
    assert batch.inspect_state(root)["status"] == "sealed"
    assert batch.inspect_state(root)["calls_reserved"] == 1


@pytest.mark.parametrize("key", ["calls_reserved", "development_calls", "acquisitions_reserved"])
def test_ledger_boolean_counter_corruption_is_not_an_integer(tmp_path, key):
    state = batch.initial_state(auth(), tmp_path, 100, "synthetic")
    state[key] = False
    with pytest.raises(ValueError, match="ledger_counter"):
        batch.validate_state(state)


@pytest.mark.parametrize("file_name", ["authorization.json", "review-development.json"])
def test_authority_envelopes_refuse_labels_or_outcomes(prepared, file_name):
    root, _, _, _, _, recorder = prepared
    path = root / "data/private" / batch.NAMESPACE / file_name
    value = read_json(path)
    value["labels"] = {"invented-case": True}
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="authority_metadata_only"):
        execute(prepared)
    assert not recorder.children
    assert batch.inspect_state(root)["calls_reserved"] == 0


def test_cli_never_opens_an_unlisted_configuration_even_with_test_activation(tmp_path, monkeypatch):
    monkeypatch.setattr(batch, "NATIVE_DISPATCH_RELEASED", True)
    monkeypatch.setattr(batch, "read_json", lambda *_: pytest.fail("unlisted file was opened"))
    assert batch.main(["--configuration", str(tmp_path / "unlisted.env"), "--call-id", "1"]) == 2


def test_runtime_schema_preserves_frozen_state_first_order(prepared):
    _, _, _, _, services, recorder = prepared

    def inspect(argv, **kwargs):
        schema = json.loads(Path(argv[argv.index("--json-schema-file") + 1]).read_text())
        assert all(
            list(branch["properties"]) == ["state", "item_configuration", "presented_categories"]
            for branch in schema["oneOf"]
        )
        return recorder(argv, **kwargs)

    services.launch = inspect
    assert execute(prepared)["accepted"] is True

"""Invented identities and metadata receipts only; no corpus, media, model or network IO."""

import copy
import json

import pytest

from scripts.visual_validation_annotations_v1 import template
from scripts.visual_validation_contract_v1 import digest, read_json
from scripts.visual_validation_selection_v1 import annotation_packet, select_training
from scripts.visual_validation_selection_v2 import (
    IDENTITY_KEYS,
    bind_acquired_frames,
    freeze_media_expectations,
    ready_annotation_packet,
    require_observed_selection,
    seal_expectations,
    seal_frames,
    seal_ids,
    select_identities,
)
from tests.test_visual_validation_preparation_v1 import exclusions, metadata, sha


def identities():
    original = metadata()
    return {
        "schema": "visual-audit-training-identities-v2",
        "cohort_size": 300,
        "split_counts": original["split_counts"],
        "source_sha256": original["source_sha256"],
        "data_kind": "synthetic",
        "rows": [{k: row[k] for k in IDENTITY_KEYS} for row in original["rows"]],
    }


def ledger(*, acquisitions=0, calls=0, outputs=False):
    return {
        "acquisitions_reserved": acquisitions,
        "audit_calls_reserved": calls,
        "model_outputs_present": outputs,
    }


def selected():
    return select_identities(identities(), exclusions(), candidate_sha256=sha("frozen-candidate"))


def expected_metadata(plan):
    return {
        "schema": "visual-audit-selected-media-metadata-v2",
        "id_selection_sha256": plan["id_selection_sha256"],
        "data_kind": "synthetic",
        "source_sha256": sha("invented-selected-source"),
        "rows": [
            {
                "sample_id": row["sample_id"],
                "media_sha256": row["media_sha256"],
                "properties_sha256": sha("properties-" + row["sample_id"]),
                "sheet_sha256": sha("sheet-" + row["sample_id"]),
                "frame_seconds": [0.2, 4.0],
            }
            for row in plan["rows"]
        ],
    }


def acquired(plan, expected):
    return {
        "schema": "visual-audit-acquisition-receipts-v2",
        "id_selection_sha256": plan["id_selection_sha256"],
        "expectations_sha256": expected["expectations_sha256"],
        "data_kind": "synthetic",
        "rows": [
            {
                "sample_id": row["sample_id"],
                "reacquired_media_sha256": row["media_sha256"],
                "properties_sha256": row["properties_sha256"],
                "sheet_sha256": row["sheet_sha256"],
                "frame_seconds": list(row["frame_seconds"]),
                "frame_sha256": [
                    sha(row["sample_id"] + "-frame-1"),
                    sha(row["sample_id"] + "-frame-2"),
                ],
                "pts_proof_sha256": sha("invented-pts-" + row["sample_id"]),
                "bridge_receipt_sha256": sha("invented-bridge-" + row["sample_id"]),
                "cleanup_confirmed": True,
                "acquisition_kind": "reacquired",
                "acquisition_number": i,
            }
            for i, row in enumerate(expected["rows"], 1)
        ],
    }


def prepared():
    plan = selected()
    expected = freeze_media_expectations(plan, expected_metadata(plan), ledger())
    return plan, expected, acquired(plan, expected)


def recommit(value, key):
    value[key] = digest({k: v for k, v in value.items() if k != key})
    return value


def test_identity_selection_preserves_the_original_exact_ids_and_order_without_any_frames():
    data = identities()
    plan = select_identities(data, exclusions(), candidate_sha256=sha("frozen-candidate"))
    old = select_training(metadata(), exclusions())
    assert [(r["sample_id"], r["alias"]) for r in plan["rows"]] == [
        (r["sample_id"], r["alias"]) for r in old["rows"]
    ]
    data["rows"].reverse()
    assert (
        select_identities(data, exclusions(), candidate_sha256=sha("frozen-candidate"))["rows"]
        == plan["rows"]
    )
    assert all(set(r) == IDENTITY_KEYS | {"alias"} for r in plan["rows"])
    assert plan["audit_calls_exact"] is None and plan["frames_frozen"] is False
    assert not plan["execution_authorized"]
    with pytest.raises(ValueError):
        annotation_packet(plan)
    with pytest.raises(ValueError):
        ready_annotation_packet(plan)


@pytest.mark.parametrize(
    "fault", ["outcome", "holdout", "duplicate", "count", "extra_frames", "insufficient_channels"]
)
def test_identity_projection_refuses_contamination_or_insufficient_reserve(fault):
    value = identities()
    if fault == "outcome":
        value["rows"][0]["views"] = 999
    elif fault == "holdout":
        value["rows"][0]["partition"] = "test"
    elif fault == "duplicate":
        value["rows"][1]["sample_id"] = value["rows"][0]["sample_id"]
    elif fault == "count":
        value["rows"].pop()
    elif fault == "extra_frames":
        value["rows"][0]["frame_sha256"] = [sha("not-an-identity")]
    else:
        for row in value["rows"]:
            if row["sector"] == "moda":
                row["channel_id"] = "one-channel"
    with pytest.raises(ValueError):
        select_identities(value, exclusions(), candidate_sha256=sha("candidate"))


def test_only_the_selected_32_need_media_metadata_and_frames_then_packet_hides_identity():
    plan, expected, receipts = prepared()
    ready = bind_acquired_frames(plan, expected, receipts, ledger(acquisitions=32))
    assert len(expected["rows"]) == len(ready["rows"]) == 32
    assert ready["audit_calls_exact"] == 192
    assert ready["id_selection_sha256"] == plan["id_selection_sha256"]
    assert ready["data_kind"] == "synthetic" and ready["execution_authorized"] is False
    assert ready["independent_media_review_required"]
    assert ready["media_proof_files_opened_by_selector"] is False
    packet = ready_annotation_packet(ready)
    assert packet["data_kind"] == "synthetic"
    encoded = json.dumps(packet)
    assert all(
        word not in encoded
        for word in ("sample_id", "channel_id", "sector", "media_sha256", "expected")
    )
    assert template(packet)["items"][0]["frames"][0]["fields"]["person_visible"] is None
    with pytest.raises(ValueError, match="synthetic_selection_not_observed"):
        require_observed_selection(ready)


@pytest.mark.parametrize(
    "fault", ["missing", "replacement", "outcome", "media", "late", "nan_time"]
)
def test_expectations_are_selected_only_and_must_be_frozen_before_acquisition(fault):
    plan = selected()
    value = expected_metadata(plan)
    state = ledger()
    if fault == "missing":
        value["rows"].pop()
    elif fault == "replacement":
        value["rows"][0]["sample_id"] = "different-case"
    elif fault == "outcome":
        value["rows"][0]["target"] = 1.0
    elif fault == "media":
        value["rows"][0]["media_sha256"] = sha("other-media")
    elif fault == "nan_time":
        value["rows"][0]["frame_seconds"] = [float("nan")]
    else:
        state = ledger(acquisitions=1)
    with pytest.raises(ValueError):
        freeze_media_expectations(plan, value, state)


@pytest.mark.parametrize(
    "fault",
    [
        "replacement",
        "media",
        "properties",
        "sheet",
        "time",
        "missing_frame",
        "pts",
        "cleanup",
        "label",
        "mixed_kind",
    ],
)
def test_changed_recovery_or_any_substitution_cannot_be_sealed(fault, tmp_path):
    plan, expected, receipts = prepared()
    row = receipts["rows"][0]
    if fault == "replacement":
        row["sample_id"] = "substitute-case"
    elif fault == "media":
        row["reacquired_media_sha256"] = sha("different-bytes")
    elif fault == "properties":
        row["properties_sha256"] = sha("different-properties")
    elif fault == "sheet":
        row["sheet_sha256"] = sha("different-pixels")
    elif fault == "time":
        row["frame_seconds"] = [0.2, 5.0]
    elif fault == "missing_frame":
        row["frame_sha256"].pop()
    elif fault == "pts":
        row["pts_proof_sha256"] = None
    elif fault == "cleanup":
        row["cleanup_confirmed"] = False
    elif fault == "label":
        row["expected_product"] = False
    else:
        receipts["data_kind"] = "observed"
    with pytest.raises(ValueError):
        ready = bind_acquired_frames(plan, expected, receipts, ledger(acquisitions=32))
        seal_frames(ready, tmp_path / "not-created", ledger())
    assert not (tmp_path / "not-created").exists()


@pytest.mark.parametrize("state", [ledger(calls=1), ledger(outputs=True), ledger(acquisitions=33)])
def test_frames_must_be_frozen_before_any_audit_answers(state):
    plan, expected, receipts = prepared()
    with pytest.raises(ValueError):
        bind_acquired_frames(plan, expected, receipts, state)


def test_candidate_ids_expectations_and_receipts_cannot_be_swapped_after_seals():
    plan, expected, receipts = prepared()
    changed = copy.deepcopy(plan)
    changed["candidate_sha256"] = sha("later-retuned-candidate")
    recommit(changed, "id_selection_sha256")
    with pytest.raises(ValueError, match="expectations_binding_changed"):
        bind_acquired_frames(changed, expected, receipts, ledger())
    damaged = copy.deepcopy(expected)
    damaged["rows"][0]["sheet_sha256"] = sha("changed-after-expectation-seal")
    with pytest.raises(ValueError, match="commitment_changed"):
        bind_acquired_frames(plan, damaged, receipts, ledger())


def test_private_phase_seals_are_exclusive_and_preserve_the_id_commitment(tmp_path):
    plan, expected, receipts = prepared()
    destination = tmp_path / "private"
    seal_ids(plan, destination)
    seal_expectations(expected, destination)
    ready = bind_acquired_frames(plan, expected, receipts, ledger(acquisitions=32))
    seal_frames(ready, destination, ledger(acquisitions=32))
    assert read_json(destination / "selection-ids.json") == plan
    assert (
        read_json(destination / "selection-frames.json")["id_selection_sha256"]
        == plan["id_selection_sha256"]
    )
    with pytest.raises(FileExistsError):
        seal_ids(plan, destination)
    with pytest.raises(FileExistsError):
        seal_expectations(expected, destination)
    with pytest.raises(FileExistsError):
        seal_frames(ready, destination, ledger(acquisitions=32))


@pytest.mark.parametrize("phase", ["ids", "expectations", "frames"])
def test_extra_outcomes_cannot_be_written_even_with_a_recomputed_self_digest(phase, tmp_path):
    plan, expected, receipts = prepared()
    ready = bind_acquired_frames(plan, expected, receipts, ledger(acquisitions=32))
    value, key = {
        "ids": (plan, "id_selection_sha256"),
        "expectations": (expected, "expectations_sha256"),
        "frames": (ready, "selection_sha256"),
    }[phase]
    value["outcomes"] = {"invented": 999}
    recommit(value, key)
    with pytest.raises(ValueError):
        if phase == "ids":
            seal_ids(value, tmp_path / "no")
        elif phase == "expectations":
            seal_expectations(value, tmp_path / "no")
        else:
            seal_frames(value, tmp_path / "no", ledger(acquisitions=32))
    assert not (tmp_path / "no").exists()


@pytest.mark.parametrize("phase", ["ids", "frames"])
def test_nested_outcomes_cannot_hide_in_provenance_hashes(phase, tmp_path):
    plan, expected, receipts = prepared()
    value = (
        plan
        if phase == "ids"
        else bind_acquired_frames(plan, expected, receipts, ledger(acquisitions=32))
    )
    value["exclusion_source_sha256"] = {"outcomes": {"invented": 999}}
    recommit(value, "id_selection_sha256" if phase == "ids" else "selection_sha256")
    with pytest.raises(ValueError, match="provenance_hashes_required"):
        if phase == "ids":
            seal_ids(value, tmp_path / "no")
        else:
            seal_frames(value, tmp_path / "no", ledger(acquisitions=32))
    assert not (tmp_path / "no").exists()


def test_duplicate_sample_alias_between_different_channels_is_not_a_blind_packet():
    plan, expected, receipts = prepared()
    ready = bind_acquired_frames(plan, expected, receipts, ledger(acquisitions=32))
    ready["rows"][1]["sample_id"] = ready["rows"][0]["sample_id"]
    ready["rows"][1]["alias"] = ready["rows"][0]["alias"]
    recommit(ready, "selection_sha256")
    with pytest.raises(ValueError, match="duplicate_frame_case"):
        ready_annotation_packet(ready)


def test_reacquisition_receipts_require_matching_global_count_and_unique_numbers():
    plan, expected, receipts = prepared()
    with pytest.raises(ValueError, match="acquisition_ledger_mismatch"):
        bind_acquired_frames(plan, expected, receipts, ledger())
    receipts["rows"][1]["acquisition_number"] = 1
    with pytest.raises(ValueError, match="acquisition_ledger_mismatch"):
        bind_acquired_frames(plan, expected, receipts, ledger(acquisitions=32))


def test_already_local_media_does_not_require_artificial_downloads():
    plan, expected, receipts = prepared()
    for row in receipts["rows"]:
        row.update(acquisition_kind="already_local", acquisition_number=None)
    ready = bind_acquired_frames(plan, expected, receipts, ledger())
    assert ready["acquisitions_reserved"] == 0 and ready["existing_local_cases"] == 32
    assert ready["acquisition_provenance_independently_verified"] is False
    assert ready["execution_authorized"] is False

"""Invented training metadata and annotations only; no images, models or corpus IO."""

import copy
import hashlib
import json

import pytest

from scripts.visual_validation_annotations_v1 import (
    seal_annotations,
    template,
    validate_annotations,
)
from scripts.visual_validation_contract_v1 import commitment, digest, load_proposal, read_json
from scripts.visual_validation_selection_v1 import (
    annotation_packet,
    seal_selection,
    select_training,
)


def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()


def metadata():
    rows = []
    for i in range(203):
        rows.append(
            {
                "sample_id": f"invented-{i:03d}",
                "channel_id": f"channel-{i:03d}",
                "sector": "beleza" if i < 102 else "moda",
                "partition": "train",
                "media_sha256": sha(f"media-{i}"),
                "frame_seconds": [0.2, 4.0],
                "frame_sha256": [sha(f"frame-{i}-1"), sha(f"frame-{i}-2")],
            }
        )
    return {
        "schema": "visual-audit-training-metadata-v1",
        "cohort_size": 300,
        "split_counts": {"train": 203, "validation": 66, "test": 31},
        "source_sha256": sha("invented-training-projection"),
        "rows": rows,
    }


def exclusions():
    return {
        "sample_ids": ["invented-000"],
        "channel_ids": ["channel-001"],
        "media_sha256": [sha("media-2")],
        "source_sha256": {"invented-reveals": sha("reveals")},
    }


def selection():
    return select_training(metadata(), exclusions())


def filled(packet, origin="synthetic"):
    value = template(packet)
    value["declared_origin"] = origin
    if origin == "human":
        value["human_reference"] = "entirely-invented-human-annotation-reference"
    for item in value["items"]:
        for frame in item["frames"]:
            frame["fields"] = {
                "person_visible": True,
                "product_visible_early": False,
                "screen_text": "unknown",
            }
            frame["product_witnesses"] = []
            frame["support_notes"] = "Invented fixture, not a visual annotation."
    return value


def test_proposal_is_read_only_inactive_and_has_consistent_bounds():
    proposal = load_proposal()
    assert proposal["limits"]["new_model_calls_max"] == 397
    assert proposal["authorization_received"] is False
    assert proposal["current_scientific_status"]["visual_audit_accepted"] is False


def test_selection_is_deterministic_balanced_and_excludes_all_three_identity_units():
    source = metadata()
    a = select_training(source, exclusions())
    source["rows"].reverse()
    b = select_training(source, exclusions())
    assert a["rows"] == b["rows"]
    assert len(a["rows"]) == len({r["channel_id"] for r in a["rows"]}) == 32
    assert sum(r["sector"] == "beleza" for r in a["rows"]) == 16
    assert not {"invented-000", "invented-001", "invented-002"} & {
        r["sample_id"] for r in a["rows"]
    }
    assert a["audit_calls_exact"] == 3 * 32 * 2
    assert a["independent_exclusion_review_required"] and not a["execution_authorized"]


@pytest.mark.parametrize("corruption", ["test", "outcome", "duplicate", "frame", "too_few"])
def test_selection_refuses_mixed_outcomes_bad_identity_or_insufficient_reserve(corruption):
    value = metadata()
    if corruption == "test":
        value["rows"][0]["partition"] = "test"
    elif corruption == "outcome":
        value["rows"][0]["view_count"] = 999
    elif corruption == "duplicate":
        value["rows"][1]["sample_id"] = value["rows"][0]["sample_id"]
    elif corruption == "frame":
        value["rows"][0]["frame_seconds"] = [0.2, 0.2]
    else:
        for row in value["rows"]:
            if row["sector"] == "moda":
                row["channel_id"] = "one-fashion-channel"
    with pytest.raises(ValueError):
        select_training(value, exclusions())


def test_packet_never_contains_sources_sectors_outcomes_predictions_or_labels():
    packet = annotation_packet(selection())
    for item in packet["items"]:
        assert set(item) == {"alias", "frame_seconds", "frame_sha256"}
    encoded = json.dumps(packet)
    for word in ("sample_id", "channel_id", "sector", "view_count", "prediction", "expected"):
        assert word not in encoded
    draft = template(packet)
    assert draft["items"][0]["frames"][0]["fields"]["person_visible"] is None
    with pytest.raises(ValueError):
        validate_annotations(packet, draft)


def test_annotations_seal_before_audit_without_claiming_human_certification(tmp_path):
    packet = annotation_packet(selection())
    body = filled(packet)
    sealed = seal_annotations(
        packet,
        body,
        {"audit_calls_reserved": 0, "model_outputs_present": False},
        tmp_path / "private",
    )
    assert sealed["declared_origin"] == "synthetic"
    assert sealed["human_review_verified"] is False and sealed["execution_authorized"] is False
    assert "items" not in sealed and "fields" not in json.dumps(sealed)
    assert read_json(tmp_path / "private/annotations-private.json") == body
    with pytest.raises(FileExistsError):
        seal_annotations(
            packet,
            body,
            {"audit_calls_reserved": 0, "model_outputs_present": False},
            tmp_path / "private",
        )


@pytest.mark.parametrize(
    "corruption", ["started", "outputs", "image", "prediction", "unfilled_witness"]
)
def test_no_post_response_annotation_or_mismatched_content(corruption, tmp_path):
    packet = annotation_packet(selection())
    body = filled(packet)
    ledger = {"audit_calls_reserved": 0, "model_outputs_present": False}
    if corruption == "started":
        ledger["audit_calls_reserved"] = 1
    elif corruption == "outputs":
        ledger["model_outputs_present"] = True
    elif corruption == "image":
        body["items"][0]["frames"][0]["png_sha256"] = sha("wrong")
    elif corruption == "prediction":
        body["items"][0]["predicted"] = {"person_visible": True}
    else:
        body["items"][0]["frames"][0]["product_witnesses"] = None
    with pytest.raises(ValueError):
        seal_annotations(packet, body, ledger, tmp_path / "not-created")
    assert not (tmp_path / "not-created").exists()


def test_assisted_annotation_cannot_fulfil_a_human_requirement(tmp_path):
    packet = annotation_packet(selection(), requirement="human_required")
    with pytest.raises(ValueError, match="human_annotations_required"):
        seal_annotations(
            packet,
            filled(packet, "assisted"),
            {"audit_calls_reserved": 0, "model_outputs_present": False},
            tmp_path / "no",
        )
    # A human declaration still has no automatic independent verification.
    sealed = seal_annotations(
        packet,
        filled(packet, "human"),
        {"audit_calls_reserved": 0, "model_outputs_present": False},
        tmp_path / "declared-human",
    )
    assert sealed["origin_independently_verified"] is False


def test_selection_commitment_is_exclusive_and_detects_metadata_mutation(tmp_path):
    value = selection()
    seal_selection(value, tmp_path / "private")
    with pytest.raises(FileExistsError):
        seal_selection(value, tmp_path / "private")
    changed = copy.deepcopy(value)
    changed["rows"][0]["sector"] = "moda"
    with pytest.raises(ValueError, match="commitment_changed"):
        commitment(changed, "selection_sha256")
    assert digest(value) != digest(changed)


@pytest.mark.parametrize("valid", [False, True])
def test_native_witness_domain_is_checked_before_annotation_seal(tmp_path, valid):
    packet = annotation_packet(selection())
    body = filled(packet)
    body["items"][0]["frames"][0]["product_witnesses"] = [
        {
            "state": "no_target" if valid else "not-a-frozen-state",
            "item_configuration": "absent",
            "presented_categories": [],
            "description": "Invented absence witness; not an image judgment.",
        }
    ]
    if valid:
        validate_annotations(packet, body)
    else:
        with pytest.raises(ValueError):
            seal_annotations(
                packet,
                body,
                {"audit_calls_reserved": 0, "model_outputs_present": False},
                tmp_path / "not-created",
            )
        assert not (tmp_path / "not-created").exists()

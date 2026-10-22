"""Private blind annotation seal; inference workers receive commitments, never GT."""

import json

from scripts.visual_validation_contract_v1 import (
    FIELDS,
    commitment,
    digest,
    require,
    timeline,
    write_new,
)
from scripts.vlm_product_v16 import decode as decode_witness


def template(packet):
    commitment(packet, "packet_sha256")
    return {
        "schema": "visual-blind-annotations-v1",
        "packet_sha256": packet["packet_sha256"],
        "declared_origin": "unfilled",
        "human_reference": None,
        "items": [
            {
                "alias": item["alias"],
                "frames": [
                    {
                        "index": i,
                        "seconds": s,
                        "png_sha256": h,
                        "fields": dict.fromkeys(FIELDS),
                        "product_witnesses": None,
                        "support_notes": "",
                    }
                    for i, (s, h) in enumerate(
                        zip(item["frame_seconds"], item["frame_sha256"], strict=True), 1
                    )
                ],
            }
            for item in packet["items"]
        ],
    }


def validate_annotations(packet, annotations):
    commitment(packet, "packet_sha256")
    require(
        type(annotations) is dict
        and set(annotations)
        == {"schema", "packet_sha256", "declared_origin", "human_reference", "items"},
        "visual_annotation_fields",
    )
    require(
        annotations["schema"] == "visual-blind-annotations-v1"
        and annotations["packet_sha256"] == packet["packet_sha256"],
        "visual_annotation_packet_mismatch",
    )
    origin = annotations["declared_origin"]
    require(origin in ("assisted", "human", "synthetic"), "visual_unfilled_annotation_origin")
    if packet["annotation_requirement"] == "human_required":
        require(origin == "human", "visual_human_annotations_required")
    reference = annotations["human_reference"]
    require(
        (origin == "human" and type(reference) is str and 1 <= len(reference) <= 300)
        or (origin != "human" and reference is None),
        "visual_annotation_origin_reference",
    )
    require(
        type(annotations["items"]) is list
        and len(annotations["items"]) == len(packet["items"]) == 32,
        "visual_annotation_count",
    )
    for item, expected in zip(annotations["items"], packet["items"], strict=True):
        require(
            type(item) is dict
            and set(item) == {"alias", "frames"}
            and item["alias"] == expected["alias"],
            "visual_annotation_alias_mismatch",
        )
        timeline(expected["frame_seconds"], expected["frame_sha256"])
        frames = item["frames"]
        require(
            type(frames) is list and len(frames) == len(expected["frame_seconds"]),
            "visual_annotation_frame_count",
        )
        for index, (frame, seconds, sha) in enumerate(
            zip(frames, expected["frame_seconds"], expected["frame_sha256"], strict=True), 1
        ):
            require(
                type(frame) is dict
                and set(frame)
                == {
                    "index",
                    "seconds",
                    "png_sha256",
                    "fields",
                    "product_witnesses",
                    "support_notes",
                },
                "visual_annotation_unexpected_fields",
            )
            require(
                type(frame["index"]) is int
                and frame["index"] == index
                and type(frame["seconds"]) in (int, float)
                and frame["seconds"] == seconds
                and frame["png_sha256"] == sha,
                "visual_annotation_frame_identity",
            )
            fields = frame["fields"]
            require(
                type(fields) is dict
                and set(fields) == set(FIELDS)
                and all(type(v) is bool or v == "unknown" for v in fields.values()),
                "visual_annotation_values_unfilled_or_invalid",
            )
            require(
                type(frame["support_notes"]) is str and len(frame["support_notes"]) <= 1024,
                "visual_annotation_notes_limit",
            )
            witnesses = frame["product_witnesses"]
            require(
                type(witnesses) is list and len(witnesses) <= 22,
                "visual_product_witnesses_unfilled",
            )
            for witness in witnesses:
                require(
                    type(witness) is dict
                    and set(witness)
                    == {"state", "item_configuration", "presented_categories", "description"},
                    "visual_product_witness_shape",
                )
                require(
                    all(
                        type(witness[k]) is str and 1 <= len(witness[k]) <= 100
                        for k in ("state", "item_configuration")
                    )
                    and type(witness["presented_categories"]) is list
                    and len(witness["presented_categories"]) <= 5
                    and all(
                        type(c) is str and 1 <= len(c) <= 100
                        for c in witness["presented_categories"]
                    )
                    and len(witness["presented_categories"])
                    == len(set(witness["presented_categories"]))
                    and type(witness["description"]) is str
                    and 1 <= len(witness["description"]) <= 1024,
                    "visual_product_witness_invalid",
                )
                native = {
                    k: witness[k] for k in ("state", "item_configuration", "presented_categories")
                }
                decode_witness(json.dumps(native), "state_first")
    return annotations


def seal_annotations(packet, annotations, audit_ledger, directory):
    validate_annotations(packet, annotations)
    require(
        type(audit_ledger) is dict
        and set(audit_ledger) == {"audit_calls_reserved", "model_outputs_present"}
        and type(audit_ledger["audit_calls_reserved"]) is int
        and audit_ledger["audit_calls_reserved"] == 0
        and audit_ledger["model_outputs_present"] is False,
        "visual_annotations_must_precede_audit",
    )
    # No human or assisted declaration is automatically certified by this writer.
    checksum = write_new(directory / "annotations-private.json", annotations)
    value = {
        "schema": "visual-blind-annotation-commitment-v1",
        "selection_sha256": packet["selection_sha256"],
        "packet_sha256": packet["packet_sha256"],
        "annotations_file_sha256": checksum,
        "annotations_content_sha256": digest(annotations),
        "sample_count": 32,
        "declared_origin": annotations["declared_origin"],
        "annotation_requirement": packet["annotation_requirement"],
        "origin_independently_verified": False,
        "human_review_verified": False,
        "independent_review_required": True,
        "execution_authorized": False,
    }
    value["commitment_sha256"] = digest(value)
    write_new(directory / "annotation-commitment.json", value)
    return value

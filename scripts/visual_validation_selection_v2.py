"""Two-phase blind-audit selection over projected metadata; no corpus/media IO or dispatch."""

import math
from collections import Counter, defaultdict

from scripts.visual_validation_contract_v1 import (
    PROPOSAL_SHA256,
    commitment,
    digest,
    identifier,
    is_sha,
    require,
    timeline,
    write_new,
)
from scripts.visual_validation_selection_v1 import PROTOCOL, annotation_packet, order_hash

IDENTITY_KEYS = {"sample_id", "channel_id", "sector", "partition", "media_sha256"}
EXPECTED_KEYS = {"sample_id", "media_sha256", "properties_sha256", "sheet_sha256", "frame_seconds"}
RECEIPT_KEYS = {
    "sample_id",
    "reacquired_media_sha256",
    "properties_sha256",
    "sheet_sha256",
    "frame_seconds",
    "frame_sha256",
    "pts_proof_sha256",
    "bridge_receipt_sha256",
    "cleanup_confirmed",
    "acquisition_kind",
    "acquisition_number",
}
ID_PLAN_KEYS = {
    "schema",
    "protocol",
    "proposal_sha256",
    "candidate_sha256",
    "data_kind",
    "training_projection_sha256",
    "exclusions_sha256",
    "exclusion_source_sha256",
    "rows",
    "acquisitions_max",
    "audit_calls_max",
    "audit_calls_exact",
    "frames_frozen",
    "independent_exclusion_review_required",
    "execution_authorized",
    "id_selection_sha256",
}
EXPECTATION_PLAN_KEYS = {
    "schema",
    "id_selection_sha256",
    "candidate_sha256",
    "data_kind",
    "source_sha256",
    "rows",
    "live_ledger_independently_verified",
    "execution_authorized",
    "expectations_sha256",
}
READY_KEYS = {
    "schema",
    "selection_process",
    "protocol",
    "proposal_sha256",
    "candidate_sha256",
    "data_kind",
    "id_selection_sha256",
    "expectations_sha256",
    "frame_receipts_sha256",
    "training_projection_sha256",
    "exclusions_sha256",
    "exclusion_source_sha256",
    "rows",
    "audit_calls_exact",
    "frames_frozen",
    "independent_exclusion_review_required",
    "independent_media_review_required",
    "media_proof_files_opened_by_selector",
    "pts_proof_sha256",
    "bridge_receipt_sha256",
    "execution_authorized",
    "selection_sha256",
    "acquisitions_reserved",
    "existing_local_cases",
    "acquisition_provenance_independently_verified",
}


def _source_map(value):
    require(
        type(value) is dict
        and value
        and all(type(k) is str and is_sha(v) for k, v in value.items()),
        "visual_provenance_hashes_required",
    )


def _times(seconds):
    require(
        type(seconds) is list
        and 1 <= len(seconds) <= 4
        and all(type(s) in (int, float) and math.isfinite(s) and s >= 0 for s in seconds)
        and seconds == sorted(set(seconds)),
        "visual_frame_times_invalid",
    )


def _expected_row(row):
    require(
        type(row) is dict
        and set(row) == EXPECTED_KEYS
        and identifier(row["sample_id"])
        and all(is_sha(row[k]) for k in ("media_sha256", "properties_sha256", "sheet_sha256")),
        "visual_expected_metadata_fields",
    )
    _times(row["frame_seconds"])


def _expectation_plan(value):
    commitment(value, "expectations_sha256")
    require(
        set(value) == EXPECTATION_PLAN_KEYS
        and value["schema"] == "visual-audit-frame-expectations-v2"
        and value["execution_authorized"] is False
        and value["live_ledger_independently_verified"] is False
        and value["data_kind"] in ("synthetic", "observed")
        and all(
            is_sha(value[k]) for k in ("id_selection_sha256", "candidate_sha256", "source_sha256")
        )
        and type(value["rows"]) is list
        and len(value["rows"]) == 32,
        "visual_expected_metadata_required",
    )
    for row in value["rows"]:
        _expected_row(row)
    require(len({r["sample_id"] for r in value["rows"]}) == 32, "visual_duplicate_expected_id")


def _unobserved_audit(ledger, *, before_acquisition=False):
    require(
        type(ledger) is dict
        and set(ledger)
        == {"acquisitions_reserved", "audit_calls_reserved", "model_outputs_present"}
        and type(ledger["acquisitions_reserved"]) is int
        and 0 <= ledger["acquisitions_reserved"] <= 32
        and type(ledger["audit_calls_reserved"]) is int
        and ledger["audit_calls_reserved"] == 0
        and ledger["model_outputs_present"] is False,
        "visual_two_phase_must_precede_audit",
    )
    if before_acquisition:
        require(
            ledger["acquisitions_reserved"] == 0,
            "visual_expected_metadata_must_precede_acquisition",
        )


def _exclusions(value):
    require(
        type(value) is dict
        and set(value) == {"sample_ids", "channel_ids", "media_sha256", "source_sha256"},
        "visual_exclusions_required",
    )
    for key in ("sample_ids", "channel_ids", "media_sha256"):
        require(
            type(value[key]) is list
            and all(type(v) is str for v in value[key])
            and len(value[key]) == len(set(value[key])),
            "visual_invalid_exclusions",
        )
    require(
        all(identifier(s) for s in value["sample_ids"] + value["channel_ids"])
        and all(is_sha(s) for s in value["media_sha256"])
        and type(value["source_sha256"]) is dict
        and value["source_sha256"]
        and all(type(k) is str and is_sha(v) for k, v in value["source_sha256"].items()),
        "visual_exclusion_provenance_required",
    )


def _identity(row):
    require(
        type(row) is dict and set(row) == IDENTITY_KEYS, "visual_identity_only_metadata_required"
    )
    require(row["partition"] == "train", "visual_mixed_or_reserved_metadata_refused")
    require(
        identifier(row["sample_id"])
        and identifier(row["channel_id"])
        and row["sector"] in ("beleza", "moda")
        and is_sha(row["media_sha256"]),
        "visual_training_identity_invalid",
    )


def select_identities(metadata, exclusions, *, candidate_sha256):
    """Freeze the original ranking using only 203 training identities, before frames exist."""
    require(
        type(metadata) is dict
        and set(metadata)
        == {"schema", "cohort_size", "split_counts", "source_sha256", "data_kind", "rows"}
        and metadata["schema"] == "visual-audit-training-identities-v2"
        and type(metadata["cohort_size"]) is int
        and metadata["cohort_size"] == 300
        and metadata["split_counts"] == {"train": 203, "validation": 66, "test": 31}
        and is_sha(metadata["source_sha256"])
        and metadata["data_kind"] in ("observed", "synthetic")
        and is_sha(candidate_sha256),
        "visual_training_identity_projection_required",
    )
    require(
        type(metadata["rows"]) is list and len(metadata["rows"]) == 203,
        "visual_training_203_required",
    )
    _exclusions(exclusions)
    groups = {s: defaultdict(list) for s in ("beleza", "moda")}
    seen = set()
    for row in metadata["rows"]:
        _identity(row)
        require(row["sample_id"] not in seen, "visual_duplicate_training_id")
        seen.add(row["sample_id"])
        if (
            row["sample_id"] in exclusions["sample_ids"]
            or row["channel_id"] in exclusions["channel_ids"]
            or row["media_sha256"] in exclusions["media_sha256"]
        ):
            continue
        groups[row["sector"]][row["channel_id"]].append(row)
    selected, used = [], set()
    for sector in ("beleza", "moda"):
        before = len(selected)
        for channel in sorted(groups[sector], key=lambda c: (order_hash(PROTOCOL, sector, c), c)):
            if channel in used:
                continue
            row = min(
                groups[sector][channel],
                key=lambda r: (order_hash(PROTOCOL, r["sample_id"]), r["sample_id"]),
            )
            selected.append(
                dict(row, alias="case-" + order_hash(PROTOCOL, "annotation", row["sample_id"])[:24])
            )
            used.add(channel)
            if len(selected) - before == 16:
                break
        require(len(selected) - before == 16, "visual_insufficient_unrevealed_channels")
    body = {
        "schema": "visual-audit-id-selection-v2",
        "protocol": PROTOCOL,
        "proposal_sha256": PROPOSAL_SHA256,
        "candidate_sha256": candidate_sha256,
        "data_kind": metadata["data_kind"],
        "training_projection_sha256": digest(metadata),
        "exclusions_sha256": digest(exclusions),
        "exclusion_source_sha256": dict(exclusions["source_sha256"]),
        "rows": selected,
        "acquisitions_max": 32,
        "audit_calls_max": 384,
        "audit_calls_exact": None,
        "frames_frozen": False,
        "independent_exclusion_review_required": True,
        "execution_authorized": False,
    }
    return body | {"id_selection_sha256": digest(body)}


def _id_plan(value):
    commitment(value, "id_selection_sha256")
    require(
        set(value) == ID_PLAN_KEYS
        and value["schema"] == "visual-audit-id-selection-v2"
        and value["proposal_sha256"] == PROPOSAL_SHA256
        and value["protocol"] == PROTOCOL
        and is_sha(value["candidate_sha256"])
        and value["data_kind"] in ("observed", "synthetic")
        and value["execution_authorized"] is False
        and value["frames_frozen"] is False
        and value["audit_calls_exact"] is None
        and value["acquisitions_max"] == 32
        and value["audit_calls_max"] == 384
        and value["independent_exclusion_review_required"] is True
        and is_sha(value["training_projection_sha256"])
        and is_sha(value["exclusions_sha256"]),
        "visual_id_plan_not_a_frame_selection",
    )
    _source_map(value["exclusion_source_sha256"])
    rows = value["rows"]
    require(type(rows) is list and len(rows) == 32, "visual_id_selection_shape")
    for row in rows:
        require(
            type(row) is dict and set(row) == IDENTITY_KEYS | {"alias"},
            "visual_identity_only_metadata_required",
        )
        _identity({k: row[k] for k in IDENTITY_KEYS})
        require(
            row["alias"] == "case-" + order_hash(PROTOCOL, "annotation", row["sample_id"])[:24],
            "visual_alias_changed",
        )
    require(
        Counter(r["sector"] for r in rows) == {"beleza": 16, "moda": 16}
        and len({r["sample_id"] for r in rows}) == len({r["channel_id"] for r in rows}) == 32,
        "visual_id_selection_shape",
    )
    return rows


def freeze_media_expectations(selection, metadata, ledger):
    """Selected-only historical metadata; expectation seal precedes any acquisition."""
    rows = _id_plan(selection)
    _unobserved_audit(ledger, before_acquisition=True)
    require(
        type(metadata) is dict
        and set(metadata) == {"schema", "id_selection_sha256", "source_sha256", "data_kind", "rows"}
        and metadata["schema"] == "visual-audit-selected-media-metadata-v2"
        and metadata["id_selection_sha256"] == selection["id_selection_sha256"]
        and metadata["data_kind"] == selection["data_kind"]
        and is_sha(metadata["source_sha256"]),
        "visual_selected_expectations_required",
    )
    require(
        type(metadata["rows"]) is list and len(metadata["rows"]) == 32,
        "visual_selected_expectation_count",
    )
    expected = {}
    for row in metadata["rows"]:
        _expected_row(row)
        require(row["sample_id"] not in expected, "visual_duplicate_expected_id")
        expected[row["sample_id"]] = row
    require(set(expected) == {r["sample_id"] for r in rows}, "visual_expected_id_substitution")
    require(
        all(expected[r["sample_id"]]["media_sha256"] == r["media_sha256"] for r in rows),
        "visual_expected_media_changed",
    )
    body = {
        "schema": "visual-audit-frame-expectations-v2",
        "id_selection_sha256": selection["id_selection_sha256"],
        "candidate_sha256": selection["candidate_sha256"],
        "data_kind": selection["data_kind"],
        "source_sha256": metadata["source_sha256"],
        "rows": [dict(expected[r["sample_id"]]) for r in rows],
        "live_ledger_independently_verified": False,
        "execution_authorized": False,
    }
    return body | {"expectations_sha256": digest(body)}


def bind_acquired_frames(selection, expectations, receipts, ledger):
    """Bind only the chosen 32 after media verification and before annotation/model outputs."""
    rows = _id_plan(selection)
    _unobserved_audit(ledger)
    _expectation_plan(expectations)
    require(
        expectations["schema"] == "visual-audit-frame-expectations-v2"
        and expectations["id_selection_sha256"] == selection["id_selection_sha256"]
        and expectations["candidate_sha256"] == selection["candidate_sha256"]
        and expectations["data_kind"] == selection["data_kind"]
        and expectations["execution_authorized"] is False,
        "visual_expectations_binding_changed",
    )
    expected_rows = expectations["rows"]
    require(
        type(expected_rows) is list
        and len(expected_rows) == 32
        and [r["sample_id"] for r in expected_rows] == [r["sample_id"] for r in rows],
        "visual_expected_selection_order_changed",
    )
    require(
        type(receipts) is dict
        and set(receipts)
        == {"schema", "id_selection_sha256", "expectations_sha256", "data_kind", "rows"}
        and receipts["schema"] == "visual-audit-acquisition-receipts-v2"
        and receipts["id_selection_sha256"] == selection["id_selection_sha256"]
        and receipts["expectations_sha256"] == expectations["expectations_sha256"]
        and receipts["data_kind"] == selection["data_kind"],
        "visual_acquired_receipts_binding",
    )
    require(
        type(receipts["rows"]) is list and len(receipts["rows"]) == 32,
        "visual_acquired_frame_case_count",
    )
    acquired = {}
    acquisition_numbers = []
    for row in receipts["rows"]:
        require(
            type(row) is dict
            and set(row) == RECEIPT_KEYS
            and identifier(row["sample_id"])
            and row["cleanup_confirmed"] is True
            and all(
                is_sha(row[k])
                for k in (
                    "reacquired_media_sha256",
                    "properties_sha256",
                    "sheet_sha256",
                    "pts_proof_sha256",
                    "bridge_receipt_sha256",
                )
            ),
            "visual_acquired_frame_receipt_fields",
        )
        require(
            row["acquisition_kind"] in ("reacquired", "already_local"), "visual_acquisition_kind"
        )
        if row["acquisition_kind"] == "reacquired":
            require(
                type(row["acquisition_number"]) is int and 1 <= row["acquisition_number"] <= 32,
                "visual_acquisition_number",
            )
            acquisition_numbers.append(row["acquisition_number"])
        else:
            require(row["acquisition_number"] is None, "visual_local_media_has_no_new_acquisition")
        timeline(row["frame_seconds"], row["frame_sha256"])
        require(row["sample_id"] not in acquired, "visual_duplicate_acquired_id")
        acquired[row["sample_id"]] = row
    require(set(acquired) == {r["sample_id"] for r in rows}, "visual_acquired_id_substitution")
    require(
        len(acquisition_numbers) == ledger["acquisitions_reserved"]
        and sorted(acquisition_numbers) == list(range(1, len(acquisition_numbers) + 1)),
        "visual_acquisition_ledger_mismatch",
    )
    ready = []
    for identity, expected in zip(rows, expected_rows, strict=True):
        observed = acquired[identity["sample_id"]]
        require(
            observed["reacquired_media_sha256"]
            == expected["media_sha256"]
            == identity["media_sha256"]
            and observed["properties_sha256"] == expected["properties_sha256"]
            and observed["sheet_sha256"] == expected["sheet_sha256"]
            and observed["frame_seconds"] == expected["frame_seconds"],
            "visual_acquired_media_or_frame_identity_changed",
        )
        ready.append(
            dict(
                identity,
                frame_seconds=list(observed["frame_seconds"]),
                frame_sha256=list(observed["frame_sha256"]),
            )
        )
    body = {
        "schema": "visual-audit-selection-v1",
        "selection_process": "two-phase-v2",
        "protocol": PROTOCOL,
        "proposal_sha256": PROPOSAL_SHA256,
        "candidate_sha256": selection["candidate_sha256"],
        "data_kind": selection["data_kind"],
        "id_selection_sha256": selection["id_selection_sha256"],
        "expectations_sha256": expectations["expectations_sha256"],
        "frame_receipts_sha256": digest(receipts),
        "training_projection_sha256": selection["training_projection_sha256"],
        "exclusions_sha256": selection["exclusions_sha256"],
        "exclusion_source_sha256": dict(selection["exclusion_source_sha256"]),
        "rows": ready,
        "audit_calls_exact": 3 * sum(len(r["frame_seconds"]) for r in ready),
        "frames_frozen": True,
        "independent_exclusion_review_required": True,
        "independent_media_review_required": True,
        "acquisitions_reserved": ledger["acquisitions_reserved"],
        "existing_local_cases": 32 - len(acquisition_numbers),
        "acquisition_provenance_independently_verified": False,
        "media_proof_files_opened_by_selector": False,
        "pts_proof_sha256": [acquired[r["sample_id"]]["pts_proof_sha256"] for r in rows],
        "bridge_receipt_sha256": [acquired[r["sample_id"]]["bridge_receipt_sha256"] for r in rows],
        "execution_authorized": False,
    }
    require(96 <= body["audit_calls_exact"] <= 384, "visual_exact_call_budget")
    return body | {"selection_sha256": digest(body)}


def _ready(selection):
    commitment(selection, "selection_sha256")
    require(
        set(selection) == READY_KEYS
        and selection.get("schema") == "visual-audit-selection-v1"
        and selection.get("selection_process") == "two-phase-v2"
        and selection.get("protocol") == PROTOCOL
        and selection.get("proposal_sha256") == PROPOSAL_SHA256
        and selection.get("data_kind") in ("observed", "synthetic")
        and selection.get("frames_frozen") is True
        and selection.get("execution_authorized") is False
        and selection.get("independent_exclusion_review_required") is True
        and selection.get("independent_media_review_required") is True
        and selection.get("media_proof_files_opened_by_selector") is False,
        "visual_frames_not_frozen",
    )
    require(
        all(
            is_sha(selection[k])
            for k in (
                "candidate_sha256",
                "id_selection_sha256",
                "expectations_sha256",
                "frame_receipts_sha256",
                "training_projection_sha256",
                "exclusions_sha256",
            )
        )
        and type(selection["rows"]) is list
        and len(selection["rows"]) == 32,
        "visual_frame_selection_lineage",
    )
    _source_map(selection["exclusion_source_sha256"])
    require(
        type(selection["acquisitions_reserved"]) is int
        and 0 <= selection["acquisitions_reserved"] <= 32
        and type(selection["existing_local_cases"]) is int
        and selection["existing_local_cases"] == 32 - selection["acquisitions_reserved"]
        and selection["acquisition_provenance_independently_verified"] is False,
        "visual_acquisition_provenance_required",
    )
    for row in selection["rows"]:
        require(
            type(row) is dict
            and set(row) == IDENTITY_KEYS | {"alias", "frame_seconds", "frame_sha256"},
            "visual_frame_selection_fields",
        )
        _identity({k: row[k] for k in IDENTITY_KEYS})
        require(
            row["alias"] == "case-" + order_hash(PROTOCOL, "annotation", row["sample_id"])[:24],
            "visual_alias_changed",
        )
        timeline(row["frame_seconds"], row["frame_sha256"])
    require(
        len({r["sample_id"] for r in selection["rows"]})
        == len({r["alias"] for r in selection["rows"]})
        == 32,
        "visual_duplicate_frame_case",
    )
    require(
        type(selection["audit_calls_exact"]) is int
        and selection["audit_calls_exact"]
        == 3 * sum(len(r["frame_seconds"]) for r in selection["rows"])
        and 96 <= selection["audit_calls_exact"] <= 384,
        "visual_exact_call_budget",
    )
    for key in ("pts_proof_sha256", "bridge_receipt_sha256"):
        require(
            type(selection[key]) is list
            and len(selection[key]) == 32
            and all(is_sha(h) for h in selection[key]),
            "visual_media_proof_reference",
        )


def ready_annotation_packet(selection, *, requirement="assisted_review_allowed"):
    _ready(selection)
    packet = annotation_packet(selection, requirement=requirement)
    # Preserve synthetic provenance while still withholding IDs, sectors, sources and GT.
    body = {k: v for k, v in packet.items() if k != "packet_sha256"}
    body["data_kind"] = selection["data_kind"]
    return body | {"packet_sha256": digest(body)}


def require_observed_selection(selection):
    commitment(selection, "selection_sha256")
    require(selection.get("data_kind") == "observed", "visual_synthetic_selection_not_observed")
    ready_annotation_packet(selection)
    return selection


def seal_ids(selection, directory):
    _id_plan(selection)
    return write_new(directory / "selection-ids.json", selection)


def seal_expectations(expectations, directory):
    _expectation_plan(expectations)
    return write_new(directory / "media-expectations.json", expectations)


def seal_frames(selection, directory, ledger):
    _unobserved_audit(ledger)
    ready_annotation_packet(selection)
    require(
        selection["acquisitions_reserved"] == ledger["acquisitions_reserved"],
        "visual_acquisition_ledger_mismatch",
    )
    return write_new(directory / "selection-frames.json", selection)

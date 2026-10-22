"""Bind the versioned sidecar to batch execution authority, preserving scientific gates."""

from scripts.visual_validation_batch_v1 import read_dispatch_receipt
from scripts.visual_validation_contract_v1 import digest, read_json, require
from scripts.visual_validation_sidecar_v1 import build_sidecar


def build_batch_sidecar(case, frame_calls, *, root, candidate_sha256):
    original = build_sidecar(case, frame_calls, root=root, candidate_sha256=candidate_sha256)
    receipts = []
    for call in original["calls"]:
        receipt = read_dispatch_receipt(root, call["call_id"])
        require(
            receipt["stage"] == "audit"
            and receipt["alias"] == case["alias"]
            and receipt["frame_index"] == call["frame"]
            and receipt["kind"] == call["kind"]
            and receipt["capture_result_sha256"] == call["result_sha256"],
            "visual_sidecar_dispatch_binding",
        )
        configuration = read_json(
            root / "data/private/issue-4-visual-validation-run-v1/configuration-audit.json"
        )
        selected = [
            row for row in configuration["selection"]["rows"] if row["alias"] == case["alias"]
        ]
        require(
            len(selected) == 1
            and all(
                selected[0][key] == case[key]
                for key in ("partition", "media_sha256", "frame_seconds", "frame_sha256")
            )
            and configuration["candidate_sha256"] == candidate_sha256,
            "visual_sidecar_candidate_changed",
        )
        receipts.append(receipt)
    kinds = {r["data_kind"] for r in receipts}
    require(len(kinds) == 1, "visual_mixed_capture_provenance")
    kind = kinds.pop()
    value = {k: v for k, v in original.items() if k != "sidecar_sha256"}
    value.update(
        schema_version="visual-validation-batch-sidecar-v1",
        data_kind=kind,
        capture_origin="reviewed_batch_receipts",
        native_execution_verified=kind == "observed"
        and all(r["native_execution_verified"] is True for r in receipts),
        dispatch_receipts_sha256=[digest(r) for r in receipts],
    )
    # Execution provenance is never a perceptual acceptance or a QualityRelease.
    require(
        value["approved_for_training"] is False and value["quality_release_sha256"] is None,
        "visual_no_automatic_quality_release",
    )
    return value | {"sidecar_sha256": digest(value)}

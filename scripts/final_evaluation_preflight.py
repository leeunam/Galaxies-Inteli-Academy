"""Metadata-only P6 readiness check; no cohort/model loader or execution authority."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

PROCEDURE_ID = "p6-final-procedure-v1"
SPLIT_COUNTS = {"train": 203, "validation": 66, "test": 31}
REQUIRED_IDENTITIES = (
    "cohort_manifest_sha256",
    "partition_manifest_sha256",
    "development_feature_manifest_sha256",
    "test_feature_contract_sha256",
    "baseline_artifact_sha256",
    "a300_artifact_sha256",
    "b_complete_artifact_sha256",
    "c_complete_artifact_sha256",
    "bc_comparison_receipt_sha256",
    "visual_audit_acceptance_receipt_sha256",
    "explanation_adherence_acceptance_receipt_sha256",
    "development_integration_receipt_sha256",
    "selected_configuration_sha256",
)
REQUIRED_GATES = (
    "same_300_cohort_and_splits",
    "visual_audit_accepted",
    "bc_complete_accepted",
    "explanation_adherence_accepted",
    "development_integration_accepted",
    "selection_validation_only",
    "holdout_closed",
)
_FIELDS = {"schema_version", "procedure_id", "cohort_size", "split_counts", "identities", "gates"}


def assess_readiness(metadata: object) -> dict:
    """Inspect supplied declarations only; a digest's spelling is not its verification."""
    blockers = []
    if not isinstance(metadata, dict):
        metadata = {}
        blockers.append("invalid_metadata")
    if set(metadata) - _FIELDS:
        blockers.append("unexpected_metadata_fields")
    if metadata.get("schema_version") != "final-evaluation-readiness-v1":
        blockers.append("invalid_schema")
    if metadata.get("procedure_id") != PROCEDURE_ID:
        blockers.append("procedure_mismatch")
    if metadata.get("cohort_size") != 300 or metadata.get("split_counts") != SPLIT_COUNTS:
        blockers.append("cohort_or_splits_mismatch")
    identities = metadata.get("identities", {})
    gates = metadata.get("gates", {})
    if not isinstance(identities, dict):
        identities = {}
        blockers.append("invalid_identities")
    if not isinstance(gates, dict):
        gates = {}
        blockers.append("invalid_gates")
    if set(identities) - set(REQUIRED_IDENTITIES) or set(gates) - set(REQUIRED_GATES):
        blockers.append("unexpected_prerequisite_fields")
    for name in REQUIRED_IDENTITIES:
        value = identities.get(name)
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            blockers.append(f"missing_or_invalid:{name}")
    for name in REQUIRED_GATES:
        if gates.get(name) is not True:
            blockers.append(f"not_accepted:{name}")
    return {
        "procedure_id": PROCEDURE_ID,
        "status": "blocked" if blockers else "metadata_complete_requires_independent_review",
        "blockers": blockers,
        "identities_verified": False,
        "holdout_access_authorized": False,
        "inference_authorized": False,
        "holdout_opened": False,
        "inference_executed": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        # This one file must contain declarations only, never assignments/labels/features.
        with args.metadata.open("rb") as stream:
            raw = stream.read(16_385)
        if len(raw) > 16_384:
            raise ValueError("metadata_too_large")
        result = assess_readiness(json.loads(raw))
    except (OSError, ValueError, RecursionError):
        print(json.dumps({"status": "blocked", "code": "invalid_readiness_metadata"}))
        return 2
    print(json.dumps(result, indent=2, allow_nan=False))
    return 2 if result["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Read-only review of the named 23/10 cached-flow archive, never its inputs.

Opens only six named report/receipt/script/text files. Does not execute the archived
script, follow feature/run pointers, read media or labels, or load model weights.
Outputs new aggregates and presentation in a fresh operator-selected directory.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path

from scripts.explanation_display import render_explanation
from scripts.explanation_review_v1 import review_recorded, review_sufficiency

RECEIPT_SHA = "06664bbcefe66450e7704bc1510fe012baa11877d0a4809bbc8b5155b9227b67"
CLOSING_SHA = "a2b2f60da177696f8a754b7e6b880964fd1f992a7e34e8660c9b53c947a279dd"
NAMES = (
    "cached-features-receipt.json",
    "closing-results.json",
    "cached-features-report.json",
    "run_cached_features_flow.py",
    "cached-features-report.txt",
    "cached-features-report-copy-fixed.txt",
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def review_archive(folder: Path, output: Path):
    source = {name: (folder / name).read_bytes() for name in NAMES}
    hashes = {name: sha(raw) for name, raw in source.items()}
    if hashes[NAMES[0]] != RECEIPT_SHA or hashes[NAMES[1]] != CLOSING_SHA:
        raise ValueError("archive_receipt_identity_mismatch")
    receipt = json.loads(source[NAMES[0]])
    closing = json.loads(source[NAMES[1]])
    for field, name in (
        ("report_sha256", NAMES[2]),
        ("script_sha256", NAMES[3]),
        ("text_sha256", NAMES[4]),
    ):
        if hashes[name] != receipt[field]:
            raise ValueError("archive_output_identity_mismatch")
    for name in (NAMES[0], NAMES[2], NAMES[4], NAMES[5]):
        if hashes[name] != closing["files_sha256"][name]:
            raise ValueError("archive_closing_identity_mismatch")
    report = json.loads(source[NAMES[2]])
    selected = review_sufficiency(report)
    complete = review_sufficiency(report, show_local_evidence=True)
    fixed = source[NAMES[5]].decode("utf-8")
    if (
        fixed.partition("\n\n")[2].rstrip()
        != render_explanation(report, show_local_evidence=True).rstrip()
    ):
        raise ValueError("archive_display_content_mismatch")
    # No original campaign brief exists. This request only binds the stored
    # numerical IDs for a read-only local review; it is not a new campaign case.
    analysis = report["analysis"]
    request = {
        "campaign_id": analysis["campaign_id"],
        "creative_ids": [c["creative_id"] for c in analysis["candidates"]],
        "sector": analysis["sector"],
        "objective": analysis["objective"],
        "brief": "Read-only diagnostic review; original campaign brief unavailable.",
    }
    reviewed = review_recorded(
        report, request, show_local_evidence=True, input_origin="cached_features"
    )
    aggregate = {
        "schema_version": "front2-recorded-cached-flow-review-v1",
        "source_file_sha256": hashes,
        "review_code_sha256": {
            name: sha((Path(__file__).parent / name).read_bytes())
            for name in (
                "verify_front2_recorded_v1.py",
                "explanation_review_v1.py",
                "campaign_evidence_v1.py",
                "explanation_display.py",
                "explanation_evidence.py",
            )
        },
        "historical_run": {
            "case_count": receipt["case_count"],
            "packet_facts": receipt["packet_facts"],
            "training_index_samples": receipt["training_index_samples"],
            "seconds": receipt["seconds"],
            "phase_seconds": receipt["phase_seconds"],
            "media_to_features": receipt["media_to_features_executed"],
            "features_to_predictions": receipt["features_to_predictions_executed"],
            "SHAP": receipt["SHAP_executed"],
            "training_comparables": receipt["training_comparables_executed"],
            "local_packet_and_text": receipt["context_binding_and_local_text_executed"],
            "StateGraph": receipt["stategraph_executed_in_this_real_run"],
            "MCP": receipt["MCP_executed_in_this_real_run"],
            "external_requests": receipt["external_requests"],
            "holdout_opened": receipt["holdout_opened"],
        },
        "current_review": {
            "new_model_runs": 0,
            "new_extractions": 0,
            "new_external_calls": 0,
            "archive_replayed_not_reexecuted": True,
            "source_numbers_ranking_unchanged": reviewed["source_result"] == report,
            "original_fixed_display_verified": True,
            "request_origin": "reconstructed_diagnostic_not_campaign",
            "selected_output_sufficiency": selected.status,
            "local_catalogue_sufficiency": complete.status,
            "coverage": [
                {
                    "alias": f"C{i}",
                    "selected_shap": a.selected_shap_groups,
                    "available_shap": b.available_shap_groups,
                    "selected_references": a.selected_references,
                    "available_references": b.available_references,
                    "sufficient_local_catalogue": b.sufficient,
                }
                for i, (a, b) in enumerate(
                    zip(selected.candidates, complete.candidates, strict=True), 1
                )
            ],
            "adherence": reviewed["campaign_adherence"]["status"],
            "final_configuration_validated": False,
            "new_display_sha256": reviewed["display_sha256"],
        },
    }
    if any((folder / name).read_bytes() != source[name] for name in NAMES):
        raise ValueError("archive_changed_during_review")
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    for name, raw in (
        ("aggregate.json", json.dumps(aggregate, ensure_ascii=False, indent=2).encode() + b"\n"),
        ("reviewed-display.txt", reviewed["display_text"].encode()),
    ):
        fd = os.open(output / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
    return aggregate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = review_archive(args.archive, args.output)
    except Exception:  # noqa: BLE001 - private archive paths/inputs never printed
        print("Revisão não concluída; arquivo incompatível ou destino indisponível.")
        return 1
    print(json.dumps(result["current_review"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

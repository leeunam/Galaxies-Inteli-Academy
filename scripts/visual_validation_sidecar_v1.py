"""Versioned training-audit sidecar from bound captures; never a QualityRelease."""

from scripts.visual_validation_capture_v1 import read_capture
from scripts.visual_validation_contract_v1 import (
    FIELDS,
    PROPOSAL_SHA256,
    digest,
    identifier,
    is_sha,
    require,
    timeline,
)
from scripts.vlm_per_frame import aggregate

SCHEMA = "visual-validation-attribute-sidecar-v1"


def build_sidecar(case, frame_calls, *, root, candidate_sha256):
    require(
        type(case) is dict
        and set(case) == {"alias", "partition", "media_sha256", "frame_seconds", "frame_sha256"},
        "visual_sidecar_metadata_only",
    )
    require(
        case["partition"] == "train"
        and identifier(case["alias"])
        and is_sha(case["media_sha256"])
        and is_sha(candidate_sha256),
        "visual_sidecar_training_only",
    )
    timeline(case["frame_seconds"], case["frame_sha256"])
    require(
        type(frame_calls) is list and len(frame_calls) == len(case["frame_seconds"]),
        "visual_sidecar_frame_count",
    )
    seen, values, calls, declarations = set(), [], [], []
    for index, (mapping, png) in enumerate(zip(frame_calls, case["frame_sha256"], strict=True), 1):
        require(
            type(mapping) is dict and set(mapping) == set(FIELDS),
            "visual_three_attribute_calls_required",
        )
        frame = {}
        for kind in FIELDS:
            binding = mapping[kind]
            require(
                type(binding) is dict and set(binding) == {"call_id", "expected_tokens"},
                "visual_call_binding",
            )
            call_id = binding["call_id"]
            require(type(call_id) is int and call_id not in seen, "visual_call_reused")
            seen.add(call_id)
            captured = read_capture(
                root, call_id, kind=kind, png_sha256=png, expected_tokens=binding["expected_tokens"]
            )
            result = captured["result"]
            require(result["technical_success"] is True, "visual_incomplete_or_failed_capture")
            response = result["parsed_response"]
            if kind == "product_visible_early":
                frame[kind] = response["value"]
                declarations.append(
                    {
                        "frame": index,
                        "native": response["native"],
                        "support_independently_reviewed": False,
                    }
                )
            else:
                frame[kind] = response[kind]
            calls.append(
                {
                    "frame": index,
                    "kind": kind,
                    "call_id": call_id,
                    "result_sha256": captured["result_sha256"],
                    "raw_sha256": captured["raw_sha256"],
                }
            )
        values.append(frame)
    value = {
        "schema_version": SCHEMA,
        "capture_origin": "injected_unreleased",
        "native_execution_verified": False,
        "proposal_sha256": PROPOSAL_SHA256,
        "candidate_sha256": candidate_sha256,
        "alias": case["alias"],
        "partition": "train",
        "media_sha256": case["media_sha256"],
        "input_policy": "contact-sheet-cell-320x330-v1",
        "input_frame_seconds": list(case["frame_seconds"]),
        "input_png_sha256": list(case["frame_sha256"]),
        "per_frame": values,
        "parsed": aggregate(values, case["frame_seconds"]),
        "native_product_declarations": declarations,
        "calls": calls,
        "approved_for_training": False,
        "released_fields": [],
        "quality_release_sha256": None,
        "test_evaluated": False,
        "requires_independent_blind_gate": True,
    }
    return value | {"sidecar_sha256": digest(value)}

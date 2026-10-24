"""Pure TRAIN32 scoring of all seven fields; never emits an extraction release."""

from __future__ import annotations

import json
from collections import Counter

from scripts.full_visual_contract_v7 import is_identifier, is_sha256
from scripts.visual_attributes_seven import BOOLEAN_FIELDS, FIELDS, parse_attributes

GATE = "visual-quality-seven-train32-v1"
BINDING_KEYS = {"alias", "sector", "partition", "channel_id", "sheet_sha256"}
ROW_KEYS = {
    "alias",
    "sector",
    "partition",
    "channel_id",
    "sheet_sha256",
    "frame_seconds",
    "annotated",
    "predicted",
}
SECTORS = ("beleza", "moda")


def _label(value):
    return ("true" if value else "false") if type(value) is bool else value


def _validate_bindings(expected_bindings):
    if type(expected_bindings) is not list or len(expected_bindings) != 32:
        raise ValueError("seven_invalid_expected_bindings")
    identities = {key: set() for key in ("alias", "sheet_sha256")}
    for row in expected_bindings:
        if type(row) is not dict or set(row) != BINDING_KEYS:
            raise ValueError("seven_invalid_expected_binding_shape")
        if type(row["partition"]) is not str or row["partition"] != "train":
            raise ValueError("seven_expected_bindings_require_train_only")
        if type(row["sector"]) is not str or row["sector"] not in SECTORS:
            raise ValueError("seven_expected_bindings_require_balanced_32_train")
        if not is_identifier(row["channel_id"]):
            raise ValueError("seven_invalid_expected_binding_identity")
        for key, seen in identities.items():
            valid = is_sha256(row[key]) if key == "sheet_sha256" else is_identifier(row[key])
            if not valid or row[key] in seen:
                raise ValueError("seven_invalid_or_duplicate_expected_binding_identity")
            seen.add(row[key])
    if Counter(row["sector"] for row in expected_bindings) != {"beleza": 16, "moda": 16}:
        raise ValueError("seven_expected_bindings_require_balanced_32_train")
    return {row["alias"]: row for row in expected_bindings}


def _validate_panel(observations, *, bindings_by_alias=None):
    if type(observations) is not list or len(observations) != 32:
        raise ValueError("seven_incomplete_panel_requires_balanced_32_train")
    identities = {key: set() for key in ("alias", "channel_id", "sheet_sha256")}
    for row in observations:
        if type(row) is not dict or set(row) != ROW_KEYS:
            raise ValueError("seven_invalid_observation_shape_no_outcomes_allowed")
        if row["partition"] != "train":
            raise ValueError("seven_panel_requires_train_only")
        if type(row["sector"]) is not str or row["sector"] not in SECTORS:
            raise ValueError("seven_incomplete_panel_requires_balanced_32_train")
        for key, seen in identities.items():
            valid = is_sha256(row[key]) if key == "sheet_sha256" else is_identifier(row[key])
            repeated = (
                valid
                and row[key] in seen
                and not (key == "channel_id" and bindings_by_alias is not None)
            )
            if not valid or repeated:
                raise ValueError("seven_invalid_or_duplicate_panel_identity")
            seen.add(row[key])
        if bindings_by_alias is not None:
            expected = bindings_by_alias.get(row["alias"])
            if expected is None or any(row[key] != expected[key] for key in BINDING_KEYS):
                raise ValueError("seven_observation_does_not_match_expected_binding")
        for key in ("annotated", "predicted"):
            if type(row[key]) is not dict:
                raise ValueError("seven_invalid_attribute_object")
            try:
                raw = json.dumps(row[key], allow_nan=False)
            except (ValueError, TypeError, OverflowError, RecursionError):
                raise ValueError("seven_invalid_attribute_object") from None
            parse_attributes(raw, row["frame_seconds"])
    if Counter(row["sector"] for row in observations) != {"beleza": 16, "moda": 16}:
        raise ValueError("seven_incomplete_panel_requires_balanced_32_train")


def evaluate_gate(observations):
    """Score declared annotations/predictions without IO or quality authority.

    All known predictions count in agreement, even rare categories. Unknown is an
    abstention, never an agreement credit. Frame evidence must be a nonempty subset
    of the independent annotation's evidence. This function cannot verify provenance,
    blinding, actual image content or review bindings; those require independent review.
    """
    _validate_panel(observations)
    return _score_panel(observations)


def evaluate_bound_gate(observations, expected_bindings):
    """Score TRAIN32 against a declared metadata table, preserving real channels.

    The five identity fields must match by alias. Repeated channels are allowed
    only as declared in that table. Scores use observation counts, not independent
    channel counts, and do not estimate general population accuracy. This pure
    function cannot authenticate the table, PNG files or partition provenance;
    the operator must verify manifests separately and obtain independent review.
    Annotated class support is an additional necessary check, not quality authority.
    """
    bindings_by_alias = _validate_bindings(expected_bindings)
    _validate_panel(observations, bindings_by_alias=bindings_by_alias)
    report = _score_panel(observations)
    channels = Counter(row["channel_id"] for row in observations)
    sectors = {}
    for sector in SECTORS:
        rows = [row for row in observations if row["sector"] == sector]
        sector_channels = Counter(row["channel_id"] for row in rows)
        sectors[sector] = {
            "samples": len(rows),
            "channels": len(sector_channels),
            "samples_per_channel": dict(sorted(sector_channels.items())),
        }
    report["panel_support"] = {
        "samples": len(observations),
        "channels": len(channels),
        "samples_per_channel": dict(sorted(channels.items())),
        "sectors": sectors,
        "channel_independence_assumed": False,
    }
    for field, column in report["columns"].items():
        support, sector_support, missing = _reference_support(observations, field)
        column["reference_value_support"] = support
        column["missing_reference_support"] = missing
        for sector, counts in sector_support.items():
            column["sectors"][sector]["reference_value_support"] = counts
        if missing:
            reason = (
                "insufficient_reference_boolean_class_support"
                if field in BOOLEAN_FIELDS
                else "insufficient_reference_category_support"
            )
            column["blocked_reasons"].append(reason)
            column["meets_thresholds"] = False
    report["passed_fields"] = [f for f in FIELDS if report["columns"][f]["meets_thresholds"]]
    report["blocked_fields"] = [f for f in FIELDS if not report["columns"][f]["meets_thresholds"]]
    report["status"] = "blocked" if report["blocked_fields"] else "all_seven_meet_thresholds"
    return report


def _reference_support(observations, field):
    """Count declared annotations only; unknown never supplies a known class."""
    labels = ("false", "true", "unknown") if field in BOOLEAN_FIELDS else ("unknown",)
    support = Counter({value: 0 for value in labels})
    sectors = {sector: Counter({value: 0 for value in labels}) for sector in SECTORS}
    for row in observations:
        value = _label(row["annotated"][field]["value"])
        support[value] += 1
        sectors[row["sector"]][value] += 1
    missing = []
    if field in BOOLEAN_FIELDS:
        for scope, counts, minimum in (
            ("global", support, 3),
            *((sector, sectors[sector], 1) for sector in SECTORS),
        ):
            for value in ("true", "false"):
                if counts[value] < minimum:
                    missing.append(
                        {
                            "reason": "reference_boolean_class_below_minimum",
                            "scope": scope,
                            "value": value,
                            "count": counts[value],
                            "minimum": minimum,
                        }
                    )
    else:
        retained = sorted(
            value for value, count in support.items() if value != "unknown" and count >= 3
        )
        if len(retained) < 2:
            missing.append(
                {
                    "reason": "fewer_than_two_reference_categories_with_three_samples",
                    "scope": "global",
                    "retained_values": retained,
                    "count": len(retained),
                    "minimum": 2,
                }
            )
    return (
        dict(sorted(support.items())),
        {sector: dict(sorted(counts.items())) for sector, counts in sectors.items()},
        missing,
    )


def _score_panel(observations):
    columns, passed_fields, blocked_fields = {}, [], []
    for field in FIELDS:
        support = Counter(_label(row["predicted"][field]["value"]) for row in observations)
        retained = sorted(
            value for value, count in support.items() if value != "unknown" and count >= 3
        )
        sectors = {}
        for sector in SECTORS:
            rows = [row for row in observations if row["sector"] == sector]
            confusion, counts = Counter(), Counter()
            known, correct, evidence_invalid = 0, 0, 0
            for row in rows:
                prediction, annotation = row["predicted"][field], row["annotated"][field]
                predicted, actual = _label(prediction["value"]), _label(annotation["value"])
                confusion[actual, predicted] += 1
                if predicted == "unknown":
                    continue
                known += 1
                counts[predicted] += 1
                evidence_ok = set(prediction["frames"]) <= set(annotation["frames"])
                evidence_invalid += not evidence_ok
                correct += predicted == actual and evidence_ok
            sectors[sector] = {
                "samples": len(rows),
                "known": known,
                "abstentions": len(rows) - known,
                "correct_value_and_evidence": correct,
                "incorrect_or_unverified": known - correct,
                "evidence_not_supported_by_annotation": evidence_invalid,
                "agreement": correct / known if known else None,
                "predicted_value_support": dict(sorted(counts.items())),
                "confusion": [
                    {"annotated": actual, "predicted": predicted, "count": count}
                    for (actual, predicted), count in sorted(confusion.items())
                ],
            }
        reasons = []
        if any(s["known"] < 12 for s in sectors.values()):
            reasons.append("insufficient_known_predictions_per_sector")
        # Integer comparison preserves the exact 90% denominator.
        if any(10 * s["correct_value_and_evidence"] < 9 * s["known"] for s in sectors.values()):
            reasons.append("value_and_evidence_agreement_below_90_percent")
        if any(s["evidence_not_supported_by_annotation"] for s in sectors.values()):
            reasons.append("unsupported_frame_evidence")
        if field in BOOLEAN_FIELDS:
            if any(support[value] < 3 for value in ("true", "false")) or any(
                s["predicted_value_support"].get(value, 0) < 1
                for s in sectors.values()
                for value in ("true", "false")
            ):
                reasons.append("insufficient_boolean_class_support")
        elif len(retained) < 2:
            reasons.append("insufficient_category_support")
        passed = not reasons
        (passed_fields if passed else blocked_fields).append(field)
        columns[field] = {
            "meets_thresholds": passed,
            "blocked_reasons": reasons,
            "retained_values": retained,
            "predicted_value_support": dict(sorted(support.items())),
            "sectors": sectors,
        }
    return {
        "gate": GATE,
        "status": "all_seven_meet_thresholds" if not blocked_fields else "blocked",
        "passed_fields": passed_fields,
        "blocked_fields": blocked_fields,
        "columns": columns,
        "quality_accepted": False,
        "release_emitted": False,
        "extraction269_allowed": False,
        "general_perception_accuracy_validated": False,
        "independent_bound_review_required": True,
        "predictive_outcomes_used": False,
    }

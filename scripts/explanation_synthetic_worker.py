"""Public invented fixture, no weights, registry, media or private data reads."""

import sys

from scripts.creative_contracts import (
    M1AnalysisResponse,
    M1Candidate,
    M1Extraction,
    M1Interval,
    M1Point,
    ObservedBaseline,
    Unavailable,
)
from scripts.empirical_baseline import EmpiricalSectorRange
from scripts.explanation_worker import Session, serve


def invented_report(payload):
    if payload != {}:
        raise ValueError("synthetic_probe_accepts_no_input")
    # These schema-shaped values are entirely fabricated, including all fingerprints.
    return M1AnalysisResponse(
        status="m1_prediction_available",
        campaign_id="entirely_invented_probe",
        sector="moda",
        mode="individual",
        learned_prediction_available=True,
        model_artifact_sha256="a" * 64,
        extractor_config_sha256="b" * 64,
        extraction_status="completed",
        baseline=ObservedBaseline(
            sector="moda",
            central_views=100.0,
            sector_range=EmpiricalSectorRange(
                lower_views=50.0,
                sector_median_views=100.0,
                upper_views=150.0,
            ),
            reference_samples=10,
            reference_channels=5,
            artifact_sha256="c" * 64,
            partition_manifest_sha256="d" * 64,
            cohort_release_sha256="e" * 64,
        ),
        candidates=[
            M1Candidate(
                creative_id="cr_" + "0" * 32,
                extraction=M1Extraction(status="completed", text_status="extracted"),
                prediction=M1Point(value=123.0),
                interval=M1Interval(lower_views=50.0, upper_views=200.0),
            )
        ],
        ranking=Unavailable(reason_code="individual_analysis"),
    ).model_dump(mode="json")


class SyntheticSession(Session):
    def __init__(self):
        super().__init__(invented_report)

    def handle(self, message):
        result = super().handle(message)
        result["fixture_entirely_invented"] = True
        return result


if __name__ == "__main__":
    serve(SyntheticSession(), sys.stdin.buffer, sys.stdout.buffer)

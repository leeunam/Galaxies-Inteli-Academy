"""Root-only worker tests: no new dependency or network in the frozen runtime."""

import io
import json

import pytest

from scripts.explanation_evidence import build_explanation_context
from scripts.explanation_worker import Session, serve
from tests.test_explanation_evidence import evidence_inputs  # noqa: F401
from tests.test_m1_service import serving  # noqa: F401


def test_worker_analyzes_once_and_validates_in_same_root_session(evidence_inputs):  # noqa: F811
    report, _, _ = evidence_inputs
    calls = []

    def analyze(payload):
        calls.append(payload)
        return report

    session = Session(analyze)
    prepared = session.handle({"op": "prepare", "payload": {"brief": "PRIVATE_BRIEF"}})
    context = build_explanation_context(report)
    assert prepared["packet_sha256"] == context.packet_sha256
    assert "PRIVATE_BRIEF" not in json.dumps(prepared)
    result = session.handle(
        {
            "op": "render",
            "selection": json.dumps(
                {"packet_sha256": prepared["packet_sha256"], "evidence_ids": ["c1_prediction"]}
            ),
            "reason": None,
        }
    )
    assert result["analysis"] == report
    assert result["explanation"]["status"] == "validated_catalogue_selection"
    assert len(calls) == 1
    with pytest.raises(ValueError):
        session.handle({"op": "prepare", "payload": {}})


@pytest.mark.parametrize("selection", ['{"packet_sha256":"other"}', "PRIVATE_RAW"])
def test_worker_invalid_selection_retains_numeric_report(evidence_inputs, selection):  # noqa: F811
    report = evidence_inputs[0]
    session = Session(lambda _: report)
    session.handle({"op": "prepare", "payload": {}})
    result = session.handle({"op": "render", "selection": selection, "reason": None})
    assert result["analysis"] == report
    assert result["explanation"]["reason_code"] == "invalid_selection"
    assert "PRIVATE_RAW" not in json.dumps(result)


def test_worker_non_m1_preserves_baseline_and_never_builds_packet():
    report = {"schema_version": "invented-baseline"}
    session = Session(lambda _: report)
    prepared = session.handle({"op": "prepare", "payload": {}})
    assert prepared["packet"] is None
    result = session.handle({"op": "render", "selection": None, "reason": None})
    assert result["analysis"] == report
    assert result["explanation"]["reason_code"] == "m1_prediction_required"


@pytest.mark.parametrize("raw", [b"not-json\n", b"{}\n", b"x" * 262145, b"[]\n"])
def test_worker_stops_on_invalid_message_without_private_echo(raw):
    out = io.BytesIO()
    serve(Session(lambda _: {}), io.BytesIO(raw), out)
    assert out.getvalue() == b'{"worker_error":"worker_failed"}\n'

"""Session evidence is invented; all claims remain bound by the real boundary."""

import copy
import json

import pytest

from scripts.explanation_session_v2 import Session
from scripts.training_comparables import ComparableResult
from tests.native_v2_fixture import fixture_session
from tests.test_explanation_evidence import evidence_inputs  # noqa: F401
from tests.test_m1_service import serving  # noqa: F401


@pytest.fixture
def invented_data(evidence_inputs):  # noqa: F811
    report, shap, references = evidence_inputs
    empty = ComparableResult(
        model_artifact_sha256=report["model_artifact_sha256"],
        cohort_sha256=report["baseline"]["cohort_release_sha256"],
        partition_sha256=report["baseline"]["partition_manifest_sha256"],
        minimum_similarity=0.5,
        references=(),
        reason_code="no_matching_training_reference",
    )
    return {
        "report": report,
        "shap": {cid: row.model_dump(mode="json") for cid, row in shap.items()},
        "comparables": {
            c["creative_id"]: references.get(c["creative_id"], empty).model_dump(mode="json")
            for c in report["candidates"]
        },
    }


def prepare(session):
    checkpoint = session.handle({"op": "analyze", "payload": {"brief": "PRIVATE_SENTINEL"}})[
        "analysis"
    ]
    for op in ("shap", "comparables"):
        session.handle({"op": op})
    return checkpoint, session.handle({"op": "context"})


def test_session_binds_evidence_and_preserves_numeric_snapshot(invented_data):
    session = fixture_session(invented_data)
    report, packet = prepare(session)
    report["candidates"][0]["prediction"]["value"] = 999
    selection = json.dumps(
        {
            "packet_sha256": packet["packet_sha256"],
            "evidence_ids": ["c1_shap_speech_embedding", "c1_reference_1"],
        }
    )
    result = session.handle({"op": "render", "selection": selection, "reason": None})
    assert result["analysis"] == invented_data["report"]
    assert result["explanation"]["status"] == "validated_catalogue_selection"
    assert result["explanation"]["adherence_status"] == "not_evaluated"
    for forbidden in (
        "PRIVATE_SENTINEL",
        "reference_a",
        "youtube.com",
        "text_embedding",
        "source_url",
    ):
        assert forbidden not in json.dumps(result)
    with pytest.raises(ValueError, match="transition"):
        session.handle({"op": "analyze", "payload": {}})


@pytest.mark.parametrize("fault", ["shap", "comparables", "context", "selection"])
def test_evidence_failures_never_change_numbers_or_allow_retries(invented_data, fault):
    data = copy.deepcopy(invented_data)
    session = fixture_session(data)
    if fault == "shap":
        session._explain = lambda *a: (_ for _ in ()).throw(RuntimeError("PRIVATE_ERROR"))
    elif fault == "comparables":
        session._load_index = lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("PRIVATE_ERROR"))
    elif fault == "context":
        next(iter(data["shap"].values()))["model_artifact_sha256"] = "0" * 64
    _, packet = prepare(session)
    result = session.handle(
        {
            "op": "render",
            "selection": "PRIVATE_RAW" if fault == "selection" else None,
            "reason": None if fault == "selection" else "transport_not_configured",
        }
    )
    assert result["analysis"] == invented_data["report"]
    assert result["explanation"]["status"] == "incomplete"
    assert "PRIVATE" not in json.dumps(result)
    if fault != "selection":
        assert packet["packet"] is None


def test_failed_analysis_is_consumed_before_callback():
    calls = []

    def fail(_):
        calls.append(1)
        raise RuntimeError("PRIVATE")

    session = Session(fail)
    with pytest.raises(RuntimeError):
        session.handle({"op": "analyze", "payload": {}})
    with pytest.raises(ValueError):
        session.handle({"op": "analyze", "payload": {}})
    assert calls == [1]

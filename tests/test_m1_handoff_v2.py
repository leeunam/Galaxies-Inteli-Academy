"""Numerical authority is real Python; model/extraction are explicitly invented."""

# ruff: noqa: F811 - pytest injects the imported serving fixture by name

import json

import pytest

from scripts import m1_service
from scripts.creative_analysis import analyze_creatives
from scripts.m1_handoff_v2 import SOURCE_PINS, M1Handoff, analyze_once, verify_sources
from tests.test_m1_service import features, payload, serving  # noqa: F401


@pytest.mark.parametrize("count", [1, 3, 5])
@pytest.mark.parametrize("case", ["ready", "partial", "no_audio", "invalid_prediction"])
def test_full_authority_parity_and_capture(serving, registry, monkeypatch, count, case):
    settings, ids, bundle = serving
    calls = []

    def extract(*args):
        calls.append(args)
        rows = features([float(i % 3 + 1) for i in range(count)])
        if case == "partial":
            rows[-1] = features([1.0], reason="extraction_timeout")[0]
        if case == "no_audio":
            rows = features([1.0] * count, state="no_audio_stream")
        return rows

    if case == "invalid_prediction":
        bundle.predict_views = lambda _: [[0, float("nan"), 1]]
    monkeypatch.setattr(m1_service, "extract_candidates", extract)
    # Capture through the canonical candidate extractor, without touching the
    # module binding used by the original authority in the adapter itself.
    monkeypatch.setattr("scripts.candidate_features.extract_candidates", extract)
    original_globals = m1_service.serve_m1.__globals__.copy()
    request = payload(ids[:count])
    expected = analyze_creatives(request, registry, m1=settings)
    session = M1Handoff(registry, settings)
    actual = session.analyze(request)
    assert actual == expected
    assert len(calls) == 2  # one per independent authority invocation
    assert session.context[2] is bundle
    ready = session.ready_inputs(actual)
    assert len(ready) == sum(c["prediction"]["status"] == "estimated" for c in actual["candidates"])
    assert m1_service.serve_m1.__globals__ == original_globals
    with pytest.raises(ValueError, match="already_consumed"):
        session.analyze(request)
    assert len(calls) == 2


@pytest.mark.parametrize(
    "mutation", ["repeated", "campaign", "sector", "extra", "unknown", "changed", "unsafe"]
)
def test_entry_errors_preserve_original_order_and_never_extract(
    serving, registry, monkeypatch, mutation
):
    settings, ids, _ = serving
    request = payload(ids[:1])
    if mutation == "repeated":
        request["creative_ids"] *= 2
    elif mutation in ("campaign", "sector"):
        request["campaign_id" if mutation == "campaign" else "sector"] = (
            "other" if mutation == "campaign" else "beleza"
        )
    elif mutation == "extra":
        request["view_count"] = 999
    elif mutation == "unknown":
        request["creative_ids"] = ["cr_" + "f" * 32]
    elif mutation == "changed":
        (registry.uploads_root / "demo.mp4").write_bytes(b"changed")
    else:
        state = json.loads(registry.registry_file.read_bytes())
        state["creatives"][ids[0]]["relative_path"] = "../escape.mp4"
        registry.registry_file.write_text(json.dumps(state))
    monkeypatch.setattr(
        "scripts.candidate_features.extract_candidates", lambda *a: pytest.fail("extracted")
    )
    assert M1Handoff(registry, settings).analyze(request) == analyze_creatives(
        request, registry, m1=settings
    )


def test_context_failure_happens_before_extraction_and_consumes(serving, registry, monkeypatch):
    settings, ids, _ = serving

    def fail(_):
        raise ValueError("invented_artifact_failure")

    monkeypatch.setattr(m1_service, "load_model_context", fail)
    monkeypatch.setattr(
        "scripts.candidate_features.extract_candidates", lambda *a: pytest.fail("extracted")
    )
    session = M1Handoff(registry, settings)
    assert session.analyze(payload(ids[:1])) == analyze_creatives(
        payload(ids[:1]), registry, m1=settings
    )
    assert session.consumed and not session._extraction_used


def test_interleaved_sessions_bind_inputs_and_detect_mutation(serving, registry, monkeypatch):
    settings, ids, _ = serving
    values = iter([1.0, 4.0])
    monkeypatch.setattr(
        "scripts.candidate_features.extract_candidates", lambda *a: features([next(values)])
    )
    a, b = M1Handoff(registry, settings), M1Handoff(registry, settings)
    ra, rb = a.analyze(payload(ids[:1])), b.analyze(payload(ids[1:2]))
    assert a.ready_inputs(ra)[0][1].text_embedding[0] == 1
    assert b.ready_inputs(rb)[0][1].text_embedding[0] == 4
    a._records.clear()
    with pytest.raises(ValueError, match="binding_mismatch"):
        a.ready_inputs(ra)
    assert b.ready_inputs(rb)


def test_source_contract_and_non_m1_path(registry, monkeypatch):
    verify_sources()
    monkeypatch.setitem(SOURCE_PINS, "m1_service.py", "0" * 64)
    with pytest.raises(ValueError, match="source_contract_changed"):
        M1Handoff(registry, None)
    assert analyze_once({}, registry)[0] == analyze_creatives({}, registry)


@pytest.mark.parametrize("field", ["q50", "interval", "ranking", "status", "unavailable"])
def test_entire_report_is_bound_to_original_response(serving, registry, monkeypatch, field):
    settings, ids, _ = serving
    rows = (
        features([1.0, 2.0])
        if field != "unavailable"
        else features([1.0, 2.0], reason="extraction_failed")
    )
    monkeypatch.setattr("scripts.candidate_features.extract_candidates", lambda *a: rows)
    session = M1Handoff(registry, settings)
    report = session.analyze(payload(ids[:2]))
    assert len(session.ready_inputs(report)) == (0 if field == "unavailable" else 2)
    changed = json.loads(json.dumps(report))
    if field == "q50":
        changed["candidates"][0]["prediction"]["value"] += 1
    elif field == "interval":
        changed["candidates"][0]["interval"]["upper_views"] += 1
    elif field == "ranking":
        changed["ranking"]["entries"].reverse()
    else:
        changed["candidates"][0]["prediction"]["status"] = (
            "estimated" if field == "unavailable" else "unavailable"
        )
    with pytest.raises(ValueError, match="report_mismatch"):
        session.ready_inputs(changed)

"""Copy and provenance regression on the public invented NIM report, without ML."""

import copy
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.explanation_display import (
    LEGACY_ORIGIN,
    LEGACY_SHAP,
    NUMERIC_ORIGIN,
    SHAP_SCALE,
    TEXT_ORIGIN,
    render_explanation,
)

ROOT = Path(__file__).resolve().parents[1]


def invented_report():
    fixture = json.loads(
        (ROOT / "orchestration/fixtures/nim-graph-three-invented-v1.json").read_bytes()
    )
    selected = {"c1_prediction", "c1_interval", "c1_shap_sector", "c2_prediction"}
    return {
        "analysis": fixture["data"]["report"],
        "explanation": {
            "status": "validated_catalogue_selection",
            "kind": "deterministic_rendering_of_selected_evidence",
            "packet_sha256": fixture["request"]["packet_sha256"],
            "adherence_status": "not_evaluated",
            "claims": [
                c for c in fixture["request"]["packet"]["evidence"] if c["evidence_id"] in selected
            ],
        },
    }


def test_display_corrects_log_scale_and_scope_without_mutating_source():
    report = invented_report()
    before = copy.deepcopy(report)
    assert LEGACY_ORIGIN in report["analysis"]["explanation"]
    assert any(LEGACY_SHAP in c["statement_pt"] for c in report["explanation"]["claims"])
    text = render_explanation(report)
    assert report == before
    assert LEGACY_SHAP not in text and LEGACY_ORIGIN not in text
    assert SHAP_SCALE in text and NUMERIC_ORIGIN in text and TEXT_ORIGIN in text
    assert "seleção parcial" in text and "Aderência ao briefing: não avaliada." in text
    for claim in report["explanation"]["claims"]:
        assert f"[{claim['evidence_id']}] " in text
        assert claim["statement_pt"].replace(LEGACY_SHAP, SHAP_SCALE) in text
    assert "[c3_shap_sector]" not in text  # never fills omitted evidence
    for cid, shap in fixture_shap().items():
        candidate = next(c for c in report["analysis"]["candidates"] if c["creative_id"] == cid)
        total = shap["base_value_log"] + sum(d["contribution_log"] for d in shap["drivers"])
        assert math.isclose(math.expm1(total), candidate["prediction"]["value"], abs_tol=1e-7)


def fixture_shap():
    return json.loads(
        (ROOT / "orchestration/fixtures/nim-graph-three-invented-v1.json").read_bytes()
    )["data"]["shap"]


@pytest.mark.parametrize("provider_verified", [False, True])
def test_origin_copy_never_claims_a_provider_was_or_was_not_called(provider_verified):
    report = invented_report()
    report["orchestration"] = {"real_provider_verified": provider_verified}
    text = render_explanation(report)
    assert TEXT_ORIGIN in text and "não comprova uma chamada externa" in text
    assert "não houve chamada" not in text
    assert report["orchestration"]["real_provider_verified"] is provider_verified


def test_missing_selection_is_not_fabricated():
    report = invented_report()
    report["explanation"] = {
        "status": "incomplete",
        "kind": "deterministic_notice",
        "reason_code": "transport_not_configured",
        "packet_sha256": None,
        "adherence_status": "not_evaluated",
        "claims": [],
    }
    text = render_explanation(report)
    assert "Explicação indisponível: transport_not_configured." in text
    assert "[c1_prediction]" not in text


def test_public_fixture_cli_presents_corrected_text_and_preserves_json(tmp_path):
    report_file = tmp_path / "invented-report.json"
    raw = json.dumps(invented_report()).encode()
    report_file.write_bytes(raw)
    process = subprocess.run(
        [sys.executable, "-B", "-m", "scripts.explanation_display", str(report_file)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert process.returncode == 0 and process.stderr == ""
    assert SHAP_SCALE in process.stdout and TEXT_ORIGIN in process.stdout
    assert report_file.read_bytes() == raw


def test_cli_rejects_invalid_report_without_exposing_input(tmp_path):
    report_file = tmp_path / "invented-invalid.json"
    report_file.write_text('{"analysis": {"brief": "PRIVATE_SENTINEL"}}')
    process = subprocess.run(
        [sys.executable, "-B", "-m", "scripts.explanation_display", str(report_file)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert process.returncode == 1 and process.stdout == ""
    assert "PRIVATE_SENTINEL" not in process.stderr

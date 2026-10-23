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


def test_comparison_includes_omitted_candidates_without_fabricating_selected_claims():
    report = invented_report()
    before = copy.deepcopy(report)
    text = render_explanation(report)
    c1, c2, c3 = [candidate["creative_id"] for candidate in report["analysis"]["candidates"]]
    assert f"{c3}: q50=211.0 views; q10–q90=[61.0, 433.0] views" in text
    assert "cobertura não validada" in text
    assert text.index(f"posição 1: {c2}") < text.index(f"posição 2: {c3}")
    assert text.index(f"posição 2: {c3}") < text.index(f"posição 3: {c1}")
    assert "[c3_prediction]" not in text
    assert "não demonstra superioridade nem retorno de mídia paga" in text
    assert report == before


def test_comparison_preserves_ties_precision_and_source_order():
    report = invented_report()
    entries = report["analysis"]["ranking"]["entries"]
    precise = 283.123456789123
    for entry in entries[:2]:
        entry["rank"] = 1
        entry["value"] = precise
        candidate = next(
            c for c in report["analysis"]["candidates"] if c["creative_id"] == entry["creative_id"]
        )
        candidate["prediction"]["value"] = precise
    before = copy.deepcopy(report)
    text = render_explanation(report)
    first, second = [
        f"posição 1: {entry['creative_id']}; q50={precise} views." for entry in entries[:2]
    ]
    assert text.index(first) < text.index(second)
    assert report == before


@pytest.mark.parametrize("receipt", [False, True])
def test_recorded_graph_and_receipt_equal_plain_report_without_mutation(receipt):
    report = invented_report()
    graph = {"legacy_result": report, "current_provider": {"real_provider_verified": True}}
    wrapped = {"protocol": "entirely_invented_receipt", "result": graph} if receipt else graph
    before = copy.deepcopy(wrapped)
    assert render_explanation(wrapped) == render_explanation(report)
    assert wrapped == before


def test_ambiguous_direct_and_wrapped_reports_are_refused():
    report = invented_report()
    with pytest.raises(ValueError, match="^ambiguous_report_shape$"):
        render_explanation(report | {"result": {"legacy_result": report, "current_provider": {}}})


def test_cli_accepts_recorded_receipt_without_rewriting_it(tmp_path):
    receipt = {
        "protocol": "entirely_invented_receipt",
        "result": {"current_provider": {}, "legacy_result": invented_report()},
    }
    report_file = tmp_path / "invented-receipt.json"
    raw = json.dumps(receipt).encode()
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
    assert process.stdout == render_explanation(invented_report())
    assert report_file.read_bytes() == raw


def test_selected_support_names_missing_fundamentals_without_fabricating_them():
    report = invented_report()
    c1, c2, c3 = [candidate["creative_id"] for candidate in report["analysis"]["candidates"]]
    before = copy.deepcopy(report)
    text = render_explanation(report)
    assert f"{c1}: grupos SHAP exibidos: 1; referências descritivas exibidas: 0." in text
    assert f"{c2}: grupos SHAP exibidos: 0; referências descritivas exibidas: 0." in text
    assert f"{c3}: grupos SHAP exibidos: 0; referências descritivas exibidas: 0." in text
    assert "não demonstra ausência no catálogo nem contribuição SHAP nula" in text
    assert "[c3_shap_sector]" not in text
    assert report == before


def test_selected_support_uses_claim_association_and_distinguishes_reference_notice():
    report = invented_report()
    c1, c2, c3 = [candidate["creative_id"] for candidate in report["analysis"]["candidates"]]
    fixture = json.loads(
        (ROOT / "orchestration/fixtures/nim-graph-three-invented-v1.json").read_bytes()
    )
    reference = next(
        c for c in fixture["request"]["packet"]["evidence"] if c["evidence_id"] == "c2_reference_1"
    )
    report["explanation"]["claims"].extend(
        [
            reference,
            {
                "evidence_id": "c3_references_missing",
                "creative_id": c3,
                "statement_pt": "Sem comparáveis: somente exemplo inventado.",
            },
        ]
    )
    report["analysis"]["candidates"].reverse()
    before = copy.deepcopy(report)
    text = render_explanation(report)
    assert f"{c1}: grupos SHAP exibidos: 1; referências descritivas exibidas: 0." in text
    assert f"{c2}: grupos SHAP exibidos: 0; referências descritivas exibidas: 1." in text
    assert f"{c3}: grupos SHAP exibidos: 0; referências descritivas exibidas: 0." in text
    assert report == before


def test_no_selection_never_infers_that_no_support_exists():
    report = invented_report()
    c1, c2, c3 = [candidate["creative_id"] for candidate in report["analysis"]["candidates"]]
    report["explanation"] = {
        "status": "incomplete",
        "kind": "deterministic_notice",
        "reason_code": "transport_not_configured",
        "packet_sha256": None,
        "adherence_status": "not_evaluated",
        "claims": [],
    }
    text = render_explanation(report)
    assert f"{c1}: grupos SHAP exibidos: 0; referências descritivas exibidas: 0." in text
    assert f"{c2}: grupos SHAP exibidos: 0; referências descritivas exibidas: 0." in text
    assert f"{c3}: grupos SHAP exibidos: 0; referências descritivas exibidas: 0." in text
    assert "não demonstra ausência no catálogo" in text
    assert "Aderência ao briefing: não avaliada." in text


def report_with_packet():
    report = invented_report()
    fixture = json.loads(
        (ROOT / "orchestration/fixtures/nim-graph-three-invented-v1.json").read_bytes()
    )
    report["evidence_packet"] = fixture["request"]["packet"]
    return report


def test_complete_local_catalogue_exposes_existing_support_and_preserves_selection():
    report = report_with_packet()
    before = copy.deepcopy(report)
    normal = render_explanation(report)
    complete = render_explanation(report, show_local_evidence=True)
    assert "[c3_shap_sector]" not in normal
    assert "[c3_shap_sector]" in complete and "[c2_reference_1]" in complete
    assert "Catálogo local completo do relatório" in complete
    assert "A seleção registrada acima permanece preservada." in complete
    for fact in report["evidence_packet"]["evidence"]:
        assert f"[{fact['evidence_id']}] " in complete
        assert fact["statement_pt"].replace(LEGACY_SHAP, SHAP_SCALE) in complete
    assert report == before


@pytest.mark.parametrize("field", ["analysis_sha256", "model_artifact_sha256", "sector"])
def test_local_catalogue_refuses_a_packet_bound_to_another_analysis(field):
    from scripts.channel_partitions import digest

    report = report_with_packet()
    packet = report["evidence_packet"]
    other_sector = "beleza" if report["analysis"]["sector"] == "moda" else "moda"
    packet[field] = other_sector if field == "sector" else "0" * 64
    report["explanation"]["packet_sha256"] = digest(packet)
    with pytest.raises(ValueError, match="local_evidence_packet_mismatch"):
        render_explanation(report, show_local_evidence=True)


def test_local_catalogue_refuses_changed_claims_and_duplicate_or_foreign_evidence():
    from scripts.channel_partitions import digest

    report = report_with_packet()
    report["explanation"]["claims"][0]["statement_pt"] = "Invented unsupported statement."
    with pytest.raises(ValueError, match="local_evidence_packet_mismatch"):
        render_explanation(report, show_local_evidence=True)
    report = report_with_packet()
    packet = report["evidence_packet"]
    packet["evidence"].append(copy.deepcopy(packet["evidence"][0]))
    report["explanation"]["packet_sha256"] = digest(packet)
    with pytest.raises(ValueError, match="local_evidence_packet_mismatch"):
        render_explanation(report, show_local_evidence=True)
    report = report_with_packet()
    packet = report["evidence_packet"]
    packet["evidence"][-1]["creative_id"] = "f" * 64
    report["explanation"]["packet_sha256"] = digest(packet)
    with pytest.raises(ValueError):
        render_explanation(report, show_local_evidence=True)


def test_cli_can_show_existing_local_packet_without_rewriting_receipt(tmp_path):
    receipt = {"result": {"current_provider": {}, "legacy_result": report_with_packet()}}
    path = tmp_path / "invented-complete-receipt.json"
    raw = json.dumps(receipt).encode()
    path.write_bytes(raw)
    process = subprocess.run(
        [
            sys.executable,
            "-B",
            "-m",
            "scripts.explanation_display",
            str(path),
            "--show-local-evidence",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert process.returncode == 0 and process.stderr == ""
    assert "[c3_shap_sector]" in process.stdout
    assert "Aderência ao briefing: não avaliada." in process.stdout
    assert path.read_bytes() == raw

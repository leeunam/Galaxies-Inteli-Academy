"""Proteções dos leitores públicos e da natureza declarada dos exemplos."""

import pytest

from scripts import apresentacao


def test_resultado_identifica_o_modelo_e_os_aliases_dos_criativos():
    data = apresentacao.read_result()
    text = apresentacao.show_result()
    assert data["model"] == "A-M1-catboost-v1"
    assert data["source_document"] == "docs/entrega-20261021.md"
    assert "A-M1-catboost-v1" in text
    assert "um único modelo" in text
    assert "A, B e C são aliases de criativos, não modelos" in text
    assert "B > C > A" in text
    assert "serviço continua em M1/A200" in text
    assert "features cacheadas" in text
    assert "Faixas q10–q90 exploratórias" in text
    assert "cobertura não validada, sem garantia de 80%" in text
    assert "avaliação final pendente" in text
    assert "NIM verificado: não" in text
    assert "incomplete" in text and "30 evidências" in text
    assert "creative_id" not in text and "sha256" not in text


def test_campanha_preserva_previsoes_e_declara_requisitos_nao_verificados():
    data = apresentacao.read_result()
    text = apresentacao.show_campaign()
    assert "conteúdo de beleza para brasileiros" in text
    assert data["source_document"] in text
    assert data["projection_commit"] in text
    assert data["model"] in text
    for item in data["predictions"]:
        assert f"{item['alias']}: {item['estimate_views']:.1f} views" in text
        assert f"{item['interval_views'][0]:.1f}–{item['interval_views'][1]:.1f}" in text
    assert "Ordem preservada: B > C > A" in text
    assert "Aderência do conteúdo ao briefing: não avaliada" in text
    assert "formato vertical: não disponível; requisito não verificado" in text
    assert "duração até 30 segundos: não disponível; requisito não verificado" in text
    assert "fala em português: não disponível; requisito não verificado" in text
    assert "Faixas q10–q90 exploratórias: cobertura não validada, sem garantia de 80%" in text
    assert "não indicam uma seleção final de campanha" in text
    assert "nenhuma chamada NIM foi executada" in text
    assert "nenhuma extração, inferência ou chamada a modelo foi executada" in text
    assert "sha256" not in text and "creative_id" not in text


def test_cli_campanha_nao_executa_percurso_mcp(monkeypatch, capsys):
    import sys

    monkeypatch.setattr(sys, "argv", ["apresentacao", "campanha"])
    monkeypatch.setattr(
        apresentacao,
        "_run_mcp",
        lambda: (_ for _ in ()).throw(AssertionError("MCP não deve ser executado")),
    )
    assert apresentacao.main() == 0
    output = capsys.readouterr().out
    assert "Briefing:" in output
    assert "Aderência do conteúdo ao briefing: não avaliada" in output


def test_metricas_nomeiam_modelos_e_agregacoes():
    data = apresentacao.read_metrics()
    text = apresentacao.show_metrics()
    assert tuple(data["metrics"]) == ("A300", "B-cache300", "C-cache300")
    assert "MAE log por canal" in text
    assert "MAE views micro" in text
    assert "cobertura micro" in text
    assert "A300:" in text and "B-cache300:" in text and "C-cache300:" in text
    assert "1.7761" in text and "1.6584" in text and "1.5444" in text
    assert "B/C completos com VLM seguem pendentes" in text
    assert "serviço continua em M1/A200" in text
    assert "não são avaliação final independente" in text


def test_leitores_nao_importam_midia_ou_mcp(monkeypatch):
    import builtins

    original = builtins.__import__
    forbidden = {
        "av",
        "fastmcp",
        "scripts.demo_creatives",
        "scripts.creative_mcp",
        "scripts.m1_service",
    }

    def guarded(name, *args, **kwargs):
        if name in forbidden:
            raise AssertionError(f"leitor tentou importar {name}")
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    apresentacao.read_result()
    apresentacao.read_metrics()


def test_snapshot_recusa_campo_nao_allowlisted(monkeypatch):
    original = apresentacao._read_snapshot

    def contaminated(name):
        data = original(name)
        data["creative_id"] = "private-id"
        return data

    monkeypatch.setattr(apresentacao, "_read_snapshot", contaminated)
    with pytest.raises(ValueError, match="campos"):
        apresentacao.read_result()


def test_metricas_recusam_cobertura_invalida(monkeypatch):
    original = apresentacao._read_snapshot

    def contaminated(name):
        data = original(name)
        data["metrics"]["A300"]["coverage_micro"] = 1.2
        return data

    monkeypatch.setattr(apresentacao, "_read_snapshot", contaminated)
    with pytest.raises(ValueError, match="item"):
        apresentacao.read_metrics()

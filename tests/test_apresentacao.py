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

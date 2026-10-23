"""Fachada de terminal para demonstração e resultados preservados do iSee."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "data" / "public"


def _read_snapshot(name: str) -> dict:
    # Nomes fechados: este leitor nunca aceita caminhos fornecidos pelo usuário.
    if name not in {"preserved-result-v2.json", "validation-metrics-v2.json"}:
        raise ValueError("snapshot_desconhecido")
    with (PUBLIC / name).open(encoding="utf-8") as stream:
        return json.load(stream)


def _number(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def read_result() -> dict:
    data = _read_snapshot("preserved-result-v2.json")
    expected = {
        "schema_version",
        "data_kind",
        "source_document",
        "projection_commit",
        "projection_date",
        "cached_features",
        "nim_verified",
        "model",
        "sector",
        "predictions",
        "explanation",
    }
    if set(data) != expected:
        raise ValueError("snapshot_resultado_campos")
    if (
        data["schema_version"],
        data["data_kind"],
        data["projection_commit"],
        data["cached_features"],
        data["nim_verified"],
        data["model"],
    ) != (
        "isee-preserved-result-v2",
        "preserved_real_demo",
        "8058cb5",
        True,
        False,
        "A-M1-catboost-v1",
    ):
        raise ValueError("snapshot_resultado_origem")
    if (
        data["sector"] != "beleza"
        or not isinstance(data["predictions"], list)
        or len(data["predictions"]) != 3
    ):
        raise ValueError("snapshot_resultado_formato")
    aliases = []
    for item in data["predictions"]:
        if set(item) != {"alias", "estimate_views", "interval_views"} or item["alias"] not in {
            "A",
            "B",
            "C",
        }:
            raise ValueError("snapshot_resultado_item")
        if (
            not _number(item["estimate_views"])
            or not isinstance(item["interval_views"], list)
            or len(item["interval_views"]) != 2
            or not all(_number(v) for v in item["interval_views"])
        ):
            raise ValueError("snapshot_resultado_numero")
        if item["interval_views"][0] > item["interval_views"][1]:
            raise ValueError("snapshot_resultado_intervalo")
        aliases.append(item["alias"])
    if set(aliases) != {"A", "B", "C"}:
        raise ValueError("snapshot_resultado_aliases")
    explanation = data["explanation"]
    if (
        set(explanation) != {"status", "evidence_count"}
        or explanation["status"] != "incomplete"
        or type(explanation["evidence_count"]) is not int
        or explanation["evidence_count"] < 0
    ):
        raise ValueError("snapshot_explicacao")
    return data


def read_metrics() -> dict:
    data = _read_snapshot("validation-metrics-v2.json")
    if set(data) != {
        "schema_version",
        "data_kind",
        "source_documents",
        "projection_commit",
        "cohort",
        "metrics",
    }:
        raise ValueError("snapshot_metricas_campos")
    if (data["schema_version"], data["data_kind"], data["projection_commit"]) != (
        "isee-validation-metrics-v2",
        "preserved_real_aggregate",
        "8058cb5",
    ):
        raise ValueError("snapshot_metricas_origem")
    expected_models = ("A300", "B-cache300", "C-cache300")
    if (
        data["cohort"] != {"videos": 66, "channels": 37}
        or tuple(data["metrics"]) != expected_models
    ):
        raise ValueError("snapshot_metricas_coorte")
    for row in data["metrics"].values():
        if (
            set(row) != {"mae_log_per_channel", "mae_views_micro", "coverage_micro"}
            or not all(_number(v) for v in row.values())
            or not 0 <= row["coverage_micro"] <= 1
        ):
            raise ValueError("snapshot_metricas_item")
    return data


def show_result() -> str:
    data = read_result()
    values = {item["alias"]: item for item in data["predictions"]}
    ranking = sorted(values, key=lambda alias: values[alias]["estimate_views"], reverse=True)
    lines = [
        "Previsões reais preservadas de um único modelo (features cacheadas; não é execução ao vivo).",
        f"Modelo: {data['model']} | setor: {data['sector']} | projeção: {data['projection_commit']} / {data['projection_date']}",
        "A, B e C são aliases de criativos, não modelos; o serviço continua em M1/A200.",
    ]
    lines.extend(
        f"{alias}: {values[alias]['estimate_views']:.1f} views (faixa {values[alias]['interval_views'][0]:.1f}–{values[alias]['interval_views'][1]:.1f})"
        for alias in ("A", "B", "C")
    )
    lines.append(
        f"Ordem dos criativos: {' > '.join(ranking)} | explicação: {data['explanation']['status']} ({data['explanation']['evidence_count']} evidências)"
    )
    lines.append(
        "Faixas q10–q90 exploratórias: cobertura não validada, sem garantia de 80%; avaliação final pendente."
    )
    lines.append("NIM verificado: não.")
    return "\n".join(lines)


def show_campaign() -> str:
    """Renderiza briefing acadêmico com as previsões públicas já preservadas."""
    data = read_result()
    values = {item["alias"]: item for item in data["predictions"]}
    ranking = sorted(values, key=lambda alias: values[alias]["estimate_views"], reverse=True)
    lines = [
        "Ensaio acadêmico hipotético, não uma campanha genuína: briefing fictício aplicado retrospectivamente à projeção pública minimizada.",
        'Briefing: "Quero divulgar conteúdo de beleza para brasileiros. Compare três opções para um teste de divulgação. Os vídeos devem ser verticais, durar até 30 segundos e ter fala em português."',
        "Renderização local nova de números preservados; nenhuma extração, inferência ou chamada a modelo foi executada.",
        f"Fonte: {data['source_document']} | modelo histórico: {data['model']} | projeção: {data['projection_commit']} / {data['projection_date']}.",
        "A, B e C são aliases dos resultados salvos; não há correspondência com mídia identificada.",
    ]
    lines.extend(
        f"{alias}: {values[alias]['estimate_views']:.1f} views (faixa {values[alias]['interval_views'][0]:.1f}–{values[alias]['interval_views'][1]:.1f})"
        for alias in ("A", "B", "C")
    )
    lines.append(f"Ordem preservada: {' > '.join(ranking)}.")
    lines.extend(
        (
            "Aderência do conteúdo ao briefing: não avaliada.",
            "Evidência de formato vertical: não disponível; requisito não verificado.",
            "Evidência de duração até 30 segundos: não disponível; requisito não verificado.",
            "Evidência de fala em português: não disponível; requisito não verificado.",
            "Estas previsões históricas A200 não indicam uma seleção final de campanha.",
            "NIM verificado: não; nenhuma chamada NIM foi executada neste ensaio.",
        )
    )
    return "\n".join(lines)


def show_metrics() -> str:
    data = read_metrics()
    lines = [
        f"Validação preservada — {data['cohort']['videos']} vídeos / {data['cohort']['channels']} canais.",
        "Modelo | MAE log por canal (menor é melhor) | MAE views micro | cobertura micro",
    ]
    for name, row in data["metrics"].items():
        lines.append(
            f"{name}: {row['mae_log_per_channel']:.4f} | {row['mae_views_micro']:.1f} | {row['coverage_micro']:.1%}"
        )
    lines.append(
        "A300, B-cache300 e C-cache300 usam features cacheadas; B/C completos com VLM seguem pendentes."
    )
    lines.append(
        "O serviço continua em M1/A200; estes agregados de validação não são avaliação final independente."
    )
    return "\n".join(lines)


async def _run_mcp() -> dict:
    # Imports de mídia, MCP e execução ficam fora dos leitores acima.
    from scripts.creative_registry import CreativeRegistry
    from scripts.demo_creatives import demonstrate

    with TemporaryDirectory(prefix="isee-apresentacao-") as folder:
        registry = CreativeRegistry(
            Path(folder) / "uploads", Path(folder) / "private" / "registry.json"
        )
        return await demonstrate(registry, synthetic_baseline=True)


def show_mcp() -> str:
    result = asyncio.run(_run_mcp())
    count = len(result["results"])
    if (
        result["fixture"] != "synthetic"
        or result["learned_prediction_available"] is not False
        or not result["synthetic_baseline_enabled"]
    ):
        raise RuntimeError("A demonstração não corresponde ao percurso sintético esperado.")
    return f"MCP STDIO executado: {count} análises com vídeos e baseline inventados.\nAprendido: não | previsão real: indisponível."


def main() -> int:
    parser = argparse.ArgumentParser(description="Demonstração iSee para terminal")
    parser.add_argument("comando", choices=("mcp", "resultado", "metricas", "campanha"))
    args = parser.parse_args()
    try:
        output = {
            "mcp": show_mcp,
            "resultado": show_result,
            "metricas": show_metrics,
            "campanha": show_campaign,
        }[args.comando]()
    except (OSError, ValueError, KeyError, json.JSONDecodeError, RuntimeError) as exc:
        print(f"Não foi possível apresentar os dados: {exc}")
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

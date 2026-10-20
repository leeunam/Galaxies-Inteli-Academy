# Issue #5 — composição local aditiva por Python e MCP

Unidade de 20/10/2026, anterior à instalação isolada e ao teste NIM recém-aprovados.
`scripts/explanation_composition.py` liga a função numérica existente ao
[catálogo](issue-5-fronteira-explicacao-local.md) e ao
[transporte local](issue-5-transporte-local.md), sem editar as fontes protegidas.
É composição Python comum, identificada como tal; não executa StateGraph/NIM.

## Uso e contrato

```python
from scripts.explanation_composition import analyze_with_explanation

result = await analyze_with_explanation(payload, registry, m1=settings)
assert result["orchestration"]["stategraph_executed"] is False
```

Há uma única chamada a `analyze_creatives`; `analysis` preserva integralmente
o resultado do modo configurado. As opções de operador `synthetic_baseline`,
`observed_baseline_dir` e `m1` mantêm a exclusividade anterior. Erro de entrada,
baseline e ausência completa de previsão M1 não acionam evidências/transporte.
Sem transporte configurado, a explicação M1 fica explicitamente incompleta.
Uma previsão parcial conserva os candidatos indisponíveis e o ranking original.

O operador pode fornecer `evidence_provider(report_copy) -> LocalEvidence`,
com mapas por ID de `M1Evidence` e `ComparableResult` já verificados. Recebe
somente cópia descartável do relatório numérico, sem brief/vetores. O catálogo
confere os vínculos e congela os fatos antes do callback de transporte. Falha
do provider ou evidência incompatível produz aviso com código fixo, nenhuma
afirmação e zero tentativas de transporte, preservando números/faixas/ranking.

Esta unidade **não calcula SHAP nem recupera comparáveis automaticamente**.
O serviço protegido não expõe as features extraídas na resposta; ligar a captura
verificada dessas features ao worker/grafo continua necessário para a integração
nativa sem reextração. Os callbacks são código local confiável do operador,
não uma fronteira para autenticar JSON arbitrário ou executar código do host.
Não há prazo rígido/sandbox do provider síncrono. O transporte preserva seu
próprio prazo cooperativo/reparo, e o cancelamento do chamador propaga.

## Adaptador MCP separado

```bash
rtk proxy .venv/bin/python -m scripts.explanation_mcp --help
rtk proxy .venv/bin/python -m scripts.explanation_mcp --synthetic-baseline
```

O segundo comando inicia servidor stdio e aguarda cliente MCP. Ele preserva
`analyze_creatives` e acrescenta `analyze_creatives_with_explanation`, com o
mesmo payload estrito de 1–5 IDs. Flags `--uploads-root`, `--registry`,
`--observed-baseline-dir` ou o par `--m1-model-dir`/`--m1-cohort-dir` são
configuração local do operador; nenhum callback/provedor/caminho vem do payload.
O CLI não configura NIM nem transporte falso silenciosamente.

`schema_version="creative-explanation-local-v1"` separa `analysis`,
`explanation`, `explanation_transport` e `orchestration`. A explicação só pode
selecionar o catálogo; aderência qualitativa permanece `not_evaluated` e
`real_provider_verified=false`. A saída reduzida não devolve URLs/IDs privados
das referências; a declaração de origem fica no índice local e ainda exige
seu contrato final de apresentação. Não marcar os critérios compostos de #5
como concluídos com essa renderização determinística.

## Verificação e preservação

Os testes usam vídeos gerados, M1/SHAP/referências inventados e transporte falso,
com bloqueio de sockets/DNS. Verificam 1/3/5 candidatos, extração única, modos
baseline, erros, indisponibilidade parcial/total, vínculos inválidos, mutação
da cópia, falhas, cancelamento e paridade numérica/evidências por cliente MCP.
Há testes reais de stdio nos três modos sem M1; os testes M1 do adaptador usam
cliente MCP em memória e serviço simulado. Não são nova demo real ou NIM real.
O tempo do transporte pode variar entre chamadas; paridade compara números,
catálogo e estados, sem prometer igualdade da telemetria de duração.

Passaram **25 testes novos e 109 direcionados em 61,95 s**, com Ruff e
formatação de 129 arquivos e revisão independente. A suíte completa do HEAD
final será executada após as unidades isoladas seguintes; não atribuir os
710 testes anteriores ao HEAD posterior ao ajuste do detector de workers
(que teve 26 direcionados finais).

Antes da unidade foram conferidos 641 hashes protegidos, incluindo as filas
seladas de V9, as oito PNGs, M1 e fontes anteriores. Recibos desta unidade:
`data/private/issue-5-composicao-aditiva-v1/`. Nenhuma aquisição/inferência VLM,
abertura de teste, instalação, alteração de lock/ambiente, credencial, push
ou deploy foi realizada nesta unidade. `README.md` não rastreado permanece
fora da leitura e das alterações. A autorização posterior para LangGraph/NIM
será executada em unidades próprias, com limites e resultados próprios.

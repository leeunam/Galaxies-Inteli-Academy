# Baseline observado pela função e MCP — 18/10/2026

**Os cinco critérios técnicos da #2 foram demonstrados no escopo de baseline do
piloto.** A [curadoria da #1](issue-1-curadoria-final.md) disponibilizou doze
referências observadas de doze canais: sete moda/cinco beleza. Sete estão no treino,
três na validação e duas na partição denominada teste. B0, faixa empírica, empate
e fallback usam apenas o treino congelado. Não há previsão aprendida do conteúdo,
intervalo preditivo calibrado ou avaliação científica concluída.

## Fluxo e estados

O cadastro seguro e o contrato de entrada não mudam: um a cinco IDs distintos,
campanha, setor, objetivo `divulgacao` e brief. Caminhos de artefatos são configuração
local do operador; não são campos aceitos no payload ou ferramentas de cadastro
expostas pelo MCP.

| Configuração do operador | Resposta | Dados numéricos |
| --- | --- | --- |
| Sem opção | `prototype-v1` / `prediction_unavailable` | Indisponíveis |
| `synthetic_baseline=True` | `prototype-synthetic-v1` / `synthetic_baseline_available` | Fixture inventada; sem previsão/ranking individual |
| `observed_baseline_dir=Path(...)` | `prototype-observed-v1` / `observed_baseline_available` | Estatísticas observadas de B0 e faixa setorial; ranking empatado |

Os dois modos com baseline são mutuamente exclusivos. Arquivos presentes no disco
não habilitam o modo observado automaticamente. Bundle ausente, incompleto,
alterado ou incompatível devolve `baseline_artifact_unavailable`, sem expor caminhos,
dados de entrada ou exceções. O padrão continua explicitamente indisponível.

No modo observado:

- `data_kind=observed_pilot`, `scientific_status=pilot_not_evaluated` e
  `real_results_available=true` significam **somente estatísticas de baseline**;
  `results_scope=baseline_statistics_only` delimita isso e
  `learned_prediction_available=false` permanece obrigatório.
- `baseline` identifica B0, suporte de treino (quatro moda/três beleza), versão,
  hashes da coorte/partições/artefato e `new_channel_policy=sector_reference`.
  Canal/ID das referências, contagens individuais e transcrições não são expostos.
- `baseline.sector_range` contém q10/mediana/q90 empíricos do setor, interpolados
  em `log1p` e convertidos por `expm1`; `coverage_status=not_evaluated`.
  Não são limites calibrados para uma nova publicação.
- Cada `candidate.prediction` tem `status=baseline_reference`, valor B0 e
  `content_features_used=false`. Vídeo e brief não mudam esse valor.
  `candidate.interval` fica indisponível por `predictive_interval_not_validated`.
- Um candidato gera análise individual e ranking indisponível. Dois a cinco
  recebem `ranking.status=tied_baseline`: todos têm rank 1 e o mesmo valor,
  preservando a ordem de entrada. Essa ordem não indica superioridade.
- `model_version=B0-train-log1p-v1`, extrator nulo e `extraction_status=not_run`:
  o baseline não requer extrair características dos criativos cadastrados.
  A explicação é determinística e informa o alcance limitado dos resultados.

O alvo observado é a contagem pública acumulada entre 30 e 37 dias das referências,
com datas originais preservadas. Não é reconstrução do dia 30, previsão de vendas
ou garantia de desempenho de mídia paga.

## Congelamento e reprodução dos artefatos

`scripts/observed_baseline.py` publica um bundle privado de layout fixo:

1. `freeze_cohort(records, directory, source_snapshot_sha256=...)` valida os
   registros curados, identidade/URL, evidência, dimensões, idioma atribuído e
   idade na observação. A entrada não aceita views. Exige ao menos três canais
   de cada setor para esta demonstração, sem afirmar suficiência estatística.
   Persiste `cohort.json` e `partitions.json` por canal antes do ajuste.
2. `publish_baseline(directory, training_targets)` aceita **exatamente** os rótulos
   de treino. Confere seu vínculo às identidades/datas/contagens originais por hash
   e grava `train-targets.json` e `baseline.json`. Rótulos extras ou de holdout,
   ausências, contagens alteradas e duplicatas são recusados.
3. `load_observed_baseline(directory)` valida novamente a coorte, a atribuição
   determinística dos canais e os hashes; recompõe o baseline dos rótulos de treino
   para conferir o artefato. Não lê os rótulos de validação/teste.

Não há sobrescrita silenciosa. Uma interrupção pode deixar bundle parcial;
ele não é servível e requer inspeção/nova execução em pasta nova. JSON limitado
a 16 MiB por arquivo, sem pickle ou execução de pesos. Diretório criado com 0700
e arquivos com 0600. A evidência de curadoria é atestada pelo operador e vinculada
por hash; hashes verificam consistência, sem constituir aprovação da plataforma,
assinatura de revisor ou prova de correção semântica.

`scripts/empirical_baseline.py` mantém Bcanal como diagnóstico offline: mediana
do canal somente se existe no treino; canal novo usa B0 do setor, com
`channel_fallback=true`. A tool continua sem receber identificador de canal.
No piloto há uma referência por canal; não há suporte para medir ranking
intra-canal ou estimar generalização com precisão.

## Usar o piloto privado existente

Na raiz do projeto, com dependências instaladas pelo lock:

```bash
rtk proxy uv sync --frozen
rtk proxy uv run --frozen python -m scripts.demo_creatives --observed-baseline-dir data/private/issue-1-curadoria-final-20261018-v3/baseline-bundle
```

A demo gera criativos verticais vazios autorizados localmente, usa o **baseline
observado** do bundle e confere as seis respostas Python/MCP: moda/beleza com
um, dois e cinco candidatos. `fixture=synthetic` descreve os arquivos candidatos;
`reference_data=observed_pilot` identifica a procedência das estatísticas.
Não se afirma análise semântica desses arquivos. Mídia/cadastro da demo são
temporários. Não há acesso à rede ou necessidade de chaves durante a execução.

Para a solicitação de arquivos já cadastrados:

```bash
rtk proxy uv run --frozen python -m scripts.creative_cli analyze --request-file data/private/analysis-request.json --observed-baseline-dir data/private/issue-1-curadoria-final-20261018-v3/baseline-bundle
rtk proxy uv run --frozen python -m scripts.creative_mcp --observed-baseline-dir data/private/issue-1-curadoria-final-20261018-v3/baseline-bundle
```

O segundo comando inicia um servidor à espera do cliente stdio. Use os mesmos
`--uploads-root`/`--registry` do cadastro. Pela função Python:

```python
response = analyze_creatives(
    request,
    registry,
    observed_baseline_dir=Path(
        "data/private/issue-1-curadoria-final-20261018-v3/baseline-bundle"
    ),
)
```

O [roteiro de cadastro](issue-2-execucao.md) fornece os imports e exemplos completos
de solicitação. Esquemas de saída incluem os três modos e erros seguros. Clonar
o repositório não disponibiliza o corpus privado; os testes e as demos padrão e
sintética funcionam sem ele, sem segredos e sem mídia de terceiros.

## Verificação e aceite

A suíte integrada passou em **198 testes**, em 77,93 s. Ruff e formatação dos
43 arquivos Python aprovados; lock verificado offline e dependências instaladas
compatíveis, sem mudanças de versões. Os testes novos cobrem recorte, datas,
congelamento, contagens originais, rejeição de holdout, adulteração, fallback,
empates, erros seguros, privacidade, modo observado explícito e paridade Python/MCP.

A execução com o **bundle real** concluiu seis comparações Python/cliente stdio
iguais, nos dois setores e tamanhos 1/2/5, mais dois fallbacks reais de canal
inédito. O artefato servido corresponde ao congelado. A saída completa permanece
privada; os arquivos temporários da demo foram removidos.

| Critério original da #2 | Evidência |
| --- | --- |
| Ambiente/contrato 1–5 | Lock preservado; validações e modos na suíte integrada |
| Cadastro e erros seguros | Controles de mídia, escape, symlink, alteração e schema preservados |
| Partições/baseline/fallback | Coorte observada congelada; ajuste somente no treino; B0/Bcanal e empates explícitos |
| Python/MCP equivalentes | Cliente stdio real, seis casos observados e regressões dos demais modos |
| Demo completa autorizada | Comandos acima, candidatos gerados e baseline observado privado, seis paridades conferidas |

Isso conclui o percurso estreito de baseline da #2. A #1 permanece aberta por
escala/base para modelos, auditoria adicional e demais critérios compostos,
incluindo explicador NIM; #3–#7 não são concluídas por este resultado.
Permanecem `platform_approval_verified=false`, adesão ao aditivo não enviada,
auditoria humana amostral adicional pendente e ausência de avaliação/calibração.
O manifesto antigo não foi promovido a treino supervisionado. As partições
deste piloto de desenvolvimento não são um teste científico intocado.

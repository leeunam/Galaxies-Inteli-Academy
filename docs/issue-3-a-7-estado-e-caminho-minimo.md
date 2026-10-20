# Issues #3–#7 — evidência disponível e caminho mínimo

Conferência local de 20/10/2026. Este documento separa critérios técnicos
implementados, implementação ainda necessária e decisões de protocolo. Não
fecha issues remotamente nem transforma uma autorização operacional em aceite
científico. A configuração servida continua sendo **M1/A200**; o teste permanece
fechado, com as partições ampliadas **203/66/31** intactas.

## Situação por entrega

| Entrega | Evidência atual | Trabalho/decisão restante |
| --- | --- | --- |
| #3 / A | Os cinco critérios técnicos locais estão conferidos; Python e MCP servem M1/A200, com paridade real anterior para 1/2/5 cadastros do mesmo vídeo. | Aceite/aprendizagem do aluno e encerramento remoto. Essa demo não comprova três criativos distintos ou qualidade/calibração. |
| #4 / B → C | B-cache foi treinado nas 300 com CLIP e medidas de imagem/áudio; A300/A200/B0 têm comparação pareada na validação. V9 ficou selado em 41/64 e não passou à liberação. | B com atributos VLM não foi treinado, e C/LightGBM completo não foi implementado/executado. O recorte original completo requer modalidades aprovadas. |
| #5 / explicação | SHAP q50 nativo, índice somente treino, contratos vinculados, composição Python/MCP aditiva, transporte local, StateGraph/subgrafo e processo isolado têm testes. | Handoff automático de features/SHAP/comparáveis, integração final grafo/MCP, geração/aderência qualitativa e demo com três arquivos distintos. A sondagem NIM única respondeu HTTP 200, mas terminou sem seleção validada; não equivale a explicação livre. |
| #6 / avaliação final | Não há previsão ou métrica nova do teste reservado. | Depende de #4/#5, congelamento da configuração final e autorização específica para abrir o teste. Falta o percurso final de avaliação conjunta; não inventar comando executável que ainda não existe. |
| #7 / reprodução/entrega | Guia local, dependências raiz travadas, contratos públicos e testes locais; isolamento LangGraph tem lock/ambiente próprios. | Ensaio final em ambiente limpo, relatório científico final, demo integrada e explicação pelo aluno. README não rastreado está protegido por instrução e não foi lido/editado. |

As caixas compostas de #4–#7 no [backlog](backlog-proposto.md) continuam abertas.
Não marcar um critério integrado como concluído só porque seus componentes
isolados funcionam. Não há necessidade de Ridge no caminho obrigatório.

## Evidência e arquivos concretos

- #3: [conferência técnica](issue-3-conclusao-tecnica-local.md),
  [serviço e paridade](issue-3-servico-m1.md),
  `scripts/creative_analysis.py`, `scripts/m1_service.py`,
  `scripts/creative_mcp.py`, `scripts/demo_m1.py`.
- #4: [comparação A300/A200](issue-3-expansao-300-resultados.md),
  [B-cache](issue-4-experimento-b-resultados.md),
  [última comparação V9](issue-4-vlm-produto-v9-adendo-limitado-resultados.md),
  `scripts/train_experiment_a.py`, `scripts/train_experiment_b.py` e
  `scripts/train_experiment_b_vlm.py`. A presença deste último não significa
  que tenha sido executado após reprovar o gate perceptivo.
- #5: `scripts/m1_evidence.py`, `scripts/training_comparables.py`,
  `scripts/explanation_evidence.py`, `scripts/explanation_composition.py`,
  `scripts/explanation_mcp.py`, `scripts/explanation_worker.py`,
  `orchestration/galaxies_orchestration/graph.py` e `worker.py`.
  O [grafo isolado](issue-5-stategraph-isolado.md) registra
  `native_feature_handoff=false`; o MCP aditivo não usa esse grafo ainda.
  `nim_probe.py`, `nim_http.py`, `nim_seal.py` e a fixture versionada limitam o
  [teste sintético único](issue-5-nim-sintetico-unico-protocolo.md).
- #6/#7: [proposta técnica](proposta-tecnica.md), [critérios](backlog-proposto.md)
  e [guia do percurso disponível](guia-reproducao-local.md). O guia identifica
  os artefatos privados necessários e os limites da demo anterior.

## Sequência mínima e decisões necessárias

1. **Preservar a parada V9.** Não completar 42–64, repetir chamadas ou descartar
   as oito folhas. A última autorização foi limitada a uma aquisição diagnóstica
   e 28 chamadas; sua fila está selada. Continuar essa investigação exigiria outro
   protocolo específico, não necessário para avançar a preparação local da #5.
2. **Resolver a representação de #4 antes de C.** Uma opção mínima para decisão
   é registrar explicitamente que o comparador multimodal disponível é B-cache,
   excluindo atributos VLM não aprovados, e então escrever/revisar o protocolo
   C-cache com as mesmas linhas/partições e orçamento fixo de ajustes antes de
   treinar. Isso altera o recorte do aceite original; não foi decidido nem
   executado aqui. A outra opção mantém B completo bloqueado pela validação
   perceptiva. Não renomear B-cache como B completo ou C-cache como C completo.
3. **Completar integração local de #5.** Capturar uma única extração verificada
   no percurso aditivo, ligar SHAP e comparáveis ao relatório e validar paridade
   no grafo/MCP, mantendo as fontes e checks congelados de M1. É trabalho técnico
   ainda pendente; a alternativa isolada não exige alterar o lock raiz. Não
   atribuir bloqueio de aprovação a todo código reversível já autorizado.
4. **Medir explicação dentro de autorização específica.** A tentativa NIM atual
   permite apenas fixture inventada e seleção fechada. Ela não autoriza dados
   privados, novas chamadas após consumo, texto livre ou alegações de reasoning
   e aderência. Validar geração/aderência exigirá desenho e orçamento próprios,
   ainda que se usem exemplos sintéticos. Não inferir suporte a português a partir
   de cópia de IDs; o [card oficial](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-nano-omni-30b-a3b-reasoning) declara somente inglês.
5. **Congelar e avaliar #6 somente depois.** Antes da abertura aprovada, definir
   modelos/configurações e métricas: MAE log por vídeo/canal, MAE em views,
   MAPE com exclusões, Spearman/pares onde estimáveis, cobertura/largura e
   contagens por setor/canal. O diagnóstico temporal é retrospectivo. Não usar
   o teste para escolher o recorte nem executar sua avaliação como smoke test.
6. **Preparar entrega #7.** Após as decisões e a avaliação, consolidar relatório
   e ensaio Python/MCP com três criativos diferentes, além dos modos 1/5, em
   ambiente limpo. São necessários arquivos de demonstração autorizados fora do
   holdout; não há licença automática para coletar nova mídia nesta continuidade.
   O README protegido exige orientação explícita antes de ser incorporado à
   edição. Push, publicação, deploy e fechamento remoto não foram autorizados.

Essas decisões são diferentes: alterar representação, enviar novos dados/chamar
NIM novamente, abrir teste e publicar não se autorizam mutuamente. A instalação
LangGraph isolada já foi autorizada e realizada; não é mais um bloqueio.

## Comandos verificáveis, sem treino ou abertura do teste

Na raiz:

```sh
rtk proxy .venv/bin/python -m pytest -q --tb=short --show-capture=no
rtk proxy .venv/bin/ruff check scripts tests orchestration
rtk proxy .venv/bin/ruff format --check scripts tests orchestration
rtk proxy .venv/bin/python -m scripts.creative_cli --help
rtk proxy .venv/bin/python -m scripts.creative_cli schema analysis-input
rtk proxy .venv/bin/python -m scripts.explanation_mcp --help
```

Em `orchestration/`:

```sh
rtk proxy .venv/bin/python -m pytest -q
rtk proxy .venv/bin/python -m galaxies_orchestration.nim_probe
```

O último comando é inerte. Não repetir `--execute-authorized-once` como teste de
reprodução. Os comandos de instalação isolada e execução local do grafo estão
no documento próprio. Os scripts A/B existentes não devem ser executados para
preencher lacunas de documentação, pois fariam novos ajustes.

## Validação desta continuidade

Código do grafo/worker: commit `3ee162e`; adaptador NIM de tentativa única:
`c0ef8ab`. Passaram 39 testes isolados,11 direcionados raiz na segunda unidade,
Ruff/formatação de 143 arquivos e revisão independente. A suíte completa única do
HEAD de código `c0ef8ab` passou em **748 testes/575,14 s**. A tentativa NIM real
respondeu HTTP 200 em 2,9134 s,763 bytes e 91 tokens, mas terminou sem seleção validada.
Causa e estágio são desconhecidos; a ausência de `reason_code` impede atribuir
erro ao provedor ou afirmar rejeição dentro do validador.
Não houve retry/reparo/fallback; a autorização foi consumida. O
[relatório separado](issue-5-nim-sintetico-unico-resultados.md) documenta esses
resultados e 695 pins/ambientes/oito PNGs preservados. O commit posterior acrescenta
replay/testes no projeto isolado e documentação; não muda fontes seladas ou
código raiz. Após o diagnóstico passaram 45 testes isolados e seis CLIs offline;
o resultado de 748 continua sendo o da raiz em `c0ef8ab`. A decisão sobre C
continua pendente.
O registro histórico de 710 testes é anterior à correção final do detector de
processos;26 direcionados foram a verificação final daquele ajuste. Esta
conferência não transforma esse histórico em suíte completa daquele HEAD.

Nenhuma destas etapas abre o teste, promove A300/B-cache, altera M1/A200, libera
VLM ou substitui as oito folhas. A preservação é conferida por hashes, com
recibos privados e sem publicar os dados da coorte.

# Recibo da integração local — 23/10/2026

**Entrega parcial, sem publicação e sem avaliação final do holdout.** Este
recibo registra trabalho executado e revisado; não congela uma configuração
científica final inexistente nem concede autorização para etapas futuras.

## Base e coordenação

Base solicitada: `3586bcab7aa3f7bf165f1ac17ced91bb85358043`. A árvore já
estava em `a9bdc17b3863b191f0967d9ceda51962c23dd38a`, limpa, na branch
`codex/fechamento-20261023-coordenacao`. Não houve restauração da base antiga.
Branches, worktrees, alterações e chats foram conferidos antes da execução.

Chats “1” e “2” identificados pelas responsabilidades e pedidos humanos.
O chat “3” recebeu a coordenação e integração únicas, com passagem explícita
do coordenador anterior. As frentes trabalharam em clones independentes.
O emissor legado produziu somente os recibos exigidos pela v4-r2, ligado ao
GO do controlador atual; sua identidade não foi falsificada. A fila pesada
teve uma única rodada visual ativa, seguida de conferência e liberação.

Os eventos e recibos privados novos estão em
`data/private/fechamento-20261023/coordenacao/unit-p6-preparation-v1/`.
O histórico anterior não foi sobrescrito. `coordenacao/current-status.json`
é o ponteiro de estado atual; os recibos de cada evento são separados.

## Unidades integradas e revisão

| Unidade | Commit de origem → integrado | Revisão / evidência |
| --- | --- | --- |
| Métricas P6 | `14b9129`→`eef7522` | Revisão independente pediu motivo de Spearman nulo, corrigido em `c871249`→`75e8b32`, depois aceito |
| Planejamento temporal | `8fbf198`→`bd099ec` | Revisão independente em leitura, sem bloqueio; não é ajuste/avaliação temporal |
| Matriz e guia | `38dc1dd`→`12e7abe` | Requisitos confrontados com TAPI; links e revisão independente das docs |
| README autorizado | `03ff2ae`→`fefb42c`, complemento `3f901f2` | Conteúdo existente preservado; origem das provas, comandos e limites revistos |
| Preparação visual v4-r2 | `a63dcaf`→`09b5a0a`, `5bf8ef2`→`54e715a` | Operador/helper idênticos aos bytes da revisão independente; 111 testes anteriores válidos e 7 skips reutilizados |
| Resultado visual v4-r2 | `516faa0`→`0789a44` | Terminal, captura/EOF, encadeamento de hashes, processos e scratch conferidos independentemente |
| Rubrica e contratos F2 | `f5cfbb7`→`0e6d0cf`, `f5adb9f`→`7a57b27` | Vínculos de briefing/conteúdo e suficiência, fixtures sem verdade perceptiva presumida |
| Revisão Python/MCP | `b30d1f4`→`eecc535` | Leitura do código e conferência integrada no shell, sem mudar a lógica numérica histórica |
| Revisão real preservada F2 | `c9aa26d`→`d705583` | 37 hashes persistidos, quatro arquivos do handoff e cinco fontes do revisor executado conferidos; sem repetir modelo |
| Preflight dos sete campos | `dc4e426`→`2ecdfc3`, `2c9dcc8`→`3964e80`, `6ae2344`→`c07c754`, `395d8cc`→`88f75f4` | 26 hashes de evidências e três fontes conferidos; revisão independente e correções de leitura limitada, JSON profundo e canais cruzados |

Os recibos e docs de cada unidade registram suas limitações. Mídias, encoders,
bundles, coorte, fontes seladas e locks não foram copiados para os clones de
implementação nem incluídos em commits desta entrega.

## Verificação proporcional no código consolidado

| Conferência | Resultado | Alcance |
| --- | --- | --- |
| P6 métricas, temporal e preflight | 31 testes, 0,19 s | 25 testes novos inventados e seis preflight existentes; sem dados científicos |
| F2 no clone | 48 testes, 7,162 s | Inclui os 28 iniciais; Python/MCP 1/3/5, falhas e timeout, com grafo/números inventados |
| P6 + F2 na principal, execução direta | **79 testes, 7,22 s**, zero falhas/skips | Mesmos 31 + 48; não são 79 cenários adicionais aos testes anteriores |
| P6 + F2 sob lançador supervisionado | 74 aprovados, uma falha de inicialização stdio, 34,12 s | Recibo negativo preservado; não houve timeout do supervisor ou causa isolada |
| Contraste stdio direto | Um teste aprovado, 2,45 s | Mesma fonte/afinidade, sem atribuir causalidade só ao ambiente |
| Novo exemplo Python do README | Passou, 0,149 s; temporários removidos | Vídeo vazio inventado e baseline sintético, sem pesos, rede ou repetição da prova pública selada |
| Preflight do inventário P6 | Código 2, 20 bloqueios esperados | Leitura de declarações apenas, `holdout_access_authorized=false` |
| Preflight original de sete campos, na principal | 46 testes, 0,30 s | Somente metadados inventados, CLI limitada; nunca aprova qualidade, origem, execução ou completude |

As correções receberam Ruff, formatação e diffcheck. Não foi repetida a suíte
completa histórica ou a prova pública selada apenas para aumentar contagens.
O JUnit consolidado é vinculado pelo SHA-256
`9335a73bbd1663cefcb0b50da464a6fc1fff57c6f5ad0d62e01fe26560550ba7`;
os logs, comando e recibos negativos estão no diretório privado da coordenação.

Com o ambiente existente, a seleção consolidada corresponde a:

```sh
rtk proxy env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  taskset -c 0 .venv/bin/python -B -m pytest -q -x --tb=short \
  --show-capture=no -p no:cacheprovider \
  tests/test_final_evaluation_metrics.py tests/test_temporal_diagnostic.py \
  tests/test_final_evaluation_preflight.py tests/test_front2_explanation_review.py \
  tests/test_front2_review_service.py
```

CPU 0 foi a afinidade disponível nesta máquina; em outro host, usar um núcleo
permitido. Executar pelo shell não exige o lançador supervisor que apresentou
falha. O modo supervisionado continua sem aceite operacional; não houve skip,
atraso artificial, mudança de biblioteca ou aumento de prazo para escondê-lo.

## Experimento, artefatos e fronteiras

V4-r2: preflight válido, uma chamada técnica completa, 1.056 tokens e 60,305 s
nativos; positivo conhecido recebeu `unknown`. STOP, 16 casos não executados,
R$0, sem retry/fallback. O terminal e a captura têm identidades documentadas no
[resultado visual](fechamento-frente-1-representacao-v4-resultados.md).
O controlador conferiu o encerramento e liberou o slot; não matou processos
alheios. A rodada é consumida, sem saldo reutilizável.

M1/A200 continua servido. A300 e B/C-cache continuam históricos de validação.
Não há QualityRelease, extração elegível dos 269, B/C completos selecionados,
briefing real validado ou configuração final congelada. Coorte 300 e partições
203/66/31 permanecem preservadas. Nenhum alvo, feature ou previsão dos 31
reservados foi aberto nesta rodada de coordenação.

A preparação P6 oferece aritmética e planejamento do corte, mas os carregadores
científicos restritos, artefatos/aceites finais e autorização específica faltam.
O diagnóstico temporal com ajuste anterior e avaliação posterior não ocorreu.
O [relatório científico](relatorio-cientifico-fechamento-20261023.md) conserva
os resultados históricos e o negativo visual, sem inventar resultados finais.

## Pacote e destino

Versão do projeto: `0.1.0`, como **snapshot parcial local**. Destino preparado:
[leeunam/case-GALAXIES-IA](https://github.com/leeunam/case-GALAXIES-IA), na branch
de coordenação atual. Push, publicação, tag de entrega e encerramento remoto
não foram executados. Consulta GitHub somente leitura confirmou #1/#2 fechadas
e #3–#7 abertas; conclusão técnica não equivale a aceite humano ou administrativo.

O pacote público é preparado por `git archive` do commit local identificado,
com SHA-256 e inventário, fora do Git em `output/`. A conferência exclui mídia,
transcrições, coortes, credenciais, `.env`, pesos, ambientes e links externos
de filesystem. `.env.example` tem valores vazios; o CSV público é somente
cabeçalho de template. Uma busca direcionada de padrões de credenciais não
encontrou ocorrências. Não se trata de uma garantia universal contra todo
tipo de conteúdo sensível; a revisão das mudanças também verifica sua origem.

O Ruff global passou; a formatação global passou em 422 arquivos após ajustar
somente a disposição de uma tupla no teste P6 antigo. Sua árvore sintática
foi comparada antes/depois e permaneceu idêntica; nenhum teste foi alterado
para modificar um resultado. Fontes antigas de serviço, predição, extração e
locks permanecem iguais ao início desta rodada.

Passagem real: obter coortes/caches/bundles/revisões autorizados com suas
identidades, sem substituição da rede ou recálculo de hashes para contornar
incompatibilidade. A instalação pública e os exemplos sintéticos não dependem
desses arquivos. O [README](../README.md), a [matriz](fechamento-requisitos-e-evidencias.md)
e o [guia curto](guia-explicacao-isee.md) são a entrada para reprodução e apresentação.

**Conclusão deste recibo: parcialmente concluído.** Ciência, integração final
da configuração escolhida, avaliação temporal executada, holdout e aceite
humano/administrativo permanecem abertos nos critérios indicados pela matriz.

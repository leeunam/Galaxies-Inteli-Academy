# Issue #5 — integração local nativa v2

Base autorizada: `69a5832ffccbd6830c3b1c39a4c75f2d1f93e307`.
Implementação em clone Git independente `/tmp/galaxies-issue5-native-v2`.
Não altera a árvore principal, fontes anteriores, locks ou ambientes existentes.

## Handoff

`m1_handoff_v2.py` conserva a validação de entrada e liga apenas dois nomes em
uma cópia privada do namespace de `serve_m1`: carregamento e extração. Ambos
delegam no momento original, capturando resultados sem antecipar processamento.
A autoridade original calcula números, estados, intervalos e ranking.
Hashes fixos recusam mudanças das três fontes das quais depende essa ligação.

Cada sessão é consumida antes de operar. Features são congeladas e vinculadas
à ordem dos IDs, registros conferidos, configuração e artefato. Somente uma
previsão efetivamente disponível pode fornecer inputs para evidências.

Os testes de handoff usam modelo e extração inventados, identificados como tal;
não demonstram percepção real, qualidade preditiva ou explicação por provedor.
As etapas e as provas posteriores estão registradas abaixo.

Primeira unidade: 22 testes de handoff passaram em 13,62 s; Ruff e formatação
conferidos. A verificação inicial encontrou 1.270 pins originais iguais e
acrescentou 35 hashes dos recibos finais, em prova privada no clone.

Revisão do supervisor: o handoff também vincula o digest do relatório inteiro
à resposta da autoridade, antes de liberar qualquer input. Passaram 27 testes
em 16,85 s, incluindo q50, faixa, ranking e disponibilidade adulterados.

## Sessão e evidências

`explanation_session_v2.py` aceita exatamente cinco mensagens ordenadas:
`analyze`, `shap`, `comparables`, `context`, `render`. Marca cada etapa como
consumida antes de operar. A análise mantém extração, previsão e ordenação na
mesma chamada da autoridade original; separar artificialmente esses cálculos
exigiria duplicar suas regras ou alterar fontes congeladas.

O percurso integrado exige o SHA de M1/A200 e 124 IDs de treino. Não promove
A300/B-cache nem incorpora os 203 IDs da expansão. O índice original continua
responsável pelos hashes, bloqueio de arquivos mistos/validação/teste, digest
do treino, exclusão de duplicatas, setor, formato técnico e limiar explícito.
O limiar é configuração do operador, sem alegação de calibração.

Somente previsões efetivamente disponíveis recebem SHAP e comparáveis. O
handoff confere o digest do relatório completo, registros, configuração, ordem
e features congeladas antes de liberar inputs. SHAP usa o bundle da previsão,
q50 nativo em `log1p(views)` e os quatro grupos existentes; a fronteira original
reconfere reconstrução, quantil, coorte e partição. Não há causalidade ou
semântica atribuída às dimensões do embedding.

Falhas de evidência devolvem códigos constantes e preservam o checkpoint
numérico. Brief, transcrição, vetores, identidade/URL/datas de referências e
caminhos não atravessam o pacote reduzido. Este contém fatos determinísticos,
inclusive as limitações e motivos de ausência de comparáveis. Um pacote
reduzido ainda pode conter dados privados; não é autorização de envio externo.

## Grafo e processos

O novo StateGraph compilado executa
`extract_predict_and_rank → native_shap → training_comparables → bind_context
→ explain`, com subgrafo compilado `select → validate_and_render`.
Nenhum checkpointer, retry, streaming ou tracing externo é configurado.
O seletor fica ausente por padrão. Callbacks confiáveis locais nos testes são
simulações, não um provedor NIM ou explicação livre.

O serviço Python inicia um supervisor dedicado Linux com `PR_SET_CHILD_SUBREAPER`,
fora do grupo encerrável. Esse supervisor conhece o grupo do grafo antes de
liberar o pedido por stdin. Grafo, worker M1, inspeção e extração permanecem no
grupo conhecido. O launcher aditivo mantém comando, ambiente offline, prazo e
formato do extrator; não utiliza o `killpg(pid)` que pressupunha outra sessão.
No timeout local ele congela o processo antes de enumerar/encerrar descendentes;
se o término for incerto, encerra o grupo para não desempilhar a limpeza interna
com processos ainda vivos. O supervisor externo recolhe os descendentes.

O supervisor conserva em memória o relatório anterior à explicação. Morte do
worker ou falha posterior retorna esse relatório e explicação incompleta.
O cliente acompanha também `returncode`, pois um neto pode manter o pipe aberto
depois da morte do pai. A leitura/escrita do supervisor é limitada e não bloqueante,
com prazo de até 480 s; o worker tem até 420 s totais e o seletor local até 45 s.
Não são SLAs medidos com mídia real.

Cancelamento pede limpeza ao supervisor e protege essa espera do escopo de
cancelamento AnyIO usado pelo MCP. O supervisor encerra o grupo, recolhe seus
filhos e só então remove o scratch que possui, mesmo que o cliente tenha sido
cancelado. Não se procura uma árvore de filhos depois de perder seu pai.
Processos externos de controle permanecem intactos nos testes.

Morte forçada do próprio supervisor ou queda da máquina pode deixar grupo e
scratch: não há promessa de exclusão instantânea nesses casos. Antes de liberar
o pedido, o supervisor publica `process-lease.json` privado, atômico e com fsync:
boot ID, PGID, PID/start ticks do supervisor e do líder. Sem confirmação de
recolhimento, o serviço conserva esse diretório para recuperação. O operador
deve verificar que a execução terminou, comparar boot/PID/start ticks e grupo,
encerrar somente o grupo identificado, conferir término dos membros e então
remover seu scratch. Divergência ou PID reutilizado exige investigação; nunca
limpar outros jobs ou diretórios por um padrão amplo. O teste de SIGKILL do
supervisor registra a recuperação manual separadamente, sem apresentá-la como
limpeza automática. Não existe retomada/reextração automática dessa sessão.

## Python, MCP e reprodução

`explanation_graph_service_v2.analyze_via_graph(payload, settings)` é o mesmo
caso de uso chamado pela ferramenta MCP `analyze_creatives_with_explanation`.
O servidor aditivo conserva a ferramenta numérica anterior. O payload continua
restrito a campanha, IDs, setor, objetivo e brief. Executáveis, diretórios,
módulo worker e callbacks são configuração de operador, não campos da tool.

O código resolve seu próprio diretório a partir dos módulos do checkout. Os
executáveis raiz e LangGraph são opções distintas; não exige `.venv` no clone,
não redireciona `ROOT` para a árvore ativa e não altera os dois ambientes.
Os filhos recebem ambiente mínimo, offline, sem credenciais/proxies/tracing.
O processo do host MCP pode ter suas próprias políticas de dados: stdio não
constitui autorização de compartilhar dados confidenciais com outro host.

Exemplo de reprodução no clone, com os executáveis já existentes em leitura:

```sh
rtk proxy env PYTHONDONTWRITEBYTECODE=1 GALAXIES_GRAPH_PYTHON=/home/inteli/Documents/projetos/Galaxies-Inteli-Academy/orchestration/.venv/bin/python /home/inteli/Documents/projetos/Galaxies-Inteli-Academy/.venv/bin/python -B -m pytest -q --tb=short --show-capture=no -p no:cacheprovider tests/test_m1_handoff_v2.py tests/test_explanation_session_v2.py tests/test_explanation_worker_v2.py tests/test_explanation_graph_service_v2.py tests/test_explanation_graph_mcp_v2.py
```

No diretório `orchestration` do clone:

```sh
rtk proxy env PYTHONDONTWRITEBYTECODE=1 GALAXIES_ROOT_PYTHON=/home/inteli/Documents/projetos/Galaxies-Inteli-Academy/.venv/bin/python /home/inteli/Documents/projetos/Galaxies-Inteli-Academy/orchestration/.venv/bin/python -B -m pytest -q --tb=short --show-capture=no -p no:cacheprovider tests/test_integrated_graph_v2.py
```

Para servidor real, partindo da raiz do checkout:

```sh
rtk proxy env PYTHONDONTWRITEBYTECODE=1 /home/inteli/Documents/projetos/Galaxies-Inteli-Academy/.venv/bin/python -B -m scripts.explanation_graph_mcp_v2 --graph-python /home/inteli/Documents/projetos/Galaxies-Inteli-Academy/orchestration/.venv/bin/python
```

Sem configuração M1, a análise permanece indisponível. Para habilitar M1,
fornecer `--m1-model-dir`, `--m1-cohort-dir`, `--evidence-root` e
`--minimum-similarity`, além do cadastro/uploads autorizado. `--request-file`
executa o mesmo serviço uma vez como Python/CLI, em vez de iniciar MCP.
Não executar `sync`, instalar pesos ou copiar caches em massa para reproduzir
os testes públicos. A extração real requer as revisões autorizadas dos pesos
nos caminhos que o extrator congelado espera no checkout; a ausência retorna
`model_weights_unavailable`, sem download ou fallback.

## Provas e limites

Os testes públicos usam evidências e extratores inventados e subprocessos leves.
As fixtures são identificadas em módulos de teste e no relatório público
inventado, com `offline_invented_fixture_not_real_m1`. O servidor de produção
nunca seleciona essas fixtures por padrão. Casos cobrem 1/3/5, seleção válida e
inválida, números preservados, sessões intercaladas, adulteração, morte abrupta,
timeout, cancelamento via MCP stdio real e isolamento de processo externo.

A conferência nativa autorizada usa `tests.native_v2_verify` e três arquivos
vazios gerados localmente: suas features são inteiramente inventadas pelo
worker de teste. Modelo M1/A200, SHAP q50 e índice dos 124 são reais e passam
pelos helpers e guardas originais. Ela verificou igualdade integral entre
Python e MCP stdio via StateGraph, doze fatos SHAP agrupados e comparáveis,
sem treinar ou abrir evidência/rótulo do holdout. O launcher padrão também
percorreu o extrator original e confirmou ausência de pesos no clone, com
indisponibilidade explícita. Isso não demonstra extração perceptiva real,
qualidade dos comparáveis ou generalização.

Na conferência final, as três consultas não encontraram referências com cosseno
≥ 0,5: três motivos de ausência e zero matches. Isso verifica a busca e a
abstenção, não a qualidade de referências selecionadas ou calibração do limiar.

O teste de ausência de pesos exige a opção explícita
`--verify-missing-extractor-weights`. Ela é própria deste clone sem encoders,
não deve ser repetida cegamente na árvore principal. Depois da integração,
o ensaio do extrator real com mídia gerada e pesos já locais é uma prova
separada, a agendar pelo integrador, sem downloads e identificada como sintética.

Recibos privados ficam no clone em `data/private/issue-5-native-v2/`. Nenhum
artefato privado é versionado ou enviado a API. A implementação não chama NIM,
reutiliza ledger, cria dispatcher remoto ou altera seleções/validadores selados.
`real_provider_verified=false`, `adherence_status=not_evaluated` e ausência de
seletor são resultados esperados. Seleção de catálogo não prova geração em
português, reasoning ou aderência.

A demo com três mídias reais distintas autorizadas, explicação real validada,
qualidade científica e aceite humano continuam pendentes. A #5 não é dada
como concluída. VLM, B/C, teste reservado e publicação permanecem fora desta
unidade. Transferir commits à árvore principal é fase posterior do integrador
único, após liberação e conferência do supervisor.

## Resultado das verificações desta unidade

- Rodada direcionada ampla: **131 testes em 84,50 s**, incluindo regressão dos
  componentes anteriores. Após os últimos ajustes de binding e cancelamento
  durante spawn: **46 testes em 50,81 s**, cobrindo todos os arquivos alterados
  nesses ajustes. São rodadas separadas, não uma suíte completa do projeto.
- Projeto isolado: **20 testes em 11,47 s**, incluindo 13 novos e sete do grafo
  anterior, sem modificar seu ambiente ou lock.
- Ruff e formatação de **214 arquivos** conferidos; fontes anteriores intactas.
- Python/MCP stdio: paridade com fixtures inventadas em 1/3/5 e cancelamento real;
  conferência adicional com M1/A200 nativo e três consultas de features inventadas.

Uma primeira rodada foi interrompida deliberadamente ao identificar espera de
EOF herdado pelo neto (um teste havia passado); não é contada como suíte passada.
Outra rodada encontrou falha do schema MCP e, depois, retenção de um diretório
vazio sob cancelamento AnyIO. As correções e rodadas posteriores são as provas
de sucesso acima. A recuperação explícita desse resíduo inicial conferiu todos
os PIDs ausentes e diretório vazio antes de removê-lo; recibo privado
`early-test-recovery.json`. O teste posterior de morte do próprio supervisor
tem seu `manual-recovery.json` separado e preserva a necessidade de recuperação.

Conferência final de integridade: **1.270 pins originais e 35 provas finais da
v15 iguais**, sem diferença. Plano, checkpoint, comparação e relatório v15
também conferidos contra as âncoras das provas preservadas. Os 40 arquivos da
fila v15 receberam inventário final; esse inventário não é apresentado como
baseline inicial de 40 arquivos. M1, comparadores, partições, locks, fontes,
pesos protegidos, oito PNGs e filas anteriores permanecem sob esses pins.
Zero workers próprios ativos e zero diretórios de execução pendentes.
A árvore principal segue em `69a5832`, somente com README não rastreado intacto.
Os resultados e JUnit ficam em `integrity-final.json`, `directed-final.xml`,
`last-review.xml`, `isolated-final.xml` e `native-probe-final/`, todos privados
e ignorados pelo Git no clone.

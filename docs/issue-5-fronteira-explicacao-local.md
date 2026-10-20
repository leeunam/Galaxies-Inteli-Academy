# Issue #5 — fronteira local de evidências e decisão sobre StateGraph

Conferência de 20/10/2026. Extensão do desenho aprovado na
[proposta técnica](proposta-tecnica.md), sem mudar serviço/MCP ou M1.
`scripts/explanation_evidence.py` prepara a junção dos componentes de
[SHAP](issue-5-shap-m1.md) e [comparáveis](issue-5-comparaveis-treino.md).

## Implementado e verificado localmente

`build_explanation_context(report, shap=..., comparables=...)` recebe somente
resultados locais confiáveis, produzidos pelos componentes verificados. Valida
IDs, modo individual/comparativo, disponibilidade, faixa ordenada e ranking
numérico com empate estável. SHAP precisa identificar o mesmo M1 e reconstruir
o q50 servido em `log1p(views)`; referências precisam coincidir com modelo,
coorte, partição, setor, limiar e ordenação. O índice de treino continua sendo
responsável pela proveniência e exclusão de cópias. Esse contrato não transforma
JSON fornecido por um usuário em evidência autenticada.

O contexto congela uma cópia JSON do relatório e um pacote imutável com fatos
em português e IDs de evidência. Brief, transcrição, vetores, IDs/URLs/datas das
referências privadas e caminhos locais não entram no pacote reduzido. O SHA do
pacote vincula a seleção às evidências e ao relatório. Reduzir dados não autoriza
envio externo: IDs opacos, previsões e contribuições também podem ser privados.

`validate_selection(context, raw)` aceita somente o SHA e uma lista limitada de
IDs existentes, sem duplicatas ou campos extras. Recusa JSON com chaves repetidas,
resposta acima de 16 KiB, texto livre, novos números/ranking e referência a outro
pacote. A renderização é determinística, com limites obrigatórios e previsão de
cada candidato; o relatório original é devolvido em campo separado, sem alterações.

Isso é um **catálogo fechado preparatório**, não explicação livre ou reasoning
demonstrado. Aderência qualitativa fica `not_evaluated`. Neste checkpoint não havia transporte,
timeout operacional, reparo, chamada NIM, grafo/subgrafo executado ou integração
ao endpoint. Esses componentes continuam pendentes. Os testes são locais com
dados públicos sintéticos e o serviço numérico simulado explicitamente.

A unidade posterior de [transporte injetável local](issue-5-transporte-local.md)
acrescenta callback falso, prazo cooperativo e reparo limitado; NIM, grafo e
integração ao endpoint continuam pendentes.

Passaram **22 testes novos e 65 direcionados** (incluindo SHAP, comparáveis e
serviço M1), em 24,72 s. Ruff e formatação dos 114 arquivos passaram. A revisão
independente somente leitura aprovou após corrigir os estados de falha/extração.
Os 138 arquivos protegidos e todas as versões instaladas continuaram idênticos;
recibos privados em `data/private/issue-5-integracao-local-v1/`. Não foi executada
uma nova suíte completa nesta unidade; a anterior passou em 624 testes.

## Por que não instalar LangGraph no ambiente M1

`experiment_a_artifact.load_bundle` confere o SHA de `uv.lock`, versões exatas
CatBoost/NumPy e quatro fontes: `experiment_a_data.py`,
`experiment_a_metrics.py`, `experiment_a_artifact.py`, `train_experiment_a.py`.
`experiment_a_data.check_extractor_runtime` confere os arquivos/pacotes de
`extractor-config.json`. O mesmo lock também protege os artefatos B-cache/B-VLM.
Não remover, relaxar ou atualizar esses checks para acomodar a orquestração.

Estado observado: Python 3.11.13, CatBoost 1.2.10, NumPy 2.4.6, Pydantic 2.14.1,
FastMCP 4.1.0. LangGraph não está instalado; o SHA do lock raiz é
`7dea78899c753f7c053cc1178c9c092f7313da7b65012b0138042446c2a161f2`.

**Opção concreta para aprovação específica, não executada:** projeto de
orquestração independente em `orchestration/pyproject.toml`,
`orchestration/uv.lock` e ambiente ignorado próprio `orchestration/.venv/`.
Candidato pinado `langgraph==1.2.16`, Python `>=3.11,<3.12`; a
[release oficial](https://pypi.org/project/langgraph/1.2.16/) declara a dependência,
mas a resolução transitiva e compatibilidade ainda precisam ser verificadas.
Um processo separado chamaria o worker M1 existente pelo Python/stdio já
verificado e receberia somente contratos JSON. Modelo, ambiente e lock raiz
permaneceriam iguais. Novos testes cobririam paridade, timeout/encerramento,
falhas e limites do worker antes de qualquer demonstração com dados reais.

Não criar um workspace uv: membros
[compartilham o lock e o ambiente por padrão](https://docs.astral.sh/uv/concepts/projects/workspaces/).
A opção requer aprovação para baixar/instalar novas dependências, fixar todas
as versões no lock separado e adicionar os arquivos de processo/grafo/testes.
Não foi criado ambiente, resolvido lock, instalado pacote ou executado
`StateGraph`. O [grafo documentado](https://docs.langchain.com/oss/python/langgraph/graph-api)
continua sendo requisito, sem substituir sua execução por fluxo manual ou mocks.

## NIM e critérios restantes

Os probes antigos autorizaram tentativas sintéticas limitadas e passaram somente
no contrato restrito de cópia; os limites consumidos não são uma cota nova. A
configuração/chave existente não autoriza novas chamadas, custo ou dados privados.
Não houve acesso a credenciais nem tráfego NIM nesta unidade. Um futuro teste
precisa de conteúdo, número de chamadas, tempo/tokens e custo autorizados antes
do transporte real; falhas não trocam de provedor/modelo. A validação de texto
livre e aderência exigirá evidência própria, sem usar apenas IDs como prova de
verdade factual.

P3 tem implementação técnica local, com aceite/aprendizagem e fechamento remoto
pendentes. P4 mantém a execução antiga selada; a recuperação recém-autorizada
será uma etapa separada com adendo prévio. P5 não está concluída por este
catálogo. P6/teste reservado não foi aberto; P7 tem guia local, sem demo integrada
final nem relatório científico final. Nenhuma issue foi fechada/publicada.

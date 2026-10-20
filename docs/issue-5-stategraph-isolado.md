# Issue #5 — StateGraph em ambiente independente

Implementação de 20/10/2026, seguindo a aprovação específica de 13:06 UTC e o
[desenho de isolamento](issue-5-fronteira-explicacao-local.md). O projeto
`orchestration/` tem `pyproject.toml`, `uv.lock` e `.venv` próprios, sem workspace
uv. LangGraph está fixado em **1.2.16**; todas as fontes do lock são PyPI oficial.
Não houve mudança do projeto, lock, versões instaladas ou artefatos M1 da raiz.

## Fluxo implementado

O [StateGraph real](https://docs.langchain.com/oss/python/langgraph/graph-api)
compilado executa `analyze_once → explain`, sendo `explain` outro
[grafo compilado](https://docs.langchain.com/oss/python/langgraph/use-subgraphs)
com `select → validate_and_render`. Os testes verificam `CompiledStateGraph`,
descobrem o subgrafo e executam `ainvoke`; não substituem LangGraph por mock.

O processo filho usa o Python da `.venv` raiz e `scripts.explanation_worker`.
O worker aceita no máximo duas mensagens JSON: prepara a análise pelo mesmo
`analyze_creatives` existente, mantém relatório/contexto em memória e valida a
seleção no mesmo processo. A seleção nunca fornece texto ou números novos.
IDs, hash do pacote, limites e renderização continuam sob o contrato local.
Baseline, erro e M1 indisponível preservam a análise e não geram pacote M1.
Não há protocolo para treinar, reabrir filas ou acessar evidências do holdout.

A configuração de modelo, coorte e uploads é argumento do operador no processo,
não campo de requisição. O canal tem limite de 256 KiB por linha e prazo total
de 480 s para o worker; falha/cancelamento mata o grupo de processos e aguarda
seu término. stderr não é devolvido ao cliente. O filho recebe uma lista curta
de variáveis, sem credenciais, proxy, PYTHONPATH ou configuração de tracing.

O grafo desativa tracing herdado antes de importar LangGraph; não configura
checkpointer, streaming, callbacks externos ou política de retries. Seu estado
interno pode conter informação privada: o schema de saída não é mecanismo de
sigilo para alguém que modifique o código e ative streaming ou tracing. O seletor
é callback confiável local; o CLI entregue **não configura provedor**. Prazo de
45 s do callback é cooperativo; o teste NIM separado terá também processo com
prazo de parede e conteúdo sintético fixo, sem autorizar uso de dados privados.

## Reprodução local

Na raiz, os comandos usados para resolver e instalar foram, em sequência:

```sh
cd orchestration
rtk proxy env -u UV_INDEX -u UV_EXTRA_INDEX_URL -u UV_INDEX_URL -u UV_FIND_LINKS -u UV_PROJECT_ENVIRONMENT -u VIRTUAL_ENV uv lock --no-config --default-index https://pypi.org/simple --cache-dir ../data/cache/uv-orchestration --python ../.venv/bin/python --no-python-downloads --no-build --keyring-provider disabled
rtk proxy env -u UV_INDEX -u UV_EXTRA_INDEX_URL -u UV_INDEX_URL -u UV_FIND_LINKS -u UV_PROJECT_ENVIRONMENT -u VIRTUAL_ENV uv sync --frozen --no-config --default-index https://pypi.org/simple --cache-dir ../data/cache/uv-orchestration --python ../.venv/bin/python --no-python-downloads --no-build --keyring-provider disabled
rtk proxy .venv/bin/python -m pytest -q
```

Foram resolvidos 44 registros no lock e instalados 42 pacotes. A reprodução
posterior deve usar **sync frozen**, sem repetir `lock`. O Python permanece
3.11.13. A instalação fica em `orchestration/.venv`, ignorada pelo Git.

Para executar localmente, partindo de `orchestration/`:

```sh
rtk proxy .venv/bin/python -m galaxies_orchestration < /caminho/privado/payload.json
```

O padrão mantém o analisador sem modelo. Para o M1 original, o operador pode
acrescentar `--worker-arguments --m1-model-dir /caminho/absoluto/modelo
--m1-cohort-dir /caminho/absoluto/coorte`, além de uploads/registry se necessário.
O CLI lê apenas um objeto JSON e retorna análise com explicação indisponível
por ausência de transporte. Ele não faz chamada NIM nem busca mídia.

## Evidência e limites

Passaram **10 testes no ambiente isolado** e **33 direcionados na raiz (8 novos)**. Há
teste real de stdio entre os dois ambientes, limpeza por timeout, remoção de
credenciais herdadas, execução/cancelamento do subgrafo e preservação da análise
M1 sintética dentro do worker. Isso não é nova demonstração com vídeos/pesos
reais nem teste de diversidade. Não houve mídia, VLM ou chamada NIM nesta unidade.

O novo worker ainda não captura features, calcula SHAP ou busca comparáveis
automaticamente; `native_feature_handoff=false` registra essa lacuna. Os
[componentes anteriores](issue-5-composicao-aditiva.md) seguem disponíveis.
A seleção fechada não comprova geração em português, aderência qualitativa ou
explicação livre. O MCP aditivo anterior continua separado deste CLI de grafo;
não há afirmação de integração StateGraph/MCP final. A issue #5 segue incompleta.

Recibos privados: `data/private/issue-5-stategraph-isolado-v1/`. As **648
proteções**, oito PNGs, filas seladas, M1/A200, partições e teste reservado são
conferidos antes/depois. O README não rastreado não foi lido nem modificado.

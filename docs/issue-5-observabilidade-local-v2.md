# Issue #5 — observabilidade local v2, sem chamada externa

Unidade de 20/10/2026, aditiva ao [diagnóstico offline](issue-5-nim-diagnostico-offline.md).
A [tentativa real anterior](issue-5-nim-sintetico-unico-resultados.md) continua
consumida, com causa e estágio desconhecidos. **Zero chamadas novas**, sem retry,
reparo, fallback, nova autorização, nonce ou reserva real. Fontes, fixture,
plano, selo e recibos anteriores permanecem iguais.

## Contrato implementado

`orchestration/galaxies_orchestration/observation_v2.py` compila grafo e subgrafo
locais, com processo raiz real por stdio. O novo
`scripts/explanation_observer_v2.py` delega preparação, validação e renderização
à sessão sintética selada. Somente depois acrescenta o diagnóstico de
`scripts/selection_observation_v2.py`. O classificador não concede aceitação,
não altera números ou ranking e não relaxa o validador.

Os recibos distinguem transporte, UTF-8, JSON, schema, referências e
renderização. Os códigos são constantes locais: por exemplo `invalid_unicode`,
`json_duplicate_key`, `schema_extra_field`, `packet_hash_mismatch` e
`unknown_evidence_id`. A ordem indica a primeira verificação diagnóstica que
falhou. Não reconstrói uma causa visual, semântica ou remota. Se a classificação
divergir do resultado selado, registra `sealed_result_unclassified` e suprime
a projeção; uma exceção sem localização segura conserva
`sealed_authority_failed`.

O caso de JSON profundamente aninhado primeiro reproduziu a falha do teste:
o caminho selado lança `RecursionError` antes de retornar resultado. A correção
aditiva identifica `json_depth_limit`, com
`authority_status=failed_before_result`, sem inventar análise, explicação ou
rejeição normal. O validador selado permanece inalterado. Os testes preservam
também sua aceitação/rejeição e a igualdade dos relatórios e rankings.

## Retenção e proteção da saída

Não há persistência de corpo bruto nem hash do conteúdo arbitrário:
`raw_response_sha256` e `raw_wire_sha256` ficam nulos. Não se copiam cabeçalhos,
exceções, mensagens, localizações, contexto ou inputs dos erros Pydantic.
Mesmo o nome de um campo extra pode conter um segredo; só o tipo estático do
erro contribui para o código.

A única captura de resposta é uma projeção canônica de `packet_sha256` e
`evidence_ids` já reconhecidos no catálogo da **fixture pública fixa e
inteiramente inventada**. Exige conferir os bytes dessa fixture pelo SHA
`0fb7b9797cd41f53c3f127b0d2f6f934d0696aa3ba288852f5cff616455cf438`
e a identidade do pacote. `retained_projection_sha256` identifica apenas essa
projeção. Um ID conhecido repetido pode ser retido, mas continua rejeitado.
Contextos não públicos e respostas que não permitem essa projeção são suprimidos.

Esse mecanismo evita depender de um redator universal de segredos. Não conserva
whitespace, prefixos, campos descartados nem o envelope original. Portanto,
reduz a capacidade de reconstrução posterior; o recibo não deve ser apresentado
como captura integral ou prova da resposta histórica do provedor.

## Consumo exclusivamente simulado

Cada execução exige uma pasta nova. Antes do callback falso grava, de forma
exclusiva e durável, `local-consumption.json`, explicitamente marcado
`offline_simulation_only` e `simulated_consumed`. Pasta existente ou incerta não
pode ser reutilizada; o ledger real e seus descendentes são recusados antes do
callback. `real_requests=0`, `real_authorization_created=false` e
`retry_allowed=false`. Cancelamento mantém o consumo local e seu recibo.

Os vínculos registram o commit-base
`883578d4334d7c0175210144dd3c4ef55146f258`, o SHA do plano pai selado, o SHA
da fixture e os hashes das seis fontes novas. Os tetos são 2.048 tokens,
45 segundos, 16 KiB e uma tentativa **simulada**. O callback é código local
confiável, com prazo cooperativo; isso não demonstra isolamento ou deadline de
um cliente remoto. O processo raiz herda o encerramento/recolhimento limitado
do worker existente. Conteúdo bruto não entra nos canais do StateGraph.

## Ponte concreta e integração remota ainda ausente

`scripts/nim_response_observer_v2.observe_response(response, render)` recebe
um objeto de resposta **já aberto**, lê no máximo 16.385 bytes para detectar
excesso, confere envelope/UTF-8/JSON e chama a renderização selada no mesmo
processo raiz. Só resultado e observação seguros atravessam stdout. A função
não abre conexão, busca chave ou cria autorização.

O opcode local `observe_http_fixture` testa essa ponte com uma resposta
inventada dentro do processo raiz, inclusive cabeçalhos extras, exceções de
leitura e conteúdo adversarial. Não é uma conexão NIM nem prova de prontidão
remota. Não foi acrescentada flag de execução remota.

Para uma futura tentativa real faltam um dispatcher pai versionado e um
entrypoint HTTP limitado no processo raiz, por exemplo futuros
`nim_probe_v3.py` e `nim_observed_http_worker_v3.py` — **não criados** nesta
unidade. Eles precisariam ligar abertura HTTP, credencial apenas no cabeçalho,
deadline externo e a ponte antes de qualquer stdout; exigir novo plano,
orçamento, nonce e autorização explícita. Não reutilizar o ledger consumido,
o despacho antigo ou sua saída bruta. Testes falsos não verificam rede,
credencial, cobrança ou comportamento do provedor.

## Verificação e reprodução

Passaram **56 testes direcionados na raiz em 19,08 s**, incluindo 23 novos, e
**81 testes da suíte isolada em 22,09 s**, incluindo 36 novos. Exercitam paridade
com a autoridade selada, números/ranking, JSON inválido/repetido/profundo,
schema, hashes/IDs, Unicode, consumo, cancelamento e tentativas de inserir
segredos inventados no corpo, nome de campo, digest, cabeçalho e exceção.
Os testes conferem bytes no disco, stdout e stderr, inclusive subprocessos reais.
Ruff e formatação passaram nos 153 arquivos Python; revisão independente
conferiu código e limites. A suíte completa raiz de **748 testes/575,14 s**
é evidência histórica do código `c0ef8ab`, não foi reexecutada nem atribuída
às fontes novas.

Cinco CLIs offline independentes concluíram:

| Caso inventado | Fase / código | Autoridade |
| --- | --- | --- |
| Seleção válida | `rendering / accepted` | aceita |
| Campo extra com segredo | `schema / schema_extra_field` | rejeita |
| JSON profundo | `json / json_depth_limit` | falhou antes de retornar |
| Envelope com cabeçalho extra | `rendering / accepted` | aceita conteúdo válido; cabeçalho suprimido |
| Envelope com conteúdo profundo | `json / json_depth_limit` | falhou antes de retornar |

Na raiz, executar os quatro arquivos de teste direcionados:

```sh
rtk proxy .venv/bin/python -m pytest -q tests/test_selection_observation_v2.py tests/test_explanation_evidence.py tests/test_explanation_worker.py tests/test_explanation_synthetic_worker.py
```

Em `orchestration/`, com os dois ambientes existentes, executar a suíte ou
um exemplo local. Usar caminho novo para cada simulação:

```sh
rtk proxy .venv/bin/python -m pytest -q
rtk proxy timeout 15s .venv/bin/python -m galaxies_orchestration.observation_demo_v2 --case valid --output-dir ../data/private/observacao-v2-exemplo-novo
```

Não executar novamente os caminhos já consumidos. Recibos desta unidade:
`data/private/issue-5-observabilidade-local-v2/`, com pré-flight de **716 hashes**,
cinco diretórios de simulação e conferência final. Todos os pins e as 130
distribuições raiz/42 isoladas conferem. Oito PNGs preservados, zero workers
NIM/VLM/explicação no host ao terminar. M1/A200, lock, partições e teste reservado
permanecem iguais; não houve mídia ou inferência VLM. README não rastreado intacto.
As filas de produto continuam seladas em 41/64; nenhuma continuação ou C foi
executada. Esta unidade não conclui a integração final da #5 nem autoriza nova
auditoria cega.

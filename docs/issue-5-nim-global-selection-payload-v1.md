# Limite global de IDs: proposta inerte de payload

A chamada da rodada autorizada às 20:28 recebeu HTTP 200 e rejeição schema_constraint:
21 IDs, tipos corretos, únicos, presentes no catálogo e hash do pacote igual.
O contrato original exige 1..12 IDs no array evidence_ids da resposta inteira.
O schema anterior já dizia maxItems=12, mas a instrução textual não ressaltava
que o limite é global para os três criativos e os fatos compartilhados.

A interpretação de uma cota por criativo é uma hipótese compatível com a
ambiguidade textual, sem comprovação do raciocínio ou da distribuição da resposta.
Os IDs rejeitados não foram retidos; não se pode afirmar quantos eram de cada
criativo nem que outros problemas de schema estavam ausentes. A violação atual
de contagem não explica as rejeições antigas nem os dois erros HTTP 503.

## Alteração mínima

O builder público acrescenta uma regra antes do pedido anterior e um lembrete no
final: uma única lista com 1..12 IDs distintos **no total**, incluindo evidências
compartilhadas; a contagem não é por criativo. Mantém o pedido anterior integral,
o JSON Schema e os 24 IDs públicos. Não altera modelo, endpoint, temperatura,
max_tokens=2048, stream=false ou enable_thinking=false. Não adiciona parâmetros
de API, mensagens system/assistant ou ferramentas.

Dois exemplos exclusivamente inventados, com 1 e 12 IDs, ilustram a contagem.
Ambos passam no validador original. São exemplos de formato, sem escolher em
nome do modelo ou impor cotas por candidato. O consumidor continua rejeitando
excesso; não corta, reordena ou repara a resposta. A autoridade numérica/ranking
e a seleção original permanecem intactas. O limite de 12 vale para a lista
emitida pelo seletor; o renderer original continua acrescentando suas evidências
obrigatórias, que não constituem uma ampliação dessa lista de entrada.

| Corpo público | Bytes | SHA-256 |
| --- | ---: | --- |
| Anterior, preservado | 8576 | fd87bed20413c52bb7873d92da48c37d5f5f391a3fa9997e77177d073aaafcba |
| Proposta global v1 | 10065 | b39fdab9b943145fcf638c990e6e19b82c40f8c9df30b006f7c5fc16040b5987 |

O corpo novo está em `orchestration/fixtures/nim-global-selection-payload-v1.json`,
sem newline adicional, exatamente como retornado pelo builder. Não está ligado
ao worker live. Nenhuma CLI remota, autorização, revisão, namespace ou ledger novo
foi criado; as autorizações anteriores seguem consumidas. Uma futura execução
precisaria integrar e revisar explicitamente o corpo novo e obter autorização
específica, mantendo o mesmo endpoint/modelo, até 45 s totais, 2048 tokens,
16 KiB de resposta, R$0 e ausência de retry/reparo/fallback/redirect/proxy.

## Geração com constraint: documentação e limite da evidência

A [referência oficial deste modelo no endpoint hospedado](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-nano-omni-30b-a3b-reasoning-infer)
lista os parâmetros de chat, mas não documenta response_format ou guided_json.
Essa ausência não prova que sejam recusados; não estabelece suporte específico.
A [página geral de Structured Generation do NIM/VLM 1.7.0](https://docs.nvidia.com/nim/vision-language-models/1.7.0/structured-generation.html)
documenta response_format/json_schema, mas seu exemplo usa container local e
outro modelo. Não é comprovação de enforcement de maxItems neste endpoint/modelo.
Por isso o builder não acrescenta esse parâmetro por suposição e não foi feito
POST de sondagem. JSON válido por si só também não garante cardinalidade válida.

Se surgir documentação primária específica de suporte no endpoint, é possível
avaliar o mesmo schema como constraint de geração numa proposta separada. Não
seria autorização para mudar provider, instalar servidor ou criar fallback.
A validação local original continuaria necessária. A presente clarificação de
prompt reduz a ambiguidade, mas nenhum teste offline comprova adesão futura do
modelo, explicação aceita ou aderência qualitativa.

## Regressões locais

Os nove testes novos usam somente a fixture pública, com rede, getter e callbacks
de modelo bloqueados. Verificam a preservação dos campos originais, corpo exato,
exemplos válidos, rejeição de 0/13/21 e aceitação de 1/12 pela autoridade original.
A estrutura de 21 usa IDs escolhidos deliberadamente pela ordem do catálogo
público, sem alegar que foram os IDs devolvidos. Sua projeção segura coincide
com o diagnóstico sanitizado capturado, mas é **simulação estrutural, não replay
exato**. Não modifica o input e não promove seleção rejeitada. Análise numérica
e ranking permanecem iguais à fixture nas seleções aceitas.

```sh
rtk proxy env -C "$SOURCE" PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false "$ROOT_PYTHON" -B -m pytest -q tests/test_nim_global_selection_payload_v1.py --junitxml="$OPERATOR_RECEIPTS/nim-global-selection-payload-v1.xml"
```

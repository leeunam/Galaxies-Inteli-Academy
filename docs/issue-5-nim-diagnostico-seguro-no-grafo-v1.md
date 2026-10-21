# Issue #5 — diagnóstico seguro da seleção dentro do grafo

Candidato local de 21/10/2026, baseado em
`4569d8bb8dbb04c818afee3015d9d8afd87a134d`, importado somente por fetch local
para branch nova. A autorização anterior foi consumida. **Não há autorização
remota nova**, leitura de chave, nonce de autorização ou reserva real nesta
preparação. Nenhuma fonte/resultado/ledger antigo foi alterado.

## Desenho implementado

São quatro módulos aditivos, sem dependência ou plano remoto novo:

- `nim_selection_diagnostic_v1.evaluate_original` chama primeiro a autoridade
  `validate_selection` original, conservando sua aceitação/rejeição. Só depois
  usa o classificador seguro existente e observa a estrutura dos campos públicos.
- `nim_diagnostic_contract_v1` define e valida a lista fechada de metadados do IPC.
- `nim_diagnostic_worker_v1` acrescenta o diagnóstico ao `select` da ponte raiz,
  somente com respostas falsas. As outras etapas continuam na Session original.
- `nim_diagnostic_graph_v1` compila o mesmo `build_graph`/subgrafo e reutiliza
  `ProbeWorker`, ambiente, limites, recolhimento e verificação de prova existentes.

A seleção só atravessa o IPC quando a autoridade original a aceitou. Falha do
observador gera `diagnostic_failed`, sem transformar uma seleção aceita em
rejeitada, conceder aceitação ou alterar números/ranking. A renderização original
valida novamente a seleção, como antes. O diagnóstico tem de corresponder à
aceitação da prova raiz desta execução. O resultado v2 permanece em
`legacy_result`; `current_provider` continua explicitamente falso nos fakes.

O helper confere o SHA da fixture fixa e recusa outros contextos, comparando
pacote e análise completos antes de instrumentar. Não é observador
genérico de dados privados. `execute_remote()` recusa incondicionalmente antes
de ler arquivos, criar nonce/reserva, iniciar processo, acessar chave ou socket.
O CLI oferece somente casos offline; não há flag que libere o caminho real.

## Informação que pode sair

`selection_diagnostic` contém somente:

- estado da autoridade: `not_invoked`, `accepted`, `rejected` ou `failed_before_result`;
- fase/código estáticos e paridade do classificador quando determinável;
- tipos de quatro posições públicas: seleção interna, `packet_sha256`,
  `evidence_ids` e tipos distintos de `evidence_ids[*]`;
- cardinalidade do array e indicadores `duplicates`, `all_ids_in_catalog` e
  `packet_hash_equal`, quando avaliáveis. Indisponibilidade é `null`/`not_observed`.

Não saem corpo bruto, cabeçalhos, exceção arbitrária, nomes extras, IDs/valores
desconhecidos ou hash de conteúdo rejeitado. Mesmo o hash divergente é reduzido
ao booleano de igualdade; nenhum identificador remoto é copiado para o diagnóstico.
As categorias de tipo são fechadas; contagem, códigos, campos e booleanos do IPC
são validados estritamente. Diagnóstico nenhum pode conceder aceitação.
Os indicadores são calculados após a autoridade quando a estrutura permite;
não representam um trace da ordem dos checks internos. A paridade compara a
aceitação, e não reconstrói a exceção ou a resposta histórica.

Erros de envelope/transporte deixam a autoridade `not_invoked`, com código
estático e sem inferir campos internos. Os tipos observados são os da seleção
interna, não um inventário arbitrário de campos do envelope. O histórico antigo
continua sem diagnóstico fino; esta unidade não o reconstrói nem o reclassifica.

## Proposta exata para decisão do pai antes de 16h UTC

**Quantidade mínima proposta: um POST**, com o corpo já revisado e sem retuning:

| Item | Proposta, ainda sem autorização |
| --- | --- |
| Endpoint | `https://integrate.api.nvidia.com/v1/chat/completions` |
| Modelo | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` |
| Corpo | [JSON exato existente](../orchestration/fixtures/nim-graph-live-v1-http-payload.json), **8.576 bytes** |
| SHA-256 do corpo | `fd87bed20413c52bb7873d92da48c37d5f5f391a3fa9997e77177d073aaafcba` |
| Dados | Três criativos e 24 fatos inteiramente inventados: IDs, números, SHAP, referências e fingerprints |
| Saída / resposta | Até 2.048 tokens / 16 KiB |
| Execução | Deadline global de 45 s; recolhimento protegido pode ultrapassá-lo, sem timeout adicional |
| Outros parâmetros | Temperatura 0,2; `stream=false`; thinking desabilitado |
| Custo e repetição | Teto R$0; sem retry, reparo, redirect, fallback ou proxy |

Nenhuma mídia, transcrição, identificação ou valor derivado dos vídeos reais,
modelos ou artefatos privados entra nesse corpo. A base financeira continua a
confirmação já registrada de plano gratuito; não há nova consulta à conta ou
permissão para pagar, aceitar termos novos ou mudar acesso.

Se o pai aprovar a proposta, ainda serão necessários autorização humana
específica e registro técnico concreto vinculados à execução. O eventual
adaptador real deverá reutilizar o transporte/ownership de worker raiz único,
reserva exclusiva, nonce/pai reais e dispatch durável antes do getter já testados,
em namespace novo. Esta unidade não implementa nem libera essa adição real e
não reaproveita qualquer autorização/ledger consumido. Limites e hashes devem
ser reconfirmados antes de qualquer envio futuro.

| Desfecho eventual | Diagnóstico permitido |
| --- | --- |
| HTTP/framing/envelope inválido | Código estático; autoridade não invocada; campos internos indisponíveis |
| JSON interno inválido ou profundo | Código de sintaxe/duplicação/profundidade, sem guardar texto |
| Campo ausente, extra ou tipo incorreto | Código de schema e tipos apenas das posições conhecidas |
| Quantidade, duplicação, catálogo ou hash | Código e contagem/booleanos avaliáveis; valores desconhecidos suprimidos |
| Seleção aceita | Aceitação original, tipos válidos, contagem 1–12, sem duplicatas, catálogo/hash corretos |
| Falha inesperada da autoridade | `failed_before_result` e código estático, sem serializar a exceção |
| Falha do observador | `diagnostic_failed`; aceitação original preservada |
| Timeout/cancelamento/crash antes do IPC | Diagnóstico pode não chegar; resultado incerto consumido, sem retry |

Isso poderá explicar a próxima resposta observada, se um envio for autorizado;
não recupera a causa histórica nem valida geração livre, aderência ou qualidade
preditiva. Não há promessa de seleção aceita por manter o mesmo pedido.

## Verificação e hashes

Passaram **35 testes raiz em 0,55 s** e **12 isolados em 6,79 s**. Nos cinco casos
comuns, resultado legado e prova completos (exceto run ID) são iguais aos do
caminho anterior. Os testes cobrem autoridade antes do observador, fallback do
observador sem mudar aceitação, tipos/contagens/duplicação/catálogo/hash, valores
desconhecidos, contexto fora da fixture, IPC contraditório, um único select,
StateGraph/subgrafo compilados, worker raiz por IPC, timeout e cancelamento
repetido durante spawn com recolhimento. Nenhum fake/replay declara provedor real.
Houve um ajuste inicial de importação dos fixtures de teste antes desses checks
finais. Ruff e formatação passaram nos seis arquivos Python novos. Os 10 pins
live e os 137 pins offline anteriores conferem. Todos os processos dos testes
encerraram e os workers desta unidade foram recolhidos; nenhum permanece ativo.

Não houve HTTP, chave, nonce/reserva real, VLM, execução de modelo, instalação,
acesso persistente ou leitura de holdout. Os testes usam fixtures públicas e
guards explícitos contra rede, credencial e loaders reais. As fontes antigas
continuam byte a byte iguais. Nenhuma nova pilha de transporte/ledger foi criada.

| Fonte nova | SHA-256 |
| --- | --- |
| Contrato do diagnóstico | `c3d98988388f13127d47aaa5bc748c3cb1e1d679e499c74f48df96a0add60026` |
| Grafo offline | `10285886aea70a27613c0ddc037ee9fcc0bd9b62c44dac934cb0bda6f81fe876` |
| Helper após autoridade | `4a0f43bc990f07511f6ae41d4390979227690fe118c8e469fcb4a3d66d3f6253` |
| Worker offline | `c2d811765885e0c2b76c89bf8fb66db5ff6bf12f8d3f11af861c004cf41c17b4` |
| Testes raiz | `f46fe4bb0fdde6b5c5b9bd225f62bc5107877db279628d44170517dcb4e103f1` |
| Testes isolados | `4d57076fd32273b0946438f5009d7e4db08525a94627fa17d9972d25390e5520` |

Use `AUDIT_ROOT_PYTHON` e `AUDIT_GRAPH_PYTHON` como caminhos absolutos dos ambientes
já existentes. Na raiz do clone:

```sh
rtk proxy "$AUDIT_ROOT_PYTHON" -m pytest -q tests/test_nim_selection_diagnostic_v1.py
```

Em `orchestration/` do clone:

```sh
rtk proxy env GALAXIES_ROOT_PYTHON="$AUDIT_ROOT_PYTHON" "$AUDIT_GRAPH_PYTHON" -m pytest -q tests/test_nim_diagnostic_graph_v1.py
```

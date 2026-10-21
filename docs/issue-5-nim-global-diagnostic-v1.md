# Candidato protegido para o payload com limite global

Este candidato liga o [payload global1..12](issue-5-nim-global-selection-payload-v1.md)
ao worker, à abertura fixa, ao IPC, ao StateGraph/subgrafo e ao resultado persistido.
Não autoriza nem executa uma chamada: nenhum recibo de autorização/revisão/ledger
real foi criado. A autorização 829d e as anteriores estão consumidas.

O corpo novo tem **10065 bytes**, SHA-256
`b39fdab9b943145fcf638c990e6e19b82c40f8c9df30b006f7c5fc16040b5987`.
Conserva os três criativos/24 fatos inventados, pacote, schema, autoridade, modelo,
endpoint e parâmetros. Só esclarece em texto o limite global com exemplos válidos.
Isso não comprova adesão futura nem transforma a simulação de 21 IDs em replay
exato: a distribuição e os valores rejeitados reais não foram retidos.

## Deltas e reuso

O worker novo herda handshake de nonce e proof/nós não-select do worker v3.
O select usa a mesma autoridade e adapter de diagnóstico, com contrato/namespace
novos e a nova abertura fixa. O selector de metadados e ReleasedProbeWorker são
importados diretamente, sem reimplementar spawn, cancelamento ou cleanup. Binding,
codec durável v3, PID real do pai, nonce e authorize original continuam preservados.
As fontes compartilhadas e as novas estão vinculadas no plano público por hash.
Não há exec dinâmico, alteração de globals/PID ou edição de fonte selada.

Como live_response anterior fixa 8576 bytes, `nim_global_fixed_http_v1` acrescenta
somente a abertura explícita para o builder global. Valida 10065 bytes/SHA antes
do socket, chave sintaticamente válida e timeout; cria uma HTTPSConnection direta
para integrate.api.nvidia.com:443, POST /v1/chat/completions, TLS padrão e os mesmos
três headers. A factory é obrigatória no seam privado de teste; live_response
liga explicitamente HTTPSConnection, sem SDK, proxy, redirect ou retry. Não há
opção de ROOT, modelo, endpoint ou body remoto arbitrário. Nenhum parâmetro de
geração não comprovado no hosted endpoint foi acrescentado.

Os fakes percorrem essa mesma abertura com conexão inventada: verificam bytes,
SHA, host/porta/path, modelo/parâmetros, headers e deadline antes de devolver
resposta. A factory do worker também exige o dispatch durável já existente. Há
uma criação/POST inventado/resposta/close, mas **zero requisições HTTP reais**.
Aceitação pela autoridade original nunca promove real_provider_verified nos fakes.

Permanecem 45 s totais: até 43 s de trabalho e até 1 s de drain + 1 s de confirmação
do reaping do único filho. Falha de cleanup não libera resultado observed nem
restaura nonce. Para fakes curtos, os máximos são proporcionalmente menores.
2048 tokens, resposta até 16 KiB e teto R$0, sem reparo/fallback/repetição.

## Diagnóstico e limites honestos

O resultado novo preserva shape, tipos, cardinalidade, duplicatas, igualdade do
hash, pertencimento ao catálogo e classifier_parity do diagnóstico v3. O sidecar
HTTP continua separado: schema fechado, status ligado ao transport, UUID opcional
estrito e categorias fixas. Metadata inválido no adapter/IPC é descartado sem
apagar seleção/transport/autoridade. Números, ranking e contexto permanecem iguais
à fixture. Corpo/IDs rejeitados, headers desconhecidos, cookies, auth, strings
livres, exceções e hashes desconhecidos não são persistidos.

Corpo de erro HTTP permanece não lido. Nos erros, só cinco campos permitidos são
consultados, cada valor limitado a 128 caracteres após o parser. Em 200, mantém-se
a leitura original de 16 KiB+1 para detectar excesso e framing pós-parser de até
100 headers/soma de 16 KiB em nomes e valores. Não existe novo hardcap global de
16 KiB antes do parser do http.client. Não se atribui causa retroativa aos 503 ou
às rejeições antigas. A clarificação global não garante seleção aceita ou aderência
qualitativa em uma futura resposta.

## Recibos externos, ausentes

AUTHORIZATION_ID=null, remote_execution_released=false e remaining_authorized_calls=0
descrevem o candidato entregue, sem saldo herdado. Não é necessário mudar código
após aprovação humana: autorização e revisão específicas devem ser registradas
externamente pelo coordenador, que confere o transcript. Não há CLI para criá-las.
O parser de recibos não autentica por si só a origem humana dessa evidência.

Os caminhos fixos dentro de SOURCE são:

- `data/private/issue-5-nim-global-diagnostic-v1-authorization/authorization.json`
- `data/private/issue-5-nim-global-diagnostic-v1-review/technical-review.json`
- `data/private/issue-5-nim-global-diagnostic-v1` para reserva/resultado únicos.

Os campos fechados são os mesmos do v3, com novos protocol/plano/config/payload:
receipt_binding vincula protocol, plan_sha256, configuration_sha256,
execution_root_sha256, http_payload_sha256 e financial_evidence_id. A autorização
acrescenta decision=authorized_for_one_synthetic_attempt, authorized_calls=1,
recorded_by_thread_id do coordenador selado e specific_remote_authorization_id
da nova mensagem explícita. A revisão acrescenta
decision=approved_for_one_synthetic_attempt, specific_remote_authorization_id,
authorization_receipt_sha256, reviewer_thread_id e source_message_id da revisão.
Planos/fontes/ROOT/payload/financeiro e bytes exatos da autorização ficam ligados.
829d, 102f, todos os IDs consumidos conhecidos e pedidos genéricos são recusados.

O pai recusa ausência/invalidez antes de nonce, reserva, spawn, getter ou socket;
o filho confere novamente antes do contexto e do dispatch/getter/HTTP. Dispatch
exclusivo e durável precede acesso à chave. Reserva existente significa consumo
em qualquer resultado, inclusive 503, timeout ou interrupção incerta. Não se repete.
Fakes recusam todos os namespaces issue-5-nim-* e symlinks, em qualquer checkout.

## Comandos para revisão e eventual proposta

SOURCE, ROOT_PYTHON, GRAPH_PYTHON e OPERATOR_RECEIPTS são parâmetros do operador.
Só a seleção nova/afetada deve ser executada, sem repetir suítes antigas:

Nesta unidade passaram 9 testes da abertura inventada e 26 do perfil/worker/grafo.
Isso valida os caminhos simulados e os bloqueios; provedor real permanece não
verificado. Não houve chamada de inferência, acesso à chave ou novo orçamento.

```sh
rtk proxy env -C "$SOURCE" PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false "$ROOT_PYTHON" -B -m pytest -q tests/test_nim_global_fixed_http_v1.py --junitxml="$OPERATOR_RECEIPTS/nim-global-fixed-http-v1.xml"
rtk proxy env -C "$SOURCE" PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=orchestration GALAXIES_ROOT_PYTHON="$ROOT_PYTHON" LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false "$GRAPH_PYTHON" -B -m pytest -q orchestration/tests/test_nim_global_diagnostic_v1.py --junitxml="$OPERATOR_RECEIPTS/nim-global-diagnostic-v1.xml"
```

Somente após integração, nova autorização específica e revisão/recibos conferidos:

```sh
rtk proxy env -C "$SOURCE" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=orchestration LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false "$GRAPH_PYTHON" -B -m galaxies_orchestration.nim_global_diagnostic_v1 --execute-reviewed-once --worker-python "$ROOT_PYTHON"
```

Proposta futura: exatamente **um POST** sintético neste corpo de 10065 bytes/SHA
acima, mesmo modelo/endpoint, até 45 s totais (43+2), 2048 tokens, 16 KiB e R$0,
sem retry/reparo/fallback/redirect/proxy. Qualquer resultado encerra a tentativa.
Nada nesta preparação constitui autorização para executar esse comando.

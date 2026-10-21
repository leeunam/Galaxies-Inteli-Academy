# Diagnóstico HTTP ligado ao worker e ao grafo, candidato v3

Esta unidade conecta o adapter metadata-only ao worker ROOT, ao IPC, ao selector
do StateGraph/subgrafo e ao novo resultado persistido. Não houve POST, leitura de
credencial, inferência ou criação de autorização/revisão/ledger real. Os dois 503
anteriores permanecem consumidos e sem causa específica conhecida. A resposta
histórica rejeitada em 200 não foi recuperada por esta alteração.

## Caminho executável

O novo worker usa `nim_http_error_observer_v1.observe_opened_response` e transmite
`selection`, o diagnóstico original, `http_error_metadata` e seu estado fixo.
Sidecar inválido do adapter é descartado ainda no filho, preservando o resultado
original; a mesma regra é aplicada a corrupção IPC no pai. O pai remove somente
o sidecar para delegar ao `DiagnosticSelector` original. Depois do proof, valida o
formato fechado e a igualdade do status do sidecar com o transport observado.
Status 200 ou ausente exige sidecar null; status não 200 válido admite apenas o
schema fechado já definido. No resultado novo, os campos são
`http_error_metadata` e `http_error_metadata_state` (not_applicable, validated ou
invalid_ipc_metadata). Um sidecar IPC inválido é descartado, sem mudar a seleção,
autoridade, transport ou ranking e sem persistir seu valor ou exceção.

O processo é o `ReleasedProbeWorker` selado, sem reimplementar spawn, cancelamento
ou cleanup. Mantém 43 s máximos de trabalho e até 1 s de drain + 1 s de confirmação
de reaping dentro do total de 45 s. Cleanup não confirmado impede resultado
observed. Para fakes curtos, os mesmos limites são proporcionalmente menores.
O binding usa a mesma representação do intervalo deadline-started já corrigida.
O codec stdlib de reserva v3 é o mesmo usado pelo v2; o filho chama `authorize`
original, com nonce original e o PID real do pai. Dispatch exclusivo e durável
precede `existing_key()` e o transporte; nenhum PID ou global é substituído em
produção. O transporte `live_response`, a autoridade, o catálogo e o grafo são
reutilizados por hash. Não há novo SDK, HTTP grandchild ou caminho de inferência.

## Limites de observação

Nos erros HTTP, o corpo continua não lido. Consultam-se somente os cinco campos
permitidos, cada valor com até 128 caracteres depois do parser. O request-ID NVCF
é opcional e só sai como UUID estrito; ausência, duplicata, má-formação ou falha
do accessor vira categoria fixa. Não se enumera header desconhecido nos erros,
nem se retém auth, cookie, corpo, texto livre, exceção ou hash desconhecido.

Em 200, o adapter original mantém sua leitura de 16 KiB + 1 para detectar excesso
e o framing original: até 100 headers e soma de nomes/valores até 16 KiB **depois
do parser**. Isso não constitui teto de 16 KiB para todos os bytes dos headers
no fio ou antes do parser. O `http.client` continua sujeito aos próprios limites
de parser e ao timeout/encerramento do processo; não foi reescrito nesta unidade.
Os fakes cobrem corpo 200 no limite/excesso, 100/101 headers, campos
permitidos longos ou duplicados e erros 401/403/429/503. Unknown headers nunca viram resultado.

## Autorização externa, ainda ausente

O plano/config não incorpora nova permissão: AUTHORIZATION_ID é null,
remote_execution_released=false, remaining_authorized_calls=0 e gasto real
liberado é zero. proposed_future_calls=1 expressa a proposta, nunca saldo após
reserva. Não será preciso alterar código ou plano após uma aprovação humana:
a entrada fixa exige dois recibos externos, registrados pelo coordenador somente
após nova autorização específica e revisão técnica. Não existe CLI para criá-los.
O parser não comprova por si só a origem humana; a revisão independente deve
conferir o transcript específico antes de registrar esses recibos privados.

Os caminhos relativos fixos, dentro de SOURCE, são:

- `data/private/issue-5-nim-worker-diagnostic-v3-authorization/authorization.json`
- `data/private/issue-5-nim-worker-diagnostic-v3-review/technical-review.json`
- `data/private/issue-5-nim-worker-diagnostic-v3` para a única reserva/resultado.

Ambos os recibos exigem exatamente os campos comuns de `receipt_binding(plan)`:
protocol, plan_sha256, configuration_sha256, execution_root_sha256 (SHA-256 do
caminho absoluto resolvido de SOURCE, sem publicá-lo), http_payload_sha256 e
financial_evidence_id. O plano vincula por hash as fontes e fixture públicas.

O recibo de autorização acrescenta decision=authorized_for_one_synthetic_attempt,
authorized_calls=1, recorded_by_thread_id igual ao coordenador selado e
specific_remote_authorization_id igual ao ID da **nova mensagem explícita**.
IDs consumidos (inclusive 102f), a confirmação financeira e o pedido genérico
c2b133 são recusados. O recibo técnico acrescenta
decision=approved_for_one_synthetic_attempt, specific_remote_authorization_id,
authorization_receipt_sha256 (bytes exatos do primeiro recibo), reviewer_thread_id
igual ao coordenador selado e source_message_id da revisão real. Campos extras,
alterações de ROOT/plano/config/input/financeiro ou hash de autorização falham.

O pai exige esses recibos antes de nonce, reserva ou spawn. O filho volta a
conferi-los no startup e antes de dispatch/getter/socket, e vincula seus hashes
ao binding, ao proof e ao novo resultado. Recibo ausente/inválido não concede
chamada. A existência da reserva significa consumo, inclusive crash, timeout,
cancelamento ou 503; nunca se tenta novamente no mesmo namespace. Fakes recusam
todo componente issue-5-nim-* e symlinks, inclusive em outro checkout. Seus
real_http_requests são zero e real_provider_verified é sempre false.

## Verificação e eventual comando

Os testes novos executam processos Python reais somente com respostas inventadas;
comprovam criação única, um select/dispatch, recusa de reentrada, persistência,
limpeza, autoridade 200, números/contexto/ranking preservados nos erros e supressão
de sidecar IPC corrompido. As suítes antigas não são repetidas. SOURCE,
ROOT_PYTHON, GRAPH_PYTHON e OPERATOR_RECEIPTS são parâmetros do operador.

```sh
rtk proxy env -C "$SOURCE" PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=orchestration GALAXIES_ROOT_PYTHON="$ROOT_PYTHON" LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false "$GRAPH_PYTHON" -B -m pytest -q orchestration/tests/test_nim_worker_diagnostic_v3.py --junitxml="$OPERATOR_RECEIPTS/nim-worker-diagnostic-v3.xml"
```

Somente depois da nova autorização específica, integração e recibos revisados:

```sh
rtk proxy env -C "$SOURCE" PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=orchestration LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false "$GRAPH_PYTHON" -B -m galaxies_orchestration.nim_worker_diagnostic_v3 --execute-reviewed-once --worker-python "$ROOT_PYTHON"
```

Não executar esse comando nesta fase. Não aceita endpoint, modelo, payload,
ROOT ou ledger remoto arbitrários. Proposta humana específica:

> Você autoriza exatamente uma nova chamada NVIDIA exclusivamente sintética,
> com os mesmos três criativos e 24 fatos inventados, mesmo endpoint
> https://integrate.api.nvidia.com/v1/chat/completions e modelo
> nvidia/nemotron-3-nano-omni-30b-a3b-reasoning, corpo exato de 8.576 bytes
> SHA-256 fd87bed20413c52bb7873d92da48c37d5f5f391a3fa9997e77177d073aaafcba,
> até 45 s totais (43+2), 2.048 tokens, resposta até 16 KiB e custo máximo R$0?
> O diagnóstico novo registra apenas status, request-ID opcional validado e
> categorias fixas; não lê corpo de erro. Não envia vídeos nem altera conta.
> Qualquer resultado, inclusive outro 503, encerra a única tentativa, sem retry,
> reparo, fallback, redirect ou proxy.

Uma resposta válida permite avaliar separadamente execução/transporte, seleção
fechada do catálogo e aderência às evidências públicas. 200 aceito comprova a
seleção e preservação numérica, mas não substitui a avaliação qualitativa de
aderência. Novo 503 só documenta falha de execução e eventual ID para correlação;
não demonstra quota, capacidade global ou inadequação do modelo e não autoriza retry.

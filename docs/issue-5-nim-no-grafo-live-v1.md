# Issue #5 — candidato para uma chamada real dentro do subgrafo

Preparação de 21/10/2026. A aprovação humana específica de uma chamada adicional
está em `Sentinel_d3d52a72c3308191b76c892fed01f4aa`, às 11:50 UTC, em resposta
à proposta de um POST dentro do grafo com três exemplos inteiramente inventados,
mesmo endpoint/modelo, teto R$0 e sem repetição. A preparação **não executou**
essa chamada. HTTP e leitura da chave aguardam revisão técnica concreta,
integração e recibo privado vinculado à árvore executora.

## Pedido e limites preservados

O corpo é exatamente o já revisado na unidade offline: **8.576 bytes**,
SHA-256 `fd87bed20413c52bb7873d92da48c37d5f5f391a3fa9997e77177d073aaafcba`.
Fixture, pacote, schema e instruções não mudaram. São três criativos e 24 fatos
inteiramente inventados, incluindo números, SHAP, referências, IDs e fingerprints.
Nenhum valor deriva das três mídias reais, modelos ou artefatos privados.

Endpoint: `https://integrate.api.nvidia.com/v1/chat/completions`.
Modelo: `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`.
Uma chamada, 2.048 tokens, resposta de até 16 KiB, temperatura 0,2, stream falso,
thinking desabilitado, orçamento de execução de 45 s e teto **R$0**.
Não há retry, reparo, fallback, proxy, redirect ou mudança de alvo/provedor.
A base financeira continua a confirmação anterior de plano gratuito; 40 rpm não
é prova de saldo. Pagamento ou termos/acesso novos não são autorizados. Resposta
de cobrança/erro encerra a tentativa, sem fluxo para pagar ou aceitar termos.

As fontes, planos e ledgers anteriores permanecem intactos. O plano novo verifica
o plano offline e seus 137 pins, sela as novas fontes e exige recibo de revisão.
Nenhum CLI cria sua própria aprovação ou reinicia uma tentativa consumida.

## Ownership: o próprio worker raiz faz HTTPS

O processo do StateGraph cria a reserva exclusiva e durável antes de iniciar
seu único worker raiz. O codec de reserva é o v3 existente, implementado apenas
com stdlib no novo contrato para o interpretador isolado; seu `parent_pid` é o
PID real do grafo. O nonce de 32 bytes é enviado somente por IPC ao filho.

Dentro do subgrafo compilado original, `select` chama o worker raiz depois de
`context` e antes de `render`. O worker reconfere plano, revisão, run ID, pacote,
deadline e vínculo do pai. A função **original** `nim_dispatch_ledger_v3.authorize`
valida o nonce e seu `os.getppid()` real, sem substituição de PID/PPID, e grava o
marcador exclusivo/durável antes do getter da chave existente.

O HTTPS ocorre nesse mesmo worker raiz. Não existe neto HTTP ou nova sessão de
rede que possa sobreviver à morte da ponte. O `ProbeWorker` existente protege o
handle durante spawn e o kill/wait contra cancelamentos repetidos; matar o único
filho também fecha seus sockets pelo sistema operacional. O worker não cria
subprocessos de transporte ou modelos. A conexão é direta, com SSL padrão e
debug zero. Chave não entra em prompt, argv, ambiente herdado, IPC, recibo ou log.
O clone não recebe `.env`; só a árvore integrada poderá usar seu getter existente
depois das guardas e da revisão específica daquele checkout.

O deadline global começa antes dos preflights e da reserva; o worker usa o
deadline monotônico vinculado à execução para o socket, e o pai limita spawn,
grafo, seletor e IPC pelo mesmo orçamento. O recolhimento é protegido e pode
terminar depois dos 45 s: não existe timeout adicional para recuperar handle
pendente e aguardar `process.wait()`. Isso é explicitado, sem promessa de teto
absoluto de parede incluindo cleanup. Resultado incerto permanece consumido.

## Prova fresca e autoridade

A autoridade raiz original recebe o conteúdo do envelope antes de qualquer
projeção. Só IDs conhecidos e validados do pacote público atravessam IPC; o
render original valida novamente sem alterar números, ranking ou afirmações.
O novo envelope conserva `legacy_result` v2 e seu literal
`orchestration.real_provider_verified=false`, além de handoff nativo falso.

`current_provider` distingue `offline_fake` e `live_nim`. A verificação real só
é verdadeira quando há, na mesma execução: um seletor, run ID atual, pacote
correspondente, reserva/nonce/pai e dispatch duráveis corretos, revisão vinculada,
um POST com HTTP 200 e metadados limitados válidos, aceitação da seleção e da
renderização raiz. A sequência é `analyze → shap → comparables → context → select
→ render → proof`, precedida pelo handshake privado do nonce.

Um HTTP falso aceito permanece falso. Recibo de outro run, origem forjada,
dispatch em cache ou resultado já finalizado não pode produzir verificação real.
Não há argumento de replay ou carregamento de resposta. Corpo bruto, cabeçalhos,
exceções e seus hashes não são retidos. O recibo contém somente estados, códigos,
metadados limitados, plano/configuração/autorização e projeção pública permitida.

## Novo consumo, revisão e passagem

Ledger fixo: `data/private/issue-5-nim-graph-live-v1/`.
Revisão: `data/private/issue-5-nim-graph-live-v1-review/technical-review.json`.
Arquivos 0600 e diretórios 0700; criação exclusiva, sem symlinks e com fsync.

A revisão do operador deve conter exatamente protocolo, decisão
`approved_for_one_synthetic_attempt`, hashes novos de plano/configuração,
`specific_remote_authorization_id`, `financial_evidence_id`, `reviewer_thread_id`,
`execution_root_sha256` e `source_message_id` da revisão técnica concreta.
O hash da árvore é SHA-256 dos bytes UTF-8 do caminho absoluto resolvido da
árvore executora. É guarda de integridade/coordenação em armazenamento do
operador, não autenticação contra o proprietário desses arquivos.

Depois da revisão e integração pelo escritor da principal:

1. Importar a branch `codex/issue-5-nim-no-grafo-live-v1` exclusivamente do clone
   local `/tmp/galaxies-nim-dispatch-v3`. As dependências são a unidade offline
   `7a7f0f00a642ff4cbea3941c41298ee085bffb37` e seu adendo documental
   `c8847f504e4159ac3f40e61ca9185a452815c0b1`, caso ainda não integrados.
   Conferir fontes/pins e ausência do novo ledger real; não ler/reabrir os antigos.
2. Registrar a revisão específica vinculada à principal, com os hashes finais.
3. Liberar uma janela sem modelos concorrentes e executar **uma única vez**, a
   partir de `orchestration/`, com os dois interpretadores existentes:

```sh
rtk proxy /caminho/isolado/python -m galaxies_orchestration.nim_graph_live_v1 --execute-reviewed-once --worker-python /caminho/raiz/python
```

4. Conservar `reservation-v3.json`, `live-graph-binding.json`, `dispatch-v3.json`
   quando criado, e `graph-result-live-v1.json`. Existência do diretório consome a
   tentativa mesmo em crash anterior ao recibo; nenhuma incerteza permite retry.

Simulações exigem `--offline-case` e diretório exclusivo em `--simulation-ledger`.
Recusam os ledgers/revisões antigos e novos, descendentes e aliases por symlink.
Usam o mesmo vínculo de pai/nonce/dispatch, com transporte exclusivamente falso
e zero chamadas reais; não leem chave nem aprovação real.

## Validação do candidato

Passaram **13 testes raiz em 2,12 s** e **14 testes isolados em 5,52 s**, executados
em sequência após devolução explícita da CPU. Ruff e formatação passaram nos seis
arquivos Python novos. Não houve HTTP real ou leitura de chave; todos os stubs
e as chaves de teste são inventados. O teste da ordem do getter usa subprocesso
direto real e não substitui `getpid`/`getppid`; sua conexão é explicitamente falsa
e não é publicada como verificação de provedor. A demonstração fake pelo grafo
sempre mantém verificação real falsa, mesmo quando a autoridade aceita a seleção.

Foram conferidos corpo exato e recusa antes de socket se ele mudar,
revisão/root-binding, dispatch/getter, PID/PPID reais, um POST sem neto,
StateGraph/subgrafo compilados, consumo único, pacote divergente,
provas falsas/recibos em cache, deadline e cancelamento antes e depois do dispatch.
Os testes confirmaram encerramento e recolhimento do único worker. Não houve
instalação, execução de modelos ou repetição das suítes anteriores de 24/140.

O novo plano sela **10 arquivos** e verifica o plano predecessor com **137 pins**.
O selo fica fora de sua própria lista para evitar autorreferência. As fontes
rastreadas anteriores permaneceram sem mudança; o ledger real novo e o recibo
de revisão continuam ausentes no clone. O corpo HTTP exato está disponível como
arquivo público `orchestration/fixtures/nim-graph-live-v1-http-payload.json`, sem
newline adicional; seus bytes são iguais aos retornados pelo gerador original.

| Artefato | SHA-256 |
| --- | --- |
| Plano live | `4e5f3acbfcf49b788894ac5072807aabad803743e58deeba36f87e17f6e794d6` |
| Configuração | `277ce579b81403b819620f924063eb9970e64a52f57242b5b9ebf202dda17a1f` |
| Corpo HTTP, 8.576 bytes | `fd87bed20413c52bb7873d92da48c37d5f5f391a3fa9997e77177d073aaafcba` |
| Fixture preservada | `365df6cc87cbca007ac8a5e09076f8c308cf78e7a49fe8151499159e12b7a380` |
| Pacote preservado | `6f41c37e13100704a6c5ae729f32371404dadc806933ffe05b00b20b6452ee2a` |
| Schema preservado | `b8ad28515e2b2b90912ddbaef3d1579e805f68ad9bcf05b8e636715fe140d66b` |

Comandos focados usados no clone, com ambientes existentes da principal:

Na raiz do clone:

```sh
rtk proxy /home/inteli/Documents/projetos/Galaxies-Inteli-Academy/.venv/bin/python -m pytest -q tests/test_nim_graph_live_contract_v1.py
```

Em `orchestration/` do clone:

```sh
rtk proxy env GALAXIES_ROOT_PYTHON=/home/inteli/Documents/projetos/Galaxies-Inteli-Academy/.venv/bin/python /home/inteli/Documents/projetos/Galaxies-Inteli-Academy/orchestration/.venv/bin/python -m pytest -q tests/test_nim_graph_live_v1.py
```

Esses comandos usam somente os testes falsos e não liberam o POST real. A revisão
técnica concreta, o recibo vinculado à principal e a janela do único envio continuam
pendentes; esta preparação não consumiu a autorização humana nova.

A chamada futura comprovará, se aceita, o provedor no subgrafo sobre esta fixture.
Não é demo com as três mídias reais, geração livre em português, reasoning,
aderência qualitativa ou avaliação preditiva; esses limites permanecem explícitos.

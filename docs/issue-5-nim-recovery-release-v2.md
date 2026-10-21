# Segunda liberação NIM: uma chamada sintética nova

Perfil aditivo ligado à proposta inerte de SHA256
`c0b16f708e77c6bf78c6478cc6837be2380dd858c23dff84daad3b9e6190452e`.
A autorização específica é `Sentinel_102f607fc6d08191a1119f9a48149a34`, resposta
“sim” às 18:43 UTC de 21/10/2026 ao pedido `Sentinel_bc8e9b7c699481918150bd3991bee8ef`.
Esse pedido separou quatro inferências locais e um POST NVIDIA; este perfil usa
somente o POST sintético, até 45 s, R$0, sem repetição. Outro 503 encerra a tentativa.
A autorização c3 e o perfil anterior permanecem consumidos e imutáveis.

São variantes mecânicas dos três adaptadores de identidade/entrada/worker porque
seus imports de contrato são fixos. Não foi criado framework ou infraestrutura
nova: dono do processo 43+2, transporte HTTPS, codec PID/nonce, grafo/subgrafo,
autoridade e diagnóstico são reutilizados por hash. Não há monkeypatch de produção
ou PID falso. A proposta inerte continua com AUTHORIZATION_ID=None e sem despacho.

O protocolo `nim-three-recovery-release-v2` fixa os namespaces novos
`data/private/issue-5-nim-graph-recovery-release-v2` e
`data/private/issue-5-nim-graph-recovery-release-v2-review/technical-review.json`.
Revisão técnica nova deve vincular autorização, plano/configuração final, evidência
financeira preservada e hash do caminho do checkout. A entrada, reserva e worker
verificam essa revisão antes de nonce/chave/socket. O despacho v3 exclusivo precede
o getter; o PID é o pai real. Existência da reserva significa consumo, inclusive
em falha/incerteza. Não se criam nem consultam ledgers consumidos para liberar outra
chamada. Os recibos/bindings v2 têm nomes próprios dentro do namespace novo.

Mantêm-se 8576 bytes de corpo, SHA256
`fd87bed20413c52bb7873d92da48c37d5f5f391a3fa9997e77177d073aaafcba`,
três criativos e 24 fatos inventados, mesmo modelo
`nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` e endpoint
`https://integrate.api.nvidia.com/v1/chat/completions`, 2048 tokens, 16 KiB e R$0.
O prazo total continua 45 s, até 43 s úteis e 2 s de cleanup. Sem retry, reparo,
fallback, redirect, proxy, mídia privada ou mudança de conta/acesso.

A configuração com uma chamada é inicial, não saldo após reserva. Seleção fake ou
replay continua incapaz de comprovar provedor real. Fakes recusam symlinks e todos
os componentes `issue-5-nim-*`, incluindo namespaces anteriores, futuros e v2.

O critério permanece o da proposta: 503 é falha de transporte antes da autoridade,
sem atribuição de causa; resposta válida permite verificar envelope, seleção de
catálogo e aderência descritiva aos fatos públicos. Não se infere qualidade de
explicação livre ou modelo em dados reais. Nenhum diagnóstico remoto extra foi
adicionado e nenhum corpo/header/valor/hash desconhecido é retido.

Após integração e revisão técnica real nova pelo coordenador, o comando único é:

```sh
rtk proxy env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SOURCE}/orchestration" LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false "${GRAPH_PYTHON}" -B -m galaxies_orchestration.nim_recovery_release_v2 --execute-reviewed-once --worker-python "${ROOT_PYTHON}"
```

O comando não foi executado nesta preparação. Não houve leitura de chave, POST,
revisão/ledger/nonce reais, instalação, edição de ambiente ou escrita na principal.
Os testes focam somente identidade/revisão/consumo novos; não repetem as suítes
anteriores nem executam modelos. O integrador único confere o selo e decide o
momento do despacho após encerrar/reconciliar a frente visual.

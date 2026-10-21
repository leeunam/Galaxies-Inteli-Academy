# NIM no subgrafo: execução negada antes de criar processo

Registro de 21/10/2026, sobre o candidato integrado em `48ab4f4` e seus
27 testes aprovados. A revisão automática da ferramenta **negou a criação
do processo** do único POST sintético. Não é resposta da NVIDIA ou falha
semântica do provedor. Nenhum CLI, worker, getter de chave ou POST foi iniciado.
A [evidência do bloqueio](evidence/issue-5-nim-no-grafo-live-bloqueio.json)
conserva ação, alvo, comando parametrizado, motivo exato e estado reconciliado.

## Ação e comando bloqueados

Alvo: `https://integrate.api.nvidia.com/v1/chat/completions`, modelo
`nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`. Pedido fixo de 8.576 bytes,
três exemplos inteiramente inventados, prazo de execução 45 s, saída até
2.048 tokens/16 KiB, teto R$0 e sem retry. O comando foi solicitado com
`sandbox_permissions=require_escalated`; o revisor negou antes de executá-lo.
Diretório de trabalho:

```text
${PROJECT_ROOT}/orchestration
```

Representação parametrizada do comando solicitado, incluindo captura de stdout:

```sh
rtk proxy .venv/bin/python -B -m galaxies_orchestration.nim_graph_live_v1 --execute-reviewed-once --worker-python ${PROJECT_ROOT}/.venv/bin/python > ${NEW_RECEIPTS}/permitted-stdout.json
```

`${PROJECT_ROOT}` representa a árvore executora e `${NEW_RECEIPTS}` o diretório
privado de recibos do operador. O argv/cwd exatos e o envelope original ficam
somente no recibo privado preservado, sem alteração. Esses símbolos documentais
não concedem liberação ou autorizam outro executor.

## Texto exato da rejeição

A mensagem abaixo foi extraída do recibo original da ferramenta, com os
escapes de newline decodificados; não é reconstrução de um erro do CLI.
O agregado público contém sua projeção sanitizada; o envelope integral permanece privado.

```text
This action was rejected due to unacceptable risk.
Reason: This executes an external authenticated POST using a credential and may incur service-side effects, but the available authorization is only relayed through untrusted assistant/tool content rather than a trusted user message.
Do not bypass this rejection through a workaround or indirect execution. Continue with a safer alternative, or carry out checks to prove that the action is authorized or low risk before trying again. Complete unaffected work without asking for confirmation. Report anything that remains blocked, clarify why it was blocked by auto-review, inform the user of the risk and ask for approval.
```

## Reconciliação, sem nova tentativa

- Estado: `denied_before_process_creation`; não existe código de saída do CLI.
- Ledger novo ausente; nenhuma reserva ou marcador de dispatch foi criado.
- Revisão técnica e sua origem literal já gravadas permanecem preservadas.
- O arquivo preparado para captura de stdout continua com o placeholder do
  operador `not_started`; isso não é uma saída emitida pelo CLI.
- Zero workers relevantes; zero chave lida, HTTP iniciado ou POST consumido.
- Sem retry, reentrada, wrapper, executor alternativo ou outro caminho de envio.

A autorização humana havia sido retransmitida ao executor. A revisão automática
não a reconheceu como mensagem direta confiável para essa ação autenticada.
Reformatar a mesma retransmissão não resolve o bloqueio. A solicitação de
confirmação direta foi apresentada, sem nova execução. Reconsiderar depende de
evidência humana nova materialmente relevante aceita pela revisão, mantendo
contrato, payload e limites; este documento não concede liberação.

O [teste NIM tipado anterior](issue-5-nim-typed-request-v1-resultados.md)
continua aceito e consumido fora do grafo. A [ligação offline](issue-5-nim-no-grafo-offline-v1.md)
continua verificada com transporte falso. O candidato live foi integrado,
mas ainda não há prova real do provedor dentro desse subgrafo nem consumo
do POST proposto. As flags da demonstração real permanecem falsas, sem
mudança de M1, atributos, avaliação ou status de issue/projeto.

Fontes, contratos, ledgers anteriores, oito PNGs, partições e teste reservado
permanecem preservados. Não houve novo teste, modelo, aquisição, instalação,
publicação ou leitura de segredo na documentação deste bloqueio.

Plano: `4e5f3acbfcf49b788894ac5072807aabad803743e58deeba36f87e17f6e794d6`.
Configuração: `277ce579b81403b819620f924063eb9970e64a52f57242b5b9ebf202dda17a1f`.
Payload: `fd87bed20413c52bb7873d92da48c37d5f5f391a3fa9997e77177d073aaafcba`.

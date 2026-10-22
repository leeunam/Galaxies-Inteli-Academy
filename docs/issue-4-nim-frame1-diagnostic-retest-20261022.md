# Reteste visual NVIDIA: limite do worker registrado

A única repetição autorizada do primeiro frame retornou **HTTP 503**. Desta vez,
a captura preservou integralmente a mensagem sanitizada do provedor:

> ResourceExhausted: Worker local total request limit reached (16/16)

O corpo JSON informa `error.code="503"` e `error.type="Service Unavailable"`.
A mensagem identifica um limite de requisições no worker. Não identifica saldo
financeiro, crédito da conta ou limite de 40 requisições por minuto.

| Medida | Resultado |
| --- | --- |
| Modelo solicitado | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` |
| Modelo retornado | não informado na resposta de erro |
| Início UTC | `2026-10-22T16:24:04.742615+00:00` |
| Latência do cliente / rodada com limpeza | 0.662 s / 1.227 s |
| Corpo recebido | 131 bytes; projeção de erro sem truncamento |
| Request ID | `4a146762-4e6e-47fd-aaab-09e4e91ba66e` |
| Tentativas / imagens / saldo | 1 / 1 / 0 |
| Classificação visual | ausente; controle não pontuado |
| Limpeza / workers remanescentes | confirmada / 0 |

Foram enviados os mesmos 13.355 bytes do pedido anterior, SHA-256
`868c2f5cbba5daccec0627d2242725ab0c1ee29c3c2300b777042a3b33fadd01`.
O PNG foi verificado por hash e decodificação base64 antes do envio. Prompt,
parâmetros e endpoint permaneceram iguais; os outros dois frames não foram enviados.
Não houve retry, probe, teste adicional, nova credencial, contratação ou alteração
de conta. O orçamento foi R$0 conforme acesso gratuito confirmado; cobrança e
consumo de tokens não foram informados/consultados.

A [evidência sanitizada](evidence/issue-4-nim-frame1-diagnostic-retest-20261022.json)
registra os cabeçalhos permitidos, hashes, parâmetros e medições. O
[HTTP 200 textual](issue-5-nim-textual-retest-20261022.md) e cinco artefatos selados
anteriores foram conferidos e permanecem iguais.

O erro é consistente com o `ResourceExhausted (16/16)` observado em 18/10 no mesmo
modelo. O corpo do primeiro 503 visual foi descartado, portanto não é possível
provar retrospectivamente sua identidade. O HTTP 200 textual recente mostra que
o acesso funciona para texto; a diferença temporal impede atribuir o problema
exclusivamente à modalidade de imagem. O recurso do backend que atingiu o limite,
sua duração e a política de alocação precisam de diagnóstico do provedor com o
request ID. Não há classificação que permita avaliar a percepção neste reteste.

A rodada está selada e não libera chamadas adicionais, auditoria, B/C ou holdout.

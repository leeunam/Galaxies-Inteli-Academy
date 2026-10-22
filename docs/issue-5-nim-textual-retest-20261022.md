# Reteste textual NVIDIA: HTTP 200

A única chamada autorizada respondeu **HTTP 200**. Usou exatamente o corpo textual
sintético histórico: 10.065 bytes, SHA-256
`b39fdab9b943145fcf638c990e6e19b82c40f8c9df30b006f7c5fc16040b5987`.
Nenhuma imagem foi enviada e não houve retry, redirect, fallback, nova credencial,
contratação ou alteração da conta.

| Medida | Resultado |
| --- | --- |
| Modelo solicitado/retornado | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` |
| Endpoint | `https://integrate.api.nvidia.com/v1/chat/completions` |
| Início UTC | `2026-10-22T16:17:36.113598+00:00` |
| Status / finish reason | 200 / `stop` |
| Tempo do worker / rodada com limpeza | 7.101 s / 7.264 s |
| Resposta | 965 bytes |
| Tokens informados pelo provedor | 4060 entrada + 150 saída = 4210 |
| Request ID | `6f16663f-8ecd-4a17-adeb-f50c56aef9b5` |
| Tentativas / saldo | 1 / 0 |
| Limpeza / workers remanescentes | confirmada / 0 |

O código executado foi `7341d5ccbf9553e0ea400fb9d1740ab5812b7034`, com o cliente
fixo existente e captura sanitizada. Os cabeçalhos permitidos e as medidas estão
na [evidência](evidence/issue-5-nim-textual-retest-20261022.json). Cinco artefatos
selados anteriores continuam byte a byte iguais. O orçamento foi R$0, apoiado
na confirmação do usuário de acesso gratuito; não foi consultada cobrança.

O teste confirma que o caminho textual e o acesso ao modelo funcionaram nessa
execução. Não identifica retrospectivamente a causa do 503 visual: tanto uma
falha transitória quanto uma falha específica do caminho multimodal continuam
possíveis. A mensagem de 131 bytes daquela falha permanece indisponível.

Este reteste é diagnóstico de transporte. Não executou StateGraph, autoridade
de seleção, auditoria visual, B/C, holdout ou avaliação qualitativa. Não promove
novos critérios do projeto. A proposta original permanece inativa e imutável;
a autorização específica foi vinculada e consumida uma vez em diretório privado
novo. Nenhuma chamada adicional está liberada.

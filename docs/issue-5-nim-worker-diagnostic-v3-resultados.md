# NIM v3: HTTP 200, seleção rejeitada por exceder 12 IDs

Em 21/10/2026, a [ligação completa revisada](issue-5-nim-worker-diagnostic-v3.md)
fez um único POST real, após nova autorização específica e revisão técnica.
O endpoint respondeu **HTTP 200**, mas a autoridade rejeitou a seleção:
`schema/schema_constraint`, com **21 IDs**, acima do limite de **12**.

O [contrato original](../scripts/explanation_evidence.py) fixa `max_length=12`
e o [schema enviado no payload](../orchestration/galaxies_orchestration/nim_graph_contract_v1.py)
fixa `maxItems=12`. Essa resposta viola comprovadamente a restrição de contagem.
Os tipos observados são corretos, os IDs pertencem ao catálogo, não há duplicatas
e o hash do pacote coincide. Isso não demonstra ausência de qualquer outra
violação de schema, nem explica por que o provedor ultrapassou o limite.
Não houve corte da lista, reparo, afrouxamento do validador ou repetição.

## Resultado observado

| Medida | Resultado |
| --- | --- |
| POSTs reais / seletor | **1 / 1** |
| Estado / outcome / processo | `consumed` / `observed` / saída 0 |
| HTTP / transporte | 200 / `selection_rejected` |
| Diagnóstico | fase `schema`, código `schema_constraint`, autoridade `rejected` |
| Cardinalidade | 21; máximo permitido 12 |
| Tipos | objeto, string de hash, array de strings |
| Duplicatas / catálogo / hash / paridade do classificador | false / true / true / true |
| Resposta / tokens de saída | **1.340 bytes / 262** |
| Tempo incluindo limpeza | **8,0903 s** |
| Seleção / renderização aceitas | false / false |
| Provedor | `real_provider_verified=false`, `live_not_validated` |
| Aderência qualitativa | não avaliada, sem explicação aceita |
| Limpeza / workers / stderr | confirmada / zero / zero bytes |
| Teto financeiro / custo medido | R$0 / indisponível (`null`) |

O grafo registrou `analyze → shap → comparables → context → select → render → proof`.
Os eventos demonstram passagem pelos nós, não aceitação de seleção/renderização.
O sidecar de erro HTTP ficou `null/not_applicable`, conforme o contrato para 200;
não houve consulta adicional de headers por esse observador. Corpo rejeitado,
valores arbitrários, headers e exceções não foram retidos ou projetados.

O resultado numérico inteiro, ranking e pacote de evidências permanecem iguais
à fixture inventada. Não foram enviados vídeos, resultados M1 ou dados privados.
Mantiveram-se modelo/endpoint, corpo de 8.576 bytes, até 2.048 tokens, 16 KiB,
45 s totais (43 úteis + 2 de limpeza), R$0 e ausência de retry/reparo/fallback.

## Proveniência e encerramento

Código executado: `1e5d57ae4625b55fc45b7edb07a5e0eaf5159160`. Plano
`4b42b168071ccb8c34334b920659fc69b217220a90ef8266a356c0905acf02d1`,
configuração `7db850b04e13102a73f8f3f2059b2c6c4a9fa21a7cfdbe12ee3e139aa19a6ea0`.
Os 33 pins e o corpo fixo conferem. A autorização e a revisão foram gravadas
externamente em recibos exclusivos e duráveis antes da única reserva do grafo.
O stdout agregado coincide com o recibo, SHA-256
`43d42555daf0a8f0e079c7318554fc320ae452dbe76e6c6b6f50de25498554e9`.

A autorização está consumida, sem saldo para outra chamada. Os testes offline
anteriores não foram repetidos. Não houve nova instalação, pesquisa, download,
mudança de fontes/limites ou abertura do teste reservado. M1, partições, mídias
e recibos anteriores preservados. O worker terminou com limpeza confirmada antes
do início da comparação visual autorizada separadamente.

A [evidência sanitizada](evidence/issue-5-nim-worker-diagnostic-v3-resultados.json)
registra a violação atual, sem aplicar sua causa às rejeições HTTP 200 históricas.
Os dois HTTP 503 anteriores continuam sem causa específica identificada.
Este ensaio não valida provedor no fluxo real, explicação livre ou aderência.

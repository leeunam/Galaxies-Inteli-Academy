# NIM global: uma chamada real, seleção de 12 IDs aceita

A [versão protegida com limite global](issue-5-nim-global-diagnostic-v1.md)
foi executada uma vez em 21/10/2026, após nova autorização específica e revisão
técnica vinculada ao checkout. O POST retornou **HTTP 200**, com **12 IDs**;
a autoridade original aceitou a seleção e a renderização. O proof atual registra
`current_provider.real_provider_verified=true` e `live_validated`.

Essa verificação vale para esta chamada e a fixture pública inteiramente
inventada. Não houve envio de vídeos, previsões ou evidências privadas. A demo
M1 com mídia real continua sem provedor configurado; não foi executada novamente.
Aderência qualitativa e geração livre não foram avaliadas por esta unidade.

## Resultado observado

| Campo | Resultado |
| --- | --- |
| POSTs reais / seletor | **1 / 1** |
| HTTP / transporte | **200 / `selection_accepted`** |
| Diagnóstico | fase `rendering`, código `accepted`, autoridade `accepted` |
| Cardinalidade / limite | **12 / máximo 12** |
| Tipos | objeto, hash string, array de strings |
| Duplicatas / catálogo / hash / paridade do classificador | false / true / true / true |
| Seleção / renderização aceitas | true / true |
| Resposta / tokens de saída | **972 bytes / 145** |
| Tempo incluindo limpeza | **6,7493 s** |
| Estado / outcome / processo | `consumed` / `observed` / saída 0 |
| Limpeza / workers / stderr | confirmada / zero / zero bytes |
| Teto financeiro / custo medido | R$0 / indisponível (`null`) |

Foram registrados `analyze → shap → comparables → context → select → render → proof`
no grafo/subgrafo compilados, com worker ROOT, nonce e dispatch duráveis. A prova
é live, não fake/replay. A análise numérica completa, ranking e pacote continuam
iguais à fixture inventada; `native_feature_handoff=false`. Os campos legados v2
não foram promovidos: `legacy_result.orchestration.real_provider_verified=false`
permanece literal; a comprovação desta chamada está em `current_provider`.

O sidecar de erro HTTP é `null/not_applicable` para 200. Não houve consulta
adicional de headers por esse observador. A autoridade manteve a restrição 1–12;
nenhuma lista foi cortada, reparada ou aceita por relaxamento. A chamada anterior
de 21 IDs continua rejeitada e seus valores descartados não foram recuperados.
Uma observação aceita não estabelece adesão do modelo em chamadas futuras nem
uma causa para as rejeições e erros 503 históricos.

## Identidade e encerramento

Código executado `48e5eb1b0d740deb96961b8e3b2087e9eae5ae64`. Plano
`6a3e52adee26579cf3c457d3cd6d843e7b70eb12ff238798ff9b7eca00ce66ab`,
configuração `f3a9dd627a1a9976edb486d463c5311f74066b50bf15b78fb9b22a32041ac8ed`.
Os 45 pins conferem. Corpo fixo de **10.065 bytes**, SHA-256
`b39fdab9b943145fcf638c990e6e19b82c40f8c9df30b006f7c5fc16040b5987`,
com os mesmos três criativos/24 fatos inventados e instrução global explícita.
Modelo, endpoint, temperatura e demais parâmetros permaneceram os aprovados;
45 s totais (43 úteis + 2 de limpeza), 2.048 tokens e resposta até 16 KiB.

A autorização e a revisão externas foram verificadas antes da reserva/nonce,
e o filho acessou a credencial existente somente após dispatch. Nenhuma chave
foi lida pelo operador, copiada para clone ou incluída nos registros. Reserva,
binding, dispatch e resultado são exclusivos, 0700/0600. O stdout agregado
coincide semanticamente com o recibo final, SHA-256
`f3f57cebb8bf8ad13752704a1207f66ab97c85bbef358146c9436256b14747f3`.

A autorização está consumida; saldo zero, sem retry/reparo/fallback/redirect/proxy.
Não houve nova instalação, coleta, treino, abertura do teste reservado ou testes
adicionais. M1, partições, PNGs, trio da demo e recibos consumidos preservados;
15 artefatos pertinentes conferem. O probe visual não foi relançado.

A [evidência sanitizada](evidence/issue-5-nim-global-diagnostic-v1-resultados.json)
registra a aceitação e seus limites. Esse resultado não encerra as pendências
VLM/B/C, avaliação final, aderência ou aceite integral do projeto.

# Diagnóstico NIM no grafo: chamada única com HTTP 503

Em 21/10/2026, a [release revisada](issue-5-nim-diagnostic-release-v1.md)
foi integrada e executada uma vez na principal, após autorização humana
específica e revisão técnica vinculada ao checkout. O único POST recebeu
**HTTP 503**. O recibo final é `observed`, com diagnóstico `http_error` na
fase `transport`; a autoridade de seleção ficou `not_invoked`.

`observed` indica conclusão com recibo, não aceitação do provedor. Seleção e
renderização não foram aceitas; `real_provider_verified=false` e
`verification_status=live_not_validated`. O resultado não explica a rejeição
HTTP 200 histórica nem a interrupção visual, cujas causas permanecem desconhecidas.

## Resultado e limites

| Medida | Observado |
| --- | --- |
| POSTs / HTTP | **1 / 503** |
| Tempo incluindo cleanup | **1,2829 s** |
| Processo / stderr | saída 0 / zero bytes |
| Diagnóstico | `transport` / `http_error` |
| Autoridade / aceitação raiz | `not_invoked` / false |
| Bytes de resposta / tokens | não registrados / não registrados |
| Tipos da seleção, hash, IDs e itens | `not_observed` |
| Cardinalidade, duplicação, catálogo, hash e paridade | não observados (`null`) |
| Cleanup / workers restantes | `confirmed` / zero |
| Teto financeiro / custo medido | R$0 / indisponível (`null`) |

Não há classificação semântica da resposta: o transporte encerrou antes
da autoridade. Corpo de erro, headers, exceções, valores desconhecidos e hashes
do conteúdo remoto não foram retidos ou projetados. Bytes/tokens ausentes não
equivalem a zero. Não foi investigada a causa específica do HTTP 503.

A reserva, binding, dispatch e resultado foram gravados no ledger exclusivo.
O stdout agregado coincide semanticamente com o recibo. A criação da reserva
consumiu a autorização; saldo operacional zero, **sem retry, reparo ou fallback**.
A configuração selada inicial com uma chamada não representa saldo após consumo.

O recibo registra `analyze → shap → comparables → context → select → render → proof`,
com uma invocação do seletor. Esses eventos confirmam o percurso do grafo;
não significam autoridade de seleção invocada ou renderização aceita.

Foram mantidos endpoint/modelo, corpo inventado de 8.576 bytes, até 2.048 tokens,
16 KiB e prazo total de 45 s, com até 43 s úteis e 2 s de cleanup. Somente três
criativos/24 fatos inventados foram enviados. Não houve envio de mídia,
previsões, SHAP ou evidências privadas, mudança de conta ou instalação.

## Integração e preservação

Código executado: `f6f0f3ca2eea7f333cf8c98b19cc9ed1fa463fe2`, tree
`7cae78973b722a7cd750cc563e999d8e93b9bf14`. Os commits de integração
`26b3587`, `c647c8a` e `f6f0f3c` adicionaram dez arquivos idênticos ao candidato,
sem alterar fontes anteriores. Conferem os 11 pins, plano/configuração e corpo;
o perfil inerte anterior permanece com `AUTHORIZATION_ID=None`.

Passaram somente os três checks delimitados de integração: um teste raiz em
0,336 s e dois isolados em 1,228 s. Os casos falsos de aceitação e hash divergente
concluíram com cleanup confirmado, sem HTTP real. Não se repetiu suíte ou teste
de runtime após o POST; a unidade final conferiu recibos e identidades.

O relatório numérico inteiro, incluindo ranking, e o pacote de evidências
permanecem iguais à fixture inventada. Conferem 49 arquivos protegidos,
incluindo os recibos NIM anteriores, fila visual selada/scratch, oito PNGs,
manifestos de partições, proteções do M1 e registros de retenção da demo.
Os namespaces reais continuam ausentes nos demais checkouts conferidos;
o registro novo existe somente na principal, com diretório 0700/arquivos 0600.

M1/A200 e teste reservado preservados, sem aquisição, geração visual, treino,
avaliação final, publicação ou fechamento de issue. Esta chamada não valida
provedor, geração livre, aderência qualitativa ou VLM/B/C.

A [evidência sanitizada](evidence/issue-5-nim-diagnostic-release-v1-resultados.json)
vincula revisão, plano, configuração e recibos, sem incluir conteúdo remoto.

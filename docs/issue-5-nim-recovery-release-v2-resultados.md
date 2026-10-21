# Recuperação NIM v2: autorização nova consumida com HTTP 503

A [liberação v2 separada](issue-5-nim-recovery-release-v2.md) fez exatamente
**um POST** em 21/10/2026, após a nova autorização específica e revisão técnica
vinculada ao checkout. O endpoint respondeu **HTTP 503**, com código `http_error`
na fase `transport`. A tentativa terminou em **1,3159 s**, incluindo limpeza
confirmada. Não houve retry, reparo, fallback ou outra chamada.

Esta é uma execução autorizada separadamente da [tentativa anterior com 503](issue-5-nim-diagnostic-release-v1-resultados.md).
O recibo anterior permanece intacto; sua autorização consumida não financiou
esta chamada. A nova autorização também foi consumida, com saldo operacional
zero. O valor inicial de uma chamada na configuração selada não representa
saldo disponível depois da reserva.

## Resultado

| Campo | Observado |
| --- | --- |
| Estado / outcome / processo | `consumed` / `observed` / saída 0 |
| POSTs reais / seletor | 1 / uma invocação |
| HTTP / diagnóstico | 503 / `transport/http_error` |
| Autoridade | `not_invoked` |
| Seleção / renderização aceitas | false / false |
| Provedor | `real_provider_verified=false`, `live_not_validated` |
| Aderência qualitativa | não avaliada |
| Tipos de seleção/hash/IDs/itens | `not_observed` |
| Cardinalidade, duplicação, catálogo, hash, paridade | não observados (`null`) |
| Bytes de resposta / tokens | não registrados (`null`) |
| Cleanup / workers / stderr | `confirmed` / zero / zero bytes |
| Teto / custo medido | R$0 / indisponível (`null`) |

`observed` significa conclusão com recibo; não significa seleção aceita. Os
eventos do grafo foram `analyze → shap → comparables → context → select → render → proof`.
Alcançar esses nós não demonstra que a autoridade ou uma explicação foram aceitas.
O erro de transporte precedeu a autoridade; não houve seleção para avaliar
semanticamente, nem explicação aceita ou avaliação de aderência aos fatos.

Não foram retidos/projetados corpo de erro, headers, exceções, strings desconhecidas
ou hashes do conteúdo remoto rejeitado. A causa específica do 503 não foi
investigada. Não se atribui quota, indisponibilidade global, schema ou relação
causal com a rejeição HTTP 200 histórica ou com os timeouts visuais.

## Identidade e preservação

Código executado `f49e221568fc1277989e35cd966945d4b7c90f64`. Plano
`71fd073d9fa9f75e8fdb14c2eb17c474d08c5512fe0f1ab46e69a53945021e58`,
configuração `77d2dd428f7ccffa268d48271a8b48f1b41ca62de8ed3536a04140bbb3234d9b`.
Os sete arquivos integrados são idênticos ao candidato, com 12 pins conferidos
e sem alteração de predecessores. Os nove testes focados do candidato passaram
em 1,45 s; não houve repetição de testes ou suites durante integração/envio.

Permaneceram fixos modelo, endpoint e corpo de 8.576 bytes com três criativos/24
fatos inteiramente inventados, sem dados privados ou vídeos. Limites de 2.048
tokens, 16 KiB e 45 s totais, incluindo até 43 s úteis e 2 s para cleanup.
Não houve mudança de conta, credencial, ambiente ou custo autorizado.

Reserva, binding, dispatch e resultado foram publicados no ledger novo e
exclusivo, com diretório 0700/arquivos 0600. A revisão técnica foi conferida antes
da reserva. O stdout agregado coincide semanticamente com o recibo final.
Recibo SHA-256: `bb00f450582c755a68a97c97645d50f4832ac9c7d6f452bdaa079d4e584531ce`.

O relatório numérico completo, incluindo ranking, e o pacote de evidências
continuam iguais à fixture pública inventada; isso não é prova de qualidade em
dados reais. Os 75 arquivos protegidos conferem, incluindo NIM anterior, VLM
v1/v2 selados, journals privados, PNGs, manifestos, proteções de M1 e registros
de retenção da demo. Novos namespaces permanecem ausentes nos demais checkouts.
Não houve nova aquisição, inferência visual, treino, abertura semântica do teste,
publicação ou fechamento de issue. M1/A200 e partições preservados.

A [evidência sanitizada](evidence/issue-5-nim-recovery-release-v2-resultados.json)
registra diagnóstico, flags, eventos e vínculos. O provedor no fluxo real,
explicação livre, aderência qualitativa e as pendências VLM/B/C continuam sem
validação por este ensaio sintético.

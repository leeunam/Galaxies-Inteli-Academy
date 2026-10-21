# Proposta inerte de recuperação NIM

A autorização `Sentinel_c3cbbc19ae7c81919fc1361a0256d307` foi consumida por um POST
com HTTP 503, diagnóstico `transport/http_error`, autoridade `not_invoked` e
`real_provider_verified=false`. O cleanup foi confirmado, em 1,2828895339916926 s.
Bytes/tokens não foram observados; não equivalem a zero. O recibo tem SHA256
`ce2deeae290804a4d6f2464a0f68afcff515d5026f85e37c184496bdd9d253e5`.
O resultado e o perfil executado permanecem imutáveis.

Não foi determinada a causa específica do 503. Não há base para atribuir quota,
capacidade global, conta ou incidente do endpoint. Isso também não explica a
rejeição HTTP 200 histórica. A consulta pública oficial do coordenador não encontrou
status útil do endpoint específico; não se repetiu consulta nem inferência.

## Próximo teste e ganho informacional

A menor proposta é um único POST novo, diretamente no grafo, com o corpo existente.
Não haverá ping de inferência antes dele. Manter modelo, endpoint e corpo fixa as
variáveis: a observação nova discrimina ausência de resposta utilizável no transporte
versus uma resposta que chega ao envelope/validador. Não identifica a causa do 503
nem garante disponibilidade. Um novo 503 encerra a tentativa sem retry.

| Dimensão | Observação futura | Limite da conclusão |
| --- | --- | --- |
| Execução/transporte | HTTP, fase/código estáticos, prazo e cleanup | 503 significa falha antes da seleção; não mede qualidade do modelo. |
| Validade de seleção | Envelope aceito, autoridade original, 1–12 IDs únicos do catálogo, hash exato e render válido | Só aceita se os gates existentes passarem; nenhuma coerção ou reparo. |
| Aderência às evidências | Após aceitação, conferir os fatos públicos selecionados e a reprodução literal pelo render; descrever cobertura por criativo/tipo | IDs válidos sustentam seleção fechada. Cobertura não vira gate novo; não demonstra relevância ótima, explicação livre, qualidade preditiva ou aderência em dados reais. |

Uma única resposta válida permite observar as três dimensões no mesmo percurso:
transporte e envelope completos, validação original e avaliação descritiva da seleção
pública aceita. Análise numérica e ranking devem continuar idênticos à fixture.
Uma resposta 200 rejeitada é falha de envelope/seleção conforme diagnóstico, sem
interpretar seu conteúdo. Dados de aderência permanecem não avaliados quando não
há seleção aceita. Nenhum resultado deste teste promove modelos ou abre teste reservado.

O diagnóstico existente já discrimina fase/código, tipos, cardinalidade, duplicação,
catálogo e igualdade do hash. Não se propõe coleta adicional: corpo de erro, headers,
strings/valores desconhecidos, exceções e hashes de conteúdo rejeitado continuam
suprimidos. Não se tentará diagnosticar o 503 retendo seu corpo.

## Pacote revisável sem capacidade remota

A entrada `nim_recovery_proposal_v1` é um envelope de proposta, não uma segunda
implementação do transporte. `AUTHORIZATION_ID=None`, saldo zero e liberação false
bloqueiam antes de ler plano/revisão, reservar, gerar nonce, iniciar worker ou tocar
chave/socket. Mesmo trocar a constante e selar outro plano não implementa despacho:
a entrada encerra com `recovery_additive_release_required`. Uma futura liberação
aditiva, vinculada à nova autorização e revisão técnica no checkout final, ainda
precisa ser preparada/revisada. Nenhum consentimento é inferido de pedidos para
acelerar os assistentes ou usar mais processamento.

O plano referencia por hash o dono 43+2 já corrigido, grafo/subgrafo, transporte fixo,
codec PID/nonce, autoridade e diagnóstico. Não copia os três módulos de execução,
não muda o perfil consumido e não usa globals/PID falsos. Os namespaces futuros
propostos são `data/private/issue-5-nim-graph-recovery-proposal-v1` e seu irmão
`issue-5-nim-graph-recovery-proposal-v1-review`; nenhum foi criado. Simulações só
aceitam caminhos inventados fora de qualquer componente `issue-5-nim-*`, sem symlinks.

Os máximos propostos são um POST total, 45 s totais (até 43 s úteis +2 s de cleanup),
2048 tokens, 16 KiB, R$0; mesmos três criativos e 24 fatos inventados. Corpo de
8576 bytes, SHA256 `fd87bed20413c52bb7873d92da48c37d5f5f391a3fa9997e77177d073aaafcba`,
modelo `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`, endpoint
`https://integrate.api.nvidia.com/v1/chat/completions`. Sem retry, reparo, fallback,
redirect, proxy, mídia privada, alteração de conta ou novos termos de acesso.
A reserva futura consumirá a autorização inclusive em falha/resultado incerto.

A inspeção offline, parametrizada pelo operador, é:

```sh
rtk proxy env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="${SOURCE}/orchestration" "${GRAPH_PYTHON}" -B -m galaxies_orchestration.nim_recovery_proposal_v1 --inspect-plan
```

`--execute-reviewed-once` nessa mesma entrada retorna somente bloqueio estático;
não é um comando de execução futura do POST. Nenhum ledger/review/nonce real foi
criado e nenhum teste de inferência foi feito nesta unidade.

## Nova autorização específica proposta

“A chamada anterior já foi consumida e recebeu HTTP 503 antes da seleção. Você
autoriza uma nova e única chamada de teste à API da NVIDIA dentro do grafo do projeto,
com os mesmos três exemplos e 24 fatos inventados, mesmo modelo, endpoint e corpo
fixo de 8576 bytes (SHA256 fd87bed20413c52bb7873d92da48c37d5f5f391a3fa9997e77177d073aaafcba),
até 45 segundos totais, 2048 tokens, resposta até 16 KiB e custo máximo R$0?
Não envia seus vídeos nem muda sua conta. Se houver outro 503 ou qualquer falha,
a tentativa para, sem retry, reparo, fallback, redirect ou proxy.”

A pergunta acima é proposta de texto; não foi enviada ao usuário por ferramenta,
não contém nova autorização e não permite reutilizar c3 ou o ledger anterior.

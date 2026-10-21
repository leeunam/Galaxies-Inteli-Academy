# NIM release v1: HTTP 200, seleção rejeitada por tipo no schema

A única tentativa sintética autorizada concluiu em **2,63 s**, com **HTTP 200,
762 bytes de corpo e 91 tokens de conclusão**. A autoridade rejeitou a seleção:
`selection_validated=false`, fase `schema`, código `schema_invalid_type`.
A tentativa está consumida, sem repetição, reparo ou fallback.

Execução em 20/10/2026, no checkout integrado `fd4f03d`, após revisão técnica
concreta vinculada ao [plano aditivo](issue-5-nim-release-v1.md). O
[recibo público sanitizado](evidence/issue-5-nim-release-v1-resultados-20261020.json)
preserva resultado, limites e auditoria. O caminho remoto e sua observabilidade
foram exercitados; nenhuma explicação ou seleção foi aceita nesta tentativa.
Isso não conclui a #5 ou o projeto, nem avalia aderência em campanhas reais.

## Resultado e diagnóstico disponível

| Campo | Resultado observado |
|---|---|
| Estado / outcome | `consumed` / `observed` |
| Resposta HTTP | 200 |
| Corpo HTTP recebido | 762 bytes |
| Tokens de conclusão informados | 91 |
| Tempo total do executor | 2,6318129209976178 s |
| Fase / código | `schema` / `schema_invalid_type` |
| Autoridade / seleção | `rejected` / `false` |
| Projeção segura da resposta | `null` |
| Custo medido | indisponível (`null`) |

O observador chegou à validação do schema e classificou uma falha de tipo.
Em `selection_observation_v2._schema_code`, esse código corresponde a erros
Pydantic de tipo string, tupla, modelo ou dicionário. O registro não retém
localização, mensagem, input ou valor da exceção; **não identifica qual campo
ou objeto tinha o tipo incorreto**. Não inferir um campo específico ou uma
correção do payload a partir desse código agregado.

A projeção segura ficou vazia porque o conteúdo não passou pelo schema. Corpo
bruto, texto da resposta, cabeçalhos arbitrários, detalhes de exceção e seus
hashes foram suprimidos pelo contrato. Não foram recuperados, publicados ou
usados para relaxar a aceitação. O diagnóstico é desta tentativa; não atribui
retroativamente a mesma causa ao [NIM sintético anterior](issue-5-nim-sintetico-unico-resultados.md).

Há um despacho durável e uma resposta HTTP observada. O campo autoritativo
`real_requests` permanece `null`, conforme o codec; não foi reescrito como
contador medido. O código fixo faz um POST e não possui retry, redirect, proxy,
fallback ou reparo. Nenhum envio adicional ocorreu na auditoria.

## Autorização, limite financeiro e consumo

O plano fixou endpoint/modelo e os mesmos bytes públicos inventados da fixture:
até uma tentativa, 45 s totais, 2.048 tokens, 16 KiB de corpo e R$0.
A condição financeira se baseou na declaração específica do aluno sobre o plano
gratuito da API do projeto e nas fontes oficiais já verificadas. **R$0 é o teto
autorizado; o custo observado não foi medido.** O recibo conserva
`max_spend_brl=0` e `measured_cost_brl=null`.

A origem literal da liberação e seu ID real foram preservados em namespace
privado novo, sem truncamento. O recibo técnico foi criado exclusivamente,
com fsync, com os oito campos exatos do contrato e o hash do checkout real.
Plano, revisão e contrato do binding foram conferidos antes da reserva, com
o ledger real ainda ausente. A pré-conferência do binding ocorreu em recibo
diagnóstico separado, sem reserva; o filho revalidou o binding real depois.

Executou-se uma única vez a CLI revisada. Reserva, binding e despacho duráveis
precederam o getter da credencial e o HTTP no filho autorizado. O valor da chave
e o `.env` não foram copiados, mostrados ou auditados; nenhum README foi lido.
O ledger fixo contém exatamente os quatro recibos esperados: reserva, binding,
despacho e resultado. Sua existência encerra esta tentativa, inclusive diante
da rejeição. Não houve teste de reentrada no executor ou nova autorização.

## Auditoria e preservações

A auditoria em leitura verificou plano, 6 pins novos e 130 pins da v3,
revisão, binding, campos do ledger e contrato IPC sanitizado. Não iniciou
processo, transporte ou credencial na fase de validação do ledger. O caminho
`observed` do executor imutável exige `process.wait()` e recolhimento do filho;
a conferência posterior do host encontrou zero workers NIM/VLM correspondentes
e zero metadados Python inacessíveis. Nenhum temporário VLM desta rodada anterior
permaneceu. Não houve nova chamada durante essa conferência.

Os **10.108 arquivos protegidos** conferem, incluindo fontes e recibos da
integração e das filas anteriores. Ledgers/recibos antigos, dois diagnósticos
VLM selados, oito PNGs e hashes dos 32 crops, tempos, M1/A200 e modelos ficaram
iguais. Os seis arquivos de pesos/runtime monitorados e os ambientes com
**130/42 distribuições** também conferem. Partições 203/66/31 e teste reservado
preservados, sem leitura semântica do teste.

A v3 continua `remote_execution_released=false`, selo remoto `None` e ledger
próprio ausente. A release nova não reabriu v1 ou v3, não liberou atributos VLM,
treino B/C, troca de M1 ou envio de dados privados. A autorização desta unidade
terminou; nenhuma próxima tentativa está automaticamente liberada.

Nenhuma fonte de execução foi alterada nesta conclusão. Permanecem os 131
checks do candidato no clone e os três checks leves da integração principal,
sem repetir suíte por documentação. O resultado real e sua auditoria são as
verificações desta unidade.

Identidades: plano `d759db319dd09bc6f2037c430d053e0563dfb07c47eacc186172c3caab50bf1b`,
configuração `042d4f6ae88900e3f20cac6a5d10c9cbb10e98f70eed6251f9d071499c9f259d`,
fixture `0fb7b9797cd41f53c3f127b0d2f6f934d0696aa3ba288852f5cff616455cf438`,
payload `40f4e22ef0f305e6d317da9e7fe065afebb393a9103e94b179495b9794855deb`.
Recibo técnico: `0802ac2d918d7491bcb2c1789a0281199b8858ff2853cb6eeb8d14cdef9f424e`.
Digest canônico da auditoria privada:
`53a3cbfcab98055fe4aca94fc54888819a732f8a2903cba491210eefbc05940d`.

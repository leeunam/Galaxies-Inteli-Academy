# NIM no grafo — auditoria offline de `selection_rejected`

Auditoria local de 21/10/2026, baseada no HEAD principal
`836af340879678fc1c556b8f4f8de3dd1c1e4f72`, importado somente por fetch local
para uma branch nova no clone. As branches anteriores foram preservadas.
Não foi demonstrado bug de contrato/parser que justifique mudar a autoridade.
Os recibos existentes não identificam a seleção nem o campo concreto que falhou.

## Evidência histórica que restou

A [evidência pública](evidence/issue-5-nim-no-grafo-live-v1-resultados.json) e os
quatro arquivos autorizados do ledger real conferem por SHA-256. A captura
sanitizada `permitted-stdout.json` é igual ao recibo final. A leitura foi
limitada a esses recibos e às fontes/fixtures públicas; nenhum dado privado foi
copiado para o clone.

O resultado permanece: um POST, HTTP 200, 1.338 bytes, 262 tokens,
8,007279974 s incluindo recolhimento, `selection_rejected`, seleção/renderização
não aceitas e `real_provider_verified=false`. O pacote retido corresponde à
fixture pública de três criativos. Não há seleção, projeção segura, diagnóstico
de tipos, `selection_observation` ou código fino da validação no recibo.
Há zero afirmações e o aviso legado é `transport_failed`.

`selection_rejected` é emitido no bloco que chama `validate_selection` e
canonicaliza a seleção, depois de receber conteúdo textual do envelope válido.
Esse bloco captura a exceção sem registrar sua classe/detalhe ou o código
específico. O corpo original e seu hash também não foram retidos. Não há fonte
adicional da seleção para reanalisar nesta auditoria.

O aviso legado não demonstra erro HTTP: rejeição raiz → seleção `None` →
`RootSelector` recusa a seleção ausente → callback do grafo retorna
`reason=transport_failed`. O campo novo conserva `selection_rejected`, distinguindo
essa trajetória do erro de rede. A explicação incompleta foi produzida
normalmente; não foi demonstrado defeito de renderização. Nenhuma flag ou aviso
do contrato v2 foi alterado.

## Comparações discriminantes inventadas

Os testes chamam a autoridade e a ponte existentes, sem cópia de sua regra de
aceitação. Todos os dados são inventados. Guards explícitos bloqueiam sockets,
DNS, requisição HTTPS, getter de credencial e loaders reais de SHAP/índice.

| Caso | Resultado confirmado offline |
| --- | --- |
| Cada um dos 24 IDs, individualmente, com hash correto | Todos aceitos |
| Um ID opcional, sem os seis mandatórios na lista remota | Aceito; os seis são apensados |
| Doze IDs válidos sem os seis mandatórios | Aceito; renderização contém 18 fatos |
| Treze IDs ou os 24 IDs | `schema_constraint`; rejeitados |
| Zero IDs | `schema_constraint`; rejeitado |
| ID repetido | `duplicate_evidence_id`; rejeitado |
| Hash divergente, incluindo o hash da fixture de um criativo | `packet_hash_mismatch`; rejeitado |
| ID desconhecido | `unknown_evidence_id`; rejeitado |
| Campo obrigatório ausente / campo extra | `schema_missing_field` / `schema_extra_field` |
| IDs escalar, objeto como item, hash como objeto, raiz duplamente codificada | `schema_invalid_type` |
| JSON com fences / chave duplicada / profundidade excessiva | `json_syntax` / `json_duplicate_key` / `json_depth_limit` |

O schema anunciado tem `maxItems=12`, assim como `EvidenceSelection`.
O enum de 24 IDs define o catálogo permitido, não uma exigência de selecionar
todos. O limite de 12 pertence à seleção remota; não limita a união posterior
com os mandatórios. Não há mismatch demonstrado de 12 versus 24.

No StateGraph/subgrafo realmente compilados e no worker raiz por IPC, a seleção
falsa existente de nove IDs omite os três `limit_*` e é aceita: a autoridade
acrescenta os limites, produzindo 12 afirmações com análise/ranking intactos.
O caso falso de hash incorreto também percorre o grafo e reproduz exatamente
`selection_rejected` com HTTP 200, seguido do aviso legado `transport_failed`.
Ambos continuam com origem falsa, zero HTTP real, verificação real falsa e
handoff nativo falso.

O pedido standalone de um criativo e o pedido do grafo usam objeto com hash
string, array de strings e limite 1–12. Seus catálogos têm cinco e 24 IDs e seus
hashes de pacote são diferentes. A seleção pública de cinco IDs é aceita pela
ponte standalone; o mesmo conteúdo com o hash antigo é rejeitado no contexto
de três, enquanto esses cinco IDs com o hash novo são aceitos. Isso compara
contratos, sem afirmar que o modelo retornou o hash antigo na chamada real.

## Por que bytes e tokens não recuperam a causa

Dois envelopes inteiramente inventados foram ajustados para exatamente
1.338 bytes e receberam metadado inventado de 262 tokens: um contém 13 IDs e
outro contém um hash divergente. O padding exterior é inventado e permitido
pelo leitor de envelope; não foi inferido do corpo real, e os tokens não foram
medidos por tokenizer/modelo. O classificador existente distingue
`schema_constraint` de `packet_hash_mismatch`, mas a ponte conserva, nos dois
casos, resultados e metadados idênticos: HTTP 200, `selection_rejected`, seleção
ausente, zero afirmações e `transport_failed`.

Portanto, mesmo os números exatos de bytes/tokens não determinam a falha.
Os exemplos são discriminantes locais, não replay nem reconstrução da resposta
suprimida. A aceitação standalone anterior também não constitui contrafactual
pareado para explicar esta rejeição com três criativos.

## Conclusão e verificação

Faltam o `message.content` original e/ou um diagnóstico estático produzido
naquela execução: sintaxe JSON, posição/tipo dos dois campos conhecidos,
cardinalidade, duplicação, pertencimento ao catálogo ou igualdade do hash.
O recibo não permite escolher entre essas falhas. Não foi retido sequer o
código fino que o classificador existente produz nas reproduções inventadas.
O observador antigo projeta somente a fixture de um criativo, e sua ausência
de projeção para o contexto de três é uma guarda conhecida, não prova de bug.

Passaram **44 testes raiz em 0,77 s** e **dois testes isolados em 0,96 s**,
somente os novos testes desta auditoria. São verificações de contrato e de
instrumentação, não validação de provedor. Nenhuma mudança de runtime,
observabilidade, payload, plano ou liberação remota foi implementada.

Os testes foram executados na raiz do clone com o Python raiz existente e, em
`orchestration/`, com o Python isolado existente e `GALAXIES_ROOT_PYTHON` explícito,
respectivamente nos arquivos `test_nim_graph_rejection_audit_v1.py` e
`test_nim_graph_mandatory_audit_v1.py`. Não houve instalação, ML, modelo carregado,
leitura de holdout, mídia, credencial ou HTTP real. As duas simulações do grafo
usaram somente diretórios temporários novos; o ledger real consumido não mudou.

Nenhuma ação do aluno foi necessária para os checks locais. O dado faltante
foi suprimido na execução já encerrada e não é recuperável dos recibos atuais.
Esta auditoria não pede nova chamada, chave ou autorização e não transforma
fakes/replays em aceitação real. A causa concreta permanece desconhecida, com
as falhas distintas compatíveis explicitadas acima.

# NIM — auditoria offline de `schema_invalid_type`

Adendo de 20/10/2026 (São Paulo), somente documental, após a tentativa sintética
consumida. O resumo fechado registra HTTP 200, 762 bytes, 91 tokens,
`authority_status=rejected`, `selection_validated=false` e nenhuma projeção.
O corpo foi suprimido; não foi recuperado, reconstruído ou inventado.

**Não foi confirmado defeito de parser/coerção que justifique um patch.**
O fluxo é bytes HTTP → texto UTF-8 → envelope JSON → `message.content` textual
→ JSON interno → `EvidenceSelection` → autoridade. Esta usa
`model_validate_json(json.dumps(body))`, assim como o observador. Um array JSON
válido é aceito e representado internamente como tupla, mesmo com contrato estrito.
A rejeição de uma lista Python por `model_validate` ocorre fora desse caminho.

Treze checagens mínimas com dados inteiramente inventados, sem rede/credencial:

| Caso | Resultado observado |
| --- | --- |
| 1. Objeto JSON correto, dois IDs em array, autoridade e ponte HTTP | Aceito em ambos |
| 2. `evidence_ids` como string escalar | `schema_invalid_type` (`tuple_type`) |
| 3. `evidence_ids` como objeto | `schema_invalid_type` (`tuple_type`) |
| 4. Objeto dentro do array de IDs | `schema_invalid_type` (`string_type`, `too_short`) |
| 5. Número dentro do array de IDs | `schema_invalid_type` (`string_type`, `too_short`) |
| 6. `packet_sha256` como objeto | `schema_invalid_type` (`string_type`) |
| 7. Raiz interna duplamente codificada como string JSON | `schema_invalid_type` (`model_type`) |
| 8. Lista Python via `model_validate` | Rejeitada com `tuple_type`; API não usada nessa resposta |
| 9. Tupla Python via `model_validate` | Aceita |
| 10. Array JSON via `model_validate_json` | Aceito; representação interna `tuple` |
| 11. `message.content` como objeto | `envelope_schema_invalid`; autoridade não invocada |
| 12. `message.content` como lista de partes | `envelope_schema_invalid`; autoridade não invocada |
| 13. `message.content` textual contendo objeto JSON correto | Aceito pela ponte e autoridade |

Nos casos internos 2–7, a autoridade rejeitou e o observador/ponte conservaram o
mesmo diagnóstico. O código agregado abrange vários tipos e posições; não permite
atribuir um campo ou formato exato à resposta remota. Os casos inventados não são
replay do corpo ausente, nem evidência de que o fornecedor produziu qualquer um deles.

O [payload fixo](../scripts/nim_dispatch_plan_v3.py) envia instruções textuais,
mas não `response_format` ou JSON Schema completo. O transporte genérico separado
inclui schema no pedido; a chamada fixa não passa por ele. Isso é **hipótese de
orientação futura**, não causa confirmada desta rejeição e não um patch validado.
Não se alterou prompt, payload, parser, autoridade, plano, fixture ou liberação.

**Bloqueio técnico atual:** sem o corpo, não se identifica o erro de tipo concreto;
com a autorização NIM consumida, não há tentativa disponível para validar mudança
de orientação ou comportamento do fornecedor agora. A resposta permanece rejeitada.
Não se enfraquece schema, repara resultado ou cria novo ensaio/liberação por este
adendo. Esta auditoria útil está encerrada sem intervenção humana genérica pendente.

Foram feitas somente as 13 checagens discriminantes acima, não a suíte de 131.
Comandos e resultados foram preservados depois da execução, sem repeti-los, no
namespace privado novo `data/private/issue-5-nim-schema-type-audit-v1/` do clone.
Fontes e planos selados ficaram byte a byte intactos; nenhum corpo/cabeçalho,
credencial ou conteúdo privado foi acrescentado ao documento público.

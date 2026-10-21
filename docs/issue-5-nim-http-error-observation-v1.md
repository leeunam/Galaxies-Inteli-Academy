# Observação offline mínima de erros HTTP NIM

A lacuna confirmada é estreita: o observador selado encerra status diferente de 200
antes de ler o corpo; o adapter também dispensa o framing nesse caminho. Assim,
os dois 503 não preservaram request-ID ou metadados dos campos de framing. Não
há corpo histórico para recuperar nem causa específica demonstrada do 503 ou da
seleção rejeitada em 200. A alteração é aditiva e offline: nenhuma fonte selada,
transporte, payload, canonicalização, catálogo, autoridade ou ranking foi alterado.

## Formato permitido, sem corpo

`nim-http-error-metadata-v1` tem exatamente seis campos:

| Campo | Valores permitidos |
| --- | --- |
| schema_version | constante nim-http-error-metadata-v1 |
| http_status | inteiro 100–599, diferente de 200, já observado pelo adapter original |
| request_id | null ou UUID canônico ASCII hexadecimal, normalizado para minúsculas |
| request_id_state | captured, missing, invalid, duplicate, unavailable |
| framing_state | supported, unsupported, missing, invalid, duplicate, unavailable |
| body_read | sempre false |

Nenhuma captura de corpo é necessária para esse ganho informacional. Não se lê
mensagem, detail, título, JSON de erro ou string livre. Headers desconhecidos,
Authorization, cookies/Set-Cookie, seus valores e hashes não são consultados nem
retidos. Consultam-se apenas `headers.get_all()` de nvcf-reqid e dos quatro campos
content-type/content-length/content-encoding/transfer-encoding. Duplicatas não são
coalescidas nem se escolhe um valor. Cada valor tem limite de 128 caracteres; o
request-ID exige exatamente 36 caracteres no formato UUID. Um valor diferente fica
invalid/null, não um hash ou trecho do conteúdo. Nenhum diagnóstico de quota,
capacidade, cobrança ou causa do provedor é inferido desses metadados.

O framing é somente classificação dos quatro campos permitidos, nunca substitui
`protocol_ok` ou prova validação de todos os headers. Supported requer JSON,
identity, comprimento declarado até 16 KiB e transferência compatível, sem conflito
de content-length/transfer-encoding. Corpo/tokens ausentes continuam null, não zero.
Mesmo framing rejeitado não altera `transport/http_error` nem invoca a autoridade.

A documentação oficial [NVCF Generic HTTP Function Invocation](https://docs.nvidia.com/nvcf/overview/generic-http-function-invocation)
descreve nvcf-reqid em Statuses and Errors. Trata NVCF self-managed; não demonstra
que integrate.api devolveu esse header nas chamadas antigas. A referência de
[invocação gRPC](https://docs.nvidia.com/nvcf/1.0.2/overview/g-rpc-function-invocation)
descreve UUID, sem garantir o formato do nosso endpoint REST. Por isso o campo é
opcional e outro formato é suprimido. Não se exige sua presença para aceitar seleção.

## Adapter e limites da correção

O adapter novo recebe uma resposta já aberta e chama o adapter original exatamente
uma vez. Só acrescenta `http_error_metadata` para status não 200 já observado.
Para 200 ou status inválido, esse campo é null e o resultado original é preservado,
inclusive aceitação/rejeição, números, catálogo e diagnóstico. Não há reparo ou
coerção de seleção. O módulo não abre conexão, lê chave, reserva ou cria worker.
Sua entrada remota é incondicionalmente bloqueada; não há novo perfil live liberado.

O ganho futuro é correlação por ID opcional e classificação estática de framing,
sem aceitar conteúdo arbitrário. Isso não recupera causas antigas nem garante que
um novo 503 traga request-ID. Payload idêntico nas três chamadas do grafo não
explica suas respostas distintas; o controle tipado aceito usou corpo diferente e
não é controle idêntico do grafo. Nada justifica mudar o JSON/catálogo para corrigir
a rejeição histórica sem a resposta rejeitada.

Uma captura real futura exigiria nova autorização específica (as anteriores foram
consumidas), liberação/revisão técnica separada e integração explícita do adapter,
com o corpo fixo, orçamento e consumo único já definidos. Nenhuma chamada real foi
feita nesta unidade e nenhuma nova é proposta como condição para testar este código:
os testes usam respostas falsas, incluindo headers maliciosos, limites, duplicatas,
status inválido e preservação da autoridade original. Não se repetem suítes antigas.

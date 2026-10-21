# NIM tipado: seleção sintética aceita

Em 21/10/2026, a única tentativa adicional autorizada do
[pedido textual tipado](issue-5-nim-typed-request-v1.md) retornou **HTTP 200**
com `selection_validated=true`. A autoridade original aceitou a seleção;
não houve coerção de tipos, reparo, fallback ou retry. A
[evidência agregada](evidence/issue-5-nim-typed-request-v1-resultados.json)
vincula plano, configuração, revisão, recibo e diagnóstico seguro.

| Medida | Resultado |
|---|---|
| Integração na principal | `90c45dc0d6332e8b5b140e16627ae6fe5cd43607` |
| Candidato revisado | `3069217a9a631f11cb09f566e64ba518cb9566c7` |
| Execuções / limite de POST | 1 / 1 |
| Tempo total do recibo | 3,9023 s; teto 45 s |
| HTTP / código / fase | 200 / `accepted` / `rendering` |
| Corpo recebido / tokens de saída | 878 bytes / 110 |
| Autoridade / seleção | `accepted` / validada |
| Custo medido | indisponível (`null`); teto autorizado R$0 |
| Worker remanescente | zero |

O campo `real_requests` do recibo continua `null`; ele não é uma contagem
externa independente. O transporte fixo faz um único POST, sem laço de
repetição, e esta execução teve dispatch durável seguido de resposta HTTP.
A autorização está consumida; o CLI não deve ser executado novamente.

## Contrato e tipos observados

Foram enviados somente a fixture pública inventada fixa e seu contrato
textual explícito, ao mesmo endpoint/modelo. Não houve vídeo, metadado
privado, previsão real ou evidência de treino/teste na requisição.
A credencial existente foi lida exclusivamente pelo filho autorizado após
o marcador de dispatch e usada no header HTTPS. O operador não leu `.env`
nem chave, e nenhum segredo foi copiado para o clone, relatório ou chat.

| Posição pública fixa | Tipo observado |
|---|---|
| envelope | objeto |
| choices | array |
| choices[0] | objeto |
| message | objeto |
| message.content | string |
| seleção interna | objeto |
| packet_sha256 | string |
| evidence_ids | array |
| evidence_ids[*] | string |

A projeção pública validada contém cinco IDs da fixture:
`limit_target`, `limit_quality`, `limit_interpretation`, `c1_prediction` e
`c1_interval`, vinculados ao hash sintético esperado. Isso comprova aceitação
contratual dessa seleção fechada. Não foi gerada ou avaliada uma explicação
livre, nem aderência qualitativa para um usuário/vídeo real.

O diagnóstico de tipos foi calculado **depois** da autoridade. O pai validou
o sidecar e exigiu igualdade entre seu resumo e o resumo do IPC antes de
incorporá-lo ao recibo final. Valores arbitrários, nomes desconhecidos,
corpo bruto, cabeçalhos, exceções e seus hashes não foram retidos.

## Consumo e preservação

A revisão específica vinculou o ID real da decisão, autorização humana,
hashes e caminho absoluto desta principal. O novo namespace foi reservado
duravelmente antes do filho; o marcador de dispatch precedeu a leitura da
credencial. Os cinco arquivos do ledger novo estão em modo 0600; o diretório
e o recibo de revisão continuam privados. Nenhuma autorização antiga foi
reaberta e nenhuma nova tentativa está habilitada.

Os sete arquivos importados foram comparados byte a byte ao clone revisado.
Passaram **32 testes novos de integração em 7,93 s**, Ruff e formatação,
sem repetir os 140 testes já registrados no candidato. Plano e predecessor
conferem antes e depois. Após a chamada, sidecar/resumo, 26 arquivos
protegidos, oito PNGs e recibos VLM conferem; os dois arquivos de partições
conferem por hash, sem leitura semântica. M1 e teste reservado preservados.
Zero workers NIM/modelo ao concluir. Nenhuma aquisição, treino ou promoção.

## Alcance da conclusão

O pedido com tipos explícitos foi aceito nesta tentativa. Isso **não prova
a causa da rejeição histórica**: a resposta anterior não está disponível e
não há contrafactual pareado. Os recibos anteriores continuam consumidos
e rejeitados como registrados, sem alteração de aceitação ou diagnóstico.

O resultado fecha a verificação deste contrato sintético tipado. Não libera
chamadas com dados privados, orçamento recorrente, mudança de modelo,
aprovação dos atributos VLM ou conclusão integral da #5/projeto. A integração
final da demonstração e a paridade independente seguem nos relatórios próprios.

Plano: `766f2974f0d759479e47d883a9f8734d1b2166a60d8fae13dfb1ada934ab369d`.
Configuração: `e75f102c6094ca8ee545d9505f3d3a4c5f69462d7896db45f0ba00ec094d4951`.
Payload: `e5437059f2b490a23bbb1d1146fc3c510c63a63ae9ddc5c075d70e41fcdfe00f`.
Ledger privado: `data/private/issue-5-nim-typed-request-v1/`.

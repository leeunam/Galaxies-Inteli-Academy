# Contraste nativo/derivado v2: duas chamadas, comparação incompleta

A [comparação v2 revisada](issue-4-vlm-contraste-nativo-v2-proposta.md) foi
executada uma única vez em 21/10/2026, com nova autorização específica para
as quatro células. A etapa terminou na segunda chamada, por `native_timeout`,
em **109,0818 s**. A fila foi selada; os dois positivos não foram executados
e os dois slots restantes estão encerrados. Não houve retry ou retomada.

A captura durável conservou os dois resultados terminais e o stdout original
somente no journal privado. Ambos os processos tiveram limpeza confirmada;
zero workers e zero scratch v2 ao encerrar. A fila v1 e seu scratch continuam
preservados, sem reabertura ou substituição de recibos.

## Observações

| Célula, ordem congelada | Resultado | Tokens de imagem observados | Decode completo | Tempo do processo |
| --- | --- | --- | --- | --- |
| Negativa derivada | `yes`, formato válido; esperado `no` | **1075** | 9/9 lotes | **53,1219 s** |
| Negativa nativa | Sem resposta; timeout técnico | não confirmado | 7/9 lotes concluídos; oitavo iniciado | **54,9211 s** |
| Positiva nativa | Não executada | — | — | — |
| Positiva derivada | Não executada | — | — | — |

O negativo derivado mantém o falso positivo, mesmo com 1.075 tokens e
encoder+decode completos. A célula nativa não fornece resposta para avaliar
percepção, formato ou acerto. Seu encoder concluiu, com 38.417 ms reportados,
mas a decodificação não terminou dentro do prazo; o processo foi recolhido com
returncode -9 e stdout vazio. A ausência de tokens confirmados no recibo não
é uma contagem observada de zero tokens.

Os eventos fechados registram `encoder_start → encoder_done` nos dois braços.
No derivado, há nove pares `decode_start/decode_done`, terminando em
`decode_done [9,9,1789]`. Na nativa, há sete pares completos; o último evento
é **`decode_start [8,9,128]`**, sem `decode_done` correspondente. A evidência
sanitizada conserva a sequência completa desses eventos, sem stderr bruto.

Sem resposta nativa e sem positivos, **não há comparação pareada completa**
nem conclusão sobre perda de detalhe na cadeia histórica. Não foi identificada
a causa da diferença de tempo entre as duas entradas, nem a causa da interrupção
v1. Não se atribuiu o timeout a memória, ambiente ou qualidade do modelo.
Os picos RSS registrados foram 2.791,87 e 2.780,38 MiB, respectivamente.

## Execução, integridade e limites

Código executado `a3e4fe02e2fde4d49c12f982098038c64abffe89`. Plano lógico
`8b6baea8e3f2f511587d52963cce14ff3e4002c5edeff8215464442bdef20b98`,
arquivo `e2735afbcdcb0a9ed19c01b398502da0a67eea1014a20ac2579093ecd997a11e`
e configuração `deca5336202f4fe5dc3d5b9fef122a83553bac0d691831c96b975822fdb4c455`
continuam iguais. Autorização e selo foram gravados externamente, de forma
exclusiva e durável, vinculados ao plano, raiz e quatro entradas, antes do
único despacho da sessão 79160.

O processo controlador saiu com código 1, coerente com a falha técnica. Seu
stdout agregado coincide com o checkpoint selado. Existem duas reservas e dois
resultados; a inspeção durável valida ambos, informa `no_reentry=true` e
`remaining_calls=0`. O total de 109,0818 s é medido, distinto do teto conservador
de 260 s usado durante reservas. A janela 60/260 é cooperativa; não constitui
garantia de prazo duro contra bloqueio de fsync/kernel.

Os quatro PNGs, quatro pins do controlador, plano e selo conferem. Os 54 arquivos
protegidos anteriores permanecem iguais, incluindo fila v1/scratch, oito PNGs,
recibos/revisão NIM, manifestos de partições, proteções de M1 e registros de
retenção da demo. M1/A200 e teste reservado preservados, sem leitura semântica
do teste. Não houve aquisição, envio externo, POST NIM, treino ou despesa nova.
Nenhum campo VLM ou candidato foi liberado; gates e dependências B/C continuam.

A retenção dos novos insumos permanece em **21/10/2026, 23h59 São Paulo**;
esta execução não estende retenções nem descarta os artefatos anteriores.
Os 133 testes focados já haviam passado no candidato; não foram repetidos.
A verificação final limitou-se a recibos, inspeção em leitura e identidades.

A [evidência sanitizada](evidence/issue-4-vlm-contraste-nativo-v2-resultados.json)
registra os resultados e vínculos sem publicar bytes originais do stdout.
O diagnóstico usa apenas o par já revelado; não é auditoria cega, aceite de
atributos ou avaliação independente do modelo preditivo.

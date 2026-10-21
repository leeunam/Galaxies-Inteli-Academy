# Contraste visual v3: timeout na primeira célula

A [comparação v3 revisada](issue-4-vlm-contraste-nativo-v3-proposta.md) recebeu
nova autorização específica e foi iniciada uma única vez em 21/10/2026.
A primeira célula, negativa derivada, terminou por **`native_timeout`**,
sem resposta. O controlador selou a fila em **76,5429 s**, com uma chamada
consumida e **três posições encerradas sem dispatch**. Não houve retry,
segunda preparação ou execução dos slots restantes.

## Evidência terminal

| Medida da negativa derivada | Observado |
| --- | --- |
| Duração do processo | **74,8638 s** |
| Encoder reportado | **51,620 s**, concluído |
| Decode de imagem concluído | **15,730 s**, 6/9 lotes |
| Último evento | `decode_start [7,9,128]`, sem conclusão correspondente |
| Tokens em lotes concluídos / iniciados | 768 / 896 |
| Total de tokens confirmado | não confirmado (`null`) |
| Resposta / stdout | ausente / zero bytes |
| Returncode / limpeza | -9 / confirmada |
| Fase terminal diagnosticada | `image_decode` |

O diagnóstico puro localizou a interrupção antes da geração da resposta;
reduzir o limite de geração não explica ou resolve essa fase. A soma dos
intervalos conhecidos é 67,350 s; os 7,5138 s restantes não foram atribuídos
à geração ou à sobrecarga de captura. Os 896 tokens em lotes iniciados não
equivalem a 896 tokens processados nem ao total de imagem esperado de 1.075.

Na v2, esse mesmo derivado concluiu com falso positivo em 53,1219 s e encoder
de 30,076 s. Na execução atual, o encoder reportou 51,620 s. A causa da variação
continua desconhecida; não foi atribuída a pixels, memória, CPU, temperatura,
journaling ou concorrência. O orçamento maior não garantiu completar sequer
essa célula. Não se estima a duração das outras entradas a partir desse caso.

As três células restantes — negativa nativa, positiva nativa e positiva derivada —
não foram iniciadas. A decisão científica é **`technical_incomplete`**, sem
comparação pareada, avaliação perceptiva nova ou campos/candidatos liberados.
Os gates continuam iguais; não houve auditoria cega ou avanço B/C.

## Recibos, identidade e preservação

O journal durável preservou o resultado terminal e o stdout vazio privado.
A inspeção estrita validou o vínculo entre resultado e captura; nenhum prefixo
foi promovido a resposta válida. O stdout agregado do controlador coincide com
o checkpoint selado; processo controlador com saída 1. Há uma reserva e um
resultado, `remaining_calls=0` e `repeat_authorized=false`. Limpeza confirmada,
zero workers e zero scratch v3 ao terminar.

Código executado `1e5d57ae4625b55fc45b7edb07a5e0eaf5159160`. Plano lógico
`39ec99f9783e91a99adc063d61541261aea4f62baaaae429b70c31d4c6f36dd3`,
arquivo `f205e930cd4c7909e6d9c8115636ca4e876246a0792ffa2c1299fad13462f168`,
configuração `af1fd2503857a32a849b0e5b20ce64c71c8ba90ab5842afdd65becd354625b6b`.
Checkpoint final SHA-256:
`8b570f504f3a46c4d7fb993b1690eb7c3c168a4b1e3e80805317aac0e27d6ea4`.

Os quatro PNGs e seis fontes fixadas conferem. Vinte artefatos pertinentes
permanecem idênticos, incluindo checkpoint v2, seus quatro inputs de origem,
plano/PNGs v3 e recibos NIM anteriores. As filas v1/v2 e seus resultados não
foram reabertos. M1, partições, teste reservado, oito PNGs protegidos e trio da
demo preservados; nenhum download, envio externo ou treino. Esta frente não
executou POST; a tentativa NIM independente já havia terminado com limpeza.

Mantiveram-se 80 s por dispatch (75 úteis + 5 de limpeza) e 340 s globais,
incluindo persistência. São limites cooperativos, sem garantia de prazo duro
contra bloqueios de fsync/kernel. Retenção dos novos insumos até
21/10/2026, 23h59 São Paulo, sem extensão ou descarte dos artefatos anteriores.
Não foram repetidos testes ou realizadas novas inferências para documentar.

A [evidência sanitizada](evidence/issue-4-vlm-contraste-nativo-v3-resultados.json)
registra eventos fechados e diagnóstico de fase sem publicar stdout original.
A autorização desta comparação está consumida e a fila não oferece saldo
para retomar ou repetir. O journaling preservou a falha; não corrigiu percepção
nem identificou as causas das variações ou das interrupções históricas.

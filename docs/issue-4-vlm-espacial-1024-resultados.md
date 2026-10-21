# Diagnóstico espacial encerrado por timeout antes da resposta

Em 21/10/2026, o [diagnóstico de maior orçamento visual](issue-4-vlm-espacial-1024-protocolo.md)
encerrou na primeira chamada, no negativo real revelado, por `native_timeout`.
O encoder concluiu, mas a decodificação foi interrompida antes de qualquer
stdout. **Não há resposta semântica, contagem visual completa ou comparação
de percepção nessa configuração.** O positivo não foi chamado, sem retry
ou reutilização do saldo. A [evidência agregada](evidence/issue-4-vlm-espacial-1024-resultados.json)
vincula os recibos e os eventos sanitizados, sem IDs ou localizadores privados.

| Medida | Resultado |
|---|---|
| Chamadas / células semânticas concluídas | 1 / 0 |
| Relógio global | 40,2631 s; teto 100 s |
| Sessão nativa, incluindo recolhimento | 40,1449 s |
| Motivo terminal / retorno | `native_timeout` / -9 |
| Pico RSS antes da interrupção | 2.212,191 MiB; teto 3,3 GiB |
| stdout / stderr recebidos | 0 / 18.604 bytes |
| Encoder | um chunk; concluído em 29.482 ms |
| Decoder | nove batches anunciados; cinco concluídos, sexto iniciado |
| Contagem visual completa / intervenção efetiva | indisponível / não avaliada |
| Resposta / formato / comparação | ausente / não avaliado por falha técnica / não avaliada |
| Cleanup / workers / scratch | confirmado / zero / zero |

## O que foi observado

Os cinco batches concluídos tinham 128 tokens cada, com tempos de 1.509,
1.463, 1.549, 1.497 e 1.898 ms. O sexto início também anunciou 128 tokens,
sem fim capturado. Esses registros parciais não completam o critério de
encoder/decodificação do protocolo. Não preencher o total como 1.024 ou
1.056 por inferência, nem converter os eventos em aprovação da intervenção.

No negativo anterior, com gramática e 100 tokens completos, o encoder levou
2.105 ms; nesta tentativa foram 29.482 ms. É custo observado em execuções
distintas, sem garantia de escala ou benchmark geral. O pico RSS parcial
mais baixo não comprova que a execução completa usaria menos memória.

O limite por dispatch era 45 s, com cinco segundos reservados conjuntamente
para limpeza. A sessão tinha até 40 s antes dessa reserva e atingiu esse
prazo. O coletor encerrou/recolheu o processo e confirmou a limpeza. O teto
global de 100 s não foi atingido; o bloqueio observado foi o prazo da chamada,
não o allowance de preparação/bookkeeping ou o teto de memória amostrado.
Nenhum limite foi aumentado depois do resultado.

## Desfecho técnico e hipótese pendente

Ausência de stdout por timeout é **falha técnica**, não `format_invalid`,
abstenção ou resposta visual errada. O código manteve `answer=null`,
`image_tokens_observed=null` e `effective_visual_budget=null`; a observação
integral exigida não foi obtida. A fila ficou consumida e selada com uma
reserva e seu recibo terminal, sem segunda reserva/resultado.

Essa tentativa não confirma nem refuta que densidade maior altere a decisão
relacional. A hipótese continua sem resultado semântico e nenhuma candidata
foi sustentada. O [contraste de gramática anterior](issue-4-vlm-percepcao-gramatica-resultados.md)
continua preservado, com falso positivo nos dois modos e seus quatro JSON válidos.

Qualquer tentativa futura precisa tratar explicitamente o custo de encoder
e decoder agora observado, revisar prazo/viabilidade antes de executar e ter
orçamento e liberação próprios. Não há nova fila, ajuste de tempo/RSS/batch,
reentrada ou chamada preparados nesta unidade. A autorização encerrada não
permite repetir o negativo ou completar o positivo. Gates, auditoria e B/C
não são aprovados por progresso parcial do encoder.

## Verificação e preservação

Código/testes/protocolo em `a6333d9`. Antes da execução passaram 16 testes
direcionados, Ruff e formatação. Preflight sem modelo reproduziu os dois PNGs
e conferiu que somente min/max de imagem mudaram para 1.024; prompt/schema,
seed, modelo/projetor, contexto e parâmetros CPU permaneceram iguais.
Preparação medida em 0,05 s, sem indício prévio de insuficiência do allowance
de dez segundos. Essa medição não estimava o forward pass de alta densidade.

Após o timeout, configuração/fontes seladas, 26 arquivos protegidos e oito
folhas conferem. Os dois arquivos de partições conferem por hash, sem leitura
semântica. Ledger das quatro células anteriores e NIM sintético aceito
permanecem iguais; contrato NIM offline segue íntegro e sem liberação remota.
Zero workers/scratch próprios após recolhimento. Sem aquisição, HTTP NIM,
treino, teste reservado aberto ou alteração do M1. Nenhum corpo bruto ou
hash de conteúdo rejeitado foi persistido. Somente documentos/evidência
agregada mudaram depois da execução.

Plano: `1d4dce8f1fab4dc851f9a961fc5b56e98bfd91da78bc05cf9449740c6af15ca4`.
Configuração: `7e50923ed4196fe1a188ec59ee86105b1f0e71306feef63a7e0f68bd189513c2`.

# Negativo espacial: 1.056 tokens, falso positivo mantido

Em 21/10/2026, a [chamada negativa única](issue-4-vlm-espacial-negativo-60-protocolo.md)
concluiu em **50,6565 s**, com retorno 0, JSON válido, encoder/decoder completos
e limpeza confirmada. Foram observados **1.056 tokens de imagem**, frente aos
100 da referência. A resposta foi **`yes`**, contrariando o esperado diagnóstico
congelado **`no`**. O aumento de densidade foi efetivo, mas não corrigiu esse
negativo; nenhuma candidata ou campo foi liberado.

A [evidência agregada](evidence/issue-4-vlm-espacial-negativo-60-resultados.json)
vincula plano, configuração, revisão e recibos sanitizados. Não publica IDs,
localizadores, pixels ou corpo bruto. O caso é de treino já revelado, com
esperado derivado de revisão assistida V14, sem nova anotação certificada.

## Resultado e operação

| Medida | Resultado |
|---|---|
| Chamadas / positivo | 1 / não avaliado |
| Relógio global / sessão nativa | 50,6565 / 50,5635 s |
| Retorno / formato / resposta | 0 / válido / `yes` incorreto |
| Encoder | um chunk, 29.887 ms |
| Decoder | nove batches completos; 14.964 ms somados |
| Tokens observados | oito batches de 128 e um de 32 = **1.056** |
| Intervenção de densidade | aumento observado frente aos 100 anteriores |
| Pico RSS amostrado | 2.345,891 MiB; teto 3,3 GiB |
| stdout / stderr recebidos | 21 / 19.435 bytes |
| Cleanup / workers / scratch | confirmado / zero / zero |

O coletor validou a sequência integral, sem falhas registradas. A contagem
é observada; não foi preenchida pela flag 1.024. Não se mediu a grade
bidimensional ou atenção. O PNG fonte e o tempo permaneceram iguais;
upscale interno não acrescenta detalhes nativos ausentes.

A margem útil de até 55 s permitiu concluir esta execução dentro do dispatch
de 60 s e relógio global de 70 s. Isso não garante o tempo de outra execução.
Não houve ampliação posterior de limite, retry, positivo, retuning ou nova fila.
Resultado sanitizado foi persistido antes da remoção do scratch próprio.
A fila terminou `scope_completed`, consumida e selada, com campos/candidatas vazios.

## Comparação limitada e leitura

| Referência no mesmo negativo | Contagem visual completa | Resposta |
|---|---:|---|
| Orçamento baixo, gramática ligada | 100 | `yes`, falso positivo |
| Primeira tentativa espacial, prazo útil 40 s | indisponível por timeout | ausente; sem comparação semântica |
| Chamada nova, prazo útil até 55 s | 1.056 | `yes`, falso positivo |

A [tentativa anterior](issue-4-vlm-espacial-1024-resultados.md) permanece
encerrada por timeout, sem atribuir-lhe uma resposta retroativa. A chamada
nova preservou seu argv nativo, pergunta, schema/gramática, min/max de imagem
1.024, modelo/projetor, seed, temperatura, contexto, saída e parâmetros CPU.
Mudou somente a margem externa de tempo, com orçamento/revisão próprios.
As referências baixas são históricas, sem comparação contemporânea completa
ou reexecução das células encerradas.

O critério de apoio pontual era obter `no` neste negativo com técnica e
intervenção íntegras. A operação e o aumento de tokens passaram; o desfecho
semântico não passou. **Maior densidade não recebeu apoio como correção
desse caso nessa configuração.** Isso não prova ausência de benefício em
outros inputs nem isola toda a causa do erro. O aviso de grounding não
garantia melhora desta classificação relacional.

O positivo em alta densidade continua não avaliado. Um negativo conhecido
não estima precisão/especificidade populacional; não foi auditoria cega.
Não há candidata para promover, alteração de rótulo, gate flexibilizado ou
avanço automático a B/C. A triagem científica posterior será somente leitura
até decisão própria; nenhuma nova implementação ou inferência deriva deste adendo.

## Verificação e preservação

Preparação em `df176e2`: passaram 11 testes direcionados inventados, Ruff e
formatação. Preflight sem modelo reproduziu o crop e verificou argv/schema
idênticos, referências seladas e custo de preparação de 0,056 s.
Após a execução, configuração/fontes e 26 arquivos protegidos conferem,
incluindo M1 e oito folhas. Quatro arquivos de manifestos/partições das duas
coortes conferem por hash contra o registro anterior, sem leitura semântica.
Filas anteriores de gramática e timeout espacial permanecem iguais.

NIM não foi executado: ledger live ausente, placeholder do operador
`not_started` e revisão técnica preservada. O [bloqueio automático](issue-5-nim-no-grafo-live-bloqueio.md)
continua em vigor, sem pedido de execução adicional ou caminho alternativo.
Sem aquisição, remoto, treino, publicação, teste reservado aberto ou mudança
no M1. Nenhuma issue ou conclusão científica integral foi declarada encerrada.

Plano: `b04e92b8807ea956ce92d717625298d2489e77600e501ebfa1d2e2ed7377e397`.
Configuração: `d303fae3f19b8f823ece4794127544634b8e6e722e1e2f456a7af364f4b42870`.

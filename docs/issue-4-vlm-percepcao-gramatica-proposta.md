# Próximo contraste: pergunta curta, com e sem gramática

**Revisão estática, não implementação ou autorização de geração.** Em
21/10/2026, o [diagnóstico direto](issue-4-vlm-encoder-trace-resultados.md)
comprovou codificação e inserção de 100 tokens no positivo conhecido.
Qualidade perceptiva e gates continuam sem aprovação. A principal permanece
com escritor único; #7/NIM têm prioridade nas frentes de implementação.
Nenhuma fila, reserva ou processo de percepção foi criado por esta proposta.

## Hipótese delimitada

Mantendo imagem, pergunta e contrato textual exatamente iguais, a presença
do mecanismo de gramática pode alterar a resposta a uma pergunta visual
simples. O contraste observa somente essa intervenção nesses dois inputs;
não compara a pergunta curta ao prompt completo de v16 como efeito causal,
pois pergunta, schema e espaço de resposta serão diferentes dos históricos.

Não aumentar resolução, tokens de imagem, modelo ou contexto simultaneamente.
O aviso de grounding em 1.024 tokens é uma hipótese separada, sem contraste
habilitado nesta proposta.

## Prompt único proposto

Usar literalmente a mesma sequência UTF-8 abaixo nas quatro chamadas,
sem rótulo do caso ou da condição, exemplos distintos, resposta esperada,
anotações ou título do vídeo. Congelar o hash antes de qualquer execução.

```text
Look at this image. Is a garment hanging from a clothes hanger visible? Answer only one JSON object with exactly one key, "answer", whose string value is "yes", "no", or "uncertain". Use "uncertain" only if the image does not allow a decision. Do not add other keys or text.
```

O próprio prompt define todas as regras, inclusive no modo sem gramática.
O schema proposto é o mesmo objeto em ambas as condições; somente sua
aplicação ao runtime muda. No modo livre, não enviar argumento de schema.

```json
{"type":"object","properties":{"answer":{"enum":["yes","no","uncertain"]}},"required":["answer"],"additionalProperties":false}
```

O parser futuro deve validar stdout **inteiro**, aceitando apenas whitespace
externo, UTF-8 válido, objeto com chave única `answer` e uma das três strings.
Recusar chave duplicada, texto extra, code fence, array, valor fora do enum
ou coerção. Não extrair um fragmento JSON, usar stderr, reparar ou completar
resposta. Persistir somente enum válido ou código estático de inválido;
descartar bruto e não guardar hash de conteúdo rejeitado.

## Pares e ordem congelável

Mesmos inputs já revelados do diagnóstico, RGB 320×330 e tempo 0,2 s.
Nenhuma seleção adicional ou aquisição.

| Ordem | Input | Aplicação do schema | Esperado conhecido |
|---|---|---|---|
| 1 | Positivo congelado | sim | `yes` |
| 2 | Mesmo positivo | não | `yes` |
| 3 | Branco congelado | não | `no` |
| 4 | Mesmo branco | sim | `no` |

A ordem oposta dos modos no segundo caso evita pôr sempre um modo primeiro;
não substitui replicação ou randomização. Cada chamada terá processo novo,
sem histórico de conversa ou cache de resposta. Temperatura zero não torna
quatro observações uma estimativa de efeito populacional.

- Positivo: corpo de caso SHA `609bfa9a3b8da1616a452ae19fcf121aabd527424d104ef18b03b6bce0684ad8`;
  PNG SHA `4a22deaca1910529f560c3af6da06270aae129a53e0cdcea76c597077fa4bda6`.
- Branco: corpo de caso SHA `4415cb4857e336fe61279b31e72249847cf951019e59b0cd8bfbdbbfae899e16`;
  PNG SHA `d6727eed5586e51129d0fcea70acc76ae1ff653a850c94906e8c34a4897d122c`.

Manter runtime/modelo/projetor e ambiente literal do diagnóstico, seed 42,
temperatura zero, contexto 3.072, saída até 64 tokens, imagem 64–128 tokens,
CPU e batch quatro threads, batch/ubatch 128, verbosidade 4 e canais separados.
Além do prompt/schema novos comuns, os argumentos de cada par só podem
diferir pela presença/ausência de `--json-schema-file` e seu valor.

## Orçamento e parada propostos

Até **quatro chamadas / 180 s globais novos**, RSS amostrado 3,3 GiB,
stdout 16 KiB / stderr 256 KiB. Reservar cinco segundos conjuntos para limpeza
dentro do saldo de cada dispatch. Zero aquisição, remoto, treino, novo caso,
holdout ou mudança no M1. Não usar saldo das duas filas encerradas.

Exigir os quatro eventos de encoder/decodificação e contagem positiva por
chamada. Reserva durável antes de spawn, marcador exclusivo contra reentrada,
recibos sanitizados antes da limpeza e parada por falha operacional, identidade,
marcadores insuficientes, resposta inválida ou limpeza incerta. Sem retry,
troca de ordem ou de caso. Uma resposta inválida no modo livre é um resultado
de formato observado, mas encerra esta proposta conservadora; o contraste
restará parcial e não será convertido em erro semântico.

## Leitura predefinida

Com os dois pares completos e válidos, apresentar os quatro enums e a
concordância com os dois esperados conhecidos, separando resposta de
incerteza. Uma diferença dentro de um par mostra sensibilidade ao mecanismo
de gramática naquele ensaio. Concordância não exclui influência da gramática;
erro nos dois modos não identifica falha do encoder por exclusão. Mesmo
acerto nos quatro não valida o atributo completo ou o espaço de 22 objetos.

Não remover `uncertain`, mudar ordem de enum, ajustar pergunta, interpretar
saída inválida por heurística ou repetir apenas o modo que falhar. Qualquer
correção posterior deverá apontar o defeito comprovado e ter protocolo próprio
antes de inferência; não há avanço automático a auditoria cega ou B/C.

## Implementação futura e revisão antes de abrir a frente

A captura atual chama o decoder `item_first`, incompatível com `answer`.
Será preciso um adaptador isolado com parser estrito da resposta curta,
mantendo limites, consumo, canais e observações; não mudar ou remendar os
arquivos selados dos diagnósticos para acomodar o novo contrato. Reutilizar
verificação de pixels/identidades e eventos, evitando criar dispatcher geral.

Quando houver slot, revisar a pergunta e o contrato, implementar somente
essa adaptação, verificar com stdout/processos inventados a transparência
do par, a diferença exata de argv, os tetos e a parada. Então congelar
fontes/configuração/ordem e apresentar hashes concretos à revisão técnica
para janela CPU. Até lá: **zero gerações e zero nova implementação**.

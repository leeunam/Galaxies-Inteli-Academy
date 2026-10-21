# Diagnóstico espacial mínimo: orçamento visual 1.024

Preparação em 21/10/2026 após a [revisão estática](issue-4-vlm-pos-gramatica-hipotese-espacial.md).
Unidade aditiva, sem modificar fontes, filas ou recibos encerrados. Modelo
aguarda revisão técnica dos hashes e janela CPU; preparar não libera geração.
A autorização NIM permanece separada e não é utilizada por este diagnóstico.

## Hipótese e controle

O [contraste anterior](issue-4-vlm-percepcao-gramatica-resultados.md) observou
100 tokens visuais e falso positivo com/sem gramática. A hipótese nova é que
maior densidade interna possa mudar a decisão relacional nesses mesmos dois
crops. O aviso do runtime inclui Qwen3VL, mas sua motivação de grounding por
coordenadas não demonstra a causa desta decisão. Upscale de PNG 320×330 não
recupera detalhes nativos ausentes e não será descrito como nova evidência visual.

Usar exatamente o par V14 já revelado, com proveniência e esperados diagnósticos
anteriores, sem novos rótulos. Identidades/localizadores permanecem privados.
Negativo primeiro, positivo depois; tempos originais 2,8 s e 0,2 s, RGB 320×330.
Reproduzir os hashes PNG congelados antes/depois de cada chamada.

Gramática ligada nas duas células. Prompt completo e schema serão **os mesmos**
do braço ligado anterior, sem nova pergunta, exemplo, ordem de enum ou instrução.
Manter modelo/projetor, ambiente literal, seed 42, temperatura zero, contexto
3.072, saída 64, quatro threads CPU/batch, batch/ubatch 128, sem GPU e verbosidade 4.

As únicas diferenças de argv em relação a esse braço são:

| Argumento | Referência | Diagnóstico novo |
|---|---:|---:|
| image-min-tokens | 64 | 1.024 |
| image-max-tokens | 128 | 1.024 |

Mínimo/máximo mudam juntos como um fator de orçamento visual. Não aumentar
batch/ubatch, contexto, RSS ou duração para contornar falha. A referência com
100 tokens é histórica, de execução já encerrada; duas chamadas novas não
serão apresentadas como quatro células contemporâneas de baixa/alta densidade.

## Ordem, medição e desfechos

| Célula | Crop | Gramática | Esperado diagnóstico |
|---|---|---|---|
| 1 | Negativo real revelado | ligada | `no` |
| 2 | Positivo real revelado | ligada | `yes` |

Reutilizar captura limitada, parser curto e logs de encoder/decodificação.
Exigir os eventos completos/ordenados e retorno 0. Medir a soma de tokens
de imagem efetivamente decodificados, sem equacionar flag e contagem.
Arredondamento de grade pode produzir cerca de 1.056; não perseguir 1.024 exatos.

O critério operacional de intervenção efetiva será **contagem inteira maior
que os 100 tokens da referência** de cada crop. Isso comprova aumento observado,
não alcance exato da recomendação de grounding. Sempre relatar a contagem real.
Se não aumentar, selar `visual_budget_not_increased` e não chamar o próximo crop;
sem retry, mudança de flags ou nova fila para completar esta autorização.

JSON inválido é `format_invalid`, sem reparo/extração/coerção; pode seguir à
célula predefinida seguinte se técnica e intervenção estiverem íntegras.
`uncertain` é abstenção válida separada. Comparar apenas `yes`/`no` válidos
aos esperados assistidos conhecidos, sem alterar GT legado. Nenhuma aprovação
de atributo ou candidata é automática, mesmo se ambos passarem.

## Limites e consumo

- Máximo **duas chamadas / 100 s globais** após o marcador de início.
- Até **45 s por dispatch**, com cinco segundos conjuntos de limpeza dentro
  do saldo; até 40 s disponíveis para a sessão nativa antes dessa reserva.
- Dez segundos globais adicionais previstos para preparação/bookkeeping;
  o saldo efetivo governa cada dispatch. Não ampliar o relógio automaticamente.
- RSS amostrado 3,3 GiB; stdout 16 KiB / stderr 256 KiB e tee adicional
  limitado a 16 KiB. Não há garantia prévia de que alta densidade caberá.
- Zero aquisição, remoto, treino, novo caso/peso, holdout ou promoção ao M1.

Fila nova única de execução, independente do orçamento encerrado das quatro
células. Plano vincula referência selada, proveniências, fontes, sequência,
limites e argv normalizado. O helper de revisão permanece com decisão
`released_for_this_perception_contrast_only`, vinculada **aos hashes novos**,
ID real e literal da revisão técnica. Nenhuma liberação antiga é reutilizável.

Marcador de tentativa impede reentrada, inclusive antes da primeira reserva.
Consumo durável antes de cada spawn; resultado incerto não devolve saldo.
Persistir observação sanitizada antes da limpeza. Falha técnica, tempo,
bytes/RSS, identidade, encoder incerto, intervenção não efetiva ou limpeza
incerta encerram imediatamente. Limpeza incerta conserva scratch próprio.
Nenhum corpo bruto, exceção arbitrária ou hash de resposta rejeitada é retido.

## Preflight e leitura

Sem modelo: conferir fontes/referência, reaproveitar recibo da mesma gramática
já validada, reproduzir dois PNGs e comparar argv. Testar com processos e pixels
inventados a ordem negativa/positiva, tetos 2/100/45, reserva prévia, aumento
observado sem igualdade exata, continuidade de formato/abstenção e parada técnica.
Medir o custo local de preparação; trazer impedimento concreto antes de qualquer
proposta de expansão de tempo. Nenhuma medição de baixa densidade garante
tempo/memória ou qualidade da configuração nova.

Se o negativo mudar para `no` e o positivo continuar `yes`, o resultado poderá
motivar avaliação maior, sem demonstrar toda a causa do erro histórico. Se o
erro persistir, não haverá candidata apoiada nesse contraste. Falha operacional
não é erro semântico; relatar somente as células de fato concluídas. Gates
originais e auditoria independente continuam necessários; B/C completos,
partições, teste reservado e M1 permanecem preservados.

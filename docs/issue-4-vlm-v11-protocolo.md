# Produto v11 — protocolo de desenvolvimento nos casos revelados

Em 20/10/2026, o aluno autorizou implementar e avaliar a
[proposta pós-v10](issue-4-vlm-pos-v10-investigacao-e-proposta.md). Esta é uma
fila nova, sem reabrir v9/v10, completar 42–64, selecionar auditoria ou iniciar
B/C. O gate cego original e o M1/A200 permanecem preservados.

## Candidato único e identidade

`scripts/vlm_product_v11.py` contém o prompt integral e schema congelados:
instrução coesa por pista do mesmo item, estados/categorias v9 e enum adicional
`presentation_cue`. Pistas positivas: `held_display`, `isolated_display`,
`visible_use`, `worn_detail_focus`. Demais estados exigem respectivamente
`absent`, `incidental`, `uncertain`, com categorias vazias. Categorias positivas
não vazias, únicas e restritas às quatro anteriores. Contradição, JSON inválido,
duplicata ou campo extra interrompem sem reparo/retry/fallback. A pista é uma
declaração a conferir visualmente, não prova automática de qualidade.

Mesmo Qwen3-VL-2B Q4_K_M/projetor Q8_0, runtime b11716, CPU4, seed42,
temperatura0, saída64 tokens e limites visuais solicitados64/128. Nenhuma
instalação ou alteração de lock/ambiente. Uma chamada por crop RGB320×330;
mesma folha, crop, hash e tempo, sem cabeçalho. Produto continua com OR sobre
tempos ≤3 s; unknown explícito, sem converter por truthiness. Pessoa/texto
ficam em cache; demais colunas não são retomadas. Nenhuma resposta aprovada
para treino. Não ajustar a variante depois de observar qualquer resposta.

Antes do congelamento, `preinspection.json` privado registra os 32 frames das
oito folhas preservadas, com itens/pistas candidatas, ambiguidades, hashes e
tempos. É inspeção assistida posterior à revelação, anterior às respostas
v11; não substitui GT antigo, auditoria cega ou certificação humana. O plano
vincula seu hash e os pins da investigação. Uma pista incompatível com a
imagem ou cuja apresentação continua ambígua não conta como suporte.

## Duas fases condicionais e conferência de pistas

1. Até44 chamadas, zero aquisição: mesmos12 controles reconstruídos por hash,
   exigindo12/12 false; depois quatro crops de cada uma das oito folhas de
   moda já preservadas. Exigir8/8 valores+frames corretos conforme anotações
   antigas. Unknown não é recuperação. Falha perceptiva termina seu bloco e
   sela antes do próximo; falha operacional para imediatamente.
2. Se os valores passarem, pausar antes de qualquer aquisição. Revisar todas
   as pistas/categorias positivas, inclusive tardias, nas mesmas folhas,
   confrontando a inspeção prévia. Gravar `cue-review-phase1.json` exclusivo,
   vinculado a plano, hash do resultado, crop, tempo, categorias e pista.
   `supported=true/false/unknown` e nota assistida por positivo; exigir todos
   true. Não substituir anotação antiga ou inferir o restante do vídeo.
   Falha/ambiguidade sela sem fase2. Ausência de recibo mantém pausa sem chamadas.
3. Somente com ambas as verificações aprovadas, até48 chamadas/12 aquisições
   nos oito negativos e quatro positivos de beleza já fixados no plano v10.
   Mesmos pixels/propriedades/tempos ou parar sem reposição. Ao concluir,
   pausar conservando somente as folhas temporárias desta fase para revisar
   suas pistas positivas; exigir `cue-review-phase2.json` completo e vinculado.
   Depois selar o relatório e descartar somente essas novas folhas com journal.
   As oito folhas antigas nunca são alvo do descarte.

Os recibos são revisão visual assistida, não autorização do usuário nem nova
auditoria independente. Continuação depois da pausa é operação da mesma fila,
com prefixo concluído imutável; nunca repete chamadas. Tentativa incerta,
running/failed, erro, consumo encerrado ou fila selada não pode ser retomada.
Falha operacional na fase2 sela o parcial e limpa as folhas novas; sem revisão
completa não há prontidão declarada. Se a fase1 falhar em valor, a revisão das
pistas pode ser registrada separadamente como diagnóstico, sem reabrir a fila.

Comparar v11/v10/v9/v8/A-v7/B-v7 com denominadores e interseções explícitos.
v10 tem apenas oito casos, B-v7 apenas os casos antigos. Relatar confusão,
unknown, índices, ganhos/perdas, estados e pistas; acerto por OR não valida
todas as decisões individuais. Os oito casos representam cinco canais; erros
v10 vêm de dois. O painel máximo tem20 casos/10 por setor, todos revelados.
Valores/pistas sem suporte não ficam prontos mesmo com boa concordância.

Critério descritivo do painel completo: ≥8 conhecidos/setor, ≥90% de acerto
composto entre conhecidos, zero índices sem suporte, ≥3 previsões por valor
global e ≥1 por valor/setor, mais as duas revisões de pista aprovadas. Não é
o gate de liberação em32 casos, não certifica generalização e não libera coluna.
Uma nova auditoria exigirá outro protocolo, candidato congelado e suficiência
de classes pré-declarada. Não ajustar seleção/gate após respostas.

## Orçamento, persistência e preservação

Até92 reservas nativas novas,12 aquisições e1.800 s de sessões: partir dos
**1.710 / 256 / 35.417,71711680302 s** selados, com tetos cumulativos
**1.802 / 268 / 37.217,71711680302 s**. Reserva durável antes de cada operação,
180 s/3,3 GiB por chamada/aquisição, prazo de sessões compartilhado e tentativa
incerta consumida conservadoramente. Tempo de revisão/testes fora das sessões
não é medido como runtime nativo. Zero NIM/API externa de inferência.

Um executor, locks dos ancestrais e da fila, guardas do teste nos dois manifestos,
hashes de fontes/configuração/inputs e recibos antes de cada dispatch. Novos
recibos não podem sobrescrever anteriores. O carregador confere reservas,
contadores, raw→parser→mapper→OR e suporte visual vinculado antes de continuar.
Segredos, mídia, PNGs privados, anotações e resultados individuais não entram
no Git. README não rastreado permanece fora do escopo.

Preservar partições203/66/31, rótulos/features/evidências do teste fechados,
M1/A200, A300, B-cache, serviço/MCP, oito PNGs e todos os pins anteriores.
Validar código/testes/protocolo e commitar antes de preparar/executar. Ao
terminar: reconstruir resultados e comparação, conferir pins/fontes/ambientes,
consumo, limpeza e ausência de workers; commitar o relato com limitações reais.

Operações do módulo `scripts.vlm_product_v11_run`: `prepare`, `execute`,
`inspect`, `review` (com `--phase` e `--review-file`) e `cleanup`. Preparação e
execução usam o novo diretório privado `data/private/issue-4-vlm-v11-v1/` e os
mesmos manifestos de200/300. Fila parada por qualidade ou falha é terminal;
nenhum saldo autoriza v12, reexecução ou mudança de modelo.

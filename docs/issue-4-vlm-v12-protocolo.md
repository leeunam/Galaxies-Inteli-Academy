# Produto v12 — contraste de ordem e exemplos com schema fixo

O aluno autorizou em 20/10/2026 implementar e executar as três variantes da
[proposta pós-v11](issue-4-vlm-pos-v11-investigacao-e-proposta.md), avançando
somente pelos critérios ali registrados. Esta fila é independente; v9/v10/v11
continuam seladas. Nenhum saldo antigo é reutilizado. Não inclui outra auditoria
cega, casos 42–64 pendentes, treino B/C, liberação de coluna ou promoção do M1.

## Contraste congelado

`scripts/vlm_product_v12.py` deriva os três prompts do v11, com os mesmos
hashes lógicos dos rascunhos aprovados:

- **R:** definições na ordem ausência, incidental, apresentado, incerto;
  texto dentro dos blocos, introdução e contrato de saída idênticos.
- **E:** ordem v11, acrescentando os quatro exemplos completos previstos,
  objetos compactos separados por `; `, antes de `No explanations.`.
- **RE:** ambas as operações, sem mudança adicional.

Schema v11, ordem dos enums, categorias, pistas e parser estrito ficam iguais.
Estado/categorias/pista devem ser compatíveis; JSON inválido, Unicode inválido,
duplicata, campo extra ou inconsistência interrompem sem reparo/retry/fallback.
OR, unknown e produto ≤3 s ficam iguais. A pista continua sendo declaração do
modelo a confrontar visualmente, não confirmação automática do item.

Mesmo Qwen3-VL-2B Q4_K_M, projetor Q8_0, runtime b11716, CPU4, seed42,
temperatura0, saída 64 tokens, limites visuais solicitados 64/128 e um PNG
RGB 320×330 por chamada, sem cabeçalho. Mesma receita/fonte/hashes dos controles,
mesmas folhas/crops/tempos dos vídeos. Sem instalação, mudança de lock/ambiente,
NIM ou inferência externa. Pessoa/texto em cache; demais colunas não retomadas.

## Matriz completa, seleção e avanço condicional

1. Executar R→E→RE, cada qual nos mesmos 12 controles: **36 chamadas máximas,
   zero aquisição**. Uma falha perceptiva não corta a matriz pré-declarada;
   uma falha operacional/JSON/identidade interrompe imediatamente, com parcial
   sem seleção. V11 é referência em cache de 12 resultados, sem repetição.
2. Qualificar somente variantes com 12/12 false. Escolher R, depois E, depois
   RE nessa prioridade fixa; não selecionar por comparação parcial, views,
   teste ou resultados dos vídeos. Nenhuma qualificada encerra a fila. A
   seleção derivada fica persistida antes da primeira chamada de vídeo.
3. Executar apenas a selecionada nos quatro crops das mesmas oito folhas de
   treino preservadas: **até 32 chamadas e zero aquisição**. Exigir 8/8 valores+
   frames conforme GT antigo. Unknown não é recuperação. Falha encerra ao
   concluir o bloco, sem tentar a segunda qualificada ou retocar instrução.
4. Se os valores passarem, pausar para revisar todas as pistas/categorias
   positivas, inclusive tardias, confrontando a inspeção por frame já congelada
   na v11. Registrar recibo assistido exclusivo, vinculado a plano, variante
   escolhida, resultado, crop, tempo, pista e categorias. Exigir todo suporte
   true; false/unknown sela sem aquisição. Ausência de recibo mantém pausa.
5. Só com valores e pistas aprovados, executar os oito negativos e quatro
   positivos de beleza já fixados no painel v10: **até 48 chamadas e 12
   reaquisições**. Reproduzir propriedades, pixels e tempos ou parar sem
   substituição. Pausar ao final para revisar pistas antes do descarte das
   folhas novas com journal. As oito folhas antigas nunca são alvo de descarte.

GT antigo permanece imutável. Inspeção/revisões são assistidas, posteriores à
revelação, sem certificação humana ou independência. A retomada após revisão
usa somente o sufixo ainda não executado; tentativa incerta/running/failed,
fila com erro ou selada não é retomada. Falha operacional sela o parcial e
limpa imagens novas. Falha de valor nos oito dispensa revisão de gate sobre
esse bloco, mas permite diagnóstico separado, sem reabrir a fila.

Cada reserva/raw/resultado registra variante, sample e índice do frame. O
carregador verifica fonte/configuração, inputs, prefixo da sequência, reservas,
contadores, raw→parser→mapper→OR, seleção derivada e revisões antes de continuar.
Trocar R/E/RE em um recibo ou no estado é divergência, mesmo com schema igual.

## Comparação e limites científicos

Relatar contagens por variante nos12 controles, matriz completa/parcial,
qualificadas, seleção e pares R/v11, E/v11, RE/E e RE/R. O comparador em cache
não é replicação simultânea nem mede variância. São controles sintéticos,
incluindo oito variações de ABC123, não especificidade em vídeos reais.

Nos vídeos, comparar só a selecionada com v10/v9/v8/A-v7/B-v7 onde houver
cache, com interseções/denominadores explícitos. V10 tem oito resultados e v11
zero; não apresentar20 resultados dessas versões. Mostrar ganhos/perdas,
unknown, estados/pistas por frame e índices sem suporte; OR correto não
certifica todas as subdecisões. Os oito positivos são cinco canais revelados.

Prontidão descritiva no painel completo de 20: ≥8 conhecidos/setor, ≥90% de
valor+frames entre conhecidos, zero índices sem suporte, ≥3 previsões por valor
global e ≥1 por valor/setor, com ambas as revisões de pistas aprovadas. Não
substitui o [gate cego original](issue-4-vlm-revisao-perceptiva-protocolo.md),
não libera treino. Outra auditoria exige protocolo/candidato congelado e
suficiência de classes pré-declarada, excluindo casos/canais já revelados.

## Orçamento e preservação

Até **116 reservas novas, 12 aquisições e 2.400 s de sessões**, partindo dos
**1.722 / 256 / 35.564,65692200101 s**, com tetos cumulativos
**1.838 / 268 / 37.964,65692200101 s**. Até 180 s por chamada nativa ou
aquisição; monitor de RSS de 3,3 GiB no subprocesso VLM,
prazo compartilhado e reserva durável antes de operar. Tentativa incerta
consumida conservadoramente, sem reiniciar contadores. Tempo de suíte e
revisão fora das operações não é contado como runtime nativo.

Um executor, locks dos ancestrais e da fila, guardas do teste nos dois
manifestos. Preservar oito PNGs antigos, partições 203/66/31, anotações,
M1/A200 servido, A300, B-cache, serviço/MCP e todos os pins anteriores. Teste
reservado fechado, sem features/rótulos/previsões/métricas. README não
rastreado fora do escopo. Segredos, dados privados e temporários fora do Git.

Commits verificados de código/testes/protocolo antes das chamadas. Ao terminar,
reconstruir comparação e recibos, conferir pins/fontes/ambientes, consumo,
limpeza e workers; commitar o relato. Nova fila privada:
`data/private/issue-4-vlm-v12-v1/`. Operações do módulo
`scripts.vlm_product_v12_run`: `prepare`, `execute`, `inspect`, `review`
(`--phase`, `--review-file`) e `cleanup`, com os manifestos 200/300 preservados.
Parada é terminal; saldo não autoriza outra versão ou nova auditoria.

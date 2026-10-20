# Produto v10 — protocolo operacional aprovado

Em 20/10/2026, o aluno respondeu **“Aprovar as duas fases da v10”** à pergunta
com os limites de 92 chamadas locais, 12 reaquisições e 30 minutos de sessões.
Este protocolo concretiza o [plano aprovado](issue-4-vlm-pos-v9-investigacao-e-proposta.md).
Não autoriza nova auditoria cega, completar v9/42–64, treino B/C, NIM ou promoção.

## Especificação única

`scripts/vlm_product_v10.py` acrescenta somente o parágrafo de apresentação de
roupas vestidas aprovado ao prompt estruturado v9, antes de `Return exactly`.
Os bytes do parágrafo ficam na constante `INSERTION`. Remover essa inserção
devolve exatamente o prompt v9. Schema, campos, ordem das alternativas/exemplos,
parser estrito v9, categorias, mapper, OR e janela ≤3 s permanecem iguais.

Uma pergunta de produto por frame; Qwen3-VL-2B Q4_K_M, projetor Q8_0,
runtime b11716 instalado, CPU4, temperatura0, seed42, 64 tokens de saída e
limites visuais solicitados64/128. PNG RGB320×330 com padding, crops e tempos
anteriores. Não medir qualidade dos subestados/categorias sem GT próprio.
Pessoa/texto vêm do cache v8. Nunca alterar unknown, evidência ou anotação para
obter aprovação. `approved_for_training=false` em todos os resultados.

O extrator salva reserva e recibo inicial antes de invocar o runtime; grava
resposta bruta antes do parser, inclusive Unicode inválido em JSON ASCII.
JSON duplicado, contraditório, truncado, tipos inválidos ou pixels alterados
consomem a tentativa e param sem reparo/retry. Escritas atômicas sincronizam
arquivo e diretório. Hashes de fontes/testes/protocolo/especificação e inputs
são congelados no plano privado antes da primeira operação real.

## Execução sequencial com bloqueio entre fases

Fila nova `data/private/issue-4-vlm-v10-v1/`, separada de todas as filas antigas.
O plano fixa os IDs e ordem a partir das evidências seladas e não expõe rótulos
de alcance. Um executor, locks das filas ancestrais e da nova fila, guarda de
acesso ao teste e conferência de workers/temporários antes de operar.

1. Reconstruir os 12 controles existentes e conferir seus hashes. Executar
   os 12 enquanto o contrato operacional funcionar; exigir **12/12 false**.
   Falha perceptiva sela o bloco, antes de usar qualquer folha real.
2. Somente após os controles, usar as oito folhas já preservadas, com quatro
   chamadas por caso. Completar esse bloco sem retuning e exigir **8/8
   valores+frames corretos**. Não baixar nada nesta fase. Ela usa até44 chamadas.
3. Somente se as duas condições anteriores passarem, reobter os oito negativos
   e os quatro positivos de beleza do piloto v9 já fixado. No máximo12
   aquisições, sem repetição interna/externa. Conferir propriedades, folha,
   crops e tempos exatos antes de inferir quatro frames por caso: até48
   chamadas adicionais. Divergência ou falha para imediatamente. Nenhum ID é
   substituído; o caso42 não faz parte da seleção. Bytes de contêiner diferentes
   não substituem a verificação dos pixels.

O painel máximo de20 é revelado e de desenvolvimento, dez/setor: beleza4
positivos/6 negativos, moda8 positivos/2 negativos. Comparar somente os mesmos
casos completos entre v10, v9, v8 e A/v7; B/v7 só onde houver cache. Relatar
denominadores, cada fase, ganhos/perdas, classes, cobertura, valor+frames,
evidência sem suporte e estados. Resultados parciais não são vinte avaliados.

Prontidão **descritiva** do painel completo exige ≥8 conhecidos/setor,
≥90% valor+frames entre conhecidos, zero índices sem suporte, ≥3 previsões por
valor no painel e ≥1 por valor/setor. Não é liberação nem revisão do gate de
32 casos. Suporte insuficiente nos grupos antigos continua explicitado,
sem fabricar erros para gerar false. Nenhuma coluna é liberada nesta unidade.

## Consumo, interrupção e preservação

Carregar os valores exatos do checkpoint limitado selado:256 aquisições,
1.666 reservas e34.792,30414601901 s contabilizados. Tetos novos:12/92/1.800 s;
cumulativos máximos268/1.758/36.592,30414601901 s, dentro de277/1.758/27 h.
O tempo é de sessões, não toda a duração do trabalho. Por operação, até180 s
e RSS filho≤3,3 GiB. Conferir runtime/pesos em leitura, sem instalar/extrair.

Persistir consumo antes de cada operação. Uma chamada em andamento reserva
conservadoramente seu prazo restante no recibo; ao concluir, registrar o tempo
medido. Interrupção incerta bloqueia retomada automática. Falhas preservam
reserva, raw e recibos; nunca reiniciar contadores, pular caso ou repetir chamada.
O prazo total compartilha os1.800 s; não fornecer esse total de novo por chamada.

Preservar as oito folhas antigas inclusive ao terminar, todos os recibos/filas
selados, M1/A200, A300, B-cache, serviço/MCP, ambiente/lock e partições203/66/31.
Teste reservado fechado, sem labels, features, previsões ou métricas.
Vídeos e scratch novos são removidos por sessão. Folhas novas da fase2 só
podem ser removidas com journal e hashes após selar o relatório; nunca remover
ou sobrescrever as oito folhas antigas. Uma limpeza incerta bloqueia operações.
Não ler, editar ou versionar README não rastreado.

Implementar e testar com fixtures inventadas antes das operações reais:
delta único, tempo/identidade, reserva durável, falha/Unicode sem retry,
gates entre fases, limites, fila incerta/selada, tampering e comparação parcial.
Commits por unidades verificadas. Fontes congeladas não mudam durante o run;
resultados são registrados em documento separado, inclusive diante de reprovação.

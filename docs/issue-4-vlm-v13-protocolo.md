# Produto v13-R — geração por ramos compatíveis

O aluno autorizou em 20/10/2026 implementar e executar a
[proposta pós-v12](issue-4-vlm-pos-v12-investigacao-e-proposta.md), incluindo
validação da gramática no b11716 instalado antes das inferências. Uma versão,
uma fila nova; v9/v10/v11/v12 continuam seladas. Não reutilizar seus saldos.
Não inclui nova auditoria cega, produto 42–64, treino B/C ou promoção do M1.

## Especificação congelada

Prompt R integral e decoder estrito v11, sem outras instruções. Schema raiz
`oneOf` de sete objetos fechados na ordem aprovada: ausência, incidental,
apresentado/held, apresentado/isolated, apresentado/use, apresentado/worn,
incerto. Todos exigem state, presented_categories, presentation_cue, nessa
ordem, sem campos adicionais. Estado/pista constantes por ramo; categorias
vazias nos três não positivos, 64 listas ordenadas únicas não vazias nos três
primeiros positivos e 49 que incluem garment no worn. Preserva o conjunto
de 244 objetos aceitos pelo decoder. Não depende de if/then, contains ou
uniqueItems. Constantes de array podem restringir whitespace serializado;
isso não altera os valores semânticos permitidos.

Não reparar raw, derivar pista ausente, aceitar só o estado ou corrigir pelo
GT. Parser, mapper, OR, unknown e produto ≤3 s inalterados. Pistas coerentes
ainda exigem suporte nos pixels; o contrato não resolve percepção sozinho.
Mesmo Qwen3-VL-2B Q4_K_M, projetor Q8_0, b11716, CPU4, seed42, temperatura0,
saída64 e limites visuais solicitados64/128; um PNG RGB320×330 por chamada.
Pessoa/texto em cache; demais atributos não retomados.

## Gate nativo anterior à geração

Ponte C++ pequena ligada a `libllama-common.so` e `libllama.so` existentes.
Somente os cabeçalhos públicos oficiais b11716 são copiados temporariamente
para compilar a ponte; hashes fixos. Não compila, instala ou substitui código
do runtime. A conversão usa `json_schema_to_grammar(..., false)`, como o
caminho --json-schema-file do adaptador. O parser/pilha nativos verificam
aceitação por caracteres e término completo, sem vocabulário/modelo/forward.

Exigir zero divergências nos 9.548 objetos do domínio finito, aceitando os244;
mais244 variações de whitespace de campos e23 mutações brutas, incluindo a
contradição de R, prefixo incompleto, conteúdo adicional, duplicata e ordem
de chaves incompatível com a gramática. Total9.815 sondas. O decoder semântico
aceita outras ordens de chaves; a geração mantém a ordem fixada. O recibo
registra schema, gramática, fontes, bibliotecas, cabeçalhos, ponte, transcrições
e contagens. Warnings, conversão parcial ou divergência bloqueiam inferência.

O carregador e cada reserva conferem o recibo e sua integridade. Alteração
de fonte/schema/biblioteca/gramática/transcrição bloqueia despacho. A ponte
é somente de pré-verificação; a inferência continua pelo adaptador existente.
Tokenização offline de vocabulário, se usada para verificar exemplos, não é
forward pass; whitespace arbitrário não tem garantia de caber em64 tokens.
Saída truncada continua falha terminal, sem ampliar o limite.

## Fases e paradas

1. **Até12 chamadas, zero aquisição:** mesmos controles/receita/fonte/hashes.
   Exigir12/12 false. Falha perceptiva conclui o bloco e sela sem vídeos;
   JSON, contradição, operação ou identidade falha interrompe imediatamente.
2. Somente com controles aprovados, **até32 chamadas, zero aquisição**:
   mesmos quatro crops/tempos das oito folhas preservadas. Exigir8/8 valores+
   frames do GT antigo. Concluir o bloco se falha perceptiva e encerrar;
   unknown não recupera. Nenhum segundo candidato ou retuning.
3. Se valores passarem, pausar para revisão assistida de todas as pistas e
   categorias positivas, inclusive tardias, contra pixels e inspeção prévia
   congelada da v11. Recibo exclusivo vinculado a plano, resultado, crop,
   tempo, categorias e pista. Exigir todos os suportes true; false/unknown
   sela sem aquisição. Ausência do recibo mantém pausa.
4. Só com ambos aprovados, **até48 chamadas/12 reaquisições** dos mesmos oito
   negativos e quatro positivos de beleza já fixados no painel v10. Exigir
   propriedades/pixels/tempos antigos; divergência para sem substituir caso.
   Pausar para revisão das pistas e publicar recibo antes de descartar novas
   folhas por journal. Oito folhas antigas nunca são alvo de descarte.

As revisões são assistidas após revelação, sem independência ou certificação
humana. GT antigo imutável. Retomada após revisão usa só sufixo não executado;
falha/uncertainty/running ou fila selada não permite retry. Falha operacional
sela parcial e descarta somente imagens novas com journal. Nenhuma revisão
retroativa reabre a fila ou muda a classificação de uma tentativa inválida.

## Comparação e preservação

Comparar controles com v11 em cache, só com pixels/tempos idênticos e pares
completos. V12 tem uma resposta rejeitada e zero resultados aceitos; não
tratá-la como false/unknown ou baseline de acurácia. V11/v12 têm zero vídeos.
Comparar vídeos com v10/v9/v8/A-v7/B-v7 apenas nas interseções; v10 tem oito,
não20. Mostrar ganhos/perdas, unknown, denominadores e suporte dos índices.
O contraste muda o schema como conjunto; não isola ordem de ramo ou palavra.

Prontidão descritiva nos20: ≥8 conhecidos/setor, ≥90% valor+frames entre
conhecidos, zero índices sem suporte, ≥3 previsões por valor global e ≥1 por
valor/setor, ambas revisões aprovadas. Não substitui o
[gate cego original](issue-4-vlm-revisao-perceptiva-protocolo.md), não libera
coluna. Outra auditoria exige protocolo próprio e exclusão de canais/casos
revelados. Não selecionar amostra nova nesta fila.

Preservar todos os pins herdados, oito PNGs originais, pixels/tempos,
anotações e partições203/66/31. Teste reservado fechado, sem abrir suas
features/rótulos/previsões/métricas. M1/A200 servido, A300, B-cache, serviço
Python/MCP, locks e ambientes intactos. Sem instalação, NIM ou inferência
externa. README não rastreado fora do escopo, sem leitura/edição/staging.

## Orçamento e verificação

Até **92 reservas novas, 12 aquisições e2.400 s de sessões**. Partir dos
**1.723 /256 /35.577,11798522601 s** selados; tetos cumulativos
**1.815 /268 /37.977,11798522601 s**. Até180 s por chamada/aquisição, RSS3,3GiB,
um executor, locks da linhagem/fila e guardas de teste200/300. Reserva durável
antes de operar; cobrar tentativa incerta conservadoramente, sem reset.
Suíte e pré-verificação sem geração não contam como sessão de inferência.

Commits de código/testes/protocolo verificados antes das chamadas. Ao fechar,
reconstruir raw→decoder→mapper→OR, comparação, recibos, consumo, descarte,
pins, pixels/tempos, versões e workers; commitar o relato. Saída nova:
`data/private/issue-4-vlm-v13-v1/`; provas em
`data/private/issue-4-vlm-v13-verificacao-v1/`. CLI
`scripts.vlm_product_v13_run`: prepare, execute, inspect, review, cleanup,
com manifestos200/300 e --phase/--review-file na revisão. Parada é terminal.

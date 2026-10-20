# Pós-v13-R — categoria cosmetic sem suporte

Investigação de 20/10/2026, somente com controles, respostas capturadas e casos
de treino já revelados. **Cosmetic foi declarado pelo modelo no raw; não foi
acrescentado pelo parser.** A gramática corrigiu combinações incompatíveis de
estado/pista, mas admite categorias extras sem comprovar um item para cada uma.
O motivo interno da escolha do modelo permanece desconhecido.

Recomendação: **v14 com uma categoria para um único item apresentado por frame,
vinculado à sua própria pista**, mantendo cosméticos, aplicadores, roupas e
acessórios disponíveis. Registrar o novo significado de `presented_categories`:
testemunho de um item, sem pretensão de inventário completo. Este documento é
investigação/proposta; não implementa extrator/fila, não retoma avaliação e não
executa inferência, aquisição, treino ou auditoria cega. O
[resultado parcial v13-R](issue-4-vlm-v13-resultados.md) continua selado.

## Reconstrução e evidência visual

Replay dos **31 raws capturados**: 12 controles, 16 frames de quatro vídeos
completos e três frames do quinto vídeo interrompido. Todos conferem com os
hashes, especificação R, PNG e tempo do plano. Os objetos são aceitos pelo
schema v13-R e pelo decoder estrito, sem reparo. Os quatro vídeos completos
acertam valor+frames do GT antigo; isso não certifica suas categorias/pistas.

Nos 16 frames completos há **12 apresentados e quatro incidentais**. As listas
positivas são seis vezes `[garment, cosmetic, accessory]`, cinco vezes
`[garment, cosmetic]` e uma vez `[cosmetic, garment, accessory]`. As pistas são
oito `worn_detail_focus` e quatro `held_display`; nenhum positivo cita
applicator. **Os 12 objetos positivos têm cosmetic sem suporte de apresentação
no crop**, conforme diagnóstico assistido, após revelação, sem independência.
Nove desses positivos são precoces e três são tardios; o problema antecede OR
e janela ≤3 s. Não há recálculo de GT ou de pontuação antiga.

| Caso já revelado | Declaração v13-R | O que os pixels permitem concluir |
| --- | --- | --- |
| Blusa branca com babado | Frames 1/2: três categorias com worn; frame 4: mesmas três com held | Roupa/rosto visíveis não identificam cosmético apresentado. A ambiguidade do detalhe já estava na inspeção congelada; pose lateral também não certifica item segurado para exibição. |
| Camisa listrada e calça marrom | Frames 2/3/4: garment+cosmetic, com accessory no 3; worn | Corpo inteiro/padrão sozinho não estabelece detalhe pela rubrica. O crop tardio de roupa tampouco sustenta cosmetic. |
| Apresentadora com pincel e recortes de roupas | Frames 1/2/3: garment+cosmetic+accessory com held, variando a ordem | Pincel é aplicador; recortes de roupa são itens distintos. Uma pista do pincel não pode ser transferida a roupa/cosmético/acessório. Não há aplicação visível tocando a pele. |
| Saia com laço e fenda, sem rosto no crop | Frames 2/3/4: garment+cosmetic com worn | Enquadramento da saia sustenta detalhe da roupa; nenhum cosmético é apresentado. Este caso impede atribuir todas as ocorrências apenas à maquiagem no rosto. |

O quinto caso tem calças em cabide e **somente três raws**, sem resultado de
vídeo: frames 1/3 dizem `[garment]`, frame 2 `[garment, cosmetic]`, todos held.
O cosmético do frame 2 não tem apresentação identificável. Os dois singletons
são contraexemplos observados à hipótese de que a v13-R sempre exige cosmetic.
Não completar o quarto frame, fabricar agregado ou contar cinco vídeos
avaliados. Este diagnóstico usa essas três respostas apenas no nível de frame.

Os controles deram **12/12 false**: seis `no_target`/`absent` e seis
`incidental_only`/`incidental`, todos com lista vazia. Esse gate verifica false;
não certifica que a distinção fina ausência/incidentalidade esteja correta.
A revisão formal de pistas da fase 1 não foi submetida, pois as oito folhas não
foram concluídas. O diagnóstico não transforma o encerramento operacional em
um novo resultado formal de gate.

## O que explica a possibilidade do erro

1. O prompt pede listar somente categorias cuja apresentação seja visível,
   mas também diz literalmente: **“At least one listed category must contain
   the SAME item with the selected cue.”** Há uma única pista para até quatro
   categorias. A cláusula de pelo menos uma é mais fraca que comprovar um item
   apresentado para cada categoria; permite uma interpretação em que uma roupa
   sustenta a pista e as outras categorias acompanham a lista. A primeira
   instrução ainda proíbe categorias sem suporte: isso é uma fragilidade de
   vinculação, não autorização semântica para alucinar.
2. O schema fecha estado, pista e listas admissíveis, sem inspecionar pixels.
   Para worn, exige que garment esteja presente, permitindo também cosmetic e
   accessory. Não obriga a pista a sustentar cada categoria extra. Decoder
   verifica tipos, enum, unicidade e contradições; não verifica verdade visual.
3. O prompt diferencia aplicador e roupa, mas não explicita que maquiagem já
   vestida no rosto não estabelece um cosmético apresentado. Isso pode favorecer
   confusão produto/aplicador/aparência; o caso sem rosto mostra que essa hipótese
   não basta sozinha. A repetição das mesmas listas é compatível com completar
   categorias por associação, sem demonstrar o mecanismo interno.

A enumeração offline confirma **244 objetos válidos**, 241 positivos. Destes,
185 incluem cosmetic e **56 não incluem**. Para worn existem 49 listas, das
quais 11 sem cosmetic. São contagens de objetos possíveis, **não probabilidades
de geração**: não se deve inferir chance de 185/241, pesos uniformes ou efeito
causal da ordem do enum.

O recibo nativo anterior já contém aceitação de `[garment]` e das continuações
`[garment, cosmetic]`, `[garment, applicator]`, `[garment, accessory]` com worn
(índices 101/381/409/465). Releitura das transcrições, sem executar a ponte:
fechar a lista sem cosmetic era possível na gramática por caracteres. Os raws
singleton do quinto caso também demonstram geração real dessa alternativa.
Isso não mede máscaras por token, logits ou preferência entre alternativas.

Na **v10, nos mesmos 16 PNGs/tempos**, cosmetic já aparecia em três frames,
todos do caso do pincel. A v13-R preserva essas três ocorrências e acrescenta
nove; v10 tinha sete frames positivos, v13-R doze. A v10 não emitia pistas,
e prompt e schema mudaram entre versões: o contraste não isola enum finito,
ordem dos ramos ou uma frase. V11/v12 não têm vídeos completos comparáveis.
Não há logits, atenção ou ablação controlada para atribuir o erro a quantização,
resolução, token específico ou prioridade de categoria. Não trocar pesos ou
pixels para testar essas hipóteses nesta investigação.

## Alternativas e próxima correção proposta

| Alternativa | Benefício | Limite / decisão |
| --- | --- | --- |
| Reforçar apenas a prosa para todas as categorias | Mantém listas completas | Continua exigindo várias vinculações sob uma única pista; não recomendada como próxima correção isolada. |
| **Um item, uma categoria, uma pista** | Elimina categorias acompanhantes e reduz a tarefa ao testemunho necessário para produto=true | Recomendada; omite deliberadamente itens secundários, podendo ainda escolher item ou pista errados. |
| Uma estrutura de evidência por item/categoria, ou várias chamadas | Permite comprovação separada e inventário mais completo | Amplia contrato, custo e complexidade; adiar enquanto o alvo é a presença booleana de produto apresentado. |

O rascunho privado mantém os três campos e a ordem dos sete ramos fechados:

| Estado/pista | `presented_categories` permitido |
| --- | --- |
| no_target/absent, incidental_only/incidental, uncertain/uncertain | Somente `[]` |
| presented_target/held_display, isolated_display ou visible_use | Exatamente um de `[cosmetic]`, `[applicator]`, `[garment]`, `[accessory]` |
| presented_target/worn_detail_focus | Somente `[garment]` |

Total **16 objetos semânticos: 13 positivos e três restantes**. Todas as quatro
categorias continuam possíveis globalmente, sem filtro por setor ou supressão
de cosmetic. O bloco de vinculação do prompt deve exigir um item identificável,
uma categoria e uma pista daquele mesmo item; permitir omitir outros itens
apresentados; proibir transferir pista entre itens/categorias. Explicitar que
cosmetic exige um produto cosmético apresentado identificável, maquiagem já
vestida não basta, e segurar aplicador não torna cosmético ou roupa held_display.
Não inserir IDs, respostas esperadas ou referências a estes casos no prompt.

Preservar as definições visuais de pistas, prioridade de um item confirmado,
abstenção para apresentação ambígua e demais blocos R. Ajustar somente o bloco
de vinculação e as duas instruções finais de cardinalidade. Novo decoder deve
acrescentar **exatamente uma categoria positiva** à validação estrita existente.
Manter mapper booleano, unknown, OR, janela ≤3 s e GT imutáveis. Registrar a
mudança de significado da lista na nova versão; não tratar o antigo contrato
multicategoria como saída equivalente.

Não reduzir listas antigas, remover cosmetic por código, mascarar pelo setor,
derivar a categoria do GT ou aceitar só o booleano. Os raws antigos continuam
os mesmos. Singleton pode continuar alucinando cosmetic ou uma pista; a proposta
reduz uma forma de erro e **não constitui recuperação perceptiva demonstrada**.
Também não corrige automaticamente corpo inteiro chamado de detalhe ou pose
chamada de held. Todas as novas declarações exigirão suporte visual integral.

## Verificação offline do rascunho

Com `jsonschema` 4.26.0 já instalado, os mesmos **9.548 objetos** do domínio
finito de campos completos foram enumerados, incluindo arrays com repetições:

- Schema v13-R aceita 244; rascunho aceita 16, todos subconjunto dos anteriores.
- Zero divergências entre o rascunho e o decoder antigo acrescido da regra de
  singleton positivo nesse domínio; **15 sondas inválidas** recusadas.
- Os 12 objetos de controles continuam válidos. Os 12 positivos completos são
  recusados por cardinalidade, e os quatro incidentais permanecem válidos.
- Dos três raws parciais, somente os dois singletons continuam válidos.

Recusar uma lista multicategoria antiga não prediz o que uma nova geração
escolherá. Não substituir resultados, mudar valor/frames ou declarar ganho com
essa rejeição offline. Esta prova não cobre todas as strings JSON, tokenização
ou runtime. **O schema/prompt v14 são rascunhos; a gramática nativa v14 ainda
não foi convertida ou verificada e não houve nova inferência.**

## Execução futura proposta, antes de outra auditoria cega

Uma versão/fila novas, um candidato congelado, sem reabrir v13 ou consumir seu
saldo encerrado. Pré-verificar conversão/aceitação nativa no b11716 instalado,
sem geração: 16 válidos, domínio finito, whitespace e mutações de raw, inclusive
multicategoria, duplicatas, estado/pista incompatíveis e worn/cosmetic. Conferir
limite de saída, identidade dos inputs e pin de fontes/gramática/recibo em cada
reserva. Divergência impede chamadas. Commitar código, testes e protocolo antes
de inferir. Nenhuma nova instalação ou substituição de runtime/pesos proposta.

1. **Até 12 chamadas, zero aquisição**, nos mesmos controles; exigir 12/12 false.
2. Se passar, **até 32 chamadas, zero aquisição**, nos quatro crops das oito
   folhas preservadas. Exigir 8/8 valor+frames do GT original e revisar todas
   as categorias/pistas positivas, inclusive tardias, contra os pixels e a
   inspeção congelada. Exigir todos os suportes true; false/unknown bloqueia
   aquisição, mesmo com booleano correto. Não redefinir ambiguidades pelo raw.
3. Só se ambos passarem, **até 48 chamadas/12 reaquisições**, nos oito negativos
   e quatro positivos de beleza já fixados no painel v10. Mesmos pixels,
   propriedades e tempos, sem substituições. Revisar suportes antes do descarte
   das novas folhas com journal; preservar as oito folhas antigas presentes.

Falha operacional/JSON/identidade interrompe imediatamente, sem retry/reparo;
falha perceptiva conclui o bloco e sela. Manter pausas para recibos de revisão
vinculados antes de aquisição/descarte. Unknown não recupera caso. Herdar os
critérios descritivos e comparações por interseção do
[protocolo v13](issue-4-vlm-v13-protocolo.md), incluindo classes, setores,
denominadores e ganhos/perdas. Não aliviar limiar ou escolher nova variante
depois de ver resultados.

Orçamento novo proposto: **92 chamadas /12 aquisições /2.400 s de sessões**.
Base selada **1.755 /256 /36.159,609599731004 s**; tetos cumulativos
**1.847 /268 /38.559,609599731004 s**. Manter 180 s por operação, RSS 3,3 GiB,
um executor, locks, guardas 200/300, reservas duráveis e cobrança conservadora
de tentativa incerta. A 32ª reserva v13 e seus 180 s não medidos continuam
consumidos; não repetir nem concluir essa operação. Nenhum orçamento novo foi
consumido nesta investigação. Implementação e execução ficam para uma próxima
instrução do aluno, após esta proposta.

Tudo acima é desenvolvimento em casos revelados. Não aprova produto, não
libera coluna e não inicia B/C ou promove M1. Outra auditoria requer protocolo
próprio, congelamento anterior e casos/canais de treino não revelados, mantendo
o [gate original](issue-4-vlm-revisao-perceptiva-protocolo.md). Pessoa, texto e
demais campos permanecem fora desta correção.

## Preservação e recibos

Os **1.100 arquivos protegidos** conferem antes/depois, incluindo evidência,
filas seladas, fontes, partições e artefatos M1/A200, A300 e B-cache. O plano,
checkpoint, comparação e raws v13 não mudaram. Oito folhas originais presentes;
32 crops reproduzidos em memória com hashes/tempos idênticos. Doze fixtures
regeneradas temporariamente, conferidas e removidas. Nenhuma mídia nova.

Partições **203/66/31** preservadas sob guardas dos manifestos 200/300, sem abrir
features/rótulos/previsões/métricas do teste. M1 e hashes dos modelos iguais.
Ambientes raiz/isolado: 130/42 distribuições iguais; runtime/pesos verificados em
leitura, sem instalação. Zero inferências, aquisições ou sessões novas de mídia;
nenhum worker ou sessão temporária restante. Contadores permanecem 1.755/256 e
36.159,609599731004 s. Não houve consulta externa ou envio de dados privados.

Recibos/rascunhos privados em
`data/private/issue-4-vlm-v13-cosmetic-diagnostico-v1/`: snapshot antes,
reconstrução vinculada, rascunho de prompt/schema, enumeração/sondas e preservação.
A única alteração versionada é este relatório; verificação por replay,
enumeração, hashes, identidade de pixels/tempos, ambientes, links e diff, com
revisão local. Sem mudança de produção ou nova execução da suíte: os 1.021
testes anteriores pertencem à implementação v13, não a esta investigação.
README não rastreado permanece fora do escopo, sem leitura, edição ou staging.

- Prompt proposto: `08432adbfee0b4ae4af793e5caa4826b7e1d48da8b6e9774b82078a6a132a325`.
- Schema proposto: `4b5c9f3a78cef507d7855d84d1a940daadbdc801bd5359713d29c07b1c31c034`.
- M1 preservado: `9dd1c7a2e35e32cf3068395ed8bf2e0561aa4fecded5c31754f981cc13d70d59`.

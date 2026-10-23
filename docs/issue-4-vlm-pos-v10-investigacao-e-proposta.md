# Produto pós-v10 — três falsos negativos e próxima correção proposta

Investigação de 20/10/2026, somente com casos de treino já revelados. Os três
erros restantes são **decisões perceptivas `incidental_only` nas respostas
brutas**, não perda de positivos no parser, no mapper ou na janela temporal.
A inserção da v10 ajudou, mas não resolveu a distinção entre roupa incidental
e roupa apresentada. Não foi isolada uma causa interna do modelo.

Recomendação: desenvolver uma **v11 com pista visual explícita de apresentação
do mesmo item**, instrução coesa e abstenção quando essa pista não puder ser
estabelecida. É uma proposta; nenhum extrator, prompt executável ou fila foi
alterado. A v10 continua selada. Não houve inferência, aquisição, auditoria
nova, treino ou promoção nesta investigação.

## Evidência reconstruída e limite da amostra

O carregador existente validou, em leitura, o plano, configuração, linhagem,
44 reservas e 44 respostas da [v10 encerrada](https://github.com/leeunam/case-GALAXIES-IA/blob/0df616e5fd64dfc4947abde583f2664b66abf410/docs/issue-4-vlm-v10-resultados.md).
Parser/intermediários/mapper/agregação reproduzem todos os resultados. As
oito folhas originais conferem; seus 32 crops foram reproduzidos somente em
memória, com os mesmos hashes, RGB320×330 e tempos. Não se salvaram novos crops.
As guardas de acesso ao teste dos dois manifestos ficaram ativas na reconstrução.

Os oito casos representam **cinco canais**, todos de moda e positivos na
anotação anterior. Os três erros representam **dois canais**: duas folhas
compartilham canal, pessoa, cenário e tipo de blusa. O caso da camisa e o do
vestido recuperado também compartilham canal. Essas relações são diagnóstico
de dependência, nunca entrada ou regra do extrator. O painel não mede
generalização, especificidade real ou desempenho nos 64 casos.

Todas as anotações antigas continuam imutáveis. As descrições visuais abaixo
são inspeção assistida posterior aos resultados, sem áudio, transcrição, views,
títulos ou intenção comercial. Não constituem novo GT de item, categoria ou
pista de apresentação, nem revisão humana certificada.

## Os três erros, comparados aos acertos

Nos três erros, os frames **0,2 / 1,5 / 2,8 s** receberam `incidental_only`
e categorias vazias. Isso produz false citando [1,2,3], exatamente como manda
o contrato. A anotação antiga de cada um é true com frames [1,2,3].
Os identificadores e hashes individuais ficam nos recibos privados.

| Caso visual já revelado | O que se vê nos pixels iniciais | Diagnóstico e limite |
| --- | --- | --- |
| Blusa branca estampada, calça verde | Rosto e blusa no primeiro frame; frente da blusa com babado centralizada no segundo; corpo mais aberto no terceiro; arara ao fundo | A roupa está visível, mas a resposta não informa se o modelo a detectou e rejeitou sua apresentação. Rosto, corpo inteiro e arara sozinhos não bastam pela rubrica. Aos 35,333 s houve `presented_target`; esse frame está corretamente excluído. |
| Camisa listrada, calça marrom e cinto | Primeiro frame sem rosto, com camisa, punho, cintura e cinto em destaque; segundo e terceiro mostram a roupa vestida ao ar livre | É o contraexemplo mais direto à instrução v10 de close dos detalhes da peça. Mesmo ele foi incidental nos três frames. O frame de 11,367 s também foi incidental; sua chamada comercial não é evidência permitida. |
| Blusa branca estampada, shorts azuis | Blusa/rosto próximos nos dois primeiros frames; corpo mais aberto no terceiro | Correlacionado ao primeiro erro, sem replicação independente. O frame de 17,933 s também foi incidental. Inferir apresentação somente pela roupa, cenário ou pessoa mudaria a rubrica. |

Comparadores úteis nas mesmas folhas:

- **Saia sem rosto:** v10 recuperou frames 2/3, mas manteve o 1 incidental.
  A peça com laço/fenda ocupa o enquadramento. Não usar a troca de cor entre
  frames como evidência de movimento em uma chamada de imagem única.
- **Vestido verde:** mão segurando a barra para fora no frame 1; v10 acertou
  frames 1/3 e rejeitou o 2. Há também um recorte de vestido no canto. Sem
  pista registrada, não sabemos qual item sustentou cada resposta positiva.
- **Peça xadrez em cabide:** frame 2 continua incidental e o 3 é positivo.
  Portanto a inconsistência também aparece em peça fora do corpo; a hipótese
  de supressão de roupa vestida não explica todos os erros por frame.
- **Pincel e roupas sobrepostas:** o valor final correto convive com categorias
  como cosmético/acessório e, em um frame, as quatro categorias. Sem anotação
  por item, não se pode afirmar que o acerto veio da testemunha esperada.
- **Calças seguradas em cabide:** três positivos iniciais mantidos, um exemplo
  de apresentação mais explícita já reconhecida.

Nos 24 frames iniciais, as mudanças v9→v10 foram quatro incidental→apresentado,
sete apresentado→apresentado e treze incidental→incidental. Dos treze últimos,
nove estão nos três erros e quatro em vídeos acertados pelo OR. Nenhum desses
24 frames recebeu `uncertain` ou `no_target`. Isso mostra falta de abstenção
neste recorte, sem demonstrar que todos deveriam ser `uncertain`.

## O que foi e não foi explicado

**Confirmado:** as 44 chamadas anteriores concluíram válidas; inputs/tempos e
cadeia de derivação conferem. Os nove estados brutos explicam os três false.
Não há base para reparar índice, converter string por truthiness, mudar OR
ou ampliar a janela. O positivo tardio não corrige uma falha do atributo precoce.

**Hipótese principal:** a decisão global entre incidental e apresentado ainda
não distingue de forma confiável o foco visual nos detalhes da roupa vestida.
A v10 acrescentou uma condição positiva a uma instrução que já contém avisos
contra roupa comum e corpo inteiro. Pode haver competição entre essas regras;
os recibos não isolam essa causa, a ordem das frases ou um efeito de comprimento.
Também não distinguem falha de detecção do item de falha na sua qualificação.

**Alternativa relevante:** parte dos frames pode ser insuficiente ou ambígua
sob a rubrica de imagem única. O GT anterior rotula o atributo e os índices,
não a peça/pista que o justifica. Não alterar esse GT para favorecer o modelo;
registrar a ambiguidade à parte. Recuperar todos os positivos não é garantido.

Não houve ablação de pesos, quantização ou resolução. Os objetos grandes
visíveis e os acertos em imagens semelhantes não provam que esses fatores
sejam irrelevantes, nem justificam escolhê-los como causa já demonstrada.

## Opções e correção recomendada

| Opção | O que permitiria investigar | Limitação / decisão |
| --- | --- | --- |
| Acrescentar outra frase sobre roupa vestida | Mais uma tentativa barata de sensibilidade ao prompt | Repetiria a estratégia v10 sem revelar a pista usada; não recomendada como próximo passo. |
| **Decisão com pista visual explícita, em uma chamada por frame** | Separar apresentação, incidentalidade e ambiguidade; inspecionar a base concreta de cada decisão | Recomendada como candidato de desenvolvimento; exige novo schema/parser e verificação perceptiva, sem promessa de recuperação. |
| Trocar pesos ou limite visual | Outra hipótese de capacidade visual | Muda outro fator e exige orçamento próprio; adiar até haver evidência de falha de detecção/detalhe. |

A v11 proposta substituiria a instrução acumulada por uma instrução única,
curta e organizada pela evidência. Isso é uma mudança conjunta de instrução e
saída; uma melhora não poderá ser atribuída isoladamente a uma frase ou campo.
Não acrescentar raciocínio livre ou várias tentativas. Manter estados e
categorias v9, adicionando **um enum `presentation_cue`**, com este contrato:

| Estado | Categorias | Pista exigida e interpretação |
| --- | --- | --- |
| `presented_target` | Não vazias, apenas as testemunhadas | `held_display`, `isolated_display`, `visible_use` ou `worn_detail_focus`; pelo menos um item da categoria citada deve ter essa pista no próprio frame. |
| `incidental_only` | Vazia | `incidental`: todos os itens visíveis são claramente incidentais e não há candidato de apresentação ambíguo. |
| `no_target` | Vazia | `absent`: nenhum item-alvo visível após inspeção. |
| `uncertain` | Vazia | `uncertain`: nenhum apresentado confirmado e algum item ou sua apresentação não pode ser estabelecido. |

`held_display` exige item segurado para exibição, incluindo tecido puxado para
mostrar a peça vestida; segurar um objeto sem apresentação não basta.
`isolated_display` exige item claramente disposto/exibido, como peça em cabide
no primeiro plano; um cabide na arara atrás de quem fala não basta.
`visible_use` exige ação de uso explicitamente visível do item-alvo, como
aplicador em contato com a pele; vestir roupa ou joia por si só não conta.
`worn_detail_focus` exige que o próprio enquadramento mostre em destaque um
detalhe identificável da peça, como corte, acabamento, fecho ou tecido. Um
rosto acompanhado de roupa, padrão apenas visível ou corpo inteiro sozinho
não estabelece essa pista. Não inferir movimento, intenção comercial ou
contexto de outro frame. Em dúvida entre apresentação e incidentalidade,
emitir `uncertain`, sem fabricar um negativo conhecido.

O parser estrito deve recusar combinações incompatíveis, chaves duplicadas,
categorias extras e enums desconhecidos, sem reparo. O mapper continua
true/false/unknown conforme o estado, com OR e janela ≤3 s existentes. O enum
é uma declaração verificável do modelo, **não prova automática de evidência**:
é possível alucinar uma pista. Auditar seu suporte visual e suas categorias
separadamente do acerto composto; uma falha dessa pista impede considerar o
candidato pronto, mesmo que o OR acerte o vídeo.

Antes de congelar a especificação executável, registrar em sidecar separado
uma inspeção assistida por frame/item/pista e suas ambiguidades nas oito folhas
já disponíveis. Ela será desenvolvimento posterior à revelação, nunca novo
GT cego. Manter as anotações antigas e relatar divergências. Isso torna explícito
o que será confrontado, em vez de escolher a testemunha após ler a v11.

A hipótese será contrariada se a camisa em close continuar incidental sem
reconhecimento de sua apresentação, ou se a nova pista aparecer também em
roupa incidental dos negativos reais. Nos dois casos da blusa, uma abstenção
pode ser mais fiel que um false categórico, mas continua sem recuperar o
positivo anotado e não permite avançar. Categorias/pistas sem suporte também
refutam a alegação de que o candidato aprendeu a testemunha correta.

## Avaliação proposta antes de qualquer auditoria

Uma futura autorização deve aprovar o candidato e um protocolo próprio. Não
reutilizar as 48 chamadas não consumidas da v10, reabrir sua fila ou completar
42–64 da v9. A presente proposta não executa as etapas abaixo.

1. Implementar versão aditiva, testes de contrato e fila separada; revisar e
   commitar antes das chamadas. Congelar prompt/schema/parser/mapper, fontes,
   runtime e painel. Uma variante, sem retuning, fallback ou retry.
2. Primeira fase, até **44 chamadas e zero aquisições**: mesmos 12 controles
   com hashes idênticos, exigindo 12/12 false; depois os mesmos quatro crops
   de cada uma das oito folhas. Manter os **8/8 valores+frames** exigidos pela
   v10 para avançar, sem contar unknown como recuperação. Exigir também
   suporte visual das pistas positivas declaradas; registrar qualquer
   ambiguidade, sem mudar GT ou afrouxar critério. Falha perceptiva sela a
   fase ao concluir seu bloco; falha operacional interrompe imediatamente.
3. Somente se a primeira passar, até **48 chamadas e 12 reaquisições** para
   os mesmos oito negativos reais e quatro positivos de beleza já fixados
   no plano v10. São casos já revelados, não nova seleção. Reproduzir pixels,
   propriedades e tempos antigos; divergência interrompe sem substituição.
   Sem esse contraste, 8/8 positivos e controles sem pessoas não demonstram
   que roupa incidental deixou de gerar falso positivo.

Comparar v11/v10/v9/v8/A-v7/B-v7 somente onde cada cache existir: v10 tem
resultado para oito vídeos, **não para os vinte**. Relatar fases, denominadores,
setores/canais, confusão, unknown, ganhos/perdas e suporte de cada índice/pista.
Não exigir todos os frames positivos para acertar o vídeo, mas mostrar os
erros por frame que o OR esconde. Manter o critério descritivo de prontidão
do [plano anterior](issue-4-vlm-pos-v9-investigacao-e-proposta.md), incluindo
as classes por setor; ele não substitui o gate cego de liberação.

Orçamento sugerido para essa futura rodada: até **92 chamadas novas**, **12
aquisições** e **1.800 s de sessões**, com 180 s/3,3 GiB por operação e reserva
durável antes de operar. Partir de **1.710 / 256 / 35.417,71711680302 s**,
sem zerar contadores: tetos cumulativos **1.802 / 268 / 37.217,71711680302 s**.
Pesos/runtime/CPU/seed/temperatura, saída64 tokens, limites visuais e inputs
ficam iguais; o novo JSON deve caber no limite e ser testado sem inferência
antes da execução. Sem instalação, NIM ou mudança de serviço/MCP.

Se passar o desenvolvimento, propor separadamente outra auditoria cega com
candidato congelado, exclusão dos casos/canais revelados e análise pré-declarada
de suficiência de classes. Manter o
[gate original](issue-4-vlm-revisao-perceptiva-protocolo.md), sem reposição após
respostas ou aprovação administrativa. Produto sozinho não libera o VLM:
pessoa/texto ainda têm erros e ambiente/formato continuam pendentes. Nenhuma
etapa desta proposta inicia B/C ou promove M1.

## Preservação e verificação desta unidade

Os **862 arquivos protegidos** conferem antes/depois, incluindo os 735 herdados,
seis fontes/testes/protocolo da v10, seus resultados, reservas, respostas,
checkpoint e recibos de verificação. O plano e a fila continuam idênticos,
selados em `v10_preserved_quality_failed`. Os oito PNGs não foram alterados,
movidos ou removidos. Partições203/66/31, teste reservado fechado, M1/A200,
A300, B-cache e serviço/MCP preservados. README não rastreado não foi lido,
editado ou versionado.

A única mudança versionada é este documento. Não houve mudança de código ou
dependências; não se atribui nova suíte de testes à análise. Foram verificados
44 recibos, 32 crops em memória, derivação dos resultados, relações por canal,
hashes, links e diff. Revisão local de evidência/escopo, sem nova auditoria cega
ou revisão independente. Recibos privados em
`data/private/issue-4-vlm-v10-erros-diagnostico-v1/`.

Referências adicionais: [protocolo v10](issue-4-vlm-v10-protocolo.md),
[rubrica e contrato v9](issue-4-vlm-produto-v9-protocolo.md) e
[comparação v9 selada de 41 casos](issue-4-vlm-produto-v9-adendo-limitado-resultados.md).

# Pós-v11 — alucinação nos controles e próxima correção proposta

Investigação de 20/10/2026, limitada a controles e casos de treino já revelados.
A v11 produziu **11 positivos sem suporte em 12 controles negativos**. Produto
e pista foram gerados juntos, de forma coerente entre si, mas incompatível com
os pixels. Não foi encontrado erro de parser, agregação ou identidade dos inputs.
**A causa interna da regressão ainda não está isolada.**

A recomendação é uma **v12 de contraste de instruções, mantendo o schema v11
fixo**: testar separadamente a ordem das definições e a restauração de exemplos
completos. Evitar outra reescrita conjunta de prompt/schema, que repetiria a
confusão de fatores. Este documento propõe a etapa; não implementa extrator,
seleciona candidato ou autoriza chamadas. A investigação fez zero inferências,
aquisições, treino ou seleção de auditoria. A fila v11 continua selada.

## Reconstrução e evidência visual disponível

Reconstruímos **84 resultados de controles / 108 recibos nativos existentes**:
v8, quatro variantes v9, v10 e v11, nos mesmos 12 inputs. Hashes dos PNGs,
tempos e manifestos do modelo são idênticos entre os comparadores. Os parsers
e agregações reproduzem os valores registrados. A linhagem foi carregada em
leitura com as guardas do teste dos dois manifestos ativas.

Os controles foram reproduzidos temporariamente com a receita anterior e seus
hashes, sem modificar pixels ou adicionar outra amostra. Os oito de texto
contêm apenas **ABC123**, com tamanho, posição e tom diferentes; não contêm
referência comercial, instrução ou nome de produto. O branco tem somente
RGB(255,255,255), o preto somente RGB(0,0,0), ambos com 320×330 pixels. Linhas
e formas são desenhos geométricos simples. Não há peça, pessoa, mão ou produto
que sustente as pistas positivas emitidas.

Na v11, oito respostas são byte a byte iguais: garment com `held_display`.
Outras duas são garment com `worn_detail_focus`; uma é cosmetic/accessory com
`held_display`. Só o preto recebeu `no_target`/categorias vazias/`absent`.
Não houve `uncertain` ou `incidental_only`. Todas as respostas são JSON completo
e formalmente consistente. Oito variações de texto não são oito vídeos
independentes; esses resultados não estimam especificidade populacional.

Também reconferimos os oito vídeos preservados: 32 recibos v10 e 32 crops
reproduzidos somente em memória, com hashes/tempos iguais. A v10 mantém 5/8
acertos compostos, em cinco canais; os três erros vêm de dois canais.
**V11 tem zero vídeos avaliados.** Não atribuir a ela melhora ou piora dos três
erros reais, nem usar os controles para certificar reconhecimento de roupa.

## O que mudou entre v10 e v11

| Fator | v10 | v11 | O que permite concluir |
| --- | --- | --- | --- |
| Primeira definição na prosa | `no_target` | `presented_target`, seguida da descrição das quatro pistas positivas | Mudou a organização da instrução; saliência ou efeito de ordem são hipóteses, não causas medidas. |
| Exemplos JSON no prompt | Quatro, com ausência/incidentalidade antes do positivo e unknown ao final | Nenhum | Foi removido o exemplo explícito de cada ramo, ao mesmo tempo que se exigiu outro campo. |
| Schema de saída | Estado e categorias | Mesmos estado/categorias, mais pista obrigatória | Mudou o contrato conjunto de geração. A necessidade do novo campo não foi isolada da mudança textual. |
| Enum dos estados no schema | Ausente, incidental, apresentado, incerto | **Mesma ordem e mesmos valores** | O schema não passou a listar o estado positivo primeiro. |
| Ordem das chaves nas 12 respostas v11 | Não aplicável à pista | `state`, `presented_categories`, `presentation_cue` | A pista foi emitida na mesma resposta, depois da classificação; não é verificação independente. |
| Limites/inputs/modelo | Saída 64, mesmos PNGs/tempos, pesos e adaptador | Iguais | Não foi identificada troca de imagem, peso, resolução solicitada ou orçamento de saída. |

A redação das definições também foi reescrita; não houve somente permutação.
O contraste proposto controla dois fatores dentro do texto v11, sem prometer
decompor toda a diferença v10→v11.

O prompt passou de 2.016 para 1.948 caracteres. Não há evidência de que um
simples excesso de comprimento explique a regressão. Os valores também não
foram extraídos de exemplos pelo adaptador: ele entrega stdout/stderr completos
ao parser estrito, sem procurar um JSON favorável no texto. Os raw preservados
são objetos únicos, não transcrições do prompt. Isso não exclui o modelo copiar
um padrão de resposta; distingue essa possibilidade de um erro de extração.

O código usa um processo local novo por chamada, com o PNG e o prompt daquela
operação; não mantém conversa entre controles. Os hashes antes/depois do
dispatch conferiram. Isso não mede atenção, logits ou uso efetivo da imagem
pelo modelo: esses diagnósticos internos não foram coletados. Não atribuir a
falha a perda de atenção visual, quantização ou algum token específico.

## Por que a pista não protegeu a decisão

O contrato exige categoria não vazia e pista positiva quando o estado é
`presented_target`. Na v11, o modelo declarou essas três partes juntas.
O enum restringe o vocabulário e o parser verifica compatibilidade lógica;
nenhum deles verifica se existe uma mão, uma peça ou seu detalhe nos pixels.
Assim, `presented_target` + garment + `held_display` pode ser válido no contrato
e falso na imagem. O quadro branco demonstra exatamente esse caso.

O schema permite ausência; o parser aceita esse ramo e o próprio controle
preto o utilizou. Portanto **não houve obrigação de responder true**. Tampouco
há evidência de truncamento nas 12 respostas completas. Tornar as combinações
mais restritas por schema, sem uma melhora perceptiva, não validaria os onze
positivos: eles já satisfazem as restrições atuais.

A hipótese principal é que a nova organização positiva da instrução, junto
da remoção dos exemplos de ausência e do contrato com pista, favoreceu um
padrão de item apresentado sem ancoragem suficiente na imagem. O predomínio
de uma resposta idêntica é compatível com essa hipótese, mas não identifica
qual fator causou a mudança. A ordem das pistas no enum também pode ser uma
interação; ela ficará fixa no contraste proposto, sem alegar seu isolamento.

## O que os contrastes antigos já mostram

| Versão / mesmos 12 controles | false correto | true | unknown |
| --- | ---: | ---: | ---: |
| v8 | 0 | 5 | 7 |
| v9 `enum_false_first` | 0 | 5 | 7 |
| v9 `examples_false_first` | 3 | 2 | 7 |
| v9 `neutral_key` | 0 | 1 | 11 |
| v9 estruturada | 12 | 0 | 0 |
| v10 | 12 | 0 | 0 |
| v11 | 1 | 11 | 0 |

Na v9, trocar somente a ordem do enum booleano manteve os 12 valores por input
da v8, não apenas seus totais;
trocar a ordem dos exemplos binários produziu alguns negativos, mas ficou
longe dos 12/12. Renomear a chave aumentou abstenções. O contrato estruturado
anterior preservou ausência, mas não resolveu apresentação de roupa vestida.
Esses contrastes não equivalem ao teste dos fatores textuais dentro do schema
v11. Impedem prometer que reordenar alternativas, sozinho, corrigirá a percepção.

## Próxima correção: contraste v12 com schema fixo

| Abordagem | Benefício | Limite / recomendação |
| --- | --- | --- |
| Reordenar apenas a v11 | Menor mudança, até 12 chamadas de controle | Não separa a contribuição dos exemplos ou sua interação. |
| **Contraste 2×2 de ordem e bloco de exemplos** | Mantém o schema e as regras visuais, distinguindo duas mudanças textuais verificáveis | Recomendado: três variantes novas e referência v11 em cache; acrescenta 24 chamadas frente a uma única variante. |
| Retirar a pista ou movê-la para outra chamada | Pode separar classificação de descrição auxiliar | Mudaria novamente contrato/prompt e não recupera, por si, os três erros v10; adiar essa ablação. |

Os rascunhos usam o prompt v11 integral e apenas duas operações textuais:

- **R:** mover os blocos de definições para a ordem `no_target`,
  `incidental_only`, `presented_target`, `uncertain`. Intro, texto dentro dos
  blocos e instrução de saída ficam idênticos; mesmas palavras/caracteres,
  sem inserir outra regra de reconhecimento.
- **E:** acrescentar, imediatamente antes de `No explanations.`, os quatro
  exemplos completos abaixo, com introdução literal `Examples:` e um espaço.
  Separar os objetos compactos por `; ` e terminar o bloco com ponto e espaço.
  O bloco tem ordem fixa em ambas as variantes que o usam. Ele é o fator testado inteiro;
  não se atribuirá um resultado a uma palavra particular de seu conteúdo.

```json
{"state":"no_target","presented_categories":[],"presentation_cue":"absent"}
{"state":"incidental_only","presented_categories":[],"presentation_cue":"incidental"}
{"state":"presented_target","presented_categories":["cosmetic"],"presentation_cue":"held_display"}
{"state":"uncertain","presented_categories":[],"presentation_cue":"uncertain"}
```

Os exemplos são de estrutura/estados possíveis, não rótulos dos controles.
O schema, ordem de seus enums, categorias, pistas, parser, mapper, OR e janela
≤3 s continuam os da v11 em todas as células. Não combinar prompt de três
campos com schema de dois: esse contraste introduziria uma incompatibilidade.

| Célula | Ordem das definições | Exemplos | Execução proposta |
| --- | --- | --- | --- |
| Referência v11 | Positivo primeiro | Não | Reusar os 12 resultados congelados; sem repetir chamadas. |
| v12-R | Ausência primeiro | Não | 12 controles idênticos. |
| v12-E | Positivo primeiro | Sim | 12 controles idênticos. |
| v12-RE | Ausência primeiro | Sim | 12 controles idênticos. |

R e RE conservam a ordem negativa antes do positivo que existia na prosa v10;
E e RE recuperam a cobertura explícita dos quatro ramos de JSON. Há rascunhos
textuais privados, sem implementação ou geração. Verificamos que R só muda
ordem, que E só acrescenta seu bloco, e que os quatro exemplos passam no parser
v11. Isso não verifica sua qualidade perceptiva. Não há candidato selecionado.

Comparações R/referência e RE/E avaliam a troca de ordem; E/referência e RE/R,
o bloco de exemplos. A referência em cache não é replicação simultânea ou
estimativa de variância. Mesmo com resultado favorável, a conclusão ficará
restrita aos contrastes de instrução nesses controles, sem afirmar mecanismo
interno ou generalização. O schema permanece fixo; seu efeito isolado não será
medido por essa etapa.

## Plano operacional proposto antes de outra auditoria

Outra autorização deve cobrir implementação/protocolo/execução próprios. Não
reabrir a v11 ou consumir seu saldo de 80 chamadas. Congelar os três prompts,
ordem de execução R→E→RE, schema, fontes, painel e recibos antes de operar;
commitar código/testes/protocolo verificados antes das chamadas.

1. **Até 36 chamadas, zero aquisição:** executar os três blocos fixos de 12
   controles, sem retuning. Concluir a matriz mesmo se um candidato falhar
   perceptivamente, pois os contrastes estão pré-declarados. Qualquer falha
   operacional/JSON/identidade interrompe tudo, sem seleção por matriz parcial,
   reparo, retry ou fallback. Preservar os resultados parciais como diagnóstico.
2. Qualificar apenas candidatos com 12/12 false. Se nenhum passar, encerrar.
   Em empate, selecionar **R, depois E, depois RE**, nessa prioridade fixa de
   menor conjunto de mudanças. Não usar views, rótulos de alcance ou teste.
3. **Até 32 chamadas, zero aquisição:** executar somente o selecionado nos
   mesmos quatro crops das oito folhas preservadas. Exigir 8/8 valores+frames
   antigos e suporte visual de todas as pistas/categorias positivas, usando
   a inspeção prévia e recibo de revisão vinculado. Unknown ou ambiguidade não
   contam como recuperação. Falha encerra; não experimentar o segundo colocado.
4. Somente com ambas as verificações aprovadas, **até 48 chamadas/12
   reaquisições** nos oito negativos e quatro positivos de beleza já fixados
   no painel v10. Mesmos pixels/propriedades/tempos, sem substituição. Revisar
   pistas antes do descarte das novas folhas; manter as oito antigas. Aplicar
   o critério descritivo do [protocolo v11](issue-4-vlm-v11-protocolo.md), sem
   confundi-lo com liberação pelo gate cego original.

Teto proposto: **116 chamadas novas, 12 aquisições e 2.400 s de sessões**;
cumulativos máximos **1.838 / 268 / 37.964,65692200101 s**, partindo dos
**1.722 / 256 / 35.564,65692200101 s** selados. São 24 chamadas de controle a
mais que o protocolo de uma variante e um teto novo de 40 minutos. Nenhum
desses limites foi consumido ou aprovado operacionalmente nesta investigação.
Manter 180 s/3,3 GiB por operação, reserva durável, prazo compartilhado,
tentativa incerta consumida e contadores herdados sem reinicialização.

Mesmo candidato que passar o desenvolvimento não está aprovado. Outra
auditoria exige protocolo separado, candidato congelado, exclusão dos casos/
canais revelados e suficiência de classes pré-declarada, com o
[gate original](issue-4-vlm-revisao-perceptiva-protocolo.md). Pessoa/texto ainda
têm pendências e ambiente/formato não foram retomados. Não iniciar B/C com
VLM, promover modelo ou reduzir o escopo para C-cache por este documento.

## Preservação e verificação desta investigação

Os **926 arquivos protegidos** conferem antes/depois, incluindo fontes,
protocolos, resultados, reservas e recibos v11, filas anteriores, oito PNGs,
M1/A200, A300, B-cache e serviço/MCP. Partições 203/66/31 e teste reservado
preservados, sem features/rótulos/previsões/métricas do teste. Anotações antigas
imutáveis; as reproduções temporárias dos controles foram removidas e nenhum
crop novo ficou salvo. Não houve instalação, inferência externa, mudança de
ambiente ou seleção nova. README não rastreado não foi lido, editado ou versionado.

A única mudança versionada é este relatório. Verificações: reconstrução dos
84 resultados/108 recibos de controles, 32 recibos v10 dos casos revelados,
hashes de 32 crops em memória, invariantes dos rascunhos, exemplos no parser,
pins, links e diff. Não houve mudança de código ou nova suíte; os 876 testes
da unidade anterior não são apresentados como uma nova execução nesta análise.
Revisão local de evidências/escopo, sem nova auditoria ou revisão independente.

Recibos privados em `data/private/issue-4-vlm-v11-alucinacoes-diagnostico-v1/`.
Referências: [resultado v11](https://github.com/leeunam/case-GALAXIES-IA/blob/0df616e5fd64dfc4947abde583f2664b66abf410/docs/issue-4-vlm-v11-resultados.md),
[resultado v10](https://github.com/leeunam/case-GALAXIES-IA/blob/0df616e5fd64dfc4947abde583f2664b66abf410/docs/issue-4-vlm-v10-resultados.md),
[contrastes v9](issue-4-vlm-produto-v9-protocolo.md) e
[investigação anterior](issue-4-vlm-pos-v10-investigacao-e-proposta.md).

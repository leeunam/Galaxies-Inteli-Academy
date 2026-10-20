# Produto VLM: diagnóstico do true em 64/64 e próxima correção

Investigação de 19/10/2026, após `efe151d`, usando somente recibos dos
64 casos de treino já revelados e dos 12 controles sintéticos já executados.
**O colapso nasce nas respostas por frame: a v8 deixou de emitir false para
produto. O OR propaga essa tendência; não a cria.** A causa exata dentro do
modelo/prompt ainda não foi isolada. A recomendação abaixo é uma hipótese de
desenvolvimento, não uma correção implementada ou validada.

Não houve download, chamada nativa, nova inspeção de imagens, ajuste de pesos,
seleção de auditoria ou treino B-VLM. Permanecem as partições 203/66/31, M1,
comparadores, serviço/MCP, fontes e rodadas seladas. O teste reservado ficou
fechado; não foram abertos views, títulos, transcrições ou rótulos preditivos.

## Reconstrução da falha

Reverificamos respostas brutas → JSON estrito → valores por frame → agregação,
com a guarda de acesso ao teste. A referência é a
[comparação v8 encerrada](issue-4-vlm-v8-resultados.md), com os mesmos pixels,
tempos e anotações assistidas imutáveis. As folhas já foram descartadas e não
foram reobtidas: não atribuímos visualmente cada erro a uma roupa ou objeto.

Há 640 saídas arquivadas de produto: A/v7 nos 256 frames dos 64 vídeos, B/v7
nos 128 frames dos 32 antigos e v8 nos mesmos 256 frames. São 256 posições
distintas de caso/frame, com repetição entre versões, sem independência entre
frames ou canais. Os 12 controles sintéticos são apresentados separadamente.

| Versão / casos | Frames ≤3 s: true / false / unknown | Frames tardios: true / false / unknown | Vídeos true / false / unknown |
| --- | ---: | ---: | ---: |
| A/v7, 64 | 155 / 37 / 0 | 61 / 3 / 0 | 57 / 7 / 0 |
| B/v7, 32 antigos | 92 / 4 / 0 | 31 / 1 / 0 | 32 / 0 / 0 |
| v8, 64 | **180 / 0 / 12** | 61 / 0 / 3 | **64 / 0 / 0** |

Dos 64 vídeos v8, 55 têm os três frames elegíveis true; seis têm dois true
e três têm um true. Cada vídeo possui pelo menos um true antes de 3 s.
Os 61 true tardios são corretamente excluídos; não há vazamento do frame tardio.
No total dos 256 frames, são 241 true, 15 unknown e zero false.

O parser não transforma strings em booleanos nem corrige respostas: usa JSON
estrito. A agregação testa `is True`, portanto a string unknown não vira
presença por ser uma string não vazia. Os hashes e a reconstrução dos recibos
confirmam que os true já estavam nas saídas brutas das chamadas de produto.
Fontes preservadas: [parser/agregação](../scripts/vlm_per_frame.py) e
[extrator v8](../scripts/vlm_explicit_presence.py).

Nos 32 antigos, A/v7 → B/v7 mudou 15 dos 19 frames false elegíveis para true;
os outros quatro continuaram false. A/v7 → v8, nos 64, mudou seus 37 false
para 31 true e seis unknown. Os quatro false de B/v7 também viraram true na
v8. Portanto, a positividade total por vídeo antecede a v8; não pode ser
atribuída exclusivamente aos exemplos JSON introduzidos nela.

## Ausência perdida e evidência excedente

| Evidência explicitamente anotada, ≤3 s | A/v7 true / false / unknown | v8 true / false / unknown |
| --- | ---: | ---: |
| 158 frames positivos | 142 / 16 / 0 | 152 / 0 / 6 |
| 24 frames negativos | 9 / 15 / 0 | **20 / 0 / 4** |

Os dez frames elegíveis não citados na anotação não são tratados como negativos.
Na v8, eles tiveram oito true e dois unknown. Esses oito true excedentes
aparecem em seis vídeos positivos, prejudicando a evidência citada.

Os rótulos dos vídeos têm 56 positivos e oito negativos de produto; os negativos
são três dos antigos e cinco dos revelados, seis de beleza e dois de moda.
Na v8 há 56 verdadeiros positivos, oito falsos positivos, zero verdadeiros
negativos e zero falsos negativos de valor. A sensibilidade foi 56/56, mas a
especificidade foi **0/8**, contra 4/8 na A/v7. Responder sempre true já rende
87,5% de acerto de valor nessa amostra. Isso não demonstra discriminação;
o VLM não foi treinado ou ajustado nesses rótulos para produzir esse padrão.

O acerto completo cai a 50/64: oito erros de valor e outros seis com valor
correto, mas frames excedentes. A métrica de índices sem suporte conta apenas
subconjuntos de frames: os índices dos oito negativos podem coincidir com os
da anotação de **ausência**, sem sustentar presença. Por isso, os seis casos
de índices sem suporte não devem ser confundidos com o total de erros.

## O que as evidências permitem concluir

- **Falha de decisão por frame, confirmada.** Nos 12 controles sem produto,
  houve cinco true e sete unknown, nenhum false. Linhas e formas foram true;
  branco e preto foram unknown. Três imagens contendo somente texto também
  foram true. Os erros não dependem apenas de roupas reais ou objetos pequenos.
- **Schema não proíbe false.** B/v7 e v8 usam exatamente o mesmo schema de
  produto e limite de 64 tokens de saída; B/v7 emitiu false. O hash lógico
  desse schema é `5963121d27a8f89c90e32eee1626811b9b42668eed7416955601f20a55ef5dda`.
  Isso não isola o efeito da ordem das alternativas sob outro prompt.
- **Formulação e contexto da pergunta são suspeitos.** B/v7 individual já
  saturava os 32 antigos, enquanto A/v7 conjunto conservava negativos. A/B
  também diferem no esquema conjunto e limite 96/64 de saída; não isolam uma
  frase. V8 mudou outras instruções e exemplos simultaneamente.
- **Ausência e apresentação continuam semanticamente difíceis.** A pergunta
  reúne cosmético, aplicador, roupa, acessório e diversos modos de uso/exposição
  numa resposta booleana. É plausível que a presença incidental seja confundida
  com apresentação; os recibos não demonstram essa causa em cada caso. Negativo
  do atributo não significa necessariamente que não exista objeto na imagem.
- **Não há histórico conversacional entre perguntas.** Cada chamada inicia
  outro subprocesso do runtime. A pessoa da chamada anterior não fornece um
  contexto de conversa à pergunta de produto. Viés do nome do campo, ordem dos
  exemplos/enum e limitação perceptiva continuam hipóteses não separadas.
- **Mais pixels não é a primeira resposta ao colapso.** Detalhe reduzido pode
  prejudicar objetos reais, mas não explica sozinho falhar em formas e fundos
  sintéticos. Não se mediram logits ou tokens visuais efetivos; não se atribui
  o padrão à quantização, resolução ou a um mecanismo interno específico.

Trocar OR por votação não resolve a decisão por frame. Uma contagem descritiva,
sem implementar outro agregador, dá:

| Quantidade mínima de frames true | Positivos anotados ainda aceitos / 56 | Negativos ainda aceitos / 8 |
| --- | ---: | ---: |
| Um, regra atual | 56 | 8 |
| Dois | 54 | 7 |
| Três | 50 | 5 |

Não aceito nessa simulação significa somente não atingir a contagem; não
significa ausência confirmada. Alterar o limiar perderia positivos sem eliminar
a maioria dos falsos positivos e mudaria o protocolo. A regra original fica.

## Correção recomendada: item e apresentação ligados à mesma evidência

Recomendo uma versão de desenvolvimento **somente para produto**, mantendo
os pixels, tempos, pesos e cache de pessoa/texto. Em vez de pedir diretamente
o booleano final, pedir um estado visual curto e categorias que testemunhem
uma apresentação observável. Os estados propostos são:

| Estado por frame | Significado preservando a rubrica | Mapeamento final |
| --- | --- | --- |
| presented_target | Existe pelo menos um cosmético, aplicador, roupa ou acessório apresentado: exposto, erguido, disposto ou visivelmente em uso segundo a rubrica atual | true |
| incidental_only | Todos os alvos visíveis são inequivocamente incidentais; nenhuma outra apresentação ou alvo ambíguo | false |
| no_target | Nenhum objeto das categorias-alvo visível, após inspecionar a imagem | false |
| uncertain | Não é possível concluir presença/apresentação ou ausência | unknown |

O JSON pode conter `state` e uma lista curta `presented_categories`, com as
quatro categorias permitidas, sem duplicatas. presented_target exige ao menos
uma categoria de item efetivamente apresentado; os outros estados têm lista
vazia. Categoria e apresentação devem se referir ao **mesmo item**. Se há roupa
incidental e cosmético apresentado, o estado é presented_target; vários itens
apresentados podem contribuir categorias, sem escolher apenas um objeto
incidental e ignorar os demais. Um apresentado confirmado basta, mesmo que
outro seja ambíguo. Sem apresentado confirmado, qualquer alvo ambíguo impede
incidental_only e leva a uncertain. Não exigir marca, OCR, intenção de venda,
compra ou movimento inferido de outro frame.

Esse desenho explicita as condições de objeto-alvo e apresentação, sem um AND
global que combine objeto de uma região com ação de outro item. O mapper é
determinístico; contradições de contrato são preservadas e rejeitadas, sem
reparo automático. O OR entre frames, false somente com todos os elegíveis
false, janela ≤3 s e gate original continuam iguais. As subcategorias seriam
somente diagnóstico privado, não novas colunas de treino.

As anotações atuais rotulam apenas o atributo composto e seus frames. Não
permitem afirmar que classe do objeto ou estado intermediário estão corretos.
Somente o atributo final pode ser pontuado contra o GT fixo. Avaliar subdecisões
exigiria anotação de desenvolvimento separada dos mesmos pixels, anterior às
novas respostas, sem alterar a anotação composta preservada.

Uma instrução booleana curta e equilibrada é alternativa de menor mudança,
mas pode apenas trocar a preferência de resposta. Reusar A/v7 é um comparador
útil, não solução aprovada: ainda tem quatro falsos positivos, três falsos
negativos e falha no gate. Aumentar resolução ou trocar modelo fica para uma
ablação separada se a decisão semântica continuar falhando; não misturar as
mudanças nem consumir outra auditoria para escolher entre elas.

## Desenvolvimento proposto antes de outra auditoria

1. Fixar nova fila/protocolo, candidatos, orçamento cumulativo e regras de parada,
   mantendo as filas antigas seladas. Ponto de partida: 182 aquisições,
   1.453 chamadas v7+diagnósticos+v8 e 15.159,68 s de sessões. Tetos antigos
   não são autorização para reabrir filas ou reiniciar contadores.
2. Usar os mesmos 12 controles reconstruídos e verificar seus hashes contra
   v8. Comparar o cache v8 com quatro variantes predefinidas: somente inverter
   a ordem do enum; somente inverter a ordem dos exemplos; somente trocar a
   chave para uma neutra com mapeamento explícito; e a decomposição proposta.
   São até **48 chamadas novas**, sem retry ou ajustes após observar saídas.
   Registrar exatamente cada contraste: chave também muda nos exemplos/schema;
   as demais partes devem permanecer iguais nas ablações individuais.
3. Esses controles são todos negativos: servem para diagnóstico e interrupção
   por incapacidade evidente de reconhecer ausência, não para escolher candidato
   ou provar recall. A decomposição deve ser especificada antes das chamadas.
   Não executar os 64 se ela continua sem rejeitar fundos/linhas/formas/texto
   sem produto; unknown não conta como ausência correta nesses controles.
4. Planejar um piloto dos **oito negativos já revelados e oito positivos**
   predefinidos desses mesmos 64 para a única correção especificada. Os positivos
   devem ter dois casos por origem×setor, escolhidos por hash/seed fixado antes
   das chamadas, sem usar acerto das versões anteriores. São 16 casos, não
   amostra cega nem balanceada por setor: dez de beleza e seis de moda, pois
   os negativos disponíveis são seis de beleza e dois de moda. Não criar
   exemplos novos ou escolher apenas frames que favoreçam a correção.
5. Se o piloto permitir continuar sem ajustes, completar os outros 48 e relatar
   piloto, demais 48, total64, origens/setores, ambas as classes, cobertura,
   valor+frames e erros. Todos os 64 já informaram o diagnóstico: os 48 restantes
   **também não são holdout independente**. Reaplicar o gate original somente
   como prontidão descritiva, sem liberar treino ou afirmar generalização.
6. Reaquisições futuras exigem orçamento próprio e a mesma identidade de
   pixels/tempos; nenhum caso indisponível é substituído. Uma chamada por frame
   dá até 256 chamadas de produto nos 64, mais os controles, com pessoa/texto
   em cache. Proposta de teto: **304 chamadas novas** (48+256), elevando esse
   contador a 1.757; **256 aquisições cumulativas** (182+64+até10 repetições
   DNS tipadas, no máximo uma por ID, após limpeza e DNS positivo). Isso é
   proposta para outra fila, não ampliação do orçamento das filas seladas.
   Carregar custos anteriores, manter um executor, limites de
   180 s/3,3 GiB e 27 h cumulativas, guardar falhas e descartar mídia por sessão.
   Se parar, preservar o resultado negativo; não iniciar automaticamente outra
   correção, resolução ou troca de pesos.

Somente após esse desenvolvimento caberia propor outra auditoria com protocolo
próprio, excluindo os 64 casos/56 canais já revelados, sem usar validação/teste
para completar amostra. Nenhuma dessas etapas foi executada nesta investigação.

## Verificação e recibos

A revisão independente somente leitura reproduziu as respostas e contagens e
conferiu **116 hashes**: 105 arquivos congelados no fechamento v8, seus dez
recibos e o próprio recibo final. Tudo permaneceu igual; zero aquisições ou
chamadas novas. Não restam imagens retidas ou sessões temporárias. Não houve mudança de
código que exigisse repetir a suíte de 567 testes da implementação congelada.
Esta unidade verifica reconstrução, comparações pareadas, hashes, isolamento,
contagens, links e diff; não atribui novas inferências à suíte antiga.

Artefatos privados: `data/private/issue-4-vlm-produto-diagnostico-20261019/`:
plano, análise por caso/frame, contrastes, comparação de schemas e verificação.
Hash lógico da análise:
`dae0e1249664846cd82f6bf81095c3afaa7e17f9b1ce95e72919f8b6d43b7da3`.
O recibo final v8 preservado é
`c4442234cf5c309a78065a5c893195c1a6a4436fd1236709d52b1a620cdcbfe2`.
Hash do recibo final desta investigação:
`6a76c1483b94ef0c3d761a97b54c54c08060be70441d9f098b1d6089100ea485`.

O diagnóstico recomenda corrigir a decisão visual antes de outra auditoria;
não muda a rubrica, as anotações, o gate ou a conclusão de que B-VLM segue
sem atributos liberados. Partições, teste reservado e M1 permanecem preservados.

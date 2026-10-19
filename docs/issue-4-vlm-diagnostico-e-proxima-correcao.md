# Falhas restantes do VLM e próxima correção proposta

Investigação de 19/10/2026, após `e28c1ca`. É diagnóstico da
[auditoria já revelada](issue-4-vlm-revisao-perceptiva-resultados.md) e proposta
de desenvolvimento. Não implementa outra versão, não inicia auditoria nova,
não libera atributos e não retoma B-VLM. Permanecem as partições 203/66/31,
o teste reservado, M1, B-cache/A300/A200, serviço/MCP e as fontes congeladas.

## O que foi examinado

Reverificamos os recibos, respostas brutas, parser, agregação e anotações fixadas
da revisão v7, sob a guarda de acesso ao teste. Foram 128 frames do candidato A
e 128 de B no desenvolvimento antigo, mais 128 de A na auditoria revelada.
São 384 saídas para 256 posições de caso/frame em 64 vídeos: os mesmos 128
frames antigos foram avaliados pelos dois candidatos. Isso não representa
384 imagens distintas nem observações independentes; frames do mesmo vídeo
também são correlacionados.
Não foram abertos rótulos de alcance, títulos ou transcrições. As 64 folhas
reais já foram descartadas e não foram reobtidas: não há nova inspeção visual
dos erros nesta investigação. As conclusões visuais dependem da anotação
assistida preservada e da revisão anterior; não constituem verdade certificada.

Detalhes por caso ficam em artefato privado separado. Contagens por frame abaixo
usam apenas índices explicitamente anotados como evidência de presença ou
ausência. Um índice não citado não é automaticamente tratado como negativo.

| Campo na auditoria revelada | Frames anotados como presentes | Frames anotados como ausentes | Falha observada |
| --- | --- | --- | --- |
| Pessoa | 115: 112 true, 3 false | 8: todos false | Três perdas por frame; uma muda o valor do vídeo |
| Produto até 3 s | 77: 70 true, 7 false | 15: 6 true, 9 false | Excesso de presença e perdas reais; evidência temporal supercitada |
| Texto | 95: 88 unknown, 7 false, zero true | 24: todos false | Presença não reconhecida, antes da agregação |

### Pessoa: a média por vídeo esconde perdas por frame

No único vídeo reprovado, a anotação indica presença somente no frame 4,
aos 35,720 s. O modelo respondeu false nos quatro frames e, corretamente
segundo a regra de agregação, produziu false com referências 1–4. É uma perda
do reconhecimento daquele frame, sem evidência de erro de índices ou filtro
temporal. Pessoa não está limitada aos primeiros 3 s.

Há outras duas perdas em frames explicitamente positivos de vídeos que ainda
possuem outro frame true; o OR preserva a presença desses vídeos. Por isso,
31/32 acertos por vídeo não significa reconhecimento perfeito dos frames.
Os recibos não permitem afirmar que o motivo foi mão pequena, oclusão ou outra
aparência específica. Esses são itens para uma revisão visual de desenvolvimento,
caso as imagens sejam reobtidas sob novo orçamento.

### Produto: presença de objeto não resolve apresentação

Os quatro desacordos de valor são três falsos positivos e um falso negativo.
Em um falso positivo de moda, apenas o frame 2 é true: o OR transforma essa
resposta isolada em presença no vídeo. No falso negativo de moda, os três
frames elegíveis, 0,203/1,488/2,806 s, são false; o frame tardio, 33,809 s, é
true e foi corretamente excluído da regra de produto inicial.

Um quinto caso tem valor true correto, mas cita os frames 1–3 quando a anotação
sustenta somente o primeiro, aos 0,208 s. A supercitação nasce nas respostas
por frame e é propagada pela agregação; não é um deslocamento de timestamp.

A instrução atual pede um objeto como item de interesse e também proíbe inferir
intenção. Isso deixa uma tarefa semântica difícil: distinguir produto apresentado
de roupa incidental e de objeto apenas associado à cena. Essa ambiguidade é
uma hipótese sustentada pelo contrato e pelos falsos positivos; sem as imagens,
não é possível atribuir cada erro a roupa, embalagem ou aplicador específico.

### Texto: colapso de presença, anterior ao OR

Em **384 respostas por frame**, não houve um único screen_text=true:

| Conjunto | true | false | unknown |
| --- | ---: | ---: | ---: |
| Desenvolvimento A | 0 | 42 | 86 |
| Desenvolvimento B, pergunta individual | 0 | 11 | 117 |
| Auditoria A revelada | 0 | 38 | 90 |

O parser preserva exatamente esses valores das respostas brutas. O agregador
retorna true quando qualquer frame elegível é true; como nenhum o é, ele não
tem presença para recuperar. Na auditoria, isso produz 25 vídeos unknown e
sete false, incluindo um falso negativo. Trocar unknown por false ou escolher
outro frame depois de ver a anotação apenas esconderia a falha. Separar as
perguntas, sozinho, tampouco resolveu: B antigo teve mais abstenções.

## Controle sintético: schema válido e prompt inadequado

Executamos nove chamadas locais, pré-declaradas em pasta privada distinta da
rodada selada, com os mesmos pesos, runtime, CPU com 4 threads e limite visual de 128 tokens. Não houve
download, mídia real ou inferência de novos casos da coorte. Os dois controles
foram PNGs RGB de 320×330: fundo branco e o mesmo fundo com ABC/123 em preto,
fonte DejaVu Sans Bold de 64 pixels. São exemplos artificiais fáceis, não nova auditoria.

Três chamadas pediram apenas copiar JSON com true, false e unknown. Todas
emitiram o valor solicitado e passaram no parser, demonstrando que true não
está bloqueado pelo schema/runtime nessa configuração. Não medem percepção.

As seis chamadas restantes mantiveram imagem, pesos e schema; trocaram a
instrução conforme o plano:

| Instrução | Imagem com texto grande | Imagem vazia |
| --- | --- | --- |
| A original, três atributos | unknown | false |
| B original, só texto | unknown | unknown |
| Curta, presença e contrato JSON explícito | true | false |

A instrução curta pergunta se há letras/números, aceita presença mesmo sem
conseguir ler as palavras e descreve literalmente as três respostas JSON.
Ela substitui o conjunto de instruções; não isolamos qual expressão causava a
abstenção. Dois controles corretos não demonstram generalização para legendas,
embalagens, português, texto pequeno ou vídeos reais.

Há uma lacuna concreta no contrato anterior: ele manda retornar o objeto
exigido pelo schema sem apresentar literalmente sua estrutura. A documentação
do [llama.cpp b11716](https://github.com/ggml-org/llama.cpp/blob/b11716/grammars/README.md#json-schemas--gbnf)
explica que o schema restringe a geração e não é inserido no prompt. Isso
motiva explicitar a estrutura, sem concluir que toda falha decorra dessa lacuna.

## Pixels: segunda hipótese, não explicação suficiente

Todos os 32 vídeos da auditoria têm fonte 360×640. O extrator reduz primeiro o
frame para caber em 512×512, grava JPEG e depois o reduz para caber em 320×330.
O conteúdo vertical fica aproximadamente 186×330, dentro de um crop 320×330
com área branca. Isso limita o detalhe disponível de texto e objetos pequenos.

O erro com letras grandes sintéticas mostra que a redução não explica sozinha
o padrão observado. Aumentar apenas image_max_tokens, ou ampliar um crop já
reduzido, não recupera detalhe perdido. O
[processamento oficial Qwen3-VL](https://github.com/QwenLM/Qwen3-VL#new-qwen-vl-utils-usage)
relaciona resolução e orçamento visual; seus exemplos do processador HF não
devem ser tratados como configuração diretamente equivalente ao runtime GGUF.

O fonte local do runtime também contém um teto condicional: modelos de visão
com atenção não causal podem ter image_max_tokens limitado por n_ubatch.
Portanto, uma futura ablação de resolução precisa registrar dimensões/tokens
efetivos, além dos argumentos pedidos, e conferir batch/ubatch. Não medimos
nesta investigação quantos tokens o runtime efetivamente usou nos casos reais.

## Próxima correção recomendada, ainda não implementada

Recomendamos começar pelo contrato e pelas perguntas visuais, mantendo os
pixels e os tempos v7 para isolar esse efeito. Propor uma versão única v8,
com perguntas curtas por atributo e respostas booleanas/unknown explícitas:

- **Pessoa:** verificar face e partes humanas, incluindo mão/braço e corpo
  parcial, antes de declarar ausência. Manter os negativos de manequim, desenho
  e rosto impresso. Avaliar também as três perdas por frame, não só o 31/32.
- **Produto:** separar na instrução os critérios de objeto visível e de
  apresentação observável, com exemplos de embalagem/aplicador, peça exposta
  e roupa incidental. Não inferir intenção de campanha. Quando não for possível
  distinguir apresentação de uso incidental, permitir unknown. A rubrica
  aprovada permanece a referência; ambiguidades exigem registro, sem relabelar
  os recibos antigos para favorecer o novo extrator.
- **Texto:** usar a pergunta de presença de letras/números e o contrato de
  saída que responderam corretamente aos controles. Não exigir leitura nem
  transcrição para reconhecer presença. Preservar unknown para dúvida real.

A hipótese é sobre o novo conjunto de prompts; o sucesso do controle de texto
não valida os novos prompts de pessoa/produto. Perguntas individuais custam
até três vezes as chamadas de A; B antigo é evidência de que esse custo, por
si só, não garante ganho. Não alterar o contrato final de atributos de treino,
o parser estrito ou a política de evidências. Manter OR para presença, false
somente com todos os elegíveis false e produto somente até 3 s.

Uma segunda abordagem, caso os erros persistam, é comparar a mesma instrução
com frames na resolução da fonte 360×640, sem a redução/JPEG da folha, e teto
visual proposto de 512 tokens. Exige nova política de entrada, prova da identidade dos
tempos, novos hashes, anotação dos pixels efetivos e piloto de RSS/tempo antes
de ampliar. Não reaproveitar automaticamente a anotação de imagem reduzida
como verdade da imagem mais detalhada. O teto de 512 é uma hipótese de engenharia,
não resultado medido. Manter limite de 3,3 GiB/180 s e parar se não couber.

Trocar pesos ou adicionar detector/OCR é uma terceira abordagem, de maior
mudança de custo/contrato. Não é a primeira recomendação: o controle mostrou
uma correção de instrução promissora com o modelo já disponível. Nenhum peso,
serviço externo ou pacote foi trocado nesta investigação.

## Sequência antes de consumir outra amostra cega

1. Fixar novo protocolo de desenvolvimento e orçamento, carregando os custos
   anteriores, sem reabrir a fila v7. Usar os 64 casos de treino já revelados;
   a última auditoria passa a ser desenvolvimento, sem alegar independência.
2. Para reobter imagens, criar uma fila distinta e limitada, validar os hashes
   das folhas/tempos e limpar mídia por sessão. Não substituir caso indisponível.
   Se testar pixels nativos, registrar a nova entrada e revisar suas evidências.
3. Congelar os prompts antes das chamadas. Comparar com v7 em cache nos mesmos
   casos e relatar valor, evidência, cobertura, ambas as classes e cada setor.
   Antes dos casos reais, usar uma grade sintética fixada de texto grande e
   pequeno, alto e baixo contraste, centro e borda, além de negativos sem
   texto e com formas/linhas. O par ABC/123 atual já é desenvolvimento e não
   deve ser o único critério para escolher a nova formulação.
   Incluir controles negativos difíceis e o caso de pessoa presente em um só
   frame, sem selecionar apenas casos em que o novo método acerta.
4. Exigir que o desenvolvimento deixe de colapsar texto e satisfaça os critérios
   operacionais por campo pretendido. Se não, continuar diagnóstico ou encerrar
   o campo, sem nova auditoria para repetir uma falha conhecida. Não remover
   evidências erradas pela anotação nem aliviar o gate de 90%/zero sem suporte.
5. Só então congelar uma configuração inteira e selecionar 32 canais de treino,
   16 por setor, fora de todos os canais já revelados. O próximo amostrador deve
   excluir o histórico completo de 64 casos/56 canais; reutilizar a função v1,
   que excluía somente os 32 antigos, permitiria repetir a última auditoria.
   Não usar validação/teste para completar cota. Nova amostra, orçamento e anotações cegas devem preceder a
   auditoria, sem reposição após inspecionar classes ou resultados.

Uma contagem somente de metadados confirmou 42 vídeos/31 canais de beleza e
35 vídeos/28 canais de moda elegíveis após excluir IDs, canais e hashes de
mídia dos 64 casos revelados. Há canais compartilhados entre setores; a próxima
seleção deve assegurar 32 distintos no total. As contagens permitem planejar
16 por setor, sem garantir disponibilidade de mídia ou suporte de classes.
Nenhum ID novo foi selecionado e nenhuma evidência desses candidatos foi aberta.

Nenhuma dessas etapas foi executada como implementação ou auditoria nova.
B-VLM continua sem atributos liberados; o teste reservado não é recurso de
depuração nem de escolha da correção.

## Recibos desta investigação

As nove chamadas sintéticas levaram 80,34 s; somadas à revisão v7, são 649
chamadas nesses dois registros. O tempo cumulativo, incluindo os 2.404,72 s
da rodada anterior, passou de 8.226,57 para 8.306,91 s. O checkpoint
v7 continua selado em 640 chamadas/8.226,57 s e seus recibos não mudaram. As duas
imagens sintéticas temporárias foram removidas; nenhuma mídia real foi retida.

Artefatos privados: `data/private/issue-4-vlm-diagnostico-20261019/`.
Hash lógico do diagnóstico:
`7e0bbc3535e8cb83763503b662d1733ed6d745b11a935c188defccd246219de1`.
Os 67 arquivos protegidos e todos os recibos do fechamento anterior conferem.
Revisão independente somente leitura confirmou os controles, contagens,
limitações de causalidade e preservação. Verificações desta unidade incluem
recomputação dos agregados, parser das nove respostas, hashes, limpeza,
limites de tempo/RSS, links internos e diff; não há alteração de código que
exija repetir a suíte de treinamento.

Esta mudança de repositório registra apenas investigação e proposta; não muda
extratores ou modelos, nem altera o resultado negativo da auditoria encerrada.

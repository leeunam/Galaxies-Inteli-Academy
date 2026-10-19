# Revisão perceptiva VLM antes da retomada de B

Solicitação de 19/10/2026: corrigir o extrator e avaliá-lo em outra amostra
cega de treino, preservando coorte, partições, teste reservado e M1. Continua
na branch `codex/issue-4-experimento-b`, após `b779a63`. A
[auditoria anterior](issue-4-experimento-b-vlm-resultados.md) está revelada e
agora serve exclusivamente ao desenvolvimento da percepção.

## Separação e hipótese

Não abrir views, títulos, descrições, transcrições ou evidências/rótulos do
teste. Validar metadados contra A300 antes de selecionar evidências. Preservar
203 treino/66 validação/31 teste, todos os bundles/fontes anteriores e os
recibos da rodada reprovada. Implementar em novos arquivos, sem mudar serviço,
MCP, extratores anteriores ou as 905 entradas de B-cache.

Usar os 32 casos antigos para desenvolvimento, sem rótulos de alcance. Fixar
por hash outra amostra de 32 casos de treino, 16/setor, em 32 canais distintos.
Excluir todos os IDs, canais e hashes de mídia da auditoria antiga. Ordenar
primeiro os canais por SHA256 de protocolo+setor+canal, selecionar16 por setor
e escolher um vídeo por canal por outro hash de protocolo+ID, beleza antes de
moda. Isso evita favorecer canais com mais vídeos elegíveis. Não inspecionar
imagens ou saídas para escolher/substituir casos.
Se faltar suporte de classes na nova auditoria, registrar insuficiência sem
reposição ou mudança de critério. Seus IDs são fixados antes das inferências.

Hipótese baseada apenas na rodada antiga: o pedido conjunto de sete atributos
misturou reconhecimento e referência temporal. Testar perguntas por frame e
construir as referências por código, com semântica explícita de presença.
Nesta revisão, somente pessoa, produto inicial e texto são candidatos.
Ambiente e formato ficam globalmente desconhecidos, assim como close-up e
aplicação; não redefinir suas taxonomias para fazê-los passar.

## Desenvolvimento limitado e congelamento

Mesmos Qwen3-VL-2B GGUF Q4_K_M, projetor Q8_0, runtime b11716, CPU4, seed42,
temperatura0, limite128 tokens de imagem e crops320×330 dos PNGs congelados.
Reaquisição deve reproduzir propriedades, tempos e SHA256 da folha original;
bytes do contêiner podem divergir, conforme o contrato de identidade anterior.
O modelo recebe somente um crop por chamada, sem cabeçalho da folha.

Pré-declarar dois candidatos, sem versões adicionais nesta rodada:

- A: uma chamada por frame, três respostas booleanas/unknown, até96 tokens.
- B: três chamadas por frame, uma resposta por atributo, até64 tokens cada.

Pessoa inclui parte humana visível, inclusive mão/braço; roupa, manequim ou
rosto impresso em embalagem não estabelecem presença de pessoa. Produto exige
cosmético, aplicador, peça ou acessório apresentado como objeto de interesse;
roupa incidental de quem fala não basta. Texto exige caracteres visíveis no
conteúdo do crop, sem inferir de áudio ou produzir transcrição OCR.
`unknown` é uma resposta explícita quando não há evidência suficiente.

Para cada campo, agregar `true` se houver frame elegível com resposta true,
citando todos esses frames. Agregar false somente se todos os elegíveis forem
false, citando-os; nos demais casos, unknown com lista vazia. Produto considera
somente tempos <=3s. O modelo não escolhe índices nem responde sobre presença
em frames que não recebeu. Não corrigir respostas individuais pela anotação.
Recusar JSON incompleto, chaves duplicadas, campos/tipos/valores inesperados;
guardar resposta bruta e prova de cada chamada antes de validar.

Executar ambos nos mesmos 32 antigos. Qualquer falha de chamada, JSON,
identidade, limpeza ou dado ausente interrompe o desenvolvimento sem ranking
parcial, substituição, reexecução ou preenchimento por outro candidato.
Selecionar uma versão inteira pelo maior
número de acertos de valor+evidência nos 96 pares caso/campo. Empatar por menos
citações sem suporte, maior número conhecido e menor custo de chamadas (A).
As ausências não contam como acerto. Isso é desenvolvimento, não validação.
Não escolher versão por coluna, views ou métrica de B. Congelar versão,
prompt, esquema, agregação, fontes/runtime e resultado de seleção antes de
qualquer inferência na nova amostra. Não ajustar após revelar a auditoria.

## Auditoria nova e gate

Um agente separado registra anotações visuais assistidas dos 32 novos casos,
cego às respostas de ambos os candidatos, views e transcrições. O executor
não usa imagens/anotações novas para desenvolver ou selecionar o extrator.
Fixar anotações, hashes das imagens e proveniência antes de comparar saídas.
Revisão assistida não equivale a verdade certificada ou revisão humana.

Reutilizar o mesmo gate por coluna/setor: ao menos12 conhecidos em cada setor,
concordância de valor+frames >=90%, zero evidências citadas sem suporte;
booleanos com ao menos3 previsões de cada valor no total e ao menos1 por setor.
Não aliviar gate ou reamostrar depois do resultado. Ambiente/formato não são
liberados nesta revisão, mesmo que suas anotações existam. Se nenhuma coluna
passar, selar a etapa e registrar falha, sem treino preditivo B-VLM. Se passar,
registrar as colunas e configuração prontas para um novo lote uniforme de269;
a retomada preditiva exige esse lote completo, mantendo a grade12 e os
comparadores. Esta etapa encerra na nova validação perceptiva; não promove M1.

## Orçamento, descarte e verificações

Carregar as54 tentativas e2.404,7164981560236s anteriores por recibos/hash.
Esta revisão permite64 reaquisições (32 desenvolvimento+32 auditoria), mais
até10 tentativas DNS extras: teto cumulativo128, sem reiniciar as27h. Até900
chamadas locais nesta revisão (512 desenvolvimento+até384 auditoria+4 smokes).
Registrar cada tentativa/chamada e tempo antes da operação, sem apagar falhas.
Não repetir inferência inválida. DNS temporário tipado admite no máximo uma
repetição por ID e10 na revisão, após limpeza, espera e DNS positivo. Auth,
403/429, timeout, memória, divergência visual e limpeza incerta sempre param.
180s por aquisição/chamada, RSS filho <=3,3GiB e um executor.

Guardar somente folhas verificadas durante desenvolvimento/auditoria e crops
temporários durante inferência. Descartar vídeos ao fim de cada sessão e
folhas após registrar/validar o gate, mantendo sidecars, respostas e hashes
privados. Saídas novas em `data/private/issue-4-vlm-revisao-1/`.
Testar agregação, parser, isolamento, escolha/congelamento, contadores,
retomada, integridade de imagens e bloqueio de teste/labels. Revisão independente
somente leitura e commits por unidades lógicas verificadas.

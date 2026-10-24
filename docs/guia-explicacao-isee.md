# Como explicar o iSee em seis minutos

**O problema.** Um produtor tem de um a cinco vídeos para a mesma campanha e
quer decidir qual priorizar antes de publicar. O iSee estima views e mostra
incerteza e evidências. Foi desenvolvido por Leunam Sousa para a Galaxies,
no contexto da Inteli Academy. A persona da Galaxies consumirá a ferramenta;
ela não foi construída neste projeto.

**O que entra.** Vídeos autorizados, cadastrados localmente com IDs, setor
moda/beleza, objetivo divulgação e briefing. O alvo aprendido é a contagem
pública observada com 30 a menos de 37 dias. O pedido não fornece as views
futuras nem permite usar curtidas do próprio vídeo como atalho.

**Como o número aparece.** O serviço Python valida o pedido e usa os mesmos
extratores versionados do treino. M1/A200, a versão servida, usa setor,
propriedades do arquivo e representação da fala. CatBoost calcula os quantis
q10/q50/q90. q50 ordena os candidatos; o reparo de faixas preserva q50.
O LLM não inventa ou modifica esses números. A faixa não tem garantia de
cobertura de 80%, e a ordenação é prioridade exploratória para teste.

**De onde vem a explicação.** SHAP decompõe log1p(q50); as contribuições da
fala/embeddings são agrupadas por modalidade, sem dar significado inventado
a cada dimensão. Comparáveis vêm somente do treino. Na arquitetura aprovada,
NVIDIA seleciona IDs de evidência; validação e texto local preservam fatos e
números. A seleção real demonstrada usou fatos inventados; suficiência e
aderência de campanha real ainda estão em validação. SHAP não é causalidade.

**Onde acontece.** Cadastro, mídia, extração, previsão, SHAP e comparáveis ficam
locais. A função Python e o MCP por stdio expõem o mesmo caso de uso. O
percurso integrado v2 usa LangGraph em ambiente separado. Só um pacote de
evidências permitido pode seguir ao provedor; mídia e transcrição integral
não são enviadas automaticamente. Pesos e coortes privadas não acompanham
o clone público. Os dois locks preservam ambientes compatíveis.

**Por que essas escolhas.** Um modelo tabular treinado fornece números
mensuráveis independentemente do LLM. Encoders congelados e cache evitam
reprocessar a mesma mídia. Partições por canal/duplicatas reduzem vazamento;
transformações aprendidas ficam no treino. A/B isolam o ganho de informação
no CatBoost; B/C comparam bibliotecas com os mesmos atributos. O registro
local guarda configurações, hashes, versões, métricas e falhas.

**O que já foi demonstrado.** A300, B-cache e C-cache foram comparados na
validação. O par histórico v6 verificou Python/MCP com A200 e três mídias
reais. Outra execução real começou em features cacheadas e calculou M1,
SHAP, comparáveis e texto local. A demo pública usa vídeos/números inventados.
Abrir um relatório salvo apenas consulta aquela execução; não roda de novo
extração, modelo ou provedor.

**O que falta e por que importa.** Atributos VLM precisam passar por qualidade
perceptiva antes de B/C completos. JSON válido, fim do timeout e um acerto
isolado não bastam. Depois vêm seleção na validação, explicação/integracão
da configuração escolhida, congelamento e autorização específica do teste
de 31 casos. O diagnóstico temporal exige ajustar no anterior e avaliar no
posterior; um snapshot não mede desempenho prospectivo. Condições de uso da
fonte, amostra pequena e alto alcance subestimado também limitam a conclusão.

Para preparar o contrato de sete campos, use `build_schema(frame_seconds)`,
`build_prompt(frame_seconds)` e `parse_attributes(raw, frame_seconds)` de
`scripts.visual_attributes_seven`. O parser exige um JSON completo, sem reparo,
com evidência para valores conhecidos e `unknown` somente com `frames=[]`;
closeup e demonstração preservam todas as opções válidas. `screen_text` indica
presença de texto, sem transcrição OCR. O controle visual anterior falhou ao
retornar texto OCR nesse booleano e `unknown` com frame; a política antiga
também forçava close-up e demonstração para desconhecido (`unknown`), e sua
avaliação cobria só cinco campos. O caminho novo corrige essas lacunas sem alterar
a política legada, as fontes ou os protocolos congelados.
O schema não comprova suporte do provedor
nem da grammar instalada; JSON Schema aceita índices como `1.0`, que o parser
estrito rejeita. Não há execução automática de modelo ou requisição remota.
Para geração, `build_generation_schema(frame_seconds)` oferece um perfil simples,
sem `oneOf`, condicionais ou `uniqueItems`. Ele permite algumas respostas que
o contrato estrito proíbe; por isso toda saída deve passar por `parse_attributes`.
Evidência obrigatória, abstenção sem frames, unicidade e limite de três segundos
continuam sendo exigidos pelo parser. O prompt e os critérios de qualidade não
mudaram. Simplificar a geração não comprova qualidade perceptiva.
Para ensaios, `build_typed_generation_schema` expressa os booleanos e `unknown`
em ramos com tipos explícitos, sem mudar o domínio aceito. O pedido aditivo
`build_classification_prompt` distingue ausência observável (`false`) de
incerteza (`unknown`) e limita a decisão aos quadros fornecidos. Ambos preservam
o parser estrito e não são promovidos ao serviço por passarem testes de código.
`build_evidence_generation_schema` acrescenta a relação entre valor e evidência
à geração: ramos `anyOf` exigem quadros para valores conhecidos, inclusive
`false`, e lista vazia para `unknown`. O parser continua rejeitando duplicatas
e índices não inteiros. Compatibilidade com o NIM e qualidade visual são
verificações separadas.
`scripts.visual_quality_seven.evaluate_gate(observations)` recebe 32 linhas TRAIN,
16 por setor, com `alias`, `sector`, `partition="train"`, `channel_id`,
`sheet_sha256`, `frame_seconds`, `annotated` e `predicted` (ambos com os sete
atributos). IDs, canais e hashes devem ser distintos. O resultado agregado exige
ao menos 12 previsões conhecidas e 90% de concordância de valor e evidência por
campo/setor, nenhuma evidência sem suporte e representação mínima das classes;
booleanos exigem ambas as classes com ao menos três casos globais e um por setor;
categorias, dois valores com três casos globais cada. `unknown` é abstenção.
Todos os sete campos precisam passar. O resultado continua
com qualidade, release e extração269 falsos: origem, cegamento, conteúdo visual e
vínculos reais precisam de revisão independente. O carregador V7 segue bloqueado.

A amostra original tem 32 imagens e 24 canais reais, com até dois casos por
canal. Para ela, `evaluate_bound_gate(observations, expected_bindings)` exige
que cada alias, setor, partição, canal e hash corresponda à tabela de metadados
verificada. IDs e imagens continuam únicos; canais só podem repetir conforme
essa tabela. Os limiares acima não mudam. O relatório informa o suporte por
canal: 32 imagens não equivalem a 32 canais independentes. A função legada
continua exigindo canais distintos quando não há tabela vinculada.
O modo vinculado também exige suporte das classes nas referências: os mesmos
mínimos de três casos globais e um por setor para cada booleano, e duas
categorias conhecidas com três casos cada. Uma previsão errada não pode criar
suporte que falta no gabarito. O relatório separa `reference_value_support` de
suporte previsto e registra `missing_reference_support`; `unknown` não é
negativo. Nas 32 referências originais, beleza não tem negativos verificados
para `person_visible` e `product_closeup`. A referência assistida atual do suplemento descrito abaixo contém
um negativo de close-up; a lacuna de pessoa continua aberta. A cobertura
completa permanece pendente, mesmo se a concordância numérica passar.

O desenvolvimento dispõe das 32 folhas TRAIN originais, 16 de moda e 16 de
beleza, conferidas pelos hashes. Os sete campos agora têm referências aditivas
completas: duas anotações assistidas independentes das 32 imagens, seguidas
de adjudicação visual de 26 divergências em 14 imagens. As referências foram
seladas antes de qualquer geração TRAIN desta continuação; as antigas foram
preservadas. Isso não é revisão humana nem uma nova amostra cega. A concordância
entre anotadores não é acurácia do VLM. Dessas imagens, 24 foram recuperadas por aquisição
temporária: propriedades iguais e PNGs com os hashes originais, mas hashes de
mídia diferentes. Os vídeos foram apagados. A identidade das imagens não
certifica identidade da mídia nem qualidade do VLM. Ainda é preciso concluir
a avaliação perceptiva dos sete campos; completar as referências
não significa aprovar a auditoria. Ela usa o treino existente, sem alterar a
coorte de 300 ou o split 203/66/31. Não houve extração das 269 referências
restantes nem treino B/C observado.

Um controle visual sintético enviado ao NIM com `response_format/json_schema`
retornou HTTP 503, com `ResourceExhausted` e limite do worker (`16/16`), sem
comprovar duração ou escopo. Em uma continuação separada, o mesmo payload
retornou HTTP 500: recursos do schema não suportados pelo `xgrammar`.
Essa resposta não identifica qual palavra-chave foi rejeitada. Os erros são
distintos e ambos ocorreram antes de gerar atributos. Nenhuma imagem TRAIN
foi enviada nessas sondagens; testes locais do contrato e do operador não
demonstram qualidade visual.

A primeira verificação do perfil simples retornou HTTP 200, mas os cinco
booleanos eram `unknown` já na resposta bruta. Contrastes posteriores geraram
`true` literal com enum misto e com tipos explícitos; isso não sustenta uma
proibição geral de booleanos pelo provedor. Um desafio com caracteres inéditos
foi lido corretamente com e sem schema. A diferença na contagem de tokens não
prova descarte da imagem nem identifica o backend.

No novo controle de classificação, os sete valores corresponderam ao esperado,
mas quatro `false` vieram com evidência vazia, rejeitada pelo parser. Com o
schema de evidência, mantendo esse prompt e as imagens, os cinco booleanos
vieram corretos e com quadros nos dois controles. O controle textual correspondeu
nos sete campos; na imagem vazia, cenário e formato ficaram `unknown`. O aceite
completo original continua falso. Uma revisão assistida independente dos pixels
considerou essas categorias não verificáveis no branco, sem substituir a
referência antiga nem converter o controle em aprovação. Esses resultados
sintéticos permitem investigar o candidato, não certificar os sete atributos
em vídeos reais ou liberar os 269. A comparação anterior mudou prompt e imagem,
portanto não isola a causa das abstenções somente no texto da instrução.

A rodada diagnóstica real foi preparada para as 32 folhas, com o candidato
congelado e os cabeçalhos removidos dos quatro recortes de cada caso. Na
execução original, sete respostas passaram pelo parser e a oitava chamada
retornou HTTP 503 com `ResourceExhausted`; 24 casos não foram tentados. A
retomada fez nove chamadas: dois HTTP 503, com esperas de 60 e 120 segundos,
seis respostas novas estritamente válidas e um HTTP 200 inválido. A resposta
inválida repetiu um índice em `product_visible_early.frames`. O schema de
geração permite duplicatas; o parser estrito inalterado as rejeita corretamente.
Os sete resultados antigos foram preservados byte a byte. Há 13 resultados
únicos válidos e faltam 19: um inválido e 18 não tentados. Não foi calculada
métrica do painel de 32 nem emitido aceite. JSON válido não comprova
correspondência com as referências; os erros remotos não estabelecem cota da
conta ou prazo de recuperação.

Um protótipo privado prospectivo usa enum de subconjuntos únicos dos frames.
Foram executados 131 testes inventados e 427 regressões sintéticas públicas,
sem novo teste NIM, prova de compatibilidade com o provedor ou seleção para
produção. O candidato original e o parser não mudaram. Esses testes não medem
qualidade perceptiva. Uma alteração futura no perfil de geração exige protocolo
prospectivo e validação coerente do candidato no painel completo; os 13 resultados
atuais não podem ser agregados aos de outro candidato como um painel validado.

O suplemento de cobertura fixou 24 fontes TRAIN de beleza de 24 canais, em duas
etapas de 12. Todas foram recuperadas e anotadas, sem falhas de recuperação,
com PNGs iguais aos hashes congelados e vínculos de metadados e pixels
conferidos. As duas anotações assistidas independentes e a adjudicação foram
seladas antes de qualquer inferência NIM suplementar; não houve essas chamadas.
São referências assistidas, sem revisão humana ou amostra populacional cega.
As mídias temporárias foram removidas e somente imagens com hashes exatos foram
conservadas, sem comprovar identidade da mídia original.

A contagem de close-up foi ajustada por revisão assistida independente do escopo da rubrica após o selo anterior e antes de qualquer inferência suplementar.

Nesse suplemento, `person_visible` tem 24 verdadeiros e nenhum falso;
`product_closeup` tem 21 verdadeiros, 1 falso e 2 desconhecidos. Há um
negativo de close-up na referência assistida atual, mas nenhum de pessoa; a cobertura completa
continua pendente. Nenhum falso foi forçado, e as 32 referências originais não
foram substituídas. A coorte de 300 e o split 203/66/31 permanecem intactos,
com o teste fechado. Não houve aceite perceptivo, release integrado, extração
das 269 ou treino B/C observado; A200 permanece servido. Antes dessas etapas,
continuam necessárias a compatibilidade prospectiva do perfil com o provedor,
a validação coerente dos sete campos no painel completo, a cobertura de negativos
e a revisão independente com release.

Ao demonstrar, identifique primeiro a origem: **demo sintética**, **execução
real a partir de mídia**, **cálculo a partir de features cacheadas** ou
**consulta de resultado preservado**. Mostre previsão, faixa, ranking,
fundamentos e um limite. Não chame B/C-cache de B/C completos nem apresente
os números da validação como resultado do teste reservado.

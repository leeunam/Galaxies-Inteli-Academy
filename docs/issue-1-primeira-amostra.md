# Issue #1: primeira amostra guiada

Atualizado em 18/10/2026. [Issue no GitHub](https://github.com/leeunam/Galaxies-Inteli-Academy/issues/1).

Estado atual: vinte candidatos de vinte canais na seleção de desenvolvimento, com metadados e três extrações audiovisuais anteriores reutilizadas. Três revisões humanas completas e uma parcial foram preservadas; os demais casos aguardam pré-classificação audiovisual e revisão por amostragem. O backend Qwen3-VL substituiu o VLM inicial reprovado, mantendo aplicação e close-up desconhecidos. O [relatório do piloto real](piloto-youtube-real.md) e a [correção dos extratores](correcao-extratores.md) registram medidas e limites. Não há registro elegível de treino, curadoria integral ou condições da fonte validadas para a base. O fixture anterior do Commons fica fora do treino. O modelo público de CSV permanece vazio.

Atualização de 17/10: o aluno confirmou que ainda não dispõe de arquivos originais e autorização de uso. Já consultou a Inteli Academy e não haverá base fornecida. Escolheu manter YouTube e moda/beleza, buscar criadores e usar ferramentas/IA para captura em lote, preservando o prazo. Não seguir com a migração proposta para SMP-Video/TikTok.

Esclarecimento confirmado pelo aluno: manter imagem/fala, automatizar aquisição temporária e usar links dos canais como entrada da coleta; remover tags e conservar canal/datas somente em auditoria. A coleta pela API não depende de legendas e contatos. Não há mudança de A/B/C para metadados apenas. Os testes de [coleta por canais](coleta-por-canais.md), [extração inicial](piloto-extracao-temporaria.md) e [Shorts reais](piloto-youtube-real.md) estão registrados. O foco viral orientou a seleção do último piloto, mas a futura base precisa conter a distribuição de desempenhos; o corpus experimental e a qualidade dos atributos VLM continuam pendentes.

Diagnóstico posterior: [Qwen3-VL GGUF substituiu o SmolVLM2](correcao-extratores.md), com extração concluída em 3/3 casos e controles visuais assistidos. Aplicação e close-up estão bloqueados globalmente; esquema válido não libera treino. As [três transcrições originais foram confirmadas por escuta](validacao-transcricoes.md). A issue permanece aberta pelas demais condições do checkpoint.

Plano confirmado: meta de 300/piso de 200 e primeira seleção de vinte candidatos, de vinte canais, sem novos downloads. O aluno aceitou a entrega de protótipo com treino/validação reais pendentes se a autorização não chegar no prazo. O [registro de uso e corte da entrega](uso-youtube-e-plano-de-entrega.md) distingue preparação, fonte utilizável e critérios científicos ainda não atendidos. A fila retomável será ensaiada com dados sintéticos enquanto o uso audiovisual estiver pendente.

## Compatibilidade ML verificada em 18/10

CatBoost **1.2.10** e LightGBM **4.7.0** foram adicionados ao ambiente Python **3.11.13**,
com NumPy **2.4.6**. As versões e dependências transitivas estão no `uv.lock`; nenhuma
versão anteriormente travada foi alterada. Verificações do lock e das dependências
instaladas passaram, assim como os **47 testes existentes** após a instalação.

O teste de viabilidade usou somente dados gerados: 128 linhas, setor categórico
moda/beleza, seis atributos numéricos artificiais e vetores aleatórios de 384/512
dimensões, totalizando 903 colunas. Esses vetores têm as dimensões previstas para texto
e visão, mas não são embeddings extraídos de vídeos. Houve ausências numéricas tanto
nas 96 linhas de ajuste quanto nas 32 usadas apenas para inferência. O rótulo é
`log1p` de visualizações inteiramente simuladas; não houve acesso à base real.

Cada biblioteca executou três ajustes independentes, com quantis explícitos
0,1/0,5/0,9, doze iterações e CPU com duas threads. Os seis ajustes aceitaram categoria
nativa e valores ausentes, produziram 32 previsões finitas cada e permitiram conversão
por `expm1`. Cada artefato foi gravado no formato nativo, recarregado e usado novamente:
a diferença máxima nas previsões foi **zero** em todos os casos.

Isso verifica instalação, treino mínimo, inferência e persistência. Não mede qualidade
preditiva, cobertura de faixa, generalização, ganho multimodal ou superioridade entre
bibliotecas. Os tempos registrados são de um fixture pequeno; não são um benchmark de
escala. Pico de memória não foi medido nesta rodada. Os quantis deste teste também
não são os experimentos A/B/C: esses continuam dependentes de dados reais utilizáveis.

Os probes são descartáveis, privados e sem papel no produto. Código, fixture, seis
artefatos e relatório com hashes estão em
`data/private/technical-probes-20261018/ml_smoke.py` e `ml-run-01/result.json` no mesmo
diretório. Uma repetição local deve usar outro diretório de saída; os resultados
existentes não são sobrescritos. Isso não é ainda uma demonstração reproduzida a partir
de um checkout público limpo nem um pipeline de treinamento de produção.

Referências do procedimento: [quantis do CatBoost](https://catboost.ai/docs/en/concepts/loss-functions-regression)
e [alpha do LightGBM](https://lightgbm.readthedocs.io/en/stable/Parameters.html#alpha).

## Objetivo do primeiro bloco

Revisar primeiro os metadados de uma referência já publicada e depois ampliar, procurando ambos os setores e canais distintos. Para cada uma, conseguir responder: o que a fonte informa sobre o conteúdo, qual é a publicação, de onde vem a métrica e quando foi observada. A revisão do registro deve distinguir campos retornados, sugestões da triagem e informações ainda desconhecidas. O arquivo audiovisual só entra como requisito quando forem extraídos atributos de áudio/frames; sua ausência não impede a coleta tabular.

Essas referências têm resultados observados para estudar o treinamento. Os criativos inéditos usados posteriormente na ferramenta não terão essas métricas e serão processados pelo percurso de inferência.

## 1. Escolher uma rota de dados viável

| Rota | O aluno verifica | O que a IA pode fazer |
| --- | --- | --- |
| Arquivos e métricas fornecidos diretamente por criador/marca | Acesso aos originais, identidade da publicação correspondente e autorização para o uso pretendido | Organizar evidências, inspecionar arquivos e auditar associação entre arquivo, publicação e rótulo |
| Dataset com licença e arquivos disponíveis | Se o uso do conjunto e da mídia está permitido e se os exemplos representam o caso | Inspecionar documentação/esquema, verificar amostra pequena, mapear campos e registrar incompatibilidades |
| YouTube Data API | Condições aplicáveis aos dados e ao uso estatístico pretendido; disponibilidade separada da mídia | Auxiliar consulta pontual autorizada, registrar instantes e validar campos, antes de decidir qualquer expansão |

Acesso público, posse de uma chave e autorização sobre um arquivo são evidências diferentes. As políticas da API têm condições para conteúdo audiovisual, agregação e métricas derivadas. Trocar uma coleta automatizada por anotação manual não resolve por si só uma restrição de uso. Conferir a fonte e suas condições antes de tratá-la como utilizável; não presumir autorização nem concluir proibição genérica de todo ML.

A inspeção dos repositórios SMTPD/MicroLens não confirmou uma alternativa pronta para vídeos de moda/beleza em pt-BR, verticais e de até 60 segundos. SMTPD aponta dados tabulares e capas, sem confirmar acesso a vídeo/áudio completos. A checagem adicional de MicroLens confirmou acesso a pequenos metadados, mas os IDs de usuário das interações não identificam criadores; publicação e instante da contagem por vídeo não foram demonstrados. A mídia é distribuída em um grande arquivo multipartes, sem download individual de MP4 verificado. O [portal dos autores](https://recsys.westlake.edu.cn/) apresenta condições específicas de pesquisa acadêmica e restrições sobre modificações e distribuição; sua aplicação ao processamento pretendido exige esclarecimento. Não tratar licença do código como licença dos arquivos de terceiros.

### Resultado da investigação adicional em 17/10

| Fonte primária | O que foi verificado | Consequência para esta entrega |
| --- | --- | --- |
| [mxmprhd/youtube-shorts-dataset](https://huggingface.co/datasets/mxmprhd/youtube-shorts-dataset) | Inspeção dos três Parquets pequenos em memória: 1.077 vídeos, 48 canais; 54 itens `beauty_fashion`, de apenas dois canais (40 Huda Beauty e 14 NikkieTutorials). Esses 54 são verticais, com 6–60 s. Há views, likes, canal e data de publicação, mas não instante de observação nem idioma por vídeo; `license` é nulo em todos os registros. O card declara inglês e restringe o CC BY 4.0 ao manifesto, sem fornecer mídia ou conceder direitos sobre ela. | Pode apoiar um exercício de importação tabular, atribuído à fonte. Não sustenta o piloto multimodal autorizado, o horizonte proposto nem avaliação robusta entre canais de moda/beleza. Não foi incorporado à amostra de treino. |
| [ShortVideo_dataset, WWW2025](https://github.com/tsinghua-fib-lab/ShortVideo_dataset) e [artigo dos autores](https://arxiv.org/html/2502.05922v1) | Plataforma Kuaishou; anuncia MP4 e transcrições. `effective_view` é indicador de uma interação com tempo assistido superior a três segundos; `cvm_like` é curtida naquela interação. O esquema não fornece contagem pública total e instante de publicação. Não foram confirmados pt-BR, autorização específica suficiente nem acesso utilizável à mídia: o link da amostra Dropbox retornou indisponibilidade temporária e o portal não pôde ser acessado nesta checagem. | Somar interações dos voluntários não produz o nosso rótulo de views públicas. Acesso, alvo, plataforma e recorte exigiriam decisões novas; não é alternativa pronta para o plano aprovado. |
| [Understanding Virality](https://arxiv.org/html/2512.21402v1), referência do TAPI | O artigo descreve 11 mil Shorts de conteúdo educativo/informativo e afirma compartilhar apenas dados derivados, sem distribuir os vídeos brutos. Não foi localizado no artigo um pacote acessível de mídia autorizada para o recorte. | Referência de método; a existência do estudo não fornece automaticamente seus dados de treino. |
| [YouGraph/PUCPR](https://www.ppgia.pucpr.br/~paraiso/Projects/YouGraph/) | A página anuncia transcrições e metadados em pt-BR, com acesso mediante contato. Não oferece diretamente o conjunto nem confirma mídia audiovisual ou o recorte de Shorts. | Possível fonte auxiliar de texto após obter acesso e condições. Não resolve a amostra multimodal de hoje. |
| [SMP-Video oficial](https://huggingface.co/datasets/smpchallenge/SMP-Video), indicado na [página do SMP Challenge](https://smp-challenge.com/download_video.html) | Há licença própria para pesquisa/não comercial, metadados e rótulos, e indicação separada da fonte de vídeos. Acesso exige login e aceite de compartilhamento de contato; esse aceite não foi realizado. O [artigo da solução vencedora de 2025, seção 4.1](https://arxiv.org/html/2507.00950v1), descreve 6 mil publicações de TikTok e rótulo `log2(views/dias) + 1`. | Alternativa discutida e descartada pelo aluno para esta entrega, que permanece em YouTube/moda/beleza. Não foi incorporada ao projeto. |

Essa investigação usou documentação e metadados pequenos; não baixou vídeos, executou scripts de download ou contatou responsáveis. A data de um commit ou arquivo do dataset não foi usada como substituto do instante de observação das contagens. A ausência de uma fonte validada nesta busca não demonstra que nenhuma exista.

### Decisão confirmada e captura inicial

Embora o TAPI previsse a preparação da base pela liga, o aluno já confirmou com a organização que não haverá fornecimento. Não aguardar essa entrega nem repetir essa solicitação como dependência do projeto.

O aluno mantém YouTube, moda/beleza e entrega em 21/10 às 23h59. A estratégia mediana → A → B → C permanece aprovada. Ferramentas/IA apoiarão descoberta, coleta estruturada e conferência; as condições de acesso e uso da mídia continuam exigindo evidência. Não enviar contatos a criadores em nome do aluno sem instrução explícita.

Uma sondagem descartável, sem criar ainda o coletor de produção, executou quatro chamadas `search.list` e uma `videos.list` em 17/10, entre 22h36m55s e 22h36m57s UTC (19h36 em São Paulo). A chave foi lida do `.env` local e enviada em cabeçalho HTTPS, sem integrar URL, arquivos de saída ou logs. O relatório registra parâmetros e instantes reais.

- Busca de viabilidade na janela proposta: dez resultados de `maquiagem skincare #shorts` e dez de `moda looks #shorts`, por relevância, com idioma de relevância português e disponibilidade no Brasil. Dos vinte, quinze atendem somente a duração de até 60 segundos e idade entre 30 e 37 dias, em quatorze canais. Os setores sugeridos pelas consultas são sete beleza e oito moda; ainda não são classificação humana confirmada.
- Busca separada de fontes de mídia: vinte resultados filtrados por `videoLicense=creativeCommon`, sem filtro de idade. Todos têm até 60 segundos, mas nenhum atende à idade proposta. Essa busca não ampliou o recorte do treino nem validou direitos ou acesso ao arquivo.
- O lote contém quarenta registros únicos de metadados. Entre os quinze candidatos da janela, views observadas vão de 6 a 2.280.666. Não houve seleção por mínimo de views. Contagens descrevem o lote e não medem qualidade do modelo.
- Os arquivos privados estão em `data/raw/youtube-pilot/20261017T223655Z/`, `data/private/primeira-amostra.csv`, `data/private/triagem-metadados.csv` e `data/private/primeira-coleta.md`. O último guia aponta o primeiro exemplo escolhido pela ordem do hash do ID, sem ordenar por views. Não houve preenchimento de setor confirmado, idioma, resolução ou localização de mídia sem evidência; situações de uso permanecem `pending`.

### Próximo lote e responsabilidades

Para ampliar a coleta experimental, usar a busca para descobrir canais, fixar canais e critérios antes das contagens e enumerar suas playlists de uploads no período. Registrar a cobertura e paginação; a busca por relevância usada na sondagem é amostra de conveniência e não um levantamento exaustivo. A documentação oficial recomenda a playlist de uploads para enumerar publicações recentes. Consultar detalhes em lotes de até cinquenta IDs; guardar a procedência e os limites da chamada. A IA pode executar esse trabalho repetitivo após revisar o primeiro exemplo.

Virais podem ser referências úteis, mas selecionar somente eles condiciona a base ao resultado. Manter vídeos de desempenho baixo e intermediário, inclusive zero quando realmente informado pela fonte, para avaliar a ordenação no domínio pretendido. Descoberta por palavras e criadores que autorizam o uso também introduz vieses que devem ser relatados; diversidade de views sozinha não prova representatividade.

A IA pode organizar a lista, consultar e validar metadados públicos e manter os links de referência. O aluno revisa o primeiro exemplo, a classificação de setor e a interpretação do rótulo. O contato com criadores deixa de ser uma dependência da coleta tabular. Se a etapa audiovisual for mantida, tratar separadamente como obter mídia ou atributos equivalentes, com condições de uso e correspondência verificáveis; não exigir o arquivo mestre do criador como única possibilidade técnica.

Para um preditor tabular, manter somente entradas que possam ser fornecidas também para o inédito, como título/descrição planejados e duração, conforme contrato a definir. Views observadas são o rótulo; curtidas do próprio vídeo ficam na análise retrospectiva. Se o produtor fornece apenas arquivo e intenção da campanha, ainda é preciso explicitar como obter entradas equivalentes às do treino. Uma URL identifica a referência, mas não substitui a transcrição, os frames ou as features extraídas. Um agente pode produzir análise qualitativa do inédito, porém isso não demonstra ganho preditivo audiovisual de um modelo treinado apenas com metadados.

Uma [cópia licenciada da TV Brasil no Wikimedia Commons](https://commons.wikimedia.org/wiki/File:%22A_moda_faz_parte_da_vida_de_todo_mundo%22,_defende_a_modelo_Carol_Ribeiro.webm), associada a publicação YouTube de 2017, foi usada no ensaio técnico: 36 segundos, 1920×1080, CC BY 3.0. O piloto executou extração e confirmou remoção da mídia; idade e orientação horizontal a excluem do treino proposto. Os atributos VLM gerados foram reprovados por ausência do esquema/evidências. Isso não equivale a liberar o treino multimodal da coorte.

Com o primeiro exemplo acessível, o aluno explica a origem e o significado da contagem; a IA confere esquema, correspondência, propriedades, datas e pendências. Depois de validá-lo juntos, repetir para três e então ampliar o piloto. Poucos exemplos demonstram funcionamento, sem comprovar qualidade estatística.

Enquanto a mídia estiver pendente, contratos e processamento podem ser ensaiados com vídeo próprio/autorizado e exemplos sintéticos claramente identificados. Isso não conclui o checkpoint de dados, não satisfaz a comparação científica A/B/C e não permite anunciar desempenho preditivo. Manter o prazo reafirmado e reportar qualquer requisito não cumprido; não trocar idioma, plataforma, setores ou horizonte silenciosamente nem chamar candidato incompleto de amostra de treino. A issue #1 permanece aberta.

## 2. Preencher o primeiro candidato

O modelo público vazio está em `examples/manifesto-amostra.template.csv`. A cópia de trabalho local é `data/private/primeira-amostra.csv`, excluída do Git. Guardar documentos privados de autorização na mesma área privada; o CSV aponta para a evidência, sem copiar mensagens ou dados pessoais para documentação pública.

Começar identificando fonte e disponibilidade; não inventar os demais campos para completar a linha.

| Campos | Responsável inicial | O que registrar |
| --- | --- | --- |
| sample_id, sector, source_url | Aluno, com revisão da IA | ID interno, moda/beleza e referência pública ou do dataset |
| media_origin, metrics_origin | Aluno | Quem forneceu o arquivo e qual sistema/arquivo fornece os resultados |
| media_rights_status, metrics_use_status, rights_evidence_ref | Aluno fornece evidência; IA organiza a revisão | Estados `pending`, `verified` ou `incompatible`, conforme documentação efetivamente conferida; referência à licença/autorização e limites |
| video_id, channel_id | IA após escolher a fonte, com conferência do aluno | Identificadores verificáveis; nome de usuário não é automaticamente ID de canal |
| published_at_utc, observed_at_utc, view_count, like_count | Fonte verificada, com revisão conjunta do primeiro registro | Publicação e observação em ISO 8601/UTC; contagens não negativas; curtidas ausentes ficam vazias |
| media_path | Aluno fornece localização; IA confere | Caminho local do arquivo autorizado e correspondência com a publicação |
| duration_seconds, width, height, media_sha256 | IA | Extrair do arquivo depois de confirmar acesso e condições de uso |
| language | Revisão humana apoiada por extração | Conteúdo efetivamente em português brasileiro; idioma do título sozinho não comprova o idioma falado |
| eligibility_status, exclusion_reason | Revisão conjunta | `candidate`, `eligible` ou `excluded`, com motivo; linha incompleta permanece candidata |

`verified` exige evidência compatível com o uso descrito; o programa não pode inferir isso pela presença de uma URL ou pelo campo marcado. Ausência de métrica não equivale a zero. Contagem abreviada na interface, como “10 mil”, não deve ser registrada como 10.000 exatos; procurar uma fonte que forneça o valor exato ou registrar a limitação antes de usar o rótulo. Caso a fonte só tenha dados do canal agregado, eles não substituem o resultado do vídeo. As colunas de resultado ficam separadas das features do preditor.

## 3. Entender o rótulo e o recorte

O recorte proposto é vertical, até 60 segundos, moda/beleza, pt-BR e idade `30 <= dias < 37` na observação. Essa faixa ainda é hipótese de viabilidade; não alargá-la depois de olhar desempenho. Se o arquivo ou a data não permitirem verificar o recorte, registrar a pendência.

Exemplo apenas de datas: uma publicação de 15/09/2026 às 15h UTC observada em 17/10/2026 às 15h UTC tem 32 dias. Sua contagem observada é a do dia 17/10, não uma medida reconstruída do dia 30. Registrar os instantes completos, pois arredondar só pela data pode mudar a elegibilidade nas bordas.

O aluno deve conseguir explicar por que views observadas formam o rótulo, por que não entram na análise de um inédito e por que a data da observação importa. Visualizações públicas não identificam por si só pessoas únicas ou resultado de patrocínio. Não ajustar views por dia para fabricar um horizonte exato.

## 4. Delegar depois de verificar o primeiro exemplo

Após uma fonte e um registro completos passarem pela revisão, a IA pode repetir a importação, extrair propriedades e hashes, identificar duplicatas, conferir datas e contagens e resumir a cobertura por canal/setor. O aluno revisa uma pequena amostra dos resultados e interpreta os motivos de exclusão.

Ampliar primeiro para três registros e depois para até vinte, procurando ambos os setores e cerca de dez canais, conforme a oferta real. Isso é piloto de acesso e funcionamento, não comprovação de qualidade preditiva. Se a fonte não sustentar essa diversidade, registrar o limite e decidir antes de treinar.

O aluno conserva as decisões sobre fonte aceitável, significado do alvo, representatividade e interpretação dos resultados. A IA não concede direitos sobre conteúdo, não inventa resultados e não envia mídia ou evidências privadas ao NIM. O teste do explicador será separado, com dados sintéticos.

## 5. Organização dos chats e conclusão

Continuar no chat principal para este primeiro registro e para a decisão da fonte. Depois de estabilizar o contrato, um chat de execução da issue #1 pode tratar importação e validação, recebendo a issue e os documentos versionados como contexto. Não manter dois executores alterando a mesma árvore. Worktree só se houver trabalho independente que justifique outra árvore.

Este primeiro bloco pode terminar com candidatos pendentes, desde que as faltas estejam claras. A issue #1 continua aberta até cumprir também o manifesto auditável, relatório de elegibilidade, ensaios dos extratores/modelos e checkpoint do alvo. Não marcar candidatos como treinamento real apenas porque foram colocados num CSV.

## Fontes verificadas

- [YouTube: recurso de vídeo](https://developers.google.com/youtube/data/reference/rest/v3/videos) e [políticas de conteúdo/dados](https://developers.google.com/youtube/terms/developer-policies).
- [YouTube: busca e filtros](https://developers.google.com/youtube/data/reference/rest/v3/search/list), [consulta de vídeos em lote](https://developers.google.com/youtube/data/reference/rest/v3/videos/list), [playlist de uploads](https://developers.google.com/youtube/data/reference/rest/v3/channels) e [paginação das publicações](https://developers.google.com/youtube/data/reference/rest/v3/playlistItems/list).
- [SMTPD: repositório dos autores](https://github.com/zhuwei321/SMTPD).
- [MicroLens: repositório dos autores](https://github.com/westlake-repl/MicroLens).
- [OpenAI: projetos locais e contexto de novos chats](https://learn.chatgpt.com/docs/projects#use-local-projects-for-folders-and-codebases).

# Issue #1: primeira amostra guiada

Data: 17/10/2026. [Issue no GitHub](https://github.com/leeunam/Galaxies-Inteli-Academy/issues/1).

Estado inicial: nenhum registro real preenchido ou fonte multimodal validada. O CSV é uma ficha de trabalho vazia; sua existência não constitui uma base de treinamento. Não houve coleta em escala, download de mídia ou inferência externa nesta preparação.

## Objetivo do primeiro bloco

Verificar até três referências já publicadas, procurando ambos os setores e canais distintos. Para cada uma, conseguir responder: qual é o conteúdo, onde está o arquivo, de onde vem a métrica, quando foi observada e quais condições permitem o uso pretendido. O primeiro registro será percorrido com o aluno antes de delegar repetição.

Essas referências têm resultados observados para estudar o treinamento. Os criativos inéditos usados posteriormente na ferramenta não terão essas métricas e serão processados pelo percurso de inferência.

## 1. Escolher uma rota de dados viável

| Rota | O aluno verifica | O que a IA pode fazer |
| --- | --- | --- |
| Arquivos e métricas fornecidos diretamente por criador/marca | Acesso aos originais, identidade da publicação correspondente e autorização para o uso pretendido | Organizar evidências, inspecionar arquivos e auditar associação entre arquivo, publicação e rótulo |
| Dataset com licença e arquivos disponíveis | Se o uso do conjunto e da mídia está permitido e se os exemplos representam o caso | Inspecionar documentação/esquema, verificar amostra pequena, mapear campos e registrar incompatibilidades |
| YouTube Data API | Condições aplicáveis aos dados e ao uso estatístico pretendido; disponibilidade separada da mídia | Auxiliar consulta pontual autorizada, registrar instantes e validar campos, antes de decidir qualquer expansão |

Acesso público, posse de uma chave e autorização sobre um arquivo são evidências diferentes. As políticas da API têm condições para conteúdo audiovisual, agregação e métricas derivadas. Trocar uma coleta automatizada por anotação manual não resolve por si só uma restrição de uso. Conferir a fonte e suas condições antes de tratá-la como utilizável; não presumir autorização nem concluir proibição genérica de todo ML.

A inspeção documental inicial dos repositórios SMTPD/MicroLens não confirmou uma alternativa pronta para vídeos de moda/beleza em pt-BR, verticais e de até 60 segundos. SMTPD aponta dados tabulares e capas, sem confirmar acesso a vídeo/áudio completos; MicroLens anuncia mídia bruta, mas adequação de setores, idioma, datas de observação e condições dos dados ainda precisam ser estabelecidas. Não tratar licença do código como licença dos arquivos de terceiros.

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
- [SMTPD: repositório dos autores](https://github.com/zhuwei321/SMTPD).
- [MicroLens: repositório dos autores](https://github.com/westlake-repl/MicroLens).
- [OpenAI: projetos locais e contexto de novos chats](https://learn.chatgpt.com/docs/projects#use-local-projects-for-folders-and-codebases).

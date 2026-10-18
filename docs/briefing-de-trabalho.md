# Briefing de trabalho e aprendizagem

Atualizado em 18/10/2026. Horários de São Paulo.

Este documento registra os compromissos confirmados e o plano de execução autorizado pelo aluno em 16 e 17/10/2026. Em 17/10 foram aprovados A → B → C, Ridge opcional e a publicação das sete issues. Fonte de dados, horizonte efetivamente sustentado e viabilidade dos extratores serão verificados no checkpoint inicial; aprovação do plano não significa que esses dados já existem ou foram validados.

O desenho técnico está em [proposta-tecnica.md](proposta-tecnica.md), acompanhado das sete entregas e links reais em [backlog-proposto.md](backlog-proposto.md). As issues #1–#7 foram publicadas e suas dependências nativas verificadas. Começar pela [#1 — amostra auditável e viabilidade](https://github.com/leeunam/Galaxies-Inteli-Academy/issues/1); ela libera o primeiro fluxo baseline após resolver o checkpoint dos dados.

O início guiado da #1 está em [issue-1-primeira-amostra.md](issue-1-primeira-amostra.md). A Academy não fornecerá base, conforme consulta do aluno. Ele mantém YouTube, moda/beleza e prazo de 21/10; TikTok/SMP-Video foi descartado. A sondagem inicial retornou 40 metadados, com 15 candidatos de 14 canais atendendo somente à idade/duração propostas. O novo coletor por links consultou duas playlists e trouxe cem registros em seis chamadas, com cobertura parcial. Houve também extração audiovisual real em um fixture licenciado fora do recorte: não há ainda amostra elegível de treino ou modelo preditivo treinado. Resultados e limites estão em [coleta-por-canais.md](coleta-por-canais.md) e [piloto-extracao-temporaria.md](piloto-extracao-temporaria.md).

Orientação mais recente de 17/10: o aluno pediu testar yt-dlp diretamente em três candidatos reais encontrados pela API e reafirmou o foco em potencial de viralização. O [piloto real do YouTube](piloto-youtube-real.md) concluiu os três downloads, extração local e descarte: dois candidatos de beleza com alto alcance e um de moda. As sessões levaram 65,99 s, 49,82 s e 45,15 s; restaram zero sessões temporárias. Há metadados, fala, embeddings e medidas técnicas, mas os atributos VLM dos três foram reprovados. A disponibilidade técnica foi demonstrada nesses casos; condições da fonte, curadoria completa e elegibilidade de uma base de treino continuam pendentes. O fixture anterior do Commons permanece fora do recorte. Não substituir fala por título nem prometer exclusão imediata após queda da máquina.

O aluno confirmou remover tags e conservar canal/datas somente para auditoria, fora das entradas do modelo. A chave de canal serve à separação por criador, e publicação/coleta verificam o horizonte observado. Views são rótulo; curtidas permanecem somente no diagnóstico. Os atributos usados para prever continuam sendo os sinais do criativo disponíveis também nos inéditos.

No piloto concluído, uma sessão de 36,061 s de vídeo levou 43,10 s para aquisição e extração com pesos já baixados, com pico de 2,65 GiB. Houve seis frames, dez segmentos de fala e embeddings de 384/512 dimensões. Limpeza foi confirmada tanto após sucesso quanto após falha real. SmolVLM2 gerou JSON sem o esquema/evidências exigidos; os atributos foram reprovados e a rubrica continua pendente. Esses números são viabilidade operacional de um exemplo, não acurácia de percepção, desempenho preditivo ou capacidade em escala. A primeira etapa tinha dez testes locais; com o adaptador do YouTube, são quatorze testes passando para coleta, limpeza, validação e timeout.

Atualização do diagnóstico: as três transcrições originais foram ouvidas e confirmadas pelo aluno (primeiro fala, terceiro canto; segundo sem classificação separada). Qwen3-VL-2B GGUF local substitui o SmolVLM2 no extrator. O novo lote concluiu 3/3 casos com esquema válido e revisão assistida dos frames; aplicação teve um falso positivo e close-up ficou ambíguo. Ambos permanecem globalmente desconhecidos, preservando saída bruta e sem aprovação automática de treino. Método, tempos, memória e pendências estão em [correcao-extratores.md](correcao-extratores.md) e [validacao-transcricoes.md](validacao-transcricoes.md). Não houve expansão da base ou inferência externa.

Atualização do plano: o aluno aprovou meta de 300 e piso de 200, começando por vinte candidatos e retomada. Escolheu manter YouTube/moda/beleza e, se autorização não chegar a tempo, entregar protótipo executável com treino/validação supervisionados reais pendentes. A descoberta adicional consultou 162 registros e preparou vinte candidatos de vinte canais (dez propostas por setor), sem novos downloads. Condições, corte e próximos marcos estão em [uso-youtube-e-plano-de-entrega.md](uso-youtube-e-plano-de-entrega.md). Não confundir candidato com base elegível ou protótipo com desempenho validado.

## Compromissos confirmados

- Entrega: quarta-feira, 21/10/2026, até 23h59.
- Apresentação: sexta-feira, 23/10/2026.
- Início planejado: 16/10, com duração não informada.
- Sábado, 17/10: das 8h às 20h, podendo se estender até 21h.
- Domingo, 18/10: aproximadamente 5 horas.
- Segunda, terça e quarta: 3 horas por dia, totalizando 9 horas.
- A janela originalmente informada para 17–21/10 soma 26–27 horas, antes de descontar pausas e trabalho já realizado.
- Não foi recebida base de dados; o material disponível é o TAPI.
- Em 17/10, após consultar a organização, o aluno confirmou que não haverá base fornecida pela Inteli Academy. A obtenção de dados passa a depender de uma fonte independente.
- Fonte pretendida: YouTube Data API v3. Setores inicialmente pretendidos: moda e beleza.
- Em 17/10, após avaliar alternativas, o aluno reafirmou YouTube, moda/beleza e prazo fixo. Autorizou buscar criadores e conteúdo da plataforma com ferramentas/IA para captura em lote. A captura de metadados foi iniciada pela API; disponibilidade da mídia é verificada separadamente. A referência a virais não será usada para eliminar publicações de baixo desempenho da base.
- Prioridades: qualidade preditiva, avaliação válida, explicação do fluxo e prevenção tanto de vazamento estatístico quanto de exposição de dados e credenciais.
- O aluno quer conseguir explicar o que acontece, como, onde e por que cada escolha foi feita.
- O aluno já programa em Python e está aprendendo machine learning.
- O aluno concordou com a estratégia conjunta para os dois setores, a comparação multimodal e a organização do trabalho descritas abaixo.
- O aluno informou ter plano Enterprise e poder deixar chats e agentes trabalhando enquanto dorme, se necessário.
- Em 18/10, o aluno confirmou Google AI Plus e pediu proposta para dividir trabalho com o Codex, incluindo instalação/configuração. O [roteiro de agentes](configuracao-de-agentes.md) é uma proposta de ferramentas independentes e troca de relatórios; não registra instalação, autenticação Google ou mudança de configuração global já executadas. Benefícios de Pro e créditos de API não foram presumidos.
- Os commits devem ser frequentes e organizados por mudanças coerentes, sem acumular assuntos independentes nem fragmentar artificialmente uma mesma mudança.
- A primeira versão foca divulgação, com visualizações como alvo principal e curtidas como informação complementar para análise.
- Em 17/10, o aluno reafirmou o foco em identificar potencial de viralização. A previsão/ranking de views no horizonte aprovado continua sendo a operacionalização; não há limiar binário de viralidade definido. A seleção de alto alcance para o piloto técnico não elimina exemplos de baixo/médio alcance da futura base de treino e avaliação.
- A YouTube Data API v3 está ativada e a chave foi configurada no `.env` local, ignorado pelo Git. Em 16/10, uma consulta mínima de verificação retornou HTTP 200 e um vídeo, sem exibir a chave nem salvar a resposta. O cliente OAuth existente no console não foi necessário para essa consulta pública.
- Em 17/10, o aluno escolheu API externa para o subagente explicador e quer testar NVIDIA NIM. Execução local via Ollama deixa de ser a escolha desse componente. A preferência se refere ao explicador, não autoriza transferir arquivos de mídia nem mudar os extratores automaticamente.
- Em 17/10, o aluno confirmou o limite operacional inicial de cinco vídeos por requisição. Adotar análise individual para um candidato e comparação para dois a cinco; três permanece um exemplo de demonstração.

## Caso de uso confirmado

Um produtor de conteúdo de moda envia de um a cinco vídeos inéditos e descreve, em texto, a intenção da campanha. Com um vídeo recebe análise individual; com dois a cinco, comparação para escolher qual criativo priorizar para patrocínio. Os arquivos já são os dados brutos dos criativos; o que ainda não existe são métricas observadas de suas publicações. A demonstração principal pode continuar usando três candidatos.

Os candidatos pertencem à mesma decisão de campanha. O treinamento, por sua vez, deve usar referências de diversos canais do setor. O usuário deseja que o sistema consiga analisar conteúdo de um canal novo, em vez de depender de ter visto aquele canal durante o treinamento.

## Objetivo e métricas aprovados

O objetivo de campanha suportado nesta primeira versão é divulgação. O modelo estatístico terá visualizações como alvo principal; o horizonte de observação ainda precisa ser definido conforme a viabilidade dos dados. A ferramenta apoiará a priorização de criativos para um teste de divulgação, com previsão, intervalo, ordenação e explicação. Esse resultado não representa uma previsão validada de retorno da mídia paga.

Curtidas serão uma informação complementar na análise retrospectiva da base e dos resultados, quando disponíveis. A expressão do aluno "feature extra para análise" é entendida como informação analítica complementar: as curtidas observadas do próprio vídeo não serão uma entrada para prever suas visualizações antes da publicação.

Um criativo inédito não tem curtidas observadas. Nesta versão, não será exigida uma previsão numérica adicional de curtidas. Se a explicação citar métricas de referências históricas, deverá identificar sua origem e respeitar os limites temporais e de separação dos dados. Histórico de curtidas de outras publicações só poderá virar atributo se sua disponibilidade anterior ao instante previsto for demonstrada e se isso fizer parte do contrato aprovado.

Vendas, leads e conversões ficam fora dos alvos preditivos desta entrega. Compartilhamentos e retenção não serão exigidos, pois a coleta pública planejada não fornece essas métricas dos canais de terceiros.

### Consequências para o desenho ainda em discussão

- Extrair sinais visuais, de áudio e de texto dos vídeos de referência e dos vídeos inéditos de maneira consistente.
- Só usar entradas que também possam estar disponíveis antes da publicação dos candidatos. Contexto e histórico do canal, se adotados, devem ter contrato e disponibilidade declarados; não podem ser presumidos a partir das métricas futuras do candidato.
- Interpretar o objetivo textual como informação de campanha. Alterar esse texto não muda automaticamente o alvo para o qual o modelo estatístico foi treinado.
- Avaliar a generalização com canais inteiros reservados, mantendo também a análise temporal exigida pelo projeto. Diversidade de canais e retirada de identificadores, sozinhas, não comprovam independência do canal nem efeito causal do conteúdo.
- Distinguir a previsão do indicador público aprendido da análise qualitativa de aderência ao objetivo da campanha. A forma de combinar essas evidências na recomendação ainda será definida.
- Prever desempenho público observado não equivale a prever retorno do investimento em mídia paga. A contagem pública pode incluir visualizações orgânicas e de anúncios sem que a consulta pública informe a composição.
- Como os candidatos são inéditos, definir quem pode receber seus arquivos, onde serão armazenados e por quanto tempo antes de escolher os serviços de processamento.

## Estratégia de modelos aprovada

Começar com um pipeline conjunto para moda e beleza, com o setor como informação de entrada. Separar os resultados de avaliação por setor e canal, além do resultado agregado.

Especializar por setor restringe o domínio de aplicação, mas não elimina a necessidade de generalizar para vídeos novos. A divisão também reduz os exemplos disponíveis para cada ajuste. Não há evidência coletada que demonstre qual abordagem será superior neste projeto.

Priorizar uma referência simples e duas configurações comparáveis do pipeline: metadados/texto e metadados/texto acrescidos da camada multimodal definida no escopo. Essa comparação mede o ganho da informação multimodal; é diferente de comparar especialistas por setor.

Em 17/10, o aluno aprovou os três experimentos: A = CatBoost com metadados/texto da fala; B = CatBoost completo; C = LightGBM com os mesmos atributos completos de B. São três configurações, não uma matriz com todos os algoritmos e modalidades. A mediana é uma referência calculada no treino, não outra cadeia de extração. A transcrição é compartilhada na ablação. Random Forest e XGBoost ficam fora do caminho obrigatório; Ridge voltou à discussão somente como comparador opcional.

A comparação A/B mede o acréscimo de atributos no CatBoost; B/C compara bibliotecas nos atributos completos. Esse desenho é válido para essas duas perguntas, mas não demonstra ganho multimodal no LightGBM nem resolve a interação entre biblioteca e representação. A ordem aprovada é mediana → A → B → C. No piloto, verificar todas as modalidades em poucos arquivos para descobrir falhas cedo. A execução não muda automaticamente de ordem nem elimina A após ver resultados.

Extensão opcional aprovada: acrescentar Ridge com os atributos completos depois do núcleo A/B/C, como referência linear de erro e ranking. Não bloqueia avaliação ou entrega se adiada. Imputação, codificação de categorias e escala devem ser ajustadas somente no treino. Não incluir outra cadeia de extração, todos os cruzamentos de modalidades, intervalos ou integração de Ridge no serviço. Ele não vira candidato completo de produção automaticamente: a entrega exige faixa e explicação compatíveis. Registrar resultado negativo ou superioridade, se observados, sem selecionar pelo teste final.

Para o explicador NIM, o aluno confirmou o ID `meta/llama-3.3-70b-instruct` em 17/10. Ele será o primeiro candidato testado para a função, sem superioridade experimental já demonstrada. A configuração NVIDIA foi posteriormente preenchida no `.env` local; nenhuma inferência NIM foi validada até este checkpoint. `.env.example` declara `NVIDIA_API_KEY` e `NVIDIA_MODEL` vazios; isso não equivale a um carregador implementado. Primeiro teste: evidências sintéticas, verificando português, fidelidade aos números, esquema e tempo de resposta. Uso com informação confidencial depende das condições do endpoint e não está liberado pela escolha do provedor.

Checkpoint técnico de 18/10: CatBoost 1.2.10 e LightGBM 4.7.0 passaram em treino/inferência/recarga com dados inteiramente sintéticos; as dependências foram travadas e os 47 testes existentes passaram. As duas requisições NIM ao Llama escolhido retornaram HTTP 410; o catálogo NVIDIA informa que seu endpoint gratuito foi descontinuado. Procedimento, evidências e limites estão em [issue-1-primeira-amostra.md](issue-1-primeira-amostra.md). Treino real, A/B/C e condições da fonte continuam pendentes.

O diagnóstico adicional esclareceu a dúvida sobre API ativa: a listagem NIM respondeu HTTP 200, mas não inclui o Llama escolhido. Uma solicitação mínima ao mesmo modelo retornou HTTP 410 com mensagem explícita do provedor de fim de vida em 26/08/2026. API/conta ativa não implica disponibilidade desse modelo hospedado; o acesso da chave a uma inferência utilizável ainda não foi demonstrado.

Após o aluno enviar a captura e o View Code com o Nemotron selecionado, `NVIDIA_MODEL` foi atualizado para `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`, preservando a chave e demais linhas. O ID consta na listagem NIM, mas as tentativas limitadas retornaram HTTP 503 com mensagem de capacidade local do worker atingida (16/16). Não houve resposta gerada para avaliar; a validação do explicador permanece pendente. Esta escolha continua restrita ao explicador de texto: não autoriza envio de mídia real nem muda os extratores. O seletor do painel ainda mostrar o Llama não contraria a mensagem explícita de fim de vida no endpoint.

Investigar especialistas apenas se a validação apresentar erros sistemáticos por setor e houver tempo para uma comparação justa. Escolher usando validação; usar o teste reservado para avaliar a solução já escolhida.

## Organização aprovada dos chats

- Chat principal: problema, escopo, arquitetura, decisões de experimento, integração e aprendizagem.
- Chat de execução: uma issue relevante, pequena o bastante para concluir e demonstrar em um bloco de trabalho. Mudanças dependentes e pequenas podem continuar no mesmo chat.
- Subagentes: investigação, consulta a documentação e revisão de alterações bem delimitadas.
- Um executor de código por árvore de trabalho. Um revisor pode analisar o resultado sem editar os mesmos arquivos.
- Até duas frentes de implementação apenas quando os contratos e responsabilidades estiverem estáveis, em worktrees diferentes. O limite é um teto, não uma meta.
- Um responsável pela integração: conferir o resultado combinado e executar a verificação do fluxo completo.

Subagentes dividem o trabalho e o contexto; worktrees separam cópias de trabalho do código. Uma coisa não substitui a outra. Worktrees também não isolam automaticamente serviços externos, cotas de API ou pastas de dados compartilhadas.

Antes de usar worktrees, consolidar um primeiro estado versionado com instruções e decisões comuns. Cada chat de execução recebe explicitamente a issue e as referências necessárias; o histórico de conversa não deve ser a única fonte das decisões.

Para a passagem da #1 à implementação da #2, recomenda-se um novo chat de execução com este briefing, a seção P2 do backlog e o checkpoint da primeira amostra. A tarefa atual pode ser concluída no chat principal; o novo chat recebe uma entrega delimitada, o estado real dos dados e as pendências do NIM. A mudança de chat organiza o contexto; não libera dependências científicas nem autoriza implementações concorrentes na mesma árvore. O aluno pediu aviso antes dessa passagem, em vez de acumular as próximas issues no histórico principal.

## Briefing mínimo de cada issue

1. Resultado observável e motivo de ele ser necessário.
2. Entradas, saídas e contratos a preservar.
3. Critérios de aceitação, limites e dependências.
4. Verificação apropriada, incluindo riscos de dados relevantes.
5. Conceito que o aluno praticará e precisará explicar.
6. Evidências finais: alterações, verificações realizadas, resultados e limitações.

As issues devem entregar um percurso estreito e demonstrável. A primeira passagem pode usar uma referência simples de predição, explicitamente identificada. Evoluções acrescentam capacidades ao mesmo fluxo e mantêm os contratos verificáveis.

## Política de commits

Fazer commits ao concluir unidades lógicas de trabalho. A frequência acompanha a conclusão dessas unidades, sem metas artificiais de tempo, quantidade de commits ou número de linhas.

- Cada commit deve ter uma intenção principal, descrita por uma mensagem clara e específica.
- Manter juntos o código, os testes e a documentação necessários para entender e verificar a mesma mudança.
- Separar mudanças independentes, inclusive refatorações sem relação com a entrega em andamento.
- Dividir uma entrega maior em passos coerentes e verificáveis. Uma issue pode resultar em vários commits quando cada passo fizer sentido isoladamente.
- Revisar o conteúdo selecionado e executar as verificações apropriadas antes de registrar o commit.
- Excluir segredos, dados sensíveis, arquivos temporários e resultados locais que não devam ser versionados.
- Aplicar a mesma política a chats de execução, subagentes e trabalho noturno.

Por exemplo, adicionar uma regra de validação de entrada com seus testes é uma unidade coerente; criar commits separados para cada arquivo dessa mudança não é necessário. Coleta de dados e explicação de previsões, quando independentes, devem ser registradas em commits distintos.

## Ciclo de execução e aprendizagem aprovado

Em cada bloco, reservar tempo para definir o resultado, praticar uma parte pequena, concluir a implementação, verificar o comportamento e explicar a solução. Em um bloco de 3 horas, uma distribuição inicial possível é: 15 minutos de orientação, 105 de execução, 30 de verificação/integração e 30 de explicação e registro. Ajustar depois da primeira experiência.

O aluno conduz hipóteses, critérios de avaliação e interpretação dos resultados. Nas partes que quer dominar, pratica primeiro uma versão pequena. A IA ajuda com investigação, revisão e ampliação de tarefas repetitivas após haver um exemplo compreendido e verificável.

Como o aluno já programa em Python, a prática deve priorizar formulação do alvo, disponibilidade das informações, baseline, separação dos dados, interpretação de métricas, intervalos e análise de erros. O aluno percorre uma amostra pequena para entender a transformação dos dados e as saídas do modelo; a IA pode ampliar a execução depois desse entendimento.

Na curadoria dos vinte candidatos, a IA faz a primeira triagem e o aluno revisa uma amostra e resultados ambíguos ou contraditórios. A sequência de vinte confirmações manuais foi suspensa em 18/10. Separar sugestões baseadas em metadados, atributos extraídos de imagem/fala e observações humanas, preservando a origem de cada informação. Campos sem evidência ficam desconhecidos; a falta de acesso audiovisual utilizável não transfere ao aluno a obrigação de preencher todos manualmente. As revisões já conhecidas são controles de desenvolvimento, não uma amostra independente para medir qualidade. A auditoria por amostragem acontece após a pré-classificação audiovisual e não constitui uma estimativa precisa de acurácia com poucos exemplos.

O coordenador e o revisor das decisões de ML devem usar capacidade de raciocínio adequada. Modelos econômicos podem executar tarefas estreitas com critérios claros. Paralelismo acrescenta trabalho de coordenação e consumo de recursos; a economia precisa ser avaliada pelo esforço total e pelo retrabalho, não só pelo modelo escolhido.

## Uso de execução noturna

Usar o período noturno para tarefas delimitadas e previamente verificadas em uma amostra: coleta autorizada com limites de cota, extração de atributos com cache, experimentos definidos com treino/validação e revisão de resultados. O aluno confere evidências, falhas e conclusões ao retomar o trabalho.

Cada tarefa deve declarar entrada, resultado esperado, orçamento de tempo/cota/custo, condições de parada e localização dos resultados. Manter o teste final fora da seleção automática de modelos. Decisões sobre alvo, novos serviços externos, dados confidenciais ou mudanças de arquitetura devem voltar para a discussão.

A execução que depende da pasta local requer a máquina ligada, disponível e o aplicativo em execução. Uma tarefa exclusivamente na nuvem precisa receber contexto acessível naquele ambiente; o acesso à pasta local não é automático. Disponibilidade e permissões dependem também das configurações do workspace Enterprise.

Não foi configurada automação nem iniciado trabalho noturno: a conversa ainda está definindo os contratos que permitirão tarefas autônomas úteis. A possibilidade de trabalho noturno não amplia as horas disponíveis para aprendizado, revisão e integração pelo aluno.

## Requisitos de prevenção de vazamento

No experimento, declarar quais informações estariam disponíveis no momento da previsão. Separar treino, validação e teste conforme a pergunta, antes de ajustar transformações aprendidas. Impedimento de acesso ao futuro exige verificar datas de observação e disponibilidade dos rótulos, além das datas de publicação.

A coleta atual de contagens acumuladas não reconstrói automaticamente desempenho aos 30 dias nem estatísticas históricas do canal. A interpretação dos resultados deve registrar essa limitação. Títulos e descrições atuais também podem diferir das versões publicadas inicialmente.

Na proteção de informações, manter segredos fora de prompts, commits, logs, notebooks e documentos compartilhados. Usar somente conteúdo autorizado nas ferramentas externas. Regras de leitura e permissões devem proteger arquivos sensíveis; ignorar um arquivo no Git não basta para torná-lo inacessível a um agente. Definir separadamente o acesso de cada componente ao que ele precisa para executar.

O `.gitignore` exclui credenciais, ambientes/caches e pastas locais destinadas a dados coletados, mídias, experimentos e modelos. Manter esses arquivos nas pastas previstas, como `data/raw/`, `data/processed/`, `uploads/` e `artifacts/`; não espalhar dados privados pela árvore de código. Documentação pública, exemplos sintéticos, esquemas, configurações sem segredos e arquivos de dependências devem continuar versionáveis. O TAPI externo recebido permanece ignorado.

A configuração pública de referência é `.env.example`, com `YOUTUBE_API_KEY` vazia. A chave real foi preenchida somente no `.env` local; sua configuração deve manter a restrição à YouTube Data API v3. A verificação de conexão enviou a chave em um cabeçalho HTTPS, sem colocá-la na URL ou nas saídas exibidas. Essa verificação não implica que exista um carregador de configuração ou coletor implementado. A política de exclusão não substitui revisão dos arquivos selecionados para cada commit.

## Marcos propostos

| Data | Entrega verificável |
| --- | --- |
| 16/10 | Definir problema, alvo, protocolo e desenho; verificar acesso viável a dados e mídia. |
| 17/10 | Obter amostra auditável, baseline e primeiro fluxo executável; iniciar multimodal e integração. |
| 18/10 | Fechar multimodal mínimo iniciado no sábado e executar a comparação principal. |
| 19/10 — 3h | Consolidar previsão, intervalo, explicação e integração; resolver pendências obrigatórias. |
| 20/10 — 3h | Encerrar funcionalidades; verificar avaliação final, reprodução e documentação. |
| 21/10 — 3h | Corrigir falhas, conferir pacote e entregar com margem antes de 23h59. |

O checkpoint principal é o fluxo executável no sábado. Se os dados ou a integração não forem viáveis, revisar imediatamente volume e complexidade. Qualquer redução de requisito obrigatório deve ser explícita e discutida. Os dias após a entrega ficam disponíveis para ensaio e preparação da apresentação.

## Decisões ainda abertas

- Prioridades específicas de aprendizagem dentro de machine learning.
- Horizonte de observação das visualizações e interpretação da contagem prevista compatíveis com os dados disponíveis.
- Viabilidade de obtenção autorizada de vídeo e áudio para o multimodal.
- Recorte final de dados e funcionalidades, mantendo a estratégia conjunta aprovada.
- Confirmar execução dos contratos e critérios publicados; qualquer revisão necessária deve registrar o impacto antes de ampliar coleta ou treino. A divisão das sete issues já foi aprovada e publicada.

## Referências consultadas

- [Codex: subagentes e escolha de modelos](https://learn.chatgpt.com/docs/agent-configuration/subagents).
- [Codex: worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees).
- [Codex: permissões de leitura](https://learn.chatgpt.com/docs/permissions#deny-reads-with-exact-paths-or-globs).
- [Codex: tarefas em segundo plano](https://learn.chatgpt.com/docs/automations).
- [Scikit-learn: validação e generalização](https://scikit-learn.org/stable/modules/learning_curve.html).
- [Scikit-learn: avaliação de grupos não vistos](https://scikit-learn.org/stable/modules/cross_validation.html#cross-validation-iterators-for-grouped-data).
- [YouTube: composição das visualizações públicas](https://support.google.com/youtube/answer/2375431?hl=en-NG).
- [YouTube: chave de API e OAuth](https://developers.google.com/youtube/registering_an_application).
- [Google Cloud: proteção de chaves de API](https://docs.cloud.google.com/docs/authentication/api-keys-best-practices).
- [Skills de Matt Pocock](https://github.com/mattpocock/skills).
- TAPI disponível localmente, com prazo de entrega corrigido pelas informações do aluno.

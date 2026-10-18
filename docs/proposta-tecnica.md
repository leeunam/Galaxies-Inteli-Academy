# Proposta técnica para revisão

Atualizada em 17/10/2026. Estado: **plano autorizado para execução e sete issues publicadas; API externa NVIDIA NIM, limite de cinco candidatos, A → B → C e Ridge opcional confirmados**. Houve coleta de metadados e extração temporária de três candidatos reais; treinamento e avaliação preditiva ainda não foram executados. Fonte utilizável em escala, alvo efetivamente observável e viabilidade estatística dependem do checkpoint da issue #1. Este documento não substitui os acordos confirmados em `briefing-de-trabalho.md`.

As justificativas de 17/10 sobre provedor, quantidade de candidatos e famílias de modelos estão em [alternativas-tecnicas.md](alternativas-tecnicas.md). A escolha do provedor não autoriza enviar arquivos ou informações confidenciais em desacordo com suas condições; o primeiro teste NIM será sintético.

## 1. Resultado e limites da entrega

Analisar um arquivo ou comparar de dois a cinco arquivos de vídeo inéditos de uma mesma campanha de divulgação, em moda ou beleza. Devolver previsão exploratória de visualizações, faixa de predição, atributos observados e explicação apoiada nas evidências. Com múltiplos candidatos, acrescentar ranking calculado e indicação de qual criativo testar primeiro. Três candidatos continuam sendo o exemplo principal da demonstração.

Recorte inicial proposto: vídeos verticais de até 60 segundos, conteúdo em português brasileiro, referências dos dois setores e de vários canais. Esse limite de duração é uma escolha do experimento, não uma definição de Shorts. Identificar o formato por curadoria e propriedades do arquivo; duração isolada não identifica Shorts com segurança. Usar o mesmo contrato de mídia no treino e nos candidatos.

O sistema será usado antes da publicação, mas a avaliação inicialmente possível é retrospectiva. Ela não comprova previsão prospectiva, efeito causal do conteúdo, alcance único, retorno pago ou desempenho do canal específico do cliente. Visualizações públicas podem misturar distribuição paga e orgânica. Curtidas ficam no diagnóstico retrospectivo, fora das entradas do preditor.

## 2. Três alternativas consideradas

| Alternativa | Benefício | Custo ou limite | Decisão proposta |
| --- | --- | --- | --- |
| Snapshot próprio, idade estreita e canais reservados | Conecta o experimento ao domínio e ao processamento dos arquivos | Contagem atual, mídia e permissão ainda não asseguradas; validade retrospectiva | Caminho principal, condicionado à viabilidade dos dados |
| Dataset histórico como SMTPD | Pode fornecer contagens observadas em um horizonte exato | Acesso, licença, setores, formato e mídia completa ainda não verificados | Alternativa auxiliar; não substitui automaticamente o experimento principal |
| Coleta prospectiva curta | Congela observações de agora para avaliar depois | Pouco tempo, poucos exemplos e alvo diferente se houver popularidade inicial | Fora do caminho crítico até 21/10 |

Uma base já licenciada e adequada pode mudar a escolha. Nesse caso, atualizar o contrato antes de consultar seus resultados. Não juntar métricas, plataformas ou horizontes incompatíveis para aumentar o volume.

## 3. Alvo e avaliação

### Alvo observável

Usar referências com **30 <= idade em dias < 37** no instante da coleta. Registrar `published_at`, `observed_at`, definição da contagem e sua origem. A fórmula é `y = log1p(view_count_observed)`; a saída central é uma mediana condicional estimada, convertida de volta para views.

Rotular a saída: **estimativa exploratória baseada em referências observadas entre 30 e 37 dias**. Não chamar de views exatamente no dia 30, nem dividir views pela idade para fabricar esse valor. A API de vídeos fornece a contagem corrente; não reconstrói automaticamente uma série histórica. Títulos, descrições e versões da mídia também podem ter sido alterados após a publicação.

A janela respeita a idade mínima sugerida no TAPI, mas pode reduzir muito a amostra. Uma janela mais larga é uma mudança de protocolo, não um ajuste automático após ver métricas. O piloto deve informar número de vídeos por canal e setor, exclusões e viabilidade da janela. O volume indicativo de 5–15 mil vídeos do TAPI não é compromisso deste cronograma sem uma base pronta.

### Partições e baselines

- Reservar aproximadamente 60% dos canais para treino, 20% para validação e 20% para teste, preservando representação dos setores quando possível. Fixar semente e manifesto antes dos ajustes. Relatar contagens reais; com poucos canais, declarar a fragilidade em vez de esconder o problema com divisão aleatória de vídeos.
- Um canal e suas duplicatas/republicações reconhecidas pertencem a uma única partição. IDs de canal servem para auditoria e agrupamento, não como atributos do preditor.
- Ajustar imputação, redução de dimensão e quaisquer transformações aprendidas somente no treino. Para CatBoost M1/M2: profundidade 4 ou 6 e regularização L2 3 ou 10. Para LightGBM completo: 7 ou 15 folhas e mínimo de 5 ou 20 exemplos por folha, com profundidade máxima 6 e L2 3. Em ambos: taxa 0,05, até 500 iterações, parada após 50 iterações sem melhoria na validação e semente 42. São no máximo quatro configurações por quantil e experimento, sem busca aberta; registrar também tempo, pois quatro ajustes de bibliotecas diferentes não têm necessariamente o mesmo custo. Escolher q50 pelo MAE log médio por canal; cada extremo pela sua perda quantílica média por canal. Congelar a escolha antes de abrir o teste.
- B0: mediana das views transformadas no treino, por setor. Bcanal: mediana do canal calculada somente com suporte de treino, com fallback para B0. Em canais inteiramente novos, esse fallback é esperado. Não usar o resultado dos próprios vídeos de teste para construir histórico ou normalizar seus alvos.
- M1: CatBoost com setor, propriedades do arquivo e texto da fala transcrito. M2: exatamente M1 acrescido dos atributos visuais, VLM e medidas acústicas. A ablação principal mede esse acréscimo; a transcrição é compartilhada. Não descrevê-la como remoção de todo o áudio do M1.
- Comparador de algoritmo: LightGBM com exatamente os atributos completos de M2. Portanto, três experimentos treinados: CatBoost M1, CatBoost M2 e LightGBM completo. Não há um terceiro conjunto de informações chamado M3. Ridge, Random Forest e XGBoost ficam fora da execução obrigatória proposta.
- Comparar B0/Bcanal e os três experimentos nas mesmas linhas e partições. Extração é compartilhada e cacheada; ablação muda as colunas usadas, sem coletar ou processar a mídia inteira novamente. Não permitir que falhas de extração removam silenciosamente exemplos apenas de uma configuração. Definir elegibilidade antes de comparar; registrar cobertura de extração.

O desenho não precisa incluir LightGBM com atributos reduzidos para sustentar A/B (ganho de informação no CatBoost) e B/C (biblioteca com informação completa). Essa célula adicional seria necessária para avaliar o ganho correspondente no LightGBM e a interação entre biblioteca e representação. Não generalizar o ganho observado no CatBoost para qualquer algoritmo.

Ordem aprovada: após o piloto de todas as modalidades em poucos arquivos, executar mediana → A → B → C. A fornece diagnóstico inicial com menos dependências; B/C compartilham a matriz completa quando estiver pronta. A ordem não substitui manter partições, critérios e teste final congelados. Não alterar a sequência ou o protocolo silenciosamente após consultar resultados.

Ridge pode ser acrescentado como comparador pontual opcional nos atributos completos, após o núcleo A/B/C. Ajustar imputação, codificação de categorias e escala somente no treino. Reportar erro e ordenação no mesmo conjunto, sem exigir novos extratores, intervalos, SHAP ou adaptador de serviço para essa comparação. Um bom resultado do Ridge não o transforma automaticamente num artefato que cumpre o contrato completo; uma adoção exigiria outra decisão explícita.

Acrescentar diagnóstico por corte na data de publicação, com modelos ajustados no lado anterior do corte e avaliação no posterior. Declarar sobreposição de canais ou aplicar separação conjunta quando houver suporte. Em snapshot único, publicação e idade estão ligadas: o corte também muda o tempo de exposição. Esse diagnóstico **não é backtest prospectivo** e não isola deriva temporal. Uma exigência de avaliação temporal estrita com informação disponível à época permanece não atendida sem dados históricos adequados.

### Métricas e decisão

- Principal: MAE em `log1p(views)`, incluindo média dos erros médios por canal, para canais prolíficos não dominarem o resultado.
- Complementares: MAE em views; MAPE apenas onde views > 0, informando a quantidade excluída e sua instabilidade em contagens pequenas; resultados e tamanho da amostra por setor.
- Ranking: Spearman e acerto de pares dentro de cada canal reservado, com agregação por canal. O protocolo exige ao menos três vídeos e variação nos valores para reportar Spearman por canal; é uma regra de suporte, não uma exigência matemática, pois dois pares sem empate já produzem +1 ou -1. Pares empatados têm regra declarada. Se faltar suporte, marcar a métrica como não estimável. Correlação global será secundária.
- Intervalos: em cada experimento, ajustar quantis 0,1 / 0,5 / 0,9 em CPU, usando a perda quantílica da biblioteca correspondente. Faixa nominal central de 80%; medir cobertura e largura no teste, também por setor. Quantis estimados não garantem cobertura. Em cruzamentos, preservar a previsão q50 e reparar somente os limites: inferior = mínimo dos três valores brutos; superior = máximo dos três. Registrar a ocorrência e a política; avaliar cobertura/largura exatamente após o reparo. O ranking e o SHAP continuam associados ao modelo q50. Três experimentos implicam mais de três ajustes por causa dos quantis e da validação, automatizados no mesmo procedimento.
- Explicar a previsão central com SHAP nativo do CatBoost ou contribuições SHAP do LightGBM (`pred_contrib`), conforme o artefato selecionado, em escala log. Contribuições de embeddings serão agrupadas por modalidade, sem inventar significados para componentes de PCA. SHAP não comprova causalidade.

O critério científico é comparar de forma reproduzível contra as referências e relatar diferenças, incerteza e falhas. Não há percentual de acerto prometido antes do piloto. Um candidato completo só substitui CatBoost M1 se reduzir o MAE log médio por canal na validação e não piorar a perda quantílica média dos três quantis. Entre candidatos completos elegíveis, escolher menor MAE log; empate favorece CatBoost para reduzir integrações adicionais. Sem ganho, manter M1 e demonstrar os completos como comparação experimental. Essa regra não garante estabilidade estatística numa amostra pequena. Um resultado abaixo do baseline é um resultado negativo a explicar, não uma métrica a ocultar.

Não usar como features: resultados do próprio vídeo; inscritos e estatísticas atuais do canal; idade acumulada após publicação; URL/ID; nome/caminho/datas do sistema de arquivos; posição em busca; métricas de publicações cuja disponibilidade anterior não esteja demonstrada. Sem histórico confiável, `relative_to_channel` será indisponível, com motivo explícito. Marca, rosto e estilo ainda podem carregar sinais de identidade/audiência; retirar IDs e reservar canais não demonstra independência causal do canal.

## 4. Viabilidade dos dados: primeira entrega

Antes da coleta em escala, produzir um manifesto com origem dos arquivos, permissão/licença aplicável, chave de canal, setor, datas, contagens, formato e hash da mídia. O arquivo mestre do produtor não é requisito técnico: uma cópia com qualidade suficiente para os extratores pode atender ao processamento. A chave pública e a possibilidade técnica de aquisição, entretanto, não demonstram as condições de uso do conteúdo.

Em 17/10, o aluno confirmou a preferência por aquisição temporária automatizada com yt-dlp e manutenção de imagem/fala. O desenho é: uma referência por vez → pasta temporária privada → validação e hash → extração compartilhada de todas as modalidades → gravação atômica dos atributos e estado → remoção de vídeo, áudio, frames e intermediários. API e downloader não compartilham credenciais desnecessárias. Usar URL canônica construída de um ID validado, limites de bytes/duração/tempo e tentativas finitas; não incorporar configurações/plugins locais ou mecanismos de contorno de acesso.

O supervisor deve limpar também após erro e cancelamento, encerrando os processos filhos antes da remoção. Queda da máquina ou encerramento forçado pode deixar resíduos: conferir trabalhos órfãos na retomada, preservando os ativos. Persistir apenas atributos, transcrição necessária, evidências estruturadas e metadados de reprodução em pastas privadas ignoradas; apagar o vídeo não torna esses derivados anônimos. A/B/C reutilizam o mesmo cache, sem repetir downloads. Registrar versões, configuração e hash; o hash não permite recuperar um vídeo posteriormente removido ou alterado na origem, e uma troca de extrator pode exigir nova aquisição.

O adaptador yt-dlp foi instalado com EJS e validado em três URLs públicas da amostra, usando Node 22 e FFmpeg fornecido por imageio-ffmpeg. O [piloto real](piloto-youtube-real.md) confirmou download, extração local e limpeza em 3/3 casos; os atributos VLM foram reprovados. O ensaio anterior no Commons e as revisões dos extratores permanecem documentados no [piloto inicial](piloto-extracao-temporaria.md). Python 3.11, PyTorch CPU e dependências estão fixados em `uv.lock`; não houve instalação global de FFmpeg/ffprobe. As [dependências do yt-dlp](https://github.com/yt-dlp/yt-dlp#dependencies) e as condições da fonte continuam separadas da extração. As [políticas da API, III.E.1](https://developers.google.com/youtube/terms/developer-policies), exigem aprovação prévia escrita do YouTube para cópias audiovisuais; armazenamento temporário e êxito técnico não demonstram conformidade. O teste não resolve as condições de uso nem disponibilidade de todo o corpus.

### Campos mínimos e papel no experimento

| Papel | Campos | Uso |
| --- | --- | --- |
| Entradas do preditor | Setor, duração e atributos da fala, imagem e áudio definidos para A/B/C | Disponíveis também antes da publicação dos inéditos |
| Rótulo | Views observadas, transformadas em `log1p` no treino | Resultado a prever; fora das entradas |
| Diagnóstico retrospectivo | Curtidas, quando disponíveis | Análise complementar; fora das entradas |
| Auditoria e avaliação | ID/link da publicação, chave de canal, `published_at`, `observed_at`, origem, estados, hash e versões | Associação de registros, canais reservados, idade da contagem e reprodução; fora das entradas |

Dispensar tags. A identidade do canal e as datas não serão preditores no recorte atual. Manter uma chave estável de canal permite agrupar publicações mesmo com pseudonimização; não é necessário expor nome/inscritos. Sem essa chave, reservar canais inteiros deixa de ser demonstrável. Sem publicação/coleta, não se verifica o horizonte de 30–37 dias nem a disponibilidade temporal do rótulo. Retirar o ID das entradas não elimina sinais de autoria existentes na voz, rosto, cenário ou estilo: é a avaliação com canais reservados que verifica parte dessa generalização.

As políticas da API impõem condições a downloads, agregação e métricas derivadas; ativar a API não resolve essas condições. Validar a adequação do uso pretendido antes da expansão. A escolha técnica de yt-dlp não autoriza contornar restrições de acesso nem resolve o enquadramento da fonte. A autorização sobre a obra e as condições da plataforma são verificações distintas. Esta proposta não conclui que todo uso de ML seja proibido ou permitido.

Piloto operacional: até 20 referências autorizadas, procurando dez canais e ambos os setores. Ele verifica esquema, extração e densidade da amostra; não serve como comprovação de qualidade preditiva. Incluir smoke test local de transcrição, CLIP e SmolVLM2 em poucos arquivos, compatibilidade de CatBoost/LightGBM e chamada ao explicador NIM com evidências sintéticas, antes de delegar lotes ou reservar apenas três horas para a integração. Medir tempo, pico de memória, tamanho dos arquivos, falhas e qualidade dos atributos em uma inspeção manual. Só então fixar o volume de extração compatível com a janela noturna e a disponibilidade real. Não confundir muitos vídeos de poucos canais com diversidade suficiente.

Checkpoint: concluir essa verificação hoje, se houver fonte disponível, ou no primeiro bloco de sábado. Sem mídia com métricas utilizáveis, a previsão supervisionada multimodal permanece dependente de dados. Fixtures sintéticas permitem testar a integração, mas não contam como evidência de desempenho. Expor a pendência e revisar o escopo; não substituir dados reais por resultados inventados.

## 5. Arquitetura abstrata

Adotar **uma aplicação Python modular e local**, com dois percursos. Eles compartilham o contrato e a implementação de extração.

**Preparação e treino:** fonte autorizada → manifesto e validação → mídia e métricas → partições congeladas → extração cacheada → transformações ajustadas no treino → baselines/M1/M2 → avaliação → artefato selecionado e manifesto.

**Uso:** cadastro local de um a cinco arquivos → IDs de criativos → função Python/MCP → validação → extração idêntica à do treino → previsão dos quantis → SHAP e comparáveis → ordenação por mediana prevista quando houver múltiplos candidatos → subagente explicador NIM → resposta validada.

O grafo LangGraph coordena etapas explícitas. O subagente explicador recebe somente evidências estruturadas, objetivo e brief validado; não acessa credenciais, arquivos arbitrários ou ferramentas de execução. A ordenação e os números pertencem ao código do preditor. A LLM comenta aderência e limitações; não altera previsão, faixa ou ranking.

### Responsabilidades e fronteiras

| Componente | Responsabilidade | Dependências permitidas |
| --- | --- | --- |
| Coleta/importação | Manifesto, datas, proveniência e métricas | Fonte aprovada; chave apenas no processo coletor |
| Ingestão de candidatos | Validar arquivo e emitir ID opaco | Pasta local autorizada; sem URLs arbitrárias |
| Extração | Converter mídia em atributos versionados e evidências | Modelos congelados; arquivo validado |
| Treino/avaliação | Produzir resultados e artefatos reproduzíveis | Dados elegíveis e manifesto de partições |
| Predição | Validar esquema e executar modelo congelado | Artefatos locais confiáveis e features compatíveis |
| Histórico/comparáveis | Selecionar até três referências do treino do mesmo setor por similaridade | Índice em memória e evidências autorizadas; nunca rótulos do teste |
| Explicação | Transformar evidências e SHAP em texto verificável | API NVIDIA NIM com conteúdo permitido; sem autonomia para recalcular métricas |
| Aplicação/MCP | Coordenar o caso de uso e devolver contrato estável | Interfaces anteriores; sem lógica de treino no pedido |

Comparáveis serão uma busca simples de cosseno sobre embeddings MiniLM normalizados da transcrição em um conjunto pequeno de treino, filtrado por setor e formato. Visualizações e curtidas não participam da seleção. Seus IDs, critérios, datas e origem ficam explícitos; métricas, quando exibidas, são observações retrospectivas com data, sem alegar disponibilidade histórica na publicação. São referências descritivas; não são prova causal ou previsão de verba. Ausência de fala ou de comparável adequado produz lista vazia e motivo.

## 6. Stack concreta proposta

| Uso | Escolha inicial | Justificativa |
| --- | --- | --- |
| Runtime e dependências | Python 3.11, uv, pyproject.toml e uv.lock | Compatível em princípio com o ambiente; uma instalação reproduzível |
| Configuração e contratos | Pydantic 2, pydantic-settings; JSON | Esquemas estritos; coletor lê apenas sua configuração |
| Acesso à API, se validado | HTTPX, endpoints oficiais v3 | Pedidos pequenos, timeout/backoff e controle explícito de credenciais |
| Dados | pandas, NumPy, PyArrow/Parquet; manifesto JSON | Análise tabular e persistência local simples |
| Mídia | FFmpeg/ffprobe e OpenCV headless | Duração, proporção, frames, áudio e medidas técnicas |
| Fala | faster-whisper; Systran/faster-whisper-small, CPU int8 | Transcrição em português, sem enviar os arquivos a uma API |
| Texto | sentence-transformers; paraphrase-multilingual-MiniLM-L12-v2 | Embedding multilíngue de 384 dimensões |
| Imagem | PyTorch CPU + Transformers; openai/clip-vit-base-patch32 | Encoder congelado de frames, sem treinar uma rede de vídeo |
| Atributos visuais | HuggingFaceTB/SmolVLM2-500M-Video-Instruct | VLM local pequeno; JSON e evidências auditáveis |
| Preditor | CatBoost CPU + LightGBM CPU + scikit-learn | Duas bibliotecas de boosting comparadas, quantis, PCA, métricas e contribuições SHAP |
| Orquestração | LangGraph StateGraph e subgrafo explicador | Estado explícito, transições limitadas e inspeção do fluxo |
| Explicador | API NVIDIA NIM hospedada; meta/llama-3.3-70b-instruct, confirmado pelo aluno | Português e explicação textual; qualidade, esquema e latência precisam ser testados |
| Integração | Função Python + FastMCP 4.1.0, transporte stdio | Mesmo serviço usado diretamente e por MCP local |
| Experimentos | JSON por execução + tabelas Parquet/CSV locais | Registro equivalente suficiente, sem um servidor adicional |
| Qualidade | pytest, pytest-asyncio, Ruff e GitHub Actions para verificações sem dados privados | Contratos, integração, estilo e reprodução do caminho público |

FastMCP 4.1.0 e LangGraph declaram suporte a Python 3.11. Ainda é necessário resolver e testar o conjunto real de dependências. As versões exatas dos pacotes e revisões dos pesos serão fixadas no lock e no manifesto após esse smoke test; não alegar compatibilidade de uma combinação ainda não instalada. Modelos abertos não dispensam registro de licença. FFmpeg depende também da licença da compilação utilizada.

Não fazem parte da entrega obrigatória: frontend elaborado, FastAPI/HTTP público, banco de vetores, PostgreSQL, Docker, fine-tuning dos encoders, especialistas por setor, Random Forest/XGBoost como experimentos adicionais, integração de Ridge no serviço, explicador local ou treinamento durante uma chamada do usuário. Ridge apenas como comparador pontual é opcional, condicionado à conclusão do núcleo. São extensões possíveis depois do núcleo comprovado.

### Política de extração

- Executar em CPU, batch 1, com carregamento sequencial dos modelos. Ambiente observado: cerca de 15 GiB de RAM, 12 threads e nenhuma GPU NVIDIA detectada. O FFmpeg empacotado foi validado no piloto real, sem instalação global. Foram medidos tempos e pico acumulado do processo nos pilotos; não são orçamento validado para extração em escala.
- Extrair seis frames com regra fixa que cubra início e restante do vídeo. Posições iniciais propostas: 0,2 s; 1,5 s; 2,8 s; 30%, 60% e 90% da duração. Limitar ao intervalo válido, ordenar e deduplicar. Aplicar a mesma regra a referências e candidatos.
- CLIP: média dos embeddings de frames normalizados. PCA ajustada só no treino; até 32 componentes, respeitando o tamanho do treino. Não usar thumbnail externa se o contrato do candidato não exige fornecê-la.
- SmolVLM2: até quatro frames nas posições 0,2 s; 1,5 s; 2,8 s e 60% da duração, aplicando a mesma limitação ao intervalo válido e deduplicação; batch 1, CPU FP32, maior lado 512; desativar divisão em recortes e verificar que o processador não reexpande os frames. Congelar prompt, revisão dos pesos e configuração do processador.
- Sete atributos VLM: produto visível nos frames amostrados dos primeiros 3 s, pessoa visível, close de produto, demonstração/aplicação, texto na tela, ambiente e formato da apresentação. Usar enumerações, `unknown` e referências aos frames. Observações se limitam às amostras: ausência em um frame não comprova ausência no vídeo inteiro. Não atribuir notas de viralidade ou inferir emoção, perfil pessoal ou qualidade profissional.
- Transcrever o áudio e dividir o texto em trechos dentro do limite de tokens do MiniLM; agregar embeddings por regra fixa. Sem fala gera ausência explícita, não texto inventado.
- Medidas baratas: brilho e saturação dos frames, RMS do áudio e densidade de fala, com unidades e escalas fixas. RMS não mede emoção nem qualidade musical. Não normalizar o volume de cada arquivo antes dessa medida.
- Cache identificado por hash do conteúdo, versão do esquema, extrator, pesos, prompt e parâmetros. Mudar qualquer parte invalida a etapa correspondente. Não usar apenas ID do vídeo como chave.

## 7. Contratos, falhas e proteção

Entrada de análise: `campaign_id`, lista de um a cinco `creative_ids` distintos, `sector` em moda/beleza, `objective=divulgacao` e `brief`. Um ID gera análise individual, sem comparação competitiva; dois a cinco geram comparação. A previsão de cada vídeo não depende da quantidade de concorrentes. O cadastro local associa os IDs aos arquivos. A tool não aceita caminhos ou URLs livres. Validar tamanho, tipo real, duração, resolução e pasta permitida, resolvendo caminhos e recusando escapes por links simbólicos. Limites operacionais de arquivo serão fixados pelo piloto e documentados, não deixados implícitos.

Saída: versão do esquema/modelo/extratores, definição do alvo, previsão central e quantis por candidato, ranking, evidências, drivers agrupados, aderência qualitativa, comparáveis, avisos e estado de cada etapa. Desempate numérico estável e explícito, sem afirmar superioridade quando a evidência for fraca. Sobreposição de intervalos não fornece a probabilidade de um candidato vencer.

Falhas previstas: mídia inválida, artefato incompatível, extração indisponível, timeout e JSON inválido. Uma tentativa de reparo do JSON; depois, falha estruturada. Falha de modalidade só permite previsão quando o modelo foi treinado para aquela ausência; caso contrário, retornar resultado incompleto. Não trocar de modelo silenciosamente. Explicador indisponível preserva números já calculados e marca a explicação como incompleta; a demonstração final precisa comprovar o caminho completo.

Vídeos inéditos, áudio e transcrições permanecem no ambiente local. Instalar pesos dos extratores antes do processamento privado e executar essa extração sem dependência de rede. Apenas o coletor acessa a chave do YouTube; apenas o adaptador do explicador usa a chave NVIDIA, sem expô-la ao modelo ou à resposta. Processos não herdam segredos desnecessários. Downloads de pesos e coleta são fases separadas do uso privado.

O explicador externo recebe somente o pacote de evidências necessário e permitido: IDs opacos, números, drivers agrupados, atributos e objetivo/brief reduzido. Isso ainda pode revelar informação confidencial. Os termos publicados de API Trial NVIDIA restringem conteúdo confidencial; primeiro teste com dados sintéticos. Para material real, conferir compatibilidade do conteúdo e do contrato antes de enviar; se incompatível, retornar restrição explícita em vez de transferir dados ou trocar o provedor silenciosamente. Não será usado explicador local como substituição automática à escolha externa do aluno.

O host MCP recebe a resposta da tool e pode processá-la fora da máquina. Portanto, stdio não garante confidencialidade de tudo: devolver somente os campos necessários; não incluir arquivos, transcrições completas, caminhos locais ou credenciais. Validar a política do host antes de usar material confidencial. Logs contêm IDs e códigos de erro, sem brief completo, prompts, transcrição, URLs com segredo ou dumps de entrada. `.gitignore` não controla leitura de arquivos por agentes.

Manter mídias, features, modelos e execuções nas pastas locais ignoradas já previstas. Versionar código, contratos, configurações sem segredos, manifestos públicos sem dados pessoais e resumos de resultados que possam ser compartilhados. Artefatos de modelo recebem versão e hash, com armazenamento local ou mecanismo de distribuição aprovado; não colocar pesos grandes no Git. Exclusão local de campanha deve remover mídia, transcrições e caches derivados; documentar retenção e não prometer apagar cópias no host.

## 8. Verificação e critérios de entrega

1. Dados: origem/permissão registradas, datas e alvo verificáveis, partições sem canal/duplicata cruzados, transformações ajustadas só no treino e teste fora da seleção.
2. Extração: executar exemplos reais autorizados e inspecionar transcrição/atributos; medir falhas, memória e latência. JSON válido não comprova percepção correta.
3. Modelo: comparar baselines, CatBoost M1/M2 e LightGBM completo no mesmo conjunto; números finitos, inversão de log correta, limites ordenados, cobertura/largura e análise de erros por setor/canal.
4. Integração: a função e um cliente MCP real por stdio retornam estrutura e números equivalentes para os mesmos IDs. Texto de chamadas LLM independentes pode variar; igualdade integral requer reutilizar o mesmo relatório cacheado. Testar validação, pasta permitida, versões, cache e falha de modalidade. Fixtures sintéticas cobrem segurança/contratos; não entram na avaliação científica.
5. Explicação: cada afirmação factual referencia evidência; números/ranking preservados; limitações explícitas. Tratar texto contido em vídeo e brief como dados, sem seguir instruções que tentem alterar o fluxo.
6. Performance: registrar tempos frios e com cache, pico de RAM, tamanho dos artefatos e latência do explicador para um, três e cinco candidatos. Confirmar rejeição acima do teto. Fixar timeout e orçamento por etapa com o piloto; não declarar um SLA sem medição.
7. Reprodução: README, versões, comandos de instalação/treino/demo, registro dos experimentos, relatório de métricas e limitações. Verificações públicas não precisam de chave nem arquivos privados.

## 9. Ordem de entrega e aprendizagem

As sete issues publicadas e suas dependências estão em [backlog-proposto.md](backlog-proposto.md). Começar pela [#1](https://github.com/leeunam/Galaxies-Inteli-Academy/issues/1): confirmar dados; depois uma comparação completa com baseline; em seguida melhorar modelo, extração e explicação mantendo a mesma interface. Um executor por árvore de trabalho. Paralelizar somente tarefas independentes após estabilizar contratos; processamento noturno só depois de passar numa amostra e receber orçamento/condições de parada.

| Dia | Marco verificável |
| --- | --- |
| Sex 16 | Revisar esta proposta e o backlog; abrir issues após aprovação; confirmar ou deixar explícita a pendência da fonte de mídia e métricas |
| Sáb 17, 08h–20h/21h | Resolver a viabilidade no primeiro bloco; fluxo baseline por função/MCP; M1 e início da extração multimodal. Terminar com algo executável |
| Dom 18, 5h | Concluir M2, auditar extração e comparar na validação; congelar contrato para explicação |
| Seg 19, 3h | Integrar LangGraph, SHAP, comparáveis e explicador NIM; demonstrar três arquivos e verificar o limite de cinco |
| Ter 20, 3h | Congelar funcionalidades, executar teste reservado uma vez, consolidar métricas/limitações e reprodução |
| Qua 21, 3h | Corrigir bloqueadores, conferir pacote e entregar antes de 23h59 |

Em cada bloco de três horas, reservar aproximadamente 30 minutos para explicar alvo, transformações, previsões e falhas. O aluno implementa/inspeciona primeiro um exemplo pequeno de preparação dos dados, baseline e avaliação; a IA amplia repetições e faz revisão. Commits por unidades coerentes, incluindo código, testes e documentação da mesma mudança. O aprendizado não pode ficar inteiramente delegado à execução noturna.

## Referências técnicas verificadas

- [YouTube: recurso de vídeo e estatísticas](https://developers.google.com/youtube/data/reference/rest/v3/videos).
- [YouTube: políticas de dados, conteúdo e métricas derivadas](https://developers.google.com/youtube/terms/developer-policies), especialmente III.E e III.L.
- [SMTPD: artigo](https://arxiv.org/html/2503.04446v1) e [repositório dos autores](https://github.com/zhuwei321/SMTPD).
- [Scikit-learn: validação por grupos e tempo](https://scikit-learn.org/stable/modules/cross_validation.html) e [pipelines](https://scikit-learn.org/stable/modules/compose.html).
- [CatBoost: perdas e quantis](https://catboost.ai/docs/en/concepts/loss-functions-regression) e [SHAP](https://catboost.ai/docs/en/concepts/shap-values).
- [uv: projetos](https://docs.astral.sh/uv/guides/projects/).
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) e [pesos small](https://huggingface.co/Systran/faster-whisper-small).
- [MiniLM multilíngue](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2), [CLIP](https://huggingface.co/openai/clip-vit-base-patch32), [SmolVLM2](https://huggingface.co/HuggingFaceTB/SmolVLM2-500M-Video-Instruct) e [seu processador](https://huggingface.co/HuggingFaceTB/SmolVLM2-500M-Video-Instruct/blob/main/preprocessor_config.json).
- [LangGraph: grafo](https://docs.langchain.com/oss/python/langgraph/graph-api) e [subgrafos](https://docs.langchain.com/oss/python/langgraph/use-subgraphs).
- [LightGBM: características](https://lightgbm.readthedocs.io/en/stable/Features.html), [objetivos e quantis](https://lightgbm.readthedocs.io/en/stable/Parameters.html) e [predições/contribuições](https://lightgbm.readthedocs.io/en/stable/pythonapi/lightgbm.LGBMRegressor.html).
- [Meta: Llama 3.3 70B Instruct](https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct), [endpoint público NIM](https://build.nvidia.com/meta/llama-3_3-70b-instruct?nim=hosted) e [termos API Trial NVIDIA](https://assets.ngc.nvidia.com/products/api-catalog/legal/NVIDIA%20API%20Trial%20Terms%20of%20Service.pdf).
- [FastMCP: instalação](https://gofastmcp.com/getting-started/installation), [release 4.1.0](https://github.com/PrefectHQ/fastmcp/releases/tag/v4.1.0), [Python suportado](https://github.com/PrefectHQ/fastmcp/blob/v4.1.0/pyproject.toml) e [teste de clientes](https://gofastmcp.com/servers/testing).

# Justificativas e alternativas técnicas

Data: 17/10/2026. Estado: **API externa NIM, ID meta/llama-3.3-70b-instruct e limite de cinco candidatos confirmados; comparação enxuta de algoritmos proposta para revisão**. Não houve instalação, inferência externa ou mudança de contrato implementada. O primeiro teste externo será sintético; escolher o provedor não libera transferência irrestrita de dados reais.

## 1. Provedor do explicador

O papel arquitetural é receber evidências estruturadas e produzir uma explicação validada. O aluno escolheu NVIDIA NIM hospedada em API externa. O contrato do explicador deve permitir futura troca de provedor sem alterar o preditor, mas só o adaptador NIM faz parte do plano atual.

A escolha anterior local foi conservadora diante do requisito de confidencialidade e foi substituída pela preferência expressa do aluno. A extração de mídia e o preditor permanecem locais; o explicador usa apenas o pacote de evidências permitido.

### Groq

É candidato viável para uma demonstração com entradas permitidas. A documentação oferece Zero Data Retention a todos os clientes; há exceções de retenção por confiabilidade/abuso quando esse controle não está ativado. O acordo proíbe treinamento com inputs/outputs sem permissão explícita. Isso não dispensa autorização para transmitir dados nem significa que o provedor não os processe.

Uma configuração candidata é `openai/gpt-oss-20b`, com JSON Schema estrito, seguida de validação semântica local. Esse modelo aparece na documentação atual de Structured Outputs e na tabela gratuita de limites. Verificar disponibilidade e limites da conta antes de fixar a versão; formato válido não garante explicação factual.

### NVIDIA NIM

Distinguir o endpoint hospedado gratuito para prototipação do contêiner NIM operado em infraestrutura própria. O primeiro não exige GPU local. A alternativa autogerida exige infraestrutura compatível e não é equivalente a uma API gratuita que já esteja pronta.

Os termos publicados do API Trial restringem conteúdo confidencial (2.6(a)) e incluem uso de conteúdo para melhoria de produtos/modelos (3.3). Não usar essa oferta para evidências confidenciais de uma campanha. Avaliações com material sintético ou não confidencial são uma situação diferente. Confirmar as condições efetivamente aplicáveis ao endpoint escolhido; não extrapolar para todos os contratos comerciais ou NIM autogerido.

### Recomendação para o projeto

Manter predição, mídia e extração locais. Testar o explicador na API NIM com `meta/llama-3.3-70b-instruct`, ID confirmado pelo aluno. A model card inclui português e diálogo multilíngue. Qwen2.5-Coder-32B-Instruct é especializado em código; Nemotron 3 Nano Omni 30B A3B Reasoning é multimodal e declara suporte linguístico somente a inglês. Isso favorece Llama como primeiro candidato para explicação textual em português; não demonstra superioridade numa avaliação da aplicação nem pelo número de parâmetros. Não habilitar troca automática de provedor em caso de falha.

Não foi localizada chave NVIDIA nos nomes previstos do `.env`. `.env.example` declara `NVIDIA_API_KEY` e `NVIDIA_MODEL` vazios, sem implementar um carregador. Assim que o acesso estiver configurado, o teste inicial deve usar pacotes sintéticos com números, drivers e IDs de evidência conhecidos. Conferir JSON, preservação de números/ranking, português, referências, latência e erros antes de usar material real permitido.

Enviar apenas o pacote mínimo necessário: IDs opacos, previsões, limites, contribuições agrupadas, atributos autorizados e objetivo/brief reduzido. Excluir vídeo, áudio, transcrição integral, nomes, caminhos e segredos. Atributos e briefs reduzidos ainda podem revelar estratégia; minimização não é anonimização garantida.

O critério de escolha deve medir qualidade factual, referências às evidências, preservação de números, português, latência, falhas e condições de tratamento dos dados. A rapidez do explicador não muda a qualidade preditiva do CatBoost.

## 2. Quantidade de candidatos

Não existe necessidade matemática de exatamente três. O número veio do caso de demonstração narrado pelo aluno e foi transformado numa restrição excessiva do rascunho.

O modelo proposto é pontual: para cada vídeo, `f(features_do_video)` estima seus quantis. O ranking ordena as previsões centrais dos N candidatos. Não é uma rede que recebe uma trinca de vídeos nem exige treino com grupos fixos de três. Mantidos modelo e features, acrescentar outro candidato não altera a previsão numérica dos anteriores.

- Um vídeo: análise individual com previsão, faixa e explicação; sem comparação competitiva.
- Dois ou mais: as mesmas análises individuais, acrescidas da ordenação e síntese comparativa.
- N vídeos: possível no desenho, sujeito a tempo, memória, tamanho da resposta, janela de contexto e cotas. Extração e predição crescem aproximadamente com N, e a ordenação custa O(N log N).

Contrato confirmado pelo aluno: núcleo capaz de processar N; interface inicial aceita de um a cinco candidatos distintos. Um candidato gera modo individual; dois a cinco geram comparação. O teto de cinco é operacional e configurável, não uma exigência estatística. Medir o custo no piloto e manter três no roteiro principal da demonstração.

A quantidade de vídeos admitida numa requisição é independente do suporte necessário para avaliar uma métrica. Em particular, Spearman com dois pares sem empate é definido, mas só assume +1 ou -1; uma regra de reportar a métrica a partir de três referências por canal procura evitar esse caso pouco informativo e ainda não garante estabilidade estatística.

## 3. Modelos de machine learning

O problema é de regressão supervisionada: prever um valor numérico, inicialmente `log1p(views)`. Regressão linear é um algoritmo para essa tarefa; Random Forest e gradient boosting também podem fazer regressão. Redes pré-treinadas de texto/imagem extraem atributos, mas não serão treinadas de ponta a ponta para prever views.

M1 e M2 identificam conjuntos de atributos: arquivo/transcrição e seu acréscimo visual/VLM/acústico. Ambos podem usar CatBoost. Comparar M1/M2 responde se as novas informações ajudam; comparar Ridge/Random Forest/CatBoost responde se outra família de algoritmo aproveita melhor as informações. Não mudar algoritmo e atributos ao mesmo tempo ao atribuir a causa de um ganho.

| Abordagem | Vantagens neste projeto | Limites e motivo para priorizar ou adiar |
| --- | --- | --- |
| Mediana por setor/canal com suporte | Barata, auditável e estabelece referência de erro | Não diferencia conteúdos com a mesma referência; obrigatória como baseline |
| Linear/Ridge | Rápida; útil com muitos atributos correlacionados; Ridge restringe coeficientes grandes | Relação aditiva nas features escolhidas; interações precisam ser construídas. Explicada para aprendizagem; retirada do plano de execução obrigatório |
| kNN | Intuitivo; aproveita semelhança quando a distância é adequada | Sensível à escala, dimensão e qualidade da vizinhança. Conteúdo parecido pode ter audiência muito diferente. Menor prioridade como preditor |
| Árvore única | Regras fáceis de inspecionar quando rasa; relações não lineares | Uma árvore profunda pode se ajustar ao ruído; pequenas mudanças nos dados podem mudar regras. Boa ferramenta didática |
| Random Forest | Média de árvores com diversidade reduz variância; captura interações; bom concorrente | Conjunto menos simples de explicar; intervalos não surgem corretamente pelo simples desvio entre árvores. Fora da execução obrigatória |
| CatBoost | Boosting não linear; categorias, perdas quantílicas e SHAP disponíveis na mesma biblioteca | Precisa de regularização/validação; embeddings e dados escassos podem favorecer um linear; não há superioridade comprovada nesta base. Candidato principal |
| LightGBM/XGBoost | Alternativas consolidadas de gradient boosting, com recursos de regularização e objetivos variados | LightGBM será o único concorrente proposto do CatBoost; XGBoost fica como alternativa futura. Não testar as três bibliotecas neste prazo |
| SVR com kernel | Relações não lineares em conjuntos menores | Escala e parâmetros exigem cuidado; custo de treino pode crescer muito; explicação e intervalos demandam trabalho adicional. Adiar |
| Rede neural treinada para views | Pode aprender representações e interações complexas | Maior espaço de escolhas e risco com poucos dados, custo e tempo. Usar encoders congelados inicialmente |

Random Forest constrói árvores diversas e combina suas previsões. Gradient boosting constrói árvores em sequência, acrescentando correções que reduzem a perda escolhida. Com erro quadrático, essas correções podem ser entendidas como ajuste dos resíduos; com quantis, o objetivo é a perda quantílica, não simplesmente o mesmo resíduo.

Plano enxuto proposto após o pedido do aluno: mediana como baseline obrigatório e apenas três experimentos treinados: (1) CatBoost com metadados/texto da fala, (2) CatBoost com os atributos anteriores acrescidos de visão/VLM/acústica e (3) LightGBM com os mesmos atributos completos de (2). Não há um terceiro conjunto de informações M3 nem uma matriz de todos os algoritmos contra todas as modalidades. Ridge, Random Forest e XGBoost saem da execução obrigatória. A comparação (1)→(2) mede o acréscimo de atributos com o mesmo algoritmo; (2)→(3) compara algoritmos com as mesmas informações. A transcrição é compartilhada e esse limite da ablação continua explícito. A exigência de medir ganho multimodal consta do TAPI e não deve desaparecer silenciosamente.

Os atributos são extraídos uma vez e reutilizados por seleção de colunas. Quantis e validação exigem múltiplos ajustes automatizados, mesmo com apenas três experimentos; não prometer que serão três chamadas de treino. Escolher hiperparâmetros e biblioteca usando treino/validação, com o mesmo protocolo de canais, e preservar o teste final.

Em cada experimento CatBoost ou LightGBM, ajustar q10, q50 e q90, preservando q50 como previsão central e explicando esse mesmo modelo com contribuições SHAP. São três ajustes da biblioteca selecionada para central e limites, não três modelos especialistas de nicho. Repetir CatBoost em M1/M2 mede o efeito das features. Quantis de previsão não garantem cobertura; verificar na avaliação.

### Como essas famílias são treinadas e onde se aplicam

Ridge usa a mesma soma ponderada da regressão linear, `y_estimado = intercepto + soma(peso × atributo)`. O treinamento escolhe pesos que reduzam o erro quadrático mais uma penalização proporcional à soma dos quadrados dos pesos. Esse controle L2 pode reduzir instabilidade quando muitas colunas se parecem; não cria automaticamente interações não lineares. Serve em tabelas com tendências aproximadamente aditivas, variáveis correlacionadas e referências rápidas sobre embeddings. Sua retirada é uma decisão de escopo, não evidência de inadequação universal.

CatBoost, LightGBM e XGBoost são bibliotecas/sistemas que implementam gradient boosting de árvores. Não são pesos prontos como Llama: o projeto treinará `CatBoostRegressor` ou `LGBMRegressor` com sua própria tabela e seus rótulos. Cada etapa ajusta uma árvore e acrescenta sua contribuição ao conjunto para reduzir a perda escolhida. A taxa de aprendizado limita o tamanho das correções; quantidade/profundidade de árvores e regularização controlam capacidade e sobreajuste.

- CatBoost fornece tratamento de categorias por estatísticas ordenadas e, na configuração usual, árvores simétricas, com a mesma condição de divisão em cada nível. É conveniente para tabelas com categorias, como setor e atributos enumerados; ordered boosting e tratamento interno de categorias não substituem a separação temporal/por canal do projeto.
- LightGBM usa histogramas de valores e, em seu crescimento usual, escolhe a folha com maior redução da perda. Pode trabalhar de modo eficiente em tabelas extensas, numéricas ou mistas; com poucos dados, limitar folhas/profundidade e exigir suporte mínimo por folha é especialmente importante. Não é automaticamente melhor ou mais rápido em qualquer base.
- XGBoost também soma árvores usando um objetivo regularizado e métodos eficientes de construção. É uma alternativa geral para regressão, classificação e ranking tabulares. Sua utilidade se sobrepõe às outras duas; adicioná-lo agora amplia a busca sem responder uma pergunta nova indispensável.

No projeto, um extrator transforma o vídeo em colunas; o treinamento relaciona essas colunas ao resultado observado, minimizando uma perda. O artefato treinado guarda árvores e valores aprendidos. Na inferência, o novo arquivo passa pelo mesmo extrator, cada árvore é percorrida e suas contribuições são combinadas para produzir a previsão. Nenhuma dessas bibliotecas entende o vídeo bruto ou deduz um novo objetivo de campanha sozinha.

Uma abordagem de learning-to-rank é uma alternativa futura quando houver grupos de decisão adequados e o objetivo for diretamente a ordenação. Ainda precisaríamos de uma solução adicional para contagem e intervalo, além de grupos de treino justificáveis. Para o contrato atual e o prazo, regressão com ordenação é mais simples de verificar.

A recomendação CatBoost é uma hipótese de engenharia, não um resultado experimental. Se LightGBM ou baseline forem superiores sob avaliação válida, isso deve aparecer no relatório. Nenhum algoritmo corrige sozinho dados indisponíveis, um alvo mal identificado ou vazamento entre partições.

## Fontes primárias consultadas em 17/10

- [Groq: tratamento de dados e controles de retenção](https://console.groq.com/docs/your-data), [acordo de serviço](https://console.groq.com/docs/legal/services-agreement), [saídas estruturadas](https://console.groq.com/docs/structured-outputs) e [limites por modelo/plano](https://console.groq.com/docs/rate-limits).
- [NVIDIA: acesso NIM para desenvolvimento](https://docs.api.nvidia.com/nim/docs/product) e [API Trial Terms, seções 2 e 3](https://assets.ngc.nvidia.com/products/api-catalog/legal/NVIDIA%20API%20Trial%20Terms%20of%20Service.pdf).
- [Meta: Llama 3.3 70B Instruct](https://huggingface.co/meta-llama/Llama-3.3-70B-Instruct), [Qwen2.5-Coder-32B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct) e [NVIDIA: Nemotron 3 Nano Omni 30B A3B Reasoning](https://build.nvidia.com/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning/modelcard).
- [Scikit-learn: modelos lineares/Ridge](https://scikit-learn.org/stable/modules/linear_model.html), [vizinhos](https://scikit-learn.org/stable/modules/neighbors.html), [árvores](https://scikit-learn.org/stable/modules/tree.html), [ensembles](https://scikit-learn.org/stable/modules/ensemble.html) e [SVR](https://scikit-learn.org/stable/modules/svm.html#regression).
- [CatBoost: objetivos de regressão e quantis](https://catboost.ai/docs/en/concepts/loss-functions-regression) e [SHAP](https://catboost.ai/docs/en/concepts/shap-values).
- [CatBoost: artigo original](https://arxiv.org/abs/1706.09516), [LightGBM: características](https://lightgbm.readthedocs.io/en/stable/Features.html) e [XGBoost: introdução às árvores boosted](https://xgboost.readthedocs.io/en/stable/tutorials/model.html).
- [SciPy: definição de Spearman](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html).

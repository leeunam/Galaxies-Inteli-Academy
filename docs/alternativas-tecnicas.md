# Justificativas e alternativas técnicas

Data: 17/10/2026. Estado: **recomendações para revisão**, complementares à proposta técnica. Não houve instalação, inferência externa, mudança de contrato implementada ou aprovação de transferência de dados.

## 1. Provedor do explicador

O papel arquitetural é receber evidências estruturadas e produzir uma explicação validada. Ollama, Groq e NVIDIA hospedada são escolhas de execução desse papel, não partes indispensáveis do algoritmo de previsão. O contrato do explicador deve permitir trocar o provedor sem alterar o preditor. Não implementar todos os adaptadores no prazo inicial.

A escolha inicial local foi conservadora diante do requisito de confidencialidade. Há custo de CPU, RAM, instalação e possível perda de qualidade frente a modelos maiores hospedados. Não foi medido desempenho que justifique declarar a execução local superior.

### Groq

É candidato viável para uma demonstração com entradas permitidas. A documentação oferece Zero Data Retention a todos os clientes; há exceções de retenção por confiabilidade/abuso quando esse controle não está ativado. O acordo proíbe treinamento com inputs/outputs sem permissão explícita. Isso não dispensa autorização para transmitir dados nem significa que o provedor não os processe.

Uma configuração candidata é `openai/gpt-oss-20b`, com JSON Schema estrito, seguida de validação semântica local. Esse modelo aparece na documentação atual de Structured Outputs e na tabela gratuita de limites. Verificar disponibilidade e limites da conta antes de fixar a versão; formato válido não garante explicação factual.

### NVIDIA NIM

Distinguir o endpoint hospedado gratuito para prototipação do contêiner NIM operado em infraestrutura própria. O primeiro não exige GPU local. A alternativa autogerida exige infraestrutura compatível e não é equivalente a uma API gratuita que já esteja pronta.

Os termos publicados do API Trial restringem conteúdo confidencial (2.6(a)) e incluem uso de conteúdo para melhoria de produtos/modelos (3.3). Não usar essa oferta para evidências confidenciais de uma campanha. Avaliações com material sintético ou não confidencial são uma situação diferente. Confirmar as condições efetivamente aplicáveis ao endpoint escolhido; não extrapolar para todos os contratos comerciais ou NIM autogerido.

### Recomendação para o projeto

Manter predição, mídia e extração locais. O explicador pode usar Groq para material permitido, após verificar conta, controles de dados e qualidade em português. Quando o material deva permanecer na máquina, usar o percurso local. Não habilitar troca automática de um provedor local para um externo em caso de falha.

Enviar apenas o pacote mínimo necessário: IDs opacos, previsões, limites, contribuições agrupadas, atributos autorizados e objetivo/brief reduzido. Excluir vídeo, áudio, transcrição integral, nomes, caminhos e segredos. Atributos e briefs reduzidos ainda podem revelar estratégia; minimização não é anonimização garantida.

O critério de escolha deve medir qualidade factual, referências às evidências, preservação de números, português, latência, falhas e condições de tratamento dos dados. A rapidez do explicador não muda a qualidade preditiva do CatBoost.

## 2. Quantidade de candidatos

Não existe necessidade matemática de exatamente três. O número veio do caso de demonstração narrado pelo aluno e foi transformado numa restrição excessiva do rascunho.

O modelo proposto é pontual: para cada vídeo, `f(features_do_video)` estima seus quantis. O ranking ordena as previsões centrais dos N candidatos. Não é uma rede que recebe uma trinca de vídeos nem exige treino com grupos fixos de três. Mantidos modelo e features, acrescentar outro candidato não altera a previsão numérica dos anteriores.

- Um vídeo: análise individual com previsão, faixa e explicação; sem comparação competitiva.
- Dois ou mais: as mesmas análises individuais, acrescidas da ordenação e síntese comparativa.
- N vídeos: possível no desenho, sujeito a tempo, memória, tamanho da resposta, janela de contexto e cotas. Extração e predição crescem aproximadamente com N, e a ordenação custa O(N log N).

Recomendação de contrato para revisão: núcleo capaz de processar N; interface inicial aceita de um a cinco candidatos distintos. Um candidato gera modo individual; dois a cinco geram comparação. O teto de cinco é uma hipótese operacional configurável a validar no piloto, não uma exigência estatística. Manter três no roteiro principal da demonstração.

A quantidade de vídeos admitida numa requisição é independente do suporte necessário para avaliar uma métrica. Em particular, Spearman com dois pares sem empate é definido, mas só assume +1 ou -1; uma regra de reportar a métrica a partir de três referências por canal procura evitar esse caso pouco informativo e ainda não garante estabilidade estatística.

## 3. Modelos de machine learning

O problema é de regressão supervisionada: prever um valor numérico, inicialmente `log1p(views)`. Regressão linear é um algoritmo para essa tarefa; Random Forest e gradient boosting também podem fazer regressão. Redes pré-treinadas de texto/imagem extraem atributos, mas não serão treinadas de ponta a ponta para prever views.

M1 e M2 identificam conjuntos de atributos: arquivo/transcrição e seu acréscimo visual/VLM/acústico. Ambos podem usar CatBoost. Comparar M1/M2 responde se as novas informações ajudam; comparar Ridge/Random Forest/CatBoost responde se outra família de algoritmo aproveita melhor as informações. Não mudar algoritmo e atributos ao mesmo tempo ao atribuir a causa de um ganho.

| Abordagem | Vantagens neste projeto | Limites e motivo para priorizar ou adiar |
| --- | --- | --- |
| Mediana por setor/canal com suporte | Barata, auditável e estabelece referência de erro | Não diferencia conteúdos com a mesma referência; obrigatória como baseline |
| Linear/Ridge | Rápida; útil com muitos atributos correlacionados; Ridge restringe coeficientes grandes | Relação aditiva nas features escolhidas; interações precisam ser construídas. Comparador leve recomendado, sem substituir a validação |
| kNN | Intuitivo; aproveita semelhança quando a distância é adequada | Sensível à escala, dimensão e qualidade da vizinhança. Conteúdo parecido pode ter audiência muito diferente. Menor prioridade como preditor |
| Árvore única | Regras fáceis de inspecionar quando rasa; relações não lineares | Uma árvore profunda pode se ajustar ao ruído; pequenas mudanças nos dados podem mudar regras. Boa ferramenta didática |
| Random Forest | Média de árvores com diversidade reduz variância; captura interações; bom concorrente | Conjunto menos simples de explicar; intervalos não surgem corretamente pelo simples desvio entre árvores. Opcional no prazo |
| CatBoost | Boosting não linear; categorias, perdas quantílicas e SHAP disponíveis na mesma biblioteca | Precisa de regularização/validação; embeddings e dados escassos podem favorecer um linear; não há superioridade comprovada nesta base. Candidato principal |
| LightGBM/XGBoost | Alternativas consolidadas de gradient boosting, com recursos de regularização e objetivos variados | Exigem escolher e validar outra configuração/biblioteca. Não há ganho conhecido que justifique testar as três bibliotecas neste prazo |
| SVR com kernel | Relações não lineares em conjuntos menores | Escala e parâmetros exigem cuidado; custo de treino pode crescer muito; explicação e intervalos demandam trabalho adicional. Adiar |
| Rede neural treinada para views | Pode aprender representações e interações complexas | Maior espaço de escolhas e risco com poucos dados, custo e tempo. Usar encoders congelados inicialmente |

Random Forest constrói árvores diversas e combina suas previsões. Gradient boosting constrói árvores em sequência, acrescentando correções que reduzem a perda escolhida. Com erro quadrático, essas correções podem ser entendidas como ajuste dos resíduos; com quantis, o objetivo é a perda quantílica, não simplesmente o mesmo resíduo.

Escolha recomendada: mediana como baseline obrigatório, Ridge como comparador de baixo custo e CatBoostRegressor como principal candidato. Random Forest é uma comparação opcional se houver tempo e valor didático; não transformar a entrega num torneio de todos os modelos da tabela. Escolher hiperparâmetros e família usando treino/validação, com o mesmo protocolo de canais, e preservar o teste final.

Para CatBoost, ajustar q10, q50 e q90, preservando q50 como previsão central e explicando esse mesmo modelo com SHAP. São três ajustes de uma família para central e limites, não três modelos especialistas de nicho. Repetir essa configuração em M1/M2 mede o efeito das features. Quantis de previsão não garantem cobertura; verificar na avaliação.

Uma abordagem de learning-to-rank é uma alternativa futura quando houver grupos de decisão adequados e o objetivo for diretamente a ordenação. Ainda precisaríamos de uma solução adicional para contagem e intervalo, além de grupos de treino justificáveis. Para o contrato atual e o prazo, regressão com ordenação é mais simples de verificar.

A recomendação CatBoost é uma hipótese de engenharia, não um resultado experimental. Se Ridge ou baseline forem superiores sob avaliação válida, isso deve aparecer no relatório. Nenhum algoritmo corrige sozinho dados indisponíveis, um alvo mal identificado ou vazamento entre partições.

## Fontes primárias consultadas em 17/10

- [Groq: tratamento de dados e controles de retenção](https://console.groq.com/docs/your-data), [acordo de serviço](https://console.groq.com/docs/legal/services-agreement), [saídas estruturadas](https://console.groq.com/docs/structured-outputs) e [limites por modelo/plano](https://console.groq.com/docs/rate-limits).
- [NVIDIA: acesso NIM para desenvolvimento](https://docs.api.nvidia.com/nim/docs/product) e [API Trial Terms, seções 2 e 3](https://assets.ngc.nvidia.com/products/api-catalog/legal/NVIDIA%20API%20Trial%20Terms%20of%20Service.pdf).
- [Scikit-learn: modelos lineares/Ridge](https://scikit-learn.org/stable/modules/linear_model.html), [vizinhos](https://scikit-learn.org/stable/modules/neighbors.html), [árvores](https://scikit-learn.org/stable/modules/tree.html), [ensembles](https://scikit-learn.org/stable/modules/ensemble.html) e [SVR](https://scikit-learn.org/stable/modules/svm.html#regression).
- [CatBoost: objetivos de regressão e quantis](https://catboost.ai/docs/en/concepts/loss-functions-regression) e [SHAP](https://catboost.ai/docs/en/concepts/shap-values).
- [SciPy: definição de Spearman](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.spearmanr.html).

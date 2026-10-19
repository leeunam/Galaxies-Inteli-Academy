# Diagnóstico da subestimação de M1

Investigação após a [demonstração Python/MCP](issue-3-servico-m1.md): **1.520,52
views previstas para 2.316.115 observadas**, com faixa estimada 49,40–16.189,49.
O diagnóstico aponta dificuldade para aprender e generalizar os casos de maior
alcance, com pouquíssimos exemplos extremos. Não foi encontrado erro de conversão
ou transporte nas verificações realizadas. Isso explica um padrão do modelo;
não identifica a causa individual exata da previsão da demonstração.

## Distribuição e erros

O bundle `9dd1c7a2…d70d59` permaneceu congelado. Foram examinadas somente
124 referências de treino e 45 de validação, preservando a separação por canal.

| Views observadas | Treino | Validação |
| --- | ---: | ---: |
| Referências / canais | 124 / 48 | 45 / 16 |
| Mediana | 642,5 | 589 |
| Percentil 90 | 15.019,2 | 9.246,4 |
| Máximo | 1.156.208 | 286.915 |
| Pelo menos 100 mil | 4 | 1 |
| Pelo menos 1 milhão | 1 | 0 |

Os quatro exemplos de treino com pelo menos 100 mil views são de beleza e
pertencem a três canais. Moda tem 56 referências e máximo de 66.683; beleza
tem 68 e mediana de 1.013,5. O suporte para aprender padrões de milhões de views
é extremamente pequeno. A média do treino, 20.228,9, é puxada pelos extremos.

Na validação, todas as previsões centrais ficaram entre **125,31 e 2.541,94**,
embora os resultados observados variem de zero a 286.915. Há compressão das
previsões: o modelo não separa adequadamente os casos de maior alcance.

| Partição / setor | Observado | M1 q50 | Limite superior servido |
| --- | ---: | ---: | ---: |
| Treino / beleza | 1.156.208 | 6.145,33 | 54.250,01 |
| Treino / beleza | 394.904 | 46.424,20 | 82.897,88 |
| Validação / beleza | 286.915 | 1.220,00 | 7.559,86 |
| Validação / beleza | 34.140 | 2.541,94 | 20.737,14 |
| Validação / moda | 21.269 | 1.162,44 | 25.023,46 |
| Validação / moda | 7.459 | 326,44 | 8.526,57 |

A dificuldade não se resume a canais novos: o maior exemplo de treino também
é fortemente subestimado. O MAE log médio por canal sobe de **0,6026 no treino
para 1,8569 na validação**. A diferença é compatível com dificuldade de
generalização e possível sobreajuste, sem demonstrar uma causa única.

Foi definido um recorte retrospectivo de alto alcance: views observadas maiores
ou iguais ao p90 **do treino por setor** (6.403,5 em moda; 33.835,3 em beleza).
Não é classe de viralidade nem informação disponível antes da publicação.
Esse quantil em views brutas difere ligeiramente do interpolado em log e
reconvertido usado por B0.

| Resultado nesse recorte | Treino | Validação |
| --- | ---: | ---: |
| Referências / canais | 13 / 10 | 4 / 3 |
| Previsão central abaixo do observado | 12 de 13 | 4 de 4 |
| Observado acima do limite superior | 7 de 13 | 2 de 4 |
| MAE log médio por canal de M1 | 2,0478 | 3,6909 |
| Mesma métrica de B0 | 4,2928 | 4,1587 |

Os dois casos de beleza da validação ficaram acima da faixa; os dois de moda,
do mesmo canal, ficaram dentro. O fator mediano `(observado+1)/(previsto+1)` nos
quatro foi 20,53. Fora do recorte, só 20 das 41 previsões ficaram abaixo do
observado e o fator mediano foi 0,992. Há também superestimação de vídeos pequenos
e dos zeros: multiplicar todas as saídas para corrigir o viral não tem respaldo.

M1 melhora o MAE log agregado de validação em cerca de 6,1% sobre B0
(1,8569 contra 1,9768) e erra menos nesse recorte, mas continua errando muito.
Melhorar uma média não comprova capacidade de identificar virais. São apenas
quatro referências em três canais; a validação já participou da seleção/parada
do modelo. Este é diagnóstico **após seleção**, sem avaliação independente final.

## Auditoria do cálculo e das entradas

q50 foi treinado em `log1p(views)` e reconvertido com `expm1`: procura uma mediana
condicional, não a média ou probabilidade de viralização. A transformação é
monótona e não obriga a mediana a ser pequena. Quantile penaliza os desvios
segundo o quantil, sem dar a um erro extremo em views brutas o peso de uma perda
quadrática nessa escala. [Perdas do CatBoost](https://catboost.ai/docs/en/concepts/loss-functions-regression).

Foram reconstruídas as saídas nativas dos três modelos nas 169 entradas,
somando folhas visitadas e aplicando escala e viés: **diferença máxima zero**.
Escala 1; 2/169/30 árvores para q10/q50/q90. A paridade real Python/MCP já havia
sido verificada na demo. Não foi encontrado fator de mil perdido nem exponenciação
ausente nesses percursos. [Fórmula de escala e viés](https://catboost.ai/docs/en/concepts/python-reference_catboostregressor_get_scale_and_bias).

Os embeddings de treino têm 384 componentes finitos, sem componente constante
ou vetor nulo. Em `PredictionValuesChange` de q50, o grupo de embeddings soma
99,43% e duração 0,57%; setor, proporção e estado do texto somam zero. É uma
importância descritiva agregada de 384 dimensões correlacionadas, **não** 99,43%
da causa, da variância explicada ou da contribuição da fala no vídeo da demo.
Não foi calculado SHAP. [Definição da importância](https://catboost.ai/docs/en/concepts/fstr).

Os cinco vizinhos de fala mais próximos no treino, do mesmo setor, foram
escolhidos por cosseno, sem usar seus resultados na seleção. Para o exemplo
de validação com 286.915 views, seus resultados são mistos: 4.091, 102.378,
42.148, 1.298 e 5.619. Proximidade semântica não fornece uma relação simples
com alcance; isso não prova falha do embedding nem caso fora da distribuição.

A soma conservadora dos extremos das folhas por árvore dá teto frouxo de
95,2 milhões para q50: não há evidência de teto arquitetural de 1,5 mil. Para
q90 bruto, o teto é 438,6 mil; o limite superior servido usa o reparo
`max(q10, q50, q90)` e não herda necessariamente esse teto. Essas somas podem
combinar folhas inalcançáveis juntas; não são extremos exatos nem intervalos.

## Interpretação e próximos passos

Há pouco suporte no alto alcance, o ajuste não aprende bem os extremos mesmo
no treino e as previsões em canais de validação ficam concentradas. A tem
124 exemplos para 384 dimensões de fala e poucos metadados. Distribuição,
histórico do canal e atributos visuais não entram nessa configuração; sua
ausência é hipótese de limitação, sem prova de que incluí-los resolverá o erro.

As entradas temporárias exatas da demo foram descartadas conforme a política
de mídia. Não foi possível atribuir suas 1.520,52 views a folhas ou trechos
específicos. Não houve novo download, treino, busca de parâmetros, recalibração,
mudança de alvo, B/C, SHAP ou chamada externa nesta investigação.

O próximo comparador aprovado continua sendo B, quando seus atributos estiverem
prontos, mantendo a comparação com A e B0. Convém acompanhar os erros de alto
alcance, sem escolher parâmetros pelo teste. Ampliar a base, reamostrar extremos,
mudar a perda ou criar classificador de viralidade exigiria decisão explícita
de protocolo; nada disso foi aplicado para encaixar o vídeo. B não tem ganho
garantido.

## Reprodução e isolamento

`scripts.diagnose_m1` seleciona os IDs de treino/validação **antes** de abrir
suas evidências. Lê metadados da coorte, partições, baseline/rótulos de treino,
configuração e índice de caminhos; verifica checksums de curadoria, observação
e entradas contra o bundle. Não lê os arquivos mistos `records.json` e
`predictor-inputs.json`, nem evidências/rótulos do teste. Abriu 338 evidências:
dois arquivos por cada uma das 169 referências permitidas. Não inferiu o teste.

```bash
rtk proxy env OPENBLAS_NUM_THREADS=1 .venv/bin/python -m scripts.diagnose_m1 \
  --cohort-dir data/private/issue-1-pool-treino-20261018-v6/released-cohort-v1 \
  --model-dir artifacts/issue-3-experimento-a-v1 \
  --output data/private/novo-diagnostico-m1/diagnostic.json \
  --plot data/private/novo-diagnostico-m1/observed-vs-predicted.png
```

Executar na raiz, com destinos novos. JSON e PNG nascem com modo privado 0600
e não sobrescrevem arquivos. O JSON inclui referências/canais/vizinhos e fica
ignorado pelo Git. O gráfico usa `log10(views+1)` nos dois eixos, sem IDs.

Evidências locais em `data/private/issue-3-diagnostico-subestimacao-v1/`:
`diagnostic-final.json`, `observed-vs-predicted-final.png` e `verification.json`.
Os testes públicos usam somente fixtures sintéticas: proíbem abertura dos
arquivos mistos e evidências do teste, conferem adulteração/observação, regra
derivada do treino, escala/viés e permissões de saída. A revisão independente
confirmou o isolamento e orientou explicitar os limites de interpretação e
criar arquivos com permissões privadas desde o início.

Verificação final: **21 testes direcionados passaram**, Ruff/formatação e diff
sem problemas. Os hashes de 16 arquivos continuam iguais ao checkpoint anterior:
seis do bundle, quatro fontes offline e seis arquivos permitidos de metadados/
baseline da coorte. Os arquivos mistos e as evidências do teste não foram abertos
nem para essa conferência de hashes. O relatório final reproduziu integralmente
o cálculo anterior desta investigação, com permissões privadas verificadas.

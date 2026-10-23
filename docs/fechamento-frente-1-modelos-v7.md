# Adaptação sintética B/C ao contrato V7

Esta unidade cria wrappers separados para CatBoost B e LightGBM C sobre o contrato V7 de 912 atributos. Ela aceita apenas `V7DevelopmentData` sintético, revalida e reabre fontes verificadas antes de treino ou recarga, e mantém `quality_accepted`, `release_emitted`, `final_test_evaluated` e `served_model_replaced` estritamente falsos. `quality_release_sha256` é `null`; não existe liberação visual V7 nesta entrega.

`train_experiment(data, directory, algorithm="B"|"C", backend=...)` executa a grade histórica de 12 combinações por algoritmo. B conserva CatBoost com validação ponderada por canal e sem pesos de treino; C usa LightGBM, pesos apenas na validação, validação customizada com alvos float64, e encoding inteiro de categorias aprendido somente no treino. Categoria ausente no vocabulário, inclusive `unknown` visto apenas na validação ou inferência, causa erro. O backend `RecordingBackend` existe apenas para testes de contrato; a recarga de artefato recording exige a injeção explícita desse backend. A recarga nativa é separada e valida descritores nativos, fontes, lock, pairing, protocolos e igualdade de previsões.

Artefatos usam diretório exclusivo `0700`, arquivos `0600`, nomes fixos (`q10.model`, `q50.model`, `q90.model`, `validation-report.json`, `artifact.json`) e manifesto publicado por último. O relatório conserva os 12 trials, os três modelos selecionados por quantil com desempate congelado, métricas de validation já previstas e baseline B0 baseado somente nos quantis por setor de treino, marcado como não calibrado. Comparação B/C reabre ambos os artefatos contra o `V7DevelopmentData` recebido antes de prever; os bundles em memória não estabelecem pareamento. Ela vincula as métricas às mesmas linhas V7 de validation e registra hashes do manifesto, identidades, splits, contrato de features, baseline B0 e artefatos B/C, além do digest da comparação. O resultado declara `partition=validation` e `final_test_evaluated=false`; não seleciona nem promove modelos.

`explain_full(bundle, inputs, data=data)` calcula a interface de contribuições q50 para 1–5 exemplos e verifica 913 colunas, cobertura exata dos 912 atributos e reconstrução da predição log1p com erro absoluto até `1e-7`. A evidência fica marcada não causal e não é gate de percepção. O conjunto de grupos inclui sete grupos legados e um por atributo V7.

## Verificação local

Suíte individual e integrada executada com o Python já instalado no projeto, sem instalação ou rede, um core (`taskset -c 0`) e timeout externo de 110 segundos:

```text
rtk proxy /usr/bin/time -v timeout 110s taskset -c 0 /home/inteli/Documents/projetos/Galaxies-Inteli-Academy/.venv/bin/python -B -m pytest -q tests/test_full_visual_models_v7.py tests/test_full_visual_evidence_v7.py
13 passed in 8.01s
wall 8.61s; peak RSS 220004 KiB; exit 0
```

Os testes cobrem as grades completas e os parâmetros registrados, round-trip de ambos os algoritmos com recorder, permissões/destino exclusivo, encoding de treino e recusa de categoria inédita, rejeição de recorder pelo loader nativo, hashes adulterados, comparação pareada B/C+B0 e SHAP q50 de B/C para 1, 3 e 5 entradas com cobertura de 912 colunas. Também exercitam a fronteira sem `loader_verified`, limite físico em tentativa não selecionada, rejeição de contribuições malformadas, tolerância SHAP estritamente absoluta, reabertura de fonte antes de predição, mutação do modelo em memória, empate, e corrupções de protocolo, relatório, runtime, fontes e descritor. Ruff check/format, `git diff --check` e `py_compile` passaram. Os pontos nativos CatBoost/LightGBM foram interceptados nos testes; nenhum Pool, ajuste, predição ou SHAP nativo, arquivo de peso nativo ou dado observado foi usado. Isso não valida execução nativa, desempenho ou qualidade perceptiva.

## Limitações e sequência

O backend nativo está implementado, mas os 24 fits sintéticos, recarga nativa e SHAP nativo não foram executados nem autorizados nesta unidade. A API do backend está registrada no relatório de execução privado. O próximo passo é o integrador aprovar um slot explícito com CPU, memória, tempo, diretório e parada para esses ensaios. Dados observados, A300, 269 extrações elegíveis, holdout e seleção científica continuam fechados. A validação desta unidade apenas executa as receitas e a regra matemática de desempate sobre fixtures sintéticas; não constitui seleção científica, promoção ou aceite do projeto.

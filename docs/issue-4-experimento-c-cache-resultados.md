# Comparação A300 / B-cache / C-cache — 23/10/2026

C-cache LightGBM foi treinado e comparado em dados reais cacheados, conforme a
orientação de prosseguir sem o VLM. A300 e B-cache foram recarregados e suas
previsões brutas nos 66 casos coincidiram exatamente com os relatórios anteriores.
B/C completos com atributos VLM continuam distintos desta comparação.

## Dados e execução

- Mesma coorte de 300 e partições 203/66/31. Somente treino e validação foram abertos.
- C-cache usa as mesmas 905 colunas e a mesma ordem de B-cache: prefixo A388, CLIP512 e cinco medidas/estados técnicos. VLM não foi solicitado ou preenchido.
- Categorias codificadas por vocabulário aprendido somente no treino, sem imputação, PCA ou scaler.
- Doze ajustes predefinidos: quantis 0,1/0,5/0,9 × folhas 7/15 × mínimo por folha 5/20; profundidade 6, L2 3, taxa 0,05, seed 42, máximo 500/parada 50, CPU1.
- Pesos uniformes no treino; seleção e parada por MAE log por canal em q50 e pinball log por canal nos extremos, com alvos float64 no callback. Desempate por menor número de folhas e depois menor mínimo por folha.
- Receita e algoritmo de seleção conferidos contra a preparação anterior antes de executar. Não houve nova grade após observar os resultados.
- O bloco de treino, gravação, recarga e comparação levou **6,794 s**, excluindo a carga/verificação inicial de dados. Não é benchmark de latência do produto.
- LightGBM 4.7.0 e NumPy 2.4.6, já instalados. Nenhuma aquisição, API, novo extrator ou abertura do teste reservado.

## Validação: menor MAE log por canal é melhor

| Grupo | Vídeos / canais | A300 | B-cache | C-cache |
| --- | ---: | ---: | ---: | ---: |
| Original | 45 / 16 | 1.9327 | 1.7082 | 1.6298 |
| Novo | 21 / 21 | 1.6568 | 1.6204 | 1.4793 |
| União | 66 / 37 | 1.7761 | 1.6584 | 1.5444 |

Na união, C-cache reduz a métrica principal em **6.88%** frente a B-cache e **13.05%** frente a A300. B-cache→C-cache compara as bibliotecas na representação sem VLM; A300→C-cache mistura representação e biblioteca.

| Métrica na união | A300 | B-cache | C-cache |
| --- | ---: | ---: | ---: |
| MAE views micro | 8249.9097 | 8007.8255 | 7873.5181 |
| Cobertura micro | 0.7121 | 0.7576 | 0.7576 |
| Cobertura por canal | 0.7342 | 0.7680 | 0.7905 |
| Acerto de pares por canal | 0.4533 | 0.6417 | 0.6683 |
| Spearman por canal | -0.0192 | 0.2070 | 0.3292 |
| Pinball log q10 por canal | 0.4631 | 0.4610 | 0.4659 |
| Pinball log q50 por canal | 0.8881 | 0.8292 | 0.7722 |
| Pinball log q90 por canal | 0.4083 | 0.4120 | 0.3420 |

A média das três perdas quantílicas passa de 0.567403 em B-cache para 0.526703 em C-cache. q10 piora ligeiramente, e a cobertura em beleza cai de 0,7000 para 0,6750; o ganho não é uniforme. Todos os cinco casos de alto alcance continuam subestimados; três permanecem acima da faixa superior de C-cache.

A validação foi usada para escolher hiperparâmetros. Estes resultados são exploratórios; não validam cobertura nominal nem desempenho independente. O modelo servido permanece M1/A200.

## Artefato e reprodução

Código congelado do treino: `cc9f2a18d7c73d5caf8d2ab2889b0b3c140eac6b`. O diretório local ignorado pelo Git `artifacts/issue-4-experimento-c-cache-300-v1/` contém três modelos LightGBM nativos, `artifact.json` e `validation-report.json`, com vocabulário, fontes/lock/versões, identidades de splits, 12 tentativas, escolhas e hashes. A recarga produziu previsões brutas exatamente iguais nas 66 linhas. Não atualizar hashes para contornar incompatibilidade futura.

Para reproduzir o treino no checkout compatível e preparado, usar destinos **novos**; o comando recusa sobrescrita:

```bash
rtk proxy env OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 .venv/bin/python -B -m scripts.train_experiment_c_cache \
  --parent data/private/issue-1-pool-treino-20261018-v6/released-cohort-v1 \
  --cohort-dir data/private/issue-3-expansao-300-v1/released-cohort-v1 \
  --model-dir artifacts/issue-4-experimento-c-cache-reproducao \
  --comparison data/private/issue-4-experimento-c-cache-reproducao.json
```

Logs completos de treino/testes, comparação detalhada e checagens ficaram no diretório privado de entrega do operador. A comparação de alto alcance reutiliza os limiares fixos anteriores, sem seleção pelo teste.

## Fidelidade das explicações e execução

Nas três primeiras entradas ordenadas de validação, SHAP nativo agrupado cobriu as 905 colunas exatamente uma vez. O erro máximo de reconstrução de log1p(q50) foi 1,78×10⁻¹⁵ em B-cache e 7,99×10⁻¹⁵ em C-cache. Previsões em lote e individuais foram exatamente iguais nos dois modelos. Isso verifica fundamentos numéricos locais; não demonstra causalidade, aderência ao briefing ou qualidade de uma explicação remota com mídia real.

A implementação original de C completo continua recusando B-cache. Não houve promoção ao serviço, teste final, mudança de base ou retomada do visual.

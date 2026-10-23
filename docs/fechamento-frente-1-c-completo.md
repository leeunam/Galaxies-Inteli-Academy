# iSee — ponte versionada para C completo

Unidade de 23/10/2026, base `3586bcab7aa3f7bf165f1ac17ced91bb85358043`.
A ponte foi implementada e verificada com dados inventados. **Não houve treino
real, liberação visual, alteração do modelo servido ou abertura do teste.**

## Contrato e execução

`scripts.experiment_c_full_data` exige `VLMDevelopmentData` e `QualityRelease`
válidos antes de validar os dados cacheados e seus alvos. Em dados observados,
exige 203 entradas de treino e 66 de validação, proveniência explicitamente
não sintética e somente colunas da revisão atual: pessoa, produto e texto.
O carregador B-VLM existente continua exigindo os 269 sidecars completos,
suas identidades e vínculo com a liberação. A ponte não converte sidecars
diagnósticos/batch em sidecars aprovados nem fabrica a liberação ausente.

`scripts.train_experiment_c_full.train_experiment(data, destino_novo)` usa a
grade original de 12 ajustes LightGBM, CPU1, vocabulário categórico somente de
treino e recarga nativa exata. Categorias sem suporte no treino são recusadas;
não se aprende um vocabulário com a validação. A matriz conserva o prefixo
B-cache de 905 colunas e acrescenta somente `vlm_<campo_liberado>`.

`load_bundle(destino, data=data)` verifica modelos, relatório, fontes, lock,
versões, parâmetros nativos, encoding e identidades dos dados.
`compare(data, b_completo, c_completo, original_validation_ids=...)` exige B/C
completos, mesmas features, ordem, rótulos, partições e liberação. Produz erros,
ranking, quantis, cobertura/largura e recortes por setor/canal, incluindo os
grupos original/novo/união e a cauda com limiares históricos.

`scripts.full_model_evidence.explain_full(bundle, inputs)` explica de um a
cinco inputs com SHAP CatBoost ou `pred_contrib` LightGBM do q50. Os grupos
cobrem cada coluna exatamente uma vez. Embeddings têm somas assinadas por
modalidade, em log1p(views); base + grupos deve reconstruir q50 com erro
absoluto máximo de 1e-7. Não há interpretação de componentes ou causalidade.
Esse contrato é um insumo para a Frente 2; não altera o serviço atual.

## Compatibilidade preservada

Os módulos históricos `experiment_c_data.py`, `train_experiment_c_offline.py`
e `train_experiment_c_cache.py`, bem como fontes A/B e o gate visual, não
foram editados. A separação versionada evita invalidar os hashes dos bundles
existentes ou ampliar silenciosamente a autorização da preparação sintética.
O novo bundle se identifica como `experiment-c-full-lightgbm-v1` e
`C_FULL_VLM`, com `data_kind` explícito, sem avaliação do teste e sem promoção.
Há repetição deliberada do procedimento congelado de C para manter a fronteira
de compatibilidade; os testes verificam a mesma grade, callback e desempates.

## Verificação e limites

Passaram **35 testes em 28,44 s**, cobrindo os caminhos C completo, C sintético
anterior e C-cache. Incluem 12 ajustes nativos de C em fixture inventada,
recarga exata, corrupção de arquivos/parâmetros, bloqueio de cache-only e
proveniência observada inválida, pareamento e SHAP nativo B/C em fixture.
Ruff e formatação passaram. Ambiente existente acessado por caminho explícito,
sem instalação, cópia de ambiente, dados ou pesos para o clone.

Log privado persistente:
`data/private/fechamento-20261023/frente-1/unit-1-c-full/pytest.log`.
As fixtures nativas e demais saídas dessa verificação estão no `test-temp`
vizinho, identificadas como sintéticas nos artefatos. Não são modelos reais
de fechamento ou evidências de qualidade perceptiva/preditiva.

Permanecem necessários: candidata visual aprovada, seleção/anotação/revisão
independentes, emissão verificável de QualityRelease, ponte dos sidecars da
candidata para o contrato B, extração uniforme, slot de recursos e execução
real B/C. Nenhum desses aceites é inferido dos testes sintéticos.

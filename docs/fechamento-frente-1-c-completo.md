# iSee — ponte versionada para C completo

Unidade de 23/10/2026, base `3586bcab7aa3f7bf165f1ac17ced91bb85358043`.
A ponte foi implementada e verificada com dados inventados. **Não houve treino
real, liberação visual, alteração do modelo servido ou abertura do teste.**

## Contrato e execução

`scripts.experiment_c_full_data` exige dados e `QualityRelease` válidos antes
de validar os dados cacheados e seus alvos. Em dados observados, somente
`load_full_data(...)` fornece o wrapper `VerifiedFullData`: os caminhos são
reabertos pelo loader B-VLM, sob a guarda do teste, e o conteúdo deve continuar
igual em cada fronteira. Um `VLMDevelopmentData` observado construído à mão é
recusado. Exigem-se 203 entradas de treino e 66 de validação, proveniência
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
grupos original/novo/união e a cauda com limiares históricos. Em dados observados,
o grupo original deriva das partições da coorte pai verificada e publica seu
digest; recortes arbitrários são recusados. A comparação reabre os bundles B/C
nativos dos diretórios verificados antes de prever, verificando seus bytes.

`scripts.full_model_evidence.explain_full(bundle, inputs, data=dados_verificados)` explica de um a
cinco inputs com SHAP CatBoost ou `pred_contrib` LightGBM do q50. Os grupos
cobrem cada coluna exatamente uma vez. Embeddings têm somas assinadas por
modalidade, em log1p(views); base + grupos deve reconstruir q50 com erro
absoluto máximo de 1e-7. Não há interpretação de componentes ou causalidade.
Dados observados exigem esse wrapper e recarga nativa verificada antes de SHAP;
pesos em memória não estabelecem o vínculo ao hash declarado. Fixtures
sintéticas são permitidas explicitamente sem essa proveniência observada.
Esse contrato é um insumo para a Frente 2; não altera o serviço atual.

## Comparação e seleção executáveis

`scripts.compare_full_models.compare_complete` reúne A200/A300, B0/Bcanal,
B-cache e B/C completos nas mesmas linhas. Em canais reservados sem histórico
de treino, Bcanal conserva explicitamente o fallback B0. A seleção considera
somente os completos, tendo A300 como M1 da mesma coorte. Exige MAE log por canal
estritamente menor e média das três perdas quantílicas sem piora. Entre elegíveis,
menor MAE; empate exato favorece B/CatBoost. Sem candidato elegível, permanece
A300 como referência experimental. Nenhuma escolha promove o serviço A200.

A CLI `scripts.run_full_models` oferece `inspect`, `train-b`, `train-c` e
`compare`, com `--data-root`, `--parent`, `--cohort-dir`, `--queue` e
`--quality-release` explícitos. Treino C exige B completo já carregado e pareado;
comparação exige também os diretórios A200/A300/B-cache. Destinos preexistentes
são recusados. A CLI é o ponto de entrada para dados observados, com carga nativa
dos comparadores históricos. Não foi invocada contra dados reais nesta entrega.

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

Após a revisão independente, passaram **34 testes** na seleção final, restrita
ao núcleo lógico 0, com **113,77 s externos** e pico de RSS do filho de
**322.840 KiB (315,27 MiB)**. O recibo medido, log e fixtures estão em
`data/private/fechamento-20261023/frente-1/unit-2-selection/`, com sufixo `frozen`.
Essa seleção cobre proveniência, CLI, regra de decisão e comparação/SHAP B/C
nativos inteiramente inventados; não se soma aos 35 anteriores como cenários
distintos. Os quatro pontos P2 da revisão foram endereçados: loader observado,
recorte vinculado ao pai, recarga para comparação e recarga antes do SHAP.

Permanecem necessários: candidata visual aprovada, seleção/anotação/revisão
independentes, emissão verificável de QualityRelease, ponte dos sidecars da
candidata para o contrato B, extração uniforme, slot de recursos e execução
real B/C. Nenhum desses aceites é inferido dos testes sintéticos.

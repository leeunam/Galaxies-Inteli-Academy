# Contrato técnico V7 dos sete atributos

Este contrato aditivo prepara somente dados **sintéticos** para verificar a compatibilidade de formato e a composição de uma matriz. Não valida percepção visual, não cria `QualityRelease7` e não autoriza treino, inferência ou extração observada. Os gates científicos e a rubrica de sete atributos continuam pendentes.

## Schemas e identidade

`scripts.full_visual_contract_v7` define `front1-seven-field-sidecar-v7`. Um sidecar tem exatamente: `schema_version`, `data_kind`, `sample_id`, `partition`, `channel_id`, `identities`, `input_frame_seconds`, `input_frame_sha256`, `attributes`, `quality_accepted` e `release_emitted`. `data_kind` pode ser `synthetic` ou `observed_unreleased` para checagem estrutural em memória. Ambas as flags devem ter tipo booleano exato e valor `false`. A checagem de sidecar observado nunca faz I/O e não o converte em entrada de preditor.

`identities` tem exatamente `cohort_sha256`, `partition_sha256`, `configuration_sha256` e `candidate_sha256`. O manifesto `front1-seven-field-data-v7-manifest-v1` tem exatamente `schema_version`, `data_kind`, `identities`, `source_versions`, `index_ref`, `index_sha256`, `split_sha256`, `quality_accepted` e `release_emitted`. O índice `front1-seven-field-sidecar-index-v1` contém `schema_version`, `data_kind`, `entries`, `quality_accepted` e `release_emitted`. Cada entrada liga ID, partição, canal, caminhos relativos de features/run e SHA-256 bruto de cada arquivo. Runs usam `front1-seven-field-run-v7` e declaram identidade, conclusão, remoção do diretório temporário e hash das features. Flags em manifesto, índice, run, sidecar e tipos de desenvolvimento são explicitamente booleanas `false`.

## Features e evidência estrutural

A ordem do sufixo segue `scripts.visual_attributes.FIELDS`: `person_visible`, `product_visible_early`, `product_closeup`, `demonstration`, `screen_text`, `scene`, `format`. Cada valor conhecido requer evidência por frames; `unknown` requer uma lista vazia. Essa regra de unknown é mais estrita que alguns sidecars históricos e não converte dados legados. Os primeiros cinco valores são strings `true`, `false` ou `unknown`; `scene` e `format` usam os enums originais. A timeline contém de 1 a 4 tempos inteiros ou floats finitos, não negativos, até 60 segundos e estritamente crescentes, com hashes SHA-256 posicionais. No loader, cada instante também precisa estar dentro da duração do criativo declarada no prefixo B. Frames são inteiros base 1, únicos e dentro da timeline. A evidência de `product_visible_early` só pode apontar para tempos até 3,0 segundos inclusive. Esses vínculos verificam formato e rastreabilidade declarada; não provam conteúdo perceptivo.

A matriz gerada tem 912 colunas: as 905 colunas da implementação B existente, na ordem idêntica, seguidas de `vlm_<campo>` para cada campo acima. As 905 entradas vêm dos `BInputs` cacheados; esta unidade não os reextrai. Os sete valores são strings categóricas explícitas, inclusive `unknown`; nenhum target, ID, canal, tempo, outcome ou campo auxiliar entra no sufixo.

## Loader, hashes e limites

O loader aceita apenas cache B sintético e manifesto sintético explícito. Para cache observado, recusa antes de abrir manifesto ou chamar o validador B; para manifesto observado, lê no máximo o próprio manifesto limitado e recusa antes de acessar índice, sidecars ou alvos. Índice e sidecars precisam corresponder exatamente, na mesma ordem, aos IDs/canais de treino e validação fornecidos pelo cache. Caminhos são relativos, limitados à raiz indicada e arquivos são lidos com teto de 2 MiB antes do parse. SHA-256 de arquivos cobre os bytes crus. Digests de payloads usam `scripts.channel_partitions.digest`, incorporando IDs, entradas B, atributos, proveniência ordenada e versões-fonte nos digests de split.

O manifesto fixa hashes de `experiment_b_data.py`, `visual_attributes.py` e dos dois módulos V7, além dos schemas, representação B e lista canônica de campos. `loader_verified` significa apenas que os arquivos sintéticos explicitamente referenciados foram reabertos, rehasheados e conferidos contra o cache sintético. Não comprova origem, anotação independente, qualidade, aprovação ou equivalência científica. `reload_data` repete essas leituras e comparações; objetos criados manualmente não são recarregáveis.

## Validação e lacunas mantidas

Os testes usam exclusivamente fixtures sintéticas pequenas e verificam a construção de matriz, identidade do prefixo, valores do sufixo, alinhamento, hashes, paths, reload e recusas dos dados observados. A implementação importa o caminho de features B existente somente depois dos gates sintéticos. A suíte pode importar transitivamente CatBoost e os módulos históricos necessários para reconstruir o prefixo; ela intercepta o uso de `Pool`/modelos e não executa instanciação, fit, predict, SHAP ou recarga de pesos.

Esta unidade não valida a rubrica VLM, não cria atributos perceptivamente aceitos, não seleciona um revisor, não prova independência entre desenvolvedor/anotador/revisor e não preenche os 269 casos reais. Os caches B/C existentes permanecem distintos de B/C completos. O contrato não altera versões, gates nem artefatos históricos e não pode servir como autorização para qualquer execução científica.

# Issue #5 — evidência SHAP local do q50 de M1

Preparação de 20/10/2026 dentro do [desenho aprovado](proposta-tecnica.md).
`m1_evidence.explain_m1(bundle, inputs)` recebe um bundle M1 já carregado e
verificado por `load_bundle`/`load_model_context`, e de um a cinco inputs
compatíveis com o treino. Não treina, abre rótulos ou chama explicador externo.
Ainda não altera a resposta da função/MCP nem disponibiliza um grafo.

## Modelo, escala e agrupamento

Usar exatamente `feature_matrix`, nomes e índices categóricos do A para
construir o `Pool`. A previsão explicada é q50 bruto do mesmo bundle servido;
o reparo dos limites q10/q90 preserva q50. A evidência contém o SHA do artefato,
versão, quantil, escala, base e quatro contribuições agrupadas:

- setor: coluna 0;
- propriedades do arquivo: duração e razão altura/largura, colunas 1–2;
- estado da fala: coluna 3;
- embedding da fala: soma assinada das 384 contribuições, colunas 4–387.

O cálculo usa `models[1].get_feature_importance(type="ShapValues")`, sem dataset
de referência ou labels. Segundo o [contrato nativo do CatBoost](https://catboost.ai/docs/en/concepts/python-reference_catboost_get_feature_importance?lang=en),
a última coluna é a base SHAP, além de uma contribuição por feature. A
[aditividade documentada](https://catboost.ai/docs/en//concepts/shap-values)
é conferida novamente no contrato local: base + soma dos quatro grupos precisa
reproduzir q50 em `log1p(views)`, dentro da tolerância numérica declarada.

Não aplicar `expm1` às contribuições individuais, chamar a base de B0 setorial
ou interpretar um componente do embedding como conceito semântico. As
contribuições são associações do modelo nessa escala, sem causalidade; não
explicam a largura da faixa nem demonstram qualidade preditiva. Os números
de previsão/faixa/ranking continuam pertencendo ao preditor.

## Contrato e estado das verificações

A saída estrita `M1Evidence` identifica `native_catboost_shap`, q50, escala
`log1p_views` e `causal=false`. Não contém transcrição, vetores, brief ou labels.
Quantidade de candidatos, contrato das features, suporte à fala, forma da
matriz nativa `(N, 389)`, finitude e reconstrução são validados. Falha retorna
erro local com código fixo; não inventar drivers ou trocar de método/modelo.

Após confirmar o processo VLM encerrado, passaram os oito testes isolados de
contrato e o teste CatBoost nativo com dados inteiramente sintéticos. Junto
dos 18 testes de comparáveis, foram **27 aprovados em 3,75 s**. Ruff e
formatação passaram. Não houve inferência VLM concorrente nessa verificação.
A suíte completa posterior passou em 624 testes em 317,65 s; Ruff e formatação
dos 112 arquivos passaram.

O bundle real servido `9dd1c7a2…d70d59` foi recarregado e explicou três inputs
sintéticos válidos, com embeddings-base unitários e propriedades declaradas,
sem abrir labels para SHAP. A maior diferença entre base+soma dos grupos e
q50 foi **8,88×10⁻¹⁶** na escala log. Isso demonstra o cálculo nativo e a
aditividade desse artefato, sem avaliar qualidade de previsão ou explicação
semântica em inéditos. Não houve fit do modelo real.

Recibos privados em `data/private/issue-5-evidencias-locais-v1/`:
`native-shap-synthetic-queries.json` e `local-verification.json`, com hashes
das fontes/testes e do bundle. A #5 continua sem integração/demo concluídas.

Os [comparáveis de treino](issue-5-comparaveis-treino.md) são outro componente
local separado. Integração StateGraph/NIM, validação factual da explicação e
demo com três criativos distintos continuam necessárias. Não houve mudança
de M1, fontes congeladas, partições, teste reservado, serviço ou `uv.lock`.

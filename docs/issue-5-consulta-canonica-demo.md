# Consulta canônica do relatório preservado da demo

A função Python `get_canonical_demo_report` e a ferramenta MCP stdio de mesmo
nome consultam **o relatório Python real já preservado**, sem recalcular a
análise. Uma leitura Python e uma leitura pelo MCP real devolveram números,
pacote original e metadados iguais. O
[recibo agregado](evidence/issue-5-consulta-canonica-demo-20261020.json)
registra os checks e a prova real sem dados de origem privados.

**A igualdade das consultas não aprova a igualdade das análises independentes.**
O [resultado anterior](issue-5-demo-local-python-mcp-resultado.md), com 22 campos
diferentes, e o [diagnóstico offline](issue-5-divergencia-demo-diagnostico-offline.md)
permanecem válidos. O novo envelope conserva `cold_run_exact_parity=false`.

## Comportamento e limites

O [leitor compartilhado](../scripts/demo_canonical_report.py) valida o contrato
`AnalysisRequest` completo, incluindo brief, campanha, setor, objetivo e IDs
ordenados. Confere os digests do cadastro, configuração, manifesto de mídias,
relatório, recibos da execução Python e origem. Hashes e tamanhos dos três
inputs são reconferidos sem decodificação de vídeo.

Para a fonte real, três hashes auditados **antes** da criação do manifesto
ancoram o arquivo Python original, seu recibo e a origem obtida do histórico
real. Um manifesto e JSON fabricados juntos não habilitam outra fonte real.
Fixtures usam ramo explicitamente identificado como `synthetic_fixture`, com
origem `explicit_invented_fixture_report`; não alegam execução real.

A resposta preservada passa por `IntegratedResponse`, `M1AnalysisResponse` e
`_check_report`, que conferem estados, faixas e ranking. Artefato, extrator e
baseline devem corresponder às identidades seladas. O pacote original conserva
SHAP/comparáveis: não é reconstruído. Seus digests devem vincular a análise
normalizada, modelo, setor, objetivo e hash da explicação. Alteração, falta,
symlink, pedido diferente ou expiração recusam a consulta sem recomputação.

Esta é uma consulta ao **contexto histórico vinculado**. Ela não verifica os
pesos atuais do modelo, não os carrega e não certifica uma previsão nova. O
hash da configuração preservada identifica o contexto da execução original.
Não há cache de features, troca de modelo ou fallback.

O envelope `demo-canonical-consultation-v1` contém o relatório original em
`report` e os metadados separados em `cache`:

```json
{
  "cache_hit": true,
  "origin": "preserved_native_python_report",
  "data_kind": "preserved_real_demo",
  "fresh_extraction": false,
  "fresh_stategraph": false,
  "fresh_provider_call": false,
  "report_flags_describe_historical_execution": true,
  "cold_run_exact_parity": false
}
```

Também são devolvidos os hashes do manifesto, relatório, recibo e origem, além
da expiração. Flags antigas de extração/grafo no relatório descrevem a execução
histórica. Não representam atividade realizada pela consulta.

## Uso opt-in

Os caminhos e o hash do manifesto são configuração do operador. Não são
aceitos no payload da ferramenta. O arquivo privado de configuração e o
recibo novo de entrega apontam os três inputs, pedido e respostas preservados.
Uma passagem privada utilizável, em arquivo `0600`, acrescenta os localizadores
das duas respostas independentes e das consultas canônicas, validade e comandos.
Ela distingue a função/argumentos efetivamente exercitados do exemplo de comando
Python equivalente, que não foi repetido como terceira leitura. Os parâmetros
do entrypoint MCP foram exercitados pela prova stdio do módulo de produção.
Os parâmetros abaixo representam esses valores privados:

```python
from pathlib import Path
from scripts.demo_canonical_report import CanonicalDemoSettings, get_canonical_demo_report

settings = CanonicalDemoSettings(Path(PRIVATE_ROOT), Path(MANIFEST), MANIFEST_SHA256)
result = get_canonical_demo_report(request, settings)
```

O [entrypoint MCP separado](../scripts/demo_canonical_mcp.py) oferece somente
essa consulta; os servidores e funções de análise anteriores não mudaram:

```sh
rtk proxy .venv/bin/python -B -m scripts.demo_canonical_mcp --root "$PRIVATE_ROOT" --manifest "$MANIFEST" --manifest-sha256 "$MANIFEST_SHA256"
```

O consumidor stdio chama `get_canonical_demo_report` com `{"payload": request}`.
As duas consultas reais já autorizadas foram concluídas; este roteiro não
autoriza novas aquisições ou inferências. A retenção dos inputs e a validade
do manifesto terminam em **21/10/2026 às 23h59, São Paulo**. Não existe timer
de exclusão; a consulta não prorroga a janela nem significa demo concluída.

## Verificações

Passaram 25 checks direcionados com números e arquivos inteiramente inventados
em 4,19 s: integridade dos oito arquivos vinculados, pedido completo/ordenação,
bytes/symlink, limites de retenção, modelo/extrator/baseline/pacote, recibo de
execução, origem falsa e cliente MCP stdio real. O teste positivo bloqueia
chamadas a decodificação, extração, carregamento de modelo e execução do grafo.
O relógio fixo da fixture é exclusivo dos testes; o servidor normal usa o
relógio real para recusar expiração.

A primeira rodada encontrou 25 erros de setup na fixture, ao validar listas
JSON como tuplas Python estritas; a fixture foi corrigida para validação JSON,
preservando contratos. Após a revisão editorial da origem sintética, os dois
checks afetados passaram novamente em 4,11 s. Ruff e formatação passaram nos
três arquivos. Nenhuma suíte completa ou inferência foi repetida.

A prova real fez uma consulta Python e uma MCP com rede isolada. Guardas de
chamadas no processo Python e nos threads do servidor MCP registraram zero
tentativas de decodificação, extração, modelos, grafo, comparáveis ou transporte
de explicação. O relatório devolvido é igual ao arquivo Python original, e as
duas respostas completas são iguais, inclusive metadados. Os recibos e resultados
completos ficam privados. Os arquivos antigos e os seis pins anteriores foram
preservados; a árvore principal não recebeu escrita.
Ao concluir, a conferência dos processos próprios de consulta encontrou zero
restantes. Não foi criada configuração persistente de MCP no aplicativo.

A revisão final tornou o parâmetro MCP `payload: object`, para entradas JSON
inválidas chegarem ao getter sanitizado, e habilitou `mask_error_details=True`.
Um check stdio adicional com uma string inválida inteiramente inventada
confirmou recusa fechada e ausência da sentinela na resposta e no log. Os 25
checks e as leituras reais anteriores não foram repetidos; core e relatório
preservado não mudaram.

## Defeito independente ainda aberto

A primeira divergência **observável** está nos valores numéricos da análise M1,
antes da montagem do pacote explicativo: duas entradas diferem em q10/q50/q90.
As mudanças máximas são 3,4939184904349716, 56,292847557117966 e
2.551,7943928820414 views, respectivamente. Posteriormente diferem as
contribuições SHAP do grupo de fala e seis similaridades de comparáveis.
Ranking, base SHAP e grupos de setor/propriedades/estado da fala são iguais.
As diferenças não se restringem ao texto ou aos hashes de apresentação.

Isso não localiza a primeira divergência **interna**: os vetores e seus digests
não foram retidos. O checksum de features do handoff existia somente na memória
de cada sessão; comprova a vinculação interna, sem comprovar igualdade entre
rotas. Configuração de extrator e hash do vídeo não são hashes das features.
Não há base para atribuir a causa a ASR, embedding, ordem ou aleatoriedade,
nem para escolher um reparo numérico ou relaxar a igualdade.

O apoio canônico oferece uma leitura estável e explícita da mesma análise
histórica. A entrega parcial continua identificando a divergência, sem criar
o handoff v3 condicionado à igualdade independente e sem encerrar issues ou
declarar conclusão científica.

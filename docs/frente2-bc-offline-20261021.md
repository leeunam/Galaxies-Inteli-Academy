# Frente 2 — preparação offline de B/C

Base: `277804223eb6121dbeb541c0663af89ccf334eac`. Clone independente
`/tmp/galaxies-front2-bc-offline-20261021`, branch `codex/front2-bc-offline`.
Nenhum alternate/hardlink Git; `.env`, README não rastreado, dados, modelos e
ambientes não foram copiados. A principal permanece somente leitura.

## Correção da fronteira de B

`validate_data` validava o cache e recalculava o baseline a partir dos rótulos
em memória antes de revalidar a liberação perceptiva. Agora revalida o contrato
e o hash do código do gate antes desse acesso. `compare` também chama essa
guarda antes das métricas dos comparadores. Testes inteiramente inventados
interceptam ambos os acessos e exigem recusa de liberação inválida/alterada.

Não muda features, partições, grade CatBoost, tolerâncias, gates, pesos ou
artefatos existentes. Como os bundles fixam hashes de fontes, a mudança exige
novos artefatos em uma futura execução autorizada; não alterar os hashes de
bundles antigos para fazê-los carregar sob o código novo.

## Estado científico

A = CatBoost com metadados/texto; B = CatBoost com o prefixo B-cache de 905
colunas e somente atributos VLM aprovados; C = LightGBM com as mesmas entradas
completas de B. B-cache não substitui B completo. As 300 referências e as
partições 203/66/31 estão preservadas; nenhum arquivo real de dados, features,
rótulos ou teste foi aberto por esta frente.

Extração completa, treino real e comparação científica continuam bloqueados
pela evidência visual válida da Frente 1 e por nova autorização operacional.
Não preencher atributos com valores inventados/`unknown` para simular aceite,
não reutilizar auditorias reveladas como aprovação independente e não afrouxar
os gates. Não houve inferência visual, encoder/loader, mídia, POST NIM,
instalação, alteração de ambiente, gasto, publicação ou fechamento de issue.

## Preparação de C entregue

`experiment_c_data.py` recebe o próprio `VLMDevelopmentData` de B: mesmas
linhas, alvos, ordem de colunas, MiniLM/CLIP/medidas técnicas e sufixo visual
liberado. Não há extrator ou loader de dados alternativo. Somente as strings
categóricas são codificadas para inteiros, com vocabulário aprendido **apenas
no treino**; categorias sem suporte produzem recusa. Não há imputação, PCA,
escala ou substituição silenciosa por `unknown`. A codificação mantém toda a
informação de B e é persistida para recarga.

`train_experiment_c_offline.py` implementa a receita de C já registrada na
[proposta técnica](proposta-tecnica.md): quantis 0,1/0,5/0,9 × 7/15 folhas ×
5/20 exemplos mínimos, profundidade máxima 6, L2 3, taxa 0,05, seed 42,
máximo 500 iterações e parada 50. São doze ajustes, treino uniforme,
validação por inverso da frequência do canal, q50 por MAE log por canal e
extremos por pinball log por canal. O desempate explícito desta preparação
é menor número de folhas e depois menor mínimo por folha, fixado antes de
qualquer resultado real. Um único processo/thread; não altera o protocolo
CatBoost existente de duas threads.

A parada usa exclusivamente um callback da métrica compartilhada, com os
alvos float64 originais. LightGBM armazena internamente labels/pesos em
float32; essa conversão nativa não muda os alvos utilizados pelo callback de
seleção. O default de métrica é desativado para não escolher q50 por uma
outra perda. `feature_pre_filter=False` permite comparar o mínimo por folha
sem reaproveitar filtragem de features da primeira configuração.

O bundle C usa arquivos nativos `.txt`, sem pickle, hashes de modelos,
relatório, lock/fontes e versões. Registra o contrato visual, codificação,
features/categorias, receita, doze tentativas e três escolhas. A recarga
verifica também parâmetros nativos, índices categóricos e número de árvores;
as previsões devem ser exatamente iguais. Saídas são exclusivas, diretório
0700 e arquivos 0600; não sobrescreve artefatos existentes. Inversão do log,
finitude e reparo que conserva q50 reutilizam as funções de A/B.

Treino, recarga e comparação recusam `observed_pilot` **antes** de abrir um
artefato ou construir matrizes/targets. O schema aceita somente `synthetic`,
`run_scope=invented_fixture_only` e `real_results_available=false` no relatório.
Não há flag que libere execução real nem CLI de coleta/treino real. A recarga
nativa LightGBM dos testes não executa o loader visual GGUF.

## Protocolo comparativo preparado

Antes de prever, exigir B completo, liberação visual válida, mesmas features
e categorias, cohort/manifest/baseline, IDs ordenados, hashes dos dois splits
incluindo alvos/entradas, configurações e fontes/versões/lock compatíveis.
Um bundle B-cache/A, mudança de linha, rótulo, feature, partição ou liberação
deve falhar. A comparação registra hashes dos dois artefatos e identidade
compartilhada, sem transformar um resultado sintético em resultado real.

O comparador B/C prepara métricas por setor/canal, MAE log/views, perdas dos
três quantis, cobertura/largura e ranking com suporte. Reutiliza os limiares
fixos de alto alcance (moda 6.403,5; beleza 33.835,3) e os diagnósticos de erro
com sinal, subestimação e casos acima da faixa. Recebe os IDs originais de
validação para formar original/novo/união; nas fixtures sem esse argumento,
todo o desenvolvimento de validação é explicitamente o grupo original.

Em futura execução real, esses grupos deverão ser exatamente 45/21/66,
ancorados no manifesto original, nunca reamostrados após observar resultados.
Reutilizar o comparador congelado de B para A300/A200/B-cache/B0 e acrescentar
C somente após conferir a identidade dos grupos; os números dos comparadores
anteriores permanecem intactos. Validação usada para seleção não é teste
independente; faixa continua estimada/não calibrada. Não atribuir causalidade
a uma modalidade nem generalizar a ablação A/B para LightGBM.

## Verificações e limite da evidência

- **66 testes direcionados passaram em 3,79 s**, com um processo/thread:
  `test_experiment_c_offline.py`, `test_experiment_b_vlm_data.py`,
  `test_experiment_b_data.py` e `test_experiment_b_vlm_quality.py`.
- As fixtures compartilhadas são inteiramente inventadas: 36 linhas de treino
  e 12 de validação, 910 colunas no caso com cinco atributos visuais. Houve
  treino/recarga LightGBM nativos; nenhum treino CatBoost ou visual nesta frente.
- A comparação B/C foi testada com **um contrato e predições B simulados**
  explicitamente dentro do teste. Isso verifica identidade, métricas e recusas,
  não prova paridade com um B completo realmente treinado.
- As recusas cobrem gate inválido antes dos rótulos/Pool/métricas, dados reais,
  B-cache, vocabulário contaminado pela validação, mudança de entradas/alvos,
  features/partições, artefatos/fontes/versões, e parâmetros nativos alterados
  mesmo após recalcular os hashes. Recarga, batch/individual e q50 conferem.
- Ruff e formatação dos seis arquivos Python alterados, além de `diff --check`,
  são as verificações finais desta entrega. Não foi executada suíte completa
  nem alegada revisão independente; a revisão de integração cabe ao supervisor.

## Bloqueio e proposta para o supervisor

O builder B atual exige `QualityRelease` do gate/política v1 e fila completa
de 269 sidecars compatíveis. Um controle visual bem interpretado ou relatório
da Frente 1, sozinho, não constitui esse contrato. Se a correção visual mudar
política, schema ou amostra, é necessário um vínculo versionado e validado,
sem converter recibos antigos em nova aprovação ou flexibilizar o gate.

Não executar a etapa abaixo com esta entrega. Proposta para agrupar após a
evidência visual válida, contrato completo e autorização operacional específica:

1. Entradas: coorte congelada de 300, apenas 203 treino/66 validação, os 269
   sidecars válidos e release ancorado, sem ler nenhum dos 31 casos de teste.
2. Destinos novos propostos: `artifacts/issue-4-bc-approved-visual-v1/B/`,
   `artifacts/issue-4-bc-approved-visual-v1/C/` e relatórios em
   `data/private/issue-4-bc-approved-visual-v1/`. Nunca sobrescrever existentes.
3. Quantidade: 12 ajustes B, recarga/paridade; depois 12 C, recarga/paridade;
   comparação somente da validação, preservando seleção separada por modelo.
4. Tempo: teto operacional proposto de 30 minutos para o bloco de treino/
   comparação, sem estimativa de conclusão com dados reais; se insuficiente,
   parar e relatar, sem ampliar orçamento ou repetir silenciosamente. Esse
   bloco pressupõe extração já concluída e não autoriza novas aquisições.
5. Custo: R$0, CPU local, sem instalação, mídia, NIM ou nova chamada externa.
   Antes disso, adaptar a fronteira C deliberadamente para o contrato aprovado
   e revisar a integração; não basta trocar `data_kind` para burlar o bloqueio.

Esta frente entrega preparação verificável e uma correção da guarda de B.
B/C reais, comparação científica, promoção ao serviço e avaliação final
permanecem pendentes; nenhuma dessas etapas foi declarada concluída.

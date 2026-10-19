# Operação da expansão autorizada

O [protocolo registrado](issue-3-expansao-300-protocolo.md) controla seleção,
orçamento, partições e ajuste. As ferramentas abaixo não mudam seus critérios.
Executar na raiz, com ambiente travado instalado. Dados e imagens são privados.

## Descoberta adicional autorizada

O [aditivo de tópicos/hashtags](issue-3-expansao-300-aditivo-descoberta.md) usa
`python -m scripts.targeted_expansion discover` e depois `migrate`, com `--pool`
e `--parent` iguais aos exemplos abaixo. O resultado vai para `targeted/`.

O [aditivo de cache por domínio](issue-3-expansao-300-aditivo-cache-dominio.md)
usa `python -m scripts.cached_domain_expansion discover` e depois `migrate`,
com os mesmos caminhos. Reaproveita IDs das dezesseis buscas originais; só os
detalhes ainda não observados consomem chamadas. O resultado vai para
`cached-domain/`, com arquivo de alocação anterior às estatísticas e hashes das
buscas de origem.

Registrar e verificar cada aditivo antes de descobrir. `discover` mantém a fila
atual e não modifica o checkpoint de mídia; concluir lote/curadoria antes de
`migrate`. Cada migração conserva backup da fila/checkpoint e journal próprio;
um retry completa a transição sem repetir API. Os limites acumulados não são
reiniciados entre vias. Não executar duas descobertas de metadados ao mesmo tempo.

O [aditivo de domínio](issue-3-expansao-300-aditivo-prioridade-dominio.md) permite,
após terminar lote e curadoria, a reordenação local sem API:

```bash
rtk proxy .venv/bin/python -m scripts.targeted_expansion prioritize-domain \
  --parent data/private/issue-1-pool-treino-20261018-v6/released-cohort-v1 \
  --pool data/private/issue-3-expansao-300-v1 \
  --addon docs/issue-3-expansao-300-aditivo-prioridade-dominio.md
```

Mantém cada linha/observação, as tentativas anteriores e a ordem relativa dentro
das faixas fixas de idioma/indicador de domínio. Título serve só à descoberta.

## Extração e curadoria

```bash
rtk proxy env OPENBLAS_NUM_THREADS=1 .venv/bin/python -m scripts.expansion_media run \
  --pool data/private/issue-3-expansao-300-v1 \
  --parent data/private/issue-1-pool-treino-20261018-v6/released-cohort-v1 --limit 20
```

Um executor por vez. O estado mantém o total de tentativas/tempo e exige concluir
a revisão do lote anterior. Capacidade máxima: 100 inclusões, 50/setor, cinco/canal;
300 tentativas e 90 minutos. O timeout cerca a sessão, cuja limpeza ocorre no
unwind. Idioma insuficiente, repetição severa, duplicata ou falha não viram inclusão.

O [aditivo de continuidade](issue-3-expansao-300-aditivo-orcamento-midia.md)
permite estender só o teto de tentativas acumuladas para450. Para ativá-lo,
acrescentar ao comando `run`:

```bash
  --attempt-limit 450 --budget-addon docs/issue-3-expansao-300-aditivo-orcamento-midia.md
```

O checkpoint vincula o arquivo por hash, conserva os contadores e5400s originais
e exige os mesmos parâmetros nas próximas execuções. Sem opção explícita, o
limite continua300. Redução/troca de política é recusada. A liberação também
revalida o vínculo antes de publicar, sem alterar os extratores congelados.

`inspect` com os mesmos argumentos retorna só IDs, caminhos dos contatos visuais
e transcrição dos pendentes, sem views. O revisor deve realmente abrir as imagens
e ler a fala, depois fornecer um JSON privado de decisões para `review --decisions`.
Cada decisão exige `video_id`, `decision`, `sector`, `reason`, confirmações
`image_review_performed=true`, `transcript_review_performed=true` e o SHA256
da folha vista em `contact_sheet_sha256`. Não se deve preencher confirmações sem
realizar a revisão. São decisões assistidas, sem alegar escuta humana ou
certificação de dialeto. Campos truthy no lugar de bool verdadeiro são recusados.

O recibo da anotação completa é ligado ao checkpoint antes de remover a folha.
Limpeza pendente é durável e repetida antes de prosseguir; falha não libera nova
aquisição nem apaga outra condição de parada. Excluir também grids auxiliares
usados na inspeção. Mídia bruta não é retida.

## Publicação, ajuste e comparação

Somente quando as 100 inclusões e limpezas estiverem verificadas:

```bash
rtk proxy env OPENBLAS_NUM_THREADS=1 .venv/bin/python -m scripts.retrain_expansion publish \
  --parent data/private/issue-1-pool-treino-20261018-v6/released-cohort-v1 \
  --pool data/private/issue-3-expansao-300-v1 \
  --cohort-dir data/private/issue-3-expansao-300-v1/released-cohort-v1

rtk proxy env OPENBLAS_NUM_THREADS=1 .venv/bin/python -m scripts.retrain_expansion train \
  --parent data/private/issue-1-pool-treino-20261018-v6/released-cohort-v1 \
  --pool data/private/issue-3-expansao-300-v1 \
  --cohort-dir data/private/issue-3-expansao-300-v1/released-cohort-v1 \
  --model-dir artifacts/issue-3-experimento-a-300-v1

rtk proxy env OPENBLAS_NUM_THREADS=1 .venv/bin/python -m scripts.retrain_expansion compare \
  --parent data/private/issue-1-pool-treino-20261018-v6/released-cohort-v1 \
  --pool data/private/issue-3-expansao-300-v1 \
  --cohort-dir data/private/issue-3-expansao-300-v1/released-cohort-v1 \
  --model-dir artifacts/issue-3-experimento-a-300-v1 \
  --report data/private/issue-3-expansao-300-v1/comparison.json
```

A publicação valida estritamente os recibos, evidências novas, baseline/labels e
índice do pai. Escreve num staging privado e renomeia só após validar a coorte
ampliada e B0. Falha remove o staging, sem publicar um bundle parcial. Conserva
os 200 metadados e assignments; aceita rótulos antigos somente do treino.

O carregador restrito seleciona treino/validação antes da leitura de evidências.
Uma guarda ativa nas operações CLI também recusa `records.json`,
`predictor-inputs.json` antigos e cada caminho de evidência do teste. A publicação
não cria cópia mista de rótulos contendo o teste.

A usa as rotinas offline congeladas, com exatamente a busca aprovada, recarga e
inferência. A comparação verifica igualdade integral dos antigos splits de
desenvolvimento; calcula B0/A antigos/novos na validação original, nova e união,
com recorte de alto alcance fixado no protocolo. Nenhuma métrica final ou
superioridade causal é inferida dessa validação usada para seleção. As ferramentas
não iniciam B nem alteram a configuração do serviço M1 atual.

O teste integrado cria uma coorte inteiramente sintética de 200 e publica 100
adições (50/setor) com a guarda ativa. Confere os 300 assignments, preservação
exata do teste e ausência de arquivos mistos de rótulos; outros testes exercitam
rollback/retry de staging e recibos adulterados. Esses fixtures não são novas
referências reais nem evidência de qualidade preditiva.

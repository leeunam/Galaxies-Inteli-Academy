# Operação da expansão autorizada

O [protocolo registrado](issue-3-expansao-300-protocolo.md) controla seleção,
orçamento, partições e ajuste. As ferramentas abaixo não mudam seus critérios.
Executar na raiz, com ambiente travado instalado. Dados e imagens são privados.

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

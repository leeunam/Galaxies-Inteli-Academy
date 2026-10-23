# 🧊 iSee

Análise preditiva de criativos antes da publicação.

Desenvolvido por **Leunam Sousa** para a **Galaxies**, no contexto da **Inteli Academy**. O nome combina a leitura de *I see* com o trocadilho visual de *ice*.

O iSee investiga uma escolha de quem produz conteúdo: entre vídeos ainda não publicados, qual vale priorizar em um teste de divulgação? Para isso, transforma características do conteúdo em entradas de um modelo estatístico e apresenta estimativas de visualizações, faixas, ordenação e evidências.

É um **serviço local em Python**, acessível por função, CLI e ferramentas **MCP por stdio**. A função, a CLI e o MCP básico chamam o mesmo analisador diretamente. Um segundo percurso, integrado na versão v2, usa LangGraph para organizar a análise e a explicação. A persona da Galaxies poderá consumir essa ferramenta; a construção da persona e a integração com a plataforma interna da empresa ficam fora deste projeto.

## Estado atual

O projeto está em fechamento do escopo. Há modelos treinados e percursos executados com dados reais, além de testes públicos com dados inventados. A avaliação final ainda não foi realizada.

| Parte | Evidência disponível | Limite atual |
| --- | --- | --- |
| M1 / A200 | CatBoost servido, quantis, SHAP e comparáveis; prova histórica Python/MCP com três vídeos reais | Não comprova desempenho prospectivo ou retorno de patrocínio |
| A300 / B-cache / C-cache | Treino e comparação reais na validação; B/C-cache incluem CLIP e atributos técnicos | Não equivalem a B/C completos com atributos VLM aprovados |
| Explicação NVIDIA | Seleção real de IDs de evidência em exemplo inteiramente inventado, com renderer local | Cobertura parcial; aderência a uma campanha real não avaliada |
| Fluxo cacheado | Três casos reais passaram por previsão, SHAP, comparáveis e texto local | Começou em features preservadas; não executou mídia, MCP, StateGraph ou NIM nesse ensaio |
| VLM e avaliação final | Implementações, protocolos e resultados de diagnóstico preservados | Qualidade visual sem aprovação; teste de 31 casos reservado |

Os registros de execução anteriores continuam válidos para os contratos que cobriram. Abrir um resultado salvo consulta aquela execução; não repete a extração ou a previsão. O [guia de evidências](docs/entrega-20261021.md) distingue esses percursos. A [matriz de fechamento](docs/fechamento-20261023.md) registra os aceites restantes.

Na tentativa diagnóstica de 23/10, a preparação da cápsula local foi recusada na criação de um namespace. Houve uma tentativa de preflight, limpeza confirmada e **zero chamadas de modelo**. Isso não acrescenta resultado perceptivo. O [relatório da parada](docs/fechamento-frente-1-diagnostico-v2-resultados.md) preserva a contagem e distingue a falha do ambiente de um resultado do VLM.

A [ponte de B/C completos](docs/fechamento-frente-1-c-completo.md) tem código e testes sintéticos de pareamento, seleção, recarga e SHAP. Seu uso com dados observados exige liberação de qualidade e sidecars compatíveis; esses aceites continuam ausentes.

## Entrada e saída

O operador cadastra arquivos locais autorizados. Cada pedido usa de **um a cinco IDs distintos**, da mesma campanha e setor, acompanhados de:

- setor: `moda` ou `beleza`;
- objetivo: `divulgacao`;
- briefing: descrição textual da intenção da campanha.

Um candidato recebe análise individual; dois a cinco recebem comparação. Quando houver previsão disponível, a resposta contém q50, faixa q10–q90, versão do modelo e avisos de suporte. A comparação usa q50 para ordenar os candidatos. A camada de evidências pode acrescentar SHAP e referências semelhantes do treino.

O alvo é a contagem pública de views observada com **30 <= idade < 37 dias**. Não é a reconstrução das views exatamente no dia 30. Curtidas são informação retrospectiva, não entrada do próprio vídeo inédito. O briefing contextualiza o pedido; no M1 atual, ele não altera a previsão numérica.

## Arquitetura

```mermaid
flowchart LR
    U[Vídeos autorizados e briefing] --> R[Cadastro local e IDs]
    R --> P[Validação Pydantic]
    CLI[CLI ou função Python] --> P
    MCP[MCP básico / stdio] --> P
    MCP2[MCP integrado v2 / stdio] --> G[LangGraph e worker local]
    G --> P
    P --> E[Extração versionada]
    E --> F[Fala, embeddings e atributos do arquivo]
    F --> M[CatBoost M1 / A200]
    M --> Q[Quantis e ranking]
    M --> S[SHAP nativo]
    F --> C[Comparáveis somente do treino]
    Q --> K[Catálogo de evidências]
    S --> K
    C --> K
    K --> L[Validação e texto local]
    K -. Em validação: seleção NVIDIA NIM .-> N[IDs de evidência permitidos]
    N -.-> L
    E -. Experimentos .-> V[CLIP, medidas técnicas e atributos VLM]
    V -.-> BC[B CatBoost / C LightGBM completos]
```

As linhas pontilhadas mostram extensões experimentais ou sem aceite integrado. O grafo pertence ao percurso v2; não é executado pela CLI ou pelo MCP básico. Há evidência real histórica desse percurso com M1, mas o ensaio recente com três casos cacheados não executou o grafo nem o MCP. O servidor integrado atual não configura um provedor externo automaticamente.

Python reúne o processamento de mídia e as bibliotecas de ML. FFmpeg/ffprobe e PyAV tratam a mídia; faster-whisper transcreve a fala; MiniLM a representa numericamente. CatBoost e LightGBM permitem comparar modelos tabulares não lineares. CLIP e o VLM fazem parte da representação visual experimental. SHAP decompõe a previsão do modelo, sem atribuir causalidade.

Pydantic valida os contratos. FastMCP expõe a lógica por stdio, sem exigir uma API HTTP. LangGraph fica em um ambiente separado para preservar a compatibilidade do ambiente de extração e predição. A NVIDIA seleciona evidências permitidas; o validador e o renderer locais conservam os fatos e os números.

## Instalação

Requisitos: **Python 3.11**, `uv` e dependências do sistema necessárias ao processamento de mídia. Na raiz deste repositório:

```bash
uv sync --frozen
uv sync --project orchestration --frozen
```

A primeira instalação pode obter dependências da rede. Com o cache previamente preparado, acrescente `--offline`. Preserve os dois locks e os ambientes separados: `.venv/` e `orchestration/.venv/`. Não sincronize ambientes durante uma extração ou treinamento.

O clone público não contém mídias, coortes privadas, pesos dos extratores ou bundles treinados. A previsão real depende desses recursos e de versões compatíveis. Os extratores não devem baixar ou substituir pesos silenciosamente durante uma análise. As revisões estão documentadas em [extratores e treino](docs/issue-1-extratores-e-treino.md).

## Primeiro teste, sem dados privados

Depois de instalar as dependências, execute:

```bash
uv run --frozen python -m scripts.demo_creatives
```

O comando gera vídeos vazios temporários e compara as respostas da função Python e de um cliente MCP real. Não precisa de chave, mídia de terceiros ou modelo treinado. Nesse modo, a previsão fica explicitamente indisponível.

Para exercitar também uma referência numérica inventada:

```bash
uv run --frozen python -m scripts.demo_creatives --synthetic-baseline
```

Esse segundo modo testa contratos e transporte com **baseline sintético**. Seus números não são resultados de um modelo treinado em vídeos reais.

## Analisar um arquivo autorizado

Coloque o vídeo em `uploads/` e faça o cadastro local:

```bash
.venv/bin/python -m scripts.creative_cli register \
  --campaign-id minha-campanha \
  --sector beleza \
  --relative-path meu-video.mp4
```

Use o ID retornado para montar um pedido JSON privado com `campaign_id`, `sector`, `objective`, `brief` e `creative_ids`. O cadastro e o pedido devem usar a mesma campanha/setor. O [guia de reprodução](docs/guia-reproducao-local.md) detalha esse contrato.

Com o bundle M1 e sua coorte já disponíveis nos diretórios documentados:

```bash
.venv/bin/python -m scripts.creative_cli analyze \
  --request-file data/private/minha-campanha/request.json \
  --m1-model-dir artifacts/issue-3-experimento-a-v1 \
  --m1-cohort-dir data/private/issue-1-pool-treino-20261018-v6/released-cohort-v1
```

Esse comando exige arquivos reais existentes e autorizados; eles não vêm no clone público. A função compartilhada é `scripts.creative_analysis.analyze_creatives`, configurada com `CreativeRegistry` e `M1Settings`. Falhas de extração, idioma ou compatibilidade retornam estados explícitos, sem substituir silenciosamente o modelo.

## Usar pelo MCP

Configure o cliente MCP com transporte **stdio**, diretório de trabalho na raiz do repositório e o servidor:

```bash
.venv/bin/python -m scripts.creative_mcp \
  --m1-model-dir artifacts/issue-3-experimento-a-v1 \
  --m1-cohort-dir data/private/issue-1-pool-treino-20261018-v6/released-cohort-v1
```

A ferramenta se chama `analyze_creatives` e recebe o pedido no campo `payload`. O cliente inicia o processo e envia as mensagens MCP. Executar o servidor isoladamente deixa-o aguardando essas mensagens.

O percurso com grafo e pacote de evidências usa `scripts.explanation_graph_mcp_v2` e a ferramenta `analyze_creatives_with_explanation`. Ele exige `--graph-python` apontando para `orchestration/.venv/bin/python` e os recursos compatíveis descritos no [guia da integração nativa](docs/issue-5-integracao-nativa-v2.md). Esse percurso não implica que uma chamada NVIDIA real esteja configurada ou validada.

## Consultar uma explicação preservada

Defina `GALAXIES_REPORT_JSON` como o caminho de um relatório local autorizado e existente. Para apresentá-lo com o catálogo de evidências:

```bash
.venv/bin/python -B -m scripts.explanation_display \
  "$GALAXIES_REPORT_JSON" --show-local-evidence
```

O leitor confere os vínculos do relatório e distingue a seleção original do catálogo completo. Não calcula nova previsão, SHAP ou comparáveis e não chama a NVIDIA. A seleção pode estar ausente mesmo quando há evidências locais disponíveis.

## Dados, experimentos e resultados

A fonte é **YouTube Shorts de moda e beleza em português**, com metadados e contagens obtidos pela **YouTube Data API v3** e características extraídas da mídia. A coorte ampliada foi consolidada em **19/10/2026**. As datas de publicação e de observação de cada referência estão nos manifestos privados; a janela do alvo é de 30 a menos de 37 dias de idade. O intervalo completo de datas da coleta não foi recalculado nesta revisão.

A autorização da plataforma e o enquadramento de licenças e condições de uso não estão comprovados nos registros do projeto. A autorização operacional de coleta e a extração técnica não equivalem a essa aprovação. O [registro de origem e uso](docs/uso-youtube-e-plano-de-entrega.md) e a [curadoria final](docs/issue-1-curadoria-final.md) preservam essa pendência.

A coorte atual tem **300 referências de 166 canais**, com divisão **203 treino / 66 validação / 31 teste**. O modelo servido continua A200, treinado nos 124 exemplos de treino da coorte original de 200. A comparação ampliada não o substitui automaticamente.

Nos mesmos 66 exemplos e 37 canais de validação:

| Modelo | MAE log médio por canal |
| --- | ---: |
| A200, controle histórico servido | 1,7349 |
| A300 | 1,7761 |
| B-cache | 1,6584 |
| C-cache | 1,5444 |

Menor é melhor. A métrica mede erro em `log1p(views)`, com peso total igual por canal; não é acurácia nem erro contado em views. A validação também foi usada para selecionar hiperparâmetros. Esses números não são do teste final. O ganho agregado não é uniforme, e os casos de alto alcance continuam subestimados.

Os experimentos têm registro local com configurações, versões, hashes, modelos e recibos. Consulte:

- [Formulação e decisões técnicas](docs/proposta-tecnica.md).
- [Treinamento e comparação de A](docs/issue-3-treinamento-offline.md).
- [Experimento B-cache](docs/issue-4-experimento-b-resultados.md).
- [Comparação A300/B-cache/C-cache](docs/issue-4-experimento-c-cache-resultados.md).
- [Revisão das explicações](docs/issue-5-nim-quality-review-v1.md).
- [Procedimento da avaliação final](docs/issue-6-protocolo-final-e-checklist-v1.md).

Os comandos de treinamento dependem dos manifestos e caches privados identificados nesses protocolos. A abertura do teste reservado é uma etapa separada, com configuração congelada e autorização própria; não faz parte do teste de instalação.

## Privacidade e limites

Credenciais ficam fora de prompts, logs e Git. `.env.example` contém somente nomes de variáveis; a CLI local não carrega `.env` nem dispara APIs automaticamente. Os IDs da ferramenta fazem referência a um cadastro local, em vez de aceitar caminhos arbitrários do cliente.

Mídias, transcrições, dados e pesos permanecem fora do repositório público. Downloads concluídos não comprovam autorização de uso: origem, condições de uso, retenção e destinos permitidos precisam estar registrados. Conteúdo privado não deve ser enviado a um serviço externo sem autorização compatível.

As faixas q10–q90 são estimadas e não têm garantia automática de cobertura de 80%. Views públicas podem misturar alcance orgânico e pago. O projeto não demonstra causalidade, classificação universal de viralidade ou retorno de patrocínio. Aderência ao briefing, qualidade visual e avaliação final ainda têm aceites abertos.

## Verificações de desenvolvimento

Os testes públicos usam fixtures e não devem abrir o holdout ou iniciar chamadas externas:

```bash
.venv/bin/pytest -q --tb=short --show-capture=no
.venv/bin/ruff check scripts tests
.venv/bin/ruff format --check scripts tests
```

Combine a execução com os demais responsáveis antes de rodar a suíte completa. Testes de código, fidelidade matemática e qualidade preditiva são verificações diferentes. Os relatórios de 23/10 registram 114 checks e, em execução posterior à correção de apresentação, 22 testes; as contagens incluem casos repetidos entre as execuções.

O código preserva identificadores técnicos históricos com o prefixo `galaxies`. O nome público da solução é **iSee**; esses identificadores não foram renomeados para evitar invalidar contratos e artefatos existentes.

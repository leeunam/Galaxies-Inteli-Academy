# Correção do extrator visual e conferência da fala

Piloto da [issue #1](https://github.com/leeunam/Galaxies-Inteli-Academy/issues/1),
17/10/2026, horário de São Paulo. Complementa o [primeiro teste real](piloto-youtube-real.md).

## Decisão e resultado

Substituir o SmolVLM2-500M por **Qwen3-VL-2B-Instruct, GGUF Q4_K_M**, executado
localmente com **llama.cpp b11716**, CPU e quatro threads. Não há envio de mídia a uma
API externa. O NIM continua reservado ao futuro explicador, componente diferente.

O lote de três vídeos concluiu a aquisição temporária, comparação ASR e nova extração
visual. As três respostas Qwen têm esquema válido e evidências com índices dos frames.
A inspeção assistida dos frames mostrou melhora nos controles de pessoa, produto e
composição gráfica. Encontrou também um falso positivo de aplicação. **Close-up e
aplicação ficam globalmente bloqueados como `unknown`**, com resposta original preservada.
Não declarar os sete atributos aprovados nem anunciar acurácia de percepção da base.

O aluno ouviu e confirmou as três transcrições originais: primeiro fala/narração;
terceiro canto; segundo vocal sem classificação separada. Foi conferência assistida,
com hipótese visível, sem anotação cega independente. O [relatório ASR](validacao-transcricoes.md)
registra método, resultados e limites. Manter Whisper small CPU int8, beam 1 e VAD ativo;
a configuração alternativa avaliada foi pior nessa referência.

## Por que o extrator anterior falhou

Havia dois problemas distintos:

1. **Contrato ambíguo.** O modelo devolvia campos planos em vez de objetos com `value`
   e `frames`; texto na tela foi confundido com transcrição OCR, e formato com `json` ou
   `image`, em vez do tipo de apresentação do criativo. As respostas originais terminavam
   completas; não havia evidência de que aumentar o limite de tokens resolveria.
2. **Percepção insuficiente neste piloto.** Perguntas fechadas por frame corrigiram a
   forma, mas produziram negativos em pessoas/produtos visíveis e pessoa/reação numa
   colagem sem gente. Esquema correto não corrigia o conteúdo. Essa tentativa não é
   backend ativo; os experimentos privados e o histórico Git preservam o diagnóstico.

A troca usa um modelo maior quantizado para caber no computador, sem carregar os pesos
em FP32. É uma decisão prática baseada nos controles do piloto, sem provar superioridade
geral do Qwen ou que modelos maiores sempre resolvem a tarefa.

## Contrato visual e barreira de qualidade

- Entrada: até quatro frames cronológicos; alvos de 0,2 s, 1,5 s, 2,8 s e 60% da duração,
  limitados ao intervalo válido e deduplicados. Seleção pelos timestamps reais, pois a
  ordenação dos seis frames técnicos pode mudar os índices em vídeos curtos.
- `person_visible`: rosto ou corpo humano; roupas sem pessoa não contam.
- `product_visible_early`: cosmético, aplicador, peça de roupa ou acessório apresentado
  até 3 s; roupa incidental de quem fala não basta. Referência a frame tardio é rejeitada.
- `screen_text`: presença de texto, sem exigir OCR. Cena usa enumeração de ambiente;
  formato descreve apresentação, como reação ou exposição de produtos.
- `product_closeup`: bloqueado por rubrica ambígua sobre detalhe do produto versus rosto.
- `demonstration`: bloqueado após confundir apresentação de embalagem com aplicação.
- Respostas incertas permanecem `unknown`; o campo utilizável fica sem frames de evidência.
  A limitação é sobre as imagens amostradas, sem afirmar o que ocorre entre elas.

O runtime restringe a geração por JSON Schema; um validador Python independente confere
estrutura, tipos, enumerações, duplicatas, índices e evidências temporais. A política
`visual-quality-gate-v1` preserva `raw_response` e `model_parsed`, e aplica o bloqueio a
`parsed` para **qualquer vídeo**, sem corrigir manualmente somente os erros conhecidos.
Versão e motivos ficam no resultado. `approved_for_training` continua falso: campos
restantes precisam de revisão em mais exemplos antes de ampliação.

O bloqueio é uma exclusão por qualidade, não uma correção perceptiva desses dois campos.
Não imputar desconhecido como falso nem incluir colunas constantes no treino como se
fossem atributos informativos. Sua reativação exige rubrica precisa e novos controles,
incluindo negativos, sem usar o teste preditivo final para decidir essa regra.

## Conferência nos três vídeos

A revisão visual foi feita pelo Codex em quatro frames por vídeo; não é anotação humana
independente. As confirmações auditivas foram feitas pelo aluno sobre os vídeos completos.

| Caso | Conferência visual assistida | Ressalva |
| --- | --- | --- |
| Beleza 1 | Pessoa, produto inicial, texto, interior e reação em tela dividida coerentes | Close-up ambíguo; aplicação bloqueada globalmente |
| Beleza 2 | Pessoa com cosméticos, interior e apresentação frontal coerentes | Aplicação `true` foi falso positivo; texto `unknown` foi abstenção apesar de texto visível |
| Moda | Sem pessoa; roupas/acessórios iniciais, texto, composição gráfica e exposição de produtos coerentes | Close-up bloqueado; nenhum uso/aplicação visível nos frames |

O lote mediu 93,77 s, 91,46 s e 108,57 s por sessão, incluindo download e duas configurações
de ASR, mas sem embeddings nesta revisão. Só o Qwen levou 73,59 s, 75,91 s e 86,05 s.
Seu pico RSS amostrado ficou entre 2.606,76 e 2.616,52 MiB, aproximadamente **2,55 GiB**.
Houve uma inspeção pontual concorrente durante a última sessão; não tratar esses tempos
como benchmark controlado ou promessa de latência do serviço completo.

Os picos Python e VLM são medições separadas: `process_peak_rss_mib` é acumulado no
processo Python e exclui filhos; `runtime_peak_rss_mib` mede o processo C++ a cada 100 ms.
O guard de 3,3 GiB vale para esse filho, não para toda a aplicação. O timeout VLM é 180 s.
Processos próprios são encerrados em cancelamento/timeout; queda da máquina ou término
forçado pode exigir limpeza na retomada. Uma interrupção durante os diagnósticos deixou
uma pasta órfã, identificada e removida antes da conclusão; não prometer limpeza infalível.

Os três diretórios temporários do lote concluído foram removidos. Artefatos privados:
`data/private/youtube-quality-qwen-20261017/`, com `features.json`, `run.json`, `batch.json`
e `quality_review.json`. Os resultados gerados antes da barreira não foram sobrescritos;
o relatório derivado contém hashes das fontes, respostas originais e atributos filtrados.
O lote anterior `youtube-quality-v3-natural-20261017` preserva a comparação ASR congelada.

O fluxo principal também concluiu um vídeo com ASR, embeddings MiniLM/CLIP e Qwen na mesma
sessão: **99,00 s**, vetores finitos de 384/512 dimensões, resposta original preservada,
close-up/aplicação bloqueados e mídia removida. Pico Python 1.252,68 MiB; pico do filho
VLM 2.617,41 MiB, sem representar um pico total sincronizado. Evidência em
`data/private/youtube-integrated-qwen-20261017/`. Ao final, restaram zero sessões de mídia.

Essas execuções precederam o ajuste final da seleção por timestamps. Em um vídeo curto,
os índices fixos anteriores escolheram 2,367 s em vez do alvo 2,8 s. O seletor foi corrigido
e verificado por teste de regressão para ordenação e deduplicação; não se afirma nova
avaliação perceptiva do frame substituído ou repetição integral da inferência após esse
ajuste. As evidências guardam os instantes efetivamente usados em cada execução.

Verificação local: **23 testes passam**, Ruff e formatação passam, dependências/lock
consistentes e links locais conferidos. Os testes cobrem contrato, evidência temporal,
abstenção, preservação da resposta, limpeza, falhas e métricas ASR; não medem percepção
ou desempenho preditivo. Os pesos/runtime também tiveram seus hashes verificados offline.

## Preparação e reprodução

Pesos oficiais fixados na revisão `52d6c8ffea26cc873ac5ad116f8631268d7eb503`:
`Qwen3VL-2B-Instruct-Q4_K_M.gguf` e `mmproj-Qwen3VL-2B-Instruct-Q8_0.gguf`.
Os SHA-256 constam de `scripts/gguf_visual_attributes.py`; runtime e seu arquivo oficial
têm versão/hash fixados em `scripts/prepare_gguf_vlm.py`. A preparação verifica os pesos
e reinstala executável/bibliotecas a partir do arquivo verificado antes da mídia.
O runtime preparado é Linux x64; modelos e binários ficam em cache ignorado pelo Git.

```sh
rtk proxy uv sync --locked
rtk proxy .venv/bin/python -m scripts.prepare_gguf_vlm
rtk proxy .venv/bin/python -m scripts.prepare_gguf_vlm --offline
rtk proxy env HF_HOME=data/cache/huggingface HF_HUB_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 TOKENIZERS_PARALLELISM=false OPENBLAS_NUM_THREADS=4 .venv/bin/python -m scripts.pilot_youtube_media --candidates data/private/youtube-pilot-candidates.json --output data/private/youtube-qwen-novo --with-vlm
```

Usar uma saída nova. Os modelos HF de ASR/embeddings precisam estar previamente em cache
para o modo offline; a aquisição YouTube continua usando rede. Para comparar configurações
ASR novamente, usar `scripts.review_pilot_quality` com candidatos, `--original-root` e
`--output` privados. Nunca sobrescrever resultados anteriores nem supor que um contêiner
readquirido tenha os mesmos bytes do anterior. A comparação ASR usa o mesmo PCM na sessão.

## Próximo checkpoint da issue #1

Fala confirmada e controles visuais mínimos permitem fechar este diagnóstico técnico;
não liberam uma coleta noturna grande. Antes de ampliar, concluir curadoria de setor,
idioma e elegibilidade, condições da fonte, critérios/cobertura do corpus e custo
operacional. Verificar também CatBoost/LightGBM e o explicador NIM com evidências sintéticas.
O treino A → B → C, a avaliação entre canais e a previsão de alcance continuam pendentes.
Nenhum resultado deste piloto é métrica de previsão de viralidade ou retorno de patrocínio.

Referências primárias: [pesos Qwen GGUF oficiais](https://huggingface.co/Qwen/Qwen3-VL-2B-Instruct-GGUF),
[llama.cpp b11716](https://github.com/ggml-org/llama.cpp/releases/tag/b11716),
[SmolVLM2 original](https://huggingface.co/HuggingFaceTB/SmolVLM2-500M-Video-Instruct)
e [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

# Coleta retomável de metadados

Modo explícito para retomar a coleta da issue #1 sem perder páginas concluídas ou duplicar
detalhes. Esta etapa não baixa mídia nem aprova condições de uso, e não cria amostra de treino.
O comando legado continua disponível. A saída privada não inclui resposta crua ou credenciais.

## Metadados por canal, página e lote de detalhes

O modo novo é explícito; sem `--resumable`, o coletor legado permanece disponível.
Estes comandos consultam a API somente quando executados pelo responsável com a chave local:

```bash
rtk proxy .venv/bin/python -m scripts.collect_channel_metadata \
  https://www.youtube.com/@canal-exemplo --resumable \
  --pages-per-channel 2 --detail-batch-size 50 --max-api-calls 10 \
  --output data/private/metadados-retomaveis.json
rtk proxy .venv/bin/python -m scripts.collect_channel_metadata \
  https://www.youtube.com/@canal-exemplo --resumable --resume \
  --pages-per-channel 2 --detail-batch-size 50 --max-api-calls 10 \
  --output data/private/metadados-retomaveis.json
```

Limites novos: **1–30 referências de canais**, **1–5 páginas por canal**, **50 IDs por página**,
lotes de detalhes de **1–50 IDs** (padrão 50), e **1–100 requisições por invocação** (padrão 30).
Canais/páginas/tamanho do lote e protocolo devem coincidir na retomada; o orçamento de chamadas
pode mudar. `--resume` exige arquivo existente, e arquivo existente exige `--resume`.
As referências são convertidas em filtros não secretos; URLs de entrada não são persistidas.
O modo permite saída dentro de `data/private` ou `data/raw`, ambas ignoradas.

O checkpoint salva a resolução de cada canal, página concluída, próximo token, IDs únicos,
lotes de detalhes já consultados (incluindo indisponíveis), registros normalizados e total de
requisições tentadas. Salva antes de tentar cada chamada e depois de cada unidade concluída;
erro de rede/cancelamento não apaga progresso. Uma interrupção entre resposta e gravação pode
repetir a última chamada, sem duplicar IDs/registros. Não salva `Client.calls`, resposta bruta,
chave, URL assinada ou mensagem crua de erro. Checkpoint atômico e lock também se aplicam aqui.

`request_count` é o total de tentativas desde o início; `invocation_requests` é o gasto atual,
incluindo chamada que falhar (em erro, consultar o total no checkpoint). `coverage_partial` informa
se a playlist foi truncada/não terminou, `details_partial` informa detalhes ainda não consultados,
e `unavailable_video_ids` diferencia indisponibilidade de falta de consulta. O intervalo
`observed_publication_interval` mostra mínimo/máximo das publicações com detalhes obtidos por canal.
A saída resumida e o checkpoint registram a cobertura; para IDs/records completos, ler o checkpoint
ou usar `summary` do módulo de retomada.

Uma página não comprova 30–37 dias de cobertura. Não há filtro de data nem parada por janela;
o consumidor deve inspecionar o intervalo real e selecionar o horizonte sustentado pelas datas
de publicação e coleta. Metadados completos **dentro do limite de páginas** podem continuar com
cobertura parcial da playlist. Não se cria partição de treino nem se habilita mídia a partir disso.

## Verificação local

```bash
rtk proxy .venv/bin/ruff check scripts tests
rtk proxy .venv/bin/python -m pytest -q
```

Os testes de metadados usam API sintética: orçamento, erro de rede, retomada, deduplicação,
incompatibilidade de protocolo/configuração e cobertura parcial. Não demonstra cobertura de
300 vídeos, adequação das condições da fonte ou validade preditiva.

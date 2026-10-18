# Coleta retomável e fila audiovisual privada

**Orientação posterior de 18/10:** o aluno autorizou expressamente consultar a API
e adquirir temporariamente os vinte candidatos sem preencher o aditivo. O
[lote direto](issue-1-coleta-direta-e-setores.md) concluiu dezessete novos downloads,
sem alterar as revisões/estados da fila antiga. A restrição do checkpoint abaixo
descreve o contrato dessa fila; não revoga a autorização posterior do aluno nem
impõe repetir o pedido para esse lote. Aprovação da plataforma continua não verificada.

Esta entrega prepara a issue #1; não cria amostra de treino nem aprova condições de uso.
A fonte continua pendente: **não executar aquisição audiovisual real enquanto essa revisão não
estiver concluída e registrada**. Preparar/inspecionar usa somente arquivos locais, sem carregar
modelos, consultar credenciais, baixar mídia ou enviar dados ao NIM. Os testes são sintéticos.
O piloto `scripts.pilot_youtube_media` mantém seu limite original de três candidatos e seu comando.

## Primeiro passo: preparar vinte exemplos, sem rede

Na raiz do projeto, com o ambiente existente e candidatos no namespace
`audit/curation/metadata/target/diagnostics`:

```bash
rtk proxy .venv/bin/python -m scripts.prepare_media_queue prepare \
  --candidates data/private/candidatos-issue-1.json \
  --queue data/private/fila-issue-1-20 --limit 20 --with-vlm
rtk proxy .venv/bin/python -m scripts.prepare_media_queue inspect \
  --queue data/private/fila-issue-1-20 --with-vlm
```

Os nomes dos arquivos são exemplos, não afirmam que esses dados existem. Aceita-se um array
JSON de 1–300 candidatos únicos, com ID canônico de onze caracteres e URL canônica correspondente.
`--limit` escolhe os primeiros candidatos na ordem recebida: padrão 20, mínimo 1, máximo 300.
Não seleciona por views. O objetivo de planejamento é chegar a 300 com piso de 200; preparar a
fila não demonstra disponibilidade ou validade de uma base desse tamanho. Expansões para 60 ou
300 exigem outro diretório e revisão dos candidatos; não há expansão automática.

`queue.json` preserva os candidatos e as revisões em campos de curadoria, separados dos atributos
`metadata`, do alvo `target` e de `diagnostics`. Uma fila existente nunca é sobrescrita por
`prepare`. Todos os inputs, referências e outputs audiovisuais ficam dentro de `data/private`,
ignorada pelo Git. Caminhos que escapem dessa área, inclusive por symlink, são rejeitados.

## Revisões necessárias para sair de blocked

Sem ambas as revisões aprovadas, o candidato nasce `blocked`, sem tentativas. Não é suficiente
ter URL pública, `youtube_license`, downloader funcional ou JSON válido do VLM. Registrar em
`curation` estas duas revisões, com responsáveis e evidências reais, somente quando existirem:

```json
{
  "usage_review": {
    "status": "approved",
    "source_status": "verified",
    "reviewer": "identificação de quem revisou as condições da fonte",
    "reviewed_at_utc": "2026-10-17T12:00:00Z",
    "evidence_path": "data/private/revisoes/condicoes-fonte.txt"
  },
  "curation_review": {
    "status": "approved",
    "reviewer": "identificação de quem revisou o recorte",
    "reviewed_at_utc": "2026-10-17T12:00:00Z",
    "evidence_path": "data/private/revisoes/curadoria.txt"
  }
}
```

Este exemplo descreve o formato, não concede autorização. Enquanto pendente, manter `status:
"pending"` e `source_status: "pending"`, ou deixar as revisões ausentes. O preparo calcula SHA-256
dos arquivos referenciados e registra caminho privado, identificação e data da revisão; não imprime
seu conteúdo. Arquivo aprovado ausente/fora da área privada é erro. Na execução, hash alterado
bloqueia o candidato antes do downloader. Revisões novas ou corrigidas exigem candidatos revisados
e uma **nova fila**; um candidato bloqueado não é promovido automaticamente.

## Execução futura, somente após resolver o gate

O comando abaixo documenta o percurso futuro, **não foi executado com mídia real nesta entrega**:

```bash
rtk proxy .venv/bin/python -m scripts.prepare_media_queue run \
  --queue data/private/fila-issue-1-20 --with-vlm \
  --execute --resume --limit 20 --max-seconds 3600
```

Sem `--execute`, `run` apenas inspeciona. A execução exige também `--resume`, usa um worker e
`run_session` já existente, processando um vídeo por vez. Modelos precisam estar preparados
localmente: o carregamento força modo offline e não provisiona pesos pela rede. Mantém os limites
do downloader existente: até 60 s, não live, até 720p, limite declarado de download de 32 MiB e
checagem final de 64 MiB; o extrator exige vídeo vertical. Isso é filtro técnico, não curadoria
científica nem licença.

O orçamento é verificado **entre vídeos**: até 1–300 tentativas por invocação (`--limit`, padrão
20) e tempo positivo finito (`--max-seconds`, padrão 3600). O tempo não interrompe uma etapa em
andamento, portanto não é um limite global rígido. Cada vídeo pode ter no máximo **duas tentativas
no total**, no máximo uma por invocação. Falhas comuns podem ser retomadas; sucessos são pulados
somente após validar hashes de `features.json`/`run.json` e assinatura de configuração/extratores.

Estados: `pending → running → completed/failed`; gate ausente/alterado deixa `blocked`. Os arquivos
ficam em `attempts/<video_id>/<n>/`, sem sobrescrever a tentativa anterior. O checkpoint é atômico,
com modo 0600. Um lock do sistema operacional impede workers simultâneos na mesma fila e é
liberado ao terminar/morrer o processo; o arquivo `.lock` pode permanecer e não deve ser removido
para contornar um worker ativo.

Autenticação/botcheck, HTTP 403/429 ou limpeza não confirmada deixam `halt_reason` persistente e
param também futuras invocações. Não há evasão nem repetição automática desses bloqueios. É
necessário investigar a causa antes de criar outra fila; criar outra fila não autoriza contornar
restrições. `running` encontrado após queda abrupta vira `failed` com parada por limpeza incerta:
não se promete descarte imediato após falha da máquina, e eventuais sessões em `data/private/media-temp`
precisam ser verificadas manualmente. Cancelamentos capturados preservam a tentativa e o estado de
limpeza. `completed` é sucesso técnico, sempre com `training_eligible: false` nesta fila.

Alterar protocolo, candidatos, `--with-vlm`, revisões dos modelos, versões de dependências ou hashes
dos scripts exige outra fila. Artefatos concluídos ausentes/alterados também rejeitam retomada.
A assinatura identifica código/configuração/versões e revisões fixas de modelos; não re-hasheia
todos os pesos locais, portanto presume íntegro o cache previamente preparado. Inspecionar não
valida condições de uso nem reavalia conteúdo da evidência.

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

A suíte usa API/downloader/extrator sintéticos: orçamento, erro de rede, retomada, deduplicação,
incompatibilidade de protocolo/configuração, hashes, falha parcial, limpeza incerta, cancelamento,
limite de tentativas, trava, gates e modo de inspeção. Não demonstra rendimento em 300 vídeos,
disponibilidade real, adequação jurídica da fonte ou validade preditiva.

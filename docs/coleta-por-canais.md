# Coleta limitada de metadados por links de canais

O comando legado descrito abaixo foi preservado. O novo modo explícito com checkpoints,
retomada e cobertura por canal está em [retomada-coleta.md](retomada-coleta.md), junto da
fila audiovisual separada. Preparar a fila não aprova fonte ou elegibilidade de treino.

Data: 17/10/2026. Parte da [issue #1](https://github.com/leeunam/Galaxies-Inteli-Academy/issues/1).

`scripts/collect_channel_metadata.py` aceita URLs `https://www.youtube.com/@handle`,
`/channel/UC...` e `/user/...`. Resolve a referência com `channels.list`, obtém a playlist
de uploads, percorre páginas com `playlistItems.list` e consulta detalhes por `videos.list`
em lotes de até cinquenta IDs. Não baixa mídia nem solicita tags.

O teste real usou dois links da amostra, uma página por canal, e retornou cem registros
em seis chamadas. Ambos os canais tinham outras páginas: a cobertura é parcial. São
metadados de descoberta, sem partições de treino ou elegibilidade audiovisual demonstrada.
O resultado privado é `data/raw/youtube-channels/20261017-probe.json`.

Os registros separam `audit` (canal, publicação, coleta e referência), `target` (views),
`diagnostics` (likes), `curation` (título e campos declarados) e `metadata` (duração).
Ausência de curtida fica nula, não zero. Canal e datas ficam somente em auditoria;
o treino deve selecionar explicitamente suas entradas e não consumir o registro completo.
Título auxilia curadoria; não substitui a transcrição do desenho A/B/C.

Para repetir, executar o script com as URLs escolhidas e os argumentos:

- `--output data/raw/youtube-channels/nova-coleta.json`: caminho local novo.
- `--pages-per-channel 1`: até cinco páginas por canal; padrão uma.
- `--max-api-calls 30`: orçamento de chamadas; padrão trinta.

Requer Python 3.11 e `YOUTUBE_API_KEY` no ambiente ou no `.env` local. A chave é enviada
em cabeçalho HTTPS, sem integrar URLs ou saídas. O coletor recusa destinos fora de
`data/private`/`data/raw` e rejeita saídas existentes antes de ler a chave ou consultar a API.
Não imprimir a chave nem passá-la na linha de comando.

Quatro testes locais verificam rejeição de referências fora do YouTube, separação dos
campos/valores ausentes, paginação parcial e vídeos indisponíveis, além da rejeição de um
destino existente sem consumir cota. É um primeiro coletor com limites, não um sistema
de aquisição em escala com recuperação automática de qualquer falha. Duração curta,
idioma declarado e localização de acesso não confirmam por si só Shorts em pt-BR.

O [piloto audiovisual separado](piloto-extracao-temporaria.md) testa acesso a uma cópia
licenciada, extração e descarte; a API não fornece o arquivo para essa etapa.
Em seguida, o [piloto real do YouTube](piloto-youtube-real.md) validou aquisição temporária
por yt-dlp e extração em três candidatos encontrados pela API.

Referências: [channels.list](https://developers.google.com/youtube/data/reference/rest/v3/channels/list),
[playlistItems.list](https://developers.google.com/youtube/data/reference/rest/v3/playlistItems/list)
e [videos.list](https://developers.google.com/youtube/data/reference/rest/v3/videos/list).


## Ampliação por uploads e datas de publicação — 18/10/2026

A retomada reutiliza o percurso oficial `channels.list` → uploads →
`playlistItems.list` → `videos.list`. O acesso aos uploads respondeu normalmente
após uma busca adicional por palavra-chave falhar. Essa falha não comprovou
revogação da chave nem bloqueio de todos os métodos; nenhuma busca foi repetida.

A [tabela oficial de cotas](https://developers.google.com/youtube/data/determine_quota_cost?hl=en),
conferida em 18/10, documenta um bucket próprio de cem chamadas diárias para
`search.list` e dez mil unidades combinadas para os demais métodos, por padrão.
A configuração efetiva do projeto não foi inferida desses valores. O percurso de
uploads é [documentado pelo YouTube](https://developers.google.com/youtube/data/reference/rest/v3/playlistItems/list?hl=en);
as chamadas permanecem autenticadas normalmente e respeitam os limites/erros da API.

A função Python `collect` aceita `publication_window=(inicio, fim)`, com início
exclusivo/fim inclusivo e datas com fuso. Ela usa `contentDetails.videoPublishedAt`,
que é a publicação do vídeo; a inclusão na playlist não substitui essa data.
Confere novamente a data em `videos.list`. Datas ausentes, sem fuso ou fora da
janela são registradas/separadas, sem preencher valores. A idade na observação
real da contagem ainda precisa passar pelo validador da coorte.

`existing_video_ids` evita solicitar novamente os outcomes de IDs congelados.
Ausência na resposta e incompatibilidade de data têm relatórios distintos.
A paginação continua limitada a uma a cinco páginas por canal, com cobertura
parcial explícita quando há próxima página; encontrar uma página antiga não
prova que todas as posteriores sejam antigas. A chamada não cria partições,
extrai mídia, confirma idioma/setor ou libera treino.

O lote de ampliação registra privadamente sementes, configuração, código e
respostas/hash de cada chamada. Inclui canais com conteúdo já curado e novas
propostas por metadados, sem ordenar por views. Novas observações não substituem
as anteriores; toda candidata ainda depende de curadoria audiovisual.

Verificação: 250 testes integrados passaram. Os novos controles cobrem a data de
publicação, bordas/fusos da janela, paginação, preservação de outcomes congelados,
datas divergentes na resposta final e parada em erro sem retentativa.

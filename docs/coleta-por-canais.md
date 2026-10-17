# Coleta limitada de metadados por links de canais

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

Referências: [channels.list](https://developers.google.com/youtube/data/reference/rest/v3/channels/list),
[playlistItems.list](https://developers.google.com/youtube/data/reference/rest/v3/playlistItems/list)
e [videos.list](https://developers.google.com/youtube/data/reference/rest/v3/videos/list).

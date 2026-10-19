# Aditivo de descoberta por setor e hashtags

Registrado em 19/10/2026, antes das novas buscas. O aluno manteve a exigência de
300 referências e pediu outras abordagens, incluindo tags/Shorts e filtros pelos
dois setores. A coleta ampla encontrou muitos itens fora do recorte; nenhum
modelo ampliado foi ajustado nem resultado de views usado para essa adaptação.

## Mudança autorizada

Usar os vídeos retornados diretamente por buscas temáticas, em vez de expandir
toda a playlist dos canais encontrados. O filtro nativo `topicId` será
`/m/032tl` (Fashion) ou `/m/041xxh` (Beauty). As consultas fixas, em alternância,
são: `#modafeminina #shorts`, `#maquiagem #shorts`, `#lookdodia #shorts`,
`#skincare #shorts`, `provador roupas`, `perfume cosmético`, `moda masculina`,
`cuidados cabelo`.

Ordem por data, mesma janela congelada, região BR e relevância de idioma pt.
A API pode retornar outros idiomas. `videoDuration=short` significa menos de
quatro minutos, não comprova Shorts ou o nosso recorte. O termo com hashtag é
uma consulta textual, não comprova que o vídeo contém a tag. Idioma, setor,
verticalidade e duração até60s continuam exigindo evidência real.
[Contrato oficial de busca e tópicos](https://developers.google.com/youtube/data/reference/rest/v3/search/list).

O limite de buscas passa de20 para28 tentativas acumuladas, dentro das mesmas
300 chamadas totais de metadados. Tentativas falhas continuam consumindo o
orçamento. Mídia permanece limitada a300 tentativas e90min nesta rodada; nenhum
critério de inclusão, alvo, extrator, modelo ou métrica foi relaxado.

## Preservação e nova ordem

Excluir os80 canais antigos e todos os IDs já observados antes de solicitar
estatísticas. Novos canais recebem o mesmo hash75/25 antes das estatísticas;
nenhuma atribuição existente muda. Não atualizar rótulos/instantes de IDs antigos.
Não usar views, popularidade ou curtidas na seleção.

Ao terminar o lote corrente e suas revisões, congelar uma versão filha da fila:
prefixo dos itens já tentados, depois candidatos novos das buscas temáticas em
hash/rodízio, depois candidatos amplos ainda não tentados na ordem anterior.
Arquivar integralmente a fila anterior e registrar hashes de origem/aditivo e
migração. Exigir igualdade de cada observação já tentada antes de atualizar o
checkpoint de seleção. A alteração é de descoberta por domínio, não otimização
pela qualidade preditiva. A amostra permanece de conveniência adaptativa.

Conservar 50 inclusões por setor e cinco/canal,200 registros originais e teste
31/16 intocados. Apenas após completar e validar as100 inclusões novas, publicar
B0 e retreinar A com a receita original. Comparar antes de iniciar B, conforme o
protocolo principal; não publicar uma base menor como se cumprisse a meta.

# Aditivo: vídeos diretos das buscas de domínio já salvas

Registrado em 19/10/2026 antes das estatísticas desta via. O aluno confirmou
manter 300 referências e autorizou novas abordagens de descoberta por setor.
A via de hashtags/tópicos encontrou muitos vídeos sem fala pt suficiente.
As dezesseis buscas originais por termos de moda/beleza também contêm IDs de
vídeos ainda não observados: a descoberta anterior ampliava playlists de somente
80 canais, em vez de aproveitar diretamente todos esses resultados.

Reutilizar somente as respostas dessas dezesseis consultas fixas, sem nova
busca, paginação, termos adicionais ou ordenação por engajamento. Excluir todos
os IDs já observados, os controles e os 80 canais da coorte antiga **antes** de
pedir estatísticas. Congelar a alocação hash dos canais novos primeiro; manter
todas as atribuições anteriores. Observar os vídeos restantes uma única vez,
com idade real de 30 <= dias < 37, na janela de publicação original.

Os títulos, idioma declarado, views e curtidas não priorizam a fila. Aplicar
o mesmo hash/rodízio entre canais. As consultas são propostas de domínio;
continuam obrigatórias a revisão real de frames/fala e todas as exclusões.
Não relaxar português, setor, verticalidade, duração ou duplicatas.

Depois de concluir o lote em execução e sua curadoria, migrar para uma nova
fila filha: tentativas anteriores intactas, novos candidatos desta via e depois
os candidatos ainda não tentados. Usar arquivo próprio de ascendência, journal,
backup e recibo, com a mesma retomada idempotente da migração anterior.

Não aumentar os orçamentos acumulados: 300 tentativas de metadados (até 28
buscas), 300 tentativas de mídia e 90 minutos de aquisição/extração. Os IDs
recuperados do cache não consomem novas buscas; suas consultas de detalhes
consomem o saldo normal. Nenhum modelo ampliado foi ajustado. A meta permanece
100 inclusões novas, 50 por setor, antes de B0/A; teste e experimento B fechados.

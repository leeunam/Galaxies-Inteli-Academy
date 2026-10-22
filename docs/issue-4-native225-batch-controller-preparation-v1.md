# Controlador nativo de lote — preparação offline

Base `fb3950850fc49ad6d0eaec409c594563e3a772ca`. Esta unidade conclui a ligação
técnica prevista na [preparação anterior](issue-4-native225-adapter-preparation-v1.md),
sem alterar a [proposta ainda inativa](issue-4-native225-next-validation-v1.md).
O [recibo sanitizado](evidence/issue-4-native225-batch-controller-preparation-v1.json)
registra hashes, limites e a seleção de testes. Nenhuma aprovação ou execução real
foi criada; o acerto anterior continua sendo um único negativo revelado.

## Entrega desta unidade

O [controlador](../scripts/visual_validation_batch_v1.py) implementa a rota nativa,
mas mantém `NATIVE_DISPATCH_RELEASED=False`. O despacho público e a CLI recusam
execução antes de ler a configuração ou criar a fila. Mesmo após uma futura
ativação revisada, a CLI só aceita os dois caminhos de configuração previstos.
Não há gerador de aprovação nem preenchimento automático de rótulos.

A configuração vincula a proposta, o candidato, a raiz, as fontes e os ativos,
a geometria, os jobs e o prazo de uso de cada imagem. Os envelopes de autorização
e revisão aceitam apenas metadados; labels e outcomes são recusados. O recibo
humano e a revisão técnica são distintos, exclusivos e vinculados por digest.
Fontes, identidade dos inputs, leases, memória e ausência de workers são conferidas
antes da reserva e novamente antes do processo. As sete fontes da preparação
anterior e as 14 fontes congeladas da proposta permanecem intactas.

Um lock exclusivo e o ledger global durável limitam a proposta a 397 chamadas,
sendo 13 de desenvolvimento e até 384 de auditoria, até 32 aquisições e 39.600
segundos totais. A reserva precede o lançamento. Estado pendente ou captura não
contabilizada bloqueia avanço; falha técnica, resposta inválida ou erro nos
controles encerra a sequência sem retry. Os reducers contabilizam aquisições,
mas esta unidade **não adiciona um downloader nem executa a fase de rede**.
A futura aquisição deve entrar no mesmo ledger, sem fila paralela.

A captura reutiliza o único owner existente. Há até 75 segundos úteis, cinco
reservados para encerramento e 80 por despacho; a revisão exige watchdog externo
verificado para cobrir também a cápsula/preflight. Não foi entregue um novo daemon
supervisor. A cápsula corrigida verifica rede isolada e `/dev/null` por um processo
inofensivo. O mínimo é 6 GiB disponíveis; o corte RSS de 3,3 GiB é cooperativo,
com as limitações de amostragem anteriores, sem promessa de cgroup ou teto físico.

A auditoria exige desenvolvimento aprovado, seleção de treino e revisão das
exclusões. O executor recebe apenas o compromisso sem rótulos. Um teste coloca
um arquivo de ground truth inválido como armadilha e completa a auditoria
inventada sem abri-lo. Compromisso e selos não certificam por si a independência
do anotador: papéis, origem e revisão continuam precisando de verificação.

O [sidecar do lote](../scripts/visual_validation_batch_sidecar_v1.py) confere os
recibos de despacho, candidato, mídia, tempos e hashes de todos os frames.
Distingue dados sintéticos de observados; filhos inventados nunca recebem
`native_execution_verified=true`. Execução observada também não é aprovação
perceptiva: `approved_for_training=false`, sem QualityRelease ou promoção a B/C.

## Geometria e testes efetivamente executados

Foi compilada apenas a função aritmética já preservada do pré-processador,
com cabeçalhos stdlib, sem bibliotecas do modelo, pesos, encoder ou pixels reais.
Com native225, a previsão é 240 tokens nos dois formatos: 320×330 resulta em
canvas 480×512 e 360×640 em 384×640. Isso é prova aritmética; não é contagem
observada de um novo encoder nem medição de qualidade.

Passaram **63 testes em 3,58 s**: 26 do novo controlador e os 37 anteriores,
sem falhas, erros ou skips. Ruff e formatação passaram nos três arquivos novos.
Os testes usam PNGs inventados e pequenos filhos Python, sequencialmente.
Cobrem autorização/revisão/raiz/fontes/ativos, leases, queda de memória antes
do spawn, contador corrompido, envelopes com labels, limites globais, reserva
incerta, falha de spawn, interrupção real de um filho falso, limpeza, parada
perceptiva, compromisso cego e sidecar sem promoção. Os limites de 397/32 e
de tempo são exercitados em reducers puros, sem centenas de processos.

As seleções intermediárias de 19, 60 e 62 testes ficam nos recibos privados;
são sobrepostas e não devem ser somadas. A passagem final corrige dois avisos
de lint antes do pytest. A inspeção CLI retornou `inactive`, zero chamadas e
zero aquisições reservadas, saída 0. Uma tentativa bloqueada pela CLI retornou
saída 2 antes de abrir configuração, sem criação do namespace real.

## Pendências antes de qualquer lote

Não foi produzida a projeção real dos 203 exemplos. A leitura de código e a
busca limitada por nomes/metadados não identificaram uma fonte confirmada com
apenas treino, canais e identidades de mídia/frames. Os caminhos examinados
misturam partições/outcomes ou omitem canal. Nenhum arquivo misto foi aberto
para depois remover campos, e isso não prova inexistência de outra fonte segura.
É necessário obter a projeção a montante e revisar as exclusões completas antes
da seleção. O usuário não precisa fornecer 32 vídeos novos por causa desta etapa.

Continuam faltando a autorização consolidada, renovações de uso aplicáveis,
seleção real, suficiência de canais, imagens autorizadas, anotações cegas e
revisão independente. O protocolo permite assistência onde prevista; esta
unidade não inventa exigência humana geral. Se `human_required` for aplicável,
a preparação anterior continua recusando origem sintética ou assistida.

Depois devem ser congeladas a configuração real, os prazos, as provas dos
ativos/raiz/fontes e a revisão operacional do watchdog. Os testes não ativam
a constante nem liberam o lote. Sem novas inferências, aquisições, POST NIM,
treino real ou holdout nesta unidade. Base, M1, imagens e recibos anteriores
permanecem protegidos; qualidade visual, B/C real e avaliação final continuam
pendentes. Não há declaração de aceite integral.

# Nativa 225: falha operacional antes do modelo

A única tentativa autorizada foi reservada em 22/10/2026 às 02:29:05 UTC no
código `477aa09`. Havia 11,37 GiB disponíveis. O controlador encerrou em
1,91 s; a captura durou 0,020 s e registrou `PermissionError`,
`process_started=false`, nenhuma resposta, nenhum token e limpeza confirmada.
A fila está selada, com uma reserva consumida e saldo zero. Não houve repetição.

## Causa demonstrada no invólucro do operador

A cápsula foi lançada com `--ro-bind / /`, sem o `/dev` efêmero. Nesse ambiente,
abrir `/dev/null` retorna `EACCES`. O coletor usa `stdin=subprocess.DEVNULL`,
portanto essa configuração impede o início do filho antes de executar o modelo.
Essa falha do lançamento não informa tempo ou qualidade do encoder.

Um teste local sem modelo reproduziu o bloqueio com `/usr/bin/true`: `DEVNULL`
falhou, enquanto `PIPE` terminou com código 0. Com a única adição
`bwrap --dev /dev`, leitura/escrita de `/dev/null` e os dois filhos inofensivos
terminaram normalmente. Nenhuma permissão ou configuração do host foi alterada.

A receita operacional corrigida inclui `--dev /dev` e exige o teste inofensivo
de `DEVNULL` antes de reservar qualquer execução futura. A cápsula continua
sem rede e com o host somente leitura; apenas o diretório privado da operação
pode receber resultados. O produto, o parser, a autoridade numérica, os pesos
e as nove fontes pinadas desta tentativa não foram alterados.

## Limites do resultado e próximo passo

Não há observação de 240 tokens, resposta `no`, término do encoder ou melhora
perceptiva. A hipótese de 960 patches permanece sem teste. Esta fila não será
reaberta, mesmo sem início do modelo. Uma nova execução exige autorização
específica e nova vinculação técnica; deve conservar os limites do
[protocolo preparado](issue-4-vlm-native225-probe-preparation-v1.md). O PNG
continua vencendo em 22/10/2026 às 02:59 UTC; este relatório não estende retenção.

M1, base 300, holdout, oito PNGs protegidos e recibos anteriores permanecem
fora desta alteração. Não houve POST NVIDIA, download, treinamento ou publicação.
O [recibo agregado](evidence/issue-4-vlm-native225-execution-result-v1.json)
registra os hashes dos recibos privados originais e a reprodução sem modelo.

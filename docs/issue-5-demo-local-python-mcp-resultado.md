# Demo real local — Python e MCP disponíveis, igualdade integral pendente

As mesmas três mídias recuperadas produziram **três estimativas reais em Python
e três em MCP**, com passagem nativa de features, StateGraph, subgrafo
explicativo e pacote de evidências. O MCP corrigido completou a análise, mas
**não passou na igualdade integral** com o resultado Python salvo. O operador
encerrou sem repetir a rota nem criar o resumo/passagem final condicionados
a esse requisito.

O [recibo agregado](evidence/issue-5-demo-local-python-mcp-20261020.json)
registra resultados, diferenças e limites sem identidades, URLs ou caminhos
privados. Este documento sucede o
[resultado da primeira execução](issue-5-recuperacao-demo-resultado.md) e a
[revisão do reparo mínimo](issue-5-reparo-mcp-demo.md), que permanecem intactos
como histórico.

## Resultado observado

| Item | Evidência |
| --- | --- |
| Entradas | Mesmos três arquivos, pedido e configuração; hashes reconferidos |
| Python original | Uma análise completa; três `estimated`; resultado preservado |
| MCP suplementar | Uma chamada de análise completa; três `estimated`; 56,433 s |
| Transporte | Ferramentas esperadas listadas e chamada única reservada em recibos |
| Comparação | 22 campos diferentes; duas das três estimativas diferem |
| Maior diferença absoluta das estimativas | 56,292847557117966 na unidade de visualizações |
| Ordem do ranking | Igual nas duas respostas |
| Pacote explicativo | Presente nas duas; conteúdo e hashes não idênticos |
| Saída do operador | Exitcode 1; causa concreta `native_python_mcp_mismatch` |
| Passagem v3 | Não executada; resumo de sucesso não criado |

As diferenças abrangem valores de previsão, limites de intervalo, valores do
ranking, afirmações do pacote e seus hashes derivados. A causa numérica não
foi estabelecida; não se presume arredondamento, instabilidade ou erro de
transporte. Não foi acrescentada tolerância, relaxado gate ou repetida
inferência para obter um resultado conveniente.

## Operação limitada e preservação

A liberação suplementar efetiva ficou vinculada ao protocolo v2 SHA256
`6b53fc0966d3672e93445169a0816b1b6265878f74d7d532ecd86983212d7241`,
ao operador privado SHA256
`bfdd371b02932fb75cf7511391bfdd488bfdb234c590eaea1839d44f03fcb934`
e ao worker MCP SHA256
`c5772e9b5f10b949eb105e7a7ca30a550998773637c657b2434d5e46cc5a3713`.
A origem literal e o identificador real da liberação constam em recibo privado
exclusivo. A política original e os seis pins de código permaneceram iguais.

O novo marcador foi consumido antes do comando. O filho completou com
exitcode 0, 14.301 bytes de stdout e zero de stderr; a falha foi a comparação
posterior do operador. O maior RSS amostrado foi 2.536.157.184 bytes e a maior
ocupação amostrada do workspace foi 11.110.257 bytes. Ambos ficaram abaixo
dos tetos autorizados; as amostras são de 50 ms, sem promessa de cota rígida
instantânea. A rede permaneceu isolada e o supervisor confirmou recolhimento.

Os oito arquivos anteriores vinculados ao protocolo, inclusive resultado Python,
pedido, cadastro e histórico da falha inicial, foram reconferidos sem mudança.
O resultado MCP e o recibo de parada foram adicionados separadamente. Scratch
foi limpo somente após quiescência confirmada. Os três inputs foram preservados
e reconferidos, com retenção autorizada até **21/10/2026 às 23h59, São Paulo**;
nenhuma exclusão automática foi programada.

Não houve nova aquisição, repetição Python, segunda chamada MCP corrigida,
VLM/NIM, treino, instalação ou escrita na árvore principal. O primeiro defeito
de transporte foi confirmado sem ML e corrigido somente no worker suplementar.
As duas análises completas usam os mesmos gates congelados; o seletor externo
permanece ausente, `real_provider_verified=false` e aderência `not_evaluated`.

## Limite da entrega atual

Há arquivos reais, pedido/cadastro e respostas completas de ambas as entradas
para revisão e demonstração técnica. A igualdade integral exigida para a
passagem continua reprovada. Não foi criado `analysis-summary.json`, não foi
emitido recibo de handoff e nenhuma issue ou conclusão científica foi declarada
encerrada. A continuidade exige decidir tecnicamente a divergência observada,
preservando estes resultados; esta unidade não iniciou outra análise.

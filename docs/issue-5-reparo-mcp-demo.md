# Demo recuperada — correção mínima do transporte MCP

A falha de transporte foi confirmada em um servidor mínimo sem mídia, modelos
ou chamadas de análise. `log_file=os.devnull` entrega uma string ao FastMCP;
a versão instalada espera `Path` ou `TextIO` e tenta usar a string como stream.
O caso reproduziu `AttributeError` referente a `fileno`, antes de iniciar o
servidor. Com `Path(os.devnull)`, conectou e listou as ferramentas do servidor
mínimo vazio. O [recibo de revisão](evidence/issue-5-reparo-mcp-demo-20261020.json)
preserva o resultado sanitizado e os hashes.

A primeira asserção do diagnóstico não percorria a cadeia de causas da
exceção e foi corrigida no próprio probe; a segunda execução mínima passou.
Não foi repetida nenhuma inferência. Uma tentativa inicial de usar a cápsula
aninhada no contexto padrão falhou na criação do namespace antes de criar
lease/filho; não foi inventada confirmação de recolhimento para ela. O probe
direto Bubblewrap com rede isolada funcionou. Esse detalhe do contexto deve
ser considerado na execução técnica suplementar.

O [resultado Python anterior](issue-5-recuperacao-demo-resultado.md) permanece
preservado: três estimativas, pacote de evidências e passagem nativa. A rota
MCP anterior não guardava marcadores de listagem/chamada nem a exceção bruta.
O defeito confirmado no mesmo tipo/parâmetro/versão ocorre antes do spawn;
não existe evidência de uma análise MCP concluída naquela execução.

## Mudança aditiva

O novo [worker exclusivo MCP](../scripts/demo_recovery_mcp_only.py) mantém os
argumentos do servidor e as configurações nativas originais. Corrige o tipo
do log e acrescenta recibos exclusivos para ferramentas listadas e chamada
reservada. Só oferece a rota MCP; não contém aquisição ou análise Python
direta. Os cinco arquivos selados do invólucro v3 não foram alterados.

O operador suplementar é um script privado fixo, que reutiliza o supervisor
já verificado. Seu protocolo fixa hashes do pedido, cadastro, configuração,
manifesto de entradas, resultado Python e recibos da execução encerrada.
Confere novamente os bytes antes de operar. Exige uma liberação suplementar
vinculada aos seis pins de código, ao hash do operador e ao protocolo novo.
O template atual não habilita nenhuma fase.

Após revisão, autoriza **uma única chamada MCP corrigida**, até 480 s, com
rede isolada, RSS amostrado até 3,5 GiB, workspace até 384 MiB, arquivo até
32 MiB e stdout/stderr até 64 KiB cada. Mantém quatro threads do extrator
congelado, sem VLM, treino, instalação, provedor externo ou mudança de gates.
Usa os mesmos três arquivos e o mesmo pedido; não refaz Python nem download.

Um marcador suplementar novo é consumido antes do processo. Os marcadores
antigos permanecem inalterados. A resposta integral é comparada com o JSON
Python salvo; uma falha ou divergência encerra sem repetição. Scratch só é
removido após confirmação de recolhimento; entradas permanecem até o prazo
autorizado de 21/10/2026 às 23h59, São Paulo. Nenhuma limpeza automática foi
programada.

## Revisão preparada

| Item | SHA256 |
| --- | --- |
| Worker aditivo | `c5772e9b5f10b949eb105e7a7ca30a550998773637c657b2434d5e46cc5a3713` |
| Operador privado v2 | `bfdd371b02932fb75cf7511391bfdd488bfdb234c590eaea1839d44f03fcb934` |
| Protocolo suplementar v2 | `6b53fc0966d3672e93445169a0816b1b6265878f74d7d532ecd86983212d7241` |

A revisão encontrou um bloqueador no primeiro operador: ele tentava reservar
uma fase suplementar pela política v3, que só aceita as quatro fases originais.
O operador v2 usa diretamente `exclusive_json` no novo marcador, antes do
despacho, sem alterar a política. Após igualdade integral, também grava
`analysis-summary.json` por criação exclusiva, apontando o resultado suplementar
e o histórico da falha original. Isso permite a passagem v3 ler um resumo real.
Operador/plano/recibos v1 permanecem preservados; o
[recibo aditivo v2](evidence/issue-5-reparo-mcp-demo-v2-20261020.json)
registra os novos hashes e a inspeção aprovada, sem inferência.

Ruff e formatação passaram nos dois arquivos. A conferência dos argumentos
confirmou igualdade com a rota MCP anterior. A inspeção real passou com seis
pins verificados. A chamada sem liberação foi recusada antes de criar marcador
ou diretório de progresso. O protocolo suplementar está preparado para revisão;
**nenhuma análise MCP corrigida foi iniciada**. Não houve escrita principal,
nova suíte completa, download ou repetição do resultado Python.

# Recuperação real da demo — resultado da execução única

As três fontes fixas de beleza foram recuperadas, cadastradas e processadas
pela entrada Python real. M1 retornou `m1_prediction_available`, com três
estimativas, passagem nativa de features, StateGraph, subgrafo explicativo e
pacote de evidências. A entrada MCP falhou antes de concluir o percurso;
**a paridade Python/MCP e a passagem final não estão concluídas**.

Este resultado sucede o [candidato para revisão](issue-5-recuperacao-demo-wrapper.md),
que permanece como registro anterior à execução. O
[recibo agregado](evidence/issue-5-recuperacao-demo-resultado-20261020.json)
registra os resultados sem expor identidades, URLs ou caminhos privados.

## Execução e ponto de parada

O código revisado foi o commit `20ec8c50d208637e3a23f80933aaa11b2de5f919`,
vinculado ao protocolo SHA256
`4bc0bffbeafdb6959c2db4556a2b3573cd7a83791db057ac5c2c5089c39fb773`.
A liberação técnica efetiva, sua origem literal verificável, os cinco pins
de código e a referência aos 17 checks prévios ficaram em recibos privados
exclusivos. Os cinco arquivos de operação permaneceram inalterados.

| Etapa | Resultado observado |
| --- | --- |
| Aquisição | Exitcode 0; três reservas e três arquivos distintos; 5.334.186 bytes totais |
| Formato | Três remuxes por cópia; sem reencodificação ou troca de fonte |
| Cadastro | Três entradas aceitas; duração medida compatível com o registro histórico |
| Python nativo | Completou em 55,409 s; três estimativas e pacote de evidências |
| MCP | Filho terminou em 2,522 s; devolveu somente `native_stage_failed` |
| Análise conjunta | Exitcode 1, `stopped_do_not_repeat`; comparação não executada |
| Passagem/descarte | Não executados; entradas preservadas |

A etapa MCP emitiu 41 bytes de stdout e zero de stderr; a exceção foi suprimida
pelo invólucro. A leitura estática identifica uma causa provável: o invólucro
passa `log_file=os.devnull` como string ao `StdioTransport`, enquanto a versão
instalada aceita `Path` ou stream `TextIO` e trata outros objetos como stream.
Essa hipótese não foi confirmada por nova execução. Não houve correção dos
pins durante a operação, repetição, reentrada ou nova aquisição.

## Entradas e continuidade

Os três arquivos estão no diretório privado ignorado de uma execução nova no
clone isolado. Seus hashes foram conferidos novamente após a parada. O pedido,
cadastro e resultado Python também estão preservados para uma continuidade
revisada que reutilize os arquivos; não é necessário adquirir novas fontes.

A retenção autorizada termina em **21/10/2026 às 23h59, São Paulo**.
Preparar ou entregar resultados não equivale à conclusão da apresentação.
Descarte antecipado exige confirmação real de uso concluído conforme o
protocolo; não foi programada automação de exclusão.

Todos os nove jobs registraram recolhimento confirmado. O scratch foi removido
após essa conferência; os inputs ficam fora dessa fronteira. O maior RSS
amostrado foi 2.306.330.624 bytes, abaixo do teto de 3,5 GiB; a maior ocupação
amostrada do workspace foi 11.085.824 bytes. As amostras são de 50 ms e não
constituem cotas instantâneas rígidas.

Não houve chamada VLM/NIM, treino, instalação, mudança de fonte, acesso novo
ao holdout ou escrita na árvore principal. A análise usou a cápsula sem rede
e os artefatos originais somente para leitura. O seletor externo segue ausente,
`real_provider_verified=false` e aderência `not_evaluated`. O resultado não
representa conclusão científica nem encerramento de issue.

## Verificação desta unidade

Foram conferidos os recibos reais das fases, o recolhimento dos nove jobs,
os hashes dos inputs preservados, os cinco pins de código e a integridade
do recibo agregado. As suítes e as inferências não foram repetidas.

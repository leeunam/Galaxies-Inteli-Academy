# Par nativo do trio — divergência não reproduzida

Os dois lotes frios do trio original concluíram com **seis extrações e seis
chamadas nativas ao bundle M1**. Nas três posições, todas as 12 famílias de
digests foram iguais entre os lotes: 36 comparações iguais. Os três conjuntos
q10/q50/q90 também coincidiram, com diferença máxima zero. Nenhuma primeira
família divergente foi observada neste par.

A comparação offline dos objetos M1 já salvos confirmou igualdade integral
entre os dois lotes novos e o campo `analysis` do MCP histórico; ambos diferem
da análise Python histórica. É um alinhamento observado, sem determinar causa,
superioridade de uma fonte ou correção da falha. O relatório Python original
permanece como fonte da consulta canônica, e os dois resultados antigos foram
preservados integralmente.

O [recibo agregado](evidence/issue-5-par-trio-corrigido-resultados-20261020.json)
registra contagens e guardas sem textos, vetores, digests de conteúdo, IDs,
previsões individuais ou caminhos privados.

| Verificação | Resultado |
| --- | --- |
| Arquivo, áudio e propriedades | Iguais nas três posições |
| Transcrição, segmentos, idioma e probabilidades ASR | Iguais nas três posições |
| Embedding, PredictorInputs e CandidateFeatures | Iguais nas três posições |
| Features e previsão nativas | Seis `completed`, seis `estimated`; sem previsão auxiliar |
| Duração do operador corrigido | 105,648 s, dentro dos 450 s globais |
| Jobs | Dois concluídos em 49,991 s e 55,534 s; recolhimento confirmado |
| Maior RSS/workspace amostrados | 2.101.465.088 bytes / 5.749.699 bytes |
| Encerramento | Zero workers próprios; scratch novo removido |

Cada processo de lote carregou seu bundle uma vez, antes da extração, e
percorreu os três candidatos na ordem original. O analisador M1, o handoff,
o cache por invocação e os gates nativos foram preservados. As previsões
usaram os próprios inputs capturados em cada lote, sem substituições ou
chamadas adicionais para comparar vetores iguais. Os retornos observados
conferiram com os inputs efetivamente previstos pelo analisador.

O observador acrescentou somente leitura de retornos/chamadas, mantendo o
hash do áudio já produzido nativamente. A máscara herdada de 12 CPUs foi
registrada antes/depois, sem alteração de afinidade. Extratores conservaram
quatro threads configuradas e o CatBoost, `thread_count=-1`. Os limites de
3,5 GiB de RSS e 384 MiB de workspace foram monitorados a cada 50 ms; não são
cotas instantâneas rígidas. Mantiveram-se 32 MiB por arquivo, 64 KiB por saída,
180 s por lote limitados pelo saldo global e rede isolada.

A [falha operacional anterior](issue-5-par-trio-parada-operacional.md) permanece
registrada: zero extrações e zero bundles antes de corrigir a constante
`DEVNULL` no proxy privado. Helper, plano, marcadores e run falhos ficaram
intactos. O helper corrigido e um protocolo novo receberam liberação própria,
vinculada à prova de zero chamadas. Os totais entre as duas tentativas são
seis extrações e seis bundles, sem reabrir a autorização terminal anterior.

O helper corrigido tem SHA256
`0daabe8542aa90801a78f54eee38831dcbb45051a9092cda33440819230114f7`;
o protocolo, SHA256
`a568d1865ab314f00a87429559b364e62e2dbd04c26d43d8da35ccbb29acb93e`.
Origem literal e identificador real da liberação estão em recibo privado.
A autorização corrigida foi consumida e encerrada, sem nova rodada preparada.

Fontes, artefatos e relatórios anteriores permanecem preservados. Os três
inputs foram reconferidos; manifesto canônico e passagem privada `0600`
continuam iguais. Só derivados novos foram removidos após quiescência. A
retenção continua até **21/10/2026 às 23h59, São Paulo**, sem exclusão automática
ou declaração de apresentação concluída.

Foram zero aquisições, chamadas remotas/NIM/VLM, treino, acesso a conteúdo do
teste reservado, instalações ou escritas na árvore principal. Não houve
suíte ampla ou inferência fora do par aprovado.

**A divergência histórica continua aberta e sua causa permanece desconhecida.**
O perfilador acrescenta overhead; este ensaio reproduz o contexto numérico
nativo M1 do trio, sem executar novamente o grafo, SHAP ou transporte MCP.
Não isola efeitos de CPU versus lote e não recupera os vetores históricos
ausentes. Consistência neste par não aprova paridade Python/MCP independente
nem elimina os [dois resultados anteriores](issue-5-demo-local-python-mcp-resultado.md).
O [guia de consulta canônica](issue-5-consulta-canonica-demo.md) permanece
disponível e independente deste diagnóstico.

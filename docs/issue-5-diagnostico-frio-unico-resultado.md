# Diagnóstico frio único — divergência não reproduzida

Duas capturas frias de um candidato já recuperado tiveram digests iguais em
**todas as nove famílias observadas**. Duas chamadas nativas ao bundle q10/q50/q90
sobre o mesmo vetor também foram iguais, com diferença máxima zero. Nenhuma
primeira família divergente foi observada neste ensaio.

O [recibo agregado](evidence/issue-5-diagnostico-frio-unico-20261020.json)
registra consumo, limites e verificações, sem transcrições, vetores, digests de
texto, identidades, previsões individuais ou caminhos privados.

| Verificação | Resultado |
| --- | --- |
| Arquivo/áudio decodificado/propriedades do áudio | Digests iguais |
| Transcrição/segmentos/idioma ASR | Digests iguais |
| Embedding/PredictorInputs/CandidateFeatures | Digests iguais |
| Duas chamadas ao bundle sobre o mesmo vetor | q10/q50/q90 iguais |
| Consumo | Duas capturas e duas chamadas lógicas ao bundle; cerca de 40 s |
| Recolhimento | Quatro jobs concluídos; limpeza confirmada; zero workers próprios |

O worker e as funções de extração originais foram preservados, com um item,
configuração e pasta por setor nativos. `sys.setprofile` leu somente retornos;
o hash nativo do áudio foi reutilizado sem decodificação adicional. Tempos de
execução, caminhos e IDs de processo não participaram dos digests comparativos.
Não houve alteração de entradas, parâmetros, seed ou gates.

O caso **isolado e frio**, a afinidade de cada subprocesso próprio a quatro CPUs
e o overhead do perfilador diferem do contexto histórico do trio. Extratores
mantiveram quatro threads configuradas; CatBoost conservou `thread_count=-1`.
O limite foi de capacidade de CPU, sem alegar teto de número de threads ou
alterar afinidade de outros processos.

O operador terminou com exitcode 0 em 39,87 s antes da limpeza final, dentro
dos 300 s globais. O maior RSS amostrado foi 1.820.545.024 bytes e o workspace,
2.416.523 bytes, abaixo de 3,5 GiB e 384 MiB. As amostras são de 50 ms; os
limites amostrados não são cotas instantâneas rígidas. Mantiveram-se 32 MiB por
arquivo, 64 KiB por saída e rede isolada.

A autorização foi consumida e encerrada: nenhuma repetição ou nova preparação.
Áudio, frames, cópias e vetores novos foram removidos após quiescência. Digests,
previsões e recibos ficam privados. Os 15 pins de fonte e os arquivos anteriores
vinculados continuam iguais. Os três inputs, o manifesto canônico e a passagem
privada permanecem preservados, com validade até **21/10/2026 às 23h59, São Paulo**.
Não foi programada exclusão automática nem declarada apresentação concluída.

Foram zero aquisições, chamadas remotas/NIM/VLM, treino, acesso a conteúdo do
teste reservado, instalações ou escritas na árvore principal. A conferência
final verificou apenas recibos, hashes, guardas e projeções; nenhuma suíte foi
repetida.

**Não reproduzir não elimina a falha histórica.** A causa permanece desconhecida
e a [divergência independente](issue-5-demo-local-python-mcp-resultado.md)
continua aberta. Não há prova de igualdade com os vetores históricos ausentes.
A [consulta canônica e o guia entregues](issue-5-consulta-canonica-demo.md) não
dependem deste diagnóstico. Nenhuma paridade independente, issue ou avaliação
científica foi declarada aprovada.

# Par real Python/MCP independente — respostas completas iguais

Uma execução Python e uma MCP stdio reais concluíram em **159,816 s** no
protocolo v6. Ambas executaram o StateGraph/subgrafo, extração nativa, M1/A200,
SHAP e comparáveis, com handoff nativo e packet vinculado. As respostas
completas são iguais, sem remover campos, arredondar números ou normalizar
valores para obter igualdade. O SHA256 de ambos os arquivos é
`89a45573800d4da77584ba789437c77b5bb389932bbf73ad3dc5148e7864aba0`.

| Conferência | Resultado |
| --- | --- |
| Áudio, ASR, embedding, PredictorInputs e CandidateFeatures | 36/36 comparações iguais nas três posições |
| Previsões e faixas q10/q50/q90 | Iguais; retornos vinculados aos inputs e à resposta |
| SHAP / comparáveis ordenados / packet | Iguais integralmente |
| Extrações / `predict_views` | 6 / 6, três de cada por rota |
| Etapas SHAP / comparáveis | 2 / 2; seis buscas de comparáveis |
| Predições dos modelos de quantil | 24, pelo laço nativo: 18 da previsão + 6 da etapa SHAP |
| Python / MCP | 72,772 s / 86,772 s, ambos com saída 0 |
| Maior RSS / workspace amostrados | 2.507.304.960 / 6.253.612 bytes |
| Terminais | 19 completos + 2 predecessores ligados ao sucessor de `exec`; zero erros |
| Encerramento | Recolhimento confirmado, scratch vazio, zero jobs de modelos no snapshot final |

Não foi observado primeiro estágio divergente neste par. O recibo
[agregado público](evidence/issue-5-paridade-independente-resultados-20261021.json)
registra contagens, recursos e resultados, sem transcrições, vetores, IDs,
caminhos privados ou previsões individuais. Os diagnósticos por fase ficam
nos recibos privados.

Nos pontos correspondentes dos workers, origens/versões dos imports e máscaras
de 12 CPUs coincidiram. Extratores mantiveram quatro threads. As diferenças de
ambiente registradas foram o grupo supervisionado e o diretório temporário
próprio de cada execução. Hashes de RNG foram capturados e diferiram entre
processos; nenhuma seed ou afinidade foi alterada pelo observador. Isso não
atribui causa à divergência histórica. Estados internos não expostos pelo
backend continuam desconhecidos.

Houve duas cargas de contexto por rota, previstas no código original: a da
análise e a revalidação de linhagem dos comparáveis. Não houve previsão
auxiliar. Os 24 calls de quantil decorrem dos oito `predict_logs` completos
e de seus três modelos congelados. Os picos foram amostrados a cada 50 ms;
o perfilador acrescenta overhead. Os limites de 1.200 s globais, 480 s internos
mais 30 s de encerramento por rota, RSS de 3,5 GiB e workspace de 384 MiB foram
respeitados. Não houve retry, aquisição, NIM, VLM gerativo, treino ou abertura
do conteúdo do teste reservado.

As respostas completas novas coincidem também com o MCP histórico; seus
objetos M1 diferem do Python histórico. Esse alinhamento não determina a
causa antiga. **Os 22 campos históricos divergentes continuam registrados e
o Python original permanece como fonte canônica.** Os inputs, relatórios,
manifesto e handoff anteriores foram preservados, inclusive as paradas de
[startup/exec](issue-5-paridade-independente-parada-e-correcao.md) e
[lock somente leitura](issue-5-paridade-independente-lock-ro.md), ambas antes
de qualquer ML. O ajuste foi restrito ao operador, sem modificar o M1.

Um handoff privado `0600` adicional aponta para este par atual e sua data,
fontes, limites e recibos. Ler esse handoff é uma consulta offline; os relatórios
descrevem as execuções reais já concluídas. Ele não substitui o canônico nem
autoriza outra execução. A autorização v6 foi consumida e encerrada.
Retenção mantida até **21/10/2026 às 23h59, São Paulo**, sem exclusão automática.

O resultado demonstra paridade deste par instrumentado, nestas três peças e
configuração. Não valida qualidade preditiva, calibração, aderência qualitativa
ou reprodução universal de outros estados de inicialização.

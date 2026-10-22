# Nativa 225 — resultado da tentativa única renovada

A execução no código `1e1d3ab` terminou com sucesso técnico no negativo
já revelado. Começou em 22/10/2026 às 03:25:07 UTC e terminou às 03:25:18 UTC.
A cápsula corrigida passou no preflight antes da reserva; havia 11,56 GiB
disponíveis. A rodada anterior v1 permaneceu selada e sem alteração.

| Observação | Resultado |
| --- | --- |
| Processo do modelo iniciou | Sim |
| Encoder e decode da imagem completos | Sim |
| Tokens visuais observados | 240 |
| Resposta JSON estrita | `{"answer":"no"}` |
| Acerto neste negativo | Sim |
| Duração da captura nativa | 10,0899 s |
| Duração do controlador | 11,0840 s |
| Pico RSS observado | 2618,04 MiB, aproximadamente 2,56 GiB |
| Limpeza confirmada, scratch ausente e workers restantes | Sim, sim e zero |
| Reservas / saldo / fila | 1 / 0 / selada |

O encoder reportou 4,775 s e os dois lotes de decode completos somaram
2,432 s, com 240 tokens no total. A previsão de 960 posições antes do merger
fica coerente com esses 240 tokens; o recibo não mede separadamente cada
posição anterior ao merger. Os 20 bytes originais de stdout e o resultado
terminal persistiram antes da limpeza. A inspeção do capturador validou
estado, hashes e encerramento, sem nova inferência.

## O que este caso permite concluir

A configuração 225 executou o mesmo PNG nativo 360×640, sem recorte ou redução
do conteúdo, nos limites de tempo e memória aprovados, e acertou a resposta
negativa. A cápsula passou a fornecer `/dev` efêmero; o preflight com
`stdin=DEVNULL` acontece antes de reservar. A mudança de geometria e o
ambiente desta rodada não constituem uma comparação causal isolada com todos
os timeouts históricos.

O caso é revelado e não avalia positivos nem libera atributos visuais. Os
gates perceptivos, a auditoria independente, B/C completos e a avaliação
final continuam pendentes. O NIM não foi chamado. Nenhuma fila antiga foi
reaberta, imagem foi adquirida ou modelo foi baixado. A renovação de uso da
imagem valeu exclusivamente para esta tentativa, agora consumida.

## Código e verificações

O [protocolo renovado](issue-4-vlm-native225-renewed-once-v2.md) mantém pesos,
pergunta, schema, seed 42, temperatura zero, quatro threads, saída 64 e
min/max 225. O novo namespace isola recibos da v1. Passaram 32 testes com
filhos inventados em 0,81 s, Ruff e formatação. Na primeira seleção, dois
testes ainda tinham datas fixas da v1; foram corrigidos para usar a janela
v2, sem mudança nos gates. Os nove pins de cada rodada continuam iguais e
os recibos v1 conferem pelos hashes originais.

O [agregado sanitizado](evidence/issue-4-vlm-native225-renewed-once-v2-results.json)
registra os hashes dos recibos privados. Não há nova autorização de inferência,
uso geral da imagem, treinamento ou abertura do holdout neste resultado.

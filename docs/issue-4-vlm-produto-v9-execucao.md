# Produto v9 — controles e preparação do piloto

**Checkpoint histórico:** a execução posterior foi interrompida externamente
no caso 34 e está selada. A [comparação parcial e o descarte](issue-4-vlm-produto-v9-resultados.md)
registram 33 resultados completos; as 64 folhas já foram removidas. Os relatos
de inferência em andamento abaixo descrevem o momento anterior à parada.

Checkpoint iniciado em 19/10 e conferido em 20/10/2026, horários de São Paulo.
A [correção de produto](issue-4-vlm-produto-v9-protocolo.md) foi implementada e
congelada antes das chamadas. O candidato estruturado passou pelos controles e
pelo mínimo de continuidade do piloto; as 64 aquisições estão verificadas e a
inferência dos 48 restantes segue em execução neste checkpoint.

## Controles reais, sem seleção de variante

Foram reconstruídos os mesmos 12 PNGs sintéticos negativos v8, com hashes e
tempos iguais aos recibos anteriores. Cada variante executou 12 chamadas locais,
totalizando 48 válidas, sem repetição/falha de contrato. Os três contrastes são
diagnósticos; somente a candidata estruturada foi autorizada para os vídeos.

| Variante | true | false correto | unknown |
| --- | ---: | ---: | ---: |
| v8, cache anterior | 5 | 0 | 7 |
| Só enumeração false primeiro | 5 | 0 | 7 |
| Só exemplos de ausência primeiro | 2 | 3 | 7 |
| Só chave neutra | 1 | 0 | 11 |
| Estruturada: estado e categorias | 0 | **12** | 0 |

O gate de 12/12 ausências corretas passou. A estruturada retornou dez no_target
e dois incidental_only; ambos mapeiam para false. Não há rótulos de subestado
nesses controles, portanto isso não valida a classificação intermediária.
O contraste de enumeração não mudou esses resultados, a chave neutra aumentou
abstenções e a ordem dos exemplos corrigiu três controles. A decomposição mudou
mais fatores conjuntamente; não foi isolada a causa interna da melhora nem
demonstrada qualidade em vídeos. As sessões dos controles somaram 613,52 s.

## Piloto pareado preparado

As 16 aquisições do piloto congelado concluíram em 69,00 s, uma tentativa por ID,
sem falha ou recuperação DNS. A revisão independente confirmou propriedades,
folhas, recortes e tempos exatamente iguais ao cache v8/plano. Vídeos temporários
foram removidos por sessão. As 16 folhas permanecem somente até comparação e
revisão; seu descarte ainda não ocorreu neste checkpoint.

São oito negativos de produto e oito positivos, todos entre os 64 casos de
treino já revelados: dez beleza/seis moda. Só produto será inferido; pessoa e
texto vêm do cache. Prosseguir aos outros 48 exige pelo menos um acerto de
valor+frames em cada célula setor×classe, sem retuning e sem alegar validação
independente. O resultado desse piloto estava pendente no primeiro checkpoint;
segue abaixo a atualização verificada.

## Piloto concluído e 64 aquisições verificadas

As 64 chamadas dos 16 casos foram válidas, sem retry. O mínimo de continuidade
passou, com pelo menos um acerto de valor+frames em cada célula:

| Setor / classe original | Casos | Acertos de valor+frames |
| --- | ---: | ---: |
| Beleza / negativo | 6 | 2 |
| Beleza / positivo | 4 | 4 |
| Moda / negativo | 2 | 2 |
| Moda / positivo | 4 | 3 |

São 11/16 acertos compostos; isso não aprova o extrator. A revisão independente
recalculou o gate, os frames ≤3 s e a preservação de pessoa/texto do cache.
O piloto é desenvolvimento revelado, sem independência estatística.

Após o gate, as outras 48 aquisições concluíram. O total é 64 casos, 64 tentativas,
zero falhas/DNS, 279,00 s de aquisição e 246 aquisições cumulativas incluindo a
linhagem anterior. A revisão confirmou os 256 recortes, folhas, propriedades e
tempos exatamente iguais à v8; todos os runs confirmam limpeza dos vídeos.
O recibo `full-acquisition-verification.json` fixa os hashes dessas sessões e
dos resultados do piloto. As 64 folhas ainda aguardam comparação/revisão para
descarte. A inferência restante está em andamento, sem alterar o candidato.

## Verificação e preservação

Os 597 testes públicos passaram em 513,79 s, incluindo 21 testes do extrator
e nove de integração; Ruff e formatação dos 108 arquivos passaram. A revisão
independente aprovou contrato, recuperação e orçamento, reparseou os 48 recibos
reais e conferiu os hashes contra os controles antigos. Os 125 pins herdados e
as quatro fontes v9 congeladas conferem. Commits de implementação: `d241db7`
e `21db02f`.

Plano privado: `data/private/issue-4-vlm-produto-v9-desenvolvimento/plan.json`,
SHA lógico `9c335500a7bc5ff72199ca957674c71f0e5481367e46d08c803036a7e48b92df`.
Recibos: `implementation-verification.json`, `control-comparison.json` e
`controls-acquisition-verification.json` na mesma pasta. Nenhuma fonte/prompt
mudou após o congelamento. Partições 203/66/31, teste reservado, M1/A200, A300,
B-cache, serviço/MCP e anotações antigas estão preservados. Nenhuma coluna
liberada, nova auditoria cega selecionada ou treino preditivo iniciado.

# Produto v9 — comparação parcial selada após interrupção externa

Conferência de 20/10/2026. A correção estruturada foi implementada e acertou
12/12 controles negativos. A avaliação dos 64 vídeos **não foi concluída**:
uma interrupção externa encerrou o processo no caso 34, após três respostas
capturadas e uma quarta chamada reservada sem saída recuperável. Há **33 casos
completos, um interrompido e 30 não iniciados**. Não houve retry ou substituição
de resposta. Nenhuma coluna foi liberada, auditoria nova selecionada ou treino
B-VLM iniciado. M1 e teste reservado permanecem preservados.

## Controles e piloto

O [protocolo](issue-4-vlm-produto-v9-protocolo.md) e as quatro fontes foram
congelados antes das chamadas; o [checkpoint](https://github.com/leeunam/case-GALAXIES-IA/blob/0df616e5fd64dfc4947abde583f2664b66abf410/docs/issue-4-vlm-produto-v9-execucao.md)
registra a implementação e a aquisição pareada. Nos mesmos 12 controles v8:

| Variante | true | false correto | unknown |
| --- | ---: | ---: | ---: |
| v8 em cache | 5 | 0 | 7 |
| Somente enumeração false primeiro | 5 | 0 | 7 |
| Somente ordem dos exemplos | 2 | 3 | 7 |
| Somente chave neutra | 1 | 0 | 11 |
| Estruturada, candidata previamente escolhida | 0 | **12** | 0 |

A candidata passou no mínimo de continuidade do piloto: 11/16 acertos de
valor+frames, sendo beleza 2/6 negativos e 4/4 positivos, moda 2/2 negativos e
3/4 positivos. Esse mínimo autoriza completar o desenvolvimento, sem aprovar
qualidade. A matriz de controles não foi usada para trocar de candidata ou
ajustar o prompt. Não há rótulos dos subestados/categorias intermediários.

## Comparação nos mesmos 33 casos completos

Os 33 são treino já revelado: 24 do grupo antigo e nove da auditoria anterior,
agora desenvolvimento; 21 beleza/12 moda. Incluem todos os oito negativos
predefinidos do piloto e 25 positivos. O subconjunto incompleto tem composição
diferente dos 64 e não é holdout independente.

| Produto / mesmos 33 casos | A/v7 | v8 | v9 |
| --- | ---: | ---: | ---: |
| Conhecidos / unknown | 33 / 0 | 33 / 0 | 33 / 0 |
| Previsões true / false | 27 / 6 | 33 / 0 | 25 / 8 |
| Acertos de valor | 27 | 25 | 25 |
| Acertos de valor+frames | **25** | 21 | 24 |
| Casos com evidência sem suporte | 2 | 4 | 1 |
| Negativos corretos / oito | 4 | 0 | 4 |
| Falsos positivos | 4 | 8 | 4 |
| Falsos negativos | 2 | 0 | 4 |

Frente à v8, v9 ganhou oito e perdeu cinco acertos compostos, saldo +3. Frente
a A/v7, ganhou quatro e perdeu cinco, saldo −1. A redução de falsos positivos
veio acompanhada de quatro falsos negativos; o acerto de valor ficou igual à
v8. A correção não demonstrou ganho geral sobre A/v7 neste subconjunto.

| Acertos de valor+frames / conjunto pareado | A/v7 | v8 | v9 |
| --- | ---: | ---: | ---: |
| Piloto, 16 | 11 | 7 | 11 |
| Outros completos, 17 | 14 | 14 | 13 |
| Grupo antigo completo, 24 | 19 | 18 | 18 |
| Grupo revelado completo, 9 | 6 | 3 | 6 |
| Beleza, 21 | 16 | 12 | 16 |
| Moda, 12 | 9 | 9 | 8 |

B/v7 só existe para o grupo antigo. **Nos mesmos 24**, acertou 17 valores+frames,
contra 19 de A/v7, 18 de v8 e 18 de v9. Não comparar esses 17/24 diretamente
com os totais de 33 ou com o B antigo completo de 32.

Nos frames explicitamente anotados, v9 marcou true em 43 dos 68 positivos e
false em 18 dos 24 ausentes; v8 marcou true em 66 positivos (dois unknown) e
nenhum false entre os ausentes (20 true/quatro unknown). Frames não anotados
não foram convertidos em negativos. Pessoa/texto ficaram idênticos ao cache
v8: respectivamente 31 e 26 acertos compostos nos mesmos 33. Os gates originais
por origem de 32 **não foram calculados**, pois a execução ficou incompleta.
`released_fields` e `fields_ready_for_future_blind_audit` estão vazios.

## Interrupção, contadores e descarte

A auditoria confirmou processo encerrado, sessão de execução inexistente e
lock livre. A operação sem resposta é o **frame 4 do caso 34, em 12,667 s**,
com PNG RGB320×330, modelo, configuração e identidade congelados no plano.
O caso tem três recibos completos válidos e um recibo `running`
sem raw, sem `result.json`. stdout/stderr eram pipes do processo, sem arquivo
recuperável. Mesmo o quarto frame estando depois de 3 s, não foi fabricada uma
resposta ou alterado o contrato de quatro frames para declarar o caso completo.

O checkpoint anterior foi arquivado byte a byte. Após revisão independente,
somente a entrada interrompida foi finalizada como falha externa, conservando
as quatro reservas; os 184 recibos originais permaneceram idênticos. A parada
operacional registrada permitiu selar a comparação apenas dos 33 completos.

- 64 aquisições novas, uma tentativa por ID, zero falhas/DNS; 246 cumulativas.
- 184 reservas novas de chamada: 48 controles, 132 dos 33 casos completos e
  quatro do caso interrompido. Há 183 respostas completas e uma reserva sem
  resposta capturada; contador cumulativo de reservas: 1.637.
- Maior duração nos recibos completos: 27,08 s; maior RSS amostrado: 2.607,06 MiB.
  Não há medidas recuperáveis da chamada sem resposta.
- Tempo contabilizado antes da interrupção: 18.738,95 s cumulativos. Foi cobrado
  conservadoramente o intervalo de 15.700,18 s desde o último checkpoint até a
  constatação da parada, incluindo possível ociosidade: **34.439,13 s no orçamento**.
  Esse acréscimo não é runtime nativo medido. O teto de 27 h não foi aumentado.
- Os cinco temporários confirmados por hash e as 64 folhas foram descartados
  com journals. Zero imagens/sessões temporárias restantes. Reexecução de
  controles/aquisição/inferência é recusada antes de novas operações;
  comparação/descarte são idempotentes.

Chegar aos 64 depende de **novo protocolo/autorização de recuperação**. A opção
mínima que reaproveite os 33 resultados e os três raw parciais exigiria repetir
uma reserva sem resposta e executar os 30 casos ainda não iniciados: mais 121
chamadas, total de 305 reservas novas, acima do limite atual de 304; seriam
1.758 reservas cumulativas, uma acima do teto de 1.757. Como as
folhas foram descartadas conforme o protocolo, também seriam necessárias 31
reaquisições pareadas (casos 34–64), total de 277, excedendo o teto atual de 256
em 21. O fluxo congelado proíbe tanto repetir inferência quanto saltar o caso
interrompido; por isso não pode continuar automaticamente só pelos outros 30.

Essa é uma **hipótese mínima para decisão humana**, sem recuperação implementada
ou garantida: novo aditivo precisaria especificar como comprovar/reutilizar os
33 resultados e os três recibos parciais, reaquisição com hashes/tempos iguais,
nova chamada do frame 4 e novos limites antes de qualquer execução. Não houve
tempo, rede ou custo adicional executado/medido para essa hipótese, nem preço
estimado. A alternativa é manter a comparação parcial selada e seguir tarefas
independentes de explicação/reprodução. Nada disso autoriza outra auditoria cega,
retry, nova aquisição ou reabertura da fila antiga.

## Recibos e preservação

Pasta privada: `data/private/issue-4-vlm-produto-v9-desenvolvimento/`.
`interruption-audit.json` e o snapshot anterior preservam a reserva sem raw;
`interruption-finalization-verification.json` aponta para o checkpoint **antes**
da comparação. O snapshot posterior e `post-comparison-verification.json`
ligam a comparação ao checkpoint selado antes do descarte; `terminal-verification.json`
confere o estado final. `paired-product-analysis.json` registra ganhos/perdas.

Comparação SHA lógico:
`ccb6236f929be22d0fbfb6c7fe1f35a27e39115ba35829545859e5d4a6e7042f`.
Comparação SHA do arquivo:
`d7706a154be9ea62d813cd23dca2ef1274c33414b8463b995c94d7c981cf4088`.

Os 125 pins herdados e quatro fontes congeladas conferem. Partições 203/66/31,
anotações, M1/A200, A300, B-cache, serviço/MCP e teste reservado estão intactos.
Antes das chamadas passaram 597 testes. A suíte final passou em **624 testes
em 317,65 s**; Ruff e formatação dos 112 arquivos passaram, assim como os 27
testes direcionados dos componentes locais posteriores. A revisão independente reproduziu os raw,
métricas, composição dos subconjuntos e a contabilidade da interrupção.
Commits de implementação: `d241db7` e `21db02f`; checkpoints: `0c90029` e `c25697a`.

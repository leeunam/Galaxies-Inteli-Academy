# B-VLM: auditoria concluída, nenhuma coluna liberada

Execução de 19/10/2026 na branch `codex/issue-4-experimento-b`. O complemento
VLM **não foi concluído como experimento preditivo**: a auditoria dos 32 casos
fixados de treino reprovou todas as cinco colunas candidatas. Não foi treinado
um B-VLM, nem criada comparação preditiva sua com B-cache/A300/A200. O resultado
é uma falha da etapa de percepção segundo o protocolo, não evidência de que
VLM melhora ou piora a previsão. B-cache continua sendo a versão de B treinada.

## Protocolo e fronteira preservados

A coorte permanece 300 referências, com 203 treino/66 validação/31 teste,
separadas por canal. Os 269 IDs de desenvolvimento e os 32 de auditoria
(16 de cada setor, todos de treino) foram fixados antes das chamadas VLM.
O teste reservado não teve evidências, rótulos, matrizes, previsões ou métricas
abertos. M1/serviço/MCP, B0, A200, A300, B-cache, extratores e partições
permanecem intactos; 45 arquivos congelados conferidos por SHA256.

Os contratos são o [protocolo inicial](issue-4-experimento-b-vlm-protocolo.md),
a [identidade visual](issue-4-experimento-b-vlm-identidade.md),
a [normalização estrita](issue-4-experimento-b-vlm-deduplicacao.md) e a
[retomada DNS](issue-4-experimento-b-vlm-dns.md), todos registrados antes das
respectivas execuções. Não houve novo serviço externo, dependência, coleta de
views, ajuste de prompt/modelo por resultado ou mudança de limiar após o gate.

O vídeo reobtido teve bytes de contêiner diferentes nos 32 casos. Seu uso foi
condicionado à reprodução exata do hash PNG da folha congelada e à igualdade
de propriedades/tempos. Qwen recebeu somente crops 320×330 dessa folha
verificada, sem os rótulos desenhados sobre ela. Isto prova identidade desses
pixels amostrados, não dos arquivos de vídeo ou dos JPEGs 512px antigos.
ASR/MiniLM/CLIP e medidas técnicas existentes não foram reextraídos.

## Execução e proveniência

- O lote v1 parou após 13 conclusões: um JSON completo continha índices de
  evidência repetidos. Um diagnóstico separado confirmou a causa. O novo
  adaptador apenas deduplica índices válidos, preservando valores e resposta
  bruta; continua recusando erros de estrutura, tipos, tempo ou evidência.
- O lote uniforme v2 concluiu 3 casos e parou no quarto por DNS. Seus fontes,
  checkpoint e sidecars foram preservados. Nenhum deles foi misturado à v3.
- A v3 concluiu os 32 casos da auditoria em 33 tentativas: uma falha DNS
  explicitamente temporária foi arquivada, com limpeza, preflight positivo e
  uma única repetição bem-sucedida. Foram 54 aquisições/tentativas cumulativas,
  incluindo 21 anteriores, frente ao teto 300. Tempo acumulado nas sessões e
  aquisições: 2.404,7165 s; a v3 consumiu 1.238,8385 s. O teto 27 h não foi reiniciado.
- Todas as sessões encerradas confirmaram descarte da mídia. A mediana por
  caso v3 foi 38,97 s; o maior tempo, 44,96 s. O maior RSS amostrado do processo
  filho VLM foi 2.610,04 MiB, com amostragem 0,1 s; não representa a memória total
  da máquina nem uma garantia para outros vídeos.
- A normalização de índices ocorreu uma vez, em produto inicial. Não houve
  alteração de valores perceptivos individuais ou preenchimento de ausências.
- Após a revisão independente reproduzir o gate, a fila foi selada com
  `quality_gate_no_columns_released`. Uma chamada real de execução recusou
  a retomada antes de rede ou modelo. As 49 folhas temporárias das rodadas e
  diagnóstico foram removidas, preservando hashes, anotações e recibos.

Plano v3: `36e922ee812dce5328eaac217bd1a83bf9373eb922e690fb0dec51af2c3d0350`.
O recibo completo de 32 anotações foi fixado antes de calcular o gate:
`82a04b63167039ea7640eb62c51827fc4d1fde4bef68cf428eeaa5f7d02175ab`.
Hash lógico do resultado do gate:
`941d1b57e9f2f3557224d0d207737bb5810c315dd806456ec64fb505dfd5f6eb`.
Os recibos e respostas brutas permanecem em armazenamento privado ignorado.

## Resultado da percepção

Anotação visual assistida por agente separado, cego às respostas do Qwen,
views e transcrições. As 14 anotações anteriores foram reutilizadas somente
após conferir ID, tempos e hash da folha. As 18 restantes foram fixadas antes
da comparação com Qwen. Correções mecânicas de evidência temporal, lista vazia
para `unknown` e uma transcrição de hash foram confirmadas pelo revisor e
registradas, sem ajustar valores por respostas do modelo. Não houve
revisão humana desta amostra nem certificação da verdade de referência ou da acurácia geral.

Concordância abaixo exige **valor e frames citados compatíveis** com a
anotação. Denominadores excluem `unknown` e classes raras retiradas conforme
regra anterior. O gate exige, em cada setor, 12 conhecidos, concordância ≥ 90%
e zero citações sem suporte; exige também suporte aos valores/classes.

| Atributo | Beleza: acertos/conhecidos | Moda: acertos/conhecidos | Citações sem suporte beleza/moda | Liberado |
| --- | ---: | ---: | ---: | --- |
| Pessoa visível | 12/16 (75,0%) | 15/16 (93,8%) | 2/1 | Não |
| Produto até 3 s | 12/16 (75,0%) | 16/16 (100%) | 1/0 | Não |
| Texto em tela | 13/16 (81,3%) | 16/16 (100%) | 1/0 | Não |
| Ambiente | 12/14 (85,7%) | 12/15 (80,0%) | 1/2 | Não |
| Formato | 3/15 (20,0%) | 6/16 (37,5%) | 2/0 | Não |

Produto inicial teve 32 previsões `true`, sem suporte ao valor `false`.
Formato apresentou discordância ampla; close-up, demonstração e formato
`application` continuam fora das entradas pelo bloqueio global anterior.
As boas contagens de produto/texto em moda não liberam colunas do modelo
conjunto quando beleza falha. Não relaxar o gate nem escolher outro atributo
após observar estas contagens.

O protocolo determina: “Se nenhuma coluna passar, registrar falha da etapa e
não declarar B completo nem substituir por B-cache.” Por isso a execução parou
na auditoria. Os 237 sidecars restantes (171 treino/66 validação) não foram
extraídos, não houve seleção de colunas por desempenho e a grade real de 12
ajustes não foi iniciada. O contrato de qualidade recusa `no_columns_released`;
o carregador recusa a fila incompleta antes de carregar rótulos de treino.
Não existe novo bundle preditivo B-VLM.

## Comparação disponível, preservada

Estes são os resultados **anteriores**, com seus artefatos e relatório
verificados por hash; não são uma nova execução nem substituem B-VLM.
MAE de `log1p(views)` médio por canal; menor é melhor.

| Validação | A200 | A300 | B-cache 300 | B-VLM 300 |
| --- | ---: | ---: | ---: | --- |
| 45 antigas | 1,8569 | 1,9327 | 1,7082 | Não treinado |
| 21 novas | 1,6419 | 1,6568 | 1,6204 | Não treinado |
| 66 unidas | 1,7349 | 1,7761 | 1,6584 | Não treinado |

B0 ampliado marcou 1,8830 na união. B-cache preserva a melhor média global
entre os modelos treinados, mas mantém a pequena regressão em moda frente
a A300 e falhas nos cinco casos fixos de alto alcance. A validação foi usada
para selecionar os modelos; não constitui avaliação final independente.
Não há métrica, ranking, cauda ou cobertura de B-VLM para comparar.
Detalhes dos comparadores: [relatório B-cache](issue-4-experimento-b-resultados.md).

## Verificação e próximo marco

509 testes passaram, incluindo ajustes CatBoost sintéticos com recarga nativa
e paridade exata; Ruff/formatação de 93 arquivos e revisão independente do
código/checkpoint passaram. A execução real confirmou hashes, limpeza,
contabilização DNS e recusa do treino incompleto/sem colunas, antes do loader
de rótulos. Esses testes de infraestrutura não são treino preditivo B-VLM real.

Para seguir com VLM, a próxima rodada precisa tratar a percepção como problema
de desenvolvimento: usar esta amostra para diagnosticar o extrator, congelar
uma nova versão e um protocolo, e avaliá-la em **outra amostra cega de treino**
antes de reexecutar os 269 casos e os 12 ajustes. A amostra atual já foi revelada
e não deve servir como nova auditoria independente. Isso pode preservar as
partições e o teste reservado. C e promoção ao serviço não foram iniciados.

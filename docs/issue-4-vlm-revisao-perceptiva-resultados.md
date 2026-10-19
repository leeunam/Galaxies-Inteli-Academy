# Revisão perceptiva VLM: nova auditoria sem colunas liberadas

Em 19/10/2026, o extrator por frame foi implementado e avaliado em outra
amostra cega de treino. **Nenhuma coluna passou no gate.** A execução foi
selada antes de retomar o treino preditivo B-VLM. M1, B-cache, A300, A200,
serviço/MCP, partições 203/66/31 e teste reservado permanecem preservados.

## Correção e separação

O [protocolo anterior às inferências](issue-4-vlm-revisao-perceptiva-protocolo.md)
limitou a revisão a pessoa, produto inicial e texto. O adaptador v7 recebe
um crop por chamada; agrega valores e referências temporais por código, com
unknown explícito. Valida imagem, JSON estrito, campos, tipos e valores,
preservando resposta bruta antes do parser. Não escolhe índices por linguagem
natural nem preenche incertezas com outro candidato. Os extratores anteriores
e os recibos da rodada reprovada não foram alterados.

A [seleção de desenvolvimento](issue-4-vlm-revisao-perceptiva-desenvolvimento.md)
usou somente os 32 casos antigos revelados: A acertou 62/96 pares
valor+evidência, contra 54/96 de B. A foi congelado antes de qualquer inferência
nova, sem combinação por coluna. Foram outros 32 casos de treino na auditoria,
16 por setor, em 32 canais distintos e sem sobreposição de canal/mídia com
desenvolvimento. A seleção por hash precedeu inspeção visual e inferência.

Um agente separado anotou as imagens, cego às saídas VLM e aos rótulos de
alcance. O arquivo foi selado antes da escolha e manteve o mesmo SHA256 até o
gate. O executor não abriu imagens/anotações novas para desenvolver ou
selecionar; durante a auditoria acompanhou somente os contadores. A anotação
é assistida e não equivale a revisão humana ou verdade certificada. Não foram
usados views, títulos, transcrições ou métricas preditivas nesta revisão.

## Resultado cego do candidato A

O gate permaneceu idêntico: ao menos 12 respostas conhecidas em cada setor,
concordância de valor+evidência de pelo menos 90%, zero evidências citadas sem
suporte e suporte às duas classes booleanas, tanto globalmente quanto por setor.
Os denominadores abaixo são respostas conhecidas; cada setor contém 16 casos.

| Campo | Beleza: acertos/conhecidos | Moda: acertos/conhecidos | Pares com evidência sem suporte (beleza/moda) | Decisão |
| --- | ---: | ---: | ---: | --- |
| Pessoa visível | 16/16 (100%) | 15/16 (93,75%) | 0/1 | Reprovado: evidência sem suporte em moda |
| Produto até 3 s | 13/16 (81,25%) | 14/16 (87,50%) | 1/0 | Reprovado: concordância e evidência |
| Texto na tela | 2/2 (100%) | 4/5 (80%) | 0/1 | Reprovado: cobertura, classes, concordância e evidência |

Pessoa teve um falso negativo em moda. Embora ambos os setores ultrapassem
90%, o requisito de evidência sem falhas também é obrigatório. As previsões
incluíram ambas as classes: 29 true e 3 false, com suporte em ambos os setores.

Produto gerou três falsos positivos e um falso negativo no total. Em beleza,
um caso com valor correto também citou evidência sem suporte; por isso,
concordância de valor isolado não equivale à coluna liberada. O suporte de
classes foi 29 true e 3 false; ele não compensa os outros requisitos.

Texto ficou unknown em 25/32 casos. Os sete conhecidos foram todos false,
seis corretos e um falso negativo. Não houve nenhuma previsão true, nem
cobertura mínima por setor. A taxa de 100% sobre apenas dois conhecidos de
beleza não demonstra qualidade suficiente. Ambiente e formato ficaram
globalmente desconhecidos, como previsto; close-up e aplicação continuam
retidos. Nenhuma saída foi corrigida pela anotação.

Essa nova amostra não permite comparar diretamente taxas com a auditoria
anterior: mudaram casos e canais, e a anterior já foi usada no desenvolvimento.
A conclusão sustentada é a reprovação no gate fixado desta rodada, sem alegar
acurácia geral validada. Não houve flexibilização, reposição, terceiro candidato
ou nova tentativa após o resultado. A auditoria agora está revelada e não pode
validar futuras correções.

## Execução e preservação

As 64 reaquisições reproduziram os hashes das folhas, propriedades e tempos,
com limpeza dos vídeos ao final de cada sessão e zero retries DNS nesta revisão.
A identidade garantida é dos PNGs/crops, não dos bytes dos contêineres de vídeo.
Somadas às 54 tentativas anteriores, são 118 frente ao teto cumulativo 128.

Foram 640 chamadas locais válidas: 128 de A e 384 de B no desenvolvimento,
mais 128 de A na auditoria. Não houve falha ou repetição de inferência. O maior
tempo por chamada foi 19,17 s, e o maior RSS amostrado do filho foi 2.610,13 MiB.
O contador cumulativo de sessões/inferências ficou em 8.226,57 s, incluindo os
2.404,72 s anteriores, dentro das 27 h. Isso não representa tempo total de
trabalho nem garantia de latência em outros casos.

A implementação passou em 549 testes completos; depois da cobertura adicional
para seleção de B e auditoria de 896 chamadas, passaram os 41 testes
direcionados. Ruff/formatação e revisão independente também foram executados.
O revisor reproduziu a seleção e o gate, verificou parsing, hashes dos crops,
tempos e evidências. Não encontrou indício de erro do parser ou alinhamento
temporal que explicasse a reprovação. Os 67 arquivos protegidos permaneceram
iguais, sem leitura de evidências/rótulos ou produção de previsões do teste.

Depois da revisão, as 64 folhas foram removidas pelo fluxo de descarte; ficaram
zero folhas e zero sessões temporárias. Permanecem recibos, sidecars, respostas
e hashes privados. Aquisição e inferência foram chamadas após o encerramento
com funções de rede/modelo que falhariam se acionadas: ambas recusaram antes
dessas funções, com checkpoint idêntico. A guarda do teste permaneceu ativa.
Verificação final:
`7633185e7db37d82ac7773da84bcb7d160ecb904a46ebcf6191e4b9d84a211ba`.

Os artefatos detalhados são privados, fora do Git. Plano:
`a370bc9e3f45f42fa2f57a900918f12622dc2d09a7bcc181a928291f438a3c4b`.
Seleção:
`32ab0507500c6e53ca8f5cc6b159a8ffc690e30e788a78ca59ad71d9fb34592b`.
Prova do gate:
`7f489faa1b6efaf4e03dcbefa49f7aa75e01a2da127071acc90c1548a3568b15`.

Não houve extração uniforme dos 269 casos, ajuste dos 12 modelos B-VLM,
comparação preditiva nova ou promoção de M1. O
[B-cache já comparado](issue-4-experimento-b-resultados.md) continua sendo o
experimento B treinado disponível. Retomar a parte VLM exige outra revisão
perceptiva, novo protocolo e outra amostra cega de treino, antes do lote completo.

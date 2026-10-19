# Revisão VLM: candidato congelado antes da auditoria nova

Este registro precede a
[auditoria nova concluída](issue-4-vlm-revisao-perceptiva-resultados.md).

Em 19/10/2026, os dois candidatos previstos no
[protocolo](issue-4-vlm-revisao-perceptiva-protocolo.md) concluíram os mesmos
32 casos antigos de treino, 16 por setor. Essa amostra já estava revelada:
serve ao desenvolvimento e não é validação da correção. Não foram usados
views, transcrições ou resultados preditivos.

O adaptador v7 pergunta por frame e agrega por código. A usa uma pergunta
com três atributos; B usa três perguntas individuais. Pessoa, produto inicial
e texto geram 96 pares caso/campo por candidato. Os resultados incluem tanto
o valor quanto o suporte dos frames citados; unknown não conta como acerto.

| Candidato | Acertos valor+evidência / 96 | Conhecidos / 96 | Desconhecidos / 96 | Pares com evidência sem suporte | Chamadas locais |
| --- | ---: | ---: | ---: | ---: | ---: |
| A, três atributos por frame | 62 | 69 | 27 | 4 | 128 |
| B, um atributo por chamada | 54 | 64 | 32 | 6 | 384 |

A venceu pelo primeiro critério pré-declarado: mais acertos nos 96 pares.
Não houve escolha por coluna, ranking parcial ou ajuste de prompt após a
comparação. A maior pontuação não demonstra que a percepção ficou adequada:
há desconhecidos e evidências sem suporte mesmo no desenvolvimento.
Nenhuma coluna foi liberada por esse resultado.

O congelamento vincula fontes, prompts, esquema, agregação, runtime, hashes
dos 64 resultados e pontuações. Seleção:
`32ab0507500c6e53ca8f5cc6b159a8ffc690e30e788a78ca59ad71d9fb34592b`.
Foram 512 chamadas válidas, sem falha ou repetição de inferência.

Antes da primeira chamada nova, foi conferido o hash do arquivo de anotações
cegas, fixado por agente separado ainda durante o desenvolvimento:
`20ba10386d0e63a2a97380cf4cbd527279c6177e433b04d2d9deb31fec1f7994`.
O executor não abriu seus valores nem imagens novas para desenvolver ou
selecionar. São outros 32 casos de treino, 16 por setor e 32 canais distintos,
sem canais ou mídia compartilhados com os antigos, selecionados por hash.
As anotações são assistidas, sem revisão humana certificada.

Somente A seguirá para esses 32 casos. O gate original será aplicado uma vez,
sem mudar suporte mínimo, concordância, exigência de evidências ou amostra.
Ambiente e formato continuam desconhecidos. O resultado dessa auditoria
definirá quais colunas, se alguma, poderão compor uma retomada posterior de B;
esta rodada termina na validação perceptiva, sem treino preditivo B-VLM.

Os 67 arquivos protegidos, partições 203/66/31, teste reservado, M1,
B-cache/A300/A200 e serviço/MCP permanecem iguais. A
[preparação](issue-4-vlm-revisao-perceptiva-execucao.md) passou em 549 testes;
a cobertura adicional de seleção de B e seu teto de 896 chamadas passou nos
41 testes direcionados e na revisão independente, commit `6e3f1b3`.

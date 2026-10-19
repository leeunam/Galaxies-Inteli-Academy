# Revisão perceptiva VLM: preparação e aquisição verificadas

Este é o checkpoint histórico de preparação. A execução terminou na
[nova auditoria, sem colunas liberadas](issue-4-vlm-revisao-perceptiva-resultados.md).

Checkpoint operacional de 19/10/2026. Segue o
[protocolo fixado antes das inferências](issue-4-vlm-revisao-perceptiva-protocolo.md),
na branch `codex/issue-4-experimento-b`. A etapa termina na nova validação da
percepção; ainda não há resultado da auditoria nova nem treino preditivo B-VLM.

A implementação passou em **549 testes**, Ruff/formatação de 98 arquivos e
revisão independente. O novo adaptador responde por frame sobre pessoa,
produto e texto; o código constrói referências temporais e preserva unknown.
JSON estrito, PNG RGB 320×330, captura da resposta antes do parser, checksums,
limites, seleção determinística, congelamento, gate e descarte foram verificados.
Os fontes/bundles antigos não foram alterados; 67 arquivos estão protegidos.

Foram fixados 32 casos antigos de desenvolvimento e 32 novos de auditoria,
todos de treino. Cada grupo tem 16 por setor. A auditoria usa 32 canais únicos,
sem canais ou hashes de mídia compartilhados com o desenvolvimento. Os canais
foram amostrados por hash antes de escolher um vídeo por canal, sem views,
transcrições ou inspeção de imagem. Não houve mudança das partições 203/66/31.
Plano: `a370bc9e3f45f42fa2f57a900918f12622dc2d09a7bcc181a928291f438a3c4b`.

As 64 folhas foram reobtidas e reproduziram os SHA256 dos PNGs congelados,
com propriedades e tempos iguais. Todos os vídeos foram descartados ao fim
da sessão. Foram 64 tentativas, sem DNS/retry nesta aquisição; somadas às 54
anteriores, são 118 frente ao teto 128 desta revisão. Não é garantia de bytes
iguais dos contêineres de vídeo; a identidade é da folha e dos crops recebidos
pelo modelo. As folhas ficam somente durante desenvolvimento/auditoria.

O piloto do candidato A concluiu quatro chamadas no primeiro caso antigo,
em 63,94 s, com pico RSS amostrado do filho VLM de 2.608,66 MiB. Pessoa/produto
foram ligados aos frames da anotação desse caso; texto ficou unknown. Isso
é apenas controle de desenvolvimento, não acurácia, latência garantida ou
aprovação de atributo. O protocolo exige ambos os candidatos nos 32 antigos,
seleção inteira por 96 pares e congelamento antes de inferir nos 32 novos.

O revisor registra as anotações novas em artefato privado separado e permanece
cego às respostas VLM. O executor não recebe valores dos novos casos durante
o desenvolvimento; a seleção lê exclusivamente as anotações antigas. A prova
do gate só será calculada depois de fixar as anotações e concluir a nova
inferência do candidato congelado. Os critérios não mudam depois do resultado.

M1/serviço/MCP, B-cache/A300/A200 e teste reservado permanecem preservados.
Não houve leitura de evidências/rótulos do teste ou início de C. Dados, imagens
temporárias, respostas e recibos detalhados ficam em armazenamento privado.
Commits da infraestrutura: `b04e363`, `f6a3298`, `d529007`.

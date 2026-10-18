# Coleta direta e revisão dos setores — 18/10/2026

## Orientação atual e execução

Depois de pedir ajuda com a adesão ao aditivo, o aluno solicitou expressamente
seguir com a consulta pela API e a aquisição dos vídeos sem esse formulário.
A execução desse lote foi autorizada pelo aluno; isso não foi registrado como
aprovação do YouTube nem como adesão contratual. O formulário não foi enviado.
Não repetir o pedido de consentimento para executar esse mesmo lote já autorizado.

Foram processados os **vinte candidatos existentes**, sem ampliar a seleção ou
ordenar por resultados. Um executor nesta árvore, um downloader por vez, usando
o piloto existente e procedimentos descartáveis privados. Nenhum código público,
modelo ou dependência foi alterado.

| Evidência | Resultado |
| --- | --- |
| Consulta oficial `videos.list` | 1 chamada bem-sucedida, 20 registros retornados |
| Novos downloads temporários | 17 concluídos, 0 falhas |
| Pilotos anteriores reutilizados | 3, com procedência e hashes conferidos |
| Referências com fingerprint e propriedades medidas | 20 |
| Vídeos verticais com duração medida até 60 s | 20 |
| Hashes de mídia repetidos | 0; não exclui republicação editada/recodificada |
| Sessões temporárias restantes ao concluir | 0 |
| Novos setores classificados pela IA | 16: 8 moda / 8 beleza |
| Setores anteriores preservados de revisão humana | 4: 2 moda / 2 beleza |
| Distribuição classificada total | 10 moda / 10 beleza, com ressalvas de inclusão abaixo |

Cada setor classificado tem dez referências de dez canais; a densidade é de uma
referência por canal. Não houve exclusão definitiva nesta rodada: os vinte seguem
como candidatos em curadoria. O relatório distingue isso dos dois casos novos
de inclusão, do idioma pendente e da ausência de detecção de republicações editadas.
Essas contagens, exclusões e duplicatas satisfazem o critério de relatório da #1;
não liberam automaticamente a coorte ou os demais critérios.

A primeira consulta feita dentro do ambiente restrito falhou por acesso de rede;
a consulta com acesso de rede autorizado foi bem-sucedida. As duas evidências
foram preservadas separadamente. O downloader usou ambiente mínimo, sem herdar
credenciais da API ou do explicador; sem cookies, plugins, configuração pessoal,
proxies ou mecanismos para contornar bloqueios de acesso.

Foi testado primeiro um novo download, com descarte confirmado; depois foram
processados os outros dezesseis. Cada sessão usou os limites já existentes:
até 60 s, não live, seleção até 720p, teto declarado de 32 MiB e verificação final
de até 64 MiB, timeout de aquisição de 180 s. O lote pararia em autenticação,
403/429 ou limpeza incerta. Não houve esse bloqueio. As dezessete sessões levaram
2,92–6,25 s cada, 77,51 s somadas para aquisição e propriedades neste ambiente.
Esses tempos não incluem revisão pelo navegador, ASR, CLIP ou Qwen e não são SLA.

## Revisão dos dezesseis setores

As referências foram abertas no player normal do YouTube e revisadas por amostras
visuais. Há notas e timestamps privados para cada decisão. Isso é revisão pela
IA, não dezesseis novas confirmações humanas nem observação integral de todos os
vídeos. Títulos e contexto da página foram considerados com sua origem explícita.
Não se alega revisão cega: páginas normais podem mostrar métricas atuais, embora
elas não tenham sido usadas para classificar setores, selecionar ou excluir vídeos.

| Índices da seleção original | Classificação | Evidência observada |
| --- | --- | --- |
| 5–8 | Moda | Apresentações e composições de roupas e looks |
| 9 | Moda | Composições de roupas; legendas em inglês exigem revisão do idioma |
| 10 | Moda | Acessórios para composição do look; amostra inicial inconclusiva foi seguida de outra |
| 11–12 | Moda | Apresentação de shorts e orientações de combinação de roupas |
| 13 | Beleza, acessório; inclusão pendente | Organizador demonstrado junto a cosméticos |
| 14 | Beleza | Produto e aplicação de maquiagem observados |
| 15 | Beleza | Apresentação de kit para cuidados capilares, além das hashtags genéricas |
| 16 | Beleza | Anúncio de hidratante facial, sem avaliação de eficácia |
| 17 | Beleza contextual; inclusão pendente | Cena diante de espelho e descrição explícita de anúncio de base; sem aplicação/produto destacado observado |
| 18–20 | Beleza | Demonstrações de maquiagem e produto blush |

Os casos 13 e 17 não foram aprovados silenciosamente para a coorte. O primeiro é
acessório de organização; no segundo a identificação do produto depende do
contexto explícito da página. São os dois casos indicados para revisão de inclusão.
O quarto candidato mantém sua revisão humana parcial anterior. Indicações de
conteúdo IA foram observadas em algumas páginas e registradas, sem inferir a
origem integral dos vídeos nem criar filtro novo depois de ver resultados.

O aluno pediu silêncio durante a revisão: o player foi silenciado e esse estado
foi conferido nos vídeos seguintes. O player foi encerrado ao terminar a revisão.
Não foi necessário reproduzir áudio para a classificação visual dos setores.

## Manifesto consolidado e observações

Os arquivos ficam em `data/private/issue-1-execucao-direta-20261018/`, ignorada pelo
Git. A consolidação está em `consolidated/candidate-records.json`,
`consolidated/manifesto-candidatos.csv` e `consolidated/report.json`. Referências,
notas, transcrições anteriores, métricas individuais e hashes ficam privados.
`sector-reviews.json` distingue rótulos humanos de classificação pela IA;
`acquisition.json` registra sucessos, fingerprints, hashes dos artefatos e limpeza.
`consolidated/eligibility-summary.json` consolida suporte por setor/canal, densidade,
exclusões e duplicatas, distinguindo candidatos de registros elegíveis.

Verificação: **28 testes direcionados passaram** para aquisição, descarte e fila;
Ruff e formatação dos 39 arquivos Python aprovados. Foram conferidos quarenta
hashes dos registros de execução/propriedades, permissões privadas e ausência da
chave da API em todos os artefatos novos examinados. Não restaram arquivos de
mídia ou sessões temporárias no lote.

**Os vinte rótulos de views anteriores e suas datas foram preservados.** A nova
consulta da API é outra observação, em arquivo separado. Dezenove das vinte novas
observações ainda se encontram na janela proposta de 30–37 dias; uma já a excede.
Não substituir o alvo congelado por uma contagem atual com idade diferente.

O manifesto agora contém setor classificado, hash e propriedades para todos os
vinte. Ele preserva a origem de cada classificação e campos ausentes. Novos
procedimentos e artefatos não substituem a seleção ou a fila anteriores.
A fila antiga continua bloqueada segundo seu contrato de revisões; esta execução
direta autorizada não marca aquelas revisões como aprovadas.

## O que está pronto e o que continua pendente

A consulta de metadados e os dezessete downloads solicitados foram concluídos.
A falta de fingerprint/propriedades dos dezessete e a ausência de classificação
dos dezesseis foram tratadas, com as ressalvas explícitas acima.

Ainda não há liberação científica da base: dezesseis idiomas continuam sem
confirmação, há dois casos novos de inclusão e uma revisão humana parcial. A
revisão visual não substitui auditoria de fala/idioma. Nesta rodada nova foram
extraídas propriedades e hashes; **ASR, CLIP e Qwen não foram executados novamente**.
Não houve treino, ajuste de baseline, acesso a teste científico ou chamada ao NIM.

Autorização operacional do aluno, aprovação da plataforma e validade científica
são campos distintos. Permanecem `platform_approval_verified=false`,
`metrics_amendment_submitted=false`, `training_eligible=false` e
`real_results_available=false`; o formulário não foi tratado como condição técnica
para executar o lote expressamente solicitado. A #1 e os critérios reais da #2
continuam abertos pela base/curadoria ainda não liberadas. O serviço Python/MCP
continua no comportamento já verificado: padrão indisponível e modo sintético
explícito, sem servir previsão real a partir deste lote.

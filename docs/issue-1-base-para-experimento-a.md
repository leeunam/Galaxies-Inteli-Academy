# Base liberada para iniciar o experimento A

Checkpoint operacional de 18/10/2026: **200 referências reais de 80 canais**, com
evidências verificadas, partições congeladas e `training_release_available=true`.
O piso combinado de 200 referências/50 canais foi cumprido. A #1 pode ser encerrada
como preparação operacional; **M1 ainda não foi treinado ou servido**. A #3 continua
aberta, assim como a avaliação de qualidade, ranking e calibração.

## Seleção e curadoria

A fila final reuniu 1.396 candidatos de metadados, em um conjunto potencial de
1.451 referências/442 canais. Houve **541 tentativas auditadas**: 522 extrações
concluídas e 19 falhas, preservadas e excluídas (16 por imagem não vertical e três
com código genérico `ValueError`, sem inventar causa mais específica). As revisões
resultaram em 203 inclusões e 338 exclusões; três inclusões ficaram fora pelo teto
de cinco referências por canal. Nenhuma revisão da fila final ficou pendente.

Entre as exclusões, 204 não estabeleceram português no ASR sem idioma forçado;
três apresentaram repetição severa na transcrição. As demais decisões registram
formato, assunto fora do recorte ou evidência insuficiente. Texto/embedding bruto
foi preservado; não houve reparo posterior da fala para conseguir inclusão.

| Setor | Referências | Canais com suporte no setor |
| --- | ---: | ---: |
| Beleza | 112 | 50 |
| Moda | 88 | 42 |
| Total | 200 | 80 únicos |

Doze canais aparecem nos dois setores. Densidade: 35 canais com uma referência,
12 com duas, sete com três, dez com quatro e 16 com cinco. Não houve duplicata de
bytes entre os 200. Um par de publicações visualmente muito semelhante, com ASR
igual, recebeu agrupamento conservador; ambas pertencem ao mesmo canal e à mesma
partição. Identidade integral do conteúdo não foi demonstrada por essa revisão.
Outras republicações editadas não foram automaticamente detectadas.

A descoberta foi ampliada por buscas e pelas playlists oficiais de uploads.
O coletor confere a publicação do vídeo, sem confundir com a data de adição à
playlist, e evita consultar novamente os IDs já observados. Foram 698 chamadas
novas bem-sucedidas de metadados nesta retomada e uma tentativa adicional de busca
sem resultado aproveitado; o erro genérico não permite afirmar sua causa.
Cobertura de histórico foi limitada e registrada, sem alegar censo dos canais.
[Contrato do coletor](coleta-por-canais.md).

A aquisição priorizou novas propostas de canais e canais com conteúdo já
confirmado, antes de qualquer ajuste. Títulos/idioma declarado só propuseram
candidatos; inclusão usou ASR real e quadros amostrados. Não houve ordenação por
views, renovação de rótulo ou mudança do recorte. Os vinte IDs originais de
desenvolvimento ficaram fora. Essa adaptação produz **amostra de conveniência**,
com viés de descoberta, canal e campanha; não é amostragem probabilística nem
avaliação prospectiva independente.

O aluno solicitou ferramentas/IA em lugar de conferir os quatro controles por
escuta. A origem das decisões é `automated_assisted_review`, sem novas escutas ou
anotações humanas. A atribuição pt-BR é assistida e não certifica dialeto de forma
independente. Alegações dos anúncios sobre eficácia ou durabilidade não foram
verificadas. Conteúdo gerado por IA não foi excluído apenas por essa característica.

## Alvo, features e partições

O alvo continua sendo `log1p(views públicas observadas)`, com contagem e instante
originais, quando **30 <= idade < 37 dias**. Não reconstrói views exatamente no
dia 30, audiência orgânica, efeito causal do patrocínio ou viralidade futura.
Propriedades medidas confirmam vídeos verticais de até 60 s.

Os 200 embeddings MiniLM de 384 dimensões e CLIP de 512 dimensões foram conferidos
quanto a dimensão e finitude. O importador recarregou os bytes originais e conferiu
fonte, contagem/datas, descarte, hashes, revisões dos modelos, políticas e partições.
As entradas de A contêm somente setor, duração, proporção altura/largura, estado
do texto e embedding da fala. Canal, datas, títulos, URLs, contagens, curtidas e
hashes ficam fora das features. [Contrato completo](issue-1-manifesto-de-treino.md).

| Partição | Referências | Canais | Moda | Beleza |
| --- | ---: | ---: | ---: | ---: |
| Treino | 124 | 48 | 56 | 68 |
| Validação | 45 | 16 | 18 | 27 |
| Teste | 31 | 16 | 14 | 17 |

A divisão por canal/grupo usa o algoritmo existente e seed 42, sem outcomes.
Foi persistida **antes** de ajustar B0/Bcanal. Cada parte contém ambos os setores;
as proporções de vídeos resultam da divisão por canal, sem rearranjo para atingir
60/20/20 exatos. O baseline usa exatamente os 124 IDs de treino, foi recarregado e
recomputado. Não houve ajuste de M1 nem avaliação de desempenho no holdout.

O piloto de doze referências da #2 permanece intacto: os quatro arquivos do bundle
foram conferidos por hash. A coorte ampliada tem seu próprio baseline e suas próprias
partições, que serão reutilizadas em A/B/C. Comparar M1 aos baselines desta coorte,
sem misturar o suporte de treino do piloto antigo com o novo experimento.

## Evidências privadas e reprodução

Diretório local ignorado pelo Git:
`data/private/issue-1-pool-treino-20261018-v6/released-cohort-v1/`.
Contém `records.json`, `predictor-inputs.json`, `evidence-index.json`, configuração,
instrução operacional, protocolo de seleção, relações reconhecidas, coorte,
partições, rótulos exclusivamente de treino, baseline, prontidão e verificações.
O índice aponta para os artefatos privados de features/execução, que devem ser
preservados para reimportação. O bundle de baseline dispensa esses arquivos para
servir B0, mas não os substitui para treinar A.

| Artefato | Checksum interno SHA-256 |
| --- | --- |
| Liberação da coorte | `84a6effc7e64979f4d51244a3c79ab83c6a66569a34510f7d326b57c2813c021` |
| Manifesto de partições | `e17dba24bcb52f824908a54d8f0e3916c05b3cf3f5003e17f2411e6ef2041ea7` |
| Baseline | `2d6664e899b1f54c2232dc1903028b08eab867692a6c3d68017384b18e9fb095` |

Esses checksums identificam o conteúdo normalizado do contrato; não são os hashes
dos bytes formatados dos arquivos. Eles verificam consistência, sem autenticar
direitos ou a correção semântica das anotações.

Com os artefatos privados disponíveis, a demo executa arquivos de entrada gerados
localmente e a referência observada real, sem acessar o teste para avaliar modelos:

```bash
rtk proxy uv run --frozen python -m scripts.demo_creatives \
  --observed-baseline-dir data/private/issue-1-pool-treino-20261018-v6/released-cohort-v1
```

Foram seis respostas iguais entre função Python e cliente MCP stdio real: moda e
beleza, com um, dois e cinco candidatos. A resposta continua identificando baseline
observado e faixa descritiva do treino; previsão aprendida, intervalo preditivo e
preferência entre criativos permanecem indisponíveis. A configuração é explícita
do operador; a presença dos artefatos no disco não habilita resultados sozinha.

## Verificações e limites de liberação

**250 testes passaram**, Ruff e formatação dos 49 arquivos Python aprovados,
lock offline consistente e 130 dependências instaladas compatíveis. Os testes
públicos dispensam a base privada. A conferência real adicional reimportou as 200
referências, comparou as entradas persistidas, verificou todos os vetores,
agrupamentos, IDs de treino, recarga do baseline e preservação do bundle antigo.

A última etapa acrescentou 181 tentativas, 179 concluídas, reaproveitando as 360
anteriores. Soma de 1.772,41 s de sessão, 4,21–21,42 s por sessão; máximo de RSS
reportado de 2.077,21 MiB no processo com pesos cacheados. Medidas operacionais
deste ambiente, sem isolamento de benchmark ou promessa de SLA. **Todas as 541
sessões confirmaram limpeza**; mídia bruta e imagens de revisão da ampliação foram
removidas. Transcrições/evidências estruturadas necessárias permanecem privadas.

As correções e os controles ASR/CLIP/Qwen estão em
[extratores](issue-1-extratores-e-treino.md). Colunas VLM, inclusive close-up e
aplicação, continuam sem aprovação de treino; A não depende delas. CatBoost/LightGBM
foram tecnicamente verificados com dados sintéticos. O NIM Nemotron passou somente
no contrato sintético restrito de cópia de evidências, inclusive brief malicioso;
explicação livre/SHAP continua na #5. Nenhuma mídia, transcrição ou métrica real foi
enviada ao NIM.

A instrução expressa do aluno autoriza operacionalmente a extração e o treino
local; **`platform_approval_verified=false` e aditivo não enviado** permanecem.
Não houve aceite de termos ou aprovação do YouTube obtida por esta execução.
`predictive_quality_validated=false`: volume, esquema válido e hashes não demonstram
acurácia de percepção, generalização ou cobertura dos quantis.

Para a #3: carregar esta mesma coorte/partições, ajustar transformações e quantis
CatBoost somente no treino, escolher ajustes na validação e manter o teste fora
da seleção. Servir a mesma política de extração, com ausências/falhas explícitas,
e comparar com B0/Bcanal deste pacote. A avaliação final permanece na #6.

# Produto v9 — recuperação parcial e auditoria da divergência de propriedades

Conferência de 20/10/2026, após o [adendo autorizado](issue-4-vlm-produto-v9-recuperacao-protocolo.md).
A recuperação completou o caso 34 com uma chamada nova e reutilização byte a
byte dos três raw válidos. A aquisição do caso 42 foi rejeitada pelo guard de
propriedades. A fila foi interrompida sem retry e sua comparação está selada em
**34/64 completos**. Não se concluiu a avaliação, liberou coluna ou iniciou B-VLM.

## O que foi executado

O commit `36bc1e3` contém fontes/testes separados, sem reabrir a fila original.
Antes de operar passaram **667 testes em 422,65 s**, Ruff/formatação de 119
arquivos e revisão independente somente leitura. Plano da recuperação:
`28906785bd57c61cc7fe0dd92d6103e33d6ac5c555e25f99e799608ba8073f90`.

O DNS falhou no sandbox e funcionou fora dele; a execução de mídia foi
autorizada fora do sandbox. Foram registradas nove tentativas de aquisição:
oito concluíram com propriedades, folha, crops e tempos idênticos; a nona
falhou no caso 42. Não houve atualização das métricas ou do alvo da coorte.
Cada vídeo foi removido pela sessão, inclusive o que falhou.

O caso 34 recebeu somente a chamada perdida do frame 4, em 12,667 s. O recibo
nativo registra **10,9413 s e 2.586,31 MiB** amostrados, abaixo dos limites.
Esse frame não participa do produto nos primeiros 3 s; os três raw elegíveis
já estavam preservados. Não atribuir a essa chamada um ganho de percepção
precoce. Os 33 resultados anteriores e o recibo antigo sem resposta não mudaram.

O registro auxiliar inicial usava getters de tempo/RSS incompatíveis e ficou
com dois campos nulos. Foi arquivado byte a byte e corrigido para os campos
nativos `runtime_seconds` e `runtime_peak_rss_mib`, com vínculo por hash.
Nenhuma resposta nativa ou contador foi alterado para corrigir esse registro.

## O que os recibos permitem concluir sobre o caso 42

A falha é `revision_frozen_properties_mismatch`, na comparação exata do
dicionário em `vlm_revision.acquire_row`, antes da criação de folha/crops.
`run.json` registra falha, fingerprint do download e limpeza confirmada, mas
não registra as propriedades recém-decodificadas. `features.json` não existe:
`run_session` só o grava se o extrator retornar. **Não há evidência para dizer
qual propriedade divergiu, sua magnitude ou sua causa exata.**

O arquivo baixado difere em bytes da aquisição v9 anterior. Isso não distingue
mudança do conteúdo de alteração de contêiner/formato ou erro: **todos os oito
downloads bem-sucedidos também diferem em bytes**, embora reproduzam os pixels
e tempos congelados. Não foi demonstrada mudança de pixels no caso 42, pois o
guard parou antes dessa verificação. Não foi demonstrado um erro específico de
implementação. Fontes e versões preservadas, além dos casos bem-sucedidos,
sustentam apenas que o guard operou conforme implementado.

Diagnosticar a diferença exige autorização específica para outra aquisição do
caso 42 e novo instrumento que persista propriedades atuais antes de comparar.
Não relaxar igualdade, recortes, resolução, tempos ou requisitos perceptivos;
não substituir a referência nem tentar formatos alternativos automaticamente.

## Comparação nos mesmos 34 casos completos

São 25 do grupo antigo e nove do grupo já revelado, todos treino; 21 beleza e
13 moda, 26 positivos e oito negativos. Não são 64 avaliados nem holdout novo.
Os controles estruturados continuam 12/12 corretos em cache; não foram repetidos.

| Produto / mesmos 34 | A/v7 | v8 | v9 |
| --- | ---: | ---: | ---: |
| Conhecidos / unknown | 34 / 0 | 34 / 0 | 34 / 0 |
| true / false previstos | 28 / 6 | 34 / 0 | 26 / 8 |
| Acertos de valor | 28 | 26 | 26 |
| Acertos de valor+frames | **26** | 22 | 25 |
| Evidência sem suporte, casos | 2 | 4 | 1 |
| Negativos corretos | 4 | 0 | 4 |
| Falsos positivos | 4 | 8 | 4 |
| Falsos negativos | 2 | 0 | 4 |

v9 ganha oito e perde cinco acertos compostos frente a v8 (saldo +3); ganha
quatro e perde cinco frente a A/v7 (saldo −1). Não há ganho geral demonstrado
sobre A/v7. No piloto, v9 mantém 11/16; nos outros 18 completos, 14/18.
B/v7 só é comparável nos mesmos 25 antigos: 18 acertos compostos, contra 20
de A/v7 e 19 tanto de v8 quanto de v9. Não comparar 18/25 com totais de 34.

Pessoa/texto permanecem idênticos ao cache v8. Gates dos dois grupos de 32 não
foram calculados; `released_fields` e `fields_ready_for_future_blind_audit`
estão vazios. Nenhuma auditoria nova, treino ou promoção de modelo ocorreu.

## Orçamento e estado observado em leitura

| Contador | Consumido nesta recuperação | Cumulativo | Teto autorizado |
| --- | ---: | ---: | ---: |
| Tentativas de aquisição | 9 (8 completas, 1 falha) | 255 | 277 |
| Reservas nativas | 1, completa | 1.638 | 1.758 |
| Tempo de sessões contabilizado | 52,4886 s | 34.491,6163 s | 97.200 s |

A contabilização preserva integralmente a base conservadora anterior. Sem
retry extra, inferência dos outros casos ou aumento de limite. Há **oito folhas
presentes**, com SHA conferido; sete correspondem a casos ainda não inferidos.
Zero vídeos/sessões temporárias `galaxies-*` e zero workers ativos. A orientação
posterior solicitou somente auditoria em leitura: não houve exclusão ou alteração
de fila nessa auditoria. O descarte das folhas continua pendente.

Uma continuação que pudesse reutilizar as sete folhas ainda válidas exigiria
23 aquisições adicionais (casos 42–64), uma exceção explícita para o caso 42 e
teto cumulativo **278**, uma tentativa além do aprovado. As 120 chamadas dos
30 casos restantes caberiam no teto nativo atual. Isso é aritmética condicional,
não execução autorizada ou garantia de recuperar os mesmos pixels. Após descarte
das folhas, seriam necessárias 30 aquisições, total 285. Qualquer continuação
precisa de novo adendo, proveniência separada e validação antes de operar.

## Evidência e preservação

Pasta privada: `data/private/issue-4-vlm-produto-v9-recuperacao-v1/`. Os recibos
de preflight/viabilidade/implementação foram congelados no plano. O run falho,
`acquisition-failure-verification.json`, `first-recovered-case-verification.json`
e `paired-product-analysis.json` preservam os fatos da execução e comparação.

SHA lógico da comparação:
`0a76d69750b5d8b46774717b50552b69d473bfb282ac190d60d84864155a6f1f`.
SHA do arquivo de comparação:
`bd0b8b95beaf9019a157f7b101ecc5a886a115cdc7142115511850e526795bd2`.
Checkpoint observado:
`bff118743b9f2135dae6b9402f7a70b53f9baef9e0741a610bb6de4d2193f7bc`.

A auditoria conferiu **542 arquivos antigos/herdados**, as seis fontes/testes/
protocolo novos e todas as versões instaladas. A revisão independente reproduziu
o estado, os recibos e as métricas parciais. A fila original continua selada com
33 resultados; a nova comparação reúne 34, sem substituir o relatório antigo.
Partições 203/66/31, anotações, M1/A200, A300, B-cache, serviço/MCP, `uv.lock`
e teste reservado permanecem intactos. Não houve chamada NIM ou nova dependência.

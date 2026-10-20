# Produto v10 — ganho parcial e parada antes da fase 2

Execução de 20/10/2026 do [protocolo aprovado](issue-4-vlm-v10-protocolo.md).
A v10 acertou **12/12 controles** e **5/8 casos preservados**, contra 3/8 da
v9 nesses mesmos casos. Houve dois ganhos e nenhuma perda, mas não atingiu
os **8/8 exigidos para continuar**. A fila foi selada com
`v10_preserved_quality_failed`, antes de qualquer aquisição ou chamada da fase2.
Nenhuma coluna foi liberada; não houve auditoria nova, treino B/C ou promoção.

## Implementação e identidade experimental

A única mudança de instrução foi acrescentar o parágrafo aprovado sobre
apresentação de roupa vestida ao prompt estruturado v9. Schema, ordem dos
estados/exemplos, parser, categorias, mapper, OR e produto ≤3 s ficaram iguais.
Permaneceram Qwen3-VL-2B Q4_K_M, projetor Q8_0, runtime b11716, CPU4,
temperatura0, seed42, saída64 tokens e limites visuais solicitados64/128,
sem medir tokens visuais efetivos. Não houve instalação ou alteração de lock.

As oito folhas e os 32 crops reproduzem os hashes e tempos dos caches anteriores.
Os 12 controles foram reconstruídos com a receita/fonte anterior e hashes
idênticos. Cada resposta foi preservada antes do parser; todas as44 chamadas
concluíram válidas, sem falha operacional, reparo ou retry. A reserva e o
checkpoint foram sincronizados antes de cada chamada, com recibo exclusivo.

O commit `f4f8e28` registra extrator/testes/protocolo; `2fca906` registra fila,
contadores, testes e comparação. As seis fontes/testes/protocolo do plano
permaneceram byte a byte iguais desde a primeira chamada. A implementação
aditiva não modifica os extratores ou as filas v9 seladas.

## Comparação nos mesmos oito casos

São oito casos de treino já revelados, todos positivos de moda. A composição
vem das folhas preservadas, não de uma nova seleção independente. As anotações
assistidas anteriores ficaram imutáveis; não são certificação humana.
Acerto composto exige valor correto, pelo menos um frame citado e todos os
índices citados contidos na anotação, conforme o contrato anterior.

| Extrator perceptivo / mesmos oito | Conhecidos / unknown | true / false | Valor+frames corretos | Índices sem suporte |
| --- | ---: | ---: | ---: | ---: |
| v10 | 8 / 0 | 5 / 3 | **5/8** | 0 |
| v9 em cache | 8 / 0 | 3 / 5 | 3/8 | 0 |
| v8 em cache | 8 / 0 | 8 / 0 | 8/8 | 0 |
| A/v7 em cache | 8 / 0 | 8 / 0 | 8/8 | 0 |
| B/v7 em cache | 8 / 0 | 8 / 0 | 8/8 | 0 |

B/v7 possui cache para os oito efetivamente avaliados; esta tabela não usa
seu denominador de13 no painel máximo planejado de20. A/v7 e B/v7 são
comparadores perceptivos, distintos de A200/A300/B-cache preditivos.
Os 8/8 de v8 neste grupo exclusivamente positivo não demonstram especificidade:
ela respondeu true nos64 da [rodada anterior](issue-4-vlm-v8-resultados.md),
inclusive nos oito negativos. Os 12 controles sintéticos atuais também não
medem especificidade em vídeos reais. A fase2 não foi executada; não existem
vinte resultados v10 nem comparação v10 nos64.

As três respostas corretas de v9 foram preservadas. Entre as cinco folhas
descritas exploratoriamente como roupas vestidas, v10 recuperou duas: saia e
vestido. As outras três continuam false. Essa classificação visual foi feita
após os resultados anteriores e não constitui novo GT dos subestados.

## O que mudou por frame e o que continua falhando

| Estados nos24 frames ≤3 s | v9 | v10 |
| --- | ---: | ---: |
| presented_target | 7 | **11** |
| incidental_only | 17 | **13** |
| no_target / uncertain | 0 / 0 | 0 / 0 |

Quatro estados mudaram de `incidental_only` para `presented_target`, dois em
cada caso recuperado; os sete positivos anteriores foram mantidos. Nos três
falsos negativos restantes, os nove frames iniciais continuam `incidental_only`.
Há outros quatro frames false em vídeos cujo valor final é true; o OR não
exige recuperar todos os frames positivos para acertar o vídeo.

A v10 emitiu dois positivos tardios nos oito frames >3 s. Um deles pertence
a um dos falsos negativos iniciais e foi corretamente excluído da decisão.
Não se deslocou a janela nem se usou outro frame para reparar a resposta.
A reconstrução das44 respostas, parsers e agregações reproduziu os resultados;
não identificou falha de conversão ou alinhamento temporal nesta rodada.

A inserção ajudou parcialmente no reconhecimento de roupas vestidas, mas
não resolve a distinção de apresentação nos frames iniciais. Não foi isolada
uma causa interna do modelo, quantização, resolução ou uma frase específica.
Categorias e testemunhas por item continuam sem anotação própria; acerto do
atributo composto não certifica essas subdecisões. Não houve retuning após
observar as respostas.

## Consumo e encerramento

| Contador herdado | Novo | Cumulativo | Máximo desta autorização |
| --- | ---: | ---: | ---: |
| Reservas nativas | **44**, todas completas | **1.710** | 1.758 |
| Aquisições | **0** | **256** | 268 |
| Tempo de sessões | **625,4130 s** | **35.417,7171 s** | 36.592,3041 s |

As chamadas nativas somaram 619,0262 s. A maior levou 20,3061 s; o maior RSS
amostrado foi **2.607,95 MiB**, abaixo do teto de 3,3 GiB. Os demais segundos
contabilizados são preparação dos inputs, gravações e verificações dentro
das operações. Esses contadores não medem toda a duração do trabalho/testes.

Não foi consumida a reserva restante de48 chamadas/12 aquisições. Ela não
autoriza outra variante ou uma nova tentativa. O estado selado recusou a
pré-condição de execução sem alterar o checkpoint; essa conferência foi pura,
sem chamar novamente o executor ou qualquer callback nativo/de rede.

Permanecem **oito folhas antigas íntegras**, zero imagens novas e zero sessões
temporárias. O journal de descarte é vazio e concluído, pois não houve aquisição.
Não há workers VLM/NIM/explicação no host ao terminar. Runtime e pesos foram
reconferidos em leitura contra o arquivo oficial em cache, sem extração,
reinstalação ou consulta externa. Zero NIM/API de inferência externa nesta unidade.

Os **735 hashes herdados e seis fontes congeladas** conferem, assim como as
130 distribuições raiz/42 isoladas. M1/A200, A300, B-cache, serviço/MCP,
anotações, partições203/66/31, filas e recibos anteriores permanecem iguais.
O teste reservado ficou fechado, sem features, rótulos, previsões ou métricas.
README não rastreado não foi lido, editado ou versionado.

## Verificação e consequência para o escopo

Passaram **52 testes direcionados em 10,88 s** e **802 testes completos em 604,68 s**
no código final, antes da execução real. Ruff/formatação dos 158 arquivos e
diff passaram. Os testes incluem ambas as fases simuladas, gates, persistência
antes de operar, prazo compartilhado, tentativa incerta, Unicode/JSON inválido,
tampering de source/recibo/contador, comparação parcial e recuperação do descarte.
As fontes mantiveram os mesmos hashes após a suíte e durante/depois do run.
Esta unidade teve revisão local de código/escopo; não se atribui uma nova
revisão independente ou auditoria cega a essa verificação.

O VLM continua **sem liberação para treino**. O resultado não sustenta iniciar
outra auditoria cega. A orientação de cumprir B/C com VLM aprovado permanece;
não foi adotada redução para C-cache. A
[investigação anterior](issue-4-vlm-pos-v9-investigacao-e-proposta.md) separa
também insuficiência de classes dos erros perceptivos: não mudar o gate ou
fabricar false para obter suporte. Qualquer correção seguinte deve ter versão,
hipótese e orçamento próprios antes de novas chamadas. As três falhas já
reveladas são evidência de desenvolvimento, não uma amostra para certificar
a próxima correção. Nenhum treino B/C, promoção ou seleção nova foi iniciado.

Recibos privados: `data/private/issue-4-vlm-v10-v1/` (plano, checkpoint,
44 reservas/raw, resultados, comparação e journal) e
`data/private/issue-4-vlm-v10-verificacao-v1/` (pré-flight, suíte, comparadores,
plano congelado, reconstrução, preservação e conferência do host/ambientes).

- Plano lógico: `debef0006a3484e9aa6835d599d64b4819fd0075fb5dc8cfaad463b764aba59f`.
- Configuração/fontes: `cf44b769c45f37f277ac878747cd28f7cf9357cf9b70fecfc5b41f87d34b84cd`.
- Comparação lógica: `f55a667aeef5f2c18c063253d1db045fbcb9e7f0d30f1db40ac83eb98c166111`.
- Arquivo de comparação: `b86f19ecf0feac357ee79299ec188fb2fedb98b4135f10c1b0c3e9a7485d667e`.
- Checkpoint selado: `03f1037d74ddaa45c020ef8d43b5e8f681f294ccec20439e2e98cd579165a4f6`.

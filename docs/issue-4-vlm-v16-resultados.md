# V16 — ordem altera os negativos, sem condição aprovada

Diagnóstico do [protocolo V16](issue-4-vlm-v16-protocolo.md), com
[preflight nativo](issue-4-vlm-v16-preflight.md) e a
[correção anterior ao despacho](issue-4-vlm-v16-pre-dispatch-v2.md).
A rodada foi selada após **24 chamadas válidas e zero aquisições**:
`v16_neither_condition_passed_negatives`.

| Mesmos12 controles negativos | false correto | true | unknown | Gate12/12 |
| --- | ---: | ---: | ---: | --- |
| item_first | **0/12** | 12 | 0 | Reprovado |
| state_first | **11/12** | 0 | 1 | Reprovado |

**Onze ganhos e zero perdas** de state_first nos12 pares. O controle de linhas
permaneceu incorreto, agora como unknown, e não foi convertido em false por
código. Nenhuma condição atingiu12/12 false; por isso **nenhum dos cinco crops
positivos foi executado**. O denominador positivo é zero, não0/5 acertos.
Nenhuma candidata ao próximo desenvolvimento foi indicada, nenhuma coluna
liberada e nenhuma auditoria, treino B/C ou v17 iniciada. As dez chamadas
restantes deste orçamento ficaram encerradas, sem reaproveitamento.

## O que o contraste demonstra

O prompt comum, os22 objetos semânticos, categorias, ordem dos ramos, listas
required, projeção, modelo/runtime/parâmetros e pixels foram iguais nas duas
condições. Mudou a serialização das propriedades: item_configuration→state
contra state→item_configuration, mantendo presented_categories por último.
As gramáticas nativas confirmaram essa diferença, sem normalizar a ordem.
Cada controle foi processado uma vez por condição, alternando a primeira
condição em seis pares para cada lado. Não houve novo exemplo, retuning ou
substituição depois das respostas.

Sob esse prompt comum, a ordem influenciou as respostas observadas neste painel
sintético:12 true passaram a11 false e um unknown. A projeção e o booleano foram
reconstruídos dos raws; a diferença já estava nas declarações nativas, sem
reparo ou mudança do agregador. Isso não demonstra a cadeia interna de
raciocínio, nem qualidade em vídeos reais, beleza ou todos os tipos de produto.

**Não isola a causa histórica v14→v15**: o prompt comum removeu a instrução
histórica de ordem do v15. O braço item_first permaneceu com0/12 false, mas seus
raws não são todos idênticos aos históricos: duas categorias mudaram. Tampouco
se mediu sensibilidade em positivos, pois o gate bloqueou essa etapa. A melhoria
nos negativos não basta para indicar candidata ou liberar atributos.

## Declarações nativas e erro remanescente

| Configuração nativa | item_first | state_first |
| --- | ---: | ---: |
| isolated_physical_item | 7 | 0 |
| isolated_graphic_item | 5 | 0 |
| incidental | 0 | 6 |
| absent | 0 | 5 |
| unclear | 0 | 1 |

Item_first declarou12 presented_target: quatro garment e oito cosmetic, todos
projetados para isolated_display/true. São produtos inexistentes nas fixtures,
inclusive garment isolado nos controles totalmente branco e preto. O v15
histórico também tinha12 true e as mesmas contagens7/5 de configurações, mas
seis garment/seis cosmetic. No prompt comum, text-14-160-250 e lines passaram
de garment para cosmetic. Não se apresenta igualdade agregada como replay
literal ou como isolamento do efeito da troca de prompt.

State_first declarou seis incidental_only e cinco no_target, todos com lista
vazia e false. O gate testa o booleano, sem certificar essa distinção fina,
que não recebeu novo gabarito. No controle **lines**, o raw declarou:
`state=uncertain`, `item_configuration=unclear`, `presented_categories=[]`.
A projeção produz cue uncertain e valor unknown corretamente. A fixture é
negativa; unknown falha no critério predefinido. Não foi repetida a chamada,
trocado o controle ou alterado o limiar para obter12/12.

Os cinco positivos continuaram com os mesmos hashes e anotações admissíveis:
quatro cabides e uma barra puxada, com alternativas isolated já explícitas na
inspeção congelada. São cinco crops de três vídeos já revelados. Nenhuma
resposta positiva V16 ou revisão nova foi fabricada para completar um gate.
As ambiguidades anteriores e o GT legado permanecem intactos.

## Implementação, revisão técnica e passagem antes de gerar

A branch `codex/issue-4-v16-ordem-serializacao` nasceu em `9c4177a`, preservando
a integração #5 e a branch v15 em `69a5832`.

- `340fc7c`: dois contratos ordenados, prompt comum, gate nativo, testes/protocolo.
- `c911761`: executor pareado, gates e liberação técnica vinculada ao plano.
- `c0ab791`: checkpoint inicial de preflight, antes de qualquer geração.
- `6c5618e`: correção das falhas de startup e substituição pré-despacho.

O plano inicial a1120d46…62dc nunca recebeu clearance e permanece com zero
operações/chamadas/aquisições. Seus plan.json e checkpoint.json são byte a byte
iguais aos originais; o marcador aditivo superseded-v2.json torna a fila inativa.
Os30 arquivos de prova anteriores foram inventariados e conservados por hash.
A nova fila v2 é o único caminho efetivo: preparação, carregamento e cópias em
outro namespace são verificados. Os limites não foram somados em dois orçamentos.

O P2 apontado na revisão foi corrigido antes do despacho: no_workers e
verify_runtime continuam obrigatórios, agora dentro do tratamento terminal após
a liberação técnica. As falhas selam a rodada sem retry; ausência de clearance
permanece recusa inerte. Passaram **39 testes finais em30,62 s**, incluindo as
duas falhas de startup, esgotamento antes da reserva, timeout depois da reserva,
consumo de180 s no relógio falso e recusa de namespace/cópia. São simulações,
sem consumo real VLM. O checkpoint anterior registrou171 testes em72,25 s;
não se somam as execuções sobrepostas como uma suíte nova. Ruff e formatação
dos222 arquivos Python passaram. Nenhum código mudou depois desses checks.

O supervisor revisou o commit final e liberou explicitamente **uma rodada** no
plano52a1248c…c973, configuraçãof281fc63…3fa7. O read_thread do executor expôs
o registro real recebido, item de mensagem
`fco_01a15b9f-bb01-7ab0-b38c-b85f33cf054b`, com source_thread_id do supervisor.
O texto literal foi extraído do input completo, sem truncamento ou reescrita,
e guardado com a origem; hash4d511fb5…b339. O recibo foi registrado pelo CLI
selado, com fsync e vínculo ao plano/configuração, **antes da primeira chamada**.
O registro da fila inicial não foi preenchido retroativamente.

## Preflight real preservado

Fontes do gate gramatical intactas; recibos reutilizados após a correção, sem
recompilar/retokenizar ou gerar novamente. Em **13.703 sondas por condição**, zero
divergências:13.640 objetos finitos,22 whitespace,19 mutações e22 objetos válidos
na ordem oposta, todos estes recusados. Cada gramática aceita os mesmos22 objetos
na própria ordem, e suas gramáticas são distintas. CLI e ponte usam as mesmas
bibliotecas b11716 verificadas contra o arquivo oficial em cache.

Tokenizer offline:88 serializações,17–32 tokens em item_first e17–29 em
state_first, máximo33 com término dentro de64. Captura do comando original com
Popen stubado confirmou argv normalizado idêntico e schemas realmente escritos
nas duas ordens. Esse recorder e o gate por caracteres não são provas visuais.

Qwen3-VL-2B Q4_K_M, mmprojQ8_0, b11716, CPU4, seed42, temperatura0, contexto3072,
saída64 e limites visuais solicitados64/128, iguais aos aprovados. Projeção com
origem derivada da declaração do modelo; não uma observação independente.
Todos os24 raws reais foram aceitos integralmente, na ordem correspondente,
com categoria/estado/configuração coerentes. Zero falhas operacionais, reparos,
retry, truncamento ou reservas novas incertas.

## Encerramento, consumo e preservação

| Contador | Novo | Cumulativo | Teto desta autorização |
| --- | ---: | ---: | ---: |
| Reservas nativas | **24**, todas completas/válidas | **1.835** | 1.845 |
| Aquisições | **0** | **256** | 256 |
| Sessões cobradas | **523,9346 s** | **37.568,2420 s** | 38.244,3074 s |

Os24 nativos somam511,6960 s, máximo22,6870 s por chamada. Pico RSS2.611,96 MiB,
abaixo de3,3 GiB. O orçamento efetivo foi único; a fila inicial consumiu zero,
a ativa24 e as dez restantes foram encerradas. As32 antigas da v15 continuam
encerradas; a reserva incerta histórica v13 e seus180 s continuam consumidos,
sem repetição ou preenchimento de resposta faltante.

Reconstrução somente em leitura conferiu os resultados, ordenação, raw→nativo→
projeção→valor, scores e pares. A reentrada na fila selada foi recusada sem
invocar o modelo ou modificar o checkpoint. Não se abre outra rodada pelo saldo.

Conferem **1.388 pins anteriores** (1.345 da integração e43 fontes/recibos novos),
**1.423 pins do plano efetivo** e nove fontes. Permanecem iguais os30 arquivos
de prova iniciais, o plano/configuração ativos e as cinco anotações positivas.
As oito folhas antigas continuam presentes;32 crops reproduzidos em memória
antes/depois com hashes/tempos iguais. Só fixtures negativas foram processadas
pelo VLM; nenhum vídeo adquirido, folha nova ou mídia real avaliada nesta rodada.
Crops/schemas temporários removidos e nenhum worker VLM restante.

Ambientes raiz130/isolado42 distribuições iguais; runtime/pesos reconferidos em
leitura, sem instalação/sync. M1/A200 e seus três modelos, A300, B-cache e a
integração #5 Python/MCP/StateGraph preservados. Partições **203/66/31** sob guardas
200/300, holdout31 sem leitura semântica de features/rótulos/previsões/métricas.
M1 continua final_test_evaluated=false. README e briefing pinado intactos.
Sem NIM/API, credenciais, download, publicação, push ou deploy nesta unidade.

Recibos em `data/private/issue-4-vlm-v16-verificacao-v1/`; execução exclusivamente
em `data/private/issue-4-vlm-v16-v2/`. O namespace inicial permanece aposentado
com suas provas, sem apagar a preparação que precisou da correção.

- Plano efetivo: `52a1248c9118f9ea8f92990521177019a7b2effa79ef2f6b559737338a10c973`.
- Configuração: `f281fc63317da538ec52546cec8799af666276d52d7a2f1b6dd4281aec773fa7`.
- Preflight lógico: `db04df2c8b53d996a8bacba46135aa01be5a9f1c56b420fc06bef9aeac497555`.
- Mensagem literal de revisão: `4d511fb5eb7a4b4b2aab5740ef70e3542b2b62cf02a46face9daca8ce3ddb339`.
- Arquivo do clearance: `5db80d6c20f5450bd783f4947526a518ed2a5784117720c26cfda3b7794ec213`.
- Comparação lógica: `4926d3fc5cad840905de83bd0783553f5d770df6b223c0bdc897e43ba8e0766f`.
- M1 preservado: `9dd1c7a2e35e32cf3068395ed8bf2e0561aa4fecded5c31754f981cc13d70d59`.

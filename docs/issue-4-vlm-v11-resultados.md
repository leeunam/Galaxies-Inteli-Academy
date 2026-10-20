# Produto v11 — falha nos controles e parada antes dos vídeos

Execução de 20/10/2026 do [protocolo v11](issue-4-vlm-v11-protocolo.md),
autorizado após a [investigação da v10](issue-4-vlm-pos-v10-investigacao-e-proposta.md).
A v11 retornou false em **1/12 controles negativos**; os outros onze receberam
true. A fila foi selada em `v11_controls_quality_failed`, após concluir o
bloco de controles, com **12 chamadas e zero aquisições**.

Os oito vídeos preservados e a fase2 **não foram executados**. Não há resultado
v11 nos três erros antigos, nos oito vídeos ou no painel de 20. Nenhuma coluna
foi liberada; não houve nova auditoria cega, treino B/C ou promoção do M1.

## Implementação congelada e verificação anterior às chamadas

O commit `9c87aaf` contém extrator, contrato/testes e protocolo. O commit
`1734f5d` acrescenta fila, linhagem, reservas, comparação e revisão de pistas
vinculada aos resultados. A implementação é aditiva: fontes e filas v9/v10
ficaram iguais. A inspeção assistida dos 32 frames antigos foi registrada
separadamente antes de congelar o plano, sem substituir anotações anteriores.

A v11 substitui a instrução acumulada por instrução coesa e acrescenta
`presentation_cue` aos estados/categorias v9. O parser recusa contradições,
incluindo `worn_detail_focus` sem categoria garment; o mapper, OR e produto
≤3 s permanecem iguais. O novo enum não é certificação de suporte visual.
O fluxo pausa para revisar todas as pistas positivas antes de permitir
aquisições; uma fase com valores corretos mas pistas falsas também não avança.
Essas duas fases e suas paradas foram verificadas com fixtures inventadas.

Passaram **105 testes direcionados em 28,92 s** e **876 testes completos em 541,02 s**,
uma execução completa no código final antes das chamadas reais. Ruff passou e
os 165 arquivos Python estão formatados. A checagem global do formatador também
apontou um exemplo Markdown antigo em `docs/issue-2-baseline-observado.md`, que
permaneceu intacto; a aprovação de formatação aqui se refere às fontes Python.
Revisão local de contratos, diferenças em relação à v10, escopo e recibos;
não se atribui nova revisão independente ou auditoria cega à unidade.

Sem geração, o tokenizador local offline contou22–41 tokens em sete exemplos
representativos de JSON, incluindo quatro categorias e cada pista positiva,
abaixo do limite 64. Isso não garante limite para whitespace arbitrário; uma
saída truncada ou inválida continuaria causando parada sem reparo. As 12
respostas efetivas foram completas e válidas. Não houve falha operacional,
retry, fallback ou ajuste após observar respostas.

## Resultado nos mesmos controles

Os controles são os mesmos oito quadros de texto e quatro fixtures visuais
simples, todos sem item-alvo. Receita, fonte, pixels/hash e tempo conferem com
os caches anteriores. Cada chamada recebeu somente um PNG RGB320×330.

| Extrator / mesmos12 controles | false correto | true incorreto | unknown |
| --- | ---: | ---: | ---: |
| **v11** | **1/12** | **11** | **0** |
| v10 em cache | 12/12 | 0 | 0 |
| v9 estruturada em cache | 12/12 | 0 | 0 |
| v8 em cache | 0/12 | 5 | 7 |

False é o valor esperado; unknown não conta como acerto. Isso é um contraste
em controles sintéticos negativos, não estimativa de especificidade em vídeos
reais. A/v7 e B/v7 não entram nesta tabela sem cache para os mesmos controles.
As comparações pareadas em vídeos do relatório têm denominador **zero** para
v11, não zero acertos em oito ou vinte. Não comparar o 5/8 anterior da v10 a
uma avaliação v11 de vídeos que não aconteceu.

O único negativo correto da v11 foi o quadro preto. Ela respondeu
`presented_target` nos oito controles com texto, no quadro branco, nas linhas
e nas formas. Emitiu:

- **9 `held_display`**, incluindo o quadro branco;
- **2 `worn_detail_focus`**, ambos em controles de texto;
- **1 `absent`**, com estado `no_target`, no quadro preto.

Dez dos onze positivos citaram garment; o controle de formas citou cosmetic
e accessory. Não houve `incidental_only` ou `uncertain`. As 11 pistas positivas
não têm suporte nas fixtures negativas. Os recibos privados registram essa
constatação separadamente; não se criou revisão de fase1 sobre oito vídeos
não executados, nem se reabriu a fila para acrescentá-la.

Reconstruímos as 12 respostas a partir dos raw/recibos, conferindo hashes,
parser, intermediários, mapper e agregação. Os positivos já estavam no raw;
não nasceram de truthiness, índice incorreto, janela temporal ou reparo.
A reconstrução dos comparadores também conferiu identidade dos inputs.

O candidato regrediu no reconhecimento de ausência e mostra que um enum de
pista formalmente válido pode ser alucinado junto com o item. Instrução e
schema mudaram conjuntamente: o resultado não isola efeito de uma frase,
ordem, ausência de exemplos, pesos, quantização ou resolução. Não houve
ablação adicional. Não há evidência nesta rodada para afirmar recuperação
ou agravamento das três falhas reais da v10.

## Consumo e encerramento

| Contador | Novo | Cumulativo | Teto desta autorização |
| --- | ---: | ---: | ---: |
| Reservas nativas | **12**, todas completas | **1.722** | 1.802 |
| Aquisições | **0** | **256** | 268 |
| Sessões | **146,9398 s** | **35.564,6569 s** | 37.217,7171 s |

O runtime nativo somou 145,4273 s; a maior chamada levou 12,6775 s. O maior
RSS amostrado foi **2.590,60 MiB**, abaixo de 3,3 GiB. O restante do tempo de
sessão inclui preparação/gravações/verificações das operações. Suíte e revisão
não são contabilizadas como inferência ou runtime nativo.

O saldo de 80 chamadas/12 aquisições ficou encerrado; não autoriza outro
prompt, modelo ou tentativa. A pré-condição pura `runnable` recusou o estado
selado sem modificar seu checkpoint; não se chamou novamente o executor.
O journal de descarte é vazio e concluído, pois nenhuma imagem nova de vídeo
foi adquirida. Nenhum recibo ou arquivo da fila antiga foi alterado.

## Preservação e consequência

Os **867 arquivos herdados** e os 869 pins do novo plano conferem antes/depois,
assim como as oito fontes/testes/protocolo congelados. As oito folhas antigas
continuam presentes, sem alteração, remoção ou movimento; os 32 crops foram
reproduzidos em memória com hashes idênticos. O plano mantém os tempos antigos.
Zero sessões temporárias e nenhum worker VLM/NIM/explicação ao terminar.
Runtime/pesos foram reconferidos em leitura contra o arquivo oficial em cache,
sem extração, reinstalação ou rede. Ambientes raiz 130/isolado 42 distribuições
ficaram iguais. Zero NIM ou API externa de inferência.

Partições 203/66/31, teste reservado fechado, M1/A 200 servido, A 300, B-cache e
serviço/MCP preservados. Não se abriram features, rótulos, previsões ou métricas
do teste. README não rastreado não foi lido, editado ou versionado.

A v11 **não está pronta para outra auditoria cega**. A orientação de cumprir
B/C com VLM aprovado permanece; este resultado não libera coluna, não altera
o gate e não reduz o escopo para C-cache. Outra correção exige hipótese e
protocolo próprios, usando os controles/casos já revelados para desenvolvimento.
Não se aproveitou o saldo desta fila para tentar v12 ou outra configuração.

Recibos privados em `data/private/issue-4-vlm-v11-v1/` (plano, checkpoint,
12 reservas/raw/resultados, comparação e descarte) e
`data/private/issue-4-vlm-v11-verificacao-v1/` (pins, inspeção prévia por frame,
tokenização sem inferência, suíte, configuração, reconstrução/comparação dos
controles e conferência final).

- Plano lógico: `2e7811d45342016ce6d37405437e070bbfca2ec91c3755a4211078b0c2507121`.
- Configuração: `07a4ba538cdd714a91c602d295ef99b33b21ede21f744f3ce173ec72e5a3332e`.
- Inspeção prévia: `8bcd045c71733de2a0265dbd5044505482d9d2acdd44464d5cc6a8de19780905`.
- Comparação lógica: `d385e94593b42ba0bc0b9b2b1ee68e055fcec79cf220c5c0b08f4c5aa97c2ad0`.
- Arquivo da comparação: `11ecd736e87ebee15bbfa38ef939e1ddf0fa9e99b69e41c7f31dfe070cca1552`.
- Checkpoint selado: `0e9eec7204db4f154c5c09ae45bf1b561024f8276963785a9f2ab73ad75144fa`.

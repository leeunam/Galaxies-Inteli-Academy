# Produto v12 — implementação das três variantes e execução interrompida

Execução de 20/10/2026 do [protocolo v12](issue-4-vlm-v12-protocolo.md),
autorizado a partir da [proposta pós-v11](issue-4-vlm-pos-v11-investigacao-e-proposta.md).
R, E e RE foram implementadas e verificadas. A execução real parou na primeira
chamada de R por contradição entre estado e pista. A matriz ficou incompleta;
**E e RE não foram executadas**, nenhuma variante foi selecionada e nenhum vídeo
foi avaliado. A fila está selada em `v12_operation_failed_ValueError`.

## Código congelado e verificações anteriores à execução

O commit `18000c1` contém os três contrastes, testes do extrator e protocolo.
O commit `747909a` acrescenta fila, matriz completa, seleção determinística,
reservas, comparação e revisões de pistas. A implementação é aditiva; mantém
fontes e filas anteriores. Cada prompt corresponde ao rascunho aprovado.

R reordena as definições; E acrescenta os quatro exemplos; RE combina ambos.
Schema, enums, categorias, decoder v11, mapper, OR, janela de produto ≤3 s,
runtime, pesos, hiperparâmetros, pixels e tempos ficam iguais. O decoder exige
compatibilidade entre estado, categorias e pista. Não há reparo/retry/fallback.

A fila distingue falha perceptiva, que permite terminar os 36 controles, de
falha operacional/contratual/identidade, que interrompe imediatamente e impede
seleção parcial. Com matriz completa, só 12/12 false qualifica, na prioridade
R→E→RE. Os oito vídeos antigos e as 12 reaquisições têm os gates adicionais de
valor+frames e suporte visual das pistas previstos no protocolo.

Antes da chamada real passaram **145 testes direcionados em 62,74 s** e
**947 testes completos em 637,66 s**, uma execução completa no código final.
Ruff passou; os 172 arquivos Python estão formatados. A revisão local conferiu
diferenças em relação à v11, contratos, identidade da variante em cada recibo,
seleção, orçamento, fases e escopo. Não se atribui revisão independente ou
auditoria cega à unidade. Não houve alteração de código após essas verificações.

## Falha observada e alcance da comparação

A reserva 1 executou R sobre `text-14-0-8`, primeiro controle sintético negativo,
com PNG RGB320×330 idêntico ao congelado e tempo 0,2 s. A resposta completa foi:

```json
{
  "state": "no_target",
  "presented_categories": [],
  "presentation_cue": "incidental"
}
```

A sintaxe JSON e os valores individuais dos enums são válidos. A combinação
é inválida: `no_target` exige `absent`; `incidental` corresponde a
`incidental_only`. O decoder herdado lançou
`v11_contradictory_state_or_cue`. O schema de saída restringe os campos e enums;
a compatibilidade entre campos é verificada pelo decoder. A resposta foi
preservada integralmente antes da rejeição, com hash e recibo da chamada.

O replay offline reproduziu a rejeição sem inferência. O controle foi
regenerado e seu hash conferiu com plano e recibo. A divergência já está no raw;
não foi produzida pelo mapper ou agregação. Não se converteu esse objeto
manualmente em false, unknown ou resultado válido, nem se trocou a pista para
`absent`. Houve **uma resposta capturada e zero resultados aceitos**.

| Variante | Chamadas reservadas | Resultados aceitos | Situação |
| --- | ---: | ---: | --- |
| R | 1 | 0 | Primeira resposta contraditória; parada terminal |
| E | 0 | 0 | Não executada |
| RE | 0 | 0 | Não executada |
| v11 em cache | 0 novas | 12 | Referência anterior: 1 false correto, 11 true |

Os denominadores das quatro comparações pareadas de controles são **zero**.
Não há taxa de acerto, ganho/perda ou ranking estimável entre R, E, RE e v11
nesta rodada. Zero resultados aceitos não significa zero acertos em 12.
O `no_target` isolado também não demonstra recuperação da ausência: ele veio
num objeto recusado e em apenas um controle. A matriz de 36 não foi concluída.

Os oito vídeos preservados, os três erros antigos da v10 e o painel adicional
não foram executados. Todos os denominadores pareados de vídeos são zero;
não há medida v12 de sensibilidade, especificidade real ou suporte das pistas.
Nenhum recibo de revisão de fase1/fase2 foi criado. A causa interna da escolha
contraditória não foi isolada; não se atribui a pesos, quantização ou atenção.

## Consumo e encerramento

| Contador | Novo | Cumulativo | Teto desta autorização |
| --- | ---: | ---: | ---: |
| Reservas nativas | **1**, resposta capturada e rejeitada | **1.723** | 1.838 |
| Aquisições | **0** | **256** | 268 |
| Sessões | **12,4611 s** | **35.577,1180 s** | 37.964,6569 s |

Runtime nativo de **12,3523 s** e pico RSS amostrado de **2.604,54 MiB**, abaixo
de 3,3 GiB. A diferença para a sessão inclui preparação e gravação da operação.
Suíte e conferência offline fora da operação não contam como inferência.

As 115 reservas e 12 aquisições restantes ficaram encerradas. Não se iniciou
E ou RE após a falha de R. O guard puro `runnable` recusou o estado selado sem
modificar seu checkpoint; o executor não foi chamado novamente. O journal de
descarte está vazio e concluído, pois não houve imagem nova de vídeo.

## Preservação e consequência

Conferem os **934 arquivos herdados**, os 935 pins do plano e as oito fontes,
testes e protocolo congelados. As oito folhas antigas continuam presentes e
idênticas, sem remoção ou movimento; seus 32 crops foram reproduzidos em memória
com hashes e tempos idênticos. Nenhuma fila anterior foi reaberta ou alterada.

Runtime e pesos foram reconferidos em leitura contra o arquivo oficial em
cache, sem extração/reinstalação. Os ambientes raiz (130 distribuições) e
isolado (42) permanecem iguais. Zero sessões temporárias e nenhum worker VLM
restante na conferência final. Zero NIM ou inferência externa; nenhuma rede
foi necessária nesta execução.

As partições continuam **203 treino / 66 validação / 31 teste reservado**.
O teste permaneceu fechado, sem abrir suas features, rótulos, previsões ou
métricas. O artefato M1/A200 e os hashes dos três modelos nativos conferem,
assim como seu relatório de validação. A300, B-cache e serviço Python/MCP
permanecem preservados. README não rastreado não foi lido, editado ou versionado.

Esta rodada não qualifica candidato para outra auditoria cega. Nenhuma coluna
foi liberada, nenhum treino B/C começou e o M1 não foi promovido/substituído.
Uma continuação requer protocolo próprio para a falha contratual observada;
o saldo selado não permite completar a matriz por uma nova tentativa.

Recibos privados em `data/private/issue-4-vlm-v12-v1/` (plano, checkpoint,
reserva/raw, comparação parcial e descarte) e
`data/private/issue-4-vlm-v12-verificacao-v1/` (pins/configuração, suíte,
plano congelado, reconstrução da falha, preservação de pixels/tempos,
ambientes, modelo/partições e conferência final).

- Plano lógico: `cccacbeccbd5e3802be26cef31cc314b4adad126eb91a7b363ff89b973b8f6ae`.
- Arquivo do plano: `aaae6cd9139a50ea957defccc3b54cc338c0599fd67e6fe9e6ed5b556023aab3`.
- Configuração: `edcfcbe018f019213fcbce994ae3744012aa8b4d8c33fdb90733b9e6ee5b3808`.
- Raw: `fa6cf84126dff84fd72b07f173b825643adfd0fddf3a017eef9546359e1e1fe8`.
- Comparação lógica: `69d0f7f8dbebbc661b56210d2ccb99c5b24b9ad05ba14de42c031b45a9ca8ec4`.
- Arquivo da comparação: `46dbe4b52344ce81ebbeb2ff563caa6ad7a863fd223f604f0d6aac7d141adbcf`.
- Checkpoint selado: `8ce98cca95ecb689de1273f78f854f5b657eb85d6fa43541f8b46ec975d616cc`.

# Nativa 225 — tentativa renovada única

A rodada v1 permanece selada e sem alterações. Esta unidade aditiva vincula a
autorização renovada a uma única tentativa no mesmo PNG, pesos, pergunta,
schema, seed 42, temperatura zero, quatro threads e saída de 64 tokens.

O capturador só muda o namespace para `issue-4-vlm-native225-probe-v2`; journal,
owner, parser e encerramento congelados são reutilizados. O controlador conserva
55 s úteis + 5 s de encerramento, 80 s globais, MemAvailable ≥6 GiB e RSS
cooperativo de 3,3 GiB. A imagem permanece RGB 360×640; min/max 225 prevê
960 patches e 240 tokens após merger. Nada é aprovado por essa previsão.

A cápsula obrigatória inclui `bwrap --unshare-net --ro-bind / / --dev /dev`,
com gravação somente no diretório privado. Antes de reservar, o controlador
confere rede isolada, abre `/dev/null` e executa somente `/usr/bin/true` com
`stdin=DEVNULL`. Falha nesse preflight não reserva nem lança o modelo.

A renovação serve exclusivamente à tentativa atual. Como teto operacional
conservador, o controlador exige ainda pelo menos 60 s antes de 03h40 UTC
de 22/10/2026. Isso não concede uso geral posterior da imagem. A reserva é
irreversível, inclusive em falha de início; não há retry ou reabertura.

Sucesso técnico exige encoder e decode completos, 240 tokens, JSON válido e
limpeza confirmada. O negativo exige `answer=no`; isso não valida positivos,
atributos gerais, B/C ou holdout. Não há rede, NVIDIA, download ou custo.

O despacho exige recibos privados externos de autorização e revisão vinculados
ao plano final; este documento e os testes inventados não constituem execução.

## Revisão técnica antes do despacho

Passaram 32 testes inventados em 0,81 s, Ruff e formatação. A primeira seleção
teve 30 acertos e dois testes ainda presos à data de expiração v1; esses dois
passaram após expressar os instantes relativamente à nova janela, sem mudar
o produto. A cápsula real corrigida passou apenas com o filho inofensivo e
mostrou somente a interface loopback. Nenhum modelo ou reserva nessa revisão.

A comparação com v1 confirmou apenas novo roteamento/recibos, janela específica
e preflight de cápsula. Os nove pins da rodada anterior continuam iguais.
O coordenador revisou essa diferença e os testes antes do commit desta unidade.

## Execução única encerrada

A tentativa renovada completou encoder/decode, observou 240 tokens e respondeu
`no` no negativo, em 10,09 s de captura e 11,08 s de controlador. Limpeza
confirmada, sem workers e fila selada com saldo zero. Consulte os
[resultados completos](issue-4-vlm-native225-renewed-once-v2-results.md).
Não há autorização restante nem aceite visual amplo.

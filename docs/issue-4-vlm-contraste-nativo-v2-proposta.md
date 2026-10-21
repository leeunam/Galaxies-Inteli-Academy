# Contraste nativo/derivado v2: candidato inerte para revisão

Esta adição liga o journaling durável ao protocolo de quatro células. Nenhum
plano, autorização, selo, PNG privado ou execução real acompanha o commit.
A autorização anterior está consumida e a fila v1 selada permanece somente
como proveniência; seu saldo nunca pode financiar v2.

A ordem futura é Dneg, Nneg, Npos, Dpos. As quatro entradas RGB 360×640,
pesos, runtime, prompt, schema e flags permanecem os congelados; orçamento
visual mínimo=máximo 1.024, com exigência de 1.075 tokens realmente observados
e encoder+decode completos em cada célula. CPU 4, RSS 3,3 GiB, até 60 s por
dispatch (55 úteis e 5 para limpeza), 260 s globais incluindo journaling.
Nenhum retry, substituição, download, envio externo, despesa ou modelo novo.
Erro semântico continua a ordem fixa; a primeira falha técnica sela a etapa.

O controlador reutiliza configuração, construção de argv, comparação e validação
do protocolo congelado. Adapta somente o loop de execução para namespace novo,
reserva com vínculo à nova autorização e captura durável. Não substitui o dono
do processo, não altera globais para redirecionar captura e não simula PID.
O helper recebe um launcher interno que rejeita raiz e argv diferentes do
caminho revisado. Não há opção CLI de raiz, modelo, payload, aprovação ou release.

`prepare` é uma entrada para futura preparação autorizada na árvore integrada:
confere v1 selada, pins e configuração e copia bytes dos quatro PNGs preparados.
Não refaz aquisição nem grava nova derivação; a função pura de configuração
reconfere a derivação congelada em memória. Não cria autorização nem selo. A preparação desta
unidade usa exclusivamente fixtures inventadas. Antes de executar, o coordenador
precisa preparar e revisar o plano real; o operador precisa fornecer autorização
nova, específica, e o revisor precisa fornecer selo externo correspondente.

A autorização externa vincula protocolo, namespace, hash do plano/configuração,
raiz canônica por hash, revisor, quatro hashes de entrada, orçamento, ausência de
retry e custo zero, além da referência e hash da instrução literal nova. O selo
independente repete esses vínculos e prende o hash do arquivo de autorização.
Não existe escritor desses dois recibos neste módulo. Ausência ou divergência
recusa antes de lock, started, contador, diretório de captura ou Popen. A referência
consumida é rejeitada; recibos da v1 não servem como liberação da v2.

Depois da liberação, `started.json` exclusivo consome a etapa, inclusive em crash
antes da primeira reserva. Cada reserva exclusiva precede o spawn e falhas de
persistência retornam ao dono do processo. Prefixo durável é provisório; inspeção
não o promove a resultado final e não permite retomada/retry. Crash sem recibo
terminal exige reconciliação somente leitura e confirmação de limpeza.

O prazo cooperativo usa relógio absoluto no launcher e no poll do processo real,
incluindo journaling antes do spawn e conservando cinco segundos à limpeza
herdada. O coletor congelado continua o único dono do processo e da limpeza;
verificações externas medem despacho e teto global.
Fsync ou outra operação bloqueada no kernel pode atrasar o encerramento: estes
checks não constituem garantia de prazo duro em falha do host. Cleanup incerto
preserva scratch e impede resultado aceito ou nova célula.

Proposta mínima de autorização, a apresentar somente depois da preparação e
revisão: “Autorizar uma única comparação informativa local v2 de exatamente
quatro chamadas Dneg/Nneg/Npos/Dpos, no plano e pins revisados, com as quatro
entradas congeladas, 60 s por dispatch e 260 s globais, custo zero, sem retry,
substituição, download, transmissão externa ou abertura do teste reservado.”
A instrução literal e a aprovação técnica precisam referenciar o plano concreto.

A hipótese é perda de detalhe na cadeia 360×640 → JPEG 512 → 186×330 com 134
colunas brancas frente ao nativo na mesma geometria. Trata-se de diagnóstico
assistido no par revelado, sem auditoria cega, aprovação VLM, promoção B/C,
aceite científico ou garantia de acurácia. Os gates congelados não mudam.

Verificação do candidato: 133 testes focados passaram em aproximadamente 2,5 s,
com Ruff e formatação. Nenhum processo de modelo, acesso externo, plano real ou
cópia privada foi realizado. Um filho Python inventado confirma timeout com
limpeza e checkpoint terminal; uma integração sem spawn comprova reserva única,
falha técnica e inspeção sanitizada. A inspeção distingue preparação de início
incerto: marcador started, captura ou contador consumido proíbe reentrada e
fecha os quatro slots, sem inferir resultado ou limpeza. Código, testes e esta
proposta formam uma unidade dependente dos dois commits do helper.

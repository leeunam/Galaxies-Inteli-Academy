# Contraste nativo/derivado: interrupção sem resposta recuperável

A execução única do [contraste preparado](issue-4-vlm-contraste-nativo-preparacao.md)
foi iniciada em 21/10/2026, às 17:22:21 UTC, após liberação específica.
Na reconciliação, a sessão original 80264 respondeu `Unknown process id 80264`.
Não há código de saída recuperado ou evidência que identifique a causa da
interrupção. Nenhum processo novo foi iniciado para recuperar a execução.

A fila tinha uma reserva, da primeira célula negativa derivada, e nenhum
`result-N.json`. O scratch conservava somente `schema.json`, com 137 bytes;
a captura mantém a saída em memória até retornar. Não foi recuperada resposta,
contagem de tokens ou confirmação de encoder/decodificação completos. Não há
resultado perceptivo ou comparação entre os braços.

A fila foi selada com `contrast_interrupted_outcome_uncertain`, uma chamada
contabilizada e os três slots não utilizados encerrados. Os 260 segundos
conservados no checkpoint são cobrança conservadora do limite global, **não
tempo medido**. O resultado da chamada permanece incerto; não houve retry,
retomada, execução das células restantes ou novo POST NIM.

O checkpoint anterior foi preservado em arquivo exclusivo antes do selo,
acompanhado de reconciliação e verificação final. Scratch, reserva, liberação,
plano e quatro PNGs permanecem preservados. A ausência atual de workers não
substitui um ack histórico de cleanup; nenhum descarte foi feito. A retenção
dos PNGs continua até 21/10/2026, 23h59 de São Paulo, conforme o protocolo.

Conferem os oito arquivos fixos da fila, os 26 arquivos protegidos e os quatro
manifestos das coortes/partições por hash. O teste reservado não foi aberto
semanticamente e M1 permanece preservado. Zero workers pertinentes foram
observados na reconciliação. Não houve alteração de código, treino, aquisição,
nova inferência ou liberação de campos. Não foram repetidos testes de runtime;
esta unidade verifica exclusivamente recibos, identidades e encerramento.

A [evidência sanitizada](evidence/issue-4-vlm-contraste-nativo-interrupcao.json)
vincula o checkpoint anterior, a reconciliação e o selo final. O próximo passo
exige decisão própria; a fila encerrada não oferece saldo para outra tentativa.

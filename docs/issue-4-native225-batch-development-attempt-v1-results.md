# Lote visual autorizado: etapa encerrada antes do modelo

A autorização consolidada foi recebida em 22/10/2026 às 12:20 UTC. A preparação
partiu de `8b2705c`; a correção de serialização do schema foi registrada em
`93f15a1`, com 64 testes sintéticos aprovados em 3,56 s. A revisão independente
conferiu configuração, ativos declarados, prazos, cápsula e watchdog e liberou
somente a execução dos 13 controles. O [recibo sanitizado](evidence/issue-4-native225-batch-development-attempt-v1-results.json)
registra o resultado; a [correção anterior](issue-4-native225-batch-schema-order-fix-v1.md)
explica o defeito removido antes do despacho.

## Resultado confirmado

Houve uma tentativa de lançamento do operador. Seu worker Python saiu com
código 2 em 0,123 s, antes de chegar ao dispatcher nativo. O ledger ficou selado
com zero chamadas reservadas, zero aquisições e nenhuma operação pendente.
Nenhum modelo iniciou, nenhum controle foi avaliado e a auditoria não começou.
A limpeza foi confirmada e não restaram workers. Não houve NVIDIA, treinamento
B/C ou abertura do holdout.

O relógio global foi registrado uma única vez: início 12:30:48.880978 UTC,
limite da triagem 12:50:48.880978 UTC e limite global 23:30:48.880978 UTC em
22/10/2026. A etapa foi encerrada pelo primeiro erro; o relógio não foi reiniciado
e os saldos não foram reciclados. Nenhuma reentrada ou repetição foi feita.

## Causa e verificação offline

O comando usado para iniciar o operador continha o caminho relativo do script.
A guarda de identidade do watchdog exigia o token absoluto desse mesmo script
na linha de comando do processo vivo. O launcher e a guarda tinham, portanto,
um contrato incompatível. O preflight anterior chamava `verify(None)` e não
exercitava essa guarda adicional de `verify(call_id)`.

O recibo real conserva apenas o erro genérico `worker_blocked_or_failed`; ele
isoladamente não identifica o predicado. A incompatibilidade foi confirmada
pela inspeção do comando utilizado e reproduzida offline com processos Python
inofensivos: a chamada completa `verify(1)`, dentro da cápsula sem rede, recusou
o caminho relativo com `live_reviewed_watchdog_required` e aceitou a identidade
com caminho absoluto. Nenhum dispatcher foi chamado nessa prova. As verificações
usaram metadados de teste em memória; a fila real continuou selada e intacta.

A correção mínima de lançamento é usar o caminho absoluto do operador revisado,
sem afrouxar a guarda. Isso ainda exige uma nova proposta de execução e revisão
concreta para uma rodada permitida. **Não executar o operador na fila encerrada.**
Não é falha perceptiva do modelo nem resultado de qualquer um dos 13 controles.

## Estado da entrega

Os artefatos da tentativa e as duas provas de identidade foram preservados em
recibos privados distintos. As fontes congeladas do protocolo e o módulo público
inativo não foram modificados pela ativação em memória do worker, que nem chegou
a ocorrer. A base, M1, imagens e recibos anteriores permanecem protegidos.

A autorização consolidada não resolve os pré-requisitos científicos. Continuam
pendentes projeção segura dos 203 exemplos de treino, exclusões completas,
seleção e anotações cegas, revisão independente e ligação da aquisição ao ledger.
Não foi solicitado que o usuário forneça 32 vídeos. Para retomar, é necessário
resolver a permissão de nova rodada após a parada técnica, sem reabrir este ledger
ou prolongar silenciosamente o limite global. B/C e avaliação final continuam
pendentes, sem declaração de aceite integral.

# Correção da serialização do schema antes do lote

A revisão independente identificou que o controlador gravava o schema com
ordenação alfabética de chaves. Isso mudava a ordem `state_first` congelada
para as branches de produto. Nenhuma inferência do lote ocorreu antes da
correção. O erro foi reproduzido por um teste que lê o arquivo efetivamente
entregue ao launcher sintético, sem modelo.

O controlador agora escreve o schema com ordem preservada, criação privada
exclusiva e fsync, mantendo a função de metadados anterior intacta. A seleção
dirigida passou em 64 testes, incluindo os 63 anteriores e a regressão, em
3,56 segundos. Ruff e formatação passaram. Isso remove um defeito técnico,
sem provar a qualidade perceptiva nem alterar prompt, schema lógico ou gates.

A autorização consolidada recebida em 22/10 às 12:20 UTC será registrada em
namespace privado próprio, vinculada à proposta existente. A ativação é
restrita ao operador revisado de desenvolvimento; o módulo público permanece
inativo. Revisão, configuração, prazo global único, cápsula e watchdog devem
ser conferidos antes de qualquer inferência. A auditoria só pode começar após
13 controles aprovados e suas condições independentes. Sem NVIDIA, treino
B/C ou holdout nesta unidade.

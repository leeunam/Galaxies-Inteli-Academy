# V16 — correção terminal antes de qualquer despacho

A revisão técnica do canal principal/supervisor aceitou o desenho científico,
as anotações e o preflight nativo do [checkpoint inicial](issue-4-vlm-v16-preflight.md),
mas identificou um P2: depois de aceitar a liberação técnica, execute() ainda
chamava no_workers(root) e verify_runtime() fora do tratamento que registra a
falha e sela a rodada. Uma exceção ali deixava a fila aberta, permitindo outra
invocação. O marco inicial e suas provas permanecem como registro daquela versão.

## Correção e checks afetados

As duas verificações continuam obrigatórias, agora dentro do try terminal,
depois do check_clearance. Falha em qualquer uma grava halt_reason, sela a
comparação e preserva consumo, sem nova chamada. Ausência de clearance continua
recusa inerte, anterior a essas verificações: não cria operação nem altera o
checkpoint. Nenhuma guarda foi removida ou enfraquecida.

Passaram **39 testes finais em 30,62 s**, somente no módulo afetado, incluindo:

- Falha de no_workers depois da liberação: zero chamadas, rodada selada,
  nova invocação recusada e checkpoint estável.
- Falha de verify_runtime: mesmas propriedades, sem carregar/inferir modelo.
- Esgotamento simulado antes da reserva, com relógio determinístico em1196 s:
  zero reservas/invocações; parada terminal e nenhuma chamada seguinte.
- Timeout simulado depois da reserva durável: uma reserva,180 s cobrados pelo
  relógio falso, falha preservada, nenhuma chamada da outra condição e sem retry.
- Recusa de namespace substituído e de cópia da fila efetiva para outro caminho.

São testes com fixtures e relógios falsos: não representam chamadas VLM ou
segundos consumidos no experimento real. O teste final conserva também os
casos anteriores de gates12/12→5/5, ordem pareada, falhas globais, reservas e
reconstrução de métricas. Houve uma checagem anterior dos mesmos39 testes;
os dois resultados não são somados como78 testes independentes. A última
checagem ocorreu após vincular o carregamento ao único caminho efetivo.

Os171 testes mais amplos do marco inicial continuam registrados com suas
fontes originais. Não foram reexecutados nem apresentados como prova da nova
correção. Ruff e formatação dos222 arquivos Python rastreados passaram no
código corrigido. Não há testes concorrentes de outro executor.

## Substituição anterior à execução, com um orçamento efetivo

O plano inicial `a1120d46a64d7984ba80e4fb14603923873859a65e37d6baa585d485f7fa62dc`
permanece em `data/private/issue-4-vlm-v16-v1/`. Seus arquivos plan.json e
checkpoint.json são byte a byte iguais aos originais: zero operações,
zero chamadas/aquisições e clearance nunca publicado. Recebeu somente o arquivo
aditivo superseded-v2.json, que identifica a substituição anterior ao despacho.
O carregador atual recusa essa fila antes de qualquer invocação.

A preparação corrigida usa exclusivamente `data/private/issue-4-vlm-v16-v2/`.
O caminho efetivo é validado tanto na preparação como no carregamento, e cópias
em outro namespace são recusadas. Um manifesto aditivo vincula as duas filas,
seus hashes e **um único orçamento de até34 chamadas, zero aquisições e1200 s**.
O plano novo mantém a mesma base histórica1811/256/37044,30741882603 s.
Os limites não são somados: o original nunca foi ativado ou consumido.

Conferência real dos dois namespaces, com invoker proibido: a fila inicial foi
recusada como superseded; a nova foi recusada por falta da nova revisão técnica.
Ambos os checkpoints permaneceram iguais e somam **zero chamadas e zero
aquisições**. Não existe recibo de liberação técnica em nenhuma das duas filas.
Não é autorização para outra rodada, saldo adicional ou repetição posterior.

## Desenho e provas mantidos

Prompt, duas ordens,22 objetos, categorias, ordem dos ramos, projeção, modelos,
CPU4/seed42/temperatura0, pixels, tempos, controles, cinco positivos e todas as
alternativas admissíveis permanecem idênticos ao primeiro plano. As configurações
diferem somente nos vínculos dos três arquivos corrigidos: plan,run e seus testes.
O corpo das anotações dos cinco positivos tem o mesmo hash anterior.

Os três arquivos fonte do gate gramatical continuam iguais. Seus recibos nativos
foram conservados, sem recompilar, retokenizar ou inferir novamente:13.703
sondas por condição, ordens distintas realmente aceitas/rejeitadas, mesmos22
objetos,88 serializações dentro de64 tokens e comandos equivalentes. O preflight
lógico continua `db04df2c8b53d996a8bacba46135aa01be5a9f1c56b420fc06bef9aeac497555`.

Um inventário novo conserva por hash os30 arquivos de prova anteriores; nenhum
foi apagado ou sobrescrito. Os registros da correção usam novos nomes, incluindo
run-plan-frozen-v2.json, technical-checkpoint-v2-verification.json e os JUnit/logs
v2. Também foram reconferidos os1388 pins anteriores,1423 pins do plano novo,
M1/holdout/partições/integração #5 e os recibos da fila inicial.

## Novo checkpoint para passagem técnica

- Plano efetivo: `52a1248c9118f9ea8f92990521177019a7b2effa79ef2f6b559737338a10c973`.
- Configuração: `f281fc63317da538ec52546cec8799af666276d52d7a2f1b6dd4281aec773fa7`.
- Cinco casos e anotações: `382ab73dc0d03b0b930c0c2f8de36f64e6ceb8ce949ae2b232dde256cf890aef`.
- Fila efetiva: `data/private/issue-4-vlm-v16-v2/`.
- Ambas as filas: zero chamadas/aquisições; revisão técnica nova pendente.

A geração continua bloqueada até a passagem técnica exigida após a correção.
Sem nova aprovação humana intermediária, NIM, API, aquisição, download,
instalação/sync, mudança de modelo/runtime, liberação de atributos, auditoria,
treino B/C, publicação, push ou deploy. README e briefing pinado intactos.

# Liberação aditiva do diagnóstico NIM, uma tentativa

Código e testes falsos concluídos; nenhuma chamada externa, chave, reserva ou
revisão técnica real foi executada/criada nesta preparação. O perfil inerte
conserva `AUTHORIZATION_ID = None`, plano, selo, fontes e testes byte a byte.

A nova autorização específica é `Sentinel_c3cbbc19ae7c81919fc1361a0256d307`,
resposta “autorizo” de 21/10/2026 às 17:20 UTC à pergunta de 17:19 UTC
`Sentinel_9ac253bb40e081918211c10f27ff03c2`. A pergunta explicitou nova chamada de teste,
pois a anterior já havia sido consumida: mesmos três exemplos inventados, modelo,
endpoint, 45 segundos, custo máximo R$0, sem repetição automática, vídeos ou mudança
de conta. A evidência financeira permanece `Sentinel_e945b14459008191a932c869a4216aef`.

`remaining_authorized_calls = 1` é a configuração inicial selada, nunca um saldo
após reserva. A criação exclusiva da pasta consome a autorização inclusive em
crash, falha, timeout, cancelamento ou resultado incerto; não autoriza repetir.

O protocolo `nim-three-diagnostic-release-v1` usa exclusivamente
`data/private/issue-5-nim-graph-diagnostic-release-v1` e exige revisão nova em
`data/private/issue-5-nim-graph-diagnostic-release-v1-review/technical-review.json`.
A revisão vincula protocolo, plano, configuração, autorização, evidência financeira,
supervisor, mensagem real de revisão e SHA256 do caminho absoluto do checkout.
`check_review()` define os campos exatos. Nenhuma revisão privada real foi criada;
a revisão inerte, histórica ou de outro checkout não serve.

O pai verifica o selo/revisão antes da reserva; a própria reserva verifica novamente
antes de mkdir/nonce. O único filho ROOT repete as verificações e usa `authorize()`
v3 original, PID real do pai e nonce original. Persiste despacho exclusivo antes
de importar/chamar o getter. O transporte HTTPS existente faz um POST direto,
sem proxy, redirecionamento, retry, reparo ou fallback. Não há argumentos de
payload, endpoint ou raiz no filho. O grafo/subgrafo, autoridade numérica e
`validate_selection()` permanecem intactos: 1–12 IDs únicos e conhecidos, hash exato.
O diagnóstico existente opera depois da autoridade; nenhum corpo rejeitado,
cabeçalho, valor desconhecido, exceção ou hash rejeitado sai. Fake/replay nunca
comprova provedor real. Simulações recusam symlinks e componentes `issue-5-nim-*`,
incluindo namespaces históricos/novos em qualquer checkout.

O corpo segue em 8576 bytes, SHA256
`fd87bed20413c52bb7873d92da48c37d5f5f391a3fa9997e77177d073aaafcba`,
para `https://integrate.api.nvidia.com/v1/chat/completions`, modelo
`nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`, 2048 tokens e resposta até 16 KiB.
São três criativos e 24 fatos inventados, sem dados/modelos/mídia reais.

## Prazo e posse do processo

O prazo total permanece 45 s: até 43 s para preparação/grafo/HTTP e até 2 s reservados
para limpeza. A binding inclui deadline global, deadline útil e orçamentos de
até 1 s para drain e até 1 s para confirmar reaping. Fakes curtos reduzem esses
orçamentos proporcionalmente. O filho usa somente o deadline útil no HTTP.

`ReleasedProbeWorker` reutiliza a proteção de spawn/`finish()`; também encaminha
spawn cancelado à limpeza aditiva. Fecha stdin, mata exclusivamente seu filho e
descarta stdout restante sem reter bytes. Drain limita um frame IPC mais um byte,
e tem prazo próprio. Excesso, erro ou EOF incerto fecha somente o pipe stdout do
Process; esse fallback restrito usa o transport porque Process não expõe close
público de stdout. Depois polla o `returncode` público, com sleep curto e prazo
próprio, como confirmação de reaping pelo watcher. Não registra `Process.wait()`
em chama waitpid concorrente. Se o status continuar desconhecido, falha fechado.
Não há wait sem prazo após fallback. Cancelamento repetido conserva um dono.

O recibo declara `worker_cleanup_confirmed` e código estático de limpeza. Falha de
limpeza descarta resultado/prova e mantém nonce/reserva consumidos. Não afirma
reaping confirmado quando a observação é incerta.

## Verificação e histórico preservado

Passaram 38 testes isolados (30 do perfil +8 de posse) em 11,61 s, com captura normal,
autoload de plugins desativado, janela inicial da ferramenta 30 s e cap operacional
60 s. A janela é condição operacional registrada, sem atribuí-la como causa ou
critério de aceite. Passaram também 18 testes ROOT (novo ramo com objetos injetados
+ adaptador existente) em 0,96 s. Ruff/formato, pins novos e herdados conferem.
Um teste aritmético adicional de binding fracionário passou após derivar o orçamento
do mesmo intervalo representável deadline-started, sem spawn. Os testes cobrem review ausente/divergente/root/symlink, PID/nonce originais,
one-shot, falha antes de resposta, rejeição200, fake aceito sem provedor real,
cancelamento/spawn, drain sem EOF/excesso/erro, reaping conhecido/desconhecido e
prova descartada com nonce consumido. JUnit final isolado:
`/tmp/nim-authorized-release-returncode-final-v1.xml`; ROOT:
`/tmp/nim-authorized-release-root-final-v1.xml`.

O candidato intermediário teve timeouts 45 s nos fakes, incluindo valid/too_many_ids;
as rodadas não concluídas foram interrompidas por PID/cmdline/cwd exatos, sem matar
outros processos. Uma rodada posterior com prazos explícitos concluiu 31/37 e
falhou 6/37: wrong_hash, scalar_ids, deep_json, send_failure e dois cancelamentos.
Os recibos localizaram espera de reap após todos os IPCs e EOF, já limitada.
O trace de wrong_hash mostrou `returncode=None` antes/no timeout de wait e logo após
close_stdout, seguido de -9 no próximo agendamento. Isso motivou polling público
limitado, corrigindo a espera observada nos fakes. Não demonstra causa geral do
runtime nem explica a rejeição NIM ou interrupção visual históricas. As falhas
intermediárias permanecem registradas; o helper histórico não foi modificado.

## Comando futuro único

Após integração/revisão independente do código final e criação da revisão privada
nova pelo coordenador, a partir do checkout principal:

```sh
rtk proxy env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/inteli/Documents/projetos/Galaxies-Inteli-Academy/orchestration LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false /home/inteli/Documents/projetos/Galaxies-Inteli-Academy/orchestration/.venv/bin/python -B -m galaxies_orchestration.nim_diagnostic_release_v1 --execute-reviewed-once --worker-python /home/inteli/Documents/projetos/Galaxies-Inteli-Academy/.venv/bin/python
```

Esse comando não foi executado nesta preparação. O coordenador/integrador mantém
posse exclusiva da integração, revisão privada e eventual despacho único.

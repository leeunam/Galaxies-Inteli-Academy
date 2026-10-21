# Liberação aditiva do diagnóstico NIM, uma tentativa

Preparação de código e testes falsos, sem chamada externa nem revisão técnica real.
O perfil inerte anterior conserva `AUTHORIZATION_ID = None`, plano, selo, fontes e testes.

A nova autorização específica é `Sentinel_c3cbbc19ae7c81919fc1361a0256d307`,
resposta “autorizo” de 21/10/2026 às 17:20 UTC à pergunta de 17:19 UTC
`Sentinel_9ac253bb40e081918211c10f27ff03c2`. A pergunta explicitou nova chamada de teste,
pois a anterior já havia sido consumida: mesmos três exemplos inventados, mesmo modelo
/endpoint, 45 segundos, custo máximo R$0, sem repetição automática, vídeos ou mudança
de conta. A evidência financeira permanece `Sentinel_e945b14459008191a932c869a4216aef`.

`remaining_authorized_calls = 1` descreve a configuração inicial selada, nunca
um saldo depois de uma reserva. A existência exclusiva da pasta de reserva consome
a autorização inclusive em falha, crash, cancelamento ou resultado incerto.

O novo protocolo `nim-three-diagnostic-release-v1` usa exclusivamente
`data/private/issue-5-nim-graph-diagnostic-release-v1` e exige revisão nova em
`data/private/issue-5-nim-graph-diagnostic-release-v1-review/technical-review.json`.
A revisão deve vincular protocolo, plano, configuração, autorização, evidência
financeira, supervisor, mensagem de revisão e SHA256 do caminho absoluto do checkout.
O formato exato é definido por `check_review()`; nenhum desses arquivos reais é criado
por esta entrega. A revisão do perfil inerte ou de outro checkout não serve.

O pai verifica o selo e a revisão antes da reserva; a própria reserva os verifica
novamente antes de mkdir/nonce. O único filho ROOT repete as verificações e usa
`authorize()` v3 original, com o PID real de seu pai e nonce original. O marcador
exclusivo de despacho é persistido antes de importar/chamar o getter da chave.
O transporte HTTPS existente faz somente um POST direto, sem proxy, redirecionamento,
retry, reparo ou fallback. O filho aceita somente o catálogo público fixo, sem
argumentos de payload, endpoint ou raiz. O prazo global de 45 s abrange o grafo e
limpeza; `ProbeWorker` mantém a posse e recolhe somente seu processo, inclusive sob
cancelamento repetido durante o spawn.

O corpo permanece em 8576 bytes e SHA256
`fd87bed20413c52bb7873d92da48c37d5f5f391a3fa9997e77177d073aaafcba`,
para `https://integrate.api.nvidia.com/v1/chat/completions`, modelo
`nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`, 2048 tokens e resposta de até
16 KiB. São três criativos e 24 fatos inventados. A autoridade numérica e o
`validate_selection()` permanecem intactos (1–12 IDs, únicos, conhecidos e hash exato).
O diagnóstico usa o helper existente somente depois da autoridade original;
nenhum corpo rejeitado, cabeçalho, valor desconhecido, exceção ou hash rejeitado sai.
A seleção fake/replay nunca comprova provedor real.

Simulações rejeitam symlinks e qualquer componente de caminho `issue-5-nim-*`,
incluindo namespaces reais históricos e novos em outros checkouts. Os testes usam
somente diretórios inventados e injetam objetos para verificar a ordem do ramo de
produção, sem reserva/revisão/chave/socket reais. Reservas são exclusivas e uma
falha, timeout ou cancelamento permanece consumido; resultado incerto não permite
repetir.

Após integração, revisão independente do código final e criação da revisão privada
nova pelo coordenador, o comando futuro único, a partir do checkout principal, é:

```sh
rtk proxy env PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/home/inteli/Documents/projetos/Galaxies-Inteli-Academy/orchestration LANGSMITH_TRACING=false LANGCHAIN_TRACING_V2=false /home/inteli/Documents/projetos/Galaxies-Inteli-Academy/orchestration/.venv/bin/python -B -m galaxies_orchestration.nim_diagnostic_release_v1 --execute-reviewed-once --worker-python /home/inteli/Documents/projetos/Galaxies-Inteli-Academy/.venv/bin/python
```

O comando acima não foi executado nesta preparação. O coordenador é o único
responsável por integração, revisão privada e eventual despacho único.

## Verificação desta preparação

Os 18 testes ROOT do novo ramo com objetos injetados e do adaptador existente
passaram em 0,96 s. Ruff e formato dos arquivos novos conferiram. Os pins herdados
de transporte HTTPS, codec v3, autoridade original, observador HTTP e diagnóstico
foram conferidos e continuam iguais.

A rodada isolada direcionada (43 casos planejados, novos + inertes) não terminou com sucesso. Houve timeouts de 45 s nos
fakes comuns, com `outcome=timeout_outcome_uncertain`, inclusive `valid/accepted`
e `too_many_ids/schema_constraint`; outras falhas da primeira saída parcial não
foram recuperadas com nomes exatos. Uma execução seletiva sem captura passou
`valid/accepted` em 0,84 s; a rodada subsequente sem captura também teve timeout
em `duplicate_ids/duplicate_evidence_id` e `extra_field/schema_extra_field`.
`deep_json` foi interrompido durante a parada. Portanto desativar captura não é
correção nem demonstra uma causa. As sessões foram interrompidas por PID/cmdline/cwd
exatos, sem terminar processos alheios. Não se declara aprovação da suíte completa
nem liberação de execução real com base nesta preparação.

O discriminante posterior instrumentou somente o runner de teste, com dois fakes
sequenciais no mesmo `asyncio.run`, prazo 5 s por caso e nenhum arquivo de produção
alterado. `duplicate_ids` concluiu os oito IPCs e a limpeza em 0,415 s, com código
`duplicate_evidence_id`. `extra_field` também concluiu os oito IPCs, incluindo
`proof`, mas ficou em `__aexit__` depois de `cleanup_before`; o prazo encerrou a
espera em 5,421 s e o recibo ficou `timeout_outcome_uncertain`. Esta observação
delimita uma falha de limpeza após IPC completo; não demonstra causa do runtime.
A seleção direcionada de 17 casos restantes também foi interrompida pelo limite
externo de 30 s, sem JUnit final. Não foi elevada a duração de produção.

Antes de usar o comando real, o coordenador precisa resolver/revisar esta falha de
limpeza e validar o candidato final. Nenhum POST, getter de chave, ledger ou revisão
real foi executado/criado, e o checkout principal não foi escrito.

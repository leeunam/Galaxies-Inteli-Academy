# Issue #5 — adaptador HTTP diagnóstico, candidato inerte

Unidade local aprovada em 21/10/2026 sobre
`8e2d74f743bdd1c7175ed91119ba77e8574d3eee`, em branch nova e isolada.
Não há autorização específica nova. `AUTHORIZATION_ID=None`,
`remote_execution_released=false` e `remaining_authorized_calls=0`.
Nenhuma chave, socket real, aprovação técnica real ou reserva/nonce real foi
usado/criado. As fontes e os registros consumidos continuam intactos.

## Adaptação concreta

O [helper de resposta aberta](../scripts/nim_diagnostic_http_adapter_v1.py)
reutiliza `protocol_ok` e `observe_response`; não abre conexão nem lê chave.
Após o envelope, chama `evaluate_original`, que executa a autoridade original
antes do diagnóstico fechado já revisado. Retorna somente seleção pública
aceita, diagnóstico e metadados limitados. A conexão permanece propriedade do
worker que a abriu, inclusive em erro de leitura/framing.

O [worker fino](../scripts/nim_diagnostic_attempt_worker_v1.py) importa a função
`live_response` existente sem duplicar ou modificar seu transporte. A sequência
permanece dentro de `select`, após contexto e antes de renderização:
reconferir plano/revisão/vínculo → dispatch durável com a função v3 original →
getter existente no ramo real autorizado → HTTPS existente → helper diagnóstico.
O mesmo processo raiz possui o socket; não há neto HTTP ou outra sessão.

O [entrypoint](../orchestration/galaxies_orchestration/nim_diagnostic_attempt_v1.py)
reutiliza `build_graph`, subgrafo, `DiagnosticSelector` e `ProbeWorker` existentes.
O pai real emite a reserva no codec v3, e o filho usa `authorize()` original com
nonce e `os.getppid()` reais. Não há monkeypatch de identidade ou guarda reduzida.
O codec foi mantido stdlib para o Python isolado, reutilizando as primitivas
duráveis existentes. Os sete passos da ponte são precedidos pelo handshake
privado do nonce; o seletor é invocado uma vez.

## Inércia e nova revisão

O ramo remoto recusa **antes de ler plano/revisão, gerar nonce, reservar diretório,
iniciar worker, chamar getter ou abrir socket** enquanto faltar autorização nova.
O worker e o emissor de reserva também verificam isso. Os dois IDs de autorização
consumidos conhecidos são recusados; o fato financeiro anterior não é uma nova
permissão de execução.

Alterar apenas a constante de autorização não ativa o candidato: a configuração
deixa de corresponder ao plano selado. Uma eventual aprovação humana futura exige
nova configuração/plano/selo, revisão independente e recibo técnico específico
do checkout antes de executar. Nenhum CLI cria esses registros automaticamente.
A guarda é de integridade/coordenação do operador, não autenticação criptográfica
contra o proprietário dos arquivos.

Namespace novo proposto: `data/private/issue-5-nim-graph-diagnostic-attempt-v1/`.
Revisão nova: `data/private/issue-5-nim-graph-diagnostic-attempt-v1-review/technical-review.json`.
Ambos permanecem ausentes. A revisão vincula protocolo, decisão de uma tentativa,
hashes de plano/configuração, autorização humana nova, evidência financeira,
chat revisor, SHA do caminho resolvido do checkout e ID da revisão técnica.
Não se lê, reseta ou reutiliza ledger/revisão antigos.

A reserva é exclusiva, 0700, com arquivos 0600 e fsync. A existência do diretório
consome a tentativa, inclusive em falha anterior ao recibo. O marcador de dispatch
precede o getter. `diagnostic-attempt-result.json` preserva estados seguros; fonte
arbitrária, corpo, headers, exceções e hashes rejeitados nunca são gravados.
Simulações recusam namespaces reais antigos/novos, descendentes e symlinks.
O pai confere reserva, nonce, PID, binding, dispatch e run ID antes da prova final.
Recibo anterior não é entrada do executor. Fakes nunca são prova real.

## Corpo e limites invariáveis

| Item | Valor |
| --- | --- |
| Endpoint | `https://integrate.api.nvidia.com/v1/chat/completions` |
| Modelo | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` |
| Corpo | [JSON já revisado](../orchestration/fixtures/nim-graph-live-v1-http-payload.json), **8.576 bytes** |
| SHA-256 | `fd87bed20413c52bb7873d92da48c37d5f5f391a3fa9997e77177d073aaafcba` |
| Dados | Três criativos/24 fatos inteiramente inventados; nenhum dado ou valor derivado de mídia/modelo privado |
| Quantidade proposta / autorizada agora | **Um POST / zero** |
| Saída e resposta | Até 2.048 tokens e 16 KiB |
| Prazo | 45 s globais de execução, incluindo preflights, spawn, HTTP e IPC |
| Parâmetros | Temperatura 0,2, stream falso, thinking desabilitado |
| Custo/repetição | Teto R$0; sem retry, reparo, fallback, redirect ou proxy |

A confirmação anterior de plano gratuito continua como evidência financeira,
sem consulta à conta, novo pagamento, instalação ou mudança de acesso/termos.
O recolhimento protegido pode ultrapassar 45 s, sem timeout adicional para
recuperar o handle de spawn e esperar o processo. Timeout/cancelamento/resultado
incerto continuam consumidos, sem reexecução. O relatório identifica esse limite
prático em vez de prometer teto absoluto de parede incluindo cleanup.

O diagnóstico é o mesmo do [candidato offline anterior](issue-5-nim-diagnostico-seguro-no-grafo-v1.md):
código estático depois da autoridade, tipos de quatro posições públicas,
cardinalidade e indicadores de duplicação/catálogo/hash quando avaliáveis.
Falha do observador não muda a aceitação original. `legacy_result` mantém o v2
literal falso; a prova atual distingue fake/live e só pode verificar live depois
de autorização/revisão/dispatch frescos, HTTP válido e autoridade raiz aceita.
Não há promessa de aceitação, aderência ou causa histórica recuperada.

## Verificação local

Passaram **17 testes raiz em 1,15 s** e **16 isolados em 6,59 s**, em sequência,
após a devolução explícita da janela de recuperação nativa de outra frente.
Ruff e formatação passaram nos sete arquivos Python novos. Nenhum worker desta
unidade permanece ativo. Os testes cobrem resposta já aberta,
framing e ausência de valores desconhecidos, inércia antes de efeitos, IDs
consumidos, mudança isolada de autorização, schema/payload imutáveis, StateGraph
e subgrafo compilados, worker raiz por IPC, PID/PPID reais, consumo único,
namespaces/symlinks, deadline e cancelamento antes/depois do dispatch. Uma falha
inventada anterior à resposta também foi testada com pai/filho reais e no grafo
completo: conserva metadados fechados
(`request_failed_outcome_uncertain`/`diagnostic_failed`), estado da autoridade
`not_invoked` e o relatório numérico, sem expor a exceção. O consumidor novo
valida a lista fechada de códigos já usada pelo transporte, inclusive essa
falha; não foi alterado o consumidor restrito da versão offline anterior.

Todos os envelopes são falsos e o modo fake marca zero HTTP real/verificação
falsa, inclusive quando a seleção é aceita. Não houve treino, VLM, execução de
modelo, nova dependência, holdout ou alteração da principal. Todos os workers
de testes foram encerrados e recolhidos. Os ledgers consumidos não foram abertos
ou modificados nesta preparação.

O [plano inerte](../orchestration/fixtures/nim-diagnostic-attempt-inert-v1-plan.json)
fixa 15 arquivos e também verifica os planos/fontes predecessores. O selo fica
fora de sua própria lista para evitar autorreferência. Hashes finais:

| Artefato | SHA-256 |
| --- | --- |
| Plano | `e2d7a12671d39c00b4033771d9022b374d1f4fc30c8d49a3d550d25d302c7067` |
| Configuração | `67f24c51aa23a306b215dfc78bfbd2b279a1edce0edebf67294dc066c649bff6` |
| Helper HTTP aberto | `2b929984f5443d0fdd2e056eadbe5f374eec2fa085d8af5fc11629b5068527be` |
| Worker fino | `921fd34edfbabe455b1b65965622e78b4acbcbc42d30d81edf09cf99c393be60` |
| Contrato da tentativa | `fbeffa22d41518592ac413e054b93ecd48071851a58f3184545e14bc99f3b257` |
| EntryPoint | `ed6a434b0ecabfe3d6b65c81152f7aed87e2977af7bd6d8ed7c7bb1e337e1b8e` |

Para reproduzir apenas os checks falsos, use caminhos absolutos dos ambientes
existentes em `AUDIT_ROOT_PYTHON` e `AUDIT_GRAPH_PYTHON`. Na raiz:

```sh
rtk proxy "$AUDIT_ROOT_PYTHON" -m pytest -q tests/test_nim_diagnostic_http_adapter_v1.py
```

Em `orchestration/`:

```sh
rtk proxy env GALAXIES_ROOT_PYTHON="$AUDIT_ROOT_PYTHON" "$AUDIT_GRAPH_PYTHON" -m pytest -q tests/test_nim_diagnostic_attempt_v1.py
```

Após o commit: revisão independente e importação sequencial pelo escritor da
principal. Nenhum comando de POST deve ser executado com este candidato inerte;
a execução remota continua pendente do pai/usuário e de registro técnico novo.

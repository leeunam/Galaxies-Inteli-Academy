# Issue #5 — liberação sintética única, preparação para revisão técnica

Unidade aditiva sobre `c108b245`, no clone independente. Não altera v1 consumido,
v3 offline, fontes seladas, planos ou recibos anteriores. Nenhum envio nesta
preparação; a execução depende da revisão técnica concreta do novo plano.

## Base financeira e autorização

O usuário confirmou especificamente que a API NVIDIA **do projeto** está no plano
gratuito: mensagem `Sentinel_e945b14459008191a932c869a4216aef`, 21/10/2026 00:20 UTC
(20/10, 21:20 de São Paulo). Retém-se apenas o fato sanitizado e o ID da declaração,
sem chave, identidade pessoal, saldo ou configuração. A declaração, combinada com
as fontes oficiais já verificadas sobre o catálogo/prototipação gratuitos, sustenta
R$0 para esta única tentativa delimitada; não há condição concreta contraditória
conhecida. Não se exige garantia genérica sobre outras modalidades de conta.

Fontes: [NIM para desenvolvedores](https://developer.nvidia.com/nim),
[FAQ oficial](https://docs.api.nvidia.com/nim/docs/product) e
[oferta do modelo](https://build.nvidia.com/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning).
O recibo distingue essa base de autorização de uma medição financeira: custo
observado permanece nulo/indisponível, nunca inventado como medição de R$0.

## Contrato novo e helpers preservados

`nim_release_contract_v1` fixa a mesma rota, modelo e bytes de payload/fixture
públicos: uma tentativa, 2.048 tokens, 45 segundos totais, 16 KiB de corpo e R$0.
Sem proxy, SDK, retry, redirect, fallback, reparo ou dados privados. O endpoint é
`https://integrate.api.nvidia.com/v1/chat/completions`, modelo
`nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`.

São reutilizados por identidade verificada o cliente/ponte/autoridade, a projeção
IPC corrigida, o ambiente literal e `bounded_child` com posse protegida do spawn,
prazo externo, encerramento de grupo e recolhimento. O plano v3 continua
`remote_execution_released=false` e seu selo remoto continua `None`.

O novo ledger fixo é `data/private/issue-5-nim-release-v1/`. Usa o codec de consumo
v3 (`reservation-v3.json`, `dispatch-v3.json`, `result-v3.json`), ligado ao **novo**
hash de plano, mais `release-binding.json` com protocolo de liberação, configuração,
evidência financeira e hash da revisão. Não reutiliza nem reabre ledger antigo.
A própria existência da pasta consome a tentativa. O filho revalida plano, revisão,
binding, nonce/PID e despacho exclusivo durável antes de ler o segredo ou abrir HTTP.
Qualquer falha, timeout, cancelamento, 429/503 ou 200 rejeitado consome a tentativa.

Só o filho liberado pode chamar o getter existente, dentro da árvore principal
integrada e vinculada à revisão privada. A credencial não entra em ambiente
herdado, argumentos, tracing, stdout, recibos ou cópias no clone. O recibo privado
contém o SHA do caminho real do checkout revisado, comparado ao `ROOT` derivado do
código, sem parâmetro público para substituí-lo. Copiar a revisão para outro
checkout falha antes de reservar. O localizador absoluto não entra no código ou
plano públicos. As simulações identificadas usam apenas a chave inventada e recusam os
ledgers reais v1/v3/liberação/revisão.

## Revisão e integração antes de executar

O plano novo exige recibo em
`data/private/issue-5-nim-release-v1-review/technical-review.json`, criado pelo
operador/escritor somente após a revisão do supervisor. Campos exatos: `protocol`,
`decision=approved_for_one_synthetic_attempt`, `plan_sha256`,
`configuration_sha256`, `financial_evidence_id`, `reviewer_thread_id` e
`source_message_id` e `execution_root_sha256`. Este último é o SHA-256 dos bytes
UTF-8 de `str(ROOT.resolve())` no checkout efetivamente revisado; só o escritor
registra esse vínculo no recibo privado. Não há comando neste pacote que aprove
a própria liberação.
É uma guarda de integridade/coordenação em armazenamento do operador; não é
autenticação criptográfica contra alguém capaz de reescrever os arquivos locais.

O escritor único precisa importar estas adições por fetch local/cherry-pick antes
de congelar nova fila VLM. Assim o filho usa a origem existente do segredo, sem
copiar `.env`. A revisão vinculada ao plano não libera VLM, mídia, holdout ou outra
chamada NIM. Não mudar pasta local ou referências históricas pelo nome novo do repo.

Depois da revisão técnica e integração, o operador executa uma única vez na raiz:

```sh
rtk proxy .venv/bin/python -B -m scripts.nim_release_v1 --execute-reviewed-once
```

Não executar esse comando durante esta preparação, nem repetir após resultado
incerto/rejeitado. Nenhum argumento permite escolher endpoint/modelo/payload/ledger.
Sem a flag, a CLI não executa. Simulações offline exigem diretório novo e são
explicitamente marcadas; não criam autorização remota.

Persistem os limites de crash durability/cleanup documentados na v3: fsync requer
filesystem que o honre; restauração/exclusão manual pode invalidar o consumo;
morte forçada do pai pode deixar filho vivo. O prazo inclui startup/HTTP/validação
no pai, mas recolhimento/persistência final podem terminar depois. Os 16 KiB são
de corpo, não de tráfego TCP/TLS. Esta tentativa não conclui a #5 ou valida dados reais.

## Checkpoint pronto para revisão técnica

Plano novo: `d759db319dd09bc6f2037c430d053e0563dfb07c47eacc186172c3caab50bf1b`.
Configuração: `042d4f6ae88900e3f20cac6a5d10c9cbb10e98f70eed6251f9d071499c9f259d`.
O plano vincula seis arquivos adicionais e verifica os 130 pins do predecessor
v3, cujo plano permanece
`22713f5a7cc5f067ef330470f13f9d0c24698b8002a2c8af5938e2cf8581d9b5`.
Fixture e payload são idênticos à v3, sem endpoint ou conteúdo novo.

Passaram **131 testes em 14,32 s**: 23 novos da liberação e os 108 direcionados
anteriores. Ruff/formatação dos cinco arquivos novos passaram. A preparação foi
pausada durante toda a janela VLM; esses checks ocorreram somente após o sinal
de encerramento/auditoria do supervisor, em sequência e sem inferência/ML.

As regressões cobrem revisão ausente/incorreta, raiz diferente antes de reserva,
alteração da evidência financeira/endpoint, binding/nonce inválidos antes do
getter, ordem do despacho durável, 200 válido/rejeitado, redirecionamento,
429/503, segredo inventado, cancelamento e recusa de repetição. A guarda de
simulação recusa v1 consumido, v3, release/revisão e seus descendentes, sem ler
seus conteúdos; symlinks também são recusados. A chave e os transports dos testes
são explicitamente inventados. Os testes v3 preservam concorrência, crash,
timeout, posse de spawn, limites e fronteira IPC já corrigida.

A revisão estática do supervisor removeu o localizador pessoal absoluto do
contrato público antes de selar: o vínculo do checkout fica no recibo privado.
Somente arquivos novos foram acrescentados; o contrato v3 false/None e suas
fontes/planos anteriores não mudaram. Nenhum recibo de revisão técnica real,
reserva ou ledger de liberação foi criado nesta preparação. Esse checkpoint
entrega um candidato revisável, não declara a chamada já liberada ou executada.

Reprodução offline no checkout, usando apenas ambientes existentes:

```sh
rtk proxy .venv/bin/python -B -m pytest -q tests/test_nim_release_v1.py tests/test_nim_dispatch_v3.py tests/test_selection_observation_v2.py
```

No clone sem ambiente próprio, usar o executável raiz existente em leitura, com
cwd neste clone. Não instalar/sincronizar ou redirecionar `ROOT` para outra árvore.
O JUnit e a conferência da preparação ficam no namespace privado novo
`data/private/issue-5-nim-release-v1-preparation/` do clone.

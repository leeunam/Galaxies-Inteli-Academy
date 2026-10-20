# Issue #5 — dispatcher v3 preparado somente offline

## Escopo e desenho

Esta unidade prepara um novo caminho aditivo, sem executar inferência remota,
ler credenciais ou reutilizar a autorização/ledger v1 consumidos. A base é
`9c4177a4ddc3b44710d0b39435d1df02d4f2201e`, em clone Git independente.
Fontes e validadores anteriores permanecem selados e inalterados.

O plano público v3 fixa endpoint, modelo, fixture inventada, corpo do pedido,
fontes e limites: uma tentativa, 2.048 tokens, 45 segundos totais e 16 KiB.
O selo externo confere os bytes do plano. A liberação remota permanece ausente;
um campo `max_spend_brl=0` expressa um limite, sem provar gratuidade da conta.

O pai valida o plano antes de reservar uma pasta exclusiva. A própria existência
da pasta significa consumo, mesmo se houver crash antes do recibo. Escritas usam
exclusividade e `fsync` de arquivo e diretório. Um nonce anônimo vincula o filho
ao pai vivo; o filho revalida os vínculos, grava despacho exclusivo e só então
abre o transporte. Falha, cancelamento, timeout ou resultado incerto consomem a
tentativa. O pai mata/recolhe o grupo do filho ao vencer o prazo.

Uma conexão HTTPS direta, sem SDK/proxy/retry/redirect, aceita exclusivamente o
corpo fixo. A credencial futura entra apenas no cabeçalho, dentro do filho.
O ambiente do filho é construído por lista permitida, sem credencial, tracing,
proxy, caminhos de importação herdados ou certificados substitutos. Nesta unidade
o caminho offline aceita apenas casos falsos identificados e uma chave inventada
constante. O pai público oferece somente simulação. A função futura de despacho
remoto usa um ledger fixo, sem argumentos de endpoint/modelo/payload/pasta, e o
filho correspondente revalida a liberação antes de abrir a chave. O plano atual
é recusado por ambos. Liberá-lo exige outra revisão de plano, contrato e selo;
alterar um booleano de custo ou só o selo externo não basta.

A resposta é observada e validada no mesmo processo, pela sessão sintética e ponte
v2 existentes, antes de qualquer stdout. O pai confere uma projeção estrita de
códigos locais, limites e IDs públicos. Não se retêm corpo, cabeçalhos, exceções,
hashes arbitrários ou campos desconhecidos. Não há modo para payloads livres.

## Alternativas consideradas

- Reusar o probe v1 exigiria tocar fontes seladas e arriscaria confundir o ledger
  consumido com nova autorização. Rejeitado.
- Acrescentar um callback remoto ao grafo v2 preservaria observação, mas deixaria
  a abertura HTTP e o deadline externo sem uma fronteira própria. Rejeitado.
- Um novo pai/filho limitado reaproveita a autoridade v2 em memória e mantém
  liberação, consumo e sanitização explícitos. Escolhido.

## Limites de durabilidade

O protocolo assume filesystem local que honre `O_EXCL`, `mkdir` e `fsync`, árvore
sob controle do operador e ausência de alteração concorrente das fontes. Não é
proteção contra root, exclusão manual, restauração de snapshot, clone do ledger,
hardware que minta sobre flush ou perda do dispositivo. Não prova exactly-once
no provedor: após envio incerto, a política é nunca repetir. O prazo de 45 s
limita a operação no pai; recolhimento e persistência final podem terminar depois.
O spawn é mantido como tarefa protegida: cancelamento antes da atribuição do
handle recupera a posse do filho para matá-lo/recolhê-lo, sem liberar nonce nem
iniciar despacho. Cancelamentos repetidos durante essa limpeza não perdem a posse.
Uma criação de processo presa no sistema pode atrasar a recuperação do handle.
Morte forçada do próprio pai/supervisor ou falha do host pode deixar um filho
vivo; não se promete limpeza instantânea nessa situação. O consumo durável e a
recusa de retomada permanecem necessários. A CLI futura não pode repetir uma
tentativa para descobrir se um filho órfão chegou a enviar.

## Verificação planejada

Testes offline com transportes/respostas falsos: validação antes de despacho,
reserva concorrente, crash/consumo incerto, nonce/PID, recusa de redirecionamento,
limites e timeout, protocolo HTTP/IPC, sanitização e dados desconhecidos.
Nenhum teste usa socket remoto ou credencial existente. Executáveis são lidos
dos ambientes existentes, com imports do clone e sem instalação.

## Custo e prontidão

Em 20/10/2026, somente leitura pública, sem login/API de inferência:

- A [página do modelo](https://build.nvidia.com/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning)
  anuncia endpoint gratuito disponível, no endpoint/modelo fixados neste plano.
- O [FAQ oficial](https://docs.api.nvidia.com/nim/docs/product) descreve acesso
  gratuito a endpoints para prototipação por membros do Developer Program e
  separa esse uso de implantação em produção com AI Enterprise.
- Os [termos de avaliação, seção 1.4](https://assets.ngc.nvidia.com/products/api-catalog/legal/NVIDIA%20API%20Trial%20Terms%20of%20Service.pdf)
  descrevem limites/créditos de avaliação e assinatura separada após seu consumo.
  A consulta não aceitou termos nem alterou conta/plano.

Isso sustenta a existência da oferta pública; não identifica o enquadramento da
chave já existente. **Lacuna concreta:** não foi verificado se esse acesso pertence
ao Developer Program/endpoint gratuito, quais limites/créditos se aplicam agora,
nem se há assinatura/cobrança associada ao acesso. Não se consultaram credenciais,
painel de conta, saldo ou faturamento. A oferta pública não é recibo financeiro.
Logo, não se garante R$0 aplicável à tentativa futura e nenhum envio é liberado.

O [card do modelo](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-nano-omni-30b-a3b-reasoning)
continua indicando inglês apenas; esta fixture mede seleção fechada de IDs,
sem validar linguagem livre/aderência ou comportamento real do provedor.
Esta unidade não conclui a issue #5, o grafo remoto ou o aceite científico.

## Resultado offline inicial e revisão (`ed5b0e5`)

Passaram **86 testes direcionados em 7,66 s**, sendo 63 novos do dispatcher e
23 da observação v2 existente. Ruff e formatação dos oito arquivos Python novos
passaram. Não houve suíte completa, instalação, ML, mídia, chamada NIM ou leitura
de credencial. A sessão anterior teve 80 passes e uma falha no próprio teste de
ambiente (sentinela impedia introspecção de pytest); corrigido antes da repetição.
Não se atribui à entrega a suíte histórica de 748 testes.

A revisão do supervisor identificou cancelamento durante criação do filho antes
da atribuição do handle. A correção retém/protege a tarefa de spawn e sua posse;
testes reais de subprocesso cobrem cancelamento repetido nessa janela, timeout
nessa janela sem envio de nonce, cancelamento posterior, crash e saída excedida.
Os testes também cobrem concorrência entre quatro processos, falhas de flush e
persistência, recusa de diretório incerto, vínculo nonce/PID, segredo inventado
em campo/ID/hash/cabeçalho/exceção, protocolo, redirecionamento e limites.

A revisão local conferiu: somente arquivos novos, nenhuma fonte selada alterada;
nenhum import redirecionado ao repositório vivo; nenhum cliente com retries;
ambiente literal sem proxies/chaves/tracing; resposta bruta não atravessa stdout;
plano/fixture revalidados no pai e no filho. O limite de 16 KiB aplica-se ao corpo
HTTP capturado. Headers são rejeitados se excederem 16 KiB após o parsing do
cliente padrão (que tem limites próprios de parsing); não é um teto de bytes
TCP/TLS ou de memória total do cliente. Não se aceita compressão nem framing
ambíguo. Não há tentativa de consertar ou repetir resposta rejeitada.

Plano inicial: `a89c20c3163ec11e4c72a6f22f5922f6c8fb986a1b8749eae31a412af7bb3c11`,
com **130 fontes Python** vinculadas; fixture pública permanece
`0fb7b9797cd41f53c3f127b0d2f6f934d0696aa3ba288852f5cff616455cf438`.
O selo externo é separado para evitar vínculo circular. Relatório/testes podem
evoluir sem mudar o pedido; mudar fonte vinculada exige recongelar/revisar plano.
Conferência pós-testes: 130 hashes iguais, nenhum worker v3 ativo, nenhum ledger
remoto v3 criado, clone sem alternates e sem compartilhamento por hardlinks.

## Correção posterior da fronteira IPC do pai

A revisão independente do canal principal encontrou uma inconsistência no commit
`ed5b0e5`: o pai aceitava um resumo que declarava sucesso com IDs públicos
repetidos, embora a autoridade selada rejeite duplicatas. Também aceitava sucesso
com `wire_bytes=0`. Não foi observado o worker honesto produzir esses estados;
o problema era a conferência insuficiente de uma mensagem IPC inconsistente.
A entrega inicial permanece no histórico e não contém a correção abaixo.

O contrato aditivo agora exige IDs únicos para `accepted`. O diagnóstico
`duplicate_evidence_id` continua permitindo a projeção canônica pública com IDs
repetidos, mas exige `selection_validated=false`, `authority_status=rejected` e
duplicatas presentes. Ambos exigem HTTP 200, contagem de tokens conhecida e corpo
de 1 a 16.384 bytes. Projeção ausente, IDs únicos sob diagnóstico de duplicatas,
sucesso sem bytes e combinações inconsistentes são recusados pelo pai.

A regressão usa resultados reais da autoridade/v2 sobre respostas inventadas,
corrompe somente a mensagem do filho e passa os bytes por subprocesso até
`bounded_child`/`inspect_child`. Confere aceitação única, diagnóstico de duplicatas
rejeitadas, rejeição sem projeção e contradições de status/projeção/metadados.
Não é uma cópia do predicado de unicidade. Antes da correção, oito dos dezenove
primeiros cenários novos falharam, reproduzindo a insuficiência. Uma verificação
intermediária passou em 105 testes/11,19 s; o complemento de zero bytes foi
acrescentado depois e tem verificação final própria.

Plano corrigido: `22713f5a7cc5f067ef330470f13f9d0c24698b8002a2c8af5938e2cf8581d9b5`.
Somente o hash da fonte v3 afetada mudou entre os 130 pins; payload e fixture
continuam iguais. Os validadores v2 e demais fontes seladas permanecem intactos.
O plano mantém `remote_execution_released=false` e o selo remoto permanece `None`.

Verificação final da correção: **108 testes direcionados passaram em 8,84 s**
(85 do dispatcher, incluindo 21 cenários na fronteira IPC, e 23 da observação v2).
Ruff e formatação passaram nos oito arquivos v3. Nenhuma inferência remota,
credencial real, instalação ou teste pesado; nenhum processo de teste/v3 ativo
ao terminar. O pedido continua inteiramente inventado e o ledger remoto v3 não
foi criado. O comando de reprodução abaixo cobre também esta correção.

## Reprodução segura

No clone `/tmp/galaxies-nim-dispatch-v3`, com cwd explícito, usar somente o Python
existente em leitura; os imports são resolvidos a partir deste clone:

```sh
rtk proxy /home/inteli/Documents/projetos/Galaxies-Inteli-Academy/.venv/bin/python -m pytest -q tests/test_nim_dispatch_v3.py tests/test_selection_observation_v2.py
rtk proxy /home/inteli/Documents/projetos/Galaxies-Inteli-Academy/.venv/bin/python -m scripts.nim_dispatch_v3 --offline-case valid --output-dir /tmp/galaxies-v3-simulacao-nova
```

A simulação exige diretório novo e registra `offline_simulation_only=true`,
`real_requests=0`, `retry_allowed=false`. Uma pasta consumida, mesmo vazia, nunca
é retomada. O comando é exclusivamente offline; não executar o probe v1 nem
copiar seu ledger. Testes usam pastas temporárias próprias, sem tocar a fila real.
Não houve push nem integração na árvore principal. A passagem entrega código,
testes e plano para revisão; a execução remota depende de evidência da conta e
de um novo congelamento revisado, jamais de reaproveitar o plano offline atual.

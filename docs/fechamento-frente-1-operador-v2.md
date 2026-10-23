# iSee — operador diagnóstico v2, ainda sem execução

A revisão independente do operador `07bea00` encontrou um P2: o início do
preflight só era persistido depois do filho. Uma queda antes do recibo permitia
repetir a preparação e reiniciar os 120 segundos. Nenhum preflight real ou modelo
foi iniciado; o plano e operador v1 permanecem preservados e não aprovados.

`scripts/front1_positive_diagnostic_v2.py` usa outro namespace. Antes de qualquer
filho, cria `preflight-reservation.json` de forma exclusiva, privada e durável,
com plano, hashes dos recibos externos, início, deadline e identidade do operador.
Falha, queda ou arquivo parcial mantêm essa tentativa consumida; outra invocação
não pode recriar o marcador. O recibo pós-filho vincula seu hash à primeira reserva.
A execução usa o deadline dessa reserva, limitado também pela autoridade vigente.
Não há reancoragem por recibo novo, nova invocação ou novo slot de recursos.

Permanecem uma chamada de modelo, CPU4, RSS cooperativo 3,3 GiB,
MemAvailable ≥6 GiB, 75 segundos úteis +5 de encerramento e 120 segundos desde
a primeira reserva de preflight. Autoridade humana nova, revisão independente
e slot do coordenador continuam obrigatórios; a v2 exige decisões de autorização
e revisão próprias, vinculadas ao novo plano. Ela não escreve esses recibos.
A reserva de preflight registra zero chamadas de modelo e uma tentativa de
preparação: os dois contadores não são confundidos.

O slot é coordenação externa mais verificações locais; não existe mutex global
de CPU/RAM nem isolamento físico de recursos. O operador não impede processos
alheios de começar em outro host. Revalidar admissão antes do dispatch, mantendo
o acordo com o coordenador, sem ampliar infraestrutura.

Passaram **19 testes offline em 0,27 s**, incluindo falha imediatamente depois
da reserva, reentrada antes do recibo e duas reservas concorrentes com exatamente
um vencedor. Nenhum filho real, cápsula ou modelo foi usado nesses testes.
Os 17 testes anteriores e estes 19 se sobrepõem; não são 36 cenários distintos.
Ruff, formatação e diffcheck passaram. A guarda conserva as quatro conclusões
diagnósticas, sem aprovar atributos, auditoria, extração ou B/C.

Preparação offline nova: 0,8922 s, RSS 27.048 KiB, afinidade [0]. Pesos/runtime
foram novamente conferidos por streaming, sem carregar modelo; nenhum input
visual foi copiado. O contrato científico continua o da célula faltante descrita
no [handoff](fechamento-frente-1-qualidade-e-handoff.md), com a limitação obrigatória
de reconstrução estática do argv antigo. O coordenador revalidou independentemente
os cinco arquivos históricos e o HTTP 500 mais recente; isso não recupera o argv
que não foi persistido.

Evidências persistentes, relativas à raiz principal:

- `data/private/fechamento-20261023/frente-1/unit-4-operator-v2/`: pedido novo,
  comparação estática, prova de schema, preparação e `pytest.log`.
- `data/private/fechamento-20261023/frente-1/diagnostic-old-prompt-positive-v2/`:
  somente `plan.json` e `control_worker.py`; sem autorização, selo, slot, reserva,
  started ou preflight reais.
- Operador SHA-256:
  `50d936b77345715eb5fa8eb5e15d25e7b331de4c5227b0a90dff2bda1c31a7a0`.
- Plano lógico:
  `0ee4b4117ba8f6e3ea8b8d5d92816b48c6b79ba7eada1c4f0075ba25cdddd9e8`.
  SHA-256 dos bytes:
  `db36da9563c868938841babbf007a1d16ce172e2f3e9d47f3ea986e2f374f2ba`.

O pedido único será encaminhado pelo coordenador somente após a revisão da v2.
Os comandos futuros são o interpretador existente absoluto, `-B`, o novo
`control_worker.py` absoluto e `--preflight-only`; depois o mesmo comando sem a
última flag. Nenhum foi executado. Não reutilizar a v1 ou os saldos históricos.

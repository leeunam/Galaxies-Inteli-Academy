# Issue #5 — diagnóstico local após a tentativa consumida

Conferência de 20/10/2026. A [única chamada real](issue-5-nim-sintetico-unico-resultados.md)
continua consumida: HTTP 200,763 bytes,91 tokens,2,9134 s e
`selection_validated=false`. **Não houve chamada adicional**, retry, reparo
remoto ou fallback. As fontes, fixture, plano e recibos daquela execução
permanecem byte a byte iguais.

## O que os recibos demonstram

O adaptador recebeu um envelope HTTP que passou nas suas verificações de
tamanho, escolha única, papel, término normal e ausência de ferramentas.
O grafo/subgrafo executaram e não produziram uma seleção validada. O relatório
original permaneceu separado da explicação; não houve promoção de números ou
texto livre do provedor como fatos aceitos.

`graph-result.json` **não gravou `explanation.reason_code`**. O texto do conteúdo
também foi descartado. Portanto, não é possível identificar a regra específica
nem sequer afirmar que `validate_selection` chegou a ser executado. Não há
evidência suficiente para dizer que o provedor retornou JSON, hash ou IDs errados.
Essas são hipóteses possíveis, não causas identificadas. A ausência de telemetria
não autoriza repetir a operação para recuperar a resposta.

No código selado, `selection_validated=false` é o resumo de qualquer resultado
final incompleto. O caminho pode retornar `transport_failed` antes de chamar
o validador ou `invalid_selection` quando ele recusa a seleção. O rótulo
`reply_received` sozinho não distingue esses estágios posteriores.

## Replays inteiramente inventados, sem rede

O módulo novo `orchestration/galaxies_orchestration/nim_replay.py` é aditivo.
Ele executa o mesmo `StateGraph`, `RootWorker`, `OneShotNim`, `bounded_child` e
parser HTTP selados. O processo filho HTTP é substituído por um simulador
explicitamente offline que usa `perform_http` com `FakeConnection`.
Sockets, DNS e busca da chave são bloqueados. O filho não recebe NVIDIA_API_KEY
e só usa um literal de chave inventado no objeto falso.

O validador roda no processo raiz real, pelo mesmo protocolo JSON/stdio. Cada
replay usa pasta temporária e cópia do plano; o ledger da chamada real fica em
leitura. Os contadores de tentativas dos ledgers temporários representam
**simulações**, nunca chamadas externas novas. As respostas são fabricadas pelo
código, sem pretender reconstruir ou reproduzir a resposta histórica.

| Conteúdo inventado | Envelope simulado | Seleção validada | Código final observado |
| --- | --- | --- | --- |
| JSON válido, SHA e IDs do catálogo | `reply_received` | **Sim** | nenhum |
| Texto sem JSON | `reply_received` | Não | `invalid_selection` |
| SHA de outro pacote | `reply_received` | Não | `invalid_selection` |
| ID ausente do catálogo | `reply_received` | Não | `invalid_selection` |
| Chave JSON repetida | `reply_received` | Não | `invalid_selection` |
| String com surrogate Unicode inválido | `reply_received` | Não | **`transport_failed`** |

O último caso falha ao codificar UTF-8 no nó de seleção, **antes** do validador
raiz. Ele reproduz o par de estados `reply_received`/`selection_validated=false`
por um estágio diferente dos quatro casos anteriores. Não demonstra que tenha
ocorrido Unicode inválido na chamada real. Demonstra que o resumo disponível
não identifica seu estágio de falha.

O caso válido atravessou grafo, processo adaptador e processo raiz/validador,
com q50 inventado 123 preservado. Os demais casos também preservaram a análise.
Não foi encontrada falha funcional local confirmada que justificasse alterar
ou relaxar o contrato. A limitação confirmada é a telemetria insuficiente da
tentativa original; o novo replay registra o código final somente nos exemplos
offline. Não se alterou retrospectivamente o recibo real para incluir esse código.

## Reprodução, verificação e limites

No projeto `orchestration/`, com os dois ambientes disponíveis:

```sh
rtk proxy .venv/bin/python -m pytest -q
rtk proxy timeout 20s .venv/bin/python -m galaxies_orchestration.nim_replay --case valid
rtk proxy timeout 20s .venv/bin/python -m galaxies_orchestration.nim_replay --case invalid_json
rtk proxy timeout 20s .venv/bin/python -m galaxies_orchestration.nim_replay --case wrong_hash
rtk proxy timeout 20s .venv/bin/python -m galaxies_orchestration.nim_replay --case unknown_id
rtk proxy timeout 20s .venv/bin/python -m galaxies_orchestration.nim_replay --case duplicate_key
rtk proxy timeout 20s .venv/bin/python -m galaxies_orchestration.nim_replay --case invalid_unicode
```

Os testes usam plano público inventado e âncora de teste temporária em memória.
O CLI usa uma cópia byte a byte do plano privado já selado: exige sua presença
local, mas não altera esse plano ou a autorização consumida. Executar cada CLI
independentemente, como acima; não usar `nim_probe --execute-authorized-once`.

Passaram **45 testes isolados em 6,84 s**, incluindo os seis novos com processos
reais, e **seis CLIs independentes** produziram os estados da tabela. Ruff e
formatação de 145 arquivos passaram. A suíte completa da raiz permanece a
executada uma vez em `c0ef8ab`: **748 testes/575,14 s**. O código/dependências
da raiz e as fontes seladas não mudaram após essa suíte; o novo código fica
somente no projeto isolado, cuja suíte foi executada completa.

Um lote auxiliar com vários replays no mesmo loop não produziu recibo final e
foi encerrado localmente (saída 143); um launcher Python aninhado também falhou.
Não foram contados como replays concluídos, e a causa desses runners auxiliares
não foi identificada. Os recibos preservam essas limitações, sem atribuí-las ao
provedor. A evidência verificável usada aqui é a suíte e os seis comandos CLI
independentes acima, não esses lotes incompletos.

Recibos em `data/private/issue-5-nim-diagnostico-offline-v1/`, incluindo as
interrupções auxiliares, `replays.json` e conferência final. São 703 hashes
protegidos:695 anteriores mais recibos reais/selo. M1/A200, lock/runtime raiz,
holdout, oito PNGs, filas V9 e README não rastreado continuam preservados.

Para validar o contrato **remoto** ainda seria necessária outra rodada com nova
autorização e desenho de telemetria sanitizada que registre estágio/código sem
corpo bruto, credencial ou dado privado. Nenhuma nova autorização é presumida.
Uma futura mudança deve ter versão própria e preservar o código desta execução.
A decisão de C segue pendente e não interferiu neste diagnóstico local.

# iSee — diagnóstico v2 parado no preflight

23/10/2026. A autorização humana específica e a revisão independente foram
recebidas pelo Chat 3, que concedeu o slot e o GO condicionado aos gates.
A tentativa executou **um preflight e zero chamadas de modelo**. O namespace
necessário à cápsula foi recusado; não houve nova resposta perceptiva.

## Execução e evidência terminal

| Medida | Resultado |
| --- | --- |
| RAM disponível na admissão | 6.738.432.000 bytes, aproximadamente 6,276 GiB |
| Hashes de autoridade/revisão/slot/plano/operador | Conferidos antes da tentativa |
| Preflight reservado antes do filho | Uma tentativa, persistida e sincronizada |
| Resultado do filho | `child_failed`, returncode 1 |
| Diagnóstico observado | `bwrap: No permissions to create a new namespace` |
| Duração do filho / envelope externo | 0,0020 s / 0,1123 s |
| Pico RSS do preflight | 35.348.480 bytes, aproximadamente 33,71 MiB |
| Limpeza do filho | Confirmada |
| `started.json`, ledger de modelo, captures ou scratch | Ausentes |
| Reserva/chamada de modelo | Zero / zero |

O erro observado não demonstra que o kernel da máquina inteira esteja
globalmente configurado dessa forma. O recibo registra uma recusa na execução
atual; a distinção entre restrição do ambiente de execução e política global
não foi investigada por sondas adicionais.

Foi executado exatamente o argv absoluto revisado com `--preflight-only`.
Como esse passo falhou, o comando sem flag **não foi iniciado**. Não houve retry,
outro sandbox/argv, escalada, alteração de namespaces do sistema, limpeza global
de cache ou mudança de swap. O coordenador confirmou STOP e liberação do slot
operacional em mensagem, preservando os recibos existentes.

## Contagem, preservação e limites

A sentinela v2 mantém uma tentativa de preflight consumida, vinculada à primeira
reserva e seu deadline. Isso não deve ser contado como chamada VLM. Embora o
modelo não tenha sido reservado, esta rodada não oferece saldo reutilizável ou
permissão para repetir a preparação. Uma nova tentativa depende de outra
decisão/protocolo; não foi criada ou solicitada automaticamente.

No diretório persistente `data/private/fechamento-20261023/frente-1/`:

- `diagnostic-old-prompt-positive-v2/` preserva plano, operador, autorização,
  revisão, slot, revisão independente, `preflight-reservation.json` e
  `preflight.json`, sem sobrescrita.
- `unit-4-operator-v2/admission.json` e `live-preflight.stdout`/`.stderr`
  preservam a admissão e o envelope da falha.
- `unit-4-operator-v2/execution-terminal.json` é uma **reconciliação do caller
  sobre a falha de preflight**, não um terminal produzido pelo operador de
  inferência. Identifica `preflight_rejected_namespace_creation`, zero modelo,
  limpeza e ausência de novos resultados perceptivos. Hash lógico:
  `ab639d52d381784a8b810e4657443e55b9e9ddaf7be9e283ffb6ad0425d615f8`.
- SHA-256 da primeira reserva de preflight:
  `7beee5e192cf81676609e0fa0d6e8da69f9b296393491ac3d4f74fdb38e34960`.

Um teste offline adicional reproduziu a recusa de namespace por callback
inventado e confirmou persistência, zero reserva de modelo e recusa de repetição.
A seleção final de **20 testes** passou; ela se sobrepõe aos 19 anteriores e
não constitui uma segunda execução real. Não houve alteração no operador/plano
congelados após a autorização. Log: `unit-4-operator-v2/pytest-after-stop.log`.

## Consequência para a Frente 1

A hipótese do prompt antigo no positivo continua sem resultado. A execução
não modifica a reprovação perceptiva do último contraste, não avalia a capacidade
do VLM e não libera nenhum campo. Os 269 sidecars uniformes, QualityRelease,
contrato observado final e B/C completos permanecem abertos. A200 servido,
comparadores cacheados, coorte 300, partições 203/66/31 e holdout foram preservados.

O próximo passo justificável é uma proposta explícita que resolva a viabilidade
da cápsula no ambiente permitido, preservando isolamento, comando revisado,
recibos e limites, antes de qualquer novo ensaio perceptivo. Não é uma correção
de percepção e não autoriza reduzir proteções ou consumir a mesma autorização.

# Probe técnico de recursos — proposta inerte

Esta unidade prepara **uma chamada Dneg**, ainda sem autorização de inferência. O objetivo é medir CPU, faults, memória e pressão durante o mesmo processo que já possui captura durável. Um timeout com prefixo válido pode fornecer informação técnica. Não é comparação perceptiva, auditoria independente, correção demonstrada do VLM ou liberação de atributos/B/C.

O namespace novo é `issue-4-vlm-resource-probe-v1`. As filas v1/v2/v3 permanecem seladas e seus saldos encerrados. O falso positivo Dneg anterior continua válido. Não há retry, retomada, aumento automático de prazo, downloads, envio externo ou custo externo. A preparação offline e os testes não executam pesos.

## Identidade e limites

| Item | Contrato fixado |
|---|---|
| Entrada única | `negative-D`, PNG SHA-256 `ee884ab32ba1535291932d38b19f867e28cd833f3e5c1fe6c8dd49228d7ce998` |
| Geometria | RGB 360 × 640, bytes congelados, sem reprocessamento |
| Configuração | Mesmo argv efetivo, pesos/runtime, prompt/schema, seed 42, CPU 4, GPU 0, limites de imagem 1024/1024 e geração 64 da v3 |
| Gate original | 1075 tokens **observados**, decode completo, schema válido e cleanup confirmado; telemetria não substitui nenhum deles |
| Orçamento proposto | 1 dispatch de até 80 s: 75 úteis + 5 para limpeza; até 100 s globais desde o preflight até o pós-processamento |
| Recursos | RSS 3379,2 MiB; stdout 16 KiB; stderr 256 KiB; mesmos limites existentes |
| Telemetria | Intervalo mínimo 250 ms, até 304 amostras, até 512 KiB persistidos; leitura individual até 16 KiB; teto acumulado de 3 s no corpo amostrado do sampler, dentro dos 75 s |
| Retenção | Mesma retenção dos PNGs congelados, 21/10/2026 às 23h59 de São Paulo |

O plano fixa ROOT por hash, fontes novas e herdadas, entrada, argv, política de telemetria, limites, plano/checkpoint v3 selados e revisor. A origem é o plano lógico v3 `39ec99f9783e91a99adc063d61541261aea4f62baaaae429b70c31d4c6f36dd3`, checkpoint `8b570f504f3a46c4d7fb993b1690eb7c3c168a4b1e3e80805317aac0e27d6ea4`. O próprio plano novo só existe depois da preparação no ROOT principal; nenhum plano real, PNG, autorização, review, reserva ou captura foi criado no clone.

## Reuso e coleta

`vlm_resource_probe_capture.py` repete apenas o roteamento/construtor/capture mecânicos da v3 para um namespace novo. Os métodos do Journal, streams, parser e coletor com ownership/cleanup são os congelados. O proxy `ObservedProcess` delega o PID real, pipes, retorno e wait; acrescenta somente observação em `.poll()`. Não há thread extra, novo dono, sinal de timer, PID inventado ou monkeypatch global.

O coletor existente mantém duas threads leitoras e consulta `.poll()` em seu laço de 50 ms. As leituras bloqueadas de stdout/stderr não bloqueiam esse laço. **250 ms é espaçamento mínimo, não garantia de frequência**: scheduler, RSS, leitura e fsync podem atrasá-lo. Cada amostra registra monotonic após leitura, duração da leitura e custo acumulado até a amostra anterior. O resumo registra primeiro/último timestamp, maior gap e custo medido; os intervalos são os observados.

O sampler lê somente os arquivos fixos de metadados do filho real: stat/status/cgroup, boot ID, namespace cgroup e arquivos fixos de CPU/PSI/memória/swap no escopo selecionado. Não lê environ, cmdline, mídia ou outro processo. Para provar o mapeamento do cgroup, o leaf precisa existir sem symlinks e `cgroup.procs` precisa conter o PID real; IDs alheios são descartados, sem abrir seus processos. Só então é permitido subir a um ancestral com cpu.max; o root sem esse arquivo é aceito com quota/período ausentes, sem período inventado. O scope é fixado por identidade/hash, com distância do ancestral, sem localizador cru nos registros.

Se o mapeamento não for demonstrável, os contadores do filho continuam disponíveis e cgroup/PSI ficam `mapping_unproven`; o resumo técnico é inconclusivo. Campos de memória ausentes após exit não viram zero. Mudança de boot, start_ticks, namespace, membership, scope, quota ou queda de contador invalida a comparação. Cgroup é compartilhado; seus deltas nunca são atribuídos exclusivamente ao filho.

CPU-time, minor/major faults e média de cores descrevem o **prefixo entre amostras**, não a chamada inteira ou uma fase isolada. A primeira amostra acontece após spawn e a última normalmente antecede saída/kill. Ao observar exit, o sampler encerra sem ler zeros; após timeout/cancelamento, não fabrica amostra terminal. Os eventos C++ e `phase_diagnostic` permanecem separados e preservam o gate original.

## Persistência e falhas

Cada registro completo de telemetria é escrito e recebe fsync antes de ser aceito em memória como amostra. Stdout continua no Journal original, com os mesmos bytes e fsync antes de devolver ao parser. `inspect` lê somente linhas completas dentro do teto, valida chaves/tipos/identidades/contadores e indica cauda truncada. O prefixo de telemetria é sempre provisório, nunca prova de terminal/cleanup. Apenas a inspeção original da captura pode comprovar término com seus recibos.

Custos do sampler são separados do filho: wall, CPU da thread via `thread_time`, leitura, escrita, fsync, bytes e contagem de fsync. Excluem criação/fsync inicial do arquivo, close e serialização do resumo final; em falha são limites inferiores. O registro durável contém custo até a amostra anterior; o resumo após retorno contém o custo do corpo inteiro amostrado. Um crash pode perder esse resumo e a medição da última escrita. Não há promessa contra SIGKILL, perda de energia, disco indisponível ou syscall de kernel bloqueada. O teto de overhead e os deadlines são verificados cooperativamente; não interrompem uma syscall bloqueada.

Falha crítica de identidade, parser, persistência, limite ou mudança de escopo volta pelo `.poll()` ao dono original, que mata/recolhe o mesmo grupo e mantém os recibos. Não há segundo dono. Falha de fsync durante a criação fecha o fd antes de sair. A primeira falha consome/encerra o slot e sela o namespace; uma resposta válida com telemetria inconclusiva não transforma o probe em êxito técnico. Resposta inválida, tokens incorretos ou timeout jamais são promovidos pela telemetria.

## Ganho discriminante e limites da conclusão

| Observação futura | O que permite avaliar | O que não demonstra |
|---|---|---|
| CPU do filho alta em relação ao wall amostrado, com pouco stall observado | Compatibilidade com trabalho de compute no prefixo | Causa exclusiva do atraso, velocidade sustentável ou suficiência de outro prazo |
| Major faults aumentam e PSI de memória/IO aumenta | Indícios contemporâneos de pressão/paginação no intervalo | Que toda pressão do cgroup veio do filho ou causou a diferença histórica |
| Throttling aumenta no escopo fixado | Restrição de CPU no cgroup durante o intervalo | Tempo perdido exclusivamente pelo VLM; ausência de restrição em ancestrais não amostrados |
| CPU baixa sem pressão nos dados disponíveis | Espera ou limitação não explicada pelos contadores coletados | Diagnóstico único ou autorização para modificar sistema/modelo |
| Scope indisponível, poucos pontos, mudança de identidade, falha ou prefixo curto | Inconclusivo, com os contadores parciais explicitados | Zeros, resposta completa, sucesso perceptivo ou motivo para repetir automaticamente |

Nenhum threshold de CPU/PSI/faults vira gate científico. A comparação histórica v2/v3 continua com causa desconhecida; esta instrumentação mede somente a futura chamada, se especificamente autorizada. Depois deste probe não há repetição automática, mesmo se ele terminar ou produzir informação insuficiente. Otimização de modelo, runtime, threads, dados, deadlines ou sistema exige outra proposta fundamentada e os gates originais continuam fechados.

## Preparação e autorização futura

Após revisão e integração, o integrador pode executar **somente a preparação offline** no ROOT principal:

```sh
rtk proxy .venv/bin/python -B -m scripts.vlm_resource_probe prepare
rtk proxy .venv/bin/python -B -m scripts.vlm_resource_probe inspect
```

Isso copia exatamente um PNG já congelado e cria plan/checkpoint zero no novo namespace. A verificação da cadeia herdada permanece somente leitura. Não cria autorização/review/started/reserva/capture. A CLI não aceita ROOT, modelo, payload, launcher ou aprovação arbitrários. `inspect` mostra slot não consumido separado de saldo autorizado, que permanece zero.

Antes de qualquer execução é indispensável uma **nova mensagem humana específica** autorizando 1 Dneg/80 s por dispatch/100 s globais, dados e limites deste plano, custo zero, sem retry, e revisão externa ligada ao hash do plano/configuração/fontes/ROOT/entrada/política e ao recibo dessa autorização. Não há writer de aprovação. IDs consumidos e pedidos genéricos conhecidos são recusados por hash; o parser de recibos não autentica sozinho a origem humana. O coordenador precisa conferir o transcript original, escopo e frescor antes de produzir o recibo externo. Sem ambos os recibos válidos, a execução recusa antes de lock/started/reserva/Popen.

A autorização geral para trabalho local cobre este código/testes e a preparação offline, não a chamada real. Nesta unidade não ocorreu inferência, benchmark, download, alteração de sistema, envio externo ou leitura semântica de mídia/holdout. Houve uma falha do transporte de exec antes da criação de um processo de edição; a reconexão foi confirmada por leitura e a edição então aplicada. Isso não informa a causa dos timeouts do VLM.

## Verificação offline

```sh
rtk proxy .venv/bin/python -B -m pytest -q -p no:cacheprovider tests/test_vlm_resource_probe.py
rtk proxy .venv/bin/ruff check --no-cache scripts/vlm_resource_telemetry.py scripts/vlm_resource_probe_capture.py scripts/vlm_resource_probe.py tests/test_vlm_resource_probe.py
rtk proxy .venv/bin/ruff format --check --no-cache scripts/vlm_resource_telemetry.py scripts/vlm_resource_probe_capture.py scripts/vlm_resource_probe.py tests/test_vlm_resource_probe.py
rtk git diff --check
```

Os testes usam apenas bytes inventados e filhos Python comuns: parsers, deltas, identidade/scope, logs parciais, bytes idênticos, timeout/cancelamento, pipes bloqueados, falha de metadados/fsync, limites, gate preservado, autoridade ausente e no-reentry. Medem observabilidade/ownership; não medem throughput de VLM nem validam percepção. Os 100 s são o teto proposto, sem extrapolar o tempo dos testes leves para a chamada real.

Resultado da rodada final: 39 testes passaram; zero falhas, erros ou skips. Ruff check e format passaram. O JUnit fica fora do repositório, apenas como recibo da verificação com dados inventados. Rodadas anteriores sobrepostas não são somadas.

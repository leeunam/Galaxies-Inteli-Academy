# Probe de recursos: timeout com prefixo de telemetria preservado

O [probe Dneg revisado](issue-4-vlm-resource-probe-proposta.md) executou
**uma inferência local**, com a autorização específica e o selo preservados.
Terminou por `native_timeout`, com captura terminal e limpeza confirmadas,
em **77,9790 s globais**. A reserva única está consumida e a fila selada,
`remaining_calls=0`, sem nova execução autorizada.

Houve dois pedidos de lançamento, com resultados distintos. O [primeiro](issue-4-vlm-resource-probe-bloqueio.md)
expirou na revisão automática antes de criar processo. Após classificação do
erro operacional, reconciliação do estado não consumido e esclarecimento do
supervisor, uma segunda solicitação do mesmo comando/ROOT/permissões foi
permitida. Somente ela criou processo, na sessão 8224. Não houve troca de rota,
fonte, parâmetros ou autorização, nem repetição de inferência. Os primeiros
recibos e logs vazios permanecem intactos.

## Captura e fase observada

| Medida | Resultado |
| --- | --- |
| Chamadas / controlador | 1 / saída 1 |
| Tempo do processo capturado | 74,4484 s |
| Último evento preservado | `encoder_start [1,1,3]` |
| Encoder concluído / decode observado | sem evento de conclusão / nenhum lote observado |
| Resposta / stdout | ausente / zero bytes |
| Total de tokens observado | não confirmado (`null`); gate de 1.075 não satisfeito |
| Retorno / limpeza | -9 / confirmada pelo coletor original |
| Decisão científica | `not_a_perceptual_comparison`, sem campos/candidatos liberados |

O diagnóstico de fase é `image_encoder`, como última fase observada. Não há
timer de encoder concluído: **não se atribuem os 74,4484 s inteiros ao encoder**.
CPU, faults e pressão abaixo não têm atribuição por fase. Não houve resposta
para nova avaliação perceptiva; o falso positivo Dneg anterior permanece.

## Recursos no prefixo amostrado

Foram preservadas **278 linhas completas, 315.274 bytes**, sem cauda truncada.
O intervalo entre primeira e última amostra foi **73,3171 s**, com maior gap
de 0,3000 s. A identidade de processo/boot/escopo permaneceu estável; o cgroup
foi demonstrado como disponível, no ancestral de distância 1. Quota sem teto
numérico (`null`), período de 100.000 µs nesse escopo.

| Medida do prefixo | Observado |
| --- | --- |
| CPU do filho user / system | 229,08 s / 4,28 s |
| Média de núcleos usados pelo filho | **3,1829**, sobre 73,3171 s amostrados |
| Minor / major faults do filho | 487.604 / 384 |
| Pico RSS amostrado do filho | 2.746,965 MiB |
| VmSwap amostrado do filho | zero em todas as amostras |
| Throttling no escopo compartilhado | deltas `nr_throttled=0`, `throttled_usec=0` |
| PSI compartilhado CPU some / full | 0,230839 s / 0,151875 s |
| PSI compartilhado memória some / full | 0,290355 s / 0,288471 s |
| PSI compartilhado I/O some / full | 0,250404 s / 0,229918 s |

Os 233,36 s de CPU do filho são compatíveis com trabalho computacional
importante nesse prefixo, com pouco stall medido no escopo observado. Não provam
causa única, frequência sustentada, comportamento térmico ou ausência de limites
em ancestrais não amostrados. Faults e PSI não demonstram que RAM causou a
lentidão histórica. PSI e CPU de cgroup são compartilhados; não se atribuem
exclusivamente ao filho, e seus intervalos não devem ser somados como atraso.

O prefixo não cobre a vida inteira do processo: a primeira amostra foi após
spawn e não se fabricou amostra depois do timeout/kill. `whole_lifetime_measured`
e `observed_exit` são false. A inspeção de telemetria permanece provisória;
o término/cleanup é comprovado separadamente pelo journal da captura.

## Custo da observação e encerramento

O corpo amostrado do sampler mediu **2,864240 s wall**, **1,020887 s de CPU da
thread**, **1,888689 s em 278 fsyncs**, 0,771098 s de leitura e 0,036932 s de
escrita. O custo ficou abaixo do teto cooperativo de 3 s e exclui setup, close
e serialização final do resumo. Os tempos de CPU/componentes não se somam ao wall
como custo adicional independente. A coleta é informativa, sem correção de
performance ou percepção demonstrada e sem garantia de conclusão futura.

O supervisor confirmou em leitura independente no **host**, com PID 1 `systemd`
e boot igual ao lease, que owner e leader estavam ausentes. Isso distingue
processos recolhidos de invisibilidade no namespace do executor. A leitura
adicional do integrador expirou no controle antes de criar processo e não foi
repetida; sua limitação e a origem independente da confirmação estão registradas.
Nenhum sinal adicional ou cleanup foi necessário na reconciliação. Não há
enumeração independente completa de membros residuais do PGID nesta evidência.

Plano lógico `ddf0da1e1ee9b915521fe4f780c45bd387c2f0545b8b4f575aa8d5166e22549f`,
arquivo `d7f1899b5890d887c7b4805a5f1a8fde72cef88625543a9add015311e3321c31`,
configuração `00aefd4e0efa20d34ce0301640910cf7853c1f601b8bb208cdf896ebf0d01fe2`.
As cinco fontes, argv, entrada, autorização e selo permaneceram iguais. O recibo
`result-1.json` tem SHA-256
`a054c9ab6b91029702a387e139fb2aaf03509eabe03cdb2fe1fa0a0a0666f0e0`.

Vinte e cinco arquivos pertinentes conferem; NIM sintético aceito, M1, partições,
teste reservado, PNGs, trio da demo e recibos anteriores preservados. Não houve
novo POST, download, teste, benchmark, alteração do sistema ou de fontes/limites.
Mantêm-se 80 s por dispatch/100 s globais e retenção até 21/10, 23h59 São Paulo.

A [evidência sanitizada](evidence/issue-4-vlm-resource-probe-resultados.json)
separa captura terminal de prefixo técnico. O próximo passo é revisar esses
deltas contra uma hipótese e uma alternativa específica antes de qualquer
proposta de otimização; não repetir a fila ou ampliar timeout por tentativa.
O resultado não abre auditoria, B/C, holdout nem aceite integral do projeto.

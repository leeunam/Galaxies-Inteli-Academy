# VLM: diagnóstico de desempenho após a parada v3

A [execução v3](issue-4-vlm-contraste-nativo-v3-resultados.md) ficou mais lenta
antes de gerar texto, no mesmo PNG e com o mesmo
comando efetivo. **Não foi identificado um defeito de geração ou uma correção de
desempenho sustentada pelos registros disponíveis.** A causa da variação permanece
aberta. Esta unidade compara metadados e acrescenta uma agregação pura; não altera
runtime, threads, sistema, prazos, gates ou filas seladas e não autoriza inferência.

## Trabalho equivalente observado

Foram relidos somente plano/configuração e metadados terminais das capturas
negativas v2/v3. Os hashes de resultado coincidem com os checkpoints dos journals;
os marcadores terminal/EOF/limpeza e os eventos sanitizados são consistentes.
Não se reabriu stdout bruto, mídia, holdout, rótulos, features ou pesos.

| Medida no mesmo Dneg | v2 | v3 | Comparação válida |
| --- | ---: | ---: | --- |
| Encoder concluído | 30,076 s | 51,620 s | +71,63% |
| Decode dos primeiros seis lotes, 768 tokens | 10,584 s | 15,730 s | +48,62% |
| Lote 1 | 1,411 s | 2,618 s | +85,54% |
| Lote 2 | 1,451 s | 2,506 s | +72,71% |
| Lote 3 | 1,625 s | 2,573 s | +58,34% |
| Lote 4 | 1,905 s | 2,773 s | +45,56% |
| Lote 5 | 2,179 s | 2,622 s | +20,33% |
| Lote 6 | 2,013 s | 2,638 s | +31,05% |
| Captura total | 53,121913 s, completa | 74,863786 s, incompleta | não dividir durações de trabalhos diferentes |
| RSS máximo amostrado | 2.791,871 MiB | 2.571,207 MiB | ambos abaixo do teto 3.379,2 MiB |

A v2D concluiu 9/9 lotes e confirmou 1.075 tokens. A v3D concluiu 6/9 e iniciou o
sétimo: 768 tokens concluídos e 896 em lotes iniciados, sem total confirmado.
Somar encoder e seis lotes dá 40,660 s na v2D e 67,350 s na v3D. O restante
7,513786 s da captura v3 inclui trabalho não localizado, inclusive o lote em
curso; não foi atribuído ao journaling, à geração ou a outra causa.

A v2N, outro PNG, teve encoder de 38,417 s e sete lotes concluídos em 13,705 s
antes do timeout de 54,921052 s. Nos primeiros sete lotes a v2D tinha 13,700 s.
Essa observação não isola causalmente a representação: a v3D demonstra variação
relevante mesmo sem trocar o input. O `-9` acompanha timeout e limpeza pelo
proprietário; isoladamente não diagnostica OOM. A contagem de RSS não mede páginas
recuperadas, swap ou tempo de espera.

## Identidade e tamanho do trabalho

A configuração herdada pela v3 é exatamente a v2. Reconstruir o argv final com as
funções puras existentes produz igualdade byte a byte com o template efetivo
registrado na v3, SHA-256
`82b2ee0e7fc890c48f4a415240b13d7abd3f9842bc2d21e71e96074b165156c4`.
A diferença de caminho do PNG/schema é apenas a localização de cada execução.
A identidade declarada do PNG Dneg permanece
`ee884ab32ba1535291932d38b19f867e28cd833f3e5c1fe6c8dd49228d7ce998`.

Permanecem os mesmos pesos/runtime/prompt/schema, CPU quatro threads e quatro de
batch, GPU layers zero, `--no-mmproj-offload`, contexto 3072, `n-predict=64`,
batch/ubatch 128, min=max 1024, temperatura zero e seed 42. A entrada congelada é
RGB 360×640. O cálculo estático fixado resulta em canvas 800×1376, grade 25×43 e
1.075 tokens; esse cálculo não transforma o prefixo v3 em encoder+decode completo.
Os tetos continuam stdout 16 KiB, stderr 256 KiB e RSS 3,3 GiB. O incremento de prazo
entre v2/v3 é real, mas não modificou esses parâmetros nem garantiu conclusão.

## Snapshot atual e lacuna histórica

Às **20:40:58 UTC**, o executor expôs 12 CPUs lógicas, afinidade 0–11, cpuset 0–11 e
`cpu.max=max 100000` nos ancestrais que o expunham. Carga 1/5/15 min:
0,37/0,95/1,48. MemAvailable 2.688.900 KiB (~2,56 GiB), SwapFree 236 KiB de
4.194.300 KiB; PSI de memória avg10/avg60 zero, CPU 0/0,04 e I/O 0/0,01.
CPU 0 reportava governor `powersave`, frequência atual 1,8 GHz e máximo 4,7 GHz.
O processador visível era Intel i5-1345U; o display enumerado era Intel integrado.
Não foi verificado backend de aceleração utilizável nem feita consulta ao runtime.

**O primeiro snapshot pertence ao namespace do executor.** O processo 1 se chama
`codex`; coincidir com o boot dos leases não bastava para chamá-lo de host.
O integrador coletou depois um recibo somente leitura, concluído às
**20:47:09 UTC**, com processo 1=`systemd`, namespaces pid/mnt/user distintos e
cgroup compartilhado. O recibo confirma o contexto host sem alteração de sistema.

No host havia 12 CPUs e afinidade 0–11, nenhuma quota CPU finita nos ancestrais
acessíveis e zero workers pelo detector existente. Duas amostras separadas por
1,000834 s mediram CPU agregada 1,931% (iowait 0,084%); carga 0,71/0,78/1,24.
MemAvailable 2.682.300 KiB (~2,56 GiB) e SwapFree 124 KiB de 4.194.300 KiB.
PSI memória e I/O avg10/avg60 eram zero; CPU some 0,40/0,20. Esse pequeno intervalo
confirma baixa ocupação **naquele momento**, não durante o timeout anterior.
O espaço disponível era da mesma ordem dos picos RSS do VLM, com swap quase cheio.
Não se publicou caminho de cgroup, PID de usuário, linha de comando ou ambiente.

Swap quase cheio e memória disponível limitada merecem medição contemporânea,
mas não provam que causaram a demora histórica. Da mesma forma, PSI/carga baixos
agora não excluem pressão durante as chamadas. O governor/frequência de um instante
não informa a frequência sustentada no encoder. Os recibos revistos não retiveram
CPU-time, major faults, deltas de throttling ou PSI durante as inferências.

A próxima observação útil, caso uma execução diferente venha a ser autorizada,
seria acoplada ao dono existente: PID+start_ticks, tempo de CPU user/system,
majflt, RSS/VmSwap, contadores cgroup de throttling e PSI cumulativo, com
monotonic/boot/identidade de escopo antes e durante a chamada. Deltas negativos,
PID reutilizado ou escopo diferente invalidariam a comparação. Tempo dos fsyncs
precisaria ser medido separadamente para avaliar sua contribuição. Isso é uma
proposta de instrumentação, não um novo coletor integrado ou autorização de teste.

## Caminho crítico até 22h40 UTC

A janela pedida às 20h40 era de aproximadamente 120 minutos. O caminho integral
continua dependente de: diagnóstico de desempenho → candidato perceptivo que
satisfaça desenvolvimento → nova auditoria cega → extração uniforme aprovada →
B completo → C completo → congelamento/avaliação final → integração/demo e aceite.
A integração NIM pode avançar em paralelo; o trecho final depende de ambas as
frentes. Nenhum tempo de CPU, por si, substitui anotação independente ou aceite.

A única captura completa deste contraste durou 53,121913 s, e a v3 já demonstra
que essa taxa não é estável. **Não há throughput medido para o trabalho integral**,
e o candidato aprovado e o reuso permitido ainda determinariam o número de chamadas.
Somente como escala aritmética: se os 269 registros de desenvolvimento documentados
exigissem uma chamada cada ao custo histórico 53,121913 s, seriam 3,97 h de processo;
três chamadas cada (807) dariam 11,91 h. Essas hipóteses não selecionam candidato,
coorte, orçamento ou nova rodada; não são previsão nem limite inferior demonstrado.

A conta exclui aquisição e identidade de mídia, anotação independente, revisão,
gates, outras modalidades, extração completa, B→C, avaliação final, integração e
ensaio. Mesmo um contraste perfeito no par revelado não abre a auditoria nem
aprova atributos. Não se deduz um prazo de aceite somando apenas segundos de CPU.

Os [12 ajustes anteriores de B-cache](issue-4-experimento-b-resultados.md)
**somaram 90,83 s**, uma medição concreta do
recorte com features já existentes. Não mede treino B completo, C ou extração VLM;
não justifica atribuir um prazo a essas etapas. A auditoria prevista anteriormente
exigia 32 canais novos, anotações cegas e gate 90%/zero evidência sem suporte; nenhuma
nova amostra foi aberta aqui. Os 31 casos de teste seguem fechados.

Portanto, **não há estimativa sustentada de concluir o escopo integral até 22h40**.
O prazo defensável desta unidade é entregar diagnóstico verificável e a agregação
testada, sem prometer correção perceptiva, B/C ou aceite. Alternativas de
escopo para decisão explícita são: consolidar a entrega dos componentes já
verificados com as pendências declaradas; ou manter o escopo completo e reservar
outra janela para resolver percepção/recursos e validar antes da extração. Usar
outro hardware/backend/modelo exige capacidade, compatibilidade, orçamento e
validação novos; nenhuma opção foi implementada ou precificada.

## Unidade aditiva e verificação

`vlm_performance_comparison.compare` é uma função pura, sem CLI, spawn, coleta de
host, configuração do sistema, acesso a modelos ou nova fila. Recebe projeções de
capturas terminais previamente verificadas, exige mesmo hash de input/comando e
reutiliza o diagnóstico por fase. Compara somente lotes concluídos equivalentes;
recusa mudança de tokens/ordem/identidade e não calcula razão de duração total
contra captura parcial. Não autentica os recibos originais por si.

Passaram **15 testes em 0,05 s**, com eventos e hashes inventados, cobrindo
identidade, prefixos, lotes pendentes, reordenação, limpeza incerta, timeout após
decode completo, timers zero e ausência de mutação. Ruff e formatação passaram.

```sh
rtk proxy "$PYTHON" -B -m pytest -q -p no:cacheprovider tests/test_vlm_performance_comparison.py
rtk proxy "$RUFF" check --no-cache scripts/vlm_performance_comparison.py tests/test_vlm_performance_comparison.py
rtk git diff --check
```

A [evidência sanitizada](evidence/issue-4-vlm-performance-offline-v1.json) contém os
pins dos recibos, agregação e snapshot explicitamente separado. Nenhum processo
nativo, benchmark, inferência, novo plano/release/reserva ou mudança de sistema
foi realizado. v1/v2/v3 continuam seladas; não há recomendação de reexecutá-las ou
aumentar o prazo. Fontes antigas, retenções, M1/A200 e gates permanecem intactos.

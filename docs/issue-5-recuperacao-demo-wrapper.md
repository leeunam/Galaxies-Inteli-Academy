# Recuperação da demo — candidato executável para revisão

O invólucro aditivo está implementado no clone e passou em **17 checks sem ML
em 0,91 s**, com Ruff/formatação aprovados. Nenhuma mídia real foi adquirida,
decodificada ou processada. O [recibo público](evidence/issue-5-recuperacao-demo-wrapper-20261020.json)
registra hashes e resultados. A aquisição/análise continua bloqueada até a
liberação técnica vinculada a este código e ao protocolo privado v3.

A [proposta de recuperação](issue-5-recuperacao-midias-demo-proposta.md) e o
[inventário](issue-5-inventario-midias-demo.md) continuam preservados. As três
fontes de beleza já autorizadas são exatamente as mesmas do plano v2; não há
nova seleção, API de métricas, fonte reserva ou pedido de arquivos novos.

Protocolo privado v3 ativo, representado por `${FINAL_PLAN}`: SHA256
`4bc0bffbeafdb6959c2db4556a2b3573cd7a83791db057ac5c2c5089c39fb773`.
Ele preserva o trio e as referências do plano-base privado v2
`${BASE_PLAN}`, SHA256
`f61bcf849d2f61b701c00ef447486494d302a86029c5f14e8f11547ed1377f80`.
Os valores de caminhos, URLs e identidades ficam somente no diretório novo
ignorado do clone. O template de liberação tem **zero fases habilitadas** e
referências de revisão/checks vazias; não permite executar aquisição.

## Arquivos e fronteiras

| Componente | Responsabilidade |
| --- | --- |
| [Política](../scripts/demo_recovery_policy.py) | Conferir trio fixo, base/protocolo/hashes do código, limites, liberação e reservas exclusivas duráveis |
| [CLI](../scripts/demo_recovery.py) | Inspecionar, adquirir, analisar, preparar passagem e descartar entradas próprias |
| [Supervisor](../scripts/demo_recovery_process.py) | Limitar stdout/stderr, tempo, disco/RSS e recolher somente os processos próprios, inclusive filhos em outra sessão |
| [Launcher limitado](../scripts/demo_recovery_child.py) | Aplicar `RLIMIT_FSIZE` antes de exec, sem `preexec_fn` no processo pai |
| [Etapa nativa](../scripts/demo_recovery_native.py) | Cadastrar entradas e chamar o serviço original por Python e MCP, com imports tardios |
| [Checks](../tests/test_demo_recovery.py) | Exercitar contratos e falhas com arquivos/filhos inventados, sem mídia real/modelos/rede |

O produto, locks, extratores, fontes seladas e recibos existentes não foram
alterados. Os novos módulos não são importados nem oferecidos pelas tools MCP
de produção. O invólucro é uma operação local explícita do operador.

A política exige liberação com hash do protocolo, os cinco hashes de código,
fases permitidas, perfil de formato, prazo de retenção e referências não vazias
de revisão e checks. O código recusa a liberação ausente/incompleta antes de
criar a pasta da execução. Cada fase/tentativa é consumida antes de operar;
crash/resultado incerto não liberam repetição. Uma execução já iniciada não
recebe aquisição ou análise repetida em outra chamada.

## Ajustes concretos para a revisão final

**Formato.** 32 MiB e altura 720 são tetos operacionais deste ensaio, não novos
requisitos da API. A API continua admitindo seus formatos/limites originais.
As propriedades históricas selecionadas cabem no teto de altura; os recibos
anteriores não conservam uma extensão de contêiner confiável do arquivo apagado.
O downloader antigo aceitava MP4/WebM/MKV e podia fazer merge por cópia.

O perfil v3 proposto admite esse percurso já conhecido e, quando a saída for
MKV, um **remux MP4 com `-c copy`**. Não redimensiona, não reencoda e não troca
fonte. Merge/remux ficam dentro da mesma tentativa, deadline e tetos de arquivo
e workspace; falha de compatibilidade encerra a tentativa, sem outro formato
selecionado por repetição. Essa opção está implementada, mas ainda não foi
executada nem liberada. A revisão precisa vincular o perfil ao protocolo.

**Percurso A200.** A cadeia congelada é literalmente
`candidate_features._extract_one → extract_features(..., False, ...)`.
Ela executa ASR/MiniLM e **também CLIP**, preservando o extrator compartilhado;
`include_vlm=False` impede a chamada VLM. Depois são usados M1/A200, SHAP q50 e
índice exclusivamente de treino na sessão/grafo nativos. O código congelado
configura **quatro threads** em Torch e Whisper; o protocolo v3 registra quatro,
sem editar o extrator ou fingir o limite anterior de um thread. Não há treino,
worker de fixture, transcrição injetada, fallback ou mudança do gate de idioma.

**Entradas e descarte.** `inputs/` contém as três entradas recuperadas; `scratch/`
contém downloads provisórios, áudio, frames e cópias de extração. Só scratch é
removido ao fim dos processos confirmadamente recolhidos. A fase `handoff`
conserva os inputs, o pedido e o recibo privado necessários à passagem ao usuário.
Preparar essa passagem não significa que a apresentação já terminou.

A janela temporária proposta para as **entradas de entrega** termina em
**21/10/2026 às 23h59, São Paulo**. Descarte antecipado exige passagem registrada
e comando explícito de demo concluída; após o prazo, o comando de descarte
pode remover as entradas. Isso propõe retenção própria e limitada para a
entrega atual: não altera retroativamente a instrução de apagar as mídias dos
pilotos, não a ignora e não presume armazenamento indefinido autorizado.
A liberação final precisa vincular esse prazo antes da aquisição.

Não foi criado timer/automação de expurgo. A coordenação/operador fica
responsável pelo comando de limpeza após o ensaio ou ao vencer o prazo.
Morte do supervisor/máquina pode exigir recuperação pelos leases e identidades
PID/start-time; não há promessa de exclusão instantânea nessa situação.
O descarte de entradas próprias não depende de que a árvore principal permaneça
com os mesmos documentos depois de concluída a demo.

## Limites efetivos

O trio tem até três aquisições serializadas, uma por fonte, sem retries ou
substituições. Mantêm-se 180 s por tentativa, 600 s de aquisição, 480 s por
percurso Python/MCP e 1.800 s totais; o recolhimento necessário pode terminar
depois do deadline. O plano exige 1 GiB livre, limita cada arquivo a 32 MiB e o
workspace a 384 MiB, e interrompe ao observar soma de RSS maior que 3,5 GiB.
Há uma conferência de slot antes de iniciar aquisição/análise, recusando outro
worker de modelos/VLM.

`RLIMIT_FSIZE` limita o arquivo no filho. RSS e uso agregado de workspace são
monitorados a cada 50 ms, podendo ultrapassar transitoriamente o limiar entre
amostras; não são cgroups ou cotas rígidas instantâneas. stdout/stderr do filho
são limitados antes de retê-los. O supervisor dedicado adota órfãos e usa
pidfds/identidade para interromper e recolher seus filhos sem matar processos
externos. Falta de confirmação preserva o scratch para recuperação.

A fase de aquisição usa somente as URLs fixas, sem cookies, chaves, proxy,
configuração pessoal, plugins ou componentes remotos novos. A análise roda
com rede isolada/desabilitada; cache, pesos, coorte e evidências originais são
somente leitura, com outputs novos no clone. Não há chamada NIM ou API de
métricas, renovação de rótulos ou reaproveitamento de orçamento científico.

## Comandos de operação

Executar no clone, com caminhos privados indicados pelos parâmetros. A inspeção
já foi executada com sucesso e não inicia processos de mídia/modelos:

```sh
rtk proxy .venv/bin/python -B -m scripts.demo_recovery inspect --plan "$FINAL_PLAN" --base-plan "$BASE_PLAN"
```

Somente depois da revisão técnica e criação de `${TECHNICAL_RELEASE}` válida:

```sh
rtk proxy .venv/bin/python -B -m scripts.demo_recovery acquire --plan "$FINAL_PLAN" --base-plan "$BASE_PLAN" --release "$TECHNICAL_RELEASE" --run-dir "$NEW_RUN"
rtk proxy .venv/bin/python -B -m scripts.demo_recovery analyze --plan "$FINAL_PLAN" --base-plan "$BASE_PLAN" --release "$TECHNICAL_RELEASE" --run-dir "$NEW_RUN"
rtk proxy .venv/bin/python -B -m scripts.demo_recovery handoff --plan "$FINAL_PLAN" --base-plan "$BASE_PLAN" --release "$TECHNICAL_RELEASE" --run-dir "$NEW_RUN"
```

A mesma aquisição alimentará Python e MCP. A fase nativa valida duração medida,
contrato e bytes, registra os IDs e compara respostas integrais; dados históricos
de ASR não são tratados como passagem atual. Uma falha preserva a
indisponibilidade, sem trocar fonte ou afrouxar regras. Os inputs e o request
privados ficam disponíveis para o operador usar o serviço/CLI já documentados
na apresentação, dentro da janela de retenção, sem nova aquisição automática.

Depois da passagem e conclusão real do ensaio, ou após o prazo de retenção:

```sh
rtk proxy .venv/bin/python -B -m scripts.demo_recovery discard --plan "$FINAL_PLAN" --base-plan "$BASE_PLAN" --release "$TECHNICAL_RELEASE" --run-dir "$NEW_RUN" --demo-completed
```

O flag de conclusão se refere à apresentação/uso terminado, não à simples
criação do recibo de passagem. Antes do prazo, a CLI recusa o descarte sem
passagem registrada. Depois do prazo, o mesmo comando pode ser usado sem o flag.
Recibos permanecem privados; mídia e scratch próprios são removidos somente
após conferência de recolhimento.

## Verificações desta unidade

Passaram 17 checks em 0,91 s: trio/limites imutáveis, vínculo de liberação a
formato/retenção/código, consumo e symlinks, projeção de origem, remux por cópia,
limite real de arquivo/saída, timeout, cancelamento, recolhimento de neto em
outra sessão, preservação de processo de controle, slot de modelo, cápsula real
Bubblewrap offline com filho sem conteúdo e chamada congelada sem VLM.

Ruff e formatação passaram nos seis arquivos Python novos/de teste. A inspeção
real do protocolo teve exitcode 0. Duas chamadas reais à CLI de aquisição,
sem liberação e com template vazio, tiveram exitcode 1 pelos códigos esperados
`technical_release_required` e `release_mismatch`, sem criar diretório de run.
Node e FFmpeg locais foram localizados por metadados, sem executá-los.

A primeira rodada teve 14 passes e uma falha no próprio teste estático, que
contava também a guarda da preparação de modelos; foi ajustado para examinar
a função de extração correta. A segunda teve 15 passes. Dois checks necessários
de slot/cápsula completaram a versão final de 17. As rodadas e JUnit antigos
foram preservados, sem repetição das suítes do projeto ou inferência de ML.

O pacote termina sem processos próprios ativos e sem bloqueio técnico observado
nos checks locais. Permanecem por verificar após liberação: disponibilidade
atual das fontes, formatos realmente oferecidos e passagem dos gates reais.
O seletor externo segue ausente, com aderência não avaliada; este candidato não
conclui cientificamente o projeto nem as issues. Não houve escrita principal,
publicação ou aquisição real nesta unidade.

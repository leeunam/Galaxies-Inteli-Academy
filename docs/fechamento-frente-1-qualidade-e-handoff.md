# iSee — Frente 1: qualidade, comparação e handoff

23/10/2026. Destinatária: Galaxies. Autor do projeto: Leunam Sousa.
**Frente ainda não concluída:** nenhum atributo VLM foi liberado nesta rodada;
extração uniforme e B/C completos observados continuam bloqueados. Esta entrega
implementa e verifica trabalho independente, preservando os critérios científicos.

**Adendo de revisão:** o operador v1 abaixo foi reprovado antes de qualquer
execução real por falta de sentinela durável anterior ao filho do preflight.
A [versão v2](fechamento-frente-1-operador-v2.md) corrige isso em outro namespace;
conservam-se os hashes e o histórico v1, sem autorização de uso.
Posteriormente, a tentativa v2 autorizada [parou no preflight](fechamento-frente-1-diagnostico-v2-resultados.md)
por recusa de namespace, com zero modelo e sem repetir. Os checkpoints de
preparação abaixo permanecem históricos; o resultado atual é esse bloqueio técnico.

## Reconciliação da percepção e da execução

O [último contraste](issue-4-three-case-prompt-result-v1.md) terminou tecnicamente
em 3/3 chamadas: encoder/decode completos, 240 tokens visuais, zero timeout e
limpeza confirmada. Acertou os dois negativos e errou o positivo com
`incidental_only`/`incidental` → false. Os 64 tokens são o limite de saída;
240 é a contagem visual observada. Native225 designa a configuração de tokens,
sem substituir as dimensões RGB 320 × 330 dos crops.

A conferência nova vinculou os três stdout e resultados capturados aos recibos,
inputs e [agregado público](evidence/issue-4-three-case-prompt-result-v1.json).
Conferiram 101 arquivos históricos, além de quatro bundles A200/A300/B-cache/
C-cache, seus modelos, relatórios, fontes, lock e versões. Não foi repetida
recarga nativa ou inferência desses comparadores; suas provas históricas de
recarga/SHAP são reutilizadas dentro dos contratos inalterados.

| Evidência | Conclusão sustentada | Limite |
| --- | --- | --- |
| Auditoria B-VLM inicial | Cinco colunas reprovadas | 32 casos já revelados; não são vídeos faltantes da base |
| Auditoria perceptiva v7 | Pessoa com evidência sem suporte; produto abaixo de concordância; texto com pouca cobertura/classes | Nenhuma coluna liberada; amostra revelada não valida correções |
| Desenvolvimento v8 | Texto melhora; produto responde true nos 64 | Ganho de cobertura não elimina suporte inválido ou falsos positivos |
| V16 negativos e pares positivos | Ordem muda a resposta; state_first perde sensibilidade nos positivos | Não sustenta escolher essa ordem como correção aprovada |
| Native225 e lote posterior | Execução tornou-se viável nos controles observados; lote parou por abstenção | Sucesso técnico não aprova percepção |
| Último contraste local | Negativos 2/2; positivo falso negativo | A cláusula nova não teve seu efeito causal isolado |
| Último ensaio visual remoto preservado | HTTP 500 na primeira chamada, sem resposta perceptiva | Falha operacional, sem evidência para comparar qualidade local/remota |

O HTTP 500 acima é especificamente o ensaio de 23/10 em
`data/private/issue-4-nim-independent-product-20261023-v1/result-0001.json`,
encerrado por `terminal.json` no mesmo diretório. Seus hashes constam de
`unit-3-audit/quality-status.json`. Não se refere às rodadas NIM públicas de
21/22 com HTTP 503. Nenhum novo envio foi feito para conferir essa distinção.

As fontes de representação inspecionadas não demonstraram a discrepância que
justificaria corrigir RGB/normalização/merger. Não se atribuiu o erro atual a
parser, timeout, falta de RAM, quantização ou capacidade geral por exclusão.
Não houve correção de resposta, de anotação ou de limiar para obter aprovação.

## Qualidade e contrato de features

Estado versionado: `front1-readonly-quality-status-v1`, mantido no diretório
privado indicado abaixo; `released_fields=[]`, `quality_release_emitted=false`.
Esse recibo de reprovação **não é QualityRelease** e não deve preencher um
aceite visual do preflight final.

| Campo | Estado atual |
| --- | --- |
| Pessoa, produto até 3 s, texto | Candidatos da rubrica atual, ainda sem novo gate independente aceito |
| Ambiente, formato | Reprovados no gate inicial e retidos na revisão atual |
| Close-up, aplicação/demonstração | Globalmente desconhecidos e excluídos; não validados indiretamente |

Conservar o gate por campo e setor: ≥12/16 conhecidos, ≥90% de concordância de
valor **e** frames, zero evidências sem suporte; booleanos com ≥3 de cada
previsão true/false no total e ≥1 por setor. A auditoria futura exige 32 casos
do treino, 16/setor, 32 canais distintos e exclusão de todo histórico revelado;
anotação separada e selada antes das respostas e revisão independente. Unknown
não conta como acerto. A revisão assistida não é certificação humana.

O contrato B/C implementado conserva as 905 colunas cacheadas e acrescenta
somente `vlm_<campo_liberado>`, na ordem da liberação. Mesmas linhas, cache,
atributos e partições; vocabulário C aprendido só no treino, sem PCA/imputação
nova. Identidades incluem coorte, partições, splits ordenados com rótulos,
configuração, pesos/prompt/schema, release, 32 sidecars de auditoria e os
269 pares features/run de desenvolvimento. A candidata batch atual ainda
precisa da ponte compatível e da liberação; seu sidecar diagnóstico não é
aceito apenas por JSON válido. **O contrato observado final permanece pendente.**
O TAPI original, seções 3/4.1, pede 5–8 atributos VLM; a proposta local definiu
sete campos com barreiras. A rubrica atual de três candidatos não encerra essa
obrigação: mesmo que passe futuramente, os demais campos obrigatórios e o
aceite do contrato completo continuam abertos. Não se reduziu o requisito
original para caber nas colunas parcialmente liberáveis da infraestrutura.

## Implementação e comparação

Os commits `bdc76fd` e `023f632` introduzem a [ponte C, SHAP e seleção](fechamento-frente-1-c-completo.md)
sem editar fontes pinadas históricas. A revisão independente de `023f632`
aprovou os controles de proveniência no fluxo prescrito. O helper de comparação
recebe A200/A300/B-cache do caller; o caminho observado prescrito é a CLI,
que os carrega nativamente. Não se alega proteção contra um adversário Python
local que reescreva código, objetos e hashes.

| Validação histórica, mesma união de 66 | A300 | B-cache | C-cache |
| --- | ---: | ---: | ---: |
| MAE log médio por canal | 1,7761 | 1,6584 | 1,5444 |
| Cobertura micro | 0,7121 | 0,7576 | 0,7576 |
| Acerto de pares médio por canal | 0,4533 | 0,6417 | 0,6683 |
| Spearman médio por canal | −0,0192 | 0,2070 | 0,3292 |

Os [resultados cacheados](issue-4-experimento-c-cache-resultados.md), incluindo
quantis, setores/canais, largura e cauda, permanecem evidência reutilizável de
experimentos sem VLM. Não substituem B/C completos. A comparação completa e a
decisão observada pela validação continuam **não disponíveis**. A implementação
da regra exige MAE menor que A300 e média das três perdas quantílicas sem piora;
empate favorece CatBoost. A200 continua servido; não houve escolha pelo teste.

## Diagnóstico novo preparado, ainda não autorizado

Uma única célula faltante: mesmo positivo revelado e configuração native225,
com o prompt V16 anterior sem a cláusula sobre caracteres. Resultado true só
conta com categoria/configuração nas alternativas congeladas do mesmo frame.
False mostra que a cláusula não era necessária ao falso negativo; unknown,
true sem suporte ou falha técnica encerram sem aprovar candidata ou auditoria.
Nem o prompt antigo nem o novo ficam aprovados por esse diagnóstico.

O literal dos dois prompts, a cláusula removida e os argv estão no manifesto
comparativo. Normalizando apenas o caminho do schema temporário, a reconstrução
difere somente no argumento do prompt. **O argv efetivamente observado da chamada
antiga não foi persistido**: o vínculo é uma reconstrução estática do plano e
operador congelados, não prova de igualdade observada dos comandos. Isso limita
qualquer interpretação causal, além da variação temporal/runtime.
Os caminhos exatos de receipt/capture/stdout e respectivos hashes foram
acrescentados sem modificar o manifesto em
`unit-3-audit/static-argv-source-paths.json`. A Frente 1 revalidou esses bytes;
a revisão independente até este checkpoint conferiu o manifesto, seus digests
e literais, sem alegar nova revalidação independente de todos esses arquivos.

Foram recalculados sem inferência os SHA-256 dos pesos Q4_K_M, projetor Q8_0,
`libmtmd` e CLI b11716. Referências, fingerprints, imagem e fontes conferiram.
Preparação final: 1,2613 s, RSS 27.232 KiB, afinidade ao núcleo 0. Duas falhas
anteriores de preparação de metadados foram preservadas: import path ausente e
consulta do fingerprint pela alias em vez do alvo HF. Nenhuma iniciou modelo,
consumiu chamada ou criou namespace de execução.

O operador versionado `front1_positive_diagnostic.py` foi materializado como
`control_worker.py` privado. Exige autorização humana nova e literal, revisão
independente vinculada aos bytes do operador/autoridade e slot do coordenador.
Não escreve esses três recibos. Verifica fontes, inputs, assets e autoridade
antes de dispatch, usa captura durável e o proprietário de processo já existente,
sem rede/segredos herdados. Uma reserva; qualquer término sela a rodada, inclusive
resultado incerto. A chamada direta interna exige proprietário vivo com argv fixo.

Limites do pedido único: **1 chamada**, CPU4, RSS cooperativo 3,3 GiB,
MemAvailable ≥6 GiB, 75 s úteis +5 s de encerramento, **120 s desde o preflight**,
disco livre ≥1 GiB, entrada existente sem aquisição, stdout 16 KiB/stderr 256 KiB,
R$0, sem rede externa ou retry. A renovação do crop é exclusiva para essa chamada.
O limite RSS é cooperativo; não constitui reserva física/cgroup de RAM. Scratch
novo contém apenas schema/intermediários próprios e é removido após quiescência;
raw e recibos são preservados. Não altera retenção ou descarte de fontes antigas.

No namespace real, nenhuma autorização, selo, slot, reserva, `started` ou
preflight foi criado. Arquivos de autoridade inventados existem somente nas
fixtures isoladas de teste e não concedem permissão operacional.
RAM aferida após a saída do Brave: aproximadamente 8 GiB disponíveis; não houve
encerramento de aplicativo pelo agente, mudança de swap ou limpeza de cache global.
Disponibilidade deve ser conferida novamente no preflight e não concede autorização.

## Handoff aos Chats 2 e 3

- Clone independente: `/tmp/galaxies-fechamento-20261023-frente-1`, branch
  `codex/fechamento-20261023-frente-1`, base de código `3586bcab7aa3f7bf165f1ac17ced91bb85358043`.
  A principal recebeu somente documentação do coordenador em `9275737`; não houve
  restauração, integração ou publicação desta frente.
- Resultados próprios persistentes: `data/private/fechamento-20261023/frente-1/`.
  `unit-1-c-full/` preserva os 35 testes iniciais/28,44 s. `unit-2-selection/`
  preserva a seleção final de 34 testes/113,24 s internos, 113,7688 s externos,
  pico 322.840 KiB, afinidade [0]. Rodadas sobrepostas não são somadas.
- `unit-3-audit/quality-status.json`: hash lógico
  `51727cdcd0c95415d9799e3cbf70ebedd751e59b24fe0fcd43117b72fa0615f1`.
  `diagnostic-request.json`: proposta lógica
  `5cc4b78091fd84f59ec20cbf753aa22fcd18c22d0144c08a785c0d9f7f4471e5`.
  `static-argv-contrast.json`: comparação lógica
  `88c9437a257ac6b9e8d54274a4f0a7a13ab9db73771c5610f4b33a0f9c152ef0`.
- `diagnostic-old-prompt-positive-v1/plan.json`: hash lógico
  `4ae5930cb9d6e8c5a1d7a69bffd56aa82f591d9d96507283fdf8d84400e77925`,
  SHA-256 dos bytes `6f7354206ce3020870f1be17bce60ef1f7ce2505cdad73d09f510b5b9974560c`.
  `control_worker.py`: SHA-256
  `4e5fd7e5a5cff86284de23f34f462c7c2e7e5c7c702f2f8c6b5845c01514bf06`.
  Os hashes locais garantem integridade, não autoria humana ou assinatura externa.
- Operador: **17 testes offline/0,24 s**, em
  `unit-3-audit/pytest-operator-complete.log`, com callbacks/arquivos inventados,
  sem cápsula/modelo real. Ruff/formatação e diffcheck passaram. Testes cobrem
  falta/escopo/expiração de autoridade, recusa de repetição, memória, relógio
  global, namespace próprio, JSON/schema ordenado e quatro resultados perceptivos.
- Frente 2 recebe `full-model-q50-evidence-v1`: contribuições assinadas por
  modalidade e campo VLM, escala log1p, base e reconstrução, release/artifact hashes.
  Para dados observados, `explain_full(..., data=dados_verificados)` reabre o
  bundle nativo; não confiar apenas em modelos em memória ou seleção de IDs.

Verificação local, a partir do clone, usando o ambiente existente por referência:

```sh
rtk proxy env PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 \
  /home/inteli/Documents/projetos/Galaxies-Inteli-Academy/.venv/bin/python -B \
  -m pytest -q -p no:cacheprovider tests/test_experiment_c_full.py \
  tests/test_compare_full_models.py tests/test_full_model_provenance.py \
  tests/test_run_full_models.py tests/test_front1_positive_diagnostic.py
```

O comando de preflight futuro é o interpretador absoluto acima, `-B`, seguido
do caminho absoluto do `control_worker.py` e `--preflight-only`; execução usa
o mesmo argv sem a última flag. Ambos recusam sem os três recibos externos novos.
Esses comandos não foram executados contra o namespace real.

Próximos aceites, nesta ordem: revisão do operador e decisão humana sobre o
diagnóstico → hipótese/candidata sustentada → triagem aprovada → auditoria
independente → QualityRelease e ponte rastreável → extração uniforme 269 →
B/C completos/recarga/SHAP/comparação → decisão pela validação → handoff final
da configuração à Frente 2 e avaliação coordenada. Nenhuma seta é aprovação
automática, e o holdout permanece fechado.

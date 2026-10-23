# Fechamento do escopo do iSee

Nome confirmado pelo autor: **🧊 iSee**. Desenvolvido por **Leunam Sousa** para a **Galaxies**, no contexto da Inteli Academy. A mudança de nome não renomeia contratos, caches ou recibos históricos.

Base da rodada: `3586bcab7aa3f7bf165f1ac17ced91bb85358043`. O escopo original continua em vigor, com os recortes posteriores registrados no briefing. Este documento organiza o trabalho; não concede autorização científica ou comprova aceites ainda ausentes.

## Responsabilidades e dependências

| Frente | Responsabilidade | Dependência para concluir |
| --- | --- | --- |
| 1 | Qualidade visual, liberação de atributos, B/C completos e seleção na validação | Gates perceptivos, representação e dados elegíveis |
| 2 | Explicação, aderência ao briefing e integração da configuração selecionada | Contrato e configuração aprovados da Frente 1 |
| 3 | Coordenação, integração única, avaliação final e pacote público | Aceites das Frentes 1/2 antes da abertura do teste |

Código e documentação podem ser preparados em paralelo, em árvores independentes. Processos pesados compartilham uma fila de CPU/RAM. Somente o coordenador integra a árvore principal. Histórico selado e orçamentos consumidos permanecem intactos.

## Matriz de aceite

| Critério | Evidência reutilizável | Lacuna / condição para concluir | Responsável |
| --- | --- | --- | --- |
| Base e alvo | Coorte 300, partições 203/66/31, views observadas com 30 <= idade < 37 dias | Origem, condições de uso e limites preservados; não atualizar rótulos ou alterar a coorte por resultado | 1/3 |
| Canal e tempo | Partições por canal e métricas de desenvolvimento | Diagnóstico temporal anterior→posterior com suporte e limites explícitos; não substituir por tabela de datas | 3 |
| Visual | CLIP e medidas técnicas; diagnósticos VLM preservados | Liberação perceptiva de todos os atributos obrigatórios pelos gates previstos | 1 |
| Comparação de modelos | A300/B-cache/C-cache reais na validação | B completo e C completo com mesma representação elegível; recarga, métricas e seleção pela regra acordada | 1 |
| Quantis e suporte | q10/q50/q90, reparo que conserva q50, testes e relatórios | Avaliação da configuração final, cobertura/largura e avisos de evidência fraca | 1/2/3 |
| Explicação | SHAP nativo, comparáveis de treino, 12 claims sintéticos revisados, texto local cacheado | Fundamentação suficiente e aderência ao briefing com conteúdo real correspondente, sob rubrica prévia | 2 |
| Função, grafo e MCP | Par real histórico v6 e testes 1/3/5 inventados | Cobrir somente lacunas do fluxo final; preservar números, ranking, falhas e proveniência | 2 |
| Teste reservado | Procedimento P6 e preflight de metadados | Congelamento, revisão e autorização próprios; execução científica final ainda ausente | 3 |
| Reprodução e README | Locks, prova pública histórica e documentação do estado atual | Comandos e pacote final coerentes com artefatos efetivos, sem dados privados; README atualizado após os aceites | 3 |
| Aprendizagem e entrega | Glossário e documentação das escolhas | Autor explica um exemplo completo, limitações e decisões; aceite humano e publicação são separados | 3 |

## Evidência e conclusão

Cada handoff precisa identificar base, commit, entradas, contrato, artefatos, hashes, fases executadas, recursos, resultados e critérios não atendidos. Uma mensagem de conclusão sem os respectivos artefatos não altera o estado de aceite.

O par real v6 continua aproveitável para contratos que já cobriu; não exige repetição apenas para preencher checklist. A execução recente de três casos cacheados cobre features→M1→SHAP→comparáveis→texto, não nova extração, MCP, StateGraph ou NIM. A revisão dos 12 claims refere-se a dados inventados e tem cobertura parcial.

O último contraste visual terminou sem timeout, acertou dois negativos e errou o positivo. Portanto, execução técnica e qualidade perceptiva continuam sendo gates distintos. A preparação de um novo experimento não é autorização para executá-lo.

O TAPI prevê de cinco a oito atributos VLM; o contrato da proposta local contém sete campos. A rubrica atual de pessoa/produto/texto não encerra essa obrigação, mesmo que esses três sejam aprovados. Campos desconhecidos ou retidos não contam como atributos validados; o aceite do contrato visual completo permanece aberto.

A tentativa v2 autorizada em 23/10 parou no preflight: a cápsula recebeu recusa ao criar o namespace, com limpeza confirmada e zero chamadas/reservas de modelo. O [relatório](https://github.com/leeunam/case-GALAXIES-IA/blob/0df616e5fd64dfc4947abde583f2664b66abf410/docs/fechamento-frente-1-diagnostico-v2-resultados.md) e o [contexto observado](https://github.com/leeunam/case-GALAXIES-IA/blob/0df616e5fd64dfc4947abde583f2664b66abf410/docs/fechamento-frente-1-contexto-execucao.md) não demonstram a regra causal específica da recusa. A rodada está encerrada, sem saldo reutilizável. Integrar sua infraestrutura e documentação não libera atributos, não altera o modelo servido e não conclui a avaliação final.

A [rodada v3 posterior](https://github.com/leeunam/case-GALAXIES-IA/blob/0df616e5fd64dfc4947abde583f2664b66abf410/docs/fechamento-frente-1-ensaio-v3-resultados.md), autorizada
separadamente, passou no preflight com a cápsula interna preservada e completou
uma inferência nativa em 17,48 s, sem timeout. O positivo conhecido recebeu
`unknown`, portanto a hipótese perceptiva permanece inconclusiva. A reconciliação
aditiva distingue a captura nativa completa do rc2 do worker por não aceitação,
sem reescrever o terminal bruto. O coordenador conferiu a captura, contagens e
limpeza e liberou o slot. Não houve repetição, liberação de atributos, sidecars
ou modelos novos. Os commits de preparação, revisão e resultado foram integrados
localmente como `20fea32`, `31fd2c0` e `53ae442`, respectivamente; não houve publicação.

O README documenta o estado disponível e será atualizado com os aceites efetivos. VLM, B/C completos, aderência, integração final e avaliação científica não estão concluídos nesta unidade. Frontend elaborado, persona sintética, FastAPI, Ridge e retreino dinâmico não são acrescentados ao caminho obrigatório.

## Integração posterior e veredito de fechamento

A [matriz detalhada](fechamento-requisitos-e-evidencias.md) distingue obrigações,
recomendações e extensões, com evidência, limite, responsável, dependência e
condição de aceite para cada requisito. O [guia curto](guia-explicacao-isee.md)
orienta a explicação do fluxo e dos diferentes tipos de demonstração.

A [v4-r2](https://github.com/leeunam/case-GALAXIES-IA/blob/0df616e5fd64dfc4947abde583f2664b66abf410/docs/fechamento-frente-1-representacao-v4-resultados.md) completou o
preflight e uma chamada nativa, em 60,305 s, com 1.056 tokens e `unknown` no
positivo. STOP no primeiro caso, 16 não executados, limpeza e encerramento
conferidos; a fila foi liberada. Os três commits foram integrados localmente:
`a63dcaf`→`09b5a0a`, `5bf8ef2`→`54e715a`, `516faa0`→`0789a44`.
Nada foi promovido ou liberado como qualidade perceptiva.

O [motor de métricas](issue-6-motor-metricas-v1.md) e o
[planejador temporal](issue-6-diagnostico-temporal-v1.md) estão implementados,
revisados e integrados. A conferência consolidada passou em 31 testes
inventados/preflight, 0,19 s, sem pesos, ajuste, dados científicos ou rede.
Isso não é o diagnóstico temporal executado nem avaliação dos 31 reservados.
Continuam ausentes a configuração final, seus aceites e os carregadores
científicos restritos com autorização específica. O inventário público P6
conserva os bloqueios, sem hashes ou aprovações inventados.

**Veredito atual: parcialmente concluído.** A execução técnica e a preparação
avançaram; a qualidade visual reprovou o gate e impede os passos dependentes.
O escopo original permanece íntegro. Nenhuma redução, novo ensaio automático,
publicação ou fechamento de issue foi inferido desta integração.

A [Frente 2 entregou a unidade offline](fechamento-frente-2-resultados.md):
contrato de briefing/conteúdo, rubrica de suficiência, função/tool MCP aditivas
e revisão do texto real preservado, com números e ranking intactos. Integrações:
`f5cfbb7`→`0e6d0cf`, `f5adb9f`→`7a57b27`, `b30d1f4`→`eecc535`,
`c9aa26d`→`d705583`. A seleção consolidada direta passou em 79 testes/7,22 s;
a falha do lançador supervisionado foi preservada e segue sem causa isolada.
Trinta e sete arquivos novos de recibos/derivados foram conferidos no destino
privado persistente. Catálogo com fundamentos disponíveis não aprova seleção
NIM ausente, aderência real ou a configuração final ainda pendente.

O [contrato V7 dos sete atributos](https://github.com/leeunam/case-GALAXIES-IA/blob/0df616e5fd64dfc4947abde583f2664b66abf410/docs/fechamento-frente-1-contrato-v7.md) foi
integrado em `2926a3d`, com esclarecimento de tipos em `4f13fb0` e correção
de caminhos inválidos em `9a56760`, todos revisados. Na versão final da principal,
72 testes sintéticos passaram em 1,45 s, com prefixo B-cache de 905 colunas
preservado e sete colunas categóricas adicionais. O loader confere fontes e
recarga sintéticas e recusa cache observado antes de I/O. Não emite liberação
de qualidade nem conecta automaticamente os treinos legados à representação
de 912 colunas. A integração foi feita pelo integrador designado pelo autor
após passagem explícita da coordenação; os eventos anteriores foram preservados.

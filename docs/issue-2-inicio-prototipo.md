# Issue #2 — fatia de protótipo concluída

Checkpoint de 18/10/2026. Referência: [issue #2](https://github.com/leeunam/Galaxies-Inteli-Academy/issues/2).

O aluno aceitou entregar protótipo executável com treino e avaliação reais pendentes
se a fonte não for utilizável no prazo. Isso permite iniciar contratos, cadastro e
transporte da #2; não conclui a #1 nem fornece o baseline dos critérios originais.
O [corte aceito](uso-youtube-e-plano-de-entrega.md) e o
[checkpoint da amostra](issue-1-primeira-amostra.md) continuam sendo referências.

## Resultado desta fatia

Receber de um a cinco criativos registrados, com IDs opacos, setor moda/beleza,
objetivo divulgação e brief. Validar entradas e expor o mesmo caso de uso como função
Python e servidor FastMCP por stdio. Distinguir análise individual e comparação,
mesmo quando a previsão estiver indisponível.

Sem base elegível ou artefato utilizável, retornar indisponibilidade explícita de
baseline, previsão, faixa e ranking dependentes do modelo. Não substituir por zeros,
valores fabricados ou ordenação arbitrária apresentada como recomendação.

Usar fixtures sintéticas ou mídia própria/licenciada já autorizada. Não coletar novos
vídeos nem enviar dados ao NIM nesta fatia. Compatibilidade sintética dos algoritmos
não equivale a treino real; o explicador NIM ainda não teve geração validada.

## Critérios verificáveis

- Modos individual/comparativo para um, dois e cinco IDs distintos; rejeição de lista
  vazia, duplicatas e seis IDs.
- Erros seguros e estruturados para ID desconhecido, formato inválido, arquivo fora
  da pasta permitida, escape por link simbólico e ausência de artefato.
- Estados de disponibilidade claros e equivalentes pela função e por cliente MCP real.
- Logs fora do stdout reservado ao protocolo stdio; nenhuma credencial nas respostas.
- Demonstração reproduzível, testes adequados e instruções mínimas de execução.
- Partições, baseline de treino, faixa empírica e avaliação real continuam desmarcados
  até existir corpus elegível; fixtures não satisfazem esses critérios.

## Resultado implementado em 18/10

Contrato estrito, cadastro local persistente com IDs opacos, validação de mídia em
subprocesso limitado e função `analyze_creatives` implementados. CLI local permite
cadastrar, analisar e exportar esquemas JSON. O servidor FastMCP 4.1.0 expõe somente
a análise por IDs, reutilizando a função. Não houve nova coleta ou chamada ao NIM.

Verificação: **103 testes passaram**, Ruff e formatação de `scripts/` e `tests/`
aprovados, lock e dependências instaladas compatíveis. Um cliente SDK stdio real
confirmou paridade integral para um, dois e cinco candidatos, erros de entrada e
falhas de arquivos/cadastro. Outro teste conferiu o stdout bruto como JSON-RPC.
A demonstração com vídeos gerados confirmou os três modos de uso sem dados privados.
Instalação com o lock, 103 testes e demonstração também passaram em um novo ambiente
temporário, sem copiar o ambiente de trabalho existente.

O [contrato](issue-2-contrato.md) e o [roteiro de execução](issue-2-execucao.md)
descrevem instalação, limites, retenção, estados e comandos. Commits de implementação:
`d6f482a` (contrato/cadastro) e `8fa8926` (MCP, CLI e demonstração).

A fatia de protótipo está concluída. A issue #2 original permanece aberta por
partições de dados reais, baseline de treino, faixa empírica e demonstração preditiva
completa, dependentes da #1. Nenhum desses itens foi satisfeito por fixtures ou
desmarcado silenciosamente do escopo científico. A implementação sempre retorna
indisponibilidade de previsão e nunca carrega um modelo colocado arbitrariamente em disco.

## Extensão das rotinas estatísticas em 18/10

Após a publicação do protótipo, o aluno autorizou implementar separação por canal,
baseline e faixa com testes sintéticos. As rotinas offline estão prontas em
`scripts/channel_partitions.py` e `scripts/empirical_baseline.py`: agrupam canais e
duplicatas, congelam manifesto, calculam B0/Bcanal e quantis empíricos somente no
treino e verificam artefatos contra seus insumos. A
[documentação da extensão](issue-2-baseline.md) explica método, contratos e limites.

A demo `scripts/demo_baseline.py` gera todos os metadados e rótulos, sem acessar
registros reais. A suíte passou de 103 para **150 testes**, com Ruff e formatação
aprovados; instalação, 150 testes e demo também passaram em ambiente temporário
limpo, com dependências instaladas pelo lock e cache local, sem rede.
Commits das rotinas: `a029109` (partições) e `7144e29` (baseline/faixa/demo).
O campo `real_results_available` permanece `false`; o serviço Python/MCP continua
devolvendo `prediction_unavailable`, inclusive com artefato sintético presente.

Essa extensão conclui a implementação offline solicitada, sem completar os critérios
científicos originais da #2. Ainda é necessário resolver a base elegível da #1,
aplicar/congelar as partições reais, calcular a referência real e habilitar e
demonstrar seu uso pela função/MCP. Não houve coleta, treino em dados reais ou NIM.

## Briefing para o próximo chat

Ler `AGENTS.md`, `docs/briefing-de-trabalho.md`, `CONTEXT.md`,
`docs/proposta-tecnica.md`, a seção P2 de `docs/backlog-proposto.md`,
`docs/uso-youtube-e-plano-de-entrega.md` e este checkpoint. Implementar somente a fatia
descrita acima, com um executor por árvore de trabalho e commits por unidades lógicas.
Não marcar a #1 ou os critérios científicos da #2 concluídos por testes sintéticos.

O aluno deve conseguir explicar: o que é baseline e em que dados seria calculado;
por que o transporte MCP não cria capacidade preditiva; onde entram a validação dos
arquivos e a indisponibilidade do modelo. A IA pode executar código repetitivo após
esses contratos estarem compreendidos e revisados.

## Primeira unidade — seleção do modo

Em 18/10, o aluno praticou `determine_mode` em `scripts/creative_analysis.py`.
A revisão corrigiu a tentativa de acessar setor em uma lista: esta função recebe
somente IDs, valida quantidade de um a cinco e rejeita duplicatas. Um ID retorna
`individual`; dois a cinco distintos retornam `comparative`. Entradas inválidas
levantam `ValueError`; a conversão para erro estruturado pertence ao contrato futuro.

Os seis casos em `tests/test_creative_analysis.py` cobrem lista vazia, um, dois e
cinco IDs, duplicatas e seis IDs. A suíte completa passou com 53 testes; Ruff e
formatação dos dois arquivos também passaram. Esses controles verificam regras do
protótipo, sem evidência de desempenho preditivo. O exercício assume lista de strings;
tipos, formato e existência dos IDs ainda precisam de validação no contrato completo.

Ao concluir esse primeiro exercício, cadastro, função completa e transporte MCP ainda
estavam pendentes; foram implementados na etapa seguinte descrita acima. Baseline,
previsão, faixa e ranking reais permanecem indisponíveis.

## Revisão externa da passagem

A primeira revisão Google foi executada diretamente pelo aluno e conferida em 18/10:
status `SUCCESS`, código 0, relatório disponível e sem diagnóstico de erro. A passagem
para esta fatia da #2 pode começar. Isso não aprova a fonte nem conclui implementação.

Aproveitar as sugestões de limites, duplicatas, caminhos, links simbólicos e paridade
de saídas. Rejeitar a sugestão de apresentar empate em modo baseline: não há baseline
calculado. Explicar a indisponibilidade por texto determinístico, sem depender de NIM
nesta fatia. Cadastro, transporte e segurança são entregas a implementar e testar;
o relatório externo não é evidência de que essas capacidades já existem.

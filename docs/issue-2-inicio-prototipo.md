# Início da issue #2 — fatia de protótipo

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

A primeira revisão Google é uma verificação adicional do escopo. Instalação/configuração
foram verificadas, mas o relatório ainda não havia sido produzido neste checkpoint.
Trazer o resultado ao chat coordenador antes de abrir a execução da #2, conforme pedido
do aluno. A revisão externa não é aprovação automática de alterações ou da fonte.

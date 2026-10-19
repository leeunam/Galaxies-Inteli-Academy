# Início da issue #3 — experimento A

**Checkpoint posterior:** o [bloco offline foi implementado e executado](issue-3-treinamento-offline.md)
na branch `codex/issue-3-experimento-a`, com escolha somente na validação,
artefato recarregado e teste preservado. A integração função/MCP permanece pendente;
a #3 não foi concluída. O roteiro abaixo registra o ponto de partida aprovado.

Conferência de 18/10/2026, antes do primeiro treino de M1.
[#1](https://github.com/leeunam/Galaxies-Inteli-Academy/issues/1) e
[#2](https://github.com/leeunam/Galaxies-Inteli-Academy/issues/2) estão fechadas no
GitHub, com seus cinco critérios técnicos marcados. A
[#3](https://github.com/leeunam/Galaxies-Inteli-Academy/issues/3) permanece aberta:
M1 ainda não foi treinado, integrado ou servido.

## O que foi reconferido

- Importador real: 200 referências de 80 canais, 200 entradas de preditor e nenhum
  bloqueio operacional. Evidências, configuração e partições foram revalidadas;
  baseline recarregado e verificado. Setores: 112 beleza e 88 moda.
- Partições congeladas: 124 referências/48 canais no treino, 45/16 na validação e
  31/16 no teste. O baseline ampliado foi ajustado somente nos 124 IDs de treino.
- A suíte pública passou novamente: 250 testes; Ruff, formatação de 49 arquivos,
  lock offline e dependências compatíveis. A demo observada com o bundle ampliado
  repetiu seis paridades Python/MCP, para um, dois e cinco candidatos em cada setor.

Isso conclui a preparação operacional e o percurso de baseline. Não comprova
qualidade preditiva, calibração ou retorno do patrocínio. A curadoria foi assistida,
a amostra é de conveniência e a aprovação da plataforma continua não verificada;
as condições registradas na liberação não mudaram nesta conferência.

## Base de trabalho

Partir da branch `codex/issue-2-prototipo`, que contém a implementação e a liberação
em `584bce3`, e criar `codex/issue-3-experimento-a` para a execução. Não partir da
`main` local antiga sem incorporar essas mudanças. Um executor por árvore; worktree
separada se outro chat continuar editando a branch anterior.

Ler `AGENTS.md`, `CONTEXT.md`, [briefing](briefing-de-trabalho.md),
[proposta técnica, seção 3](proposta-tecnica.md),
[liberação ampliada](issue-1-base-para-experimento-a.md),
[contrato do importador](issue-1-manifesto-de-treino.md),
[contrato do serviço](issue-2-contrato.md) e o corpo atual da issue #3.

Pacote local privado:
`data/private/issue-1-pool-treino-20261018-v6/released-cohort-v1/`.
Reutilizar registros, índice de evidências, configuração, coorte e partições
existentes. Preservar também os artefatos apontados pelo índice. Não substituir
essa coorte pelo piloto de doze referências da #2, nem refazer a divisão.

## Entrega e sequência

1. **Entradas e treinamento offline.** Reutilizar `training_manifest`, as entradas
   aprovadas e os IDs congelados. A usa setor, duração, proporção altura/largura,
   estado do texto e MiniLM de 384 dimensões. Rótulo separado:
   `log1p(views públicas observadas)` com idade `30 <= dias < 37` na observação.
   Canal, datas, título, URL, métricas e hashes são auditoria, não features.
2. **Ajuste limitado e validação.** Seguir o protocolo existente: CatBoost CPU,
   quantis 0,1/0,5/0,9; profundidades 4/6 e L2 3/10; taxa 0,05, até 500 iterações,
   parada após 50 sem melhoria e semente 42. No máximo quatro configurações por
   quantil. Transformações aprendidas usam somente treino; escolha usa validação.
   Escolher q50 pelo MAE log médio por canal e extremos pela perda quantílica média
   por canal. Comparar com B0/Bcanal **da mesma coorte**. Não consultar o teste
   para selecionar ou ajustar; a avaliação final pertence à #6.
3. **Artefato e inferência.** Persistir modelos, política de ausências,
   configuração e hashes compatíveis com os extratores. Verificar recarga,
   finitude, conversão de volta para views e reparo de cruzamento que preserve
   q50. A faixa estimada não deve ser anunciada como cobertura validada.
4. **Mesmo percurso pela função e pelo MCP.** Extrair atributos dos inéditos com
   a mesma política congelada, incluindo ASR sem idioma forçado, chunks e revisão
   dos embeddings. Preservar silêncio/falha explícitos. Servir previsão, faixa e
   ranking pelo modelo q50, com definição do alvo, estados e limites de suporte.
   Testar entradas, artefato incompatível, extração indisponível e paridade real
   Python/MCP sem quebrar os modos de baseline já existentes.

Cada passo pode formar uma unidade lógica de commit com sua verificação e
documentação. Não separar código e testes necessários à mesma intenção.

## Aprendizagem e delegação

Antes de ampliar a execução, o aluno deve acompanhar um exemplo de treino e um de
validação, sem consultar resultados do teste: quais colunas chegam ao modelo,
onde fica o rótulo, como o log é invertido e por que baseline e CatBoost diferem.
Praticar a seleção de IDs/colunas e a leitura de uma comparação de validação.

A IA pode implementar a rotina repetitiva de ajuste, persistência, verificações e
integração após esse percurso estar claro. Um revisor independente verifica
vazamento, versões e equivalência, sem editar os mesmos arquivos do executor.
O aluno interpreta resultados, inclusive desempenho inferior ao baseline; não há
meta de acerto garantida ou autorização para esconder resultado negativo.

## Limites desta issue

Não iniciar B/C, Ridge opcional, SHAP/explicação livre ou LangGraph neste começo;
essas entregas mantêm suas issues. Não usar colunas visuais/VLM não aprovadas em A.
Não repetir coleta, renomear contagens atuais como rótulos antigos ou enviar dados
reais ao NIM. Não marcar #3 concluída por um treino sintético ou só pela existência
de um arquivo de modelo: os cinco critérios da issue exigem o percurso servido.

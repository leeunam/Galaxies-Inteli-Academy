# Briefing de trabalho

Este arquivo registra acordos de execução e escopo vigentes. O histórico detalhado de checkpoints e tentativas permanece na [revisão-base da documentação](https://github.com/leeunam/case-GALAXIES-IA/tree/0df616e5fd64dfc4947abde583f2664b66abf410/docs). Use `CONTEXT.md` como glossário do domínio.

## Acordos de trabalho

- Entregar mudanças pequenas, demonstráveis e verificáveis, mantendo juntos código, testes e documentação necessários à mesma unidade.
- O aluno conduz hipóteses, critérios de avaliação e interpretação científica. A IA auxilia investigação, revisão e tarefas repetitivas após existir uma amostra compreendida.
- Preservar contratos, dados, fontes, evidências, locks e protocolos congelados. Atualizar guias existentes antes de criar documentação pública nova.
- Separar evidência observada, derivada, sintética e opinião. Campos sem evidência permanecem desconhecidos; resultados negativos também são registrados.
- Nunca usar o teste reservado para selecionar modelos. Transformações aprendidas são ajustadas no treino; decisões de seleção usam validação.

## Escopo e estado confirmados

O iSee é uma aplicação local Python para análise de vídeos, com CLI, função compartilhada e MCP por stdio. Não há API web nem UI web. O projeto foi desenvolvido por Leunam Sousa para a Galaxies / Inteli Academy. A integração da persona à plataforma interna da Galaxies está fora deste repositório.

O modelo A200 continua servido. A300, B-cache e C-cache têm resultados reais de validação na mesma amostra de 66 vídeos e 37 canais: MAE médio de `log1p(views)` por canal, respectivamente, 1,7761, 1,6584 e 1,5444, contra 1,7349 do A200. O teste final de 31 casos permanece fechado.

V7 tem verificações com gravadores e ensaios nativos B e C sobre dados inventados, em fixtures/ambientes distintos, sem comparação científica pareada ou bundle completo. Não houve treino V7 observado; VLM de sete campos, extração das 269 referências restantes e qualidade externa continuam pendentes. A restauração de uma fonte TRAIN parou sem comprovar a folha original nem liberar atributos. O manifesto de 32 referências é de auditoria TRAIN existente, não de vídeos faltantes da coorte.

A fachada NIM dinâmica é optativa: duas tentativas numéricas sobre o mesmo pacote cacheado ficaram indisponíveis (HTTP 200 de causa desconhecida e, após correção do parser, HTTP 503); um controle visual sintético separado teve HTTP 200 com schema inválido. Não houve IDs aceitos ou revisão qualitativa remota possível. O briefing acadêmico teve aderência parcial por metadados, sem certificação comercial. A configuração final e a experiência com mídia nova mais seleção externa continuam sem aceite; não há reenvio programado. Consulte o [registro da tentativa](fechamento-frente-2-resultados.md#tentativa-real-autorizada-de-2310). Não equiparar dados MCP sintéticos ou resultados salvos a uma análise nova.

O alvo definido é a contagem pública de views observada entre 30 e menos de 37 dias de idade, sem reconstruir o valor exato do dia 30. Métricas públicas, coleta operacional, direitos e condições da plataforma são questões distintas. A autorização operacional documentada não comprova aprovação da plataforma nem altera decisões científicas.

## Privacidade e recursos

Não versionar segredos, mídia, dados privados, modelos ou resultados locais. O clone público contém exemplos sintéticos, contratos e documentos, mas não contém a coorte privada, pesos dos extratores ou bundles de treino. Usar conteúdo em serviços externos somente conforme autorização específica já registrada. Não interpretar um arquivo ignorado pelo Git como inacessível.

O trabalho autônomo deve ter entradas, saída esperada, orçamento e critérios de parada definidos. Não iniciar coleta, treino, inferência externa ou acesso a dados confidenciais por inferência de escopo; decisões científicas ou de recursos externos seguem as autorizações expressas existentes. Execução noturna não amplia o escopo nem substitui revisão do aluno.

## Aprendizagem e commits

Reservar cada bloco para definir resultado, praticar uma parte, implementar, verificar e explicar. Priorizar formulação do alvo, disponibilidade das informações, baseline, separação dos dados, métricas, intervalos e análise de erros. O aluno deve conseguir explicar os passos e limitações entregues.

Fazer commits ao concluir unidades lógicas, com uma intenção principal por commit. Revisar o conteúdo e executar verificações adequadas antes de registrar. Separar assuntos independentes e manter alterações necessárias à mesma entrega juntas. Excluir segredos, dados sensíveis e temporários.

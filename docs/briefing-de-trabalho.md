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

V7 tem verificações com gravadores e ensaios nativos B e C sobre dados inventados, em fixtures/ambientes distintos, sem comparação científica pareada ou bundle completo. Não houve treino V7 observado; a validação perceptiva dos sete campos VLM, a extração das 269 referências restantes e a qualidade externa continuam pendentes. O manifesto de 32 referências é de auditoria TRAIN existente, não de vídeos faltantes da coorte.

O contrato aditivo dos sete campos valida tipos e referências a frames sem reparar respostas nem forçar close-up e demonstração para desconhecido (`unknown`). A avaliação pura exige 32 referências TRAIN, 16 por setor, com limiares por campo/setor e revisão independente; não emite aceite ou release, mesmo se todos os limiares passarem. A amostra original tem 24 canais reais: a avaliação vinculada permite as repetições comprovadas pelos metadados, sem mudar limiares nem presumir independência entre imagens do mesmo canal. O carregador V7 permanece bloqueado. As 32 folhas originais conferem com seus hashes. Foram recuperadas 24 PNGs por aquisição temporária, com propriedades iguais e hash de mídia divergente; todos os vídeos temporários foram apagados. Isso comprova identidade das imagens, não da mídia nem qualidade perceptiva. As referências dos sete campos estão completas por duas anotações assistidas independentes e adjudicação de 26 divergências em 14 imagens, seladas antes de qualquer geração TRAIN desta continuação. As referências antigas foram preservadas. Não são anotações humanas nem uma nova amostra cega; a qualidade do candidato continua pendente. A coorte de 300 e o split 203/66/31 permanecem intactos. O [guia de explicação](guia-explicacao-isee.md) registra o uso do contrato.

A fachada NIM dinâmica é optativa: duas tentativas numéricas sobre o mesmo pacote cacheado ficaram indisponíveis (HTTP 200 de causa desconhecida e, após correção do parser, HTTP 503); um controle visual sintético separado teve HTTP 200 com schema inválido. Não houve IDs aceitos ou revisão qualitativa remota possível. O briefing acadêmico teve aderência parcial por metadados, sem certificação comercial. A configuração final e a experiência com mídia nova mais seleção externa continuam sem aceite; não há reenvio programado. Consulte o [registro da tentativa](fechamento-frente-2-resultados.md#tentativa-real-autorizada-de-2310). Não equiparar dados MCP sintéticos ou resultados salvos a uma análise nova.

As sondagens do controle visual sintético com `response_format/json_schema` identificaram dois erros distintos: HTTP 503 com `ResourceExhausted` e limite do worker (`16/16`), seguido, em continuação separada, de HTTP 500 informando recursos do schema não suportados pelo `xgrammar`. O primeiro não comprova duração ou escopo do limite; o segundo não identifica a palavra-chave incompatível. Ambos falharam antes de gerar atributos. Nenhuma imagem TRAIN foi enviada nessas sondagens; a qualidade dos sete campos permanece pendente.

Um perfil de geração simples foi adicionado sem alterar prompt, parser estrito ou critérios. Sua verificação sintética única retornou HTTP 200 em cerca de 1,53 s, com os sete campos estruturalmente válidos: cinco booleanos `unknown`, cenário `graphic` e formato `other`. O controle reprovou por abstenção nos cinco booleanos; não houve nova chamada. Isso demonstra uma resposta válida nesse pedido, sem comprovar todas as alternativas do schema, qualidade perceptiva ou a causa das abstenções. Nenhuma imagem TRAIN foi enviada e não houve liberação dos 269 nem troca do A200.

O alvo definido é a contagem pública de views observada entre 30 e menos de 37 dias de idade, sem reconstruir o valor exato do dia 30. Métricas públicas, coleta operacional, direitos e condições da plataforma são questões distintas. A autorização operacional documentada não comprova aprovação da plataforma nem altera decisões científicas.

## Privacidade e recursos

Não versionar segredos, mídia, dados privados, modelos ou resultados locais. O clone público contém exemplos sintéticos, contratos e documentos, mas não contém a coorte privada, pesos dos extratores ou bundles de treino. Usar conteúdo em serviços externos somente conforme autorização específica já registrada. Não interpretar um arquivo ignorado pelo Git como inacessível.

O trabalho autônomo deve ter entradas, saída esperada, orçamento e critérios de parada definidos. Não iniciar coleta, treino, inferência externa ou acesso a dados confidenciais por inferência de escopo; decisões científicas ou de recursos externos seguem as autorizações expressas existentes. Execução noturna não amplia o escopo nem substitui revisão do aluno.

## Aprendizagem e commits

Reservar cada bloco para definir resultado, praticar uma parte, implementar, verificar e explicar. Priorizar formulação do alvo, disponibilidade das informações, baseline, separação dos dados, métricas, intervalos e análise de erros. O aluno deve conseguir explicar os passos e limitações entregues.

Fazer commits ao concluir unidades lógicas, com uma intenção principal por commit. Revisar o conteúdo e executar verificações adequadas antes de registrar. Separar assuntos independentes e manter alterações necessárias à mesma entrega juntas. Excluir segredos, dados sensíveis e temporários.

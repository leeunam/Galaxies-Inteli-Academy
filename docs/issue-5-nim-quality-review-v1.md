# Qualidade da explicação NIM: auditoria offline do resultado aceito

A chamada NIM aceita demonstrou seleção estrutural de evidências e preservação
do relatório. **A qualidade de uma explicação livre da NVIDIA continua sem
avaliação**: o provedor devolveu IDs, e os 12 textos em português foram escritos
previamente no catálogo local. A presente revisão avalia esses textos, sua
cobertura e seus limites; não transforma aceitação do esquema em aprovação
qualitativa ou aderência à campanha.

## Material e método

Foi revisado um único resultado aceito, de 21/10/2026, com três criativos,
números, SHAP e referências inteiramente inventados. O recibo autorizado
`global-diagnostic-result-v1.json` foi lido somente após conferir seu SHA-256
`f3f57cebb8bf8ad13752704a1207f66ab97c85bbef358146c9436256b14747f3`.
Não foi copiado para esta entrega. Sua identidade e o resultado técnico já
constam no [registro público da execução](issue-5-nim-global-diagnostic-v1-resultados.md).

A comparação offline usou a [fixture pública](../orchestration/fixtures/nim-graph-three-invented-v1.json),
o [renderer local](../scripts/explanation_evidence.py) e os
[exemplos do pedido fixo](../orchestration/galaxies_orchestration/nim_global_selection_payload_v1.py).
Foram comparados o objeto completo de análise, o pacote, cada objeto de claim
(ID, criativo e texto) e os números de SHAP. A revisão de clareza e de alegações
é uma leitura assistida por agente, sem painel humano ou teste de compreensão
com usuários. Os critérios abaixo são explícitos; não há nota agregada.

Nenhuma nova chamada, credencial, mídia, treino, teste reservado ou instalação
foi usada. O resultado original, seus hashes, o contrato e a autoridade de
validação permanecem intactos. A [evidência derivada](evidence/issue-5-nim-quality-review-v1.json)
contém somente métricas e identificadores do material inventado já público.

## Rubrica aplicada

| Dimensão e critério | Observação | Julgamento delimitado |
| --- | --- | --- |
| Fidelidade: manter relatório, ranking e fatos autorizados | Análise e pacote iguais à fixture; 12/12 objetos de claim iguais ao catálogo, incluindo texto e associação ao criativo | Verificada em relação à fonte inventada; não valida a previsão nem fatos de mídia real |
| Cobertura: expor previsões, incerteza e fundamentos para comparar os três criativos | 3/3 previsões, 3/3 faixas, 1/12 grupos SHAP e 2/3 referências | Parcial; não demonstra uma explicação suficiente do ranking |
| Limites: declarar alvo, falta de validação e interpretação exploratória | Os três avisos globais estão presentes; cada faixa diz que sua cobertura não foi validada | Presentes no texto local inspecionado; não mede se usuários os entendem |
| Português e clareza: leitura compreensível, unidade correta e origem inequívoca | Português legível, mas com jargão, uma imprecisão sobre a escala SHAP e uma frase legada ambígua sobre provedor externo | Revisão parcial do renderer; português produzido pela NVIDIA não foi observado |
| Alegações sem suporte: evitar promessa paga, causalidade ou superioridade | Nenhuma promessa afirmativa desse tipo nos 12 claims; os avisos a negam expressamente | Nenhuma encontrada nesta amostra; não é avaliação de alucinação em geração livre |
| Aderência: justificar a escolha diante de briefing e conteúdo da campanha | O pedido fechado contém um catálogo; não fornece conteúdo de campanha suficiente nem admite justificativa livre | Não avaliável; `adherence_status=not_evaluated` preservado |

## Cobertura observada

| Tipo | Exibido / disponível no catálogo |
| --- | --- |
| Limites globais | 3 / 3 |
| Previsões q50 | 3 / 3 |
| Faixas q10/q90 | 3 / 3 |
| Grupos SHAP | 1 / 12 |
| Referências descritivas de treino | 2 / 3 |
| Total | 12 / 24 |

Os seis fatos obrigatórios (três limites e três previsões) estão presentes.
O renderer os inclui mesmo que o seletor os omita; sua presença, isoladamente,
não mede a qualidade da decisão remota. O limite global de 12 não exige quota
por criativo ou cobertura de todos os tipos; as omissões não são violações do
contrato aceito.

| Criativo inventado | q50 | Faixa | Grupos SHAP exibidos | Referências exibidas |
| --- | --- | --- | --- | --- |
| c1 | 137 | 41–311 | setor: +0,1 em log1p(views) | 1 / 1 |
| c2 | 283 | 97–577 | nenhum | 1 / 1 |
| c3 | 211 | 61–433 | nenhum | 0 / 1 |

O ranking numérico preservado é **c2 → c3 → c1**, como prioridade exploratória
para teste. O texto selecionado não explica por que c2 é o primeiro: não há
SHAP de c2 ou c3 na saída, nem contribuição negativa de qualquer criativo.
Em c1, o grupo exibido (+0,1) não é o maior em valor absoluto; o catálogo
contém também +0,4, +0,3 e −0,2. Nenhum criativo tem todos os seus quatro grupos
exibidos. Isto limita a leitura comparativa e a reconstrução pela saída; não
estabelece que outra seleção teria maior utilidade sem um critério acordado.

As referências explicam similaridade técnica e de fala, não desempenho futuro.
A ausência da referência de c3 não autoriza concluir que ela não existe: ela
está no catálogo inventado e foi omitida desta seleção.

## O exemplo e a independência da seleção

O conjunto dos 12 IDs renderizados coincide exatamente com o exemplo de 12 IDs
do pedido. O recibo registra 12 IDs remotos distintos aceitos e 12 claims finais;
como o renderer apenas acrescenta os obrigatórios, os conjuntos remoto e final
são iguais neste caso. A ordem original da resposta remota não é inferida.

O pedido diz que o exemplo ilustra sintaxe e contagem, sem preferência fixa.
A coincidência é uma observação, **não uma prova de cópia ou de sua causa**.
Ainda assim, esta única amostra não distingue uma seleção independente de uma
resposta orientada pelo exemplo e não sustenta uma conclusão sobre seleção
útil em casos diferentes. Os mesmos SHAP inventados se repetem nos três
criativos, o que também reduz a diversidade do caso avaliado.

## Duas correções de leitura necessárias

**Escala SHAP.** O claim `c1_shap_sector` termina com “A soma assinada de base e
grupos reconstrói q50.” A formulação é imprecisa sobre a unidade: a soma é
`log1p(q50)`; para obter views é preciso aplicar `expm1`. Na fixture, as três
somas são aproximadamente 4,927254, 5,648974 e 5,356586, cujas transformações
inversas são 137, 283 e 211 views. O cálculo confere, mas o texto isolado pode
induzir uma soma direta em views. Além disso, só um grupo de c1 foi exibido;
não é possível fazer a soma completa apenas com essa seleção.

**Origem da explicação.** O campo legado `analysis.explanation`, preservado
integralmente da análise numérica, diz “não houve chamada a explicador externo”.
Ele descreve a etapa numérica anterior à seleção. A execução completa tem uma
chamada NIM comprovada em `current_provider`; seus textos continuam locais.
Exibir a frase legada como resumo do percurso inteiro daria uma interpretação
errada da proveniência.

Estas ressalvas são aditivas a esta auditoria: nenhum texto selado, pacote,
hash ou corpo autorizado foi reescrito. Uma apresentação futura deve dizer
explicitamente que a soma está na escala log e separar o resumo numérico da
seleção NIM. Alterar o catálogo canônico requer atualizar suas dependências e
pins em uma unidade própria; esta revisão não promove uma mudança de contrato.

## O que falta para fechar a validação qualitativa

A fidelidade e os limites do renderer têm evidência local favorável nesta
amostra. A suficiência comparativa é parcial, com as ambiguidades acima.
Continuam sem demonstração: português livre da NVIDIA, síntese útil do ranking,
aderência a uma campanha, robustez a casos diferentes e validade em mídia real.
`live_validated` descreve a chamada aceita; não responde a essas perguntas.

Para validar uma explicação livre, seria necessário primeiro definir um
contrato separado e revisável: caso inteiramente inventado com briefing,
evidências e resposta esperada, números sob autoridade local e critérios
explícitos para português, cobertura e alegações. O corpo atual proíbe prosa;
repeti-lo não responderia à pergunta sobre geração livre. Qualquer experimento
remoto futuro precisa de proposta própria com payload, destino, quantidade e
limites, mantendo teto R$0 e sem credenciais ou mídia neste material. **Esta
auditoria não executa nem autoriza esse experimento.** O saldo da chamada já
consumida permanece zero.

A frente entrega uma revisão verificável do material existente e pendências
específicas. O requisito de qualidade ampla do explicador permanece aberto;
nenhum campo de aderência ou aceite integral do projeto foi promovido.

# Retomada única do lote visual — resultados dos controles

A retomada autorizada em 22/10/2026 às 12:52 UTC foi executada com o comando
absoluto revisado, em namespace novo. A [tentativa anterior](issue-4-native225-batch-development-attempt-v1-results.md)
permanece selada e seus 28 arquivos conferem por hash. O início global de
12:30:48.880978 UTC foi herdado; o limite conservador continua 23:30 UTC.
A janela dos controles foi ajustada até 13:17:03.810303 UTC dentro desse limite.
O [recibo sanitizado](evidence/issue-4-native225-batch-resume-v2-results.json)
preserva identidades, tempos, hashes, resposta e limites.

## Resultado e parada

Foram realizadas seis inferências locais, sequenciais. Os cinco primeiros
controles retornaram ausência de produto e foram aceitos. O sexto,
`text-48-0-250`, retornou um objeto completo e válido:

```json
{"state":"uncertain","item_configuration":"unclear","presented_categories":[]}
```

A projeção correta é `product_visible_early="unknown"`. O protocolo exige
`false` nesse controle negativo, portanto o resultado foi rejeitado e a etapa
encerrou imediatamente. Não houve repetição. Sete controles, incluindo o
positivo relacional, ficaram sem execução. A auditoria de 32 casos não começou;
nenhuma aquisição foi feita. Os seis consumos estão preservados e os saldos
não usados não estão liberados para novas chamadas.

Essa falha é de decisão perceptiva por abstenção. A resposta não apresentou
um produto positivo nem um erro de formato. Não há correção de parser que
justifique convertê-la em ausência. O resultado não aprova a candidata visual.
A etapa encerrada não fornece uma taxa geral de acurácia.

## Runtime efetivamente observado

Nas seis chamadas, o encoder e o decode terminaram com 240 tokens visuais;
todos os contratos técnicos passaram. O maior runtime nativo foi 26,82 s e
o maior tempo externo por chamada, incluindo cápsula e coleta, foi 28,06 s.
O pico nativo máximo foi 2.627,30 MiB, aproximadamente 2,57 GiB; o pico somado
observado pelo operador foi aproximadamente 2,63 GiB. As medições ficaram
abaixo dos limites de 80 s e RSS cooperativo de 3,3 GiB. Elas demonstram
funcionamento nesses seis controles, sem validar desempenho em toda a base.

A cápsula sem rede e o preflight com o argv absoluto efetivo passaram antes
do primeiro dispatcher. O modo preparatório exercitou `verify(1)` com attempt
só em memória, sem inferência. A revisão independente conferiu os operadores,
a herança dos contadores e os deadlines. Não houve novas alterações nos
arquivos públicos do runtime ou na candidata depois do congelamento da v2.

O ledger final está selado, com seis chamadas, zero auditorias, zero aquisições
e nenhuma operação pendente. Toda limpeza foi confirmada, scratch está vazio
e não restam workers. Não houve NVIDIA, treino real, abertura do holdout,
publicação ou alteração de configuração do sistema. Base, M1 e imagens
protegidas permanecem fora da alteração.

## Comparação offline e próximos pré-requisitos

Entre os controles 5 e 6, a receita mantém fonte, tamanho 48, cor preta, texto
`ABC123`, fundo branco e dimensões; muda apenas a posição vertical de 8 para
250, além do identificador. A primeira resposta foi ausência; a segunda,
incerteza. Os dois resultados sustentam uma hipótese de sensibilidade à
posição nessa condição, sem identificar um mecanismo geral ou justificar
outra rodada cega. Nenhuma inferência adicional foi feita para essa análise.

A próxima candidata exige hipótese e protocolo delimitados. Os gates atuais
não foram alterados e esta rodada não permite seguir com a candidata reprovada.

A investigação estática também identificou um caminho para a projeção de treino:
um emissor a montante pode validar o contrato de partições e emitir somente
sample, canal, setor e mídia dos 203 treinos, sem features, targets ou pesos.
Não foi aberto o manifesto misto nem produzida a projeção real nesta unidade.
O seletor atual pede hashes de frames para todos os 203 antes de selecionar os
32, enquanto a fila histórica dispõe de propriedades e hash da folha, que não
permite deduzir os hashes dos crops. A preparação precisa separar duas fases:
congelar os 32 IDs pelas exclusões e ordem originais; só depois conferir as
reaquisições autorizadas e selar os frames antes das anotações e inferências.
Isso é trabalho técnico offline, não pedido de 32 arquivos novos ao usuário.

Seleção, anotações cegas e revisão independente continuam pendentes. B/C real
e avaliação final permanecem bloqueados pela reprovação visual e pelos demais
pré-requisitos científicos. Não há declaração de conclusão integral.

# Contraste de prompt em três casos — resultado reprovado

Os três despachos terminaram tecnicamente, sem timeout. A candidata acertou os dois controles negativos, mas classificou o positivo previamente anotado como incidental. A rodada parou no primeiro erro perceptivo e está selada, sem retry, auditoria ou liberação de B/C.

| Caso | Esperado | Resposta observada | Aceite | Tempo nativo |
| --- | --- | --- | --- | --- |
| negative-control-5 | `false` | `no_target` / `absent` → `false` | passou | 18.128 s |
| negative-control-6 | `false` | `no_target` / `absent` → `false` | passou | 18.635 s |
| annotated-product-positive | `true` | `incidental_only` / `incidental` → `false` | reprovou | 24.844 s |

## Condições e evidência

Alterou-se somente a cláusula do prompt: caracteres impressos, isoladamente, não estabelecem um item-alvo. Modelo, pesos, schema e ordem `state_first`, imagens, seed 42, temperatura zero, quatro threads, native225 e saída de 64 tokens permaneceram fixos. O schema continuou admitindo `uncertain`; `unknown` não foi convertido em ausência.

O positivo foi reconstruído da folha protegida pelo crop `(0,25,320,355)` e conferido contra o hash histórico `4a22deaca1910529f560c3af6da06270aae129a53e0cdcea76c597077fa4bda6`. Não houve aquisição ou novo controle. Os três inputs eram PNG RGB 320×330; cada chamada observou 240 tokens visuais.

A rodada do operador durou **62.372 s**, dentro de 260 s, com máximo de 80 s por despacho. Preparação/revisão e preflight sem modelo não integram essa duração. Pico nativo observado: 2628.723 MiB; pico externo: 2.631 GiB, abaixo de 3,3 GiB. A admissão exigiu pelo menos 6 GiB disponíveis. Custo externo: **R$0**, rede isolada, zero NVIDIA, downloads, treinamento ou abertura do holdout.

Os três runtimes nativos devolveram exit 0. O controlador do positivo devolveu exit 2 por reprovação perceptiva; isso não foi falha de execução do modelo. As capturas brutas e recibos privados foram preservados. Limpeza confirmada nos três, scratch vazio e zero workers remanescentes.

Os 65 hashes anteriores e os 28 pins de fontes conferiram. As seis chamadas anteriores continuam em sua rodada selada; o agregado deste orçamento é agora 9/397, com zero aquisições. O início global original de 12:30:48 UTC e o teto adicional de 23:30 UTC de 22/10 foram preservados; não houve reinício das 11 horas.

## Interpretação limitada

O controle 5 manteve ausência e o controle 6 passou de `unknown` no run anterior para ausência correta. O positivo de produto, com a mesma pergunta dos negativos, falhou: a apresentação anotada em primeiro plano foi tratada como incidental. A hipótese não demonstrou discriminação suficiente para continuar.

Não há comparação pareada desse positivo com o prompt antigo sob esta mesma configuração native225; portanto, este resultado não prova que a nova frase causou o falso negativo. Ele também não isola resolução, quantização ou capacidade geral do modelo. Não houve mudança de rótulo, exceção de gate ou nova tentativa após a falha.

Plano lógico: `b35e824c92b1235862afb750419136c4197d9a64206a1c51117a663006aa6faa`. Prompt: `287344f0e57830017f58d0f06e2efdebec6e51a03e0b1fd16fbdad5055c9ee27`. Os números, hashes de inputs/respostas, tempos por chamada e flags estão na [evidência sanitizada](evidence/issue-4-three-case-prompt-result-v1.json). O [registro da rodada anterior](issue-4-native225-batch-resume-v2-results.md) permanece intacto. A validação visual ampla, B/C completos e avaliação final continuam pendentes.

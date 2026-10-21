# Hipótese espacial após o contraste de gramática

Revisão estática em 21/10/2026. O [ensaio encerrado](issue-4-vlm-percepcao-gramatica-resultados.md)
manteve o falso positivo nos dois modos e não sustentou candidata. A hipótese
de maior densidade visual tem fundamento para discussão, mas **não está
demonstrada nem autorizada para execução**. Não há código, fila, reserva ou
orçamento novos nesta unidade. A revisão do principal continua em andamento.

## O aviso e seu alcance

O ramo do Qwen3VL está explicitamente entre os tipos que emitem o aviso de
1.024 tokens quando o mínimo visual fica abaixo desse patamar. A validação
também recusa mínimo de pixels maior que máximo. Portanto, trocar somente
o mínimo para 1.024 e conservar máximo 128 seria incompatível; uma hipótese
de orçamento 1.024 teria de tratar min/max juntos como um fator.
[Fonte fixada, `clip.cpp`](https://raw.githubusercontent.com/ggml-org/llama.cpp/797de63b2/tools/mtmd/clip.cpp).

A [discussão upstream citada pelo aviso](https://github.com/ggml-org/llama.cpp/issues/16842)
trata de coordenadas/bounding boxes e resize, incluindo arredondamento para
grade. Transferir essa motivação à decisão binária mão–tecido é hipótese,
sem garantia para nosso modelo quantizado de 2B ou para esses crops.
Uma flag de 1.024 não deve ser confundida com contagem efetiva exatamente
igual; essa contagem precisa ser observada, sem retuning para perseguir um número.

O código de decodificação não inclui Qwen3VL entre os caminhos não causais:
ele cai no retorno padrão causal. O cap da CLI a `n_ubatch` é condicionado
ao caminho não causal, conforme o fonte CLI local já verificado. Assim,
não há base estática para aumentar batch/ubatch junto do orçamento Qwen;
isso introduziria outro fator sem necessidade demonstrada.
[Fonte fixada, `mtmd.cpp`](https://raw.githubusercontent.com/ggml-org/llama.cpp/797de63b2/tools/mtmd/mtmd.cpp).
A inspeção estática da função correspondente no ELF instalado é compatível
com os ramos especiais do fonte; não houve chamada dessa função ou carga de pesos.

## Contexto e recursos: plausibilidade, não garantia

| Evidência local atual | Consequência para a revisão |
|---|---|
| PNGs de entrada 320×330 preservados | Upscale interno não recupera detalhe nativo ausente. |
| 100 tokens visuais observados por célula | Há um contraste de densidade possível, independente de retirar gramática. |
| Contexto configurado 3.072 e saída até 64 | Não há impedimento aritmético imediato para cerca de 1.024 tokens visuais; ocupação total ainda precisa ser verificada. |
| Prompt comum de 491 bytes UTF-8 | Bytes não são contagem tokenizada nem incluem todo o template. |
| Pico anterior 2.587,781 MiB; teto 3,3 GiB | Diferença aproximada de 791,419 MiB, sem comprovar que o encoder maior cabe. |
| Maior sessão anterior 6,9563 s | Não permite extrapolar linearmente o tempo em maior densidade. |

Os números vêm do agregado local do contraste, sem nova leitura de pesos,
ambientes ou conteúdo do teste. Mais posições/patches alteram trabalho e
memória intermediária; o pico anterior não é previsão do novo pico. Não
prometer caber em 45 s ou 3,3 GiB sem observação. Contexto textual, tokens
visuais efetivos e overhead precisam permanecer dentro do contexto original;
não ampliar contexto, RSS ou duração automaticamente para concluir uma tentativa.

## Questões para a decisão do principal

Uma ideia em discussão é observar o mesmo positivo e negativo em duas sessões
com orçamento visual maior, preservando fonte PNG, prompt/contrato, schema,
seed, temperatura, runtime/modelo e parâmetros CPU. Antes de qualquer código,
a revisão deve fixar um dos modos originais de gramática, a sequência, os
limites e o critério de aumento efetivo frente aos 100 tokens observados.
As respostas baixas já concluídas seriam uma referência histórica, sem
apresentar duas sessões novas como quatro células contemporâneas pareadas.

Esse desenho só seria informativo se o log confirmar que a intervenção
aumentou a densidade de fato e a operação permanecer íntegra. Falha de
identidade/encoder/contexto/recursos/limpeza deve encerrar, sem elevar outro
parâmetro, repetir ou trocar caso. Não há autorização para essa ideia neste
documento e nenhuma configuração executável foi preparada.

Se o negativo mudar para `no` e o positivo continuar `yes`, haverá apenas uma
hipótese de candidata para avaliação maior. Se o erro persistir, não haverá
candidata apoiada por esse contraste. Mesmo eventual melhora não recupera
informação da fonte, não identifica toda a causa histórica e não aprova
atributos. Gates originais, auditoria independente e teste reservado continuam
intactos; M1 e B/C não mudam por essa revisão.

Alternativa caso a revisão não sustente a intervenção: documentar a limitação
relacional observada e investigar um predicado visual atômico apoiado nas
anotações reveladas, com especificação própria antes de gerar. Não transformar
uma rodada sem hipótese em requisito automático de continuidade.

## Verificação desta unidade

Somente leitura estática de fonte/ELF e de agregados públicos, consulta a
fontes primárias e documentação. Sem testes novos, carga de modelo, geração,
aquisição, HTTP NIM, mudança de fonte selada ou reabertura de autorização.
O erro `Path` da conferência posterior anterior já havia sido corrigido e as
preservações concluídas antes do commit `63f6117`; não exigiu nova inferência.

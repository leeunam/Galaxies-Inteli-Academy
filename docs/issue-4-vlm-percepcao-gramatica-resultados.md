# Contraste real de gramática: falso positivo nos dois modos

Em 21/10/2026, as quatro células do
[protocolo congelado](issue-4-vlm-percepcao-gramatica-proposta.md) concluíram
em **25,8088 s**, com JSON válido, encoder e decodificação observados em todas.
O positivo recebeu `yes` nos dois modos; o negativo também recebeu `yes` nos
dois, contrariando seu esperado diagnóstico `no`. **Retirar a gramática não
corrigiu o negativo neste ensaio; nenhuma candidata foi sustentada.**

A [evidência agregada](evidence/issue-4-vlm-percepcao-gramatica-resultados.json)
vincula configuração, revisão e recibos sanitizados, sem IDs, localizadores de
mídia, pixels ou corpo bruto. O par é de treino já revelado, com esperados
derivados da revisão assistida V14, sem independência ou certificação nova.

## Quatro células, sem reparo

| Célula | Crop | Gramática | Esperado | Resposta | Formato | Comparação |
|---|---|---|---|---|---|---|
| 1 | Positivo real revelado | sim | `yes` | `yes` | válido | correto |
| 2 | Mesmo positivo | não | `yes` | `yes` | válido | correto |
| 3 | Negativo real revelado | não | `no` | `yes` | válido | incorreto |
| 4 | Mesmo negativo | sim | `no` | `yes` | válido | incorreto |

Houve zero abstenções, formatos inválidos, falhas técnicas, retries ou células
substituídas. Não foi necessário exercer a continuidade por formato inválido
na execução real; esse comportamento foi verificado com processos inventados.
Os quatro stdout passaram inteiros pelo parser comum, sem coerção, extração
de fragmento JSON ou uso de stderr. A abstenção permaneceu `uncertain`;
nenhuma resposta `unknown` foi convertida depois da geração.

Pergunta, contrato textual, pixels, modelo/projetor, seed, temperatura,
contexto, limites de imagem e parâmetros CPU foram iguais em cada par.
Somente a aplicação de `--json-schema-file` variou. O predicado era a relação
mão–tecido e o tecido afastado do corpo visíveis no quadro, sem intenção ou
movimento inferidos. A ordem predefinida foi respeitada em processos novos.

## Operação e encoder

| Célula | Sessão nativa | Pico RSS (MiB) | Tokens de imagem | stdout / stderr (bytes) |
|---|---:|---:|---:|---:|
| 1 | 6,9563 s | 2.575,125 | 100 | 21 / 19.031 |
| 2 | 5,8406 s | 2.573,359 | 100 | 21 / 19.031 |
| 3 | 6,2606 s | 2.587,781 | 100 | 21 / 19.031 |
| 4 | 6,3426 s | 2.580,754 | 100 | 21 / 19.031 |

Os quatro retornos foram 0. Início/fim de codificação e batch 1/1 de
decodificação com 100 tokens foram observados por chamada, com limpeza
confirmada. Isso sustenta o percurso visual observado, não qualidade de
representação, atenção ou uso semântico correto. O aviso fixo de grounding
em 1.024 tokens apareceu; não foi tratado como causa medida dos erros.

Limites respeitados: quatro chamadas, 180 s globais, até 45 s por dispatch
com reserva de limpeza, RSS 3,3 GiB e canais limitados. O recibo foi salvo
antes de remover cada scratch. A fila terminou `scope_completed`, consumida
e selada, com zero workers e zero scratch próprios no snapshot final.
Nenhum saldo habilita reentrada ou nova tentativa.

## Leitura e próximo passo

O critério proposto para sustentar a retirada da gramática exigia corrigir
o negativo, preservar o positivo e manter formato válido. O segundo e o
terceiro ocorreram, mas o negativo persistiu errado. Não há base neste par
para promover o modo livre como correção de produto ou da relação visual.

Concordância dos modos não prova ausência de influência da gramática em
outros casos. Esse prompt/schema curto também não é a instrução histórica
com 22 objetos; o contraste não identifica a causa ampla da V16. O erro nos
dois modos não atribui causa ao encoder por exclusão. Quantização, densidade
visual, instrução e capacidade relacional permanecem hipóteses não isoladas.

O próximo trabalho deve investigar uma hipótese visual distinta antes de
propor candidata: por exemplo, compatibilidade entre densidade de tokens e
o detalhe relacional observado, ou decomposição do predicado em relações
visíveis mais simples. O aviso de grounding apenas motiva investigação;
não autoriza aumentar resolução/tokens ou trocar modelo. Qualquer contraste
novo exige configuração, limites e revisão próprios, mantendo os casos
revelados e sem reusar esta autorização. Nenhuma nova implementação ou
inferência foi iniciada a partir desse resultado.

## Verificação e preservação

Implementação em `ad6e523` e `bf0c7d7`; execução sobre `e2c064a`. Passaram
35 testes direcionados, Ruff e formatação antes da geração. O preflight
reproduziu os dois PNGs e verificou prompt/contrato iguais, diferença exata
de argv, fontes e proveniência. A gramática curta teve 19 sondas sem modelo;
a diferença de whitespace da serialização nativa está documentada no protocolo,
sem alegar equivalência completa ao parser.

Depois do ensaio, configuração/fontes seladas, 26 arquivos protegidos e oito
folhas conferem. Os dois arquivos de partições conferem por hash, sem leitura
semântica. Recibos VLM anteriores e ledger NIM aceito preservados. Zero aquisição,
remoto, treino, teste reservado aberto ou mudança no M1. Campos e candidatas
liberados continuam vazios; gates originais, auditoria independente e B/C
permanecem pendentes. Não há declaração de projeto concluído.

Plano: `22645d9440671b97273df9d59162f32776c02e7b07d98f37d569dc7a8c4dfd80`.
Configuração: `0d9d59a4855bdf6ff89c42be3e9e21a7bdb4cdefc8b2d14eae7dac92ac77b055`.

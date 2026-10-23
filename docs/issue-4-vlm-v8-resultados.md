# VLM v8: comparação concluída nos 64 casos revelados

Em 19/10/2026, a correção de instruções explícitas melhorou fortemente texto,
melhorou pessoa em um caso e piorou produto. **Nenhum campo atingiu a prontidão
definida para outra auditoria cega; nenhuma coluna foi liberada para treino.**
O teste reservado permaneceu fechado, M1 e partições 203/66/31 preservados.

## O que foi implementado e comparado

Seguindo o [protocolo congelado](issue-4-vlm-v8-desenvolvimento-protocolo.md),
a v8 faz uma pergunta por campo/frame com exemplos JSON literais true/false/unknown.
Pessoa explicita partes humanas; produto exige apresentação observável e
separa roupa incidental; texto pergunta presença de caracteres sem transcrição.
Parser estrito, rubrica e agregação v7 permanecem: presença por OR com todos os
frames positivos citados, ausência só quando todos os elegíveis são false,
produto apenas até 3 s. Ambiente, formato, close-up e aplicação ficam unknown.

Foram exatamente os mesmos **64 casos/56 canais de treino**, 32 antigos e 32
da auditoria v7 agora revelada, com 16 por setor em cada grupo. As 64 folhas e
256 crops reproduziram hashes, propriedades e tempos v7. Não houve reposição,
nova observação pública ou seleção de auditoria. Os nomes técnicos development
e audit indicam somente a origem: ambos são desenvolvimento nesta rodada.
As anotações assistidas anteriores ficaram imutáveis; não são certificação humana.

Houve uma única versão, congelada antes dos controles, sem retuning. Permaneceram
Qwen3-VL-2B Q4_K_M, projetor Q8_0, runtime b11716, CPU4, seed42, temperatura 0,
64 tokens de saída e limites visuais solicitados 64/128, sem medir tokens
visuais efetivos. Os PNGs RGB 320×330 mantêm o enquadramento/padding anterior;
não houve aumento de resolução, OCR ou serviço externo. Não entraram views,
títulos, ASR, rótulos preditivos, validação ou evidências/rótulos de teste.

A referência principal é **A/v7 em cache nos mesmos 64**. B/v7 é uma variante
de prompt em cache nos 32 antigos, distinta do modelo preditivo B-cache.
Não houve novas chamadas dos comparadores ou treino preditivo B-VLM.
Esta rodada compara o conjunto de perguntas separadas e instruções explícitas;
não isola o efeito de cada frase ou componente do prompt.

## Resultado nos 64

Acerto completo exige valor correto, pelo menos um frame citado e todos os
índices citados contidos nos frames da anotação. SS conta respostas conhecidas
com índices sem esse suporte; erro de valor é contado separadamente. K/U são
conhecidos/unknown. Os denominadores da tabela são sempre os mesmos 64 casos.

| Campo | K/U v7 | K/U v8 | Valor correto v7→v8 | Valor+frames v7→v8 | SS v7→v8 | Ganhos/perdas pareados |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Pessoa | 64/0 | 64/0 | 62→63 | 61→62 | 3→2 | 1/0 |
| Produto ≤3 s | 64/0 | 64/0 | 57→56 | 54→50 | 3→6 | 3/7 |
| Texto | 12/52 | 62/2 | 11→60 | 11→57 | 1→3 | 47/1 |

Texto saiu de zero previsões true em vídeo na v7 para 52 na v8: 50 verdadeiros
positivos e dois falsos positivos, além de dez verdadeiros negativos e duas
abstenções positivas. Entre 62 conhecidos, 60 acertaram o valor e 57 também
os frames. A cobertura cresceu, mas sobraram três respostas com índices sem
suporte, portanto a melhora não satisfaz o gate.

Pessoa corrigiu o caso revelado cuja presença aparecia somente no frame tardio.
Nos 32 antigos não melhorou o acerto completo: persistem um erro de valor e
uma resposta de valor correto com evidência excedente. Nos 32 revelados acertou
32/32 com evidência. Isso é desenvolvimento após diagnóstico desses casos.

Produto respondeu **true nos 64 casos**, inclusive nos oito negativos anotados.
Os três falsos negativos de valor da v7 desapareceram, mas os falsos positivos
subiram de quatro para oito, sem qualquer verdadeiro negativo na v8. Ganhos de
recall vieram com pior distinção entre presença/apresentação e ausência. Houve
seis respostas de valor correto que falharam na evidência, contra três na v7.
O ganho em texto não compensa essa regressão para aprovar o conjunto.

## Grupos e setores

Cada linha tem 16 casos. As células mostram **K/U; valor correto; valor+frames;
SS**, nessa ordem, para permitir ler cobertura, valor e suporte separadamente.

| Origem dos 32 | Setor | Campo | A/v7 | v8 |
| --- | --- | --- | ---: | ---: |
| Antigos | beleza | Pessoa | 16/0; 16; 15; 1 | 16/0; 16; 15; 1 |
| Antigos | beleza | Produto ≤3 s | 16/0; 15; 13; 2 | 16/0; 13; 10; 3 |
| Antigos | beleza | Texto | 1/15; 1; 1; 0 | 15/1; 14; 13; 1 |
| Antigos | moda | Pessoa | 16/0; 15; 15; 1 | 16/0; 15; 15; 1 |
| Antigos | moda | Produto ≤3 s | 16/0; 14; 14; 0 | 16/0; 16; 16; 0 |
| Antigos | moda | Texto | 4/12; 4; 4; 0 | 15/1; 15; 14; 1 |
| Revelados | beleza | Pessoa | 16/0; 16; 16; 0 | 16/0; 16; 16; 0 |
| Revelados | beleza | Produto ≤3 s | 16/0; 14; 13; 1 | 16/0; 13; 11; 2 |
| Revelados | beleza | Texto | 2/14; 2; 2; 0 | 16/0; 16; 15; 1 |
| Revelados | moda | Pessoa | 16/0; 15; 15; 1 | 16/0; 16; 16; 0 |
| Revelados | moda | Produto ≤3 s | 16/0; 14; 14; 0 | 16/0; 14; 13; 1 |
| Revelados | moda | Texto | 5/11; 4; 4; 1 | 16/0; 15; 15; 0 |

Nos 32 antigos, valor+frames passou de 62/96 para 83/96 pares caso/campo;
nos 32 revelados, de 64/96 para 86/96. São 169/192 contra 126/192 no total,
sem tratar os campos, frames ou casos do mesmo canal como observações independentes.
As evidências sem suporte aumentaram de sete para onze no total.

Para a referência adicional **B/v7 somente nos 32 antigos**, K/U, acerto de valor,
valor+frames e SS foram: pessoa 32/0, 30, 29, 2; produto 32/0, 29, 25, 4;
texto 0/32, 0, 0, 0. O total de acertos completos foi 54/96, contra A/v7 62/96
e v8 83/96 nesses mesmos 32. B/v7 não possui resultados nos outros 32.

## Classes e frames explicitamente anotados

| Campo | Anotações true/false | Previsões v8 true/false/unknown | VP / FN / FP / VN v8 | Unknown em positivos/negativos |
| --- | ---: | ---: | ---: | ---: |
| Pessoa | 60/4 | 59/5/0 | 59 / 1 / 0 / 4 | 0/0 |
| Produto ≤3 s | 56/8 | 64/0/0 | 56 / 0 / 8 / 0 | 0/0 |
| Texto | 52/12 | 52/10/2 | 50 / 0 / 2 / 10 | 2/0 |

As contagens abaixo usam somente frames explicitamente anotados como positivos
ou ausentes. Frames não citados não viram negativos. T/F/U são respostas por
frame; a quantidade varia por campo e não constitui novas observações independentes.

| Campo | Positivos anotados: T/F/U v7→v8 | Ausentes anotados: T/F/U v7→v8 |
| --- | ---: | ---: |
| Pessoa | 217/11/0→224/3/1 | 0/16/0→0/16/0 |
| Produto ≤3 s | 142/16/0→152/0/6 | 9/15/0→20/0/4 |
| Texto | 0/13/171→139/4/41 | 0/47/1→2/46/0 |

## Gate original preservado e decisão

O gate foi reaplicado a cada grupo de 32 apenas como diagnóstico de prontidão:
≥12 conhecidos/setor, ≥90% valor+frames entre conhecidos, zero SS, ≥3 previsões
de cada valor booleano no grupo e ≥1 de cada valor por setor. Prontidão exige
passar nos dois grupos; ainda assim este desenvolvimento não libera treino.

| Campo | Antigos | Revelados |
| --- | --- | --- |
| Pessoa | Falha: um SS em cada setor; beleza não tem previsão false | 32/32 completos, zero SS; falha apenas por duas previsões false, abaixo de três |
| Produto | Beleza 10/16 e três SS; nenhum false nos dois setores | Beleza 11/16 e moda 13/16; três SS; nenhum false |
| Texto | Beleza 13/15, abaixo de 90%; um SS em cada setor | 15/16 em cada setor; um SS em beleza |

Cada grupo tem só **30 true e dois false anotados de pessoa**. Um classificador
perfeito daria 30/2 e falharia no suporte mínimo de três previsões false, como
ocorreu nos revelados. Nos antigos, ambos os negativos são de moda e beleza
não tem negativo anotado. Essa insuficiência da amostra é separada dos erros
perceptivos. O gate não foi alterado; não foram introduzidos erros nem repostos
casos para passar.

`fields_ready_for_future_blind_audit=[]` e `released_fields=[]`. Ambiente e
formato também seguem retidos, sem tentar novas classes nesta correção.
Texto justifica manter a pergunta explícita como evidência de desenvolvimento;
produto impede recomendar a v8 inteira para nova auditoria. A ablação de
resolução nativa continua proposta separada, não executada nem selecionada
por estes resultados. Outra versão ou auditoria exige protocolo próprio;
os 64 casos/56 canais já revelados devem continuar excluídos de nova amostra cega.

## Controles, execução e preservação

Os [12 controles congelados](https://github.com/leeunam/case-GALAXIES-IA/blob/0df616e5fd64dfc4947abde583f2664b66abf410/docs/issue-4-vlm-v8-execucao.md) já haviam sinalizado
limitações: pessoa 12/12 somente negativos; produto 0/12, com cinco falsos positivos
e sete unknown; texto 5/12, com dois positivos grandes na parte superior e três
negativos corretos. Texto pequeno e texto grande inferior ficaram unknown.
Foram 36 chamadas válidas em 415,18 s. Não houve retuning após os controles,
que não certificam percepção geral nem equivalem a vídeos independentes.

As 64 reaquisições levaram 266,06 s, sem retry DNS, elevando o acumulado de
118 para 182 diante do teto 192. Todos os vídeos foram descartados nas sessões.
As 768 inferências reais levaram 6.171,53 s; com controles e aquisições, esta
etapa somou 6.852,77 s. O tempo contabilizado cumulativo foi **15.159,68 s
(4,211 h)** diante de 27 h; não é medição de toda a duração de parede do trabalho.
As **804 chamadas novas** se somam às 649 de v7+diagnóstico, totalizando 1.453
nesse contador. Não se afirma que esse contador inclui todas as chamadas v6.
Máximo por chamada: **16,98 s e 2.603,02 MiB de RSS do processo filho**, abaixo
de 180 s e 3,3 GiB. Zero falhas operacionais ou repetições de inferência.

A revisão independente somente leitura reconstruiu respostas, agregações,
métricas e gates, conferiu caches/pareamento, anotações, orçamento e hashes.
Após a comparação selada e a revisão, as **64 folhas foram removidas**, com
jornal de descarte preservado e zero sessões temporárias restantes. A etapa
selada recusou aquisição, inferência real e controles antes de qualquer
download/chamada nativa, sem mudar o checkpoint. Compare/dispose retornam
recibos existentes de forma idempotente. Os 99 arquivos protegidos permaneceram
idênticos; as fontes/prompts/protocolo também conferem com o plano congelado.

Passaram **567 testes completos** em 403,53 s, 58 direcionados, Ruff e formatação
dos 103 arquivos; a versão testada é a mesma congelada antes das chamadas.
Não houve alterações posteriores de código, integração serviço/MCP, promoção
de modelo, treino B-VLM, avaliação de validação ou abertura do teste reservado.

## Recibos e commits

Os recibos privados estão em `data/private/issue-4-vlm-v8-desenvolvimento-64/`:
plano, checkpoint, 64 identidades/sessões/resultados, 12 controles, 804 chamadas
brutas, comparação, análise pareada, verificação de runtime, revisão e descarte.
Não foram versionados dados privados, modelos, mídia ou temporários.

- Plano lógico: `11f70036a059979a94eba997a4de4816df25bea28e25db33b63dcd05cb0f9c7d`.
- Comparação lógica: `c80bcdbb47e0106371e1fad64e58c73b53423a16ac98851c13e6754bc4acf9e0`.
- Arquivo da comparação: `2320e40646183d179f0511654c3560d4324c702d5500b9b9c6993f5b3cbaa6cb`.
- Arquivo do recibo final: `c4442234cf5c309a78065a5c893195c1a6a4436fd1236709d52b1a620cdcbfe2`.
- Commits verificados: `e3fbc65` protocolo; `c99eae8` extrator/testes;
  `e923bdb` fluxo/comparação/testes; `6dcb42e` controles/pareamento.

O recibo final fixa os hashes dos arquivos protegidos, fontes, testes e evidências
locais. A implementação está em [extrator](../scripts/vlm_explicit_presence.py),
[plano](../scripts/vlm_prompt_plan.py) e [fluxo](../scripts/vlm_prompt_development.py),
com testes de isolamento, identidade antes/depois das chamadas, falha sem retry,
orçamento, comparação e recuperação de descarte interrompido.

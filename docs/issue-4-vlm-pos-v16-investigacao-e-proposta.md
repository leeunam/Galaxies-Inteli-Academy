# Pós-v16: evidência da ordem e contraste positivo proposto

Investigação offline em 20/10/2026, sobre o HEAD integrado `3ce5af1`.
Não houve geração, aquisição, chamada NIM, treino ou nova auditoria nesta análise.
O replay aditivo está em `scripts/diagnose_vlm_v16.py`; os recibos privados
ficam em `data/private/issue-4-vlm-pos-v16-diagnostico-v1/`.

## O que os recibos permitem afirmar

O replay dos 24 raws reproduziu os [resultados selados da v16](issue-4-vlm-v16-resultados.md):

| Ordem | true | false | unknown | Acertos negativos |
|---|---:|---:|---:|---:|
| item_first | 12 | 0 | 0 | 0/12 |
| state_first | 0 | 11 | 1 | 11/12 |

São 12 pares com pixels e tempos iguais, 11 ganhos e zero perdas de
`state_first` nos negativos. Nenhum positivo foi executado. O `unknown` de
`lines` já consta no raw como `state=uncertain`, `item_configuration=unclear`
e categorias vazias. A projeção, o parser, o OR temporal e a serialização dos
recibos não introduziram essa abstenção. Nenhum braço passou o gate de 12/12.
As dez chamadas não usadas da v16 estão encerradas, sem saldo reutilizável.

**Errata aditiva:** a descrição anterior de tempo zero no protocolo v16 é
imprecisa. Os 12 controles usaram **0,2 s** nos dois braços, conforme seus
casos e resultados congelados. O replay verifica o tempo do caso original;
não o substitui. Todos continuam elegíveis no intervalo ≤3 s, sem efeito na
comparação ou explicação para a abstenção.

`lines` contém 13 linhas horizontais pretas de dois pixels, de x=12 a x=308,
em fundo branco RGB 320×330; são 7.722 pixels pretos e 97.878 brancos. Uma
reconstrução temporária da receita existente reproduziu seu hash congelado
e foi removida. Não criou caso ou anotação novos. Não há produto no controle;
supor que o modelo confundiu as linhas com tecido continua sendo hipótese.
Os raws não contêm logits, atenção ou justificativas para sustentá-la.

## Hipótese que ainda pode ser discriminada

O conjunto permitido contém os mesmos 22 objetos completos, com o mesmo
prompt neutro, categorias, ordem dos ramos, arrays `required`, projeção e
runtime. A primeira escolha serializada muda: dez configurações em
`item_first`, quatro estados em `state_first`. As continuações completas
por estado são 1 `no_target`, 1 `incidental_only`, 19 `presented_target` e
1 `uncertain`. Esses números descrevem a gramática finita; não são
probabilidades uniformes, logits ou ordem de raciocínio.

A ordem pode alterar o condicionamento dos tokens seguintes e reduzir a
tendência a produzir configuração positiva. Ainda não sabemos se essa
redução conserva a sensibilidade a produtos apresentados. Tampouco podemos
atribuir à ordem a diferença histórica v14→v15: a v16 isola a serialização
sob um prompt comum. Os seis `incidental_only` de controles negativos não
constituem novas anotações finas certificadas.

As provas nativas já existentes aceitam os mesmos 22 objetos e rejeitam as
22 serializações opostas por braço, em 13.703 sondas por ordem. As 88
serializações tokenizadas cabem no limite de 64 tokens, incluindo término.
Os 24 raws concluíram sem truncamento ou falha operacional; maior duração
22,69 s e pico de RSS 2.611,96 MiB. Não há falha de infraestrutura observada
que explique `lines`. O reuso dessas provas exige identidade exata de
fontes, schema ordenado, gramática, runtime e recibos; não nova geração.

## Próximo contraste delimitado

Cinco chamadas apenas com `state_first` mediriam sua resposta aos positivos,
mas não a eventual perda pareada. Alterar o prompt agora misturaria essa
pergunta com outra intervenção e poderia ensinar o controle conhecido.
A proposta adotada pelo principal e supervisor é um **diagnóstico positivo
pareado separado**, com os cinco crops já congelados em v16, nos dois braços
inalterados: **dez chamadas novas, zero aquisições, até 400 s de sessões**.

São cinco crops conhecidos de três vídeos de moda, todos de treino, com
tempos 0,2/1,5/2,8 s e os mesmos pixels, anotações e alternativas admissíveis
já selados. O primeiro braço alterna por crop: I/S, S/I, I/S, S/I, I/S.
Sem seleção adicional, correção de rótulo, mudança de prompt, resolução,
categoria, gramática, modelo ou parâmetros. CPU=4, 180 s por chamada e
RSS≤3,3 GiB. A autorização desse diagnóstico é nova e separada do orçamento
encerrado da v16. O histórico continua em 1.835 reservas, 256 aquisições e
37.568,24201608001 s, incluindo a reserva incerta histórica, sem desconto.

O diagnóstico completa as dez respostas apesar de erros perceptivos.
Falha operacional, de JSON/ordem, identidade ou limite encerra a fila sem
retry; cancelamento/reserva incerta impede reentrada. Cada despacho exige
reserva durável, e a execução real exige revisão técnica do plano/configuração
concretos. Até essa revisão a fila fica em zero operações.

Registrar por braço `true`/`false`/`unknown` e, separadamente, **true com
suporte**: categoria exatamente `garment` e configuração na lista admissível
original daquele crop. Um true sem suporte refuta uma constante mecânica
não positiva, mas não demonstra percepção correta. Ganhos/perdas usam o
acerto com suporte nos mesmos pares completos, com denominadores explícitos.
Uma parada parcial não pode ser apresentada como cinco pares avaliados.

Esse diagnóstico nunca aprova candidata ou coluna. Os gates de 12/12
negativos e 5/5 positivos continuam intactos, a v16 continua reprovada, e
mesmo dez acertos novos não a completam retroativamente. Auditoria cega,
treino B/C, promoção de M1 ou rodada automática seguinte ficam fora do escopo.
Partições 203/66/31, teste reservado, M1/A200 e integrações existentes
permanecem preservados.

## Verificação da unidade offline

Os dez testes sintéticos do replay verificam reconstrução somente leitura,
ausência de processo/rede/modelo e rejeição de alterações em raw, projeção,
tempo, pixels, ordem, fonte, selo ou número de operações. Ruff e formatação
foram conferidos. A prova inicial protege 9.974 arquivos e preserva os
9.944 pins herdados. Nenhum recibo antigo foi reescrito; a errata acima é aditiva.

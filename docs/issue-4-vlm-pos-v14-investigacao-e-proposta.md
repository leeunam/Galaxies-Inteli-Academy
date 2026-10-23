# Pós-v14 — held_display sem relação visível com o item

Investigação de 20/10/2026, restrita aos controles e oito vídeos de treino já
revelados. **Held_display já estava nos raws: 16 declarações, cinco suportadas
e 11 sem suporte na revisão assistida.** O erro observado é de vínculo entre
item e relação de apresentação. Não nasceu no parser, OR ou janela temporal;
o mecanismo interno que levou o modelo a escolher a pista não foi isolado.

Recomendação: uma **v15 que declare uma configuração visível do item e derive
a pista por código**, distinguindo item na mão, cabide segurado, tecido puxado,
item isolado e recorte gráfico. A configuração continuará sendo afirmação do
mesmo VLM, sujeita a alucinação. Propor primeiro um bloco limitado de controles
e folhas preservadas, sem aquisição ou nova auditoria. Este documento não
implementa extrator/fila nem executa inferências. A
[v14 reprovada](https://github.com/leeunam/case-GALAXIES-IA/blob/0df616e5fd64dfc4947abde583f2664b66abf410/docs/issue-4-vlm-v14-resultados.md) permanece selada, sem alterar
o [protocolo executado](issue-4-vlm-v14-protocolo.md).

## Reconstrução dos erros

Os 44 raws foram reconferidos com hashes, especificação, decoder e bindings de
PNG/tempo. As 16 declarações held aparecem em seis vídeos. Todas são objetos
formalmente válidos, com uma categoria. Das 12 declarações held precoces, cinco
têm suporte e sete não; as quatro tardias não têm suporte. Portanto excluir
frames tardios não resolve o problema. A métrica antiga de pertinência dos
índices ao GT também não verifica a nova relação visual declarada.

| Situação nos casos revelados | Declarações held | Suportadas | Sem suporte |
| --- | ---: | ---: | ---: |
| Cabide segurado exibindo a própria peça | 4 | 4 | 0 |
| Barra do vestido segurada para fora | 1 | 1 | 0 |
| Recortes de roupas, com outro item na mão | 3 | 0 | 3 |
| Bolsa segurada, pista atribuída ao vestido | 2 | 0 | 2 |
| Pincel classificado como cosmetic | 1 | 0 | 1 |
| Pose/roupa vestida, sem exibição segurada da peça | 3 | 0 | 3 |
| Acessório vestido ou sem item exibido identificável | 2 | 0 | 2 |
| **Total** | **16** | **5** | **11** |

Nos recortes sobrepostos, o item garment não é o pincel que a mão segura. No
vestido verde, segurar a bolsa não torna o vestido held. Mãos junto ao pescoço,
joia vestida e pose lateral tampouco estabelecem item segurado para exibição.
O cosmetic do pincel também falha na identidade/categoria do alvo. Já quatro
cabides e uma barra puxada mostram uma ligação concreta entre mão e peça.
Essas diferenças são observações dos pixels, sem atribuir ao modelo uma cadeia
de raciocínio ou intenção que não foi registrada.

Os demais 14 positivos são worn_detail_focus: seis suportados, três sem suporte
e cinco ambíguos. A correção de held não bastará se esses erros persistirem.
Os dois incidentais não foram convertidos em positivos. A revisão original dos
30 positivos, o GT e todas as métricas permanecem iguais; esta análise apenas
agrupa os registros existentes, com nova descrição diagnóstica vinculada.

Na interseção dos quatro vídeos completos da v13-R, com os mesmos 16 crops,
as declarações held passaram de **quatro para seis**. As seis atuais não têm
suporte. A redução de cosmetic 12→1 nessa interseção não eliminou o problema
relacional. Prompt e cardinalidade mudaram juntos; a comparação não identifica
qual alteração causou esse comportamento. Os três raws parciais do quinto
vídeo v13 não são usados como comparação completa.

## Contrato, hipótese e limites causais

O prompt v14 já manda usar evidência do mesmo item, não transferir pista,
distinguir pincel de cosmético e não tomar mera sustentação de objeto como
apresentação. A definição herdada é explícita:

> held_display = held out to display, including fabric pulled out to show a worn garment; merely holding an object is insufficient.

Não houve inversão dessa regra no código. O schema/decoder verificam estado,
categoria única e pista compatíveis, mas só recebem três declarações:
`state`, `presented_categories`, `presentation_cue`. Não registram **qual
configuração visível liga a mão ao item selecionado**. Garment identifica uma
classe, não distingue a roupa vestida, a peça sobreposta e a peça no cabide.
Selecionar só uma categoria removeu listas extras, sem resolver essa referência.

O recibo nativo v14 já aceita garment com held, isolated, use e worn (sondas
98/99/100/101). A releitura das transcrições e a verificação pura do recibo
confirmaram alternativas disponíveis, sem recompilar ou gerar. **Held não era
obrigatório pela gramática.** A primeira pista positiva na prosa/ordem de ramos
continua sendo held, mas isso não demonstra viés causal de ordem ou token.

| Hipótese | Evidência e limite |
| --- | --- |
| Coocorrência de pessoa/mãos/roupa substituindo a relação do mesmo item | Compatível com poses, mãos no pescoço e bolsa junto ao vestido; a relação efetivamente declarada não está nos pixels. Não identifica o cálculo interno do modelo. |
| Transferência entre objetos ou camadas da imagem | Os raws e a inspeção mostram garment held onde só outro item está na mão ou a peça é recorte isolado. O rótulo não distingue esses suportes. |
| Held como opção padrão após detectar um alvo | Compatível com 16 held, zero isolated/use e 30/32 frames positivos; não demonstrado sem contraste controlado ou logits. |
| Parser, agregação ou frame tardio introduziram held | Refutada pelos raws preservados e por sete erros precoces. |
| Quantização, resolução, capacidade visual ou ordem do enum causaram o erro | Não medido. Não há logits, atenção, máscaras por token ou ablação controlada que isole essas causas. |

As contagens são deste painel selecionado, positivo, de moda e já revelado.
Não estimam precisão populacional ou especificidade. Coerência gramatical e
uma explicação produzida pelo próprio modelo não são comprovação visual.

## Próxima correção recomendada

| Alternativa | Benefício | Limite / decisão |
| --- | --- | --- |
| Mais negativas no prompt, mantendo a saída v14 | Baixo custo e contrato igual | A v14 já proíbe transferir relações; o rótulo continuaria ocultando o suporte escolhido. Não recomendada isoladamente. |
| **Declarar configuração e projetar a pista por código** | Torna auditável se o modelo afirmou mão no item, cabide, tecido afastado ou item isolado; separa esses casos em ramos fechados | Recomendada como uma hipótese de desenvolvimento, sem garantia de percepção. |
| Segundo verificador ou outro VLM | Pode contrastar reconhecimento da relação | Outra chamada do mesmo modelo pode repetir o erro; outro modelo exige custo, runtime e validação próprios. Não ampliar agora. |

O rascunho nativo tem três campos, na ordem **item_configuration, state,
presented_categories**, com 10 ramos fechados. Não pede presentation_cue:

| Configuração declarada | Estado/categorias | Pista derivada |
| --- | --- | --- |
| absent | no_target /[] | absent |
| incidental | incidental_only /[] | incidental |
| hand_holds_item_out | presented_target /um dos quatro singletons | held_display |
| hand_holds_hanger_out | presented_target /[garment] | held_display |
| hand_pulls_worn_fabric_out | presented_target /[garment] | held_display |
| isolated_physical_item | presented_target /um dos quatro singletons | isolated_display |
| isolated_graphic_item | presented_target /um dos quatro singletons | isolated_display |
| explicit_item_use | presented_target /um dos quatro singletons | visible_use |
| framed_garment_detail | presented_target /[garment] | worn_detail_focus |
| unclear | uncertain /[] | uncertain |

São **22 objetos nativos: 19 positivos e três restantes**. Todas as quatro
categorias continuam disponíveis, sem filtro por setor. O texto deve exigir
ligação visível mão–mesmo item e configuração de exibição; mão próxima, outra
coisa na mão e recorte apenas do item não bastam. Cabide precisa de ligação
com a mão e a própria peça; tecido vestido precisa estar segurado afastado do
corpo. Não inferir movimento ou proveniência real/sintética da imagem. Uma
relação representada dentro de uma imagem deve concernir ao mesmo item ali
representado, sem importar a mão de outra camada.

Recortes isolados podem sustentar isolated_graphic_item; não recebem held
emprestado da apresentadora. Pincel continua applicator, não cosmetic. Manter
os critérios de uso explícito, detalhe de roupa, incidentalidade e incerteza.
Sem relação confirmada, declarar unclear quando a apresentação for ambígua,
em vez de inventar testemunha ou forçar ausência. Um item confirmado pode
vencer outros incidentais/ambíguos; não inventariar todos os itens.

A projeção deve preservar a categoria declarada e mapear configuração para
pista/estado/booleano de forma fixa. **A pista passará a ser derivada**, com
essa origem explícita na evidência versionada; não será outra observação do
VLM nem validação independente. Guardar raw nativo e configuração antes de
validar/projetar. Não converter antigos raws, inferir sua configuração pelos
pixels/GT ou reparar cosmetic para applicator por código.

A ordem serializada da configuração não prova uma ordem de raciocínio visual.
O modelo ainda pode declarar hand_holds_item_out sem suporte: se apenas trocar
o nome da alucinação, a correção falhou. Revisar a ligação e a exibição nos
pixels, não aceitar o nome mais descritivo como prova. Manter os cinco exemplos
de held suportado como controles positivos da relação, sem exigir esse nome
quando outra configuração do mesmo item também for defensável. Não excluir
held do contrato nem suprimi-lo automaticamente para passar.

## Rascunho verificado offline, sem runtime ou avaliação novos

Com `jsonschema` 4.26.0 instalado, enumeramos 10 configurações × 4 estados × 341
arrays de tamanho 0–4 sobre quatro categorias: **13.640 objetos**. O schema
aceita exatamente 22, sem divergência com a tabela. As projeções chegam aos
**16 objetos semânticos v14**, todos aceitos pelo decoder atual e com o mesmo
mapeamento booleano/unknown. Isso demonstra cobertura formal, não equivalência
perceptiva entre as instruções ou respostas futuras.

Quinze mutações de campos/tipos/categorias/compatibilidade foram recusadas.
Nenhum dos 44 raws v14 é aceito como novo raw: falta a configuração, que não
pode ser preenchida retroativamente. O rascunho não é decoder/extrator de
produção. Sua gramática nativa e limite de 64 tokens **ainda não foram
verificados**. Nenhuma inferência, compilação ou tokenização nova nesta análise.

## Ambiguidade existente e execução futura proposta

As duas blusas têm GT legado true, frames 1/2/3. Na inspeção congelada, seus
primeiros frames permanecem ambíguos quanto a detalhe, e o look/arara dos
frames seguintes não estabelece apresentação sozinho. **Não há true precoce
confirmado nessa inspeção para garantir recuperação desses dois vídeos.**
Isso não prova ausência física de apresentação nem cria nova anotação
certificada; mostra uma tensão que o acerto agregado não resolve.

Abster-se de uma apresentação ambígua pode contrariar o GT legado. Não forçar
held/worn para obter 8/8, promover a ambiguidade pelo raw ou reescrever GT,
índices, inspeção ou limiar. Os 8/8 antigos continuam reportados com sua
definição original; o gate de suporte continua exigindo todas as declarações
positivas suportadas. Se a tensão permanecer, registrar bloqueio científico,
sem declarar aprovação por melhora parcial ou mudar o protocolo após o resultado.

Propor uma **v15 aditiva, um candidato, inicialmente só 44 chamadas/zero
aquisição/1.200 s de sessões**, com pré-verificação e avanço condicional:

1. Antes de gerar: conferir rascunho, fontes e projeção; validar gramática no
   b11716 instalado sem modelo, cobrindo 22 válidos, domínio finito, whitespace
   e mutações brutas. Verificar tokenização/limite 64, chaves duplicadas e tipos
   no decoder estrito. Qualquer divergência impede despacho. Não instalar ou
   trocar pesos/runtime. Commitar código/testes/protocolo verificados.
2. Até 12 chamadas nos mesmos controles, exigindo 12/12 false; só se passar,
   até 32 chamadas nos quatro crops das oito folhas preservadas. Sem retuning,
   novos exemplos no prompt, substituição de caso, retry ou aquisição.
3. Relatar valor+frames contra o GT imutável e revisar todas as configurações
   positivas, inclusive tardias, com vínculo ao crop/tempo e inspeção congelada.
   Avaliar se os erros atuais deixaram de receber held falso, sem aceitar uma
   configuração alternativa igualmente sem suporte. Ambiguidades permanecem
   desconhecidas. False/unknown no suporte sela; ausência de recibo mantém pausa.

Manter mapper temporal, OR, produto ≤3 s e pessoa/texto em cache. Falha de
operação, identidade ou JSON interrompe imediatamente; falha perceptiva conclui
o bloco e sela. Um executor, locks, reserva durável, 180 s/operação, RSS 3,3 GiB
e cobrança conservadora de tentativa incerta, sem reabrir saldos antigos.
Base selada **1.799 /256 /36.786,75786307302 s**; tetos novos propostos
**1.843 /256 /37.986,75786307302 s**. Nenhum orçamento novo consumido aqui.

Essa primeira rodada encerra no diagnóstico/revisão das oito folhas, mesmo
se melhorar. Não inclui as 12 reaquisições da fase 2 antiga: nova etapa exigirá
protocolo próprio para completar negativos reais/beleza e resolver eventuais
incompatibilidades documentadas sem falsificar anotações. Não antecipar outra
auditoria cega por acertos nesses casos revelados. Manter o
[gate original](issue-4-vlm-revisao-perceptiva-protocolo.md), exclusão de casos/
canais revelados e suficiência de classes antes de qualquer auditoria nova.

## Preservação e evidências desta investigação

Os **1.262 arquivos protegidos** conferem antes/depois, incluindo fila v14,
seus raws/recibos, fontes, evidências anteriores e bundles M1/A200, A300 e
B-cache. Plano/configuração, checkpoint selado e comparação continuam iguais.
Oito PNGs originais presentes; 32 crops reproduzidos em memória com hashes e
tempos idênticos. Nenhuma imagem removida, movida, alterada ou adquirida.

Partições 203/66/31 preservadas sob guardas 200/300, teste reservado fechado,
sem abrir suas features/rótulos/previsões/métricas. M1 e modelos nativos iguais.
Ambientes raiz 130/isolado 42 distribuições iguais e runtime/pesos conferidos em
leitura. Zero inferências, aquisições ou sessões novas de mídia; nenhum worker
ou sessão temporária detectado. Contadores permanecem 1.799/256 e
36.786,75786307302 s. Sem instalação, acesso externo, B/C ou auditoria nova.

Apenas este relatório é versionado. Verificação por replay, enumeração,
projeções/sondas, identidade de pixels/tempos, pins, ambientes, links e revisão
local do diff. Nenhum código de produção mudou; não houve nova suíte, e os
1.115 testes anteriores não são apresentados como execução desta investigação.
README não rastreado fora do escopo, sem leitura, edição ou staging.
Recibos/rascunhos privados em
`data/private/issue-4-vlm-v14-held-diagnostico-v1/`.

- Prompt proposto: `5896b5bf3c9e053c09da1179e11737e0d5b782b524cd179346a94bece1d23d36`.
- Schema proposto: `1ee90e85d7204bbf21c86c7146852fb84fc433e26cc41a7949a90660cf54bfd3`.
- Projeção proposta: `958f8d2f25e00d581f3d8bcc80278d78fabd10b6595124451b59c1c2f525adf0`.

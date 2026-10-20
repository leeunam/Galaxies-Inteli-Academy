# Produto v14 — contrato validado, pistas ainda reprovadas

Execução de 20/10/2026 do [protocolo v14](issue-4-vlm-v14-protocolo.md),
aprovado após a [investigação de cosmetic na v13-R](issue-4-vlm-pos-v13-investigacao-e-proposta.md).
A gramática passou no runtime instalado. A v14 acertou **12/12 controles** e
**8/8 valores+frames** dos vídeos preservados, mas falhou no suporte visual:
dos **30 objetos positivos**, 11 foram suportados, 14 ficaram sem suporte e
cinco permaneceram ambíguos na revisão assistida.

Fila selada em **`v14_phase1_cue_quality_failed`**, com **44 chamadas válidas e
zero aquisições**. A fase 2 não começou. Nenhuma coluna liberada, nova auditoria
cega, treino B/C ou promoção do M1. A redução de categorias extras não resolveu
a atribuição de pistas a itens distintos ou apenas vestidos.

## Implementação e verificações antes da geração

- `c713f4a`: extrator de um item, decoder estrito, gramática/gate nativos,
  testes e protocolo.
- `38d7575`: fila separada, linhagem preservada, reservas duráveis, comparações
  por interseção e revisão de suporte vinculada aos resultados.

O prompt e schema correspondem integralmente ao rascunho aprovado. Os sete
ramos permitem 16 objetos semânticos, dos quais 13 positivos. Positivos têm
exatamente uma categoria e uma pista desse item; worn admite somente garment.
As quatro categorias continuam disponíveis nos demais ramos positivos, sem
filtro por setor. A lista agora testemunha um item, sem inventário completo.
Não houve corte/reparo de listas antigas nem derivação de pistas. Mapper,
unknown, OR, janela ≤3 s, GT e entradas permanecem iguais.

Passaram **94 testes direcionados**: 53 de contrato/recibos em 5,62 s e 41 de
fila em 24,64 s. A suíte completa única no código final `38d7575` passou em
**1.115 testes/660,63 s**, antes da primeira inferência. Ruff passou; os 188
arquivos Python rastreados estão formatados. A checagem ampla de formatação
também apontou um snippet preexistente em
[documento histórico](issue-2-baseline-observado.md); ele não foi alterado.
Não se apresenta essa checagem ampla como aprovada.

Revisão local das diferenças em relação aos módulos congelados, bindings,
limites e fases; sem alegar revisão independente. Nenhum código mudou após
a suíte. Preparar o plano durante a suíte não despachou chamadas: o contador
continuou zero até o registro da aprovação completa.

## Gramática e limite de saída

Ponte C++ v13 imutável, compilada somente como ponte contra as bibliotecas
b11716 instaladas. Os nove cabeçalhos oficiais já estavam em cache e foram
conferidos por hash; nenhum download, instalação ou troca de runtime/pesos.
Conversor `json_schema_to_grammar(..., false)` e aceitação por caracteres com
término completo, sem modelo ou forward pass nessa pré-verificação.

**9.589 sondas, zero divergências**: 9.548 objetos do domínio finito, 16
variações de whitespace entre campos e 25 mutações brutas. Os 16 válidos foram
aceitos; multicategoria, duplicatas, worn/cosmetic, incompatibilidade de
estado/pista, conteúdo extra, prefixo incompleto e outras mutações foram
recusados. A gramática fixa a ordem das chaves; o decoder semântico aceita
outras ordens. Isso verifica o contrato, sem certificar a percepção.

O recibo final vincula schema, fontes, bibliotecas, cabeçalhos, compilador,
ponte, gramática e transcrições; sua integridade foi verificada nas reservas
e depois do encerramento. Uma pré-verificação anterior ficou invalidada pela
organização de imports; a execução usou exclusivamente o recibo final de
`native-preflight-final-v2`, reconstruído antes das chamadas.

O tokenizador local em modo offline, sem geração, conferiu os 16 objetos em
serializações compacta e indentada: **32 exemplos de 18–37 tokens JSON**, com
espaço para um token final dentro de 64. Whitespace arbitrário não tem garantia
de caber; truncamento continuaria falha terminal, sem ampliar limite ou retry.
Na avaliação, os 44 raws foram aceitos integralmente sem reparo.

## Controles idênticos

| Versão / mesmos 12 controles | false correto | true | unknown |
| --- | ---: | ---: | ---: |
| **v14** | **12/12** | **0** | **0** |
| v13-R em cache | 12/12 | 0 | 0 |
| v11 em cache | 1/12 | 11 | 0 |

Frente à v13-R, zero ganhos/perdas nos 12 pares; frente à v11, 11/0. V12 tem
zero resultados aceitos e não entra como taxa de acerto. A v14 produziu dez
`incidental_only` e dois `no_target`, todos com lista vazia. O gate exige
false e não certifica essa distinção fina. Controles sintéticos não estimam
especificidade em vídeos reais.

## Oito vídeos completos e comparação limitada

O painel contém oito positivos de moda, em cinco canais já revelados.
Não há negativos reais ou beleza nesta fase. Os acertos seguem a regra
congelada: valor correto e índices citados não vazios dentro dos índices do GT;
não é necessário citar todos os frames positivos anotados.

| Versão / mesmos 8 vídeos | Valores+frames corretos | Ganhos/perdas da v14 |
| --- | ---: | ---: |
| **v14** | **8/8** | — |
| v10 em cache | 5/8 | 3/0 |
| v9 em cache | 3/8 | 5/0 |
| v8 em cache | 8/8 | 0/0 |
| A/v7 em cache | 8/8 | 0/0 |
| B/v7 antigo32 em cache | 8/8 | 0/0 |

V13-R só tem quatro vídeos completos: **4/4 contra 4/4 da v14 na mesma
interseção**, zero ganhos/perdas. Seus três raws parciais do quinto não foram
agregados ou usados como baseline de vídeo. V11/v12 não têm vídeos completos.
O quinto foi executado como caso da fila v14, sem retomar ou concluir a
tentativa incerta antiga. Todos os comparadores têm pixels/tempos idênticos.
Pessoa/texto foram preservados do cache, substituindo somente produto.

Nos 32 frames novos houve **30 presented_target e dois incidental_only**, sem
unknown; nos 24 precoces foram 22 apresentados e dois incidentais. Pistas:
**16 held_display e 14 worn_detail_focus**; nenhuma isolated_display/visible_use.
Categorias: **27 garment, uma cosmetic e duas accessory**; nenhum applicator.
Todos os positivos têm uma categoria, conforme o novo contrato.

Nos mesmos 16 frames dos quatro vídeos comparáveis à v13-R, cosmetic caiu de
**12 para 1**, e accessory de 7 para 0; a quantidade de positivos passou de 12
para 15. As listas antigas eram multicategoria e agora testemunham um item;
a redução não deve ser interpretada como precisão de inventário ou efeito
isolado de uma frase. Prompt e cardinalidade mudaram juntos. O cosmetic
remanescente aparece no frame do pincel, sem produto cosmético apresentado.

## Revisão formal de todas as pistas positivas

Após o bloco completo e antes de qualquer aquisição, o executor pausou para
revisão. Recibo exclusivo, vinculado aos 30 objetos por plano, resultado, hash
do crop, tempo, categoria, pista e inspeção congelada anterior à v11.
Revisão assistida após revelação, sem independência ou certificação humana.

| Caso revelado | Suportados | Sem suporte | Ambíguos | Achado principal |
| --- | ---: | ---: | ---: | --- |
| Blusa branca com babado | 0 | 2 | 2 | Foco em detalhe continua ambíguo; poses não demonstram garment held_display. |
| Camisa listrada | 1 | 2 | 0 | Close lateral sustenta detalhe; corpo inteiro/padrão sozinho não basta. |
| Recortes de roupas e pincel | 0 | 4 | 0 | Roupas sobrepostas são itens isolados, não segurados; pincel não demonstra cosmetic. |
| Saia com laço/fenda | 4 | 0 | 0 | Detalhes da própria peça identificáveis; cosmetic extra desapareceu. |
| Calças em cabide | 3 | 1 | 0 | Três exibições claras da peça; joia vestida no frame tardio não é accessory held_display. |
| Vestido verde | 2 | 2 | 0 | Barra puxada e detalhe lateral têm suporte; segurar bolsa não transfere held_display ao vestido. |
| Peça xadrez | 1 | 1 | 1 | Mão/cabide sustenta peça; mãos no pescoço não certificam acessório apresentado; detalhe no espelho permanece ambíguo. |
| Blusa branca com shorts | 0 | 2 | 2 | Ambiguidades anteriores preservadas; look/arara e mera pose não sustentam as pistas declaradas. |
| **Total** | **11** | **14** | **5** | **Gate reprovado** |

Há três declarações de cosmetic/accessory sem apresentação confirmada e
outros erros de pista, mesmo com garment visível. A categoria isolada não
impediu transferir held_display entre itens ou confundir roupa vestida com
detalhe apresentado. As ambiguidades antigas não foram promovidas pelo raw.

O acerto de valor+frames e o campo `unsupported_evidence=0` da métrica antiga
verificam pertinência dos índices ao GT congelado. **Não verificam a nova
categoria/pista atribuída a cada crop.** Por isso 8/8 não contradiz a reprovação
de suporte; nenhum valor/índice do GT foi reescrito para acomodar os resultados.
False ou unknown na revisão bloqueia aquisição, conforme o protocolo.

O recibo foi publicado com fase1=false. A reentrada prevista após a pausa
encerrou antes da primeira aquisição, sem reservar outra chamada. Estado e
comparação foram selados; fase2/prontidão nos 20 não foram medidas. O guard
terminal recusou retomada sem modificar o checkpoint.

## Consumo, descarte e preservação

| Contador | Novo | Cumulativo | Teto desta autorização |
| --- | ---: | ---: | ---: |
| Reservas nativas | **44**, todas com raw válido | **1.799** | 1.847 |
| Aquisições | **0** | **256** | 268 |
| Sessões cobradas | **627,1483 s** | **36.786,7579 s** | 38.559,6096 s |

Zero falhas operacionais, retry, reparos ou tentativas novas incertas. As 44
chamadas somam 614,7680 s de runtime nativo, máximo 17,2889 s; pico RSS 2.610,85 MiB,
abaixo de 3,3 GiB. Manter consumida a reserva incerta v13 e seus 180 s; ela não
foi repetida nem teve uma resposta preenchida. O saldo de 48 chamadas e 12
aquisições desta fila ficou encerrado. Suíte/pré-verificações sem geração não
contam como chamadas nativas.

Não houve mídia/folha nova. Journal de descarte vazio e concluído; crops/schema
temporários das chamadas foram removidos. As oito folhas antigas continuam
presentes, sem remoção, movimento ou edição. Nenhum worker ou sessão temporária
de mídia detectado ao terminar.

Conferem **1.108 arquivos herdados, 1.109 pins do plano e dez fontes**. Os 32
crops foram reproduzidos em memória antes/depois, com hashes e tempos iguais;
doze fixtures também foram regeneradas e conferidas antes da geração.
Ambientes raiz 130/isolado 42 distribuições iguais, sem instalação. Runtime e
pesos reconferidos em leitura contra o arquivo oficial em cache.

Partições **203 treino/66 validação/31 teste** preservadas sob guardas 200/300,
sem abrir features, rótulos, previsões ou métricas do teste. M1/A200 e seus três
modelos, A300, B-cache, serviço Python/MCP e filas anteriores intactos. README
não rastreado não foi editado ou incluído no commit. Não houve acesso externo
ou envio de mídia/dados privados; inferências exclusivamente locais.

A v14 permanece reprovada para outra auditoria cega. A aprovação do contrato
e os acertos deste painel revelado não liberam produto nem autorizam treino.
Nova correção exige investigação/proposta próprias; outra auditoria mantém
o [gate original](issue-4-vlm-revisao-perceptiva-protocolo.md), com protocolo
próprio e exclusão dos casos/canais revelados.

Recibos privados em `data/private/issue-4-vlm-v14-v1/` e
`data/private/issue-4-vlm-v14-verificacao-v1/`: baseline protegido, paridade do
rascunho, pré-verificações nativas/tokenização, suíte, plano, pixels/tempos,
raws/reservas, revisão vinculada, comparação, descarte e verificação final.

- Plano lógico: `12792b460cce1a517b754064155d719cfc2c5d75ea441ed76a147f6a31a56921`.
- Configuração: `9c4b76ff6dd91e7b9a628851c76aa2cf627f526833aa602a87b691d6af2cbe11`.
- Gramática: `6fb3e7afdb80afa69a5fdb571f2be8daa10a45578a8fd49c26d8f2a6a9d71d07`.
- Recibo nativo lógico: `be5738c52df4613a007db394f2e887cb5e0a42782dedfd3a364a67d7203e5186`.
- Comparação lógica: `a9c12738f5a0f90eb0e525b19e8bb56d451b34a1ba70d0def5cab250b2acc792`.
- Arquivo da comparação: `35a192dc2728132a3a78803650e9dcb587ef5f7a500be657d7a206bbf45ebd59`.
- Checkpoint selado: `2ac7ba47e60884293e005e484b9ef3a02de110572c2f9ef60bbab2e18e8d07fe`.
- M1 preservado: `9dd1c7a2e35e32cf3068395ed8bf2e0561aa4fecded5c31754f981cc13d70d59`.

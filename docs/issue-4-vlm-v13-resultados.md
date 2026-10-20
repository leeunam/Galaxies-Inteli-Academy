# Produto v13-R — gramática validada, controles aprovados e vídeos parciais

Execução de 20/10/2026 do [protocolo v13-R](issue-4-vlm-v13-protocolo.md),
autorizado após a [investigação da contradição de R](issue-4-vlm-pos-v12-investigacao-e-proposta.md).
A gramática passou na validação nativa sem modelo; a v13-R acertou **12/12
controles negativos**. Foram concluídos **quatro dos oito vídeos preservados**,
com 4/4 valores+frames corretos. O processo encerrou com código143 durante
o quinto vídeo; uma reserva ficou sem resposta capturada. A origem desse
encerramento, compatível com SIGTERM, não foi identificada.

A fila foi auditada e selada em `v13_external_termination_exit_143_no_retry`.
Não houve retry, preenchimento do quinto resultado ou continuação dos demais.
Nenhuma aquisição, auditoria nova, liberação de coluna, treino B/C ou promoção
do M1. A inspeção diagnóstica parcial também encontrou categorias sem suporte;
o acerto do valor não certificou a percepção.

## Implementação e verificação anteriores às inferências

O commit `1edf3f9` implementa extrator, schema fechado, ponte/gate nativos,
testes de contrato e protocolo. O commit `901ebfb` acrescenta fila própria,
linhagem, reservas, comparações e revisões de pistas. A implementação é aditiva;
fontes e filas anteriores ficaram iguais. O prompt R, decoder v11, mapper,
OR, unknown e janela de produto ≤3 s continuam os aprovados.

Os sete ramos restringem estados, categorias e pistas às244 combinações já
aceitas pelo decoder. Não há reparo da saída antiga nem derivação de pista
para esconder contradição. Cada reserva depende da integridade do recibo
nativo, além das fontes/configuração e inputs congelados.

Passaram **74 testes direcionados** (39 em7,83 s e35 em27,70 s) e
**1.021 testes completos em634,59 s**, uma execução completa no código final
antes da primeira inferência. Ruff passou;180 arquivos Python estão formatados.
Revisão local de diferenças normalizadas em relação à v11/v12, contrato,
ponte nativa, recibos, fases, orçamento e preservação. Não se atribui revisão
independente ou auditoria cega a esta unidade. O código não mudou após a suíte.

## Gramática no runtime instalado

A ponte C++ compilou sem warnings e chamou o conversor de `libllama-common.so`
e o parser/pilha de `libllama.so` do b11716 já instalado. Usou cabeçalhos
oficiais dessa versão com hashes fixos, copiados temporariamente para compilar
somente a ponte. Não recompilou, instalou ou substituiu bibliotecas/pesos.

A conversão usou `json_schema_to_grammar(..., false)`, consistente com o
caminho --json-schema-file. O código oficial desse argumento lê o schema e
chama o mesmo conversor com o parâmetro padrão.
[Referência b11716](https://github.com/ggml-org/llama.cpp/blob/b11716/common/arg.cpp#L2185-L2200).
A validação consumiu caracteres e conferiu término completo na pilha nativa,
sem vocabulário, carga de modelo ou forward pass nessa etapa.

Das **9.815 sondas**, nenhuma divergiu do esperado:9.548 objetos do domínio
finito,244 variações de whitespace entre campos e23 mutações brutas. Os244
objetos semânticos válidos passaram, incluindo todas as ordens de categorias
aprovadas; a contradição `no_target`/`incidental`, duplicata, conteúdo extra,
prefixo incompleto e demais mutações foram recusados. A geração mantém a
ordem das chaves; o decoder semântico admite outras ordens. Arrays constantes
usam literais compactos na gramática. Isso mede conformidade da geração, não
percepção dos pixels ou garantia contra truncamento com whitespace arbitrário.

O recibo final vincula fontes, schema, gramática, bibliotecas, cabeçalhos,
ponte e transcrições. A versão de schema é exatamente o rascunho aprovado;
o gate de integridade também passou após a avaliação, sem executar inferência.

## Controles idênticos

| Versão / mesmos12 controles | false correto | true | unknown |
| --- | ---: | ---: | ---: |
| **v13-R** | **12/12** | **0** | **0** |
| v11 em cache | 1/12 | 11 | 0 |

Foram11 ganhos e nenhuma perda nos12 pares. O primeiro controle, que interrompeu
a v12-R, agora respondeu `no_target`/vazio/`absent`, com o mesmo prompt R e
PNG/tempo. A v12 tinha uma saída rejeitada e zero resultados aceitos; não
entra como taxa de acerto ou baseline de doze controles.

Esse painel sintético inclui oito variantes de ABC123 e não estima
especificidade em vídeos reais. Frente à v11, prompt e schema diferem; o
resultado não isola causalmente ordem textual, ramo ou token. Não houve
retuning depois das respostas ou execução de E/RE.

## Quatro vídeos completos e diagnóstico separado de suporte

Os quatro completos são positivos de moda, em quatro canais revelados.
A comparação usa apenas essa interseção, sem transformar o parcial em oito
ou vinte avaliados:

| Versão / mesmos4 vídeos | Valores+frames corretos | Ganhos/perdas de v13-R |
| --- | ---: | ---: |
| **v13-R** | **4/4** | — |
| v10 em cache | 2/4 | 2/0 |
| v9 em cache | 1/4 | 3/0 |
| v8 em cache | 4/4 | 0/0 |
| A/v7 em cache | 4/4 | 0/0 |
| B/v7 antigo32 em cache | 4/4 | 0/0 |

V11/v12 têm zero vídeos. O 5/8 histórico da v10 não é o denominador desta
tabela. Dois dos três erros antigos da v10 foram recuperados no valor; o
terceiro não foi executado. Nos12 frames precoces completos, a v13-R produziu
nove `presented_target` e três `incidental_only`, sem unknown. O OR acerta o
vídeo mesmo quando perde um frame positivo; não exigir que todos sejam true
para contabilizar o acerto composto previsto no protocolo.

Nos16 frames dos quatro completos, houve12 positivos: oito pistas
`worn_detail_focus` e quatro `held_display`; os quatro restantes foram
incidentais. As12 listas positivas incluíram garment e cosmetic; sete também
incluíram accessory. Uma inspeção assistida separada confrontou todos esses
12 objetos com as quatro folhas originais e a inspeção congelada anterior:

- **Blusa branca:** detalhe versus roupa incidental continua ambíguo nos
  dois primeiros frames; cosmetic/accessory apresentados não têm suporte.
  O positivo tardio com held_display não mostra exibição clara de item segurado.
- **Camisa listrada:** corpo inteiro/padrão sozinho não estabelece detalhe;
  mesmo no crop lateral tardio, cosmetic não tem item apresentado visível.
- **Roupas sobrepostas/pincel:** as peças são recortes isolados e o pincel é
  um aplicador. Não transferir sua pista às categorias de peça/cosmético/
  acessório listadas ou inferir aplicação sem contato visível com a pele.
- **Saia com laço/fenda:** há suporte ao detalhe da peça nos positivos,
  mas nenhum cosmético apresentado sustenta a categoria extra.

**Nenhum dos12 objetos positivos teve suporte integral às categorias/pista
declaradas**, pois todos incluíram cosmetic sem item apresentado visível.
Maquiagem no rosto, roupa ou joia vestidas não certificam essas apresentações.
Essa constatação não transforma os quatro valores true em falso no GT antigo.

O diagnóstico é posterior à revelação, assistido e não certificado; fica em
sidecar próprio. Não foi submetido como revisão formal da fase1: o bloco de
oito não terminou. Não substitui o gate, não reabre a fila e não altera sua
parada operacional. O painel completo de prontidão e a fase2 não foram medidos.

## Interrupção, contabilização e encerramento auditado

Depois dos12 controles e quatro vídeos, o quinto preservou três raw válidos.
Seu quarto frame tinha reserva e recibo `running`, sem raw. O comando retornou
código143, sem erro Python capturado; não há evidência para atribuir o evento
a OOM, timeout, parser, provedor ou mudança de identidade. Nenhum worker VLM
estava ativo na auditoria seguinte. Não se sabe se a tentativa incerta chegou
a concluir inferência; ela permanece consumida.

O checkpoint anterior ao fechamento e os hashes de todos os arquivos da fila
foram guardados à parte. Sob locks/guardas, a operação foi marcada failed/
ExternalTermination e o parcial selado pelas funções existentes, sem chamar
novamente o executor. Os31 raw, o recibo running,16 resultados completos e32
reservas ficaram byte a byte iguais. O quinto vídeo não foi agregado ou
incluído nas métricas. A revisão de oito casos e as12 reaquisições não ocorreram.

| Contador | Novo | Cumulativo | Teto desta autorização |
| --- | ---: | ---: | ---: |
| Reservas nativas | **32**:31 respostas válidas e1 incerta | **1.755** | 1.815 |
| Aquisições | **0** | **256** | 268 |
| Sessões cobradas | **582,4916 s** | **36.159,6096 s** | 37.977,1180 s |

O total mantém180 s alocados à chamada não medida; não é todo runtime medido.
As31 chamadas capturadas somam393,6439 s de runtime nativo, com máximo14,4817 s
e pico RSS2.610,87 MiB, abaixo de3,3 GiB. Não reiniciar contadores nem recuperar
tempo incerto. Suíte e validação sem geração não contam como inferências.
O saldo de60 chamadas/12 aquisições ficou encerrado; não autoriza retry.

O guard puro recusou a fila selada sem modificar o checkpoint. O journal de
novas folhas está vazio/concluído, pois não houve aquisição. Os quatro crops
temporários do quinto caso e seu schema foram conferidos por hash e removidos
com journal separado e escopo exato, após preservar as evidências da interrupção.
Nenhuma folha antiga foi removida ou movida; nenhum arquivo running recebeu
uma resposta inferida ou fabricada.

## Preservação e consequência

Conferem os **961 arquivos herdados**,962 pins do plano e dez fontes/testes/
protocolo congelados. As oito folhas antigas continuam presentes e idênticas;
seus32 crops foram reproduzidos em memória antes/depois, com tempos iguais.
Os12 controles também foram regenerados com hashes idênticos.

Ambientes raiz130/isolado42 distribuições iguais. Runtime/pesos reconferidos em
leitura contra o arquivo oficial em cache, sem reinstalação. Zero temporários
de mídia e nenhum worker ao terminar. O único acesso externo foi aos cabeçalhos/
fontes públicos oficiais para a ponte; nenhuma mídia ou dado privado foi enviado.
Inferência exclusivamente local. README não rastreado não foi lido ou alterado.

Partições **203 treino /66 validação /31 teste reservado** preservadas. O teste
continuou fechado, sem abrir features/rótulos/previsões/métricas. M1/A200,
seus três modelos nativos, A300, B-cache, serviço Python/MCP e filas anteriores
conferem com seus pins. Nenhuma coluna/modelo liberado. A v13-R não está pronta
para outra auditoria cega; controles aprovados e quatro acertos não substituem
o painel e as revisões exigidos. Qualquer recuperação da execução interrompida
exige protocolo próprio, preservando esta fila e a tentativa incerta.

Recibos privados em `data/private/issue-4-vlm-v13-v1/` e
`data/private/issue-4-vlm-v13-verificacao-v1/`: validação nativa, suíte, plano,
pins/pixels, raw/reservas, auditoria/fechamento da interrupção, comparação,
diagnóstico assistido parcial de pistas, descarte e conferência final.

- Plano lógico: `890043b330f969d0f8740fe1392131aa389b46076a9135f7da85cd2f228f880c`.
- Configuração: `3e25456271a2b8d481175c2cfeddec5be0ef606b91d0b1fd9e25aaf4500d7cc2`.
- Gramática: `78cfda2f41086e178888c0191ab5fadb46e10766830798d7f5ed4553826ea354`.
- Recibo nativo lógico: `bce268c3b6551381607ad888446c521e2fa452565235cf6323c0b3aba3099a7c`.
- Comparação lógica: `dda6f7c4292b9d942c5a40ce5baf45f3ea98e2e64ce3ffc7fdf302e7f52944e3`.
- Arquivo da comparação: `c63975c51a81b02d1ab7d3021982239ccbe648fa0d5a8e1bf6ee3df474703d94`.
- Checkpoint selado: `3b8c6c75d8f5a83c0137a23efbdeca6d7efbe613303147451cf63067264be716`.

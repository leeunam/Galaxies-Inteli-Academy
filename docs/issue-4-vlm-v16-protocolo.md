# V16 — diagnóstico limitado da ordem de serialização

Autorização humana de20/10/2026,19:25 de São Paulo (22:25 UTC), mensagem
`Sentinel_c36e04c6f9388191b2cb3380d86351ae`: “Prepara uma proposta sem minha
aprovação e executa. Confio em você”. O canal principal e o supervisor delimitaram
este diagnóstico e exigiram passagem técnica do protocolo/preflight antes de
inferir. Isso não pede nova aprovação humana intermediária nem permite
ultrapassar os limites ou aprovar percepção artificialmente.

A branch local `codex/issue-4-v16-ordem-serializacao` parte da integração #5,
`9c4177a4ddc3b44710d0b39435d1df02d4f2201e`. Preservar a integração e a branch
v15 em `69a5832`; não retornar a uma árvore anterior. Um único escritor e
executor nesta árvore. NIM é outra frente, fora deste diagnóstico.

## Contraste e limites causais

Comparar duas ordens de **resposta JSON** sob o mesmo prompt comum:

| Condição | Ordem serializada |
| --- | --- |
| item_first | item_configuration → state → presented_categories |
| state_first | state → item_configuration → presented_categories |

Manter exatamente os22 objetos semânticos v15:19 positivos e três
negativos/incerto, dez ramos, mesmas categorias e ordem dos ramos. Na segunda
condição, mudar apenas a ordem das propriedades de cada ramo. Inclusive as
listas `required` continuam com a ordem antiga nas duas condições; sua semântica
não depende de ordem. `fields` registra a ordem esperada como metadado local.
Não remover categorias nem configurações para facilitar um gate.

O prompt comum deriva do v15 mudando somente a frase que ordenava a saída:
“Return only the JSON object defined by the schema, with every required field
exactly once.” As demais instruções e a projeção são idênticas nas duas condições.
O prompt não privilegia uma ordem de campos. Não haverá exemplos por condição,
retuning, reparo, nova rodada, mudança de modelo ou troca de crop após respostas.

Este contraste mede efeito da serialização sob esse prompt comum. Não prova,
sozinho, a causa histórica da regressão v14→v15, pois o prompt comum também
difere do v15 histórico. Ordem de serialização não demonstra ordem de raciocínio.
Coerência gramatical não certifica suporte visual.

Hashes congelados (`digest` canônico ordena chaves; hash ordenado preserva-as):

- Prompt comum: `8d8409bb27160460d38d71fc94914b68412504ce3db8437b16876053aed8ae3d`.
- Schema semântico comum: `1ee90e85d7204bbf21c86c7146852fb84fc433e26cc41a7949a90660cf54bfd3`.
- Schema ordenado item_first: `3ad765214176a92d6b166ceb835b1824635719b4395f470b61bfa39ad477ed06`.
- Schema ordenado state_first: `47bf27350b557bb6223b1213654d3a1f21b7099c159408dd8960b0ecd387baef`.
- Projeção: `958f8d2f25e00d581f3d8bcc80278d78fabd10b6595124451b59c1c2f525adf0`.
- Seleção dos cinco crops: `14f950b8b23708362ab21c1b40bc0089d5a2313d08cf09f22e4e9496a068ac23`.

## Entradas e suporte positivo congelado

Negativos: as mesmas12 fixtures v15 (oito textos, branco, preto, linhas e formas),
mesma receita/fonte, PNG RGB320×330 e tempo0. Exigir12/12 false em cada condição;
unknown falha. A distinção fina absent/incidental não é um novo gabarito.

Positivos: exatamente os cinco crops que já tinham held_display/garment
suportado na revisão v14. A inspeção congelada anterior à v11 também registra
as alternativas isolated explicitadas abaixo. São **cinco crops de três vídeos**,
com três crops de um mesmo vídeo; não cinco vídeos independentes.
Mesmos cinco casos e gabaritos nas duas condições, sem ampliar alternativas
após respostas. Todos pertencem ao treino e têm tempo≤3 s.

| Crop revelado | Tempo | Configurações admissíveis / categoria | Testemunha na anotação congelada |
| --- | ---: | --- | --- |
| epAKcoQrirk /frame1 | 0,2 s | hand_holds_hanger_out ou isolated_physical_item /garment | Calça cinza no cabide segurado, exibida separada do corpo em primeiro plano; anotada held ou isolated. |
| epAKcoQrirk /frame2 | 1,5 s | hand_holds_hanger_out ou isolated_physical_item /garment | Calça azul no cabide segurado; mesma relação e peça física separada do corpo; anotada held ou isolated. |
| epAKcoQrirk /frame3 | 2,8 s | hand_holds_hanger_out ou isolated_physical_item /garment | Calça escura no cabide segurado; mesma configuração física em primeiro plano; anotada held ou isolated. |
| toNRze0de1M /frame1 | 0,2 s | hand_pulls_worn_fabric_out ou isolated_graphic_item /garment | Mão puxando a barra do vestido vestido; alternativamente, recorte gráfico de vestido no canto, explicitamente anotado isolated. |
| xln8Ioqk1jU /frame3 | 2,8 s | hand_holds_hanger_out ou isolated_physical_item /garment | Peça xadrez e mão no cabide, em primeiro plano; anotada held ou isolated. |

Nos cabides, isolated_physical_item corresponde à própria peça física exibida
separada do corpo. A definição permite item exibido em primeiro plano, sem
exigir que esteja solto de uma mão; não corresponde à arara do fundo. A ligação
mão–cabide sustenta a outra alternativa, sem fingir que a mão segura diretamente
o tecido. No vestido, o recorte gráfico e a barra puxada são instâncias visuais
diferentes: cada alternativa tem sua própria testemunha no mesmo crop. A mão da
pessoa não é emprestada ao recorte. Não aceitar configuração genérica sem suporte.

O plano guardará, por crop, hash do PNG original e recorte, índice original,
tempo, registro literal da inspeção, revisão positiva anterior e hashes das
fontes, além do mapa configuração→testemunha. Hash da inspeção anterior à v11:
`8bcd045c71733de2a0265dbd5044505482d9d2acdd44464d5cc6a8de19780905`.
São anotações assistidas já reveladas, sem independência, nova auditoria ou
certificação humana. Não substituir GT nem promover ambiguidades das blusas.

## Ordem de execução, critérios e paradas

1. Antes de gerar, concluir testes/revisão local, protocolo e preflight offline,
   selados em commits. Preparar fila nova com contadores zero. Publicar aqui o
   checkpoint legível para conferência técnica do supervisor e canal principal.
   Exigir recibo de liberação técnica vinculado ao plano/configuração e mensagem
   efetivamente recebida; não fabricá-lo ou substituí-lo por aprovação humana nova.
2. Processar os12 controles em ambas as condições:24 chamadas. Alternar a ordem
   dentro dos pares: item/state no controle de índice par, state/item no ímpar,
   índices começando em zero. Falha perceptiva não encerra a outra condição:
   concluir os24 para comparar. Exigir12/12 false por condição para elegibilidade.
3. Somente para cada condição elegível, processar os mesmos5 crops positivos:
   até10 chamadas adicionais. Ordem dos crops conforme a tabela; quando ambas
   forem elegíveis, alternar a primeira condição em cada par como nos negativos.
   Falha perceptiva conclui o bloco elegível, sem retry ou retuning.
4. Exigir5/5 true **e** categoria/configuração pertencentes ao mapa admissível
   congelado, além dos12/12 negativos. True com pista/categoria sem suporte,
   unknown ou false falha. A resposta pode escolher qualquer uma das testemunhas
   predefinidas, sem trocar a configuração por código para fazê-la passar.
5. Selar o resultado. Relatar denominadores, unknown, ganhos/perdas nos crops
   comuns e suporte nativo separado do booleano. Se nada passar, encerrar com
   resultado negativo. Se passar, indicar apenas candidata ao próximo
   desenvolvimento. Não liberar atributos, auditoria, treino B/C ou v17.

Falha operacional, identidade divergente, JSON, ordem ou gramática incorreta
interrompe **toda a rodada** imediatamente, sem completar a outra condição.
Preservar raw/reservas e resultado parcial/incerto, sem retry/reparo/substituição.
Running/incerto não é retomável automaticamente. Nenhuma fila selada reabre.

## Preflight offline obrigatório

Reutilizar a ponte C++ v13 imutável e nove cabeçalhos oficiais em cache. Compilar
somente a ponte contra b11716 instalado; converter schema exatamente pelo caminho
`json_schema_to_grammar(..., false)` usado pelo CLI, sem carregar modelo/inferir.
Conferir runtime/pesos em leitura contra o arquivo oficial, sem reinstalar.

Para **cada condição**, zero divergências em13.703 sondas:13.640 objetos do
domínio finito (22 aceitos),22 variações de whitespace entre campos,19 mutações
brutas e22 objetos semanticamente válidos com a ordem oposta, todos recusados.
Comparar os22 objetos aceitos como conjuntos semânticos e exigir gramáticas
nativas distintas. Se a conversão normalizar a ordem e não houver contraste,
bloquear a avaliação sem gastar chamadas. Arrays enumerados são literais;
whitespace interno arbitrário não é garantido pelo runtime.

Usar tokenizer instalado, offline, sem geração, nos22 objetos por condição,
compactos e com whitespace entre campos:88 serializações; exigir≤64 tokens
incluindo reserva de término. Capturar o comando do adaptador original com
Popen substituído por recorder, sem iniciar o VLM: argv normalizado idêntico,
schemas ordenados distintos e iguais aos schemas convertidos. Nenhum mock de
comando será tratado como prova perceptiva. Guardar fontes, bibliotecas,
cabeçalhos, compilador, schemas, gramáticas, sondas, respostas e comandos por hash.

Mesmo Qwen3-VL-2B Q4_K_M, projetorQ8_0, b11716, CPU4, seed42, temperatura0,
saída64, contexto3072 e limites visuais solicitados64/128. Mesma projeção,
mapper e regras temporais; pessoa/texto não são regenerados. Cada positivo usa
um crop e seu tempo original, com índice original identificado separadamente
do índice1 da chamada. Nenhum outro frame ou folha é gerado para avaliação.

## Orçamento e preservação

Novo orçamento único: **≤34 chamadas locais /zero aquisições /1.200 s de sessões**,
180 s por chamada e RSS3,3 GiB. Reserva durável com fsync antes do despacho,
locks ancestrais, um executor e contabilização conservadora de tentativa incerta.
Base selada1.811 chamadas /256 aquisições /37.044,30741882603 s; tetos novos
1.845 /256 /38.244,30741882603 s. Os32 saldos encerrados da v15 não são reutilizados.
Preflight/testes sem geração não contam como chamadas nativas.

Conservar os1.345 hashes conferidos pela integração #5 e suas21 fontes/21 recibos
novos, mais o próprio recibo final:43 pins adicionais, total1.388 antes deste
marco. O baseline novo adiciona o hash de seu próprio arquivo ao plano. Comparar
antes/depois também ambiente raiz130/isolado42, locks, pesos/runtime, M1/A200,
A300, B-cache, serviço Python/MCP/StateGraph, oito PNGs,32 crops, tempos,
partições203/66/31 e recibos anteriores. Guardas das coortes200/300: holdout31
fechado, sem abrir suas features, rótulos, previsões ou métricas.

Tudo aditivo: docs/código/recibos novos, sem editar briefing pinado, fontes
seladas, README ou clone NIM. Sem aquisições, downloads, API/NIM, credenciais,
sync/install, publicação, push ou deploy. Não alterar ambiente/lock ou modelo.

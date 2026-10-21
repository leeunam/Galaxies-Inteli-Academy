# Encoder observado: 100 tokens de imagem inseridos

O [adendo em nível 4](issue-4-vlm-encoder-trace-protocolo.md) concluiu em
21/10/2026 com uma chamada no mesmo positivo conhecido. Os quatro eventos
exigidos foram capturados e validados: início/fim de codificação e início/fim
de um batch de **100 tokens de imagem**. Retorno 0, stdout válido pelo decoder
original e limpeza confirmada. A [evidência agregada](evidence/issue-4-vlm-encoder-trace-resultados.json)
vincula os recibos sem texto livre, imagens ou saída bruta.

| Medida | Resultado |
|---|---|
| Implementação | `1c649d6` |
| Chamadas / branco / aquisições / NIM | 1 / 0 / 0 / 0 |
| Relógio global | 14,8767 s de 90 s |
| Sessão nativa | 14,7992 s |
| Pico RSS amostrado | 2.599,828 MiB; teto 3,3 GiB |
| stdout / stderr recebidos | 125 / 19.031 bytes |
| Codificação | um chunk; início `(1, 1, 3)`; fim em 2.062 ms |
| Decodificação | batch 1/1; 100 tokens; fim em 1.041 ms |
| Retorno / contrato / projeção | 0 / `item_first` válido / `true` |
| Workers / scratch ao terminar | 0 / 0 |

O stdout validado manteve `hand_holds_hanger_out`, `presented_target` e
`garment`, iguais ao ensaio anterior. Não há saída bruta retida. O objeto
de enums foi validado isoladamente; stderr não participou do parser.

## O que foi resolvido

No fonte CLI verificado, os marcadores ficam depois da carga do bitmap,
ao redor de `mtmd_batch_encode`. Os eventos do helper abrangem os batches
de embeddings de imagem enviados ao decoder. Sua sequência completa,
contagem positiva, retorno 0 e saída válida sustentam **processamento da
imagem e inserção observada de 100 tokens nesse caso**. A carga do contexto
do projetor é inferida dos guards e do percurso bem-sucedido; não houve
captura independente dos tensores carregados.

A [primeira fila](issue-4-vlm-encoder-resultados.md) continua encerrada por
observabilidade insuficiente. A diferença entre níveis foi localizada nos
ELF e confirmada por função pura da biblioteca instalada: o nível interno 2
do helper requer verbosidade 4. Este adendo alterou somente `3 → 4` no argv
normalizado e passou no critério antes ausente. Isso resolve a lacuna de
observabilidade atual; não recupera logs históricos descartados nem muda
os resultados de v16 ou dos pares positivos.

O aviso fixo sobre mínimo de 1.024 tokens para grounding Qwen-VL foi emitido
e registrado como enum. A solicitação permaneceu em 64–128 tokens e a
contagem observada foi 100. O aviso não demonstra que essa configuração
seja a causa dos erros de classificação: não houve contraste de resolução
ou de tokens. Nenhum desses parâmetros foi alterado automaticamente.

## Limite e próximo contraste

Logs não mostram valores dos embeddings, atenção, informação preservada
ou interpretação correta. Um positivo conhecido também não estima
sensibilidade/especificidade. Produto e demais atributos continuam sujeitos
aos gates originais; este resultado não aprova candidata, auditoria cega,
treino B/C ou promoção ao M1.

Agora há fundamento para preparar o contraste curto de gramática/percepção
já proposto: mesma pergunta explícita de presença de roupa em cabide,
nos mesmos positivo e branco, com e sem schema, quatro chamadas pareadas.
O contrato semântico da pergunta e a leitura da resposta precisam ficar
congelados antes, sem reparar resposta inválida. Isso investigaria o efeito
da restrição de saída nessa pergunta simples; não isolaria toda a instrução
ou a qualidade do encoder. Não aumentar tokens/modelo simultaneamente.
Esse próximo contraste **não foi reservado, preparado ou executado** nesta
unidade e requer protocolo e orçamento próprios; nenhuma inferência segue
automaticamente após o sucesso do diagnóstico.

## Verificação e preservação

Passaram 29 testes direcionados, Ruff e formatação antes da execução.
O preflight comprovou diferença exata `3 → 4`, uma chamada/90 s e zero
branco. A revisão técnica vinculou plano e configuração e foi registrada
com ID real/texto literal, antes da reserva durável. O resultado sanitizado
foi persistido antes da limpeza; a fila está selada, sem retry/reentrada.

Após a chamada, a configuração, os 26 arquivos protegidos, as oito folhas
e recibos anteriores conferem. Os dois arquivos de partições também
conferem por hash contra o registro anterior, sem leitura semântica.
M1 e teste reservado preservados, zero aquisição, remoto, treino ou campo
liberado. Zero workers e temporários deste ensaio ao terminar. A janela de
modelos foi devolvida após o resultado.

Plano: `7b710db454e1efdb24cfe401511fbd292866f288f0c2c318bec9e9bfa1af35eb`.
Configuração: `85579d3bf9de1d29c886ca79ff1ae5e472d42eb6100ec61dbea341e79b1d7737`.
Fila privada: `data/private/issue-4-vlm-encoder-trace-v1/`.

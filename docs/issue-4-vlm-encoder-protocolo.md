# Diagnóstico direto do encoder: proposta de duas chamadas

Preparação em 21/10/2026, sobre `0e85170`. Esta unidade acrescenta observação
ao percurso existente; não corrige ou aprova atributos. Nenhuma inferência
está liberada até a revisão técnica do código, plano e configuração concretos
e a devolução da janela CPU. O aluno autorizou preparar/executar propostas
técnicas; a barreira pendente é de revisão/coordenação, sem novo consentimento
humano genérico.

## Hipótese e inspeção sem modelo

`gguf_visual_attributes.invoke_local_vlm` usa `--verbosity 0` e concatena
stdout e stderr. O runtime documenta nível 0 como saída genérica e nível 3
como info. Assim, os recibos antigos não demonstram ausência de processamento
visual: os marcadores podem ter sido suprimidos. Essa é uma hipótese de
observabilidade, não explicação confirmada dos erros perceptivos.

Dois `--help` e um `--version`, com ambiente literal sem credenciais e sem
argumento de modelo, terminaram sem forward pass. O binário informa b11716,
commit `797de63b2`, GNU 11.4.0/Linux x86_64. O help do debug separado aceita
imagens sintéticas próprias e redefine argumentos; ele não será usado como
substituto do caminho que recebeu os crops reais.

O fonte CLI local e strings do ELF instalado contêm estes marcos:

1. `encoding mtmd batch, n_chunks = ...`;
2. `mtmd batch encoding done in ... ms`;
3. `decoding image batch .../... , n_tokens_batch = ...`;
4. `image decoded (batch .../...) in ... ms`.

O fonte carrega o contexto de projeção por `mtmd_init_from_file`, recusa contexto
nulo, carrega o bitmap, intercala mídia/texto, chama `mtmd_batch_encode`, exige
embedding não nulo e chama `mtmd_helper_decode_image_chunk` antes de gerar.
Os marcadores de codificação ficam nesse caminho da mensagem, depois da carga
da mídia, distintos do warmup do loader. O fonte e o ELF contêm os mesmos
literais; isso não é prova de que esses eventos já ocorreram em uma inferência.

**Ainda falta validar no processo real** a presença, canal e sequência dos
marcadores no nível 3. Se não aparecerem, o resultado será observabilidade
insuficiente, sem concluir falha perceptiva ou escalar verbosidade automaticamente.

## Contraste e entradas congeladas

Executar somente o crop positivo 1 do plano positivo pós-v16 e o controle
branco da v16, nessa ordem. Ambos são RGB 320×330, tempo original 0,2 s.
O positivo é de treino já revelado; não há seleção nova, aquisição ou holdout.
Os digests dos corpos de caso originais são:

- positivo: `609bfa9a3b8da1616a452ae19fcf121aabd527424d104ef18b03b6bce0684ad8`;
- branco: `4415cb4857e336fe61279b31e72249847cf951019e59b0cd8bfbdbbfae899e16`.

O plano guarda somente identidades necessárias, tempo e localizador da folha;
não copia anotações textuais, pixels ou transcrições para logs. O recorte e a
reconstrução do branco precisam reproduzir seus PNG SHA-256 originais. As oito
folhas permanecem intactas e o scratch é novo e exclusivo.

Usar `item_first` da v16, com o mesmo prompt, schema ordenado, categorias,
projeção e os mesmos argumentos auditados. Na lista de argumentos, somente
o valor de `--verbosity` muda de **0 para 3**, além dos caminhos temporários
equivalentes de imagem/schema. Continuam Qwen3-VL-2B Q4_K_M, mmproj Q8_0,
contexto 3.072, saída 64 tokens, imagem solicitada 64–128 tokens, seed 42,
temperatura zero, CPU/batch quatro threads e batch/ubatch 128, sem GPU.

O ambiente novo é literal, offline, sem proxies, chaves, tracing ou variáveis
de debug de tensores. O ambiente efetivo histórico completo não foi retido;
portanto, não se atribuirá uma eventual mudança de resposta somente ao logger.
Este é um teste do caminho visual, não uma nova avaliação de acurácia.

## O que medir e o que não concluir

Exigir, por chamada, exatamente um início/fim de codificação, com um chunk
de mídia, seguido dos batches de imagem decodificados completos e ordenados,
com contagem de tokens positiva. Exigir saída do processo sem erro e stdout
validado isoladamente pelo decoder original `item_first`.

Com esses eventos, o fonte verificado sustenta que o bitmap entrou no encoder
e que embeddings de imagem foram enviados ao decoder. A carga do projetor
é inferida desse caminho bem-sucedido e do guard de contexto não nulo; não
há captura independente de pesos carregados. Não se observam valores dos
embeddings, atenção ou informação preservada. **Executar o encoder e inserir
tokens não prova qualidade da representação ou uso semântico correto.**

O ELF também contém um aviso sobre 1.024 tokens em grounding Qwen-VL. Sua
presença estática não prova que se aplique ou tenha sido emitido neste modelo.
Registrar somente o evento, se aparecer; não aumentar tokens, resolução,
modelo ou ubatch nesta unidade.

## Orçamento, consumo e parada

| Recurso | Limite novo |
|---|---:|
| Chamadas nativas | 2, positivo e branco |
| Relógio global | 180 s, incluindo inicialização, probes/checks e sessões após o marcador de início |
| Chamada | até 180 s, limitada ao saldo global menos 5 s |
| RSS amostrado | 3,3 GiB, intervalo 50 ms |
| stdout / stderr em memória | 16 KiB / 256 KiB por chamada |
| Aquisições, NIM, remoto, instalações | 0 |

A fila única é `data/private/issue-4-vlm-encoder-probe-v1/`. Preparação cria
plano e checkpoint zerado; não cria liberação. A revisão deve vincular os
hashes do plano/configuração, ID real e texto literal da decisão. `execute`
recusa revisão ausente ou diferente antes de iniciar o processo.

Um marcador exclusivo de tentativa impede reentrada até mesmo antes da
primeira reserva ou entre chamadas completas. Cada chamada é consumida e
sincronizada antes de Popen. Morte forçada/resultado incerto não libera saldo;
o marcador conserva 180 s como teto de cobrança incerta. Não há retry, troca
de caso, nova fila ou reaproveitamento de orçamento v16.

Falha operacional, timeout, recurso, identidade, stdout inválido ou ausência/
inconsistência dos marcadores encerra a fila. A primeira falha impede chamar
o branco. Um erro perceptivo com JSON válido e caminho visual comprovado não
interrompe a comparação observacional do segundo input.

Os canais são separados. Somente eventos fixos/inteiros, códigos estáticos,
contadores, métricas e o objeto de enums já validado podem persistir. Texto,
pixels, dumps, stderr desconhecido, resposta inválida, exceções e seus hashes
não são retidos. Nem stderr com JSON aparente pode reparar stdout inválido.
O diagnóstico sanitizado deve ser persistido **antes** da limpeza do scratch.
Limpeza não confirmada preserva o scratch e encerra a tentativa; não se promete
recolhimento instantâneo após morte do pai/host.

O snapshot de processos deve estar livre dos outros workers de modelos antes
do início. A janela será serializada com a #7. Não há autorização de inferência
neste documento ou nas verificações leves da preparação.

## Continuidade discriminante proposta, fora desta fila

Se o caminho visual for demonstrado e continuar havendo erro semântico, o
próximo contraste possível seria um prompt curto com contrato JSON explícito
de presença de roupa em cabide (`yes`/`no`/`uncertain`), nos mesmos dois inputs,
com e sem gramática: quatro chamadas pareadas, hipótese de efeito da restrição
de saída, até 180 s novos. Seria preciso selar a pergunta e o orçamento antes
de executar; **essas quatro chamadas não estão habilitadas ou reservadas**.

Esse contraste separaria o efeito da gramática naquela pergunta simples;
não isolaria por si só todas as causas do prompt/serialização original. Se
ambos os modos falharem, não se poderia culpar o encoder apenas por exclusão.
Não há correção ou próximo ensaio automático derivado deste plano.

Os gates 12/12 negativos e 5/5 positivos continuam iguais. Casos conhecidos
não aprovam candidata, coluna, auditoria cega, B/C, avaliação do teste ou troca
de M1. Partições, M1, oito PNGs, filas e recibos antigos permanecem protegidos.

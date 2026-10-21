# Contraste de percepção: relação mão–tecido, com e sem gramática

Protocolo de desenvolvimento em 21/10/2026. Substitui o rascunho anterior
com branco e pergunta sobre cabide. O [diagnóstico do encoder](issue-4-vlm-encoder-trace-resultados.md)
comprovou codificação e inserção de tokens em um caso; qualidade perceptiva
continua sem aprovação. Nenhuma geração está liberada até revisão técnica
dos novos hashes e janela CPU. Não se reutiliza saldo de filas encerradas.

## Hipótese e par real

Comparar a aplicação de gramática mantendo pergunta e contrato textual
exatamente iguais. O principal identificou dois crops de treino já revelados
na V14: um erro negativo de vínculo mão–roupa e um positivo de tecido da
própria roupa segurado para fora do corpo. As anotações assistidas congeladas
sustentam os esperados diagnósticos `no` e `yes`; não são novos rótulos
certificados ou amostra independente. Identidades e proveniências ficam
somente nos recibos privados, sem publicar IDs ou localizadores de mídia.

Os PNGs RGB 320×330 e tempos originais (positivo 0,2 s, negativo 2,8 s)
devem reproduzir seus hashes antes/depois de cada chamada. Não há aquisição,
seleção adicional, novo caso ou leitura do teste reservado. A indicação do
principal foi vinculada aos recibos V14, incluindo a revisão e os resultados.

## Pergunta e contrato comuns aos dois braços

O predicado é a relação mão–tecido e o tecido afastado do corpo visíveis
no mesmo quadro. Não pedir intenção de apresentar/exibir, movimento ou
proveniência real/sintética. Usar literalmente o mesmo prompt UTF-8, sem
newline final ou rótulo de condição/caso:

```text
Does the image show a hand directly gripping and pulling outward the fabric of a garment that someone is wearing? In this question, pulling outward means a visible hand-to-fabric grip with that same fabric held away from the wearer's body in this single image; do not infer motion or intent. Return exactly one JSON object with the single key "answer" and one string value: "yes", "no", or "uncertain". Use "uncertain" when the image does not allow a decision. Do not add other keys or text.
```

A abstenção se chama `uncertain`, conforme o contrato do supervisor. O rascunho
do principal usava `unknown`; a correspondência é apenas de nome no protocolo
novo. Não converter respostas `unknown` em `uncertain` depois de gerar.

```json
{"type": "object", "properties": {"answer": {"enum": ["yes", "no", "uncertain"]}}, "required": ["answer"], "additionalProperties": false}
```

O prompt inclui o contrato completo mesmo sem gramática. Em cada par, a
única diferença de argv é a presença/ausência de `--json-schema-file` e seu
valor; não mudar texto, enum, seed ou parâmetros junto da condição.

Manter Qwen3-VL-2B Q4_K_M e projetor Q8_0, contexto 3.072, saída até 64 tokens,
imagem solicitada 64–128 tokens, temperatura zero, seed 42, quatro threads
CPU/batch, batch/ubatch 128, sem GPU e verbosidade 4. Usar o mesmo ambiente
literal offline e captura de canais separados do diagnóstico. Não habilitar
debug 5, aumentar tokens/resolução/modelo ou inserir exemplos por condição.

## Ordem congelada e desfechos

| Célula | Crop | Gramática | Esperado diagnóstico |
|---|---|---|---|
| 1 | Positivo real revelado | sim | `yes` |
| 2 | Mesmo positivo | não | `yes` |
| 3 | Negativo real revelado | não | `no` |
| 4 | Mesmo negativo | sim | `no` |

Processo novo por chamada, sem histórico ou cache de resposta. A ordem oposta
no segundo par evita sempre pôr o mesmo braço primeiro, mas não substitui
replicação/randomização. Sem repetir ou trocar uma célula após seu resultado.

O [parser curto](issue-4-vlm-percepcao-captura-curta.md) exige stdout inteiro:
objeto JSON com chave única `answer` e string `yes`, `no` ou `uncertain`.
Whitespace externo é permitido. Recusar duplicatas, extras, coerção, code
fences, prosa ou extração de fragmento JSON. Stderr não repara stdout.

O preflight sem modelo usou a ponte nativa já instalada: os três enums em
formas compacta/indentada foram aceitos; dez mutações inválidas recusadas.
Três formas JSON válidas com whitespace após o objeto são recusadas pela
serialização gerada. A expectativa inicial de paridade nessas três formas
falhou e foi preservada; a gramática termina no `}`. A conferência final
registra esse subconjunto explícito, sem alegar equivalência completa ao
parser ou mudar os enums. Whitespace externo continua válido no parser comum
aos dois braços, sem punição artificial no braço livre. Foram 19 sondas,
seis aceitas/13 recusadas no domínio nativo documentado, sem recompilação,
carregamento de modelo ou geração.

- JSON inválido: `format_invalid`, desfecho de formato falho, sem comparação
  semântica; **continuar** as células predefinidas se a execução técnica estiver íntegra.
- `uncertain`: abstenção válida, separada de acerto/erro; não aprova percepção.
- `yes`/`no` válidos: comparar ao esperado diagnóstico, sem alterar GT legado.
- Falha técnica: resposta não avaliada, encerrar como parcial; não inventar
  resultado para células não executadas.

Persistir somente enums/códigos fixos, contadores e observações do encoder.
Nenhum corpo bruto, texto arbitrário, exceção ou hash de resposta rejeitada.
A captura limitada permanece intacta; o adaptador aplica o contrato novo aos
mesmos bytes, descartando a decodificação histórica de outro schema.

## Orçamento, identidade e encerramento

Quatro chamadas máximas, **180 s globais**, **até 45 s por dispatch**, incluindo
cinco segundos reservados conjuntamente para limpeza dentro do saldo.
RSS amostrado de 3,3 GiB; stdout 16 KiB / stderr 256 KiB. O tee mantém uma
cópia adicional limitada a 16 KiB em memória. Zero aquisição, remoto, treino,
novo campo, troca de M1 ou abertura de holdout.

Plano deve vincular fontes, seleção privada, proveniência V14, prompt, schema,
sequência e limites. Revisão durável deve vincular hashes, ID real e texto
literal da decisão específica. Preparação não cria liberação. Marcador de
início impede reentrada mesmo antes da primeira reserva; cada chamada é
consumida duravelmente antes de spawn. Resultado incerto não devolve saldo.

Exigir encoder início/fim, batches completos/ordenados, tokens positivos,
retorno 0 e limpeza confirmada. Parar por falha técnica, relógio, bytes/RSS,
identidade divergente ou encoder incerto. Formato inválido **não** é razão
técnica de parada neste contraste. Salvar recibo sanitizado antes de remover
scratch próprio; limpeza incerta conserva scratch e sela. Nunca repetir.

## Critério de leitura

Relatar as quatro células, formato, abstenção e comparação semântica separados.
Se retirar gramática corrigir o negativo, preservar o positivo e produzir
formato válido, haverá hipótese de candidata para avaliação maior. O par
sozinho não aprova atributos nem explica a causa ampla da V16. Concordância
não exclui efeito da gramática, e erro nos dois modos não identifica encoder
como causa por exclusão. Não comparar esse prompt curto ao histórico como
ablação causal: pergunta/schema/espaço de resposta históricos são diferentes.

Gates originais e auditoria independente continuam obrigatórios. Nenhum avanço
a B/C ou promoção por acerto nesses casos conhecidos. Próxima correção exige
defeito demonstrado e protocolo próprio, sem afrouxar os critérios originais.

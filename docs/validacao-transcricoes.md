# Validação auditiva das transcrições do piloto

O processamento automático dos três vídeos não demonstra que a transcrição está correta.
O aluno ouviu os três vídeos e confirmou as três hipóteses originais nesta sessão.
Classificou o primeiro como fala/narração e o terceiro como canto; o segundo ficou como
vocal não classificado separadamente. O roteiro com links e hipóteses está em
`data/private/revisao-transcricoes.md`, ignorado pelo Git. São cerca de 39 segundos de áudio.
Essa é uma revisão assistida com hipótese visível, não uma anotação independente cega.

## Comparação automática e referência

Comparar duas configurações do mesmo Whisper small, CPU int8, português solicitado:

- Baseline reproduzido: beam 1 e VAD ativo, como no piloto original.
- Diagnóstico: beam 5, temperatura 0, sem condicionamento no texto anterior e sem VAD.

As duas configurações recebem o mesmo áudio decodificado na sessão. Guardar o SHA-256
desse PCM e o do contêiner adquirido. Reaquisição pode mudar o hash do arquivo; não
presumir identidade de bytes com uma mídia anterior que foi apagada. O resultado
original permanece preservado. Igualdade entre hipóteses é concordância, não acurácia.
Log-probabilidade, probabilidade de ausência de fala e compressão são diagnósticos do
modelo, sem interpretação como probabilidade calibrada de transcrição correta.

O revisor deve ouvir antes de abrir a hipótese, registrar literalmente o que é audível
e indicar fala, canto, misto, instrumental, ausência de vocal ou inaudível. Não completar
finais interrompidos, trocar coloquialismos nem usar título/OCR para fazer o áudio combinar
com o assunto visual. Um vídeo de beleza pode usar diálogo sobre outro assunto; um vídeo
de looks pode conter letra cantada. Idioma solicitado ao Whisper não comprova idioma real.

Registrar `video_id`, `text`, `audio_type`, `reviewer`, `listened: true` e, quando necessário,
`uncertain_spans`. O tipo usa `speech`, `singing`, `mixed`, `instrumental`, `no_vocal` ou
`inaudible`. `vocal_unspecified` permite medir uma referência vocal não vazia quando o
revisor confirmou o texto, sem classificar separadamente fala/canto. Sem escuta registrada
e texto explícito, o avaliador recusa calcular acurácia.
Referência vazia só é aceita para ausência de vocal confirmada. Nesta primeira versão,
um intervalo incerto exclui o vídeo inteiro da métrica, com motivo; não apagar palavras
seletivamente para melhorar o resultado. O áudio ainda precisa de curadoria.

## Métricas e reprodução

`scripts/asr_quality.py` calcula distância de edição e WER/CER contra a referência humana.
A normalização versionada usa Unicode NFC, casefold, pontuação substituída por espaço e
espaços reduzidos. Mantém acentos, formas coloquiais e números como escritos; aplicar a
mesma convenção na referência. CER inclui espaços normalizados.

WER é a quantidade de substituições, remoções e inserções, dividida pelas palavras da
referência. CER faz o mesmo por caractere. O agregado soma erros e denominadores antes
de dividir; não usa média simples de porcentagens de clipes desiguais. Referência vazia
não produz divisão por zero: suas inserções são registradas, com taxa individual indisponível (`null`).

```sh
rtk proxy .venv/bin/python -m scripts.asr_quality --references data/private/referencias-humanas.json --hypotheses-root data/private/youtube-quality-v3-natural-20261017 --output data/private/avaliacao-asr-nova.json
```

Usar uma saída nova. Entradas e saídas ficam restritas a `data/private`; não versionar
transcrições ou referências reais. O avaliador não altera hipóteses, embeddings ou flags
de treino. Corrigir a transcrição exige recalcular o embedding correspondente, com
proveniência; uma anotação manual do piloto não pode ser aplicada silenciosamente ao
restante da base.

## Resultado do piloto assistido

As referências estão em `data/private/referencias-humanas-piloto.json`; a comparação
congelada da execução `youtube-quality-v3-natural-20261017` está em
`data/private/avaliacao-asr-piloto-3.json`. Os arquivos originais não foram sobrescritos.

| Vídeo | Palavras na referência normalizada | WER baseline reproduzido | WER diagnóstico |
| --- | ---: | ---: | ---: |
| Beleza 1, fala/narração | 67 | 0% | 4,48% |
| Beleza 2, vocal não classificado | 18 | 0% | 0% |
| Moda, canto | 24 | 8,33% | 79,17% |
| Agregado por contagens | 109 | 1,83% | 20,18% |

CER agregado: 0,96% no baseline reproduzido e 42,45% no diagnóstico. A reprodução do
baseline diferiu em duas edições de palavras no canto em relação à hipótese original
confirmada pelo aluno. Os parâmetros anteriores não fixavam a temperatura em um único
valor; não alegar identidade de saída entre execuções. A comparação alternativa mudou
busca, VAD, contexto e temperatura juntos, portanto não identifica o efeito de cada fator.

O diagnóstico não substitui automaticamente o baseline: foi pior nessa referência
assistida. As hipóteses originais foram confirmadas pelo aluno, mas calcular erro zero
delas contra a própria hipótese confirmada não seria evidência independente de acurácia.
Manter canto identificado na auditoria; a letra não é necessariamente a mensagem visual
do criativo. O tipo anotado manualmente não vira preditor sem um contrato equivalente
para novos vídeos. Esses resultados servem ao piloto, sem estimar qualidade populacional.

Os testes cobrem erros lexicais, ausência de referência vocal, exigência de escuta,
agregação por contagens e exclusão explícita de referência incerta. Três vídeos avaliam
o piloto, sem estimar a acurácia da futura base. A issue #1 continua dependente dessa revisão.

Referência de execução: [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

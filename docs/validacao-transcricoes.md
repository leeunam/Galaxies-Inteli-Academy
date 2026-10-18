# Validação auditiva das transcrições do piloto

O processamento automático dos três vídeos não demonstra que a transcrição está correta.
A validação de referência continua pendente de escuta humana. O roteiro com links e
hipóteses está em `data/private/revisao-transcricoes.md`, ignorado pelo Git. São cerca de
39 segundos de áudio; o revisor pode repetir trechos antes de registrar sua referência.

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
`inaudible`. Sem escuta registrada e texto explícito, o avaliador recusa calcular acurácia.
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
restante da base. Até a referência ser recebida, WER e CER **não foram medidos**.

Os testes cobrem erros lexicais, ausência de referência vocal, exigência de escuta,
agregação por contagens e exclusão explícita de referência incerta. Três vídeos avaliam
o piloto, sem estimar a acurácia da futura base. A issue #1 continua dependente dessa revisão.

Referência de execução: [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

# Captura aditiva para a pergunta visual curta

Preparação de 21/10/2026, sem inferência, aquisição ou fila nova. Esta unidade
prepara somente o contrato de resposta do próximo contraste; não implementa
a sequência de quatro células nem escolhe os casos finais. O diagnóstico
anterior e seus módulos, planos e recibos selados permanecem intactos.

O adaptador reutiliza o coletor limitado do diagnóstico de encoder. Um tee
de stdout devolve cada byte original sem mudança ao coletor e retém em memória
somente até o mesmo teto de 16 KiB para o parser novo. Não intercepta stderr,
substitui bytes, fabrica JSON, escreve corpo bruto ou registra hash da resposta.
Reserva, processo isolado, canais separados, RSS, relógio e limpeza continuam
no coletor já verificado. A cópia adicional também é limitada a 16 KiB.

O decoder histórico `item_first` continua sendo chamado dentro do coletor;
seu resultado é descartado pelo adaptador porque pertence a outro contrato.
Sua rejeição específica de schema não decide a aceitação da resposta curta.
O novo parser recebe os mesmos bytes de stdout e exige objeto JSON inteiro,
UTF-8 válido, chave única `answer` e string `yes`, `no` ou `uncertain`.
Whitespace externo é permitido. Chaves duplicadas, extras, tipos errados,
constantes não JSON, prefixos, sufixos e code fences são recusados, sem reparo.
Nem JSON aparentemente válido em stderr pode completar stdout.

O recibo guarda apenas enum válido ou `format_status=invalid`. `uncertain`
é resposta válida de abstenção; formato inválido não é abstenção ou resposta
semântica errada. A sequência futura poderá continuar nas células predefinidas
quando formato falhar, desde que a execução técnica esteja íntegra.

Falha do processo, marcadores insuficientes, limite de bytes/RSS/tempo,
cancelamento ou limpeza incerta preservam o código terminal do coletor;
a resposta fica `not_assessed_technical_failure`. O adaptador não pode
autorizar continuidade nessas condições. Não há retry ou modo que relaxe
o contrato, nem alteração dos gates perceptivos originais.

Passaram 23 testes com processos/streams inventados e rede/runtime nativo
proibidos. Cobrem os três enums, 14 respostas inválidas, separação de canais,
falhas técnicas, transparência byte a byte, limite do tee e excesso de stdout.
Ruff e formatação passaram. Não houve carregamento de modelo ou geração.
Seleção/proveniência dos dois casos reais e pergunta ainda precisam da revisão
estática coordenada antes de congelar a fila e submetê-la à revisão técnica.

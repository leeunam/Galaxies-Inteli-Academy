# Diagnóstico positivo pós-v16: fila preparada, zero operações

Preparação final em 20/10/2026, sobre o código `16d9b17`. O replay offline
está em `3d57700`; o inventário documental de mídia foi integrado em `994d227`.
Os dez testes de replay e os 44 testes do runner passaram, com Ruff/formatação
verificados. A revisão em leitura confirmou as três correções: relógio global,
retenção do raw retornado antes do julgamento de recursos e marcador durável
que impede outra entrada após início técnico, inclusive entre chamadas completas.
Não foi necessário repetir testes ou o gate nativo nesta preparação sem mudança
de código.

| Identidade | SHA-256 |
|---|---|
| Plano canônico | `efec450cc89b54a5a3ca28bdd2f6eda5bd7fdf3facf8b936a5447a01d4c2bebc` |
| Arquivo do plano | `53be90b5b2d4f4bab0ef5fef4704c6282afde567e1d0ff5a83be36f6bbe8ae8d` |
| Configuração | `b8a50a2cd0a526fc80fe516d1b57625335e2d18f946fa132be23a756355614d4` |
| Checkpoint inicial | `353d948e7b65f27964a2e3eedf31ff0ea64dfeb5da4602974ba79d60708a88cb` |
| Inventário dos 9.978 arquivos protegidos | `0cf5e4fcc5e815ee17d7e31e0a462c95eeef69bacfb47932c2b7617f7f269df0` |
| Recibo privado de preflight, digest canônico | `2c2f29700c78c69df1265277a754190dff79cfec470a10736fd77b38a6cf6314` |

A fila efetiva é `data/private/issue-4-vlm-pos-v16-pares-positivos-v1/`.
Tem somente `.lock`, `plan.json` e `checkpoint.json`: **zero operações,
reservas e aquisições**, sem marcador de execução ou liberação técnica.
A CLI `inspect`, sob as duas guardas de coorte, validou o plano e a linhagem.
Os 18 pins de fontes e os 9.978 hashes protegidos conferem. O conjunto inclui
os 9.974 pins iniciais, seu recibo e três provas aditivas de replay.

As provas gramaticais, tokenização e comandos da v16 foram reutilizadas por
identidade exata. Não houve nova compilação, execução gramatical nativa,
tokenização, carregamento para geração ou forward pass. Pesos, runtime e
tokenizer coincidem com os hashes já verificados. Pixels, tempos e anotações
dos cinco crops continuam idênticos ao plano v16; seu digest é
`382ab73dc0d03b0b930c0c2f8de36f64e6ceb8ce949ae2b232dde256cf890aef`.

## Sequência operacional e independência do NIM

Este checkpoint substitui somente a ordem de coordenação antes descrita:
o supervisor autorizou preparar o VLM antes da entrega NIM, mantendo integração
NIM para um ponto seguro **após o diagnóstico selado**. Não altera o
[protocolo científico ou seus limites](issue-4-vlm-pos-v16-pares-positivos-protocolo.md).

`load_base` usa um mapa explícito de caminhos/hashes já existentes e os recibos
VLM nomeados. As enumerações da linhagem se restringem às filas VLM ancestrais
seladas. Arquivos futuros não entram automaticamente no inventário. Portanto,
adições NIM em caminhos novos não mudam o plano, desde que não editem pins,
fontes/recibos existentes ou versões instaladas. Isso não autoriza alterar os
arquivos NIM v3 já protegidos. Nenhuma integração, teste pesado concorrente ou
operação NIM ocorrerá durante a janela nativa VLM.

A agenda é aguardar revisão concreta destes hashes e confirmação da suspensão
dos outros workers pesados; então executar uma única tentativa local exclusiva,
selar resultado/parada e só depois abrir o ponto de integração NIM. Esta
preparação **não libera geração**. A liberação técnica virá em mensagem própria,
com ID/literal reais e vínculo ao plano/configuração; não usar a liberação antiga.

## Critérios preservados

São dez chamadas novas, zero aquisições e 400 s em relógio global, sem reinício
por operação; até 180 s por chamada e RSS 3,3 GiB. Usam os mesmos cinco crops
conhecidos de três vídeos de moda de treino, em I/S, S/I, I/S, S/I, I/S.
As dez chamadas antigas não usadas continuam encerradas. O consumo anterior
permanece em 1.835 reservas, 256 aquisições e 37.568,24201608001 s.

Concluir as dez respostas apesar de erros perceptivos; falha operacional,
JSON/ordem, identidade, recurso ou tempo encerra sem retry. Registrar contagens
brutas separadas de true com suporte, que exige `garment` e configuração
admissível congelada. Ganhos/perdas usam somente pares completos e denominadores
explícitos; parcial não vira cinco pares avaliados.

Nenhum resultado deste diagnóstico aprova candidata, atributo, auditoria ou
treino. Gates 12/12 negativos e 5/5 positivos intactos; v16 continua reprovada.
Partições 203/66/31, teste reservado, M1/A200 e integrações existentes permanecem
preservados, sem promoção. Reserva incerta histórica não é descontada.

O recibo completo sanitizado por campos de coordenação fica em
`data/private/issue-4-vlm-pos-v16-diagnostico-v1/final-preflight.json`;
identidades privadas dos casos e respostas não foram publicadas aqui.

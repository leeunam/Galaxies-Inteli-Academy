# Produto v9 — diagnóstico limitado e comparação em 41 casos

Execução de 20/10/2026, conforme o [adendo aprovado](issue-4-vlm-produto-v9-adendo-limitado-protocolo.md).
Concluíram **uma aquisição diagnóstica e 28 chamadas locais**, sem retries.
A nova comparação está selada em **41/64**, sem liberação de atributos,
nova auditoria cega, treino B-VLM ou promoção. Os relatórios anteriores continuam
intactos; as oito folhas permanecem preservadas, inclusive ao terminar.

## Diagnóstico do caso 42

A aquisição única concluiu em **4,4271 s**, com limpeza confirmada. O registro
`observed-properties.json` guardou os valores antes da comparação. As sete
propriedades atuais coincidem exatamente com as congeladas: política de frames,
duração, largura, altura, tempos amostrados, brilho e saturação. Não houve
diferença a registrar, inferência ou aprovação de identidade desse caso.

O SHA do novo download difere **tanto do run v9 antigo quanto do run falho da
recuperação**, vinculados por arquivo e fingerprint. Portanto, o diagnóstico
descreve o download atual; **não reconstrói a propriedade que divergiu antes e
não identifica a causa da falha passada**. Não se fez outro download para buscar
bytes específicos. Coincidência de propriedades não demonstra igualdade dos
pixels do caso 42, que continua fora das inferências e da comparação nova.

Decodificador: PyAV 16.1.0; libavutil 60.8.100, libavcodec 62.11.100,
libavformat 62.3.100, libavdevice 62.1.100, libavfilter 11.4.100,
libswscale 9.1.100 e libswresample 6.1.100. Versões e valores observados estão
nos recibos privados, sem alterar as propriedades antigas.

## Comparação pareada de produto

Os sete casos 35–41 usaram somente as folhas já existentes, quatro chamadas
por caso, com todos os hashes de crops e tempos idênticos aos caches congelados.
Não houve aquisição desses sete nem repetição dos 34 completos. A união reúne
32 casos antigos de desenvolvimento e nove já revelados, todos treino:
21 beleza/20 moda, 33 positivos/oito negativos. Não é um holdout novo.

| Produto / mesmos 41 | A/v7 | v8 | v9 |
| --- | ---: | ---: | ---: |
| Conhecidos / unknown | 41 / 0 | 41 / 0 | 41 / 0 |
| true / false previstos | 35 / 6 | 41 / 0 | 28 / 13 |
| Acertos de valor | 35 | 33 | 28 |
| Acertos de valor+frames | **33** | 29 | 27 |
| Evidência sem suporte, casos | 2 | 4 | 1 |
| Negativos corretos | 4 | 0 | 4 |
| Falsos positivos | 4 | 8 | 4 |
| Falsos negativos | 2 | 0 | 9 |

Nos sete novos, todos positivos de moda, v9 acerta **2/7**, contra **7/7** de
v8 e A/v7. Na união, v9 ganha oito e perde dez acertos compostos frente a v8
(saldo −2); ganha quatro e perde dez frente a A/v7 (saldo −6). Os nove falsos
negativos são de moda: suas 27 respostas nos primeiros 3 s são `incidental_only`.
Isso localiza o caminho da decisão false, sem estabelecer sua causa visual.

Por setor, acertos compostos de v9 são **16/21 beleza e 11/20 moda**, contra
12/21 e 17/20 de v8 e 16/21 e 17/20 de A/v7. No grupo antigo completo de 32,
v9 fica em **21/32**, v8 em 26/32, A/v7 em 27/32 e B/v7 em 25/32. B/v7 não
tem resultado para os nove revelados: não comparar seu total de 32 com 41.

Os controles estruturados herdados acertam 12/12, **todos negativos de produto**;
não medem sensibilidade aos produtos reais. O piloto herdado mantém 11/16.
Não foram repetidos controles ou piloto. Nos outros 25 avaliados, todos positivos,
v9 acerta 16/25; v8 e A/v7 acertam 22/25. O resultado atual não sustenta avançar
para outra auditoria cega. Antes de propor outra correção, revisar os nove falsos
negativos já revelados contra a rubrica original, sem mudar anotações para
acomodar a saída nem ajustar o gate. Nenhum retuning foi executado neste adendo.

Pessoa/texto continuam idênticos ao cache v8. Gates completos dos dois grupos
de 32 não foram calculados; `released_fields` e
`fields_ready_for_future_blind_audit` permanecem vazios.

## Consumo, preservação e verificação

| Contador | Novo | Cumulativo | Teto global preservado |
| --- | ---: | ---: | ---: |
| Aquisições | 1 | **256** | 277 |
| Reservas nativas | 28, todas completas | **1.666** | 1.758 |
| Tempo de sessões contabilizado | 300,6879 s | **34.792,3041 s** | 97.200 s |

As inferências contabilizaram 296,2608 s. O maior runtime nativo capturado foi
12,3636 s; o maior RSS amostrado foi **2.607,93 MiB**, abaixo de 3,3 GiB.
Todos os 28 raw/recibos foram preservados, sem falha, retry ou inferência externa.
Há **oito folhas íntegras**, zero sessões temporárias e zero workers ao terminar.
Não existe autorização para continuar nos casos 42–64 ou descartar essas folhas.

O commit `b44ea1c` congelou fontes/testes/protocolo separados. Passaram
**710 testes completos em 564,53 s**; após o ajuste pontual do detector para
ignorar o wrapper RTK ancestral, passaram **26 direcionados finais em 97,30 s**.
Ruff/formatação dos 125 arquivos e revisão independente passaram. O runtime,
bibliotecas e pesos instalados foram conferidos somente em leitura contra o
arquivo oficial em cache, sem extração, reinstalação ou consulta externa.

Os **588 hashes da pré-flight**, cinco fontes/testes/protocolo novos congelados
e versões instaladas conferem. O plano guarda 582 pins herdados; a conferência
final inclui também os seis arquivos adicionais de configuração/serviço e
componentes locais da #5. Permanecem iguais ambas as filas antigas,
partições 203/66/31, teste reservado, anotações, M1/A200, A300, B-cache,
serviço/MCP e lock. A fila nova bloqueia novas operações após a selagem.

Recibos privados: `data/private/issue-4-vlm-produto-v9-adendo-limitado-v1/`,
incluindo pré-flight, verificação de implementação, diagnóstico, 28 respostas,
comparação, análise pareada e análise dos estados dos falsos negativos.
Plano: `417e99a5ea07fd282181f2121786679fb63e2ffa91379f5855345a8514e88af2`.
SHA lógico da comparação:
`f36f74abb957fd93a4b8a0de059899ba157af6e441a3c34fbde82d758afd8aad`.
SHA do arquivo de comparação:
`55d58c4fd711ec6dbcb6bfa75321cee9d999ed11716cad55515255530af012ea`.
Checkpoint: `8ddccdc5847137bd9126286855d016ddae5717dd279706073d4fcd13c040fcee`.

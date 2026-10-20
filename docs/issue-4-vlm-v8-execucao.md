# VLM v8: controles e identidade das 64 entradas

Checkpoint histórico de preparação de 19/10/2026, seguindo o
[protocolo de desenvolvimento](issue-4-vlm-v8-desenvolvimento-protocolo.md).
A [comparação final](issue-4-vlm-v8-resultados.md) já concluiu os 64 casos,
com revisão e descarte das folhas. Nenhum atributo foi liberado. O texto
abaixo registra o estado anterior às inferências reais, sem seleção de outra
amostra cega ou treino B-VLM.

## Implementação verificada e congelada

A v8 usa uma pergunta por atributo/frame com JSON explícito, mantendo o parser
estrito, a agregação e os pesos v7. Só há uma versão nesta rodada. Os hashes
de fontes, prompts, controles e protocolo foram fixados antes da primeira
chamada. Fontes e recibos antigos permanecem preservados, sem alterações no
serviço/MCP ou M1. Os modelos não recebem views, títulos ou transcrições.

Passaram **567 testes completos** em 403,53 s e os 58 direcionados. Ruff e
formatação passaram nos 103 arquivos. A revisão independente conferiu a
identidade entre chamadas, o pareamento, os limites e a recuperação de
comparação/descarte após interrupção, sem repetir inferências. Commits:
`e3fbc65` (protocolo), `c99eae8` (extrator), `e923bdb` (fluxo e comparação).

Plano congelado:
`11f70036a059979a94eba997a4de4816df25bea28e25db33b63dcd05cb0f9c7d`.
Saídas detalhadas privadas: `data/private/issue-4-vlm-v8-desenvolvimento-64/`.

## Grade sintética

Os 12 controles concluíram 36 chamadas válidas, sem erro operacional, em
415,18 s. Houve oito imagens com ABC123 variando tamanho, contraste e posição,
e quatro negativos sem texto. Cada imagem passou pelas três perguntas.

| Campo | Acertos / 12 | true | false | unknown |
| --- | ---: | ---: | ---: | ---: |
| Pessoa | 12 | 0 | 12 | 0 |
| Produto | 0 | 5 | 0 | 7 |
| Texto | 5 | 2 | 3 | 7 |

Todos os controles são negativos de pessoa e produto: acertar pessoa neles
não demonstra reconhecimento de presença humana. Produto produziu cinco
falsos positivos e sete abstenções, um sinal de limitação que não deve ser
escondido. Texto acertou dois positivos de tamanho 48 na posição superior,
incluindo cinza; os textos pequenos e os grandes na posição inferior ficaram
unknown. Dos quatro negativos de texto, três foram false e o fundo preto ficou
unknown. Não são exemplos independentes de vídeo ou validação da percepção.

O protocolo prevê registrar erros perceptivos dos controles e concluir os 64
casos autorizados se o contrato operacional funcionar. Nenhum prompt foi
ajustado depois da grade; não foi criado outro candidato. Os PNGs sintéticos
temporários foram descartados, preservando receitas, hashes e respostas.

## Reaquisição e pareamento

As **64 folhas e 256 crops** foram reobtidos e conferidos contra v7, com
propriedades, tempos e hashes idênticos. Uma segunda passagem verificou cada
crop. São os mesmos 32 casos antigos e 32 da auditoria revelada, todos de
treino, com 16 por setor em cada grupo. Não houve substituição de caso,
renovação de observação pública ou seleção de novas evidências.

As 64 aquisições levaram 266,06 s, sem retry DNS ou falha. Somadas às 118
anteriores, são 182 frente ao teto cumulativo 192. Todos os vídeos foram
descartados por sessão. A identidade comprovada é dos PNGs/crops, sem afirmar
igualdade dos bytes dos contêineres reobtidos. As folhas ficam somente durante
avaliação e revisão; o protocolo exige descarte depois da comparação selada.

Os 99 arquivos protegidos conferem, e as partições continuam 203/66/31.
O teste reservado permanece fechado. A comparação prevista usava A/v7 em cache
nos mesmos 64, além de B/v7 em cache nos 32 antigos, para mostrar os dois grupos,
setores, suporte, cobertura e evidências, sem chamar desenvolvimento de auditoria
independente. Ambos os grupos têm somente dois negativos anotados de pessoa,
limitação que será mostrada junto ao gate original preservado.

# Recuperação nativa: duas fontes verificadas, sem inferência

Em 21/10/2026, após a exceção específica autorizada pelo usuário e a revisão
técnica vinculada, a [recuperação preparada](issue-4-vlm-fonte-nativa-preparacao.md)
concluiu **duas tentativas e dois frames verificados em 12,1893 s**.
As quatro sessões de download/ponte concluíram com retorno 0 e cleanup
confirmado. A fila está consumida e selada, sem retry ou reentrada.
**Nenhuma geração VLM ou chamada NIM foi feita.**

A [evidência sanitizada](evidence/issue-4-vlm-fonte-nativa-recuperacao-resultados.json)
conserva plano, configuração, revisão, recibo terminal, métricas dos jobs e
hashes dos dois PNGs. Não publica URLs, IDs dos vídeos, imagens ou caminhos
privados. Os mesmos dois casos de treino já revelados foram usados, sem
substituição, novos frames, métricas de alcance ou alteração de anotação.

| Resultado | Positivo | Negativo |
| --- | ---: | ---: |
| PTS nativo exato | 0,2 s | 2,8 s |
| Formato / dimensões | RGB 360×640 | RGB 360×640 |
| PNG retido | 153.757 bytes | 187.160 bytes |
| Download supervisionado | 2,9421 s | 4,8268 s |
| Ponte offline supervisionada | 1,3278 s | 2,2143 s |
| Propriedades históricas completas | iguais | iguais |
| Quatro PTS selecionados | iguais | iguais |
| Folha inteira / crop congelado por SHA-256 | iguais / iguais | iguais / iguais |

O frame nativo foi salvo somente após a ponte completa. O pai reconferiu
hash, modo, geometria e origem antes da cópia exclusiva para retenção.
"Nativo" designa o frame decodificado desta aquisição antes de thumbnail e
JPEG intermediário; não certifica pixels originais da câmera.

Os bytes dos dois contêineres diferem tanto dos originais quanto da recuperação
anterior. Isso foi registrado, sem alegar identidade nativa histórica; a folha,
os crops e tempos comprometidos foram reproduzidos exatamente. A nova fonte
permite preparar o contraste de informação, mas não demonstra melhora perceptiva.

## Recursos e preservação

- Duas tentativas de fonte, quatro jobs; não equivalem a duas conexões HTTP.
  Nenhum retry, fallback após falha, cookie, credencial ou API de métricas.
- Pico RSS amostrado de um job: **173,848 MiB**, abaixo de 3,3 GiB.
  Pico de workspace amostrado: **3.280.997 bytes**, abaixo de 128 MiB.
  Esses picos não são os tamanhos exatos das mídias, já removidas; o helper
  verificou o limite de 32 MiB por arquivo antes da ponte.
- stdout de rede 107 bytes e de ponte 518 bytes por job; stderr 0 nos quatro.
  Conteúdos brutos dos streams não foram publicados nem retidos pelo supervisor.
- Scratch próprio vazio após cleanup; **zero workers relevantes/modelos**
  na inspeção do host. Todos os quatro acks de recolhimento conferem.
- Quinze pins do candidato, 26 arquivos protegidos, oito PNGs antigos,
  quatro hashes de coortes/partições e quatro recibos NIM consumidos conferem.
  Teste reservado fechado, M1/A200, atributos e gates preservados.

Restam somente os dois PNGs novos e recibos privados para revisão até
**21/10/2026, 23h59 São Paulo**, com descarte explícito posterior, sem timer.
Os vídeos novos, partes e JPEGs temporários foram removidos somente após os
acks. As oito folhas antigas e os três inputs da demo, retidos até 23/10,
nunca foram alvos da limpeza.

O código permanece em `2817922`, com 36 testes offline aprovados; não houve
mudança de fonte ou repetição de testes nesta unidade operacional/documental.
O protocolo estático posterior acrescentado em `064b559` não alterou os 15 pins
nem o plano 349c…; isso foi conferido antes do despacho.

O [contraste de quatro células](issue-4-vlm-contraste-nativo-derivado-proposta.md)
**não foi executado nem liberado por esta recuperação**. Não há aprovação de
coluna, auditoria nova, treino B/C, promoção de modelo ou encerramento científico.

Plano: `349cfbfec2b1ffc4dce5727d608672fd9fb5f1ddd5019042445ab212be3eaedc`.
Configuração: `3f1a3672a211ceb247970601d50b833323c7ab56c66fc203eb26ef05113ce88f`.

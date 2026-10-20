# Issue #5 — resultado da única tentativa NIM sintética

Execução de 20/10/2026, após o [protocolo congelado](issue-5-nim-sintetico-unico-protocolo.md),
testes, revisão e commit `c0ef8ab`. O [grafo isolado](issue-5-stategraph-isolado.md)
foi commitado antes, em `3ee162e`. Houve **uma reserva, um despacho e uma chamada
real**, sem retry, reparo, fallback ou envio de dados privados. A autorização
foi consumida e não é um comando reutilizável de reprodução.

## Resultado observado

| Medida | Observação |
| --- | --- |
| Endpoint | POST `https://integrate.api.nvidia.com/v1/chat/completions` |
| Modelo solicitado | `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` |
| Conteúdo | Somente a fixture textual pública, inteiramente inventada |
| Status HTTP | **200** |
| Envelope do provedor | `reply_received`, término normal, sem ferramenta |
| Corpo HTTP recebido | **763 bytes**, abaixo de 16 KiB |
| Tokens de saída informados | **91**, abaixo de 2.048 |
| Tempo da tentativa no pai | **2,9134 s**, abaixo de 45 s |
| StateGraph/subgrafo | Executados com worker sintético no ambiente raiz |
| Seleção aceita pelo catálogo | **Não** (`selection_validated=false`) |
| Aderência qualitativa | `not_evaluated` |
| Retries/reparos/fallback | **0 / 0 / 0** |

O HTTP 200 demonstra comunicação e uma resposta de envelope válido neste caso;
**não demonstra aprovação da explicação**. O resultado final ficou sem seleção
validada. Nenhum fato livre do provedor foi publicado como explicação aceita.
Os recibos não guardaram `explanation.reason_code`: não se pode afirmar que
a resposta foi inadequada nem que a falha ocorreu dentro de `validate_selection`.

O corpo bruto e o texto da resposta não foram persistidos, conforme o protocolo.
Os recibos sanitizados não permitem distinguir uma falha anterior ao validador
de erro de formato, hash ou IDs dentro dele. A causa e o estágio detalhado
**não foram identificados**; não foi feita outra chamada para recuperar ou
corrigir esse conteúdo. O [diagnóstico offline](issue-5-nim-diagnostico-offline.md)
demonstra essa ambiguidade sem reconstruir a resposta histórica. O pedido limitava
a operação a uma tentativa, mesmo quando o contrato final falhasse.

Isso não valida português livre, reasoning, aderência ao brief, qualidade
preditiva, calibração ou desempenho geral do endpoint. O
[card oficial](https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-nano-omni-30b-a3b-reasoning)
declara suporte somente a inglês. O teste foi seleção de IDs sobre fatos
inventados, não avaliação linguística ou semântica independente.

O teto monetário autorizado foi **R$0**, usando o endpoint que a
[página oficial](https://build.nvidia.com/nvidia/nemotron-3-nano-omni-30b-a3b-reasoning)
informa como gratuito. Não houve configuração de faturamento, compra de créditos
ou aceite adicional de termos. Não foi consultado/medido saldo ou custo da conta;
o recibo não transforma o limite autorizado em medição financeira.

## Sequência e verificações

1. Implementação local do grafo/worker em ambiente próprio, sem tocar o lock ou
   pacotes da raiz;39 testes isolados finais e 11 direcionados da segunda unidade
   passaram, com Ruff/formatação de 143 arquivos e revisão independente.
2. Plano com **695 pins**, fixture e corpo HTTP congelados. SHA externo em
   `nim_seal.py`, versionado antes da operação, recusa plano alterado. Nonce
   efêmero por pipe, PID do pai e despacho exclusivo impedem retomada manual
   de reserva incerta. Nenhum token efêmero ou chave aparece em recibos.
3. **Uma execução completa da suíte raiz no código final `c0ef8ab`:748 testes
   passaram em 575,14 s**, sessão 87304, saída 0. A consulta Python inicial tinha
   namespace restrito; consulta do host confirmou o mesmo pytest PID138238.
   A sessão foi acompanhada até terminar, sem lançar suíte duplicada. O recibo
   foi gravado e os pins conferidos antes da chamada real.
4. Reserva durável antes de iniciar o filho; despacho durável antes de acessar
   a chave existente e tentar HTTPS. Captura limitada, resultado sanitizado e
   validação no worker. Nenhuma repetição após o resultado sem seleção validada.
5. Conferência final em leitura: **695 pins iguais**, selo externo igual,
   versões raiz e isoladas iguais, oito PNGs com hashes originais, zero sessões
   de mídia e zero workers NIM/VLM/explicação no namespace do host.

O resultado de 748 testes fecha a lacuna da suíte antiga: os 710 históricos
antecediam o último ajuste do detector e os 26 direcionados foram posteriores.
Os 39 testes do projeto isolado são separados da suíte raiz, não a substituem.
Após a tentativa, as fontes/protocolo/plano/fixture originais permaneceram
congelados. O commit posterior acrescenta um módulo de replay, seus testes e
documentação: não é somente documentação. A raiz permanece com 748 testes no
código `c0ef8ab`; após o diagnóstico, o projeto isolado passou em **45 testes**
e seis CLIs de replay independentes, sem rede. Não foi repetida a suíte raiz
porque seu código e suas dependências permaneceram iguais.

## Preservação e recibos

Sem nova mídia, inferência VLM, rótulo/evidência do teste, treino, promoção ou
publicação. Permanecem M1/A200, A300, B-cache, partições 203/66/31 e filas V9
seladas em 41/64. As oito folhas continuam preservadas; README não rastreado
não foi lido nem modificado. A #5 continua incompleta pelos motivos do
[estado de #3–#7](issue-3-a-7-estado-e-caminho-minimo.md); o resultado não muda
o recorte de #4 nem autoriza #6.

Fila privada: `data/private/issue-5-nim-sintetico-unico-v1/`, com pré-flight,
plano, revisão/verificação local, auditoria de processos, suíte completa,
reserva, despacho, resultado sanitizado, resultado do grafo e conferência final.
Hashes dos principais vínculos:

- Plano: `2e673c9c189c39a899c34df54ed5443b24d23c5e3dc78e5c3e48030d98ed7fd9`.
- Fixture: `0fb7b9797cd41f53c3f127b0d2f6f934d0696aa3ba288852f5cff616455cf438`.
- Reserva: `6a0f7604c5504d81ed9a0bfbb01e1b0269962ed2f91631f4d68a2b9f2b1262ea`.
- Despacho: `d6d444eb2ec73bd762ca140921ed581d83e24a75bbd7108b03c27803bad82b63`.
- Resultado HTTP: `c6acc734b8e5d49ce327b70a5c783e4d353f7c63b3ee4747772ff2265d450b72`.
- Resultado do grafo: `7f03d368bdca9f4f8bad376c66ccb19ec730aca4daec17099d37bc603d7a1802`.

Não executar novamente o comando de envio. Qualquer nova rodada exige desenho,
conteúdo e orçamento específicos; o teste reservado e a fila V9 não entram nela.

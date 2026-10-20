# Produto v15 — gramática aprovada, controles reprovados

Execução de 20/10/2026 do [protocolo v15](issue-4-vlm-v15-protocolo.md),
conforme a [proposta pós-v14](issue-4-vlm-pos-v14-investigacao-e-proposta.md).
A implementação corresponde ao rascunho aprovado e passou no gate nativo.
Na avaliação real, **os 12 controles retornaram true: 0/12 false corretos**.
O executor concluiu o bloco e selou a fila em **`v15_controls_quality_failed`**,
com **12 chamadas válidas e zero aquisições**. Os oito vídeos não foram
processados; as 32 chamadas restantes ficaram encerradas, sem reaproveitamento.

Nenhuma auditoria cega, revisão formal de vídeos, treino B/C, liberação de
colunas ou promoção do M1. A v15 permanece reprovada para avançar. Aprovação
formal da gramática não demonstra reconhecimento visual de um item.

## Implementação e verificações anteriores à geração

- `c19440f`: configuração nativa, projeção explícita, decoder, gramática,
  testes e protocolo.
- `37745a2`: fila limitada aos controles e oito folhas preservadas, reservas,
  linhagem, comparação e revisão vinculada à configuração nativa.

Saída nativa com `item_configuration`, `state`, `presented_categories`:
dez configurações e 22 objetos permitidos, dos quais 19 positivos. A projeção
cobre os 16 objetos semânticos anteriores, preservando mapper, unknown, OR e
janela de produto ≤3 s. Raw e configuração nativa ficam separados da pista
projetada. A origem registrada é
`derived_from_model_declared_item_configuration_not_independent_verification`;
a pista derivada não é observação visual independente nem certificação.

Prompt, schema e projeção correspondem integralmente ao rascunho aprovado,
inclusive aos três hashes publicados no protocolo. Não houve reparo de raw,
recorte de listas antigas, correção por GT ou retuning depois dos resultados.
O executor não possui caminho de aquisição; diretórios/reservas/contadores
correspondentes são recusados. A revisão, se alcançada, vincularia inclusive
configurações distintas que projetam a mesma pista, além de categoria, pixels,
tempo, resultado, plano, origem e hash da projeção.

**80 testes direcionados passaram em 44,63 s**. No código final `37745a2`, a
verificação completa cobriu **1.195 testes aprovados em dois segmentos sem
sobreposição**. A primeira sessão concluiu 96 e ficou esperando no teste MCP
por stdio dentro do isolamento. Foi encerrada explicitamente com SIGTERM;
seu código -15 e log foram preservados, sem apresentá-la como suíte aprovada.
A continuação selecionou exatamente os 1.099 restantes, fora desse isolamento,
e passou em **843,25 s**. Não houve duas suítes concorrentes nem repetição do
prefixo concluído. Uma tentativa de lançar a lista por argv excedeu o tamanho
permitido e não iniciou testes; a continuação usou arquivo de argumentos.

Ruff e formatação dos **196 arquivos Python rastreados** passaram. Nenhuma
fonte mudou depois desses testes. Plano preparado com contador zero; a
primeira chamada foi despachada somente após o registro da cobertura completa.
A revisão das mudanças foi local; não se alega revisão independente.

## Gramática nativa e limite de saída

Ponte C++ v13 imutável, compilada somente como ponte contra as bibliotecas
b11716 instaladas, com os nove cabeçalhos oficiais já conferidos em cache.
Conversão `json_schema_to_grammar(..., false)` e aceitação por caracteres com
término completo; sem modelo ou forward pass nesse gate, sem instalação,
download, extração ou troca de runtime/pesos.

O preflight final passou em **13.681 sondas, zero divergências**: 13.640 objetos
do domínio finito (22 aceitos), 22 variações de whitespace entre campos e 19
mutações brutas. Rejeita incoerência entre configuração/estado/categoria,
campos extras/ausentes, duplicatas, truncamento, conteúdo extra e ordem de
chaves indevida. A gramática fixa a ordem; o decoder semântico valida objetos.

O primeiro preflight falhou em 19 versões com arrays positivos indentados.
O conversor representa arrays enumerados como literais, sem whitespace interno.
Esse diagnóstico foi preservado; ajustaram-se somente as sondas de whitespace
ao formato nativo, sem alterar prompt, schema ou projeção. O recibo final é de
`native-preflight-final-v2`, anterior à inferência, e foi conferido nas reservas
e após o encerramento. Fontes, bibliotecas, headers, compilador, ponte,
gramática, sondas e respostas estão vinculados por hash.

O tokenizador instalado, offline e sem geração, verificou os 22 objetos em
formato compacto e com whitespace entre campos: **44 serializações, 17–32
tokens JSON**, máximo 33 com reserva de término, dentro do limite64. Whitespace
arbitrário não é garantido. As 12 respostas reais foram aceitas integralmente,
sem reparo, truncamento ou aumento do limite.

## Resultado dos mesmos controles

| Versão / mesmos 12 controles | false correto | true | unknown |
| --- | ---: | ---: | ---: |
| **v15** | **0/12** | **12** | **0** |
| v14 em cache | 12/12 | 0 | 0 |
| v13-R em cache | 12/12 | 0 | 0 |
| v11 em cache | 1/12 | 11 | 0 |

**Zero ganhos/12 perdas** frente a v14 e v13-R; zero ganhos/uma perda frente
à v11. Comparação somente por hashes e tempos idênticos. V12 continua com
zero resultados aceitos e não entra como taxa de acerto.

As 12 declarações nativas foram `presented_target`, todas projetadas para
`isolated_display` e booleano true, conforme o contrato:

| Configuração nativa | garment | cosmetic | Total |
| --- | ---: | ---: | ---: |
| isolated_physical_item | 6 | 1 | 7 |
| isolated_graphic_item | 0 | 5 | 5 |
| **Total** | **6** | **6** | **12** |

Inclui garment isolado nos controles inteiramente branco e preto. São fixtures
negativas sem item alvo; textos, linhas e formas também não demonstram os
produtos declarados. A projeção foi reconstruída a partir dos raws e não
introduziu o erro: a alucinação já está na configuração/categoria nativa.
A gramática permite os três objetos não positivos; não força essa escolha
positiva. Este contraste muda prompt e representação juntos e não determina
qual componente causou a regressão. Não houve chamada exploratória adicional.

## Gates e escopo não executado

O gate exige 12/12 false, por isso nenhum vídeo foi processado. Não há medida
v15 de 8/8 valor+frames, suporte de configuração, pessoa/texto combinado ou
comparação de vídeos com v14/v13/v10/v9/v8/v7. Os denominadores de vídeos são
zero, **não 0/8 acertos**. As ambiguidades dos dois casos de blusa, o GT legado
e a inspeção congelada anterior à v11 permanecem intactos.

A revisão formal de todas as configurações positivas dos oito vídeos não foi
alcançada; não existe recibo de revisão de fase1. O campo agregado de gate
false significa que o avanço foi bloqueado, sem inventar uma revisão feita.
A fila selada recusou reentrada sem despachar chamada ou alterar o checkpoint.
Não se autoriza outra rodada, aquisição, auditoria ou treino por saldo restante.

## Consumo e preservação

| Contador | Novo | Cumulativo | Teto desta autorização |
| --- | ---: | ---: | ---: |
| Reservas nativas | **12**, todas completas/válidas | **1.811** | 1.843 |
| Aquisições | **0** | **256** | 256 |
| Sessões cobradas | **257,5496 s** | **37.044,3074 s** | 37.986,7579 s |

Zero falhas operacionais, retry, reparos ou tentativas novas incertas. As
chamadas somam **253,8874 s** de runtime nativo, máximo **21,7490 s**, pico
RSS **2.609,75 MiB**, abaixo de3,3 GiB. Mesmo Qwen3-VL-2B Q4_K_M, projetorQ8_0,
b11716, CPU4, seed42, temperatura0, saída64 e limites visuais solicitados64/128.
As reservas e 180 s da tentativa incerta v13 continuam consumidos, sem retry.
Suíte, tokenizer e preflight sem geração não contam como chamadas nativas.

Conferem **1.270 arquivos protegidos, 1.271 pins do plano e dez fontes**.
As oito folhas originais continuam presentes; os **32 crops** foram
reproduzidos em memória antes/depois, com hashes/tempos iguais. Doze controles
idênticos; nenhum vídeo, mídia ou folha nova. Temporários removidos, nenhum
worker restante e nenhum diretório de aquisição. Não foi necessário descarte
de folhas novas; as antigas nunca foram alvo de remoção ou edição.

Ambientes raiz130/isolado42 distribuições iguais; locks/dependências intactos.
Runtime e pesos reconferidos em leitura contra o arquivo oficial em cache.
Partições **203 treino /66 validação /31 teste**, sob guardas das coortes200/300.
Teste reservado sem leitura de features, rótulos, previsões ou métricas.
M1/A200 e seus três modelos, A300, B-cache, serviço Python/MCP e filas anteriores
intactos. Hash canônico do M1 confirmado pelo contrato próprio do artefato.
README não rastreado e briefing protegido não foram editados ou incluídos.
Sem NIM, acesso externo, envio de mídia, push ou deploy.

Recibos privados em `data/private/issue-4-vlm-v15-v1/` e
`data/private/issue-4-vlm-v15-verificacao-v1/`: antes/depois, pixels, ambiente,
preflights, tokenizer, logs/cobertura dos testes, plano congelado, raws,
reservas, reconstrução, comparação e recusa terminal.

- Plano lógico: `a3b9e8cbb6ba3f160ff382780d92ef965effc09d222b17129890cf26ba1a407e`.
- Configuração: `14f78d6f68b9b3d6ac456d4ff3822ce7969d3ae95429f659f44f022163256d93`.
- Gramática: `5ef403f14df75c08396d9280dee3a49ac1b1aec7b536a316a140172623fb35e6`.
- Recibo nativo lógico: `5cfef3c906857830c1e96edef4881068edb19d05c72b70a2efcb3aff47e345f5`.
- Comparação lógica: `c7fac9993a21ccd52cb72d4c25aee61f0acdd7a51f8cf60e939b49ad2673d0cb`.
- M1 preservado: `9dd1c7a2e35e32cf3068395ed8bf2e0561aa4fecded5c31754f981cc13d70d59`.

# Frente 1 — decisão técnica e validação visual controlada

Base: `277804223eb6121dbeb541c0663af89ccf334eac`. Entrega desta unidade:
**plano e rubrica, sem execução de sonda, modelo ou auditoria**. Nenhum caso foi
selecionado, nenhuma imagem/anotação nova foi aberta e nenhum atributo foi
liberado. A principal, a demo e seus recibos não foram alterados.

O objetivo é separar duas perguntas: por que a execução demora e se a resposta
é sustentada pelos pixels. Concluir o encoder não aprova percepção; um acerto
semântico não explica desempenho. Não há promessa de encerrar ambas até
00h36 UTC de 22/10/2026, limite operacional desta preparação.

## Evidência e perguntas que discriminam hipóteses

| Frente | Evidência disponível | Pergunta / consequência permitida |
| --- | --- | --- |
| Threads e parser | Auditoria estática não demonstrou defeito; `encoder_start` não é duração concluída | Não corrigir threads/parser sem discrepância demonstrada |
| Recursos | Probe consumido: 278 amostras, sem `encoder_done`, timeout e nenhuma resposta | Não atribuir toda a duração ao encoder ou ao escopo compartilhado |
| Seleção CPU | Fonte enumera variantes, compara score com `>` e carrega a escolhida | Sonda CPU-only observa seleção atual; não reconstitui backend histórico nem mede encoder |
| Representação | Sete casos sintéticos/19 invariantes passaram em RGB, resize e padding | Conferir dispatch, normalização e patches/merger antes de inferir defeito de pixels |
| Gramática | Negativo respondeu `yes` com e sem gramática | Não repetir retirada da gramática como correção sustentada |
| Densidade | Negativo seguiu `yes` com 1.056 tokens; rodada nativa posterior expirou | Mais tokens/prazo não são correções demonstradas; não repetir comando idêntico |

As sete fontes textuais oficiais já obtidas são da revisão `797de63b2`.
Nesta unidade foram lidas regiões necessárias e calculados seus hashes,
sem carregar bibliotecas. O controle `mtmd-cli.cpp` coincide com
`72c9163dcc2e0e491c74b6b0ee15406765e6e4c1b868ea1d3e73c2a87c9369d3`.
Há agora declaração pública `void ggml_backend_load_all_from_path(const char *)`
em `ggml-backend.h:262`. `ggml-backend-reg.cpp:480–599` mostra busca, score,
famílias adicionais e `GGML_BACKEND_PATH`. Isso fecha a ausência de declaração
na fonte recebida; não prova equivalência de build/ABI do binário instalado,
segurança dos inicializadores ou confinamento da sonda.

`mtmd-helper.cpp:404–408` solicita três canais ao decoder e cria o bitmap;
`mtmd.cpp:741–751` encaminha Qwen3VL ao preprocessor dinâmico. `clip.cpp:1442–1451`
lê mean/std dos metadados; `6336–6344` inclui caminhos deepstack na dimensão de
saída Qwen3VL. São relações de fonte, sem decoder, tensores ou pesos executados.
A frente de representação deve fechar correspondência com metadados locais e
fontes complementares; não duplicar essa inspeção aqui.

Hashes das sete fontes recebidas e conferidas nesta leitura:

| Arquivo | SHA-256 |
| --- | --- |
| `mtmd-cli.cpp` | `72c9163dcc2e0e491c74b6b0ee15406765e6e4c1b868ea1d3e73c2a87c9369d3` |
| `ggml-backend.h` | `0e5e8e1f16d11ebbf501e38bc6705d79eee819b5f0b17476533f2100ed9674e2` |
| `ggml-backend-reg.cpp` | `1436b46bd1e8355345d454baa4b40069be73e9cb09a3a188d32426ea1e1037fe` |
| `ggml-cpu.cpp` | `ccf382d3fbf126b5ddb5850a0a970656fb24e00587da4003419439277c91cd01` |
| `mtmd.cpp` | `4ea82d48fad89cd45133ce5f966539d926e1e9dacccd1d708f921c0bc4c5ee06` |
| `clip.cpp` | `391dd74bd078a8ab2358e22bbb8b53c259e76dcd460450834640256e2e457798` |
| `mtmd-helper.cpp` | `fd24441c391d1d8669bc865c27fc64ee76ffdec0f0df9737ed3a1097a9ee2f08` |

## Sequência com parada entre etapas

**0. Revisões sem inferência.** A sonda CPU-only é responsabilidade da frente
runtime; representação/metadados têm outro executor já designado. Este plano
não cria outra sonda nem altera seus clones. Receber commits, hashes,
allowlists, limites e parecer independente dessas entregas. Resolver lacunas
de fonte/binário e inicializadores antes de carregar bibliotecas.

**1. Seleção CPU, após revisar a sonda.** Uma execução de helper sem modelo,
tensores ou graph compute responderia qual variante o loader escolhe na visão
CPU permitida. Propor teto externo de 20 s, zero chamadas de modelo e R$0.
Limites de CPU/memória, argv e cleanup devem constar do plano final do executor
antes da execução; não estão implementados por este documento. Se o helper
não atender ao teto ou confinamento, não lançar. Um basename mapeado não basta:
exigir vínculo entre registro selecionado, biblioteca permitida e regra de
score. Seleção esperada elimina apenas essa hipótese; falha da sonda não é
falha de percepção. Não executar encoder para completar uma sonda inconclusiva.

**2. Decisão de candidata.** Só propor inferência nova se houver mudança
discriminante registrada: correção de discrepância comprovada de runtime ou
representação, ou candidata de percepção com hipótese própria e contrato
revisável. Registrar antes/depois, mecanismo esperado e o que o refutaria.
Não fixar outra CPU arbitrariamente, reduzir tokens perdendo detalhe relevante,
aumentar timeout, trocar modelo ou reapresentar prompt antigo como correção.
Se não houver discrepância, manter causa desconhecida e encerrar sem chamadas;
outra candidata exigirá desenho próprio. Incapacidade do modelo não é um
diagnóstico estabelecido por exclusão.

**3. Triagem após correção de runtime/representação.** Após congelar essa
correção justificada, propor até **14 chamadas / zero aquisições / 1.200 s / R$0**:
os mesmos 12 controles negativos de produto, em ordem congelada, seguidos do
crop negativo e do positivo conhecidos do contraste de percepção. Não repetir
os braços com/sem gramática ou nativo/derivado. Só a mudança da etapa 2
justificaria essa execução. Nos 12 controles, manter o contrato de produto;
nos dois crops, manter a pergunta diagnóstica de relação visível e seus
esperados `no`/`yes`. Esse predicado não é a anotação da coluna produto: não
transpor seus esperados ou acertos para o booleano de produto. Uma mudança
somente de prompt de produto não justifica repetir o diagnóstico relacional
inalterado; exige outro desenho. Vincular antes do lançamento hashes privados,
pixels, tempos, perguntas e esperados; não foram recuperados ou escolhidos aqui.

Exigir 12/12 controles `false` no contrato de produto e duas decisões
relacionais corretas com suporte nos crops. Reportar os blocos separadamente;
`unknown`/`uncertain` não é acerto. Parar no primeiro erro perceptivo,
falha técnica, identidade divergente ou limpeza incerta; sem repetição, reparo,
substituição ou retomada de reserva incerta. Propor até 75 s úteis + 5 s de
término por dispatch, RSS cooperativo de 3,3 GiB e executor único; não alegar
cgroup exclusivo ou teto físico de RAM. Os 1.200 s incluem preflight/fechamento;
saldo antigo consumido não é reutilizável.

Essa triagem é desenvolvimento, não o gate original ou prova dos 64 revelados.
Não libera produto, pessoa ou texto. Outras configurações ficam fixadas por
campo; aprovação não pode ser importada de respostas em cache para casos novos.

**4. Auditoria independente, em execução separada.** Somente após revisar a
triagem e congelar o extrator inteiro, aplicar a
[rubrica de seleção e gate](issue-4-front1-blind-audit-rubric-v1.md).
Não selecionar casos cegos para depois usá-los no desenvolvimento. Treino B/C,
avaliação de validação e promoção do M1 ficam fora desta frente.

## Dados, destinos e orçamento de decisão

| Etapa futura | Dados / destino novo proposto | Teto e condição |
| --- | --- | --- |
| Sonda CPU-only | Bibliotecas/fontes fixadas; `data/private/issue-4-front1-cpu-selection-v1/` | 1 helper, 20 s externos, 0 chamadas de modelo, R$0; confinamento final pendente |
| Triagem | 12 controles de produto + 2 crops relacionais revelados; `data/private/issue-4-front1-corrected-pilot-v1/` | 14 chamadas, 0 aquisições, 1.200 s globais, R$0; correção discriminante do caminho obrigatória |
| Auditoria | 32 referências do treino da base 300; `data/private/issue-4-front1-blind-audit-v1/` | Até 384 chamadas: 32 × até 4 frames × 3 atributos; R$0; plano privado e execução próprios |

384 é envelope, não autorização para escolher estratégia após ver respostas.
Congelar antes o número exato de chamadas e instruções por atributo. Contrato
conjunto permitiria até 128, mas seria outra candidata, sem equivalência
presumida. Ambiente/formato, close-up/aplicação seguem fora desta revisão.

Se a auditoria futura precisar recuperar mídia, limitar a 32 referências do
treino existente, uma tentativa por ID, até 180 s cada; sem novas linhas,
views atualizadas ou substituição. Exigir propriedades, pixels e tempos
congelados; sem evidência reproduzível, registrar insuficiência e parar.
Aquisição não está autorizada nesta unidade. Somar ao ledger anterior com
hashes/reservas duráveis, sem reiniciar contadores ou as 27 h históricas.

Só 384 chamadas × 80 s + 32 aquisições × 180 s somam **36.480 s (10 h 08 min)**,
sem anotação/preparação. Não prometer a auditoria inteira na hora restante.
O saldo cumulativo não foi reaberto nem calculado aqui; sem saldo, não lançar.

## Revisão e preservação

Revisor independente lê fonte, argv/configuração e prova de isolamento antes
da sonda; depois confere vínculo entre saída e conclusão. Antes da triagem,
revisa candidata, pins/esperados, ledger e paradas. Antes da auditoria, verifica
cegamento, seleção, anotações seladas e exclusões sem alcance. Depois reproduz
o gate dos registros selados, sem rerun do modelo. Falha mantém reprovação.

Destinos devem ser novos e privados, recusados se existentes. Conservar raw,
hashes, contagem e estado terminal antes de remover temporários. Não modificar
filas antigas ou estender retenção automaticamente. Expiração impede uso, sem
autorizar reaquisição ou limpeza nesta unidade. O marco desta hora é parecer
técnico com defeitos demonstrados ou lacunas explícitas e plano revisável.
Partições 203/66/31, teste fechado, M1/A200, A300/B-cache, guia/cartão da demo e
evidências anteriores ficam preservados. Aprovação depende do gate, não do prazo.

Referências: [runtime](issue-4-vlm-runtime-audit-v1.md),
[representação](issue-4-vlm-representacao-offline-v1.md),
[probe consumido](issue-4-vlm-resource-probe-resultados.md),
[gramática nesse par](issue-4-vlm-percepcao-gramatica-resultados.md),
[revisão original](issue-4-vlm-revisao-perceptiva-protocolo.md) e
[B-VLM](issue-4-experimento-b-vlm-protocolo.md).

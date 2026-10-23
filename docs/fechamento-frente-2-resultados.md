# Frente 2 — entrega implementada e limites de aceite

23/10/2026. A unidade offline foi implementada e validada. **A Frente 2 e o
projeto ainda não estão concluídos:** falta a configuração aprovada da Frente 1,
briefing real com conteúdo correspondente e seleção NIM sobre pacote real permitido.
A chamada histórica aceita e um catálogo legível não fecham esses aceites.

## Código e configuração

Branch `codex/frente-2-explicacao-integracao`, clone independente. Base auditada
`3586bcab7aa3f7bf165f1ac17ced91bb85358043`; HEAD observado no início `a9bdc17`.
As mudanças posteriores foram conferidas antes da implementação: comparação
B/C completos, identidade/proveniência de SHAP e diagnósticos visuais. Esses
componentes não liberaram atributos nem escolheram a configuração final.
O coordenador confirmou o STOP visual v4-r2 no primeiro caso por `unknown`,
sem QualityRelease, sidecars completos ou B/C finais selecionados.

Commits próprios de implementação:

- `f5cfbb7`: contrato, rubrica prévia e limites.
- `f5adb9f`: vínculo briefing/conteúdo e suficiência do catálogo; 28 testes iniciais.
- `b30d1f4`: mesma revisão por Python/MCP, exemplo público, apresentação dos sinais
  e recibos de proveniência; seleção direcionada final com 48 testes.

O Chat 3 revisou e integrou esses três commits como `0e6d0cf`, `7a57b27` e
`eecc535`; somente ele alterou a árvore principal. Esta entrega adicional inclui
o revisor reproduzível do arquivo histórico e o resultado qualitativo abaixo.
Não foram editadas fontes pinadas, modelos, partições, locks ou `.env`.

Os [contratos e comandos](fechamento-frente-2-contrato-e-rubrica.md) documentam
`CampaignCase`, `ReviewSettings`, `ReviewedResponse` e a tool optativa
`analyze_creatives_reviewed`. A resposta conserva os objetos numéricos integrais,
mais texto apresentado, hashes, cobertura, aderência por requisito e fases
reportadas. Fonte com pacote/claim alterado é recusada pela revisão. Observações
descritivas de campanha não viram entradas do preditor.

## Evidências separadas por proveniência

| Material | Execução efetivamente coberta | Não demonstra |
| --- | --- | --- |
| Par real histórico v6 | Mídia, extração nativa, M1/A200, SHAP, comparáveis, grafo e paridade Python/MCP em três peças | Novo modelo final, seleção NVIDIA ou aderência de campanha |
| Fluxo real cacheado de 23/10 | Features preservadas → previsão/faixa/ranking → SHAP → 124 referências de treino indexadas → comparáveis → pacote/texto local | Nova extração, validação de mídia, MCP, StateGraph ou chamada externa nessa execução |
| NIM histórico aceito | Uma chamada externa com números inventados; 12 claims iguais ao catálogo | Qualidade em mídia real ou aderência; cobertura parcial permanece registrada |
| Desenvolvimento desta frente | Casos inventados com briefing identificável e conteúdo correspondente, Python/MCP em memória e stdio reais com grafo simulado | Verdade perceptiva, desempenho preditivo, briefing real ou nova chamada NIM |
| Revisão atual do arquivo real | Leitura dos recibos, JSON e textos preservados; conferência de hashes, vínculos, números e cobertura; nova apresentação local | Reexecução de features/modelos ou nova avaliação científica |

Os 114 checks agregados e os 22 testes posteriores são recibos diferentes, com
sobreposição. Não são 136 cenários únicos. Os 48 testes desta entrega incluem
os 28 iniciais e não devem ser somados a eles como testes novos independentes.

## Revisão qualitativa do texto real efetivamente apresentado

Foram lidos o JSON real cacheado, seu texto corrigido preservado e o texto
aditivo produzido nesta frente. A identidade do recibo é
`06664bbcefe66450e7704bc1510fe012baa11877d0a4809bbc8b5155b9227b67`;
a do fechamento histórico é
`a2b2f60da177696f8a754b7e6b880964fd1f992a7e34e8660c9b53c947a279dd`.
O script histórico, JSON, texto original e texto corrigido foram ligados aos
hashes desses recibos. O script histórico **não foi executado**. Nenhum ponteiro
para features, runs, mídia ou rótulos foi seguido para refazer a previsão.

A fonte contém três candidatos de beleza e 30 fatos: três limites, três
previsões, três faixas, 12 grupos SHAP e nove referências do treino. O texto
corrigido mostra catálogo completo e mantém a seleção como indisponível.
A ordem por mediana é C2 → C3 → C1, usando aqui somente aliases de apresentação.
Nenhum nome de publicação, transcrição, URL ou caminho privado foi copiado
para este relatório público.

| Dimensão | Resultado da revisão assistida, limitado a esses três candidatos |
| --- | --- |
| Fidelidade | Números, faixas, ranking e fonte integral permaneceram iguais; grupos do pacote reconstruíram as medianas na escala log1p. A transformação inversa foi descrita corretamente, sem somar contribuições diretamente em views |
| Suporte | O texto do catálogo corresponde aos fatos vinculados; a nova leitura dos sinais cita os mesmos IDs. Não foram inventados temas, frases, emoções ou significado de dimensões do embedding |
| Suficiência | Seleção ausente: 0/12 grupos e 0/9 referências, reprovada. Catálogo local completo: 12/12 e 9/9, suficiente na rubrica para expor fundamentos da comparação exploratória. Isso não aprova um seletor NIM ausente |
| Utilidade comparativa | O leitor consegue identificar a prioridade por q50. C1 tem associações negativas maiores, principalmente no grupo da fala; C2 tem os dois grupos não nulos positivos e C3 os dois negativos, em relação à mesma base. Isso explica o cálculo sem identificar por que uma frase ou tema teria causado alcance |
| Faixas e limites | As faixas são amplas e se sobrepõem; o texto informa cobertura não validada e não deduz chance de vitória. Ranking é prioridade exploratória, sem superioridade, causalidade ou retorno pago demonstrados |
| Clareza | A nova seção resume os principais sinais em português e separa seleção/catálogo. A leitura completa continua longa, com muita precisão numérica, IDs e termos técnicos. Clareza para produtores permanece parcialmente avaliada; não houve painel humano ou teste de compreensão |
| Aderência | **Não avaliada.** O recibo declara contexto diagnóstico, não briefing de campanha. Features numéricas e comparáveis não substituem evidência de conteúdo correspondente aos requisitos de uma campanha |
| Origem | O português foi escrito localmente. Nenhuma prosa livre NVIDIA foi exigida; nenhum HTTP200 ou fixture repetida foi tratado como aceite qualitativo real |

A decisão de suficiência não exige selecionar o catálogo inteiro. Um subconjunto
inventado com os maiores grupos de cada sinal e uma referência por candidato
passa na rubrica; o exemplo histórico de 12 claims falha por omitir os
fundamentos relevantes em dois candidatos. Essa demonstração de contrato não
prova que o provedor escolherá bem em dados diferentes.

A rubrica é exigente por candidato: em cinco candidatos com sinais mistos,
os fundamentos e uma referência por peça podem ultrapassar o limite histórico
de 12 IDs remotos. Essa situação deve permanecer uma reprovação visível da
seleção, ou usar apresentação local explicitamente identificada e avaliada
separadamente. Não ampliar o limite pinado ou alegar que a seleção remota
cobriu o que apenas o catálogo apresentou. O teste 1/3/5 confirma contratos e
transporte; não encerra qualidade NIM nesses três volumes.

A revisão atual levou 0,422 s, uma CPU e pico de filhos de 114.860 KiB, sem
modelos/extração/rede. O histórico de features levou 0,310 s; são fases e
medições diferentes. Recibos atuais incluem hashes da fonte e do código do
revisor. O coordenador conferiu a integração no shell da principal: **79 testes em
7,22 s** (31 P6 + 48 desta frente), sem falhas ou skips. A rodada sob launcher
supervisionado falhou no primeiro stdio e permanece registrada; os 79 não
são cenários novos adicionais aos 48.

Nenhum número privado individual precisa ser divulgado para conferir
o estado de aceite no [agregado público](evidence/front2-explanation-handoff-v1.json).

## Recibo e comandos reproduzíveis

O revisor abre somente seis arquivos nominais do arquivo histórico, confere
suas identidades e escreve derivados em destino novo. Não executa o script
arquivado e não segue referências para o conjunto de dados.

```sh
rtk proxy .venv/bin/python -B -m scripts.verify_front2_recorded_v1 \
  --archive /arquivo-local-autorizado/closing \
  --output /destino-local-novo/revisao-frente-2
```

O caminho acima é um placeholder de configuração do operador, não uma fonte
pública para download. Na ausência do arquivo autorizado, usar o exemplo
público sem chave ou mídia:

```sh
rtk proxy .venv/bin/python -B -m scripts.explanation_review_mcp_v1 --public-example --format text
```

Resultados novos foram preservados em
`data/private/fechamento-20261023/frente-2/`, em namespace próprio. Os recibos
separam: fixtures, transporte real com números simulados, arquivo real apenas
revisado e fases históricas iniciadas por mídia. Há hashes e JUnit, inclusive
de falhas e timeouts; fontes antigas não foram sobrescritas. Foram preservados
37 arquivos novos no namespace privado `frente-2/release-v1`, com manifesto
SHA-256 `dd12164b980a68c3a4664589b2c4244edda40ce4761f9e8fb6571ccce28484e4`
e todos os hashes de destino conferidos. Nenhum arquivo histórico integral,
peso, mídia, transcrição ou `.env` foi copiado. O exemplo público
é inventado e deixa contradições e evidência insuficiente visíveis.

## Matriz exata de conclusão

| Critério da rubrica | Estado desta entrega | Lacuna que permanece |
| --- | --- | --- |
| F2-01 Fidelidade | Verificado no M1 histórico, nos objetos reais preservados e nos testes novos | Repetir somente os vínculos que mudarem com o handoff final |
| F2-02 Suporte | Vínculos de catálogo e conteúdo implementados/testados; fonte real preservada revisada | Verdade de conteúdo e suporte de campanha real ainda sem pacote correspondente |
| F2-03 Suficiência | Rubrica executável, reprovações e cobertura registradas | Seleção NIM sobre pacote real e configuração final não avaliada; limite de 12 em cinco casos deve ser respeitado |
| F2-04 Clareza | Leitura qualitativa dos textos reais e novo exemplo concluída | Compreensão por produtores não testada; densidade e jargão permanecem limites |
| F2-05 Limites | Avisos, origem, escala e distinção preditivo/descritivo preservados | Não converter esses avisos em validação científica |
| F2-06 Aderência | Contrato, casos de desenvolvimento inventados, conflitos e insuficiência implementados | Briefing real permitido e conteúdo correspondente faltam; aderência real não avaliada |
| F2-07 Integração | Adaptador Python/MCP aditivo implementado; v6 reutilizado nas fases cobertas | Recibo de configuração final e NIM real permitido pendentes |
| F2-08 Operação | 48 testes de 1/3/5, IDs, empates, falhas, timeout e preservação; stdio em shell aprovado | Inicialização sob launcher supervisionado, inclusive com ambiente herdado, falha sem causa isolada; não foi transformada em skip |
| F2-09 Configuração final | Gate explícito, sem promoção indevida de A200 ou VLM | Handoff aprovado da Frente 1 ainda inexistente |
| F2-10 Reprodução/privacidade | Comandos, fixture segura, agregados e recibos persistentes concluídos | Integração/publicação e avaliação final pertencem ao Chat 3 |

## Único pacote remoto proposto, inerte

Não há autorização nova de chamada. A configuração final e um briefing real
permitido ainda faltam, portanto **não há payload pronto para envio**. O
coordenador recebe este único pacote de requisitos, sem nonce/reserva/credencial:

- Finalidade: avaliar seleção de evidências e texto local sobre caso de
  desenvolvimento real permitido, sob esta rubrica, sem alterar números/ranking.
- Dados: somente projeção revisada de IDs opacos, quantis/faixas, SHAP agrupado,
  referência descritiva de treino e requisitos reduzidos do briefing. Cada byte
  do payload precisa de revisão de permissão; redução não torna dados públicos.
- Exclusões: mídia, áudio, frames, transcrição integral, rótulos reservados,
  URLs, caminhos, credenciais, ferramentas e texto livre com instruções.
- Limites propostos: uma chamada, sem retry/reparo/fallback, 45 s, 2.048 tokens,
  pedido até 64 KiB, resposta até 16 KiB, custo R$0. Esses tetos não são autorização.
- Pré-condições: handoff final aprovado, dados compatíveis com termos aplicáveis,
  payload exato/hashes e autorização humana nova conferidos pelo coordenador;
  slot e autoridade do operador existente antes de qualquer envio.
- Parada: cobrar/alterar termos, limite excedido, erro, timeout, resultado incerto,
  seleção inválida ou divergência de identidade encerram sem repetir. Preservar
  números locais e registrar explicação incompleta. Não trocar para prosa livre
  NVIDIA como requisito adicional.

Até cumprir essas pré-condições, manter `new_external_calls=0`. Esta proposta
não reutiliza as rodadas NIM consumidas, não autoriza acesso a dados e não fecha
aderência, explicador escolhido ou integração final.

# Frente 2 — entrega implementada e limites de aceite

23/10/2026. **A Frente 2 e o projeto ainda não estão concluídos.** A tentativa
real autorizada abaixo produziu três análises A200 cacheadas e aderência acadêmica
parcial; a seleção NIM ficou indisponível. F2-03/F2-06/F2-09 permanecem sem aceite,
sem configuração final ou experiência completa com mídia nova e seleção externa.
As seções da entrega offline registram o histórico anterior a essa tentativa.

## Histórico da entrega offline: código e configuração

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
| Revisão histórica do arquivo real | Leitura dos recibos, JSON e textos preservados; conferência de hashes, vínculos, números e cobertura; nova apresentação local | Reexecução de features/modelos ou nova avaliação científica |

Os 114 checks agregados e os 22 testes posteriores são recibos diferentes, com
sobreposição. Não são 136 cenários únicos. Os 48 testes desta entrega incluem
os 28 iniciais e não devem ser somados a eles como testes novos independentes.

## Revisão histórica do texto real efetivamente apresentado

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
Nenhum nome de publicação, transcrição, URL ou caminho privado foi copiado
para este relatório público.

| Dimensão | Resultado da revisão assistida, limitado a esses três candidatos |
| --- | --- |
| Fidelidade | Números, faixas, ranking e fonte integral permaneceram iguais; grupos do pacote reconstruíram as medianas na escala log1p. A transformação inversa foi descrita corretamente, sem somar contribuições diretamente em views |
| Suporte | O texto do catálogo corresponde aos fatos vinculados; a nova leitura dos sinais cita os mesmos IDs. Não foram inventados temas, frases, emoções ou significado de dimensões do embedding |
| Suficiência | Seleção ausente: 0/12 grupos e 0/9 referências, reprovada. Catálogo local completo: 12/12 e 9/9, suficiente na rubrica para expor fundamentos da comparação exploratória. Isso não aprova um seletor NIM ausente |
| Utilidade comparativa | O catálogo permite inspecionar os fundamentos do cálculo e a prioridade por q50, sem atribuir a frases ou temas uma causa do alcance |
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

A revisão histórica levou 0,422 s, uma CPU e pico de filhos de 114.860 KiB, sem
modelos/extração/rede. O histórico de features levou 0,310 s; são fases e
medições diferentes. Os recibos dessa revisão incluem hashes da fonte e do código do
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

Resultados da entrega offline foram preservados em
`data/private/fechamento-20261023/frente-2/`, em namespace próprio. Os recibos
separam: fixtures, transporte real com números simulados, arquivo real apenas
revisado e fases históricas iniciadas por mídia. Há hashes e JUnit, inclusive
de falhas e timeouts; fontes antigas não foram sobrescritas. Foram preservados
37 arquivos novos no namespace privado `frente-2/release-v1`, com manifesto
SHA-256 `dd12164b980a68c3a4664589b2c4244edda40ce4761f9e8fb6571ccce28484e4`
e todos os hashes de destino conferidos. Nenhum arquivo histórico integral,
peso, mídia, transcrição ou `.env` foi copiado. O exemplo público
é inventado e deixa contradições e evidência insuficiente visíveis.

## Matriz de aceite atualizada após a tentativa real

| Critério da rubrica | Estado desta entrega | Lacuna que permanece |
| --- | --- | --- |
| F2-01 Fidelidade | Verificado no M1 histórico, nos objetos reais preservados e nos testes novos | Repetir somente os vínculos que mudarem com o handoff final |
| F2-02 Suporte | Vínculos de catálogo e conteúdo implementados/testados; fonte real preservada revisada | Metadados cacheados suportam apenas requisitos acadêmicos delimitados; verdade perceptiva e campanha comercial não validadas |
| F2-03 Suficiência | Rubrica executável, reprovações e cobertura registradas | Tentativa real sem IDs aceitos; catálogo local suficiente não aprova seleção remota; configuração final ausente |
| F2-04 Clareza | Leitura qualitativa dos textos reais e novo exemplo concluída | Compreensão por produtores não testada; densidade e jargão permanecem limites |
| F2-05 Limites | Avisos, origem, escala e distinção preditivo/descritivo preservados | Não converter esses avisos em validação científica |
| F2-06 Aderência | Contrato, casos de desenvolvimento inventados, conflitos e insuficiência implementados | Briefing acadêmico observado: 5 requisitos suportados, 1 contradito, 3 desconhecidos; aderência parcial, sem certificação geral |
| F2-07 Integração | Adaptador Python/MCP aditivo implementado; v6 reutilizado nas fases cobertas | NIM real autorizado terminou indisponível; integração com mídia nova e configuração final não demonstrada |
| F2-08 Operação | 48 testes de 1/3/5, IDs, empates, falhas, timeout e preservação; stdio em shell aprovado | Inicialização sob launcher supervisionado, inclusive com ambiente herdado, falha sem causa isolada; não foi transformada em skip |
| F2-09 Configuração final | Gate explícito, sem promoção indevida de A200 ou VLM | Handoff aprovado da Frente 1 ainda inexistente |
| F2-10 Reprodução/privacidade | Comandos, fixture segura, agregados e recibos persistentes concluídos | Integração/publicação e avaliação final pertencem ao Chat 3 |

## Tentativa real autorizada de 23/10

Antes dessa autorização, a entrega offline não tinha novo envio autorizado;
essa etapa histórica, o pacote remoto era apenas uma proposta inerte.
Uma execução nova, distinta do arquivo bruto histórico ausente, usou A200
provisório em três pares feature/run cacheados de beleza da validação, escolhidos
pela ordem do manifesto congelado antes dos resultados. Produziu três previsões,
SHAP nativo, comparáveis de um índice com 124 referências de treino e pacote local
de 30 fatos. Foram 1,754 s, pico RSS do grupo de 131.874.816 bytes e dois threads;
sem extração nova, grafo, MCP ou HTTP nessa etapa. Os 31 casos reservados ficaram
fechados. O operador original foi arquivado com hash correspondente ao recibo;
o código corrigido posteriormente não é a identidade daquela execução.

A revisão local confirmou as três reconstruções de `log1p(q50)` por base mais
quatro grupos SHAP com sinal e a inversa `expm1`. O catálogo completo tem 12 grupos
e nove referências, suficientes para comparação exploratória, sem interpretação
semântica ou causal dos embeddings. Fonte e pedido permaneceram byte a byte iguais.
O briefing foi escrito para desenvolvimento acadêmico com metadados observados:
orientação/duração deram cinco requisitos suportados e um contradito; três
requisitos de idioma da fala ficaram desconhecidos. São vínculos cacheados, sem
revisão nova da mídia ou escuta; aderência parcial, sem certificado de campanha.
O briefing não alterou previsões nem ranking.

A primeira tentativa numérica fez uma chamada NVIDIA autorizada, ao modelo
`nvidia/nemotron-3-nano-omni-30b-a3b-reasoning`, em modo instruct
(`enable_thinking=false`), teto de 2.048 tokens, 45 s e limites de 64 KiB no
pedido/16 KiB na resposta. R$0 foi orçamento declarado, sem medição de cobrança.
Em 4,770 s retornou HTTP 200, modelo correspondente, `finish_reason=stop`,
1.035 bytes e 2.057 tokens (1.892 de entrada e 165 de saída); filho recolhido,
sem timeout. O resultado foi `unavailable`: **zero IDs aceitos**, sem relatório
selecionado ou revisão qualitativa remota possível. O corpo bruto e a etapa
específica da rejeição não foram retidos; a causa exata permanece desconhecida.
O `response_complete` histórico indicava apenas resposta dentro do limite de
bytes, sem certificar framing HTTP. Não permite atribuir falha a JSON, conteúdo
ou indisponibilidade do provedor.

A fachada dinâmica optativa e a falha segura existem. A correção posterior
`2dfc160` distingue tamanho/framing e registra etapas fechadas de falha para
recibos novos: 75 testes controlados passaram em 2,33 s, com lint/formatação
aprovados, sem chamada externa ou prova nativa nova. Não classifica retroativamente
a rejeição anterior. Os recibos de 79/48 e 114+22 testes continuam históricos e
sobrepostos; não se somam a essa seleção como cenários independentes.

No seguimento autorizado, a correção de compatibilidade aceitou offline o envelope
real do controle visual com metadados opcionais, sem alterar seu conteúdo. Os
121 testes focados passaram; não se somam aos 75 históricos como cenários únicos.
Isso não identifica a causa da primeira resposta numérica, cujo corpo está ausente.
Uma nova reserva permitiu uma única segunda tentativa sobre o mesmo pacote,
sem refazer previsão ou extração e com modelo, configuração e payload canônicos
iguais. Sob os mesmos tetos de 45 s, 2.048 tokens e 64/16 KiB, parou em
**HTTP 503**, etapa de transporte, em 0,568 s, com processo recolhido. A fonte
numérica ficou intacta; nenhum ID ou revisão remota foi aceito. Não houve nova
tentativa nem leitura do corpo de erro. R$0 continua declarado, não medido.

O controle visual sintético foi separado: uma chamada HTTP 200, modelo
correspondente, cerca de 3,73 s e schema visual inválido, sem atributos aprovados.
O total deste seguimento é **duas tentativas numéricas e um controle visual**,
sem validação remota bem-sucedida. A tentativa de recuperar a primeira fonte de
treino parou em 2,220 s, sem folha original comprovada, rótulo reutilizado,
atributo liberado ou mídia/frames retidos. Pins/versões e opções passaram na
conferência offline; a causa da parada não foi isolada. Isso não comprova falha
do YouTube, da extração ou do VLM. O manifesto de 32 referências pertence à
auditoria TRAIN existente, sem alterar a coorte 300 ou as partições 203/66/31.

Nos adaptadores V7, o ensaio inicial sob teto de espaço virtual de 2 GiB teve
timeout em 115 s, sem estágio verificável ou fit comprovado. O diagnóstico de
imports passou em 1,017 s. Um ensaio B nativo q50 (4,3), com 32+8 linhas inventadas
por 912 colunas, passou em 0,693 s: 51 iterações avaliadas, uma árvore, oito
predições finitas e igualdade exata após salvar/carregar/predizer. Sob teto de
espaço virtual de 8 GiB e teto cooperativo de RSS de 2 GiB, o VMS final foi 3.180.072.960
bytes, pico VMS 3.370.901.504 e RSS final 147.345.408. Isso sugere inadequação
do teto anterior; não prova a causa do timeout nem desempenho de produção.

C falhou antes do treino porque o Dataset recusou listas. O commit `475f31d`
converte apenas as duas entradas Dataset para arrays float64. O teste nativo
LightGBM 4.7.0 com 8+4 linhas inventadas por 912 colunas, q50 (7,5), passou:
51 iterações avaliadas, uma árvore, quatro predições finitas e igualdade no
save/load/predict. O recibo registra oito testes com gravador e um nativo C,
nove aprovados, nenhum skip, 6,52 s (7,083 s supervisionados, teto 45 s).
A fixture gera uma árvore sem divisão e comprova API/persistência, sem qualidade
preditiva. B e C usaram fixtures e ambientes distintos; não constituem comparação
pareada, grade de 12 trials por três quantis ou treino de bundle completo.
VLM de sete campos, extração das 269 referências restantes, B/C observado e
avaliação externa de qualidade seguem pendentes; A200 permanece servido.

Não houve novo handoff, B/C final ou QualityRelease de sete campos. F2-03,
F2-06 e F2-09 seguem sem aceite; o percurso com mídia nova mais seleção externa
não foi demonstrado. Não há outro envio programado. Contagens e hashes estão no
[agregado público](evidence/front2-explanation-handoff-v1.json).

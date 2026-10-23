# Frente 2 — contrato e rubrica de explicação

Base auditada: `3586bcab7aa3f7bf165f1ac17ced91bb85358043`; início desta
unidade: `a9bdc17`. Execução offline autorizada pelo pedido humano de 23/10.
Clone independente, branch `codex/frente-2-explicacao-integracao`; somente o
Chat 3 integra. Contratos científicos, fontes seladas e autorizações consumidas
não são alterados. A configuração final depende do handoff aprovado da Frente 1.

## Critérios de aceite prévios

| ID | Critério verificável | Evidência / reprovação |
| --- | --- | --- |
| F2-01 | Fidelidade: análise, q10/q50/q90, ordem dos IDs, empates e ranking integrais | Igualdade dos objetos antes/depois; rejeitar pacote ou claim de outra análise |
| F2-02 | Suporte: cada claim exibido pertence ao catálogo vinculado; conteúdo tem referência à mesma mídia/ID | Recusar texto alterado, vínculo incorreto, duplicatas e evidência conflitante |
| F2-03 | Suficiência: números/faixas disponíveis e fundamento relevante de cada candidato; sinais relevantes de SHAP e referência ou motivo explícito | Exigir grupo de maior magnitude e maior contribuição de cada sinal disponível; todos os grupos zero precisam explicitação. Não exigir catálogo completo; seleção insuficiente continua estruturalmente válida, mas reprova suficiência |
| F2-04 | Clareza: alvo em views, escala log1p, origem dos textos, seleção versus catálogo e prioridade exploratória | Revisar o texto efetivamente exibido; avaliação automática de cobertura não substitui leitura qualitativa |
| F2-05 | Limites: sem causalidade, sem semântica inventada de embedding, sem promessa paga/superioridade/cobertura | Avisos e frases vinculadas no texto; SHAP não explica o conteúdo sem evidência descritiva correspondente |
| F2-06 | Aderência: briefing de campanha identificável e conteúdo correspondente por candidato/requisito | Contexto diagnóstico não conta; ausente/inconclusivo permanece não avaliado ou parcial. Conflito explícito não modifica ranking |
| F2-07 | Integração: entrada → extração necessária → features → previsão/faixa/ranking → SHAP → comparáveis de treino → seleção/validação/renderização → Python/MCP | Recibo por fase e origem; distinguir herdado, replay e execução nova. HTTP200 e fixture repetida não aprovam qualidade real |
| F2-08 | Operação: individual, até cinco, ordem, erros, timeout, falta de suporte e limpeza | Testes direcionados de contratos e processo; zero diretórios próprios pendentes após confirmação de recolhimento |
| F2-09 | Configuração: identidade do modelo/extratores coincide com handoff aprovado | A200 histórico servido não é configuração final vencedora; sem handoff não declarar fechamento |
| F2-10 | Reprodução e privacidade: comandos, exemplo público e recibos separados | Sem credenciais, mídia, transcrição integral ou caminho privado na resposta; fontes nunca sobrescritas |

O requisito de suficiência é uma rubrica desta rodada, não uma alteração retroativa
da seleção NIM histórica. Uma seleção pode passar no schema e falhar nesta rubrica.
Para contribuições iguais, qualquer grupo empatado na maior magnitude do sinal
serve. Faixas são exibidas pela apresentação numérica mesmo se omitidas pela seleção.
Evidência omitida não significa inexistente. Nenhuma quota total de catálogo é exigida.

## Contrato aditivo

A entrada pública continua `AnalysisRequest`: campanha, 1–5 IDs distintos,
setor, divulgação e brief. Caminhos, configurações, callbacks, evidências e
autorizações são fornecidos apenas pelo operador local. O fluxo original M1
permanece intacto, incluindo o StateGraph em ambiente separado e o proprietário
de processos. A resposta adicional inclui a fonte integral, texto apresentado,
revisão de cobertura e aderência com referências verificadas localmente.

Um caso de desenvolvimento liga a versão/hash do briefing à mesma campanha,
setor, objetivo, IDs e hashes de mídia registrados. Os requisitos são predicados
fechados, não instruções executáveis. Observações de conteúdo são fornecidas por
revisão local explícita; o contrato verifica os vínculos, não certifica sua verdade.
Observações usadas para aderência são descritivas, não features adicionadas ao
preditor. Nenhum VLM reprovado é promovido a feature ou evidência verificada.

Aderência é reportada por requisito/candidato, incluindo contradições e lacunas;
não gera uma nota de campanha nem reordena previsões. Casos inteiramente
inventados serão identificados como desenvolvimento sintético e não aprovam
aderência de uma campanha real. Novos casos reais exigem briefing e evidências
correspondentes permitidos; diagnóstico não será renomeado para campanha.

## Evidência reaproveitada

- [Par real v6](issue-5-paridade-independente-resultados.md): extração nativa,
  M1/A200, SHAP, comparáveis e paridade Python/MCP em três candidatos. Não NIM,
  qualidade visual, configuração final ou aderência.
- [Revisão NIM](issue-5-nim-quality-review-v1.md): 12 claims suportados por
  fonte inventada; seleção1/12grupos SHAP e2/3referências, suficiência parcial.
- Fluxo recente de três features reais cacheadas até texto local: sem extração,
  grafo, MCP ou NIM novos. O texto existe e deve ser reutilizado na revisão.
- Os114checks agregados e22testes posteriores têm sobreposição; não são136
  cenários distintos. Novos resultados serão registrados separadamente.

Não há chamada remota autorizada nesta unidade. Se necessária após o handoff,
um único pacote será apresentado ao coordenador com projeção permitida, hashes,
finalidade, tetos de chamadas/tempo/tokens/bytes, R$0 e parada sem retry/fallback.
A presença de chave ou uma rodada consumida não autoriza envio. Não enviar
mídia, áudio ou transcrição integral automaticamente.

## Unidade 1 implementada

`campaign_evidence_v1` liga requisitos fechados a observações locais do mesmo
criativo/mídia e briefing. `explanation_review_v1` confere pacote, claims e
reconstrução dos grupos SHAP e mede a suficiência do texto selecionado ou do
catálogo local, separadamente. A fonte integral não é reescrita. Ausência em
frame amostrado permanece insuficiente para estabelecer ausência no vídeo.
Observações conflitantes não são resolvidas em favor do briefing.

A fixture pública `front2-campaign-invented-v1.json` contém briefing de campanha
explicitamente inventado, três IDs e observações correspondentes: um candidato
atende texto/duração, outro contraria ambos, e o terceiro tem texto inconclusivo.
Ela não representa uma campanha real nem corrige a origem diagnóstica antiga.

Validação inicial: **28 testes novos/0,31 s**, uma CPU, RSS máximo dos filhos
143.232 KiB, sem modelos, mídia ou rede. Ruff e diffcheck passaram. A primeira
rodada deixou 27 aprovados/1 falho porque o teste havia atribuído +0,4 ao grupo
errado da fixture; a checagem de suficiência o rejeitou corretamente. O teste
foi corrigido para selecionar os grupos efetivamente mais relevantes, sem
alterar o catálogo, a regra ou a evidência. Ambos os recibos foram preservados
em `data/private/fechamento-20261023/frente-2/` no clone independente.

## Unidade 2 — função e MCP

`analyze_reviewed(payload, ReviewSettings(...))` chama o grafo M1 existente uma
única vez, conserva sua resposta integral em `source_result` e acrescenta
`display_text`, hashes, `quality_review`, `campaign_adherence` e
`integration_receipt`. A tool optativa `analyze_creatives_reviewed` usa a mesma
função; as tools anteriores permanecem disponíveis. O payload não recebe
callbacks, caminhos, configuração científica ou evidências do operador.

`ReviewSettings` configura somente o grafo histórico e casos locais revisados.
O servidor não configura NIM ou seletor alternativo automaticamente. Sem seleção,
essa etapa continua incompleta; mostrar o catálogo é uma opção local explícita,
registrada separadamente da seleção. Os textos são locais. A configuração
multimodal final continua pendente: este adaptador não aceita silenciosamente
B/C completos como se fossem M1/A200.

Os metadados de mídia do cadastro são conferidos antes/depois da execução quando
há caso de campanha correspondente, sem redecodificar mídia para a revisão.
Alteração do cadastro invalida aderência, mas preserva os números retornados.
Cancelamento propaga ao proprietário de processos já existente; revisão não
faz retry ou fallback. Erros de entrada não lançam o grafo. Falha de revisão,
lançamento ou pacote ausente tem código fixo, sem eco de entrada/caminho privado.

O recibo aditivo deriva das fases reportadas pelo grafo; ele não é uma captura
independente de execução. `native_feature_handoff` não prova extração nova.
`fresh_media_extraction_proven_by_this_receipt=false` torna essa limitação explícita.
A contagem de referências encontradas é separada dos avisos de ausência; uma
busca concluída com lista vazia não significa suporte recuperado. Fontes
simuladas não recebem confirmação falsa de recolhimento pelo supervisor.

### Reprodução pública sem mídia, modelos ou chave

```sh
rtk proxy .venv/bin/python -B -m scripts.explanation_review_mcp_v1 --public-example --format text
rtk proxy .venv/bin/python -B -m scripts.explanation_review_mcp_v1 --public-example --format json
rtk proxy .venv/bin/python -B -m pytest -q -p no:cacheprovider tests/test_front2_explanation_review.py tests/test_front2_review_service.py
```

O exemplo é inteiramente inventado, com seleção local escrita para demonstrar
os fundamentos relevantes. Não simula uma nova resposta NVIDIA. Ele mostra
sinais SHAP, números/faixas, ranking e contradições/lacunas dos requisitos do
briefing, sem modificar a fonte. O título de uma campanha inventada não é prova
de aderência em criativos reais.

### Configuração local do operador

A CLI aceita `--graph-python`, `--worker-python`, `--uploads-root`, `--registry`,
`--scratch-root`, o par `--m1-model-dir`/`--m1-cohort-dir`, `--evidence-root` e
`--minimum-similarity`. `--campaign-case` lê um contrato `CampaignCase` local;
`--request-file` executa a mesma função Python uma vez, sem essa flag o servidor
aguarda cliente MCP por stdio. `--show-local-evidence` apresenta o catálogo e
registra esse escopo. Localizações são configurações privadas do operador,
nunca campos aceitos na solicitação do host.

### Validação e limite operacional encontrado

**48 testes direcionados passaram em 7,16 s**, com fixtures inventadas,
transporte MCP real por stdio e nenhuma carga de modelo/rede externa. Incluem
os 28 testes da unidade1; não são 48 casos novos adicionais. Verificados 1/3/5,
empates/ordem, preservação numérica, fontes alteradas, falta de suporte, mudança
do cadastro, entradas inválidas, cancelamento/timeout e ausência de retry.
Ruff/formatação e diffcheck são exigidos antes do commit.

Há uma **falha operacional aberta na inicialização stdio sob ambiente totalmente
substituído**: o cliente não recebe inicialização em 30 s. O primeiro traceback
com `-x` registrou `Client._connect` aguardando `ready_event`; não houve resposta
ou stderr que atribua causa. A captura de pilha observou o servidor em asyncio,
sem evidência de import/pesos bloqueado. Acrescentar identidade/locale ao ambiente
mínimo não isolou a causa. No ambiente de shell existente a mesma seleção stdio
passou; não se atribui causalidade apenas a essa diferença.

A rodada agregada de 45 s foi terminada e seu grupo próprio foi recolhido;
sem JUnit completo, não conta como rodada aprovada. A anterior de 60 s também
não conta. Recibos e falhas foram preservados para revisão. Nenhum timeout foi
ampliado, pacote atualizado, segredo herdado por intenção ou fonte científica
modificada para obter o resultado. O modo de ambiente reduzido precisa de
investigação própria antes de ser prometido como caminho operacional.

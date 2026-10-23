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

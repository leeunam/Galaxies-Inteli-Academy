# Matriz de requisitos e evidências — iSee

Conferência de 23/10/2026. Fontes: TAPI original local, seções 3–4, 6–8 e 10;
[proposta técnica](proposta-tecnica.md), [briefing](briefing-de-trabalho.md),
[backlog](backlog-proposto.md) e [matriz de fechamento](fechamento-20261023.md).
O PDF recebido permanece privado e ignorado. Esta matriz não altera o escopo.

**Veredito deste checkpoint: parcialmente concluído.** A implementação e as
provas históricas são reais nos limites abaixo; os aceites compostos ainda
abertos impedem declarar conclusão do escopo ou abrir o teste final.

## Obrigações e escolhas confirmadas

| ID / obrigação | Evidência reutilizável | Limite atual | Responsável / dependência | Condição de aceite |
| --- | --- | --- | --- | --- |
| R01 — problema, autoria, público e entrada de 1–5 criativos | [README](../README.md), `CONTEXT.md`, `scripts/creative_contracts.py`; autoria confirmada no histórico Git | Contrato de moda/beleza/divulgação; não cobre integração interna da Galaxies | 3; decisão de escopo já confirmada | Documentação e comandos correspondem ao código efetivamente servido |
| R02 — base documentada, origem, alvo, período e uso | [Base 300](issue-3-expansao-300-resultados.md), [origem e uso](uso-youtube-e-plano-de-entrega.md), manifestos privados preservados | Autorização operacional não comprova aprovação da plataforma/licença irrestrita; snapshot de views aos 30–37 dias, não dia 30 reconstruído | 1/3; passagem privada autorizada | Registrar datas e condições por referência, limites e ausência de licença pública da base; não publicar dados |
| R03 — partições e prevenção de vazamento | 300 referências, 166 canais, 203/66/31; `scripts/channel_partitions.py`, `scripts/retrain_expansion.py` | Generalização por canal não elimina sinais de identidade em voz/rosto/estilo | 1/3; manifestos congelados | Mesmos canais/duplicatas e linhas; transformações aprendidas só no treino; nenhuma seleção pelo teste |
| R04 — baseline explícito | [Baseline observado](issue-2-baseline-observado.md), B0/Bcanal, `scripts/empirical_baseline.py` | Sem histórico anterior confiável, Bcanal cai em B0; `relative_to_channel` indisponível com motivo | 1/3; mesma coorte e treino | Comparar B0/Bcanal no mesmo conjunto e identificar faixa descritiva, fallback e suporte; não fabricar histórico |
| R05 — A treinado e servido | [Conferência de A](issue-3-conclusao-tecnica-local.md), [treino A](issue-3-treinamento-offline.md), A300 preservado | A200 continua servido; A300 não foi promovido | 1/2/3; compatibilidade de artefatos | Artefato recarregável, features/alvo separados, quantis e avisos corretos; comparação final ainda pendente |
| R06 — multimodal leve e atributos VLM | CLIP/ASR/medidas técnicas, diagnósticos preservados; [qualidade e handoff](fechamento-frente-1-qualidade-e-handoff.md) | TAPI exige 5–8 atributos; proposta contém sete. Rubrica de três presenças e `unknown` não encerram o contrato | 1; gates perceptivos independentes | Validar atributos obrigatórios com evidência, suporte e gates originais; emitir liberação verificável antes da extração elegível |
| R07 — B completo e C completo | [Ponte B/C](fechamento-frente-1-c-completo.md), código integrado em `e8630c0`/`e3a0eac`, testes inventados | Ponte observada restrita a três presenças; caminho versionado de sete atributos em preparação. B/C-cache não substituem completos; 269 sidecars elegíveis e treino real ausentes | 1; R06, contrato técnico de sete campos e fila exclusiva | B CatBoost antes de C LightGBM, mesmos atributos/linhas/partições, recarga e proveniência verificadas |
| R08 — ganho multimodal e escolha na validação | [Comparação cacheada](issue-4-experimento-c-cache-resultados.md); `scripts/compare_full_models.py` | Resultados cacheados favoráveis não liberam VLM nem promovem modelo servido | 1; R07 | MAE log por canal menor sem piora da média das perdas quantílicas; empate favorece CatBoost; seleção antes do teste |
| R09 — quantis, ranking e suporte | q10/q50/q90; política q50 preservado; `scripts/experiment_a_metrics.py`; [motor P6](issue-6-motor-metricas-v1.md) em `14b9129` | Testes e validação não são calibração independente | 1/2/3; configuração final | Erro, pinball, cobertura/largura, ranking intra-canal, empates e suporte explícitos, inclusive falhas e células não estimáveis |
| R10 — SHAP e comparáveis | [SHAP M1](issue-5-shap-m1.md), [índice treino](issue-5-comparaveis-treino.md), SHAP B/C inventado | Fidelidade matemática não demonstra percepção, causalidade ou qualidade da narrativa | 2; R08 | Reconstruir log1p(q50), agrupar embeddings por modalidade, comparáveis somente treino e ausência declarada |
| R11 — explicação útil e aderência | [Revisão NIM](issue-5-nim-quality-review-v1.md), [rubrica e revisão real da Frente 2](fechamento-frente-2-resultados.md), adaptador em `eecc535` e leitor em `d705583` | Catálogo real tem fundamentos disponíveis, seleção está ausente e aderência real não foi avaliada; falta briefing e conteúdo correspondentes | 2; rubrica prévia e handoff R08 | Números/ranking preservados, fundamentos suficientes, português claro, limites e avaliação do texto exibido; envio externo somente no pacote permitido |
| R12 — grafo, função e MCP | [Integração v2](issue-5-integracao-nativa-v2.md), [par v6](issue-5-paridade-independente-resultados.md), [prova pública](issue-7-reproducao-offline.md), adaptador revisado 1/3/5 com fixtures | Par v6 cobre A200; não prova futura configuração completa. Falha de inicialização sob lançador supervisionado continua sem causa isolada; execução direta passou | 2; R08/R11 | Percurso final 1/3/5, IDs/ordem, falhas/timeout/limpeza e paridade dos contratos alterados; reutilizar os inalterados |
| R13 — diagnóstico temporal anterior→posterior | [Protocolo P6](issue-6-protocolo-final-e-checklist-v1.md); [planejador temporal](issue-6-diagnostico-temporal-v1.md) em `8fbf198` | Nenhum ajuste anterior/avaliação posterior executado; datas e plano não encerram obrigação | 3; representação aprovada, vista de desenvolvimento e recursos | Ajustar no anterior, avaliar no posterior, mostrar suporte/sobreposição/idade e disponibilidade; snapshot não é backtest prospectivo |
| R14 — congelamento e 31 casos finais | [Procedimento P6](issue-6-protocolo-final-e-checklist-v1.md), preflight de metadados, motor de métricas | Configuração final, carregadores restritos, reserva e aceites científicos ausentes; teste fechado | 3; aceites 1 e 2, revisão e autorização específica | Congelar identidades/seleção, executar cinco configurações no mesmo teste sem fit/retuning/promoção, registrar falhas e relatório privado/sanitizado |
| R15 — reprodução e pacote público | Dois locks, [ensaio offline](issue-7-reproducao-offline.md), README/diagrama | Prova histórica cobre contratos inventados; obtenção real depende de passagem privada e termos aplicáveis | 3; código consolidado | Pacote sem mídia/chave/transcrição/pesos; comandos com origem de verificação declarada, versões e artefatos identificados |
| R16 — entrega e aprendizagem | Glossário, [guia curto](guia-explicacao-isee.md), registros de escolhas | Aceite humano, publicação e fechamento remoto são passos separados | 3 e autor; R01–R15 | Autor explica exemplo completo e limites; recibo final associa arquivos, commits, testes e pendências sem alegar 100% prematuramente |

## Recomendações e adaptações explicitadas

As tecnologias da seção 8 do TAPI são recomendações, não uma lista de pacotes
a instalar. O projeto justifica Python, CatBoost/LightGBM, CLIP, Whisper,
Qwen, LangGraph isolado, FastMCP e registro local com hashes; MLflow, pandas,
Parquet, MediaPipe, OCR/YOLO ou outro provedor não são acrescentados apenas
porque aparecem como alternativas. Uma alternativa de ferramenta não elimina
a obrigação de demonstrar a informação multimodal correspondente aprovada.

O TAPI permite escolher pelo menos dois setores: moda e beleza são a decisão
local. Views e a mediana por setor/fallback são as escolhas registradas diante
da falta de histórico anterior confiável. A meta original de milhares de
vídeos não é um aceite fictício: o recorte confirmado é 300. O contrato local
recebe IDs do cadastro seguro em vez de aceitar caminhos arbitrários do host.
A avaliação temporal estrita recomendada no TAPI continua limitada pela falta
de observações históricas; o diagnóstico retrospectivo acordado permanece
obrigatório e ainda pendente. Não declarar que o split por canal o substitui.

## Extensões opcionais e fora do núcleo

Permanecem opcionais: Ridge após A/B/C, conformal, retreino dinâmico por cliente,
RAG/FAISS, otimização what-if, comparação LLM zero-shot, X-CLIP/VideoMAE/CLAP e
interface de demonstração elaborada. A persona sintética, integração com contas
de anúncios/plataforma interna e acesso a dados internos não são entregas
obrigatórias deste projeto. Nenhuma dessas extensões foi usada para ampliar
silenciosamente o caminho de aceite.

## Situação administrativa verificada

Consulta somente leitura pelo conector GitHub em 23/10/2026, com filtros
separados `is:open` e `is:closed`: **#1/#2 fechadas; #3–#7 abertas**, no destino
[leeunam/case-GALAXIES-IA](https://github.com/leeunam/case-GALAXIES-IA).
O remote local aponta para esse mesmo repositório; os links antigos com o
nome `Galaxies-Inteli-Academy` são históricos. Corpos das issues preservam
checkpoints antigos de stack/provedor; fontes, locks e adendos atuais são
necessários para interpretar o estado real. Não houve comentário, alteração
de issue, push ou publicação nesta consulta. Proposta de destino de entrega:
o repositório atual, em commit local revisado; publicar exige autorização
aplicável e não fecha aceites científicos por si só.

# Issue #5 — integração na árvore principal

Integração local autorizada em 20/10/2026, após revisão do supervisor e passagem
para um único escritor. A branch `codex/issue-5-integracao-v2` nasceu em
`69a5832` e recebeu por fetch exclusivamente local e fast-forward os quatro
commits `f05fdf6`, `d12aa04`, `89b0189` e `427a035`. A branch da v15 continua
em `69a5832`; o README não rastreado não foi lido, editado ou incluído no Git.

Antes da mutação foram conferidos os estados exatos das duas árvores,
1.305 hashes originais/finais e os 19 hashes da entrega. Nenhum ambiente,
lock, fonte selada, artefato privado protegido ou partição foi alterado.
Somente os recibos necessários do clone foram copiados para um diretório
privado novo; dataset, pesos, cache e uploads não foram copiados.

## Verificações combinadas e correção de protocolo

Após o fast-forward passaram **133 testes direcionados raiz em 87,82 s** e
**94 testes da suíte isolada em 41,00 s**, em sequência, sem jobs duplicados.
São os resultados anteriores à pequena correção descrita a seguir.

A primeira prova com mídias geradas e extrator de produção confirmou igualdade
numérica entre o analisador original, Python/StateGraph e MCP/StateGraph, mas
falhou no pós-check da explicação indisponível. O grafo encaminhava o motivo
local da sessão pelo campo reservado a motivos do transporte. O worker o
recusava e o supervisor devolvia os números preservados com o aviso genérico
de falha do worker. Isso era falha de integração, não motivo para substituir
as indisponibilidades legítimas do preditor.

O adaptador agora envia `reason=None` quando não há pacote; a sessão raiz
continua autoridade sobre seu próprio motivo. Somente resultados do transporte
usam o campo de motivo do transporte. Nenhuma guarda ou fonte anterior foi
relaxada. A regressão confere entrada inválida, todas as previsões indisponíveis
e falhas de evidência, preservando números e motivos.

Após a correção passaram **13 testes raiz em 31,55 s**, mais o novo caso de
sessão real com todas as previsões indisponíveis (**1 teste em 2,51 s**).
No ambiente isolado passaram **17 testes em 12,50 s**, incluindo os quatro
novos casos de encaminhamento de motivo sem pacote.
O novo verificador de mídia é separado das fixtures de features do clone:
usa o serviço e launcher de produção, pesos já locais e arquivos gerados.
Seus resultados finais são registrados na seção seguinte.

## Prova separada com extração real de mídia gerada

O verificador `scripts.verify_generated_media_v2` não utiliza fixture de
features ou worker de teste. Gerou três vídeos com FFmpeg já empacotado e fala
portuguesa com a biblioteca eSpeak NG já instalada, em modo PCM sem reprodução
no dispositivo. Não instalou dependências ou baixou pesos/mídia.

Na tentativa final `generated-native-v2`, o serviço original e os serviços
Python/StateGraph e MCP stdio/StateGraph usaram os mesmos três arquivos e o
launcher de produção. A análise numérica completa foi igual nos três percursos;
o resultado integrado Python e MCP também foi integralmente igual.

| Controle sintético | Extração real | Previsão |
| --- | --- | --- |
| Vídeo sem áudio | `no_audio_stream` | Indisponível: `unsupported_text_status` |
| Vídeo com áudio silencioso | `no_speech_detected_by_asr` | Indisponível: `unsupported_text_status` |
| Vídeo com fala sintetizada em português | Texto extraído; triagem de idioma inconclusiva | Indisponível: `language_inconclusive` |

A biblioteca de ASR foi executada com sua política original, sem forçar idioma.
Não foi determinada qual subcondição tornou a triagem inconclusiva, nem se
relaxou essa guarda para obter uma previsão. O modelo foi carregado/verificado
como M1/A200, mas nenhuma previsão ficou disponível nesses controles. Portanto,
SHAP e busca no índice de treino foram **corretamente omitidos**, e a explicação
retornou `learned_prediction_unavailable`, sem ser confundida com falha do worker.
Não houve fallback numérico ou ranking competitivo fabricado.

Essa prova é diferente da anterior no clone: lá as features eram inventadas,
com previsão/SHAP/índice nativos. Aqui a extração foi real, sobre mídia sintética,
com indisponibilidade legítima das previsões. Nenhuma delas substitui a demo
com três mídias reais distintas autorizadas ou valida qualidade científica.

Depois da paridade, outra execução de produção foi cancelada somente após
observar `scripts.candidate_features` no grupo identificado pelo lease. O
cancelamento propagou, o extrator e o grupo foram recolhidos e o scratch ficou
vazio. Os arquivos gerados, áudio, cadastro e temporários foram removidos.
O resultado registra **zero downloads, VLM, provedor e leitura de holdout**.
O caminho original levou 19,95 s nesta execução; não é benchmark ou SLA.

Para repetir o ensaio, com recursos locais já presentes, executar na raiz:

```sh
rtk proxy env PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_TELEMETRY=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=4 .venv/bin/python -B -m scripts.verify_generated_media_v2 --model-dir /home/inteli/Documents/projetos/Galaxies-Inteli-Academy/artifacts/issue-3-experimento-a-v1 --cohort-dir /home/inteli/Documents/projetos/Galaxies-Inteli-Academy/data/private/issue-1-pool-treino-20261018-v6/released-cohort-v1 --evidence-root /home/inteli/Documents/projetos/Galaxies-Inteli-Academy --graph-python /home/inteli/Documents/projetos/Galaxies-Inteli-Academy/orchestration/.venv/bin/python --output-dir /caminho/privado/novo-e-exclusivo
```

O diretório de saída deve ser novo; a rotina não sobrescreve recibos anteriores.
A biblioteca local e a voz portuguesa precisam existir; não há instalação ou
download automático. Não usar o teste de ausência de pesos próprio do clone.
Os checkpoints e resultados em `generated-native-v2/` são privados e não entram
no Git. A prova gerada não configura um provedor ou avalia aderência.

## Integridade e passagem final

Foram comparados **1.345 hashes, sem diferença**: 1.270 pins originais,
35 provas finais da v15 e 40 arquivos de sua fila cujo inventário já existia
antes desta integração. O inventário dos 40 não é retrospectivamente tratado
como baseline da preparação inicial do clone. Os conjuntos e versões das
**130 distribuições raiz e 42 isoladas** continuam iguais aos registros
protegidos. Ruff e formatação passaram nos **215 arquivos Python** atuais.
M1/A200, comparadores, partições, oito PNGs, recortes e filas protegidas continuam
intactos. Nenhum ambiente foi sincronizado ou reinstalado.

A conferência final encontrou zero workers ativos e zero scratch/mídia pendente
das provas nativas. A recuperação manual após morte do próprio supervisor
continua descrita no documento do clone e coberta pelo teste com lease; o
cancelamento normal nativo desta integração teve recolhimento automático.
O README segue somente como arquivo não rastreado, fora da leitura e staging.

`integration-final-verification.json`, os JUnit, snapshots de versões e
`generated-native-v2/generated-native-result.json` sustentam esta passagem no
diretório privado acima. A execução anterior que encontrou o erro de protocolo
permanece identificada como falha em seu próprio recibo. O marco local de
integração foi demonstrado; a #5 e suas pendências científicas/humanas não
foram encerradas. Não houve push, publicação ou deploy.

Recibos privados exclusivos desta integração:
`data/private/issue-5-integracao-v2-20261020/`. A tentativa `generated-native-v1`
permanece registrada como falha; não é convertida retrospectivamente em sucesso.
Não houve NIM, VLM, aquisição de mídia, abertura do holdout ou publicação.
A explicação por provedor, três mídias reais distintas e aceite humano continuam
pendentes; a #5 permanece aberta.

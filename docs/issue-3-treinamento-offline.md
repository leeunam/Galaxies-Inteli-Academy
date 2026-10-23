# Experimento A — treinamento offline

O bloco offline da #3 reutiliza a coorte e as partições da liberação ampliada.
**Checkpoint posterior:** a [integração de M1 na função/MCP](issue-3-servico-m1.md)
foi implementada com paridade real e teste reservado preservado. Este documento
registra a entrega offline anterior e suas métricas de validação.

**Execução real de 18/10/2026 concluída:** modelos treinados somente nas 124
referências/48 canais de treino, configurações escolhidas nas 45/16 de validação.
As 31 referências/16 canais do teste permanecem fora de previsões e métricas.
Naquele checkpoint, M1 estava disponível offline, sem a integração da #3.

`scripts/experiment_a_data.py` revalida coorte, baseline, evidências, configuração,
arquivos dos extratores e versões instaladas. Compara as entradas persistidas com
as entradas reimportadas. Essa leitura integral verifica a integridade, incluindo
as observações congeladas do teste; não calcula previsões ou métricas do teste.
A fronteira de ajuste recebe somente dois `DevelopmentSplit`: treino e validação.
Não há parâmetro para avaliar teste nem rotina para refazer sua divisão.

A matriz tem 388 colunas: setor e estado do texto categóricos, duração, proporção
altura/largura e 384 componentes MiniLM da fala. Canal/ID ficam no agrupamento e
na auditoria; rótulos ficam em outro vetor. Não há transformação aprendida,
normalização, PCA ou imputação ajustada nos dados. A representação fixa para
texto ausente é embedding zero com estado explícito, utilizável somente quando
esse estado teve suporte no treino. Falha de extração não é silêncio.

## Exemplo para acompanhar

Uma referência de treino fornece `x = [setor, duração, proporção, estado,
embedding...]` e, separadamente, `y = log1p(views)`. Para um exemplo **sintético**
de 999 views, `y = log(1000) ≈ 6,9078`; `expm1(y)` recupera 999.
O baseline atribui a mediana do setor no treino a todos os candidatos desse setor.
O CatBoost usa os sinais do arquivo para estimar uma mediana condicional.

Uma referência de validação fornece as mesmas colunas, mas seu rótulo serve
somente à parada antecipada e à escolha da configuração. Calculamos o erro de
cada vídeo, a média dentro de cada canal e então a média entre canais; canais
com mais publicações não dominam a escolha. O teste reservado não participa.
Reproduzir essa seleção de IDs/colunas e interpretar a comparação de validação
é a prática prevista; este texto não afirma que o aluno já a realizou.

## Ajuste, escolha e inferência offline

`scripts/train_experiment_a.py` executa exatamente quatro combinações por quantil:
profundidade 4/6 × L2 3/10, quantis 0,1/0,5/0,9, CPU, taxa 0,05, até 500 iterações,
parada após 50 sem melhoria, seed 42 e dois threads. As linhas de treino têm peso
uniforme. A validação tem pesos `1/n_vídeos_do_canal` para que cada canal contribua
igualmente à métrica de parada: MAE no q50 e perda quantílica nos extremos.
A métrica nativa é conferida contra o cálculo independente (tolerância 3e-6 para
float32/epsilon da biblioteca). O padrão da biblioteca usa os pesos disponíveis;
declarar `use_weights=true` explicitamente falha quando o treino não tem pesos.

A seleção usa essas mesmas métricas, recomputadas em Python. Empates favorecem
menor profundidade e depois menor L2. Cada quantil é escolhido antes do reparo
conjunto; não há busca adicional após a avaliação dos três escolhidos. Os modelos
selecionados mantêm somente as árvores até a melhor iteração, sem reajuste na
união treino/validação. O protocolo permanece idêntico mesmo se A perder de B0.
O [objetivo Quantile do CatBoost](https://catboost.ai/docs/en/concepts/loss-functions-regression)
é a perda usada no ajuste, inclusive para q50.

A inferência verifica finitude e domínio físico de todos os logs (`0` até
`log1p(2**63-1)`), recusando previsões inválidas em vez de alterar q50.
Aplica inferior = mínimo dos três logs brutos e superior = máximo dos três,
mantendo q50, e só então `expm1`. O relatório avalia exatamente essa faixa reparada,
registra cruzamentos, cobertura/largura e resultados por setor/canal.
Cobertura na validação é diagnóstico exploratório, não calibração garantida.

B0/Bcanal vêm do mesmo bundle e treino. Em canais reservados, Bcanal usa fallback
B0; sua faixa é descritiva do setor no treino, não intervalo preditivo.
O relatório privado traz MAE log macro por canal e micro, MAE views, MAPE só nas
views positivas (fração, com exclusões declaradas), perdas quantílicas, cobertura,
largura, ranking por canal e correlação global secundária. Spearman por canal exige
três vídeos e variação em rótulo/previsão; caso contrário fica indisponível.
Pares com empate no alvo são excluídos e empate na previsão vale meio acerto.
O diagnóstico temporal e a avaliação final continuam na #6.

## Artefato e reprodução

O diretório de saída deve ser novo. Contém `artifact.json`, `validation-report.json`
e modelos nativos `q10.cbm`, `q50.cbm`, `q90.cbm`; não há pickle. Os arquivos são
privados (0600, diretório 0700). O manifesto só é publicado ao fim e inclui todas
as tentativas/tempos, escolha, IDs de desenvolvimento, hashes de dados/partições/
baseline/configuração, política de ausências, código, lock e versões CatBoost/NumPy.
Modelos e dados ficam ignorados pelo Git. Um diretório parcial não é um bundle.

`load_bundle` confere esquema, seleção, checksums, versões/código/lock,
configuração esperada e contratos dos modelos. O ajuste confere igualdade exata
das previsões de validação antes/depois da recarga. `predict_logs`/`predict_views`
recebem somente `PredictorInputs`, nunca outcomes ou dados de campanha.
Essas funções ainda não conectam M1 ao serviço da #2.

Com ambiente instalado a partir de `uv.lock`, na raiz do repositório:

```bash
rtk proxy env UV_CACHE_DIR=/tmp/galaxies-uv-cache uv run --offline --frozen python \
  -m scripts.train_experiment_a \
  --cohort-dir data/private/issue-1-pool-treino-20261018-v6/released-cohort-v1 \
  --inspect

rtk proxy env UV_CACHE_DIR=/tmp/galaxies-uv-cache uv run --offline --frozen python \
  -m scripts.train_experiment_a \
  --cohort-dir data/private/issue-1-pool-treino-20261018-v6/released-cohort-v1 \
  --output-dir artifacts/issue-3-experimento-a-v1

rtk proxy uv run --frozen pytest -q
rtk proxy uv run --frozen ruff check scripts tests
rtk proxy uv run --frozen ruff format --check scripts tests
```

`--inspect` mostra um exemplo real de treino e validação, sem ajustar modelo;
não publicar sua saída como fixture pública. O cache alternativo evita escrita
no cache global somente leitura deste ambiente. Não baixa modelos nem mídia.

## Resultado da primeira execução real

Branch `codex/issue-3-experimento-a`, criada do HEAD `ea69d42` da branch
`codex/issue-2-prototipo`. Entradas isoladas em `c346dc6`; busca, inferência offline
e persistência em `50edb41`. Nenhuma coleta, extração adicional ou chamada NIM.
Os 12 ajustes consumiram **9,83 s somados**, neste ambiente, excluindo importação,
carregamento dos dados e publicação. Não é medida de latência do serviço.

Todos os quantis escolheram profundidade 4 e L2 10, mantendo taxa/seed/protocolo.

| Quantil | Melhor iteração (base zero) | Árvores persistidas | Métrica de escolha |
| --- | ---: | ---: | ---: |
| q10 | 1 | 2 | Pinball macro por canal: 0,554836 |
| q50 | 168 | 169 | MAE log macro por canal: 1,856909 |
| q90 | 29 | 30 | Pinball macro por canal: 0,510182 |

Comparação **na validação usada para selecionar**; menor erro é melhor:

| Métrica | A/M1 | B0 = Bcanal |
| --- | ---: | ---: |
| MAE log médio por canal | 1,856909 | 1,976826 |
| MAE log por vídeo | 1,898253 | 1,935233 |
| MAE views por vídeo | 9.222,94 | 9.298,44 |
| Pinball q10 médio por canal | 0,554836 | 0,561935 |
| Pinball q50 médio por canal | 0,928454 | 0,988413 |
| Pinball q90 médio por canal | 0,510182 | 0,492700 |

O ganho de aproximadamente 6,1% na métrica principal é exploratório e pode refletir
seleção na própria validação. **q90 piorou** frente à referência: não resumir o
resultado como superioridade em todas as métricas. Bcanal coincide com B0 porque
os canais de validação não têm suporte no treino; nenhum histórico foi inventado.

| Setor na validação | Vídeos / canais com suporte | MAE log por canal A | MAE log por canal B0 | Cobertura da faixa A |
| --- | ---: | ---: | ---: | ---: |
| Beleza | 27 / 10 | 2,323990 | 2,453866 | 66,7% |
| Moda | 18 / 9 | 1,627840 | 1,793245 | 88,9% |

Três canais de validação têm referências nos dois setores. A cobertura global por
vídeo de A foi **75,6% (34/45)** e a média por canal, 74,5%; largura média de
7.697,75 views. Houve zero cruzamentos nas 45 previsões reais; os testes sintéticos
exercitam reparos e preservação de q50. A faixa nominal não tem cobertura validada.
A faixa descritiva de B0 cobriu 77,8% e teve largura média 22.785,72; não confundir
essa faixa do treino com um intervalo preditivo calibrado de baseline.

MAPE de A: 214,8%, excluindo quatro rótulos zero; sua instabilidade com contagens
pequenas impede chamá-lo de percentual de acerto. Acerto de pares por canal de A:
58,7%, com dez canais tendo pares comparáveis. Spearman médio de A: 0,1024 em nove
canais com suporte. B0 só tem Spearman estimável em três canais (muitas previsões
empatadas); essas médias não comprovam ganho em um conjunto comum de canais.
O aluno ainda deverá interpretar esses resultados e praticar o percurso documentado.

## Evidência e próximo passo

Bundle privado: `artifacts/issue-3-experimento-a-v1/`, com os três modelos
(31.920 / 109.152 / 43.072 bytes para q10/q50/q90), manifesto, relatório privado
por canal/linha de validação e `offline-verification.json`.

Checksum interno do artefato:
`9dd1c7a2e35e32cf3068395ed8bf2e0561aa4fecded5c31754f981cc13d70d59`.
Coorte, partições e baseline mantêm os checksums da
[liberação ampliada](https://github.com/leeunam/case-GALAXIES-IA/blob/0df616e5fd64dfc4947abde583f2664b66abf410/docs/issue-1-base-para-experimento-a.md).

A conferência real reimportou as evidências, verificou IDs de treino/validação,
recarga exata das previsões, conversão finita, preservação de q50 e recomputação
exata do relatório. Comparou hashes antes/depois de todos os 16 arquivos do pacote
de origem e dos quatro do baseline antigo: **20 inalterados**. Não foi criada
matriz, previsão ou métrica do teste. A leitura de seus registros ficou restrita
às validações de integridade do importador já aprovado.

A revisão independente, somente leitura, não encontrou problemas acionáveis em
vazamento, protocolo, métricas ou equivalência offline; 33 testes direcionados
passaram na revisão. O revisor também conferiu escolhas/artefatos e a fidelidade
deste resumo aos resultados reais. A suíte pública final do executor passou em
**284 testes**, incluindo erro nativo/privacidade da CLI; Ruff, formatação de 55
arquivos, lock offline e 130 dependências instaladas foram conferidos.
Os testes dispensam a base privada.

Unidade seguinte, [já implementada](issue-3-servico-m1.md): ligar a extração
congelada de inéditos ao bundle e servir
previsão/faixa/ranking na função e MCP, preservando os modos de baseline. A coorte
real só sustenta `text_status=extracted`; ausência de áudio/fala e falha de extração
devem produzir indisponibilidade explícita, sem trocar de modelo silenciosamente.
Os controles de compatibilidade, falhas e paridade real estão relatados na integração.
B/C, SHAP/explicador, LangGraph e avaliação final seguem nas respectivas issues.

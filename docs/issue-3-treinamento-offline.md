# Experimento A — treinamento offline

O bloco offline da #3 reutiliza a coorte e as partições da liberação ampliada.
A integração de M1 na função/MCP permanece uma etapa posterior da mesma issue.

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

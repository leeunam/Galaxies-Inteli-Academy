# Rotinas de partição e baseline — evidência sintética

Extensão autorizada em 18/10/2026. Estas rotinas preparam a implementação da #2;
resultados científicos reais continuam dependentes da base elegível da #1.
Nenhuma rotina de partição verifica licença, curadoria, datas ou elegibilidade.

## Manifesto de partições

`scripts/channel_partitions.py` oferece `create_partitions`, `freeze_partitions`
e `load_partitions`. As entradas contêm somente `sample_id`, `channel_id`, `sector`,
`media_sha256` e, opcionalmente, `duplicate_group`. Visualizações e outros rótulos
são recusados nesse contrato, para que o resultado não influencie a divisão.

Um canal inteiro pertence a uma partição. Canais conectados por hash de mídia ou
grupo de duplicatas/republicações reconhecidas formam um componente indivisível,
inclusive em cadeias transitivas. A detecção automática de novas republicações
não faz parte desta rotina; ela usa somente os vínculos fornecidos.

O algoritmo versionado usa semente 42 e alvos de aproximadamente 60%/20%/20% dos
canais para treino/validação/teste. A ordem das linhas não altera a saída, e um
canal com muitas publicações não recebe peso adicional na contagem de canais.

Componentes são estratificados pelo conjunto de setores presentes. Estratos com
pelo menos três componentes são distribuídos por déficit de canais, reservando
uma unidade para cada partição. Nos estratos esparsos, há no máximo seis componentes;
suas combinações são enumeradas para minimizar ausência de setores e, depois,
desvio das proporções. Empates são resolvidos por hash da semente e dos grupos.

O manifesto relata contagens efetivas de publicações, canais, componentes e setores
por partição. Grupos grandes podem impedir as proporções exatas. Setores ausentes
e poucos componentes geram avisos explícitos. Menos de três componentes independentes
gera erro, sem repartir publicações do mesmo canal para fabricar suporte.

O arquivo congelado tem esquema, algoritmo, semente, procedência declarada
(`synthetic` ou `unvalidated`), hashes, atribuições e suporte. A recarga verifica
integridade e reproduz a atribuição pelos metadados, detectando alterações de
partição mesmo se o checksum tiver sido recalculado. Escrita atômica com permissão
0600 não substitui arquivos existentes; uma mudança requer novo manifesto.
Hashes identificam o conteúdo, sem constituir assinatura de um revisor.

`real_results_available` é sempre `false`. A procedência declarada não comprova
que um conjunto é elegível. Os registros locais existentes não foram importados,
reclassificados ou usados para treino nesta extensão.

## Verificações da partição

Vinte casos sintéticos passaram: divisão por canal e setor, proporções e contagens,
ordem de entrada, semente, canais prolíficos, duplicatas transitivas entre canais,
grupos mistos esparsos, pouco suporte, contratos, congelamento sem sobrescrita e
detecção de adulteração. Isso verifica o algoritmo, não uma partição científica
real nem generalização preditiva.

## Baseline e faixa empírica somente no treino

`scripts/empirical_baseline.py` oferece `fit_baseline`, `estimate_baseline`,
`save_baseline` e `load_baseline`. O ajuste recebe o manifesto já congelado e
exatamente os pares `sample_id`/`view_count` da partição `train`. Rótulos de
validação/teste, IDs extras, ausentes ou repetidos são recusados. Contagens precisam
ser inteiros de 0 a `2**63 - 1`; não há coerção de strings, booleanos ou ausências.

O cálculo usa `y = log1p(view_count)` e devolve valores na escala original por
`expm1`. B0 é a mediana dos valores transformados no treino, por setor. Para uma
quantidade par de exemplos, isso é diferente da mediana direta das views: no
exemplo inventado `[0, 8]`, `expm1((log1p(0) + log1p(8))/2) = 2`.

A faixa por setor corresponde aos quantis empíricos 0,1 e 0,9 dos valores de treino
transformados. Para `n` valores ordenados, usa posição `(n - 1) * p` e interpolação
linear entre os vizinhos nessa escala, antes de aplicar `expm1`. O método está
versionado no artefato. Faixas degeneradas com pouco suporte são mantidas e avisadas.
Isso descreve a distribuição de treino; não é uma faixa individual calibrada nem
uma demonstração de cobertura de 80% em novos vídeos.

Bcanal é um comparador retrospectivo opcional da rotina: usa a mediana do canal
somente quando há suporte desse canal no treino, com fallback explícito para B0
no canal novo. Seu identificador serve a esse diagnóstico, sem ser acrescentado
às entradas do preditor ou da tool. A faixa continua sendo descritiva **do setor**.
O centro de Bcanal pode ficar fora dela: `central_outside_sector_range` sinaliza
isso, sem expandir os limites artificialmente ou apresentar os três valores como
quantis de um mesmo modelo condicional. O baseline principal B0 tem o centro e a
faixa derivados da mesma distribuição setorial.

Setor sem dados de treino retorna `unavailable`, motivo
`sector_training_support_missing`, sem zero ou fallback para outro setor. A saída
inclui procedência e suporte. `synthetic_baseline` identifica números de fixtures;
`unvalidated_baseline` identifica cálculos sem corpus validado. Nenhum dos estados
declara treinamento científico real: `real_results_available=false` e
`scientific_status=pending_issue_1` são fixos nesta versão.

O artefato contém versões, quantis/medianas, contagens de suporte, IDs de treino e
hashes do manifesto e dos rótulos usados. Salvar não sobrescreve arquivo existente.
A recarga exige o manifesto e os rótulos de treino: recalcula a referência para
rejeitar estatísticas alteradas, outra divisão ou contagens corrigidas. Não usa
pickle, executáveis ou pesos externos. Esses arquivos são de auditoria local;
armazenar somente em pastas privadas ignoradas pelo Git.

## Demonstração reproduzível

Na raiz do projeto, depois de instalar as dependências travadas:

```bash
rtk proxy uv run --frozen python -m scripts.demo_baseline
```

A demonstração gera metadados e contagens inteiramente artificiais de 20 canais,
40 referências e dois setores. Congela as partições, seleciona somente os rótulos
do treino, ajusta, salva/recarrega o baseline e mostra B0 e Bcanal com fallback.
O resultado tem 12 canais no treino, quatro na validação e quatro no teste; B0
sintético de 2 para moda e aproximadamente 999 para beleza. Esses números são
consequência das contagens inventadas `[0, 8]` e `[99, 9999]`, não desempenho de vídeos.
Por padrão os arquivos temporários são removidos ao encerrar normalmente.

Para guardar os artefatos sintéticos em um diretório novo e ignorado:

```bash
rtk proxy uv run --frozen python -m scripts.demo_baseline --output-dir artifacts/synthetic-baseline/run-001
```

Uma pasta não vazia é recusada antes de começar. O comando retorna erro JSON seguro
e código 1 em falhas de saída, sem exibir caminhos ou dados. Não há coleta de mídia,
leitura de `.env`, chamada NIM ou acesso à base privada existente.

## Limite da integração e verificações

O serviço público `analyze_creatives` e o MCP continuam retornando
`prediction_unavailable`: esses artefatos não são carregados automaticamente.
Um teste com cliente stdio real verifica a indisponibilidade mesmo depois de
criar artefatos sintéticos junto ao cadastro de teste. A demonstração numérica
é offline; a integração preditiva real exige resolver o checkpoint da #1.

Os 27 controles adicionais cobrem valores conhecidos, interpolação, zero,
contagens extremas, rejeição de rótulos de validação/teste, alteração somente
dos rótulos de treino, Bcanal e fallback, falta de suporte, faixas degeneradas,
procedência, persistência, adulteração e paridade de indisponibilidade Python/MCP.
Os resultados reais dos critérios 3 e 5 da issue original continuam pendentes.

Verificação integrada da extensão: **150 testes passaram** no ambiente de trabalho
e em ambiente temporário limpo instalado com `uv sync --frozen --offline` a partir
do cache. Ruff e formatação dos 37 arquivos Python aprovados; a demo foi reproduzida
também nesse novo ambiente. Não houve alteração de dependências ou dados reais.

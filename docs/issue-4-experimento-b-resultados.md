# Experimento B-cache na coorte de 300

**A primeira rodada multimodal melhorou a métrica principal na validação.** Na união de 66 casos, MAE log médio por canal foi 1,6584: 6,63% menor que A300 (1,7761) e 4,41% menor que A200 (1,7349). O ganho não é uniforme por setor ou métrica, não houve avaliação no teste e M1 atual foi preservado.

## Escopo executado e pendência VLM

Esta é a ablação **B-cache com CLIP e medidas técnicas de imagem/áudio**, conforme o [protocolo anterior aos ajustes](issue-4-experimento-b-protocolo.md). Nos 269 casos de desenvolvimento, VLM está `not_requested` e suas colunas continuam sem aprovação de treino. A camada Qwen não foi fabricada, extraída novamente ou usada. A execução não conclui o M2 com VLM nem todos os critérios da issue #4; essa etapa continua pendente, assim como C.

A base de 300 e as partições são as mesmas de A300: 203 referências/113 canais no treino, 66/37 na validação e os mesmos 31/16 no teste. Não houve nova coleta, atualização de views, alteração de coorte/manifesto ou de extratores.

| Grupo de entradas | Colunas |
| --- | ---: |
| Prefixo exato de A: setor, duração, proporção, estado de texto e MiniLM384 | 388 |
| CLIP dos mesmos frames cacheados | 512 |
| Brilho, saturação, RMS e duração do áudio | 4 |
| Estado de áudio | 1 |
| Total | **905** |

A fala/ASR/MiniLM já está em A e é compartilhada; B não mede o acréscimo de todo o áudio. Não há PCA, scaler ou imputação: ausência/valor inválido produz recusa explícita. `audio_status=transcribed` é constante nos 269 casos, sem informação variável à qual atribuir ganho. Títulos, datas, canal/IDs, métricas observadas, hashes, tempos de processamento e VLM não entram na matriz.

## Ajuste e artefato

Foram executados exatamente os 12 ajustes previstos: CatBoost CPU2, seed42, quantis 0,1/0,5/0,9, profundidades4/6 × L2 3/10, taxa0,05, máximo500/parada50. Rótulos log1p e pesos uniformes apenas no treino; validação/parada com inverso da frequência do canal. q50 por MAE log por canal, extremos por pinball por canal. Não houve nova busca ou mudança de representação após os resultados.

| Quantil | Profundidade | L2 | Árvores | Escore na validação ampliada |
| --- | ---: | ---: | ---: | ---: |
| 0,1 | 6 | 10 | 13 | 0,4610 |
| 0,5 | 4 | 10 | 218 | 1,6584 |
| 0,9 | 4 | 3 | 98 | 0,4120 |

Os ajustes somaram 90,83 s neste ambiente, sem extração de mídia e sem representar benchmark de latência de candidatos. Pesos foram persistidos em formato nativo, recarregados e produziram exatamente as mesmas previsões brutas do relatório nos 66 inputs de validação. O reparo mantém q50, usa mínimo/máximo dos três valores para os extremos e converte por expm1.

## Comparação nos mesmos casos

MAE log médio por canal; menor é melhor. Cada coluna avalia os quatro modelos nos mesmos IDs, entradas compartilhadas e rótulos. As métricas de A200/A300/B0 são exatamente as da comparação anterior, reconferidas sem retreino.

| Modelo | Originais: 45 vídeos/16 canais | Novos: 21 vídeos/21 canais | União: 66 vídeos/37 canais |
| --- | ---: | ---: | ---: |
| B0 ampliado | 2,0032 | 1,7915 | 1,8830 |
| A200 | 1,8569 | 1,6419 | 1,7349 |
| A300 | 1,9327 | 1,6568 | 1,7761 |
| B-cache300 | 1,7082 | 1,6204 | 1,6584 |

Frente a A300, B-cache reduz o erro 11,61% nos 45 originais, 2,20% nos 21 novos e 6,63% na união. Frente a A200, as reduções são 8,01%, 1,31% e 4,41%. O par principal é B-cache300/A300, com os mesmos 203 rótulos de treino e os mesmos 66 de seleção. A200 é controle adicional treinado em outro volume.

### Setores e regressões

| Conjunto/setor | A200 | A300 | B-cache300 |
| --- | ---: | ---: | ---: |
| Originais / moda | 1,6278 | 1,9408 | 1,7881 |
| Originais / beleza | 2,3240 | 2,2626 | 1,9734 |
| Novos / moda | 1,0116 | 1,0239 | 1,2084 |
| Novos / beleza | 2,0298 | 2,0464 | 1,8740 |
| União / moda | 1,3378 | 1,5093 | 1,5153 |
| União / beleza | 2,1577 | 2,1404 | 1,9172 |

O ganho agregado vem principalmente de beleza. Na união, moda piora ligeiramente frente a A300 e permanece pior que A200. Os novos canais de moda também pioram. Médias por setor usam seus próprios canais e não são uma decomposição aditiva da média global.

### Outras métricas na união de 66

| Métrica | B0 ampliado | A200 | A300 | B-cache300 |
| --- | ---: | ---: | ---: | ---: |
| MAE views micro | 8329,3863 | 8266,1382 | 8249,9097 | 8007,8255 |
| Pinball log q10 por canal | 0,4971 | 0,4603 | 0,4631 | 0,4610 |
| Pinball log q50 por canal | 0,9415 | 0,8674 | 0,8881 | 0,8292 |
| Pinball log q90 por canal | 0,4539 | 0,4435 | 0,4083 | 0,4120 |
| Cobertura micro | 0,7879 | 0,7576 | 0,7121 | 0,7576 |
| Cobertura média por canal | 0,7500 | 0,7545 | 0,7342 | 0,7680 |
| Largura média em views | 26925,6669 | 7554,2020 | 8597,4608 | 9322,8513 |
| Largura média em log | 5,9289 | 4,9758 | 5,0022 | 4,8806 |
| Spearman médio por canal | -0,2467 | 0,1024 | -0,0192 | 0,2070 |
| Canais com Spearman estimável | 3 | 9 | 9 | 9 |
| Acerto de pares médio por canal | 0,4533 | 0,5867 | 0,4533 | 0,6417 |
| Canais com pares comparáveis | 10 | 10 | 10 | 10 |

Cobertura é fração. B-cache melhora cobertura micro frente a A300 (71,21% → 75,76%), iguala A200 e melhora ranking nos canais estimáveis; isso não garante cobertura nominal ou desempenho prospectivo. A perda q90 piora ligeiramente frente a A300 (0,4083 → 0,4120), apesar de melhorar frente a A200. As faixas B0 são descritivas do treino, e as de A/B são estimadas, sem calibração validada.

O ranking de A/B usa apenas nove canais para Spearman e dez para pares. B0 tem Spearman estimável em só três. Os 21 canais novos têm um caso de validação cada, logo não acrescentam suporte para ranking dentro de canal. Os relatórios privados incluem todas as métricas por setor/canal.

## Alto alcance continua limitado

Mantidos os limiares fixos do treino original: moda6.403,5 e beleza33.835,3. São quatro casos/três canais originais mais um caso/um canal novo, total **cinco casos/quatro canais**. Não foram redefinidos limiares para favorecer B.

| Diagnóstico dos cinco casos | B0 ampliado | A200 | A300 | B-cache300 |
| --- | ---: | ---: | ---: | ---: |
| MAE log por canal | 4,0649 | 3,7439 | 3,3041 | 2,9681 |
| Erro log com sinal por canal | -4,0649 | -3,7439 | -3,3041 | -2,9681 |
| Fração subestimada por q50 | 1,0000 | 1,0000 | 1,0000 | 1,0000 |
| Mediana (observado+1)/(previsto+1) | 40,0002 | 22,7831 | 25,9097 | 12,2571 |
| Fração acima do limite superior | 0,6000 | 0,6000 | 1,0000 | 0,8000 |

B-cache reduz o erro log e a mediana da razão nesse recorte, mas **todos os cinco casos continuam subestimados**. Quatro ficam acima do limite superior, contra cinco em A300 e três em A200. A mediana da razão ainda é 12,26. A validação segue sem qualquer vídeo de um milhão de views: não foi demonstrada correção da subestimação da demo de 2,32 milhões nem capacidade geral de prever viralidade.

## Interpretação e isolamento

Há ganho descritivo de validação com o grupo CLIP + sinais técnicos, sob este protocolo de seleção. Não foi isolada a contribuição individual de imagem, cor ou RMS; configurações/iterações são selecionadas separadamente. A validação também guiou parada/escolha, a amostra é de conveniência e a curadoria é assistida. Estes números não são avaliação final independente, efeito causal ou retorno de mídia paga.

Antes de qualquer leitura de rótulo/evidência, o carregador valida os metadados de ascendência, os 200 registros/assignments antigos e o tuple exato de teste. O CLI também ancora coorte/partições nos hashes de A300. A guarda ativa recusa arquivos mistos antigos e os caminhos de evidências do teste. Não houve matriz, previsões ou métricas de teste.

Os **31 arquivos congelados** de M1/A200, A300, coorte/B0 e serviço permaneceram idênticos. O bundle B fixa 14 fontes de representação, treinamento, carregamento, partições, baseline e persistência, além de modelos/runtime/lock. A auditoria cobriu 538 caminhos únicos de evidência de desenvolvimento; os extras são relidos com novo checksum, sem alterar os fontes congelados de A. Zero aquisição de mídia e zero sessão temporária restante.

**M1 atual não foi substituído**, e função/MCP continuam nos modos anteriores. C não começou. VLM continua pendente: esta rodada não deve ser apresentada como CatBoost com Qwen validado nem como conclusão de toda a issue #4.

## Reprodução e resultados privados

Executar na raiz, com o ambiente travado e os dados privados existentes. Os diretórios de saída são exclusivos; repetir treino com diretório já existente é recusado. Não refazer ajuste para tentar melhorar as métricas desta rodada.

```bash
rtk proxy env OPENBLAS_NUM_THREADS=1 .venv/bin/python -m scripts.train_experiment_b train \
  --parent data/private/issue-1-pool-treino-20261018-v6/released-cohort-v1 \
  --cohort-dir data/private/issue-3-expansao-300-v1/released-cohort-v1 \
  --model-dir artifacts/issue-4-experimento-b-300-v1

rtk proxy env OPENBLAS_NUM_THREADS=1 .venv/bin/python -m scripts.train_experiment_b compare \
  --parent data/private/issue-1-pool-treino-20261018-v6/released-cohort-v1 \
  --cohort-dir data/private/issue-3-expansao-300-v1/released-cohort-v1 \
  --model-dir artifacts/issue-4-experimento-b-300-v1 \
  --report data/private/issue-4-experimento-b-300-v1/comparison.json
```

- Bundle: `artifacts/issue-4-experimento-b-300-v1/`.
- Comparação, snapshot anterior, preflight e prova final: `data/private/issue-4-experimento-b-300-v1/`.
- Artefato B: `0ad468f10e3746e579f3d5b23e487b1dc743e62361bea29075d23a41138c070b`.
- Comparação SHA256: `26433487179a4602e2cbd24c81521cee82576de94eec8024e0f2e26fc7329ca5`.
- Coorte/partições preservadas: `2ca9af4ed875875cdc0a813ed8a9283489d6e7708dcd0c2b650eeaed904fea59` / `66fbcb36a1a908428f0fd2096b7aef47e26b883efbf6461a22127ea563ee2738`.

Passaram **420 testes públicos**, incluindo ajuste CPU nativo em fixtures sintéticos, fronteira de rótulos, alterações de partição recusadas antes de evidência, corrupção/incompatibilidade de bundle e paridade de recarga. Ruff e formatação passaram nos 80 arquivos Python. A execução real teve 12 ajustes, recarga com paridade exata e conferência de seleção/splits/checksums, seguida de revisão independente somente leitura. Dados, modelos, transcrições e relatórios detalhados permanecem fora do Git.

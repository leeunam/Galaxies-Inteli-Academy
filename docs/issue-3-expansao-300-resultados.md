# Expansão para 300 — retreino e comparação de B0/A

Este relatório preserva o checkpoint anterior a B. Posteriormente,
[B-cache foi executado e comparado](issue-4-experimento-b-resultados.md) nas
mesmas partições; a parte VLM ainda não foi liberada para treino. As métricas
e conclusões de A abaixo permanecem as registradas naquela execução.

**A ampliação foi concluída e os modelos foram comparados, mas A300 não superou A200 na métrica principal.** Nos mesmos 45 casos originais, o MAE log médio por canal piorou 4,08%; na união de 66, piorou 2,38%. Há ganhos pontuais, incluindo a perda q90 e o erro log médio no recorte de alto alcance, acompanhados de regressões de cobertura e ranking. O teste reservado permaneceu fechado e B não começou.

## Dados e execução

A [publicação verificada](issue-3-expansao-300-execucao.md) tem 300 referências/166 canais: 203 de treino, 66 de validação e os mesmos 31 de teste. As 100 adições foram alocadas antes das views: 79 treino e 21 validação, sem novo teste. Os 200 metadados/assignments e as 169 linhas antigas de desenvolvimento permaneceram idênticos. B0 foi recalculado apenas com os 203 rótulos de treino.

A executou exatamente os 12 ajustes registrados, sem busca adicional após os resultados: 388 entradas, alvo log1p, quantis 0,1/0,5/0,9, profundidades 4/6 × L2 3/10, taxa 0,05, seed 42, CPU 2, até 500 iterações/parada 50. Treino com pesos uniformes; validação e parada com pesos por canal. Os ajustes somaram 34,41 s, sem incluir extração ou preparação dos dados.

| Quantil | Profundidade | L2 | Árvores selecionadas | Escore na validação ampliada |
| --- | ---: | ---: | ---: | ---: |
| 0,1 | 4 | 3 | 3 | 0,4631 |
| 0,5 | 4 | 3 | 139 | 1,7761 |
| 0,9 | 4 | 10 | 71 | 0,4083 |

q50 foi escolhido por MAE log por canal; extremos por perda quantílica por canal, antes do reparo conjunto. O reparo preserva q50 e amplia extremos para mínimo/máximo das saídas brutas. Os três modelos foram persistidos, recarregados e produziram previsões brutas exatamente iguais ao relatório nos mesmos 66 inputs de validação. Não houve reajuste na união treino/validação.

## Métrica principal: quatro modelos nos mesmos conjuntos

MAE log médio por canal; menor é melhor. Cada canal tem o mesmo peso dentro de cada conjunto. Não comparar diretamente a coluna de 45 com a de 66 como se fossem os mesmos casos.

| Modelo | Originais: 45 vídeos/16 canais | Novos: 21 vídeos/21 canais | União: 66 vídeos/37 canais |
| --- | ---: | ---: | ---: |
| B0 original (200) | 1,9768 | 1,8209 | 1,8883 |
| A original (200) | 1,8569 | 1,6419 | 1,7349 |
| B0 ampliado (300) | 2,0032 | 1,7915 | 1,8830 |
| A ampliado (300) | 1,9327 | 1,6568 | 1,7761 |

A300 ainda supera B0 ampliado na união (1,7761 contra 1,8830), mas fica atrás de A200 nos três conjuntos. O B0 ampliado piora nos 45 casos antigos e melhora ligeiramente na união. Não usar a melhora de B0 na união para atribuir ganho à representação de A.

A regressão de A concentra-se em moda; beleza melhora ligeiramente:

| Conjunto/setor | A200 | A300 |
| --- | ---: | ---: |
| Originais / moda | 1,6278 | 1,9408 |
| Originais / beleza | 2,3240 | 2,2626 |
| União / moda | 1,3378 | 1,5093 |
| União / beleza | 2,1577 | 2,1404 |

Os relatórios privados incluem todos os setores e canais; as médias por setor usam seus próprios canais e não são uma decomposição aditiva da média global.

## Diagnósticos na união de 66

| Métrica | B0 original | A200 | B0 ampliado | A300 |
| --- | ---: | ---: | ---: | ---: |
| MAE views micro | 8341,9905 | 8266,1382 | 8329,3863 | 8249,9097 |
| Pinball log q10 por canal | 0,4735 | 0,4603 | 0,4971 | 0,4631 |
| Pinball log q50 por canal | 0,9442 | 0,8674 | 0,9415 | 0,8881 |
| Pinball log q90 por canal | 0,4302 | 0,4435 | 0,4539 | 0,4083 |
| Cobertura micro | 0,7727 | 0,7576 | 0,7879 | 0,7121 |
| Cobertura média por canal | 0,7635 | 0,7545 | 0,7500 | 0,7342 |
| Largura média em views | 22951,7725 | 7554,2020 | 26925,6669 | 8597,4608 |
| Largura média em log | 5,6743 | 4,9758 | 5,9289 | 5,0022 |
| Spearman médio por canal | -0,2467 | 0,1024 | -0,2467 | -0,0192 |
| Acerto de pares médio por canal | 0,4533 | 0,5867 | 0,4533 | 0,4533 |

Cobertura é fração, não porcentagem. As faixas de B0 são descritivas do treino; as de A são estimadas e não calibradas. A perda q90 de A melhora de 0,4435 para 0,4083, mas a cobertura micro cai de 75,76% para 71,21%; o ganho dessa perda não demonstra calibração. O MAE views melhora muito pouco enquanto a métrica principal piora.

O ranking por canal tem suporte em apenas nove canais para Spearman e dez para pares. Os 21 novos canais têm uma referência de validação cada: não acrescentam pares dentro de canal e o ranking desse subconjunto não é estimável. Na união, o acerto de pares cai de 0,5867 para 0,4533.

## Alto alcance: mesmo recorte, suporte ainda pequeno

Foram mantidos os p90 do treino original: moda 6.403,5 e beleza 33.835,3 views. Eles não foram redefinidos pelos resultados. São quatro vídeos/três canais nos 45 antigos e um vídeo/um canal nos 21 novos; a união tem **cinco vídeos/quatro canais**.

| Diagnóstico dos cinco casos | B0 original | A200 | B0 ampliado | A300 |
| --- | ---: | ---: | ---: | ---: |
| MAE log por canal | 4,2334 | 3,7439 | 4,0649 | 3,3041 |
| Erro log com sinal por canal | -4,2334 | -3,7439 | -4,0649 | -3,3041 |
| Fração subestimada por q50 | 1,0000 | 1,0000 | 1,0000 | 1,0000 |
| Mediana (observado+1)/(previsto+1) | 46,4681 | 22,7831 | 40,0002 | 25,9097 |
| Fração acima do limite superior | 1,0000 | 0,6000 | 0,6000 | 1,0000 |

O erro log médio por canal nesse recorte melhora (3,7439 → 3,3041), mas **todos os cinco continuam subestimados**. A mediana da razão piora (22,78 → 25,91) e os cinco ficam acima do limite superior de A300, contra três em A200. Essas estatísticas resumem os mesmos poucos casos com agregações diferentes; não há contradição em uma melhorar e outra piorar. Nos quatro casos originais, a mediana da razão melhora de 20,53 para 17,01, mas a subestimação e o baixo suporte continuam.

O treino ganhou exemplos extremos: de quatro para nove com ≥100 mil views e de um para três com ≥1 milhão. O recorte fixo de alto alcance no treino passou de 13 para 28 casos. O p90 descritivo ampliado é 13.246,2 em moda e 35.935,0 em beleza; ele não substituiu os limiares fixos. A validação ampliada continua sem qualquer vídeo de um milhão de views e tem apenas um acima de 100 mil. Não foi demonstrada capacidade de reconhecer alcance de milhões ou de corrigir a subestimação vista na demonstração externa, que segue fora da coorte.

## Interpretação e sequência

A ampliação trouxe mais canais e exemplos extremos, sem produzir ganho geral de A nesta rodada. A validação foi usada para parada/escolha de modelos nas duas versões; não é uma avaliação final independente. A validação ampliada também alterou a configuração/iteração selecionada, portanto não foi isolado um efeito causal puro do aumento de dados. A amostra permanece de conveniência adaptativa, com curadoria assistida e sem auditoria humana independente de acurácia dos extratores.

Não houve mudança de perdas, pesos, representação, limiares ou dados após esses resultados, nem ajustes adicionais. O serviço continua usando M1 original; estes resultados não justificam sua substituição por A300. B não foi iniciado. Quando autorizado, B deve usar a mesma coorte e as mesmas partições de A300 para uma ablação pareada; A200 pode permanecer como controle adicional, sem substituir esse par.

## Artefatos e verificação

- Coorte/B0: `data/private/issue-3-expansao-300-v1/released-cohort-v1/`.
- Modelos A300: `artifacts/issue-3-experimento-a-300-v1/`.
- Comparação, distribuições e provas: `comparison.json`, `development-distribution.json` e `training-comparison-verification.json` no pool privado.
- Artefato A300: `905b4886920f29d741f2e349444d2eea523178bfffda6a8aa82a56f82ad914c2`.
- Comparação SHA256: `8b31d5c02fa21f197994f7ba8107bb2cfa241839ef66d347748b6763b55a5790`.

Dados, rótulos, modelos e relatórios detalhados permanecem fora do Git. Os [comandos reproduzíveis](issue-3-expansao-300-ferramentas.md) usam o carregador restrito e a guarda do teste. Foram verificados os 12 ajustes, IDs de treino/validação, seleção mínima por quantil, recarga com paridade exata e comparação nos mesmos casos. Os 16 hashes antigos permitidos seguem idênticos. Não houve leitura de arquivos mistos antigos, evidências/rótulos do teste, previsões ou métricas reservadas.

Nesta retomada passaram os 26 testes direcionados de sondagem/extração/publicação, Ruff e formatação de 75 arquivos. A suíte completa anterior passou em 388 testes e não houve mudança de código nesta rodada. Coleta/publicação e treino/comparação tiveram revisão independente somente leitura, com commits separados por unidade verificada.

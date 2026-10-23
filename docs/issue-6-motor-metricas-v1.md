# P6 — motor de métricas preparado sem abrir o teste

Unidade de 23/10/2026, base `a9bdc17`. O procedimento científico continua
`p6-final-procedure-v1`. Esta implementação não muda critérios, não carrega
artefatos e não concede autorização para acessar o teste reservado.

`scripts.final_evaluation_metrics.evaluate_predictions` recebe somente objetos
em memória, com IDs ordenados e exatamente as mesmas linhas para B0, Bcanal,
A300, B completo e C completo; A200 é controle adicional permitido. O padrão
é exigir 31 linhas. Outro tamanho precisa ser explícito, como nos testes
inventados e no futuro diagnóstico de desenvolvimento.

Cada linha de cada modelo contém os três quantis brutos ou um código estático
de falha. Faltas silenciosas, modelos ausentes, duplicatas, ordem diferente,
NaN e quantis fora dos limites físicos são recusados. Falhas declaradas ficam
no denominador total e nos recortes por setor/canal; não viram zeros. Métricas
de um conjunto parcialmente disponível são marcadas como parciais.

O relatório contém MAE log por canal/vídeo, MAE views por canal/vídeo, MAPE
com suporte e zeros excluídos, perdas quantílicas, cobertura, largura e
cruzamentos. Reutiliza o reparo que preserva q50 e as fórmulas de ranking
existentes: Spearman intra-canal precisa de três vídeos e variação; empates
no alvo não geram pares e empates na previsão recebem meio crédito. Exibe
suporte por setor/canal, inclusive células vazias. A300→B e B→C usam o mesmo
subconjunto pareado; se houver falhas, a interseção é somente diagnóstico.

Conserva por caso os quantis brutos/servidos, falhas e erros, além dos cinco
maiores erros em log e views, com desempate por ID. **Essa saída é privada**:
uma futura projeção sanitizada precisa de revisão antes da publicação.
As faixas B0/Bcanal são identificadas como descritivas do treino.

Verificação: 15 testes inventados passaram em 0,16 s no clone independente,
sem arquivos científicos, pesos, rede, fit ou inferência. Cobrem resultados
analíticos, peso por canal, empates, cruzamentos, falhas completas/parciais,
modelos/linhas ausentes e valores inválidos. A contagem não é avaliação de
15 criativos reais.

```sh
rtk proxy .venv/bin/python -m pytest -q tests/test_final_evaluation_metrics.py
```

Este motor é uma peça do futuro executor: ainda faltam carregadores estáticos
restritos dos artefatos efetivos, conferência de identidades e aceites reais,
reserva exclusiva/durável, limites operacionais, revisão e autorização
específica de abertura. O preflight de metadados existente continua sem
autoridade de acesso ou inferência. Nenhuma função deste módulo seleciona,
retreina ou promove modelos pelo teste.

A revisão independente em leitura pediu propagar o motivo de Spearman não
estimável, já presente no cálculo histórico. O relatório agora conserva esse
status por canal e na correlação global, além de indicar falta de canais com
suporte na agregação. Os 15 testes de métricas passaram em 0,32 s após essa
correção; Ruff/formatação passaram. O parecer não transforma os testes em
avaliação científica ou em revisão dos artefatos finais ainda inexistentes.

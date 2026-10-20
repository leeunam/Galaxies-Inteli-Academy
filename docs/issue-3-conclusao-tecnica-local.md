# Issue #3 — conferência de conclusão técnica local

Conferência em 19/10/2026. Os cinco critérios técnicos de A e de sua integração
estão implementados localmente. Isso não encerra a issue remota, não substitui a
demonstração/explicação pelo aluno e não aprova qualidade preditiva ou cobertura.
O teste reservado continua fechado; sua avaliação pertence à #6.

## Critérios e evidências

| Critério | Implementação e prova verificável |
| --- | --- |
| Isolamento por canal/duplicata; ajuste sem teste | `channel_partitions.py`, `training_manifest.py` e `experiment_a_data.py` validam as fronteiras. A200 usa 124/45/31; a [expansão](issue-3-expansao-300-execucao.md) preservou as atribuições antigas e publicou 203/66/31. Não houve previsão ou métrica dos 31 reservados. Commits `c346dc6` e `d5567f3`. |
| Mesma política de fala/embedding; silêncio e falhas explícitos | `training_manifest.py`, `candidate_features.py` e `m1_service.py` compartilham versões/política de extração. A [integração real](issue-3-servico-m1.md) demonstra igualdade Python/MCP para 1, 2 e 5 cadastros; o controle sem áudio retorna indisponibilidade explícita, sem fabricar previsão. Commits `574cd28` e `0fc788b`. |
| Bundle e features compatíveis; inversão e quantis servidos | `experiment_a_artifact.py`, `experiment_a_metrics.py` e `train_experiment_a.py` verificam hashes, finitude, inversão e limites; o reparo preserva q50. O bundle A200 tem três modelos q10/q50/q90, 388 features e 12 ajustes; a recarga e a avaliação usam a forma servida. Commits `50edb41` e `35762e3`. |
| Comparação pareada com baselines; ausência de outcomes nas features | A [avaliação offline](issue-3-treinamento-offline.md) compara A/B0/Bcanal nas mesmas referências elegíveis. O [retreino A300/B0](issue-3-expansao-300-resultados.md) usa a mesma união de validação e mantém A200 como controle. Views observadas e estatísticas atuais do canal não entram como atributos. Commit da comparação ampliada: `0188547`. |
| Função/MCP com previsão, faixa, ranking e limites | `creative_analysis.py`, `creative_contracts.py`, `creative_cli.py`, `creative_mcp.py` e `m1_service.py` preservam os modos baseline e oferecem M1 explicitamente configurado. Contrato, estados, ranking e paridade real estão na [demonstração](issue-3-servico-m1.md). Commits `574cd28`, `0fc788b` e `ae3a6f6`. |

O artefato servido continua sendo M1/A200, SHA256
`9dd1c7a2e35e32cf3068395ed8bf2e0561aa4fecded5c31754f981cc13d70d59`.
A300 e B-cache permanecem comparadores offline, sem promoção. A expansão não
superou A200 na métrica principal; o [B-cache posterior](issue-4-experimento-b-resultados.md)
melhorou essa métrica na união de validação, com limitações por setor e quantil.
A parte VLM de B ainda não foi liberada para treino.

## Verificação e limites

Uma conferência independente somente leitura recarregou o bundle real com a
configuração congelada, conferiu os 30 hashes do recibo de integração e oito
fontes de serviço, sem diferenças. Releu os recibos das três paridades positivas
e da ausência de áudio; não refez download nem inferência real. Os resultados
estão nos recibos privados de integração já existentes e na auditoria local
`/tmp/galaxies-issue3-audit-wwl6pbjr/`. Esta última é evidência auxiliar temporária;
os recibos originais em `data/private/issue-3-m1-demo-real-v1/` são a fonte durável.
A suíte pública atual passou em 597 testes, incluindo A, bundle, extração,
contratos, baseline, CLI e MCP; Ruff e formatação passaram.

As paridades positivas reutilizaram um único criativo em cadastros distintos.
Elas verificam o transporte e a extração real, sem demonstrar diversidade de
criativos ou qualidade geral. O exemplo externo de 2.316.115 views recebeu
estimativa de 1.520,52, com faixa 49,40–16.189,49; essa subestimação segue
documentada e não foi corrigida por retuning do exemplo. O ranking sem empates
é coberto pelos testes públicos, sem atribuí-lo às cópias da demonstração.

Pendências: explicação dos conceitos pelo aluno, aceite/encerramento remoto,
experimentos restantes e avaliação final após congelamento aprovado. Nenhuma
dessas pendências autoriza abrir o teste, promover outro modelo ou tratar uma
faixa exploratória como calibrada. Os documentos anteriores preservam seus
checkpoints históricos; esta conferência indica o estado técnico posterior.

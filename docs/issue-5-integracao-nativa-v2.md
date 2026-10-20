# Issue #5 — integração local nativa v2

Base autorizada: `69a5832ffccbd6830c3b1c39a4c75f2d1f93e307`.
Implementação em clone Git independente `/tmp/galaxies-issue5-native-v2`.
Não altera a árvore principal, fontes anteriores, locks ou ambientes existentes.

## Handoff

`m1_handoff_v2.py` conserva a validação de entrada e liga apenas dois nomes em
uma cópia privada do namespace de `serve_m1`: carregamento e extração. Ambos
delegam no momento original, capturando resultados sem antecipar processamento.
A autoridade original calcula números, estados, intervalos e ranking.
Hashes fixos recusam mudanças das três fontes das quais depende essa ligação.

Cada sessão é consumida antes de operar. Features são congeladas e vinculadas
à ordem dos IDs, registros conferidos, configuração e artefato. Somente uma
previsão efetivamente disponível pode fornecer inputs para evidências.

Os testes de handoff usam modelo e extração inventados, identificados como tal;
não demonstram percepção real, qualidade preditiva ou explicação por provedor.
A integração das etapas seguintes será registrada com suas provas efetivas.

Primeira unidade: 22 testes de handoff passaram em 13,62 s; Ruff e formatação
conferidos. A verificação inicial encontrou 1.270 pins originais iguais e
acrescentou 35 hashes dos recibos finais, em prova privada no clone.

Revisão do supervisor: o handoff também vincula o digest do relatório inteiro
à resposta da autoridade, antes de liberar qualquer input. Passaram 27 testes
em 16,85 s, incluindo q50, faixa, ranking e disponibilidade adulterados.

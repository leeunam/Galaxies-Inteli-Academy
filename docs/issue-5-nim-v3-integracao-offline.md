# Issue #5 — integração local offline do dispatcher NIM v3

Integração autorizada em 20/10/2026, com um único escritor após o encerramento
da V16. Base exata: `7675c3ed35bd928c5f75c1759c22586c69a24ded`.
A branch `codex/issue-4-v16-ordem-serializacao` foi preservada nesse commit.
A nova branch local é `codex/issue-5-nim-v3-integracao-offline`.

O fetch usou exclusivamente o clone local `/tmp/galaxies-nim-dispatch-v3`, limpo
em `c108b2453c6adcaee069db64650dd81e60507c4e`. Os dois commits foram aplicados
sequencialmente, sem conflito e sem alterar fontes anteriores:

| Origem no clone | Commit na integração | Conteúdo |
| --- | --- | --- |
| `ed5b0e5da33e9352683aafa90087a1072f480809` | `5a15f51` | Dispatcher, plano/ledger novos, testes e limites offline |
| `c108b2453c6adcaee069db64650dd81e60507c4e` | `867e93a` | Correção da conferência de aceitação na IPC do pai |

Os dez arquivos importados são byte a byte iguais à entrega corrigida. A
[revisão anterior](issue-5-nim-dispatch-v3.md) continua no histórico; somente a
segunda revisão recusa sucesso com IDs repetidos ou `wire_bytes=0`. A projeção
de IDs duplicados permanece permitida como diagnóstico corretamente rejeitado.
Não se alterou a autoridade selada v2 para obter essa concordância.

## Verificações na árvore principal

Passaram **110 testes raiz em 10,86 s**: os 108 direcionados da entrega e duas
regressões da integração #5, cobrindo indisponibilidade de previsão com motivo
da autoridade e cancelamento durante criação do filho. No ambiente isolado,
passaram **5 testes em 0,21 s**: quatro motivos sem pacote e cancelamento do
subgrafo sem renderização/repetição. Foram executados em sequência, com fixtures
inventadas e subprocessos locais, sem inferência ou mídia nova.

Ruff e formatação passaram nos oito arquivos Python v3. Não houve suíte completa,
prova com mídia gerada, execução de modelo, instalação ou sincronização de
ambiente. Os resultados históricos das suítes completas permanecem associados
aos seus commits anteriores, não a esta integração.

Plano/selo v3 conferidos:
`22713f5a7cc5f067ef330470f13f9d0c24698b8002a2c8af5938e2cf8581d9b5`.
Seus **130 pins de fontes** são iguais aos do clone. Fixture:
`0fb7b9797cd41f53c3f127b0d2f6f934d0696aa3ba288852f5cff616455cf438`.
O payload HTTP congelado também permaneceu idêntico.

## Preservação e reentrada V16

Antes de integrar foram inventariados **9.944 hashes**, incluindo os 1.423 pins
do plano V16, suas nove fontes, os 24 raws, filas ativa/aposentada, marcador de
supersessão, provas e relatório finais, fontes anteriores e recibos da integração
#5. O inventário ampliado inclui arquivos de testes antigos; um arquivo chamado
`.env` nesse namespace foi excluído antes de abrir, sem excluir nenhum pin
herdado. README e credenciais permaneceram fora da leitura e do staging.

As conferências antes e depois dos testes preservaram todos os 9.944 hashes.
Os ambientes atuais conferem com o registro protegido da V16: **130 distribuições
raiz e 42 isoladas**, sem mudanças. O inventário vivo de versões desta integração
foi feito após os cherry-picks e antes dos testes; seu baseline anterior é o
registro da V16. Nenhuma operação de ambiente ocorreu entre esses marcos.

Runtime/pesos foram verificados somente por leitura. M1/A200 e seus três modelos,
A300/B-cache, integração #5, partições 203/66/31 e teste reservado permaneceram
sob guardas. O holdout não recebeu leitura semântica de features, rótulos,
previsões ou métricas. M1 continua `final_test_evaluated=false`.
As oito folhas foram conferidas, com os 32 crops reproduzidos somente em memória
e hashes/tempos iguais; nenhum novo arquivo de imagem ou aquisição foi criado.

O carregador selado V16 reconstruiu/conferiu seu estado e relatório. A reentrada
real no executor recebeu um invocador proibido e foi recusada por
`v16_consumed_or_uncertain_no_retry`, antes de invocá-lo. Os locks existentes
foram usados para exclusão; os comprovantes e o checkpoint conservaram seus bytes.
Essa prova foi repetida depois dos testes, com **zero chamadas ao invocador**.

Permanecem **24 chamadas consumidas, 24 raws completos e dez chamadas encerradas**,
sem novo orçamento. Item_first continua com 0/12 negativos corretos e state_first
com 11/12, incluindo `lines=unknown`; nenhuma condição atingiu 12/12. Nenhum
positivo foi executado, nenhuma candidata indicada, coluna liberada, auditoria
iniciada ou treino B/C realizado. Não há continuação implícita pelo saldo.

## Limites e recibos

`remote_execution_released=false` e `REMOTE_PLAN_SHA256=None` permanecem
obrigatórios. O ledger remoto v3 estava ausente antes/depois; os testes usaram
somente diretórios novos de simulação. Não houve HTTP NIM, leitura de chave,
reutilização do ledger consumido v1, proxy, retry, publicação, push ou deploy.
A integração não comprova R$0 aplicável ao acesso existente: seu enquadramento,
limites/créditos e eventual cobrança continuam sem evidência de conta.

Esta entrega integra a preparação offline. Não demonstra provedor real, grafo
remoto, aderência, qualidade científica ou aceite humano. As pendências da #5
e da investigação VLM continuam abertas. Os limites de durabilidade, morte
forçada do pai e captura HTTP estão no documento do dispatcher e permanecem
inalterados. A auditoria final não encontrou workers ou subprocessos pendentes.

Recibos novos e exclusivos:
`data/private/issue-5-nim-v3-integracao-offline-20261020/`.
`before.json`, `import-verification.json`, `before-tests.json`, os dois JUnit e
`final.json` registram inventário, importação, testes e guardas. O verificador
privado é próprio desta integração; não reexecuta ou sobrescreve comprovantes
V16/#5 antigos. Os diretórios de testes são identificados como fixtures locais.
O recibo de conclusão registra hashes e commits finais após este documento.

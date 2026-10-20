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
Seus resultados finais são registrados na unidade seguinte.

Recibos privados exclusivos desta integração:
`data/private/issue-5-integracao-v2-20261020/`. A tentativa `generated-native-v1`
permanece registrada como falha; não é convertida retrospectivamente em sucesso.
Não houve NIM, VLM, aquisição de mídia, abertura do holdout ou publicação.
A explicação por provedor, três mídias reais distintas e aceite humano continuam
pendentes; a #5 permanece aberta.

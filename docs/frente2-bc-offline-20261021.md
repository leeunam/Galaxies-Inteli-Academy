# Frente 2 — preparação offline de B/C

Base: `277804223eb6121dbeb541c0663af89ccf334eac`. Clone independente
`/tmp/galaxies-front2-bc-offline-20261021`, branch `codex/front2-bc-offline`.
Nenhum alternate/hardlink Git; `.env`, README não rastreado, dados, modelos e
ambientes não foram copiados. A principal permanece somente leitura.

## Correção da fronteira de B

`validate_data` validava o cache e recalculava o baseline a partir dos rótulos
em memória antes de revalidar a liberação perceptiva. Agora revalida o contrato
e o hash do código do gate antes desse acesso. `compare` também chama essa
guarda antes das métricas dos comparadores. Testes inteiramente inventados
interceptam ambos os acessos e exigem recusa de liberação inválida/alterada.

Não muda features, partições, grade CatBoost, tolerâncias, gates, pesos ou
artefatos existentes. Como os bundles fixam hashes de fontes, a mudança exige
novos artefatos em uma futura execução autorizada; não alterar os hashes de
bundles antigos para fazê-los carregar sob o código novo.

## Estado científico

A = CatBoost com metadados/texto; B = CatBoost com o prefixo B-cache de 905
colunas e somente atributos VLM aprovados; C = LightGBM com as mesmas entradas
completas de B. B-cache não substitui B completo. As 300 referências e as
partições 203/66/31 estão preservadas; nenhum arquivo real de dados, features,
rótulos ou teste foi aberto por esta frente.

Extração completa, treino real e comparação científica continuam bloqueados
pela evidência visual válida da Frente 1 e por nova autorização operacional.
Não preencher atributos com valores inventados/`unknown` para simular aceite,
não reutilizar auditorias reveladas como aprovação independente e não afrouxar
os gates. Não houve inferência visual, encoder/loader, mídia, POST NIM,
instalação, alteração de ambiente, gasto, publicação ou fechamento de issue.

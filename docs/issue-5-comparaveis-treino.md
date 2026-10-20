# Issue #5 — comparáveis locais restritos ao treino de M1

Fatia local de 20/10/2026, seguindo a busca por MiniLM já aprovada na
[proposta](proposta-tecnica.md). `training_comparables.py` prepara um índice
descritivo e devolve até três referências. Não altera serviço/MCP, M1, bundles,
partições ou lock. Ainda não há integração ao grafo, chamada NIM ou demo de #5.

## Fronteira de treino e linhagem

O helper recebe `M1Settings` do operador e usa `load_model_context` para validar
o bundle, coorte, baseline e runtime. Seleciona os IDs de treino do artefato
servido e confere-os contra o manifesto **antes de abrir evidências**. Para
M1/A200 são os 124 originais; não incorpora os 203 de A300 ou referências de
validação apenas por estarem disponíveis na máquina.

O índice de caminhos é metadado. Os caminhos das outras partições formam uma
lista de bloqueio, sem abrir seus conteúdos. Redirecionamentos, symlinks para
essas evidências, escape da raiz e arquivos mistos `records.json` ou
`predictor-inputs.json` são recusados antes da leitura. Somente os pares
features/run do treino são abertos. Hashes da curadoria e dos recibos,
identidade, propriedades, observação congelada e limpeza são conferidos.

O split de treino reconstruído precisa reproduzir o digest do artefato.
Rótulos de treino participam somente dessa verificação; não são retidos no
índice e não entram no cosseno, desempate ou resultado. Não há
treinamento, nova coleta ou leitura de evidência/labels do teste.

## Seleção e ausência de suporte

Embeddings da fala são normalizados para cosseno. Filtrar setor e formato
técnico antes de ordenar; ordenar por similaridade decrescente e desempatar
estavelmente por ID. Retornar no máximo três referências iguais ou acima do limiar
explicitamente configurado pelo operador. Esse limiar ainda não é calibrado
nem selecionado por resultados de views.

“Formato” nesta fatia significa **vídeo vertical de até 60 s**, o suporte
técnico atual de M1. Esse filtro é constante na coorte vertical e não demonstra
semelhança editorial. Tutorial, demonstração e outros gêneros não estão
anotados/aprovados; se solicitados em `semantic_format`, a resposta é vazia
com `semantic_format_not_available`, sem inferência VLM ou fallback.

Fala ausente, embedding nulo em norma ou ausência de matches suficientes geram
lista vazia com motivo explícito. Não relaxar setor/formato ou limiar para
preencher três posições. Excluir mídia com o mesmo hash e grupos de duplicatas
reconhecidos, inclusive quando a cópia exata não tinha embedding elegível.
O chamador deve fornecer o hash obtido do arquivo registrado/conferido; ele
não é um campo de texto livre do usuário na futura integração.

O resultado local identifica IDs, setor, origem, datas, cosseno, coorte,
partição, artefato e critério. Não contém views, transcrição ou vetores.
Referências são descritivas de treino, sem causalidade ou promessa de alcance.
Esse resultado local não é automaticamente um pacote autorizado para API
externa; o adaptador explicador ainda precisa de seu contrato de evidências.

## Uso e verificações

API preparada: `load_training_index(settings, evidence_root,
minimum_similarity=limiar_explicito)`, seguida de
`index.search(predictor_inputs, media_sha256=hash_verificado)`.
`settings` usa exatamente a coorte e o bundle do [M1 servido](issue-3-servico-m1.md).
O helper só lê arquivos; não persiste dados, sobrescreve artefatos ou faz rede.

Os **18 testes de comparáveis** usam somente evidência pública sintética.
Canários bloqueiam validação/teste e arquivos mistos; testes cobrem redirects,
symlink/escape, linhagem, ausência de fala, norma zero, ranking de cosseno,
limiar, setor, cópias e gênero sem suporte. Junto dos oito testes isolados de
SHAP e do teste SHAP nativo, passaram **27 testes em 3,75 s**, após confirmar o
processo VLM encerrado. Ruff e formatação dos quatro arquivos novos passaram.
Revisão independente somente leitura aprovou a fronteira e a seleção.

O índice real foi carregado sobre M1/A200: **124 embeddings elegíveis e 248
arquivos features/run de treino abertos**. Um guarda adicional de leitura
bloqueou caminhos de validação/teste e arquivos mistos; nenhum foi aberto.
O digest do split coincidiu com o artefato. Uma consulta com embedding de treino,
excluindo sua cópia exata, respeitou setor, limiar e pertencimento ao treino;
isso verifica funcionamento, sem validar a qualidade dos comparáveis ou
calibrar o limiar. Nenhuma lista de referências privadas foi persistida.
Recibos: `training-index-verification.json` e `local-verification.json` em
`data/private/issue-5-evidencias-locais-v1/`. Os 125 pins herdados da v9 e as
quatro fontes congeladas continuaram idênticos.

A suíte completa posterior passou em 624 testes em 317,65 s, com Ruff e
formatação dos 112 arquivos aprovados.

As caixas compostas da #5 permanecem abertas. Faltam integrar
StateGraph/explicador, validar sua saída e
demonstrar três criativos distintos. LangGraph não está instalado e o lock
atual está congelado; não foi instalado um substituto nem descrito um fluxo
Python manual como `StateGraph`. O teste reservado segue condicionado à #6.

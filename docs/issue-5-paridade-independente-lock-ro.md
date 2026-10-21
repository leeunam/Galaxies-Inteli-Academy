# Paridade independente — lock operacional sob host somente leitura

O run v5 encerrou em **6,600 s**, com `registry_unavailable` na resposta
Python completa preservada. O grafo/subgrafo executaram, mas o cadastro falhou
antes de `serve_m1` e de carregar o modelo. Traces completos e terminais
válidos confirmam zero extrações, previsões e SHAP. MCP não reservada;
autorização encerrada, recolhimento confirmado e scratch vazio.

O layout do operador deixou o host inteiro em somente leitura. O cadastro
original exige `O_CREAT|O_RDWR` no arquivo auxiliar `.lock` até para validar
criativos. O probe reproduziu **EROFS**, sem reter a exceção bruta, e o mesmo
`registry_unavailable` pelo método nativo de validação.

A correção altera somente a montagem do sandbox: um arquivo de lock novo no
scratch é montado sobre o caminho lógico esperado dentro do namespace. O
inode do lock original, cadastro JSON, pedido, uploads, modelos e código
continuam intocados/somente leitura. Cada rota recebe seu próprio lock;
nenhum campo ou caminho da configuração da aplicação é substituído. Isso
preserva o pedido e a identidade do cadastro para a comparação das rotas.

Com essa montagem, o método original validou as três peças e suas propriedades
por inspeção nativa. Foram zero imports de M1/encoders, cargas de modelos,
previsões, extrações de features ou SHAP. Cadastro e lock originais conferiram
byte a byte; terminais válidos e recolhimento confirmado.

O protocolo v6 vincula as duas provas e a tentativa v5 encerrada, mantém os
tetos anteriores e exige liberação técnica própria para um run novo. O
preflight inventado usa a montagem corrigida tanto off quanto on. O observador
e os 14 checks de terminal já verificados permanecem sem mudança nesta unidade.

A falha do layout não demonstra defeito no M1 e não explica os 22 campos
históricos divergentes. A fonte canônica continua sendo o Python histórico;
os relatórios e inputs anteriores permanecem preservados até o prazo acordado.

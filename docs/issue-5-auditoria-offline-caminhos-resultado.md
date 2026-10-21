# Auditoria offline dos caminhos Python/MCP e do ensaio frio

A auditoria não demonstrou diferença efetiva de configuração, aliasing de
features Python ou perda de precisão no transporte que explique a divergência
real. Três grupos de casos inventados passaram sem carregar pesos, extrair ou
prever. **A primeira diferença comprovada permanece nos valores do relatório
M1; a etapa interna que divergiu não pode ser recuperada dos recibos antigos.**

O [recibo agregado](evidence/issue-5-auditoria-offline-caminhos-20261020.json)
registra as verificações. Nenhuma fonte selada foi editada e nenhum patch de
produto foi preparado, pois não houve bug causal confirmado.

## Configuração, estado e contexto

| Aspecto | Duas análises históricas | Diagnóstico frio | Verificação offline |
| --- | --- | --- | --- |
| Pedido e ordem | Mesmos três IDs ordenados, cadastro e bytes | Uma posição já divergente | Vínculos anteriores preservados |
| Worker efetivo | Mesmo módulo, interpretadores, argumentos e timeout de 480 s | `main` nativo com observação | Builders/parser de produção produziram argumentos equivalentes com paths inventados |
| Temporários | Configurações externas de scratch diferem, mas são substituídas pelo diretório exclusivo do worker | Diretório novo por captura | Diferença externa não chega como diferença de configuração numérica |
| Ambiente | Supervisor/grafo/worker/extração recriam ambientes literais | Ambiente nativo da extração, por AST pinado | Hash sem TMPDIR coincide com os traces frios; snapshots internos históricos não foram retidos |
| Cache de modelos | Novo por invocação; objetos reutilizados entre três itens sequenciais | Novo por captura isolada | Caso inventado confirmou reutilização local e isolamento entre caches |
| Aplicação M1 | Um candidato por chamada, mesmo bundle nas três previsões sequenciais | Um vetor por chamada, bundles em processos frios separados | Não há minibatch de três na previsão original |
| CPU | Afinidade efetiva histórica não registrada; quatro threads configuradas nos extratores | Capacidade restrita a quatro CPUs próprias | O contexto frio não certifica o contexto histórico |

O primeiro candidato já diverge e é processado com cache novo nos dois pedidos
originais. Portanto, aquecimento por candidatos anteriores não explica sozinho
essa diferença. Isso não prova imutabilidade ou determinismo das bibliotecas
nativas. O cache contém instâncias vivas de modelos, não uma prova de ausência
de estado interno.

O handoff copia os resultados por JSON para contratos congelados com tuplas,
e a matriz de features cria listas novas. Um caso inventado alterou a lista
de origem e a matriz retornada: o `PredictorInputs` congelado permaneceu igual.
Não foi demonstrada corrupção por aliasing nessas fronteiras Python.

## Modelos, tokenização, pooling e serialização

Os caminhos usam o mesmo artefato, configuração de extrator, baseline, coorte
e linhagem de treino já verificados. A checagem atual de fontes/pacotes do
extrator passou. Quatro arquivos de metadados do snapshot MiniLM pinado foram
lidos, sem abrir pesos; o pooling interno é média de tokens.

O extrator fixa 128 tokens de sequência, divide o texto em blocos de 126 tokens
e calcula a média dos embeddings dos blocos. O código instalado de
`SentenceTransformer.encode` usa `eval()` e `inference_mode`, restaura a ordem
após ordenar por comprimento e mantém o perfil padrão float32. O faster-whisper
recebe temperatura zero e seleciona a ramificação sem amostragem. Esses fatos
não constituem garantia universal de determinismo, nem demonstram que ausência
de seed causou a falha.

Um servidor MCP stdio real, usando a fronteira de produção com serviço numérico
substituído **somente no fixture por dados inventados**, preservou integralmente
floats de alta precisão, pedido e pacote. Guardas registraram zero tentativas
de extração/modelo/treino. A validação JSON pelo contrato integrado também
preservou a fixture. Não foi demonstrado arredondamento no adaptador que
explique as diferenças reais armazenadas.

Também foram conferidos **os dois resultados reais já salvos**, sem nova
consulta: em ambas as rotas, o roundtrip de `M1AnalysisResponse` preserva a
análise; seu digest normalizado corresponde a `evidence_packet.analysis_sha256`,
e o digest do pacote corresponde a `explanation.packet_sha256`. Portanto, os
valores diferentes já estavam vinculados internamente aos pacotes de cada
análise. Uma perda simples de precisão no transporte externo MCP, depois da
montagem do pacote, não explica essa divergência. Isso estreita a investigação
para a produção das análises vinculadas, sem identificar o componente causal.

O relatório numérico é congelado antes de SHAP, comparáveis e renderização.
SHAP recebe os três candidatos depois das previsões individuais; o índice de
treino é preparado depois disso. A montagem do pacote não recalcula os valores
de previsão já registrados. Limpeza usa diretórios exclusivos e ocorre após
confirmação de recolhimento; não foi encontrado reaproveitamento de scratch
entre as duas rotas.

## Conclusão e bloqueio causal preciso

O [diagnóstico frio anterior](issue-5-diagnostico-frio-unico-resultado.md)
produziu entradas e previsões iguais nesse contexto limitado. Ele não elimina
a [divergência histórica](issue-5-demo-local-python-mcp-resultado.md). A
[consulta canônica](issue-5-consulta-canonica-demo.md) oferece leitura estável
de um resultado preservado, mantendo a paridade independente aberta.

As análises originais não conservaram hashes de áudio decodificado, transcrição,
embedding ou `PredictorInputs`, nem snapshots de afinidade, RNG ou estado do
backend. O checksum do handoff vivia na memória de cada sessão e não comprova
igualdade entre sessões. Também não ficaram IDs das referências no pacote
reduzido. Esses dados não podem ser reconstruídos sem outra execução, fora do
escopo autorizado desta auditoria.

Assim, não é possível atribuir a causa a ASR, embedding, CatBoost, ambiente ou
estado mutável, nem escolher um reparo numérico fundamentado. Esta auditoria
não propõe outra captura, não reabre a autorização encerrada e não altera a
igualdade exigida. A evidência disponível sustenta esse bloqueio causal, não
uma declaração de que todos os componentes são determinísticos.

Foram zero ensaios ML novos, leituras canônicas reais, aquisições, chamadas
remotas, treino ou acesso a conteúdo do teste reservado. Mídias, manifestos,
relatórios e passagem privada continuam intactos; a árvore principal não
recebeu escrita. Nenhuma issue ou avaliação científica foi declarada concluída.

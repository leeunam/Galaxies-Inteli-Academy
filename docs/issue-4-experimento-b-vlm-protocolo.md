# Complemento de B com VLM — protocolo anterior à execução

Solicitação de 19/10/2026: completar B com VLM nas mesmas 300 referências,
preservar teste e M1 atual e comparar com B-cache, A300 e A200. Continuação na
branch `codex/issue-4-experimento-b`, depois de `6e2bf71`.

## Fronteira e extração

A base continua 203 treino/66 validação/31 teste. Selecionar os 269 IDs de
desenvolvimento pelos metadados de partição antes de abrir qualquer evidência.
Validar a ascendência de 200 e ancorar hashes em A300. A guarda reservada
continua recusando os arquivos mistos antigos e evidências dos 31 de teste.
Não extrair VLM, construir matriz ou prever o teste nesta solicitação.

Preservar todos os fontes e bundles de A/B-cache, os extratores, o serviço,
MCP, B0 e a coorte. Nova extração em sidecars privados, sem alterar índices ou
evidências congelados. Não consultar métricas públicas novamente. Usar o
downloader existente, sem cookies, proxies ou contorno de bloqueios. Cada
reaquisição deve coincidir com o SHA256 original da mídia e com propriedades
e timestamps dos frames congelados; divergência impede uso, sem remover ou
substituir linhas. Reutilizar ASR/MiniLM/CLIP e medidas técnicas existentes.

Qwen3-VL-2B-Instruct GGUF Q4_K_M, projetor Q8_0, runtime llama.cpp b11716,
prompt, esquema, limites e seleção de até quatro frames do extrator existente.
Verificar pesos/runtime locais, sem inferência externa nem novas dependências.
Guardar resposta bruta, saída sob a barreira de qualidade, modelo/configuração,
hashes da mídia/frames/fontes, tempo e memória. Descartar vídeo/frames ao fim de
cada sessão, inclusive em falha. Imagens da amostra de auditoria podem existir
apenas durante a revisão assistida e devem ser removidas após seu registro.

Começar com um caso de treino para verificar aquisição, identidade, extração e
limpeza. O lote é sequencial e retomável, com até 269 aquisições, 180 s por
aquisição e 180 s por chamada VLM. Registrar orçamento total de 27 horas,
sem prometer conclusão nessa duração. Parar imediatamente em autenticação,
403/429, identidade divergente, memória/timeout, saída inválida ou limpeza
incerta. Não repetir automaticamente uma falha, trocar vídeo ou mudar fonte.
Uma falha impede treino completo enquanto houver referências incompletas.

## Qualidade antes dos rótulos de treino

JSON válido não comprova percepção. Os candidatos a entradas são cinco
atributos categóricos: pessoa visível, produto nos primeiros 3 s, presença
de texto, ambiente e formato. `unknown` é um valor explícito. Close-up e
demonstração/aplicação continuam globalmente desconhecidos e fora da matriz;
o formato `application` também será mapeado para `unknown`, evitando liberar
indiretamente a percepção reprovada. Não extrair OCR ou notas de viralidade.

Antes de ajustar, fixar por hash uma amostra de 32 casos de treino (16 por
setor), usando somente IDs/setor, sem rótulos, título, descrição ou transcrição.
Revisão visual assistida de valores e frames citados, registrada como tal,
sem afirmar revisão humana. Registrar por coluna valores conhecidos, acertos,
divergências e suporte. Uma coluna só pode entrar se tiver ao menos 12 valores
conhecidos revisados, nenhum valor conhecido sem evidência válida e pelo menos
90% de concordância com os frames; nas booleanas exigir suporte aos dois
valores, com ao menos três exemplos conhecidos de cada. Colunas reprovadas permanecem excluídas em todas as linhas. Não
corrigir valores individuais para favorecer treino. Se nenhuma coluna passar,
registrar falha da etapa e não declarar B completo nem substituir por B-cache.
Fixar e registrar a seleção de colunas antes de consultar métricas preditivas.
O tamanho pequeno da auditoria não certifica acurácia geral do extrator.

## Ajuste, comparação e isolamento

Acrescentar somente as colunas liberadas ao prefixo exato das 905 de B-cache,
sem PCA, escala ou imputação aprendida. Exigir sidecars completos e compatíveis
nos mesmos 269 IDs; não fazer análise somente dos casos que funcionaram.
Congelar protocolo de percepção/colunas/digests no novo bundle e verificar
paridade exata após recarga nativa. Não promover o modelo ao serviço.

Repetir a grade aprovada: quantis 0,1/0,5/0,9 × profundidades 4/6 × L2 3/10,
taxa 0,05, seed42, CPU2, máximo500/parada50. Treino uniforme somente nas203;
validação por inverso da frequência de canal, q50 por MAE log por canal e
extremos por pinball por canal; desempate por menor profundidade/L2. Não
modificar representação ou repetir busca após observar resultados.

Comparar B-VLM com B-cache/A300/A200 (e B0 ampliado) nos mesmos grupos45/21/66,
com métricas por setor/canal, perdas dos quantis, cobertura/largura e ranking
com suporte. Mesmos reparo de cruzamento/conversão e limiares de alto alcance
do treino original (moda6.403,5; beleza33.835,3). Preservar as previsões e
métricas dos comparadores. A validação continua usada na seleção e não é teste
independente. Não atribuir efeito causal a atributo isolado nem inferir
correção de viralidade com a cauda pequena conhecida.

Saídas separadas em `data/private/issue-4-experimento-b-vlm-300-v1/` e
`artifacts/issue-4-experimento-b-vlm-300-v1/`. Um executor, revisão independente
somente leitura e commits por unidades verificadas. Implementação, execução e
resultado devem distinguir infraestrutura pronta de VLM realmente extraído,
atributos aprovados e modelo efetivamente treinado. C não faz parte deste pedido.

Referências: [B-cache](issue-4-experimento-b-protocolo.md),
[resultados anteriores](issue-4-experimento-b-resultados.md),
[correção dos extratores](correcao-extratores.md),
[contrato técnico](proposta-tecnica.md) e [P4](backlog-proposto.md#p4--acrescentar-multimodal-e-comparar-catboost-com-lightgbm--b--c).

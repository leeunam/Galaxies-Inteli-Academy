# Como explicar o iSee em seis minutos

**O problema.** Um produtor tem de um a cinco vídeos para a mesma campanha e
quer decidir qual priorizar antes de publicar. O iSee estima views e mostra
incerteza e evidências. Foi desenvolvido por Leunam Sousa para a Galaxies,
no contexto da Inteli Academy. A persona da Galaxies consumirá a ferramenta;
ela não foi construída neste projeto.

**O que entra.** Vídeos autorizados, cadastrados localmente com IDs, setor
moda/beleza, objetivo divulgação e briefing. O alvo aprendido é a contagem
pública observada com 30 a menos de 37 dias. O pedido não fornece as views
futuras nem permite usar curtidas do próprio vídeo como atalho.

**Como o número aparece.** O serviço Python valida o pedido e usa os mesmos
extratores versionados do treino. M1/A200, a versão servida, usa setor,
propriedades do arquivo e representação da fala. CatBoost calcula os quantis
q10/q50/q90. q50 ordena os candidatos; o reparo de faixas preserva q50.
O LLM não inventa ou modifica esses números. A faixa não tem garantia de
cobertura de 80%, e a ordenação é prioridade exploratória para teste.

**De onde vem a explicação.** SHAP decompõe log1p(q50); as contribuições da
fala/embeddings são agrupadas por modalidade, sem dar significado inventado
a cada dimensão. Comparáveis vêm somente do treino. Na arquitetura aprovada,
NVIDIA seleciona IDs de evidência; validação e texto local preservam fatos e
números. A seleção real demonstrada usou fatos inventados; suficiência e
aderência de campanha real ainda estão em validação. SHAP não é causalidade.

**Onde acontece.** Cadastro, mídia, extração, previsão, SHAP e comparáveis ficam
locais. A função Python e o MCP por stdio expõem o mesmo caso de uso. O
percurso integrado v2 usa LangGraph em ambiente separado. Só um pacote de
evidências permitido pode seguir ao provedor; mídia e transcrição integral
não são enviadas automaticamente. Pesos e coortes privadas não acompanham
o clone público. Os dois locks preservam ambientes compatíveis.

**Por que essas escolhas.** Um modelo tabular treinado fornece números
mensuráveis independentemente do LLM. Encoders congelados e cache evitam
reprocessar a mesma mídia. Partições por canal/duplicatas reduzem vazamento;
transformações aprendidas ficam no treino. A/B isolam o ganho de informação
no CatBoost; B/C comparam bibliotecas com os mesmos atributos. O registro
local guarda configurações, hashes, versões, métricas e falhas.

**O que já foi demonstrado.** A300, B-cache e C-cache foram comparados na
validação. O par histórico v6 verificou Python/MCP com A200 e três mídias
reais. Outra execução real começou em features cacheadas e calculou M1,
SHAP, comparáveis e texto local. A demo pública usa vídeos/números inventados.
Abrir um relatório salvo apenas consulta aquela execução; não roda de novo
extração, modelo ou provedor.

**O que falta e por que importa.** Atributos VLM precisam passar por qualidade
perceptiva antes de B/C completos. JSON válido, fim do timeout e um acerto
isolado não bastam. Depois vêm seleção na validação, explicação/integracão
da configuração escolhida, congelamento e autorização específica do teste
de 31 casos. O diagnóstico temporal exige ajustar no anterior e avaliar no
posterior; um snapshot não mede desempenho prospectivo. Condições de uso da
fonte, amostra pequena e alto alcance subestimado também limitam a conclusão.

Ao demonstrar, identifique primeiro a origem: **demo sintética**, **execução
real a partir de mídia**, **cálculo a partir de features cacheadas** ou
**consulta de resultado preservado**. Mostre previsão, faixa, ranking,
fundamentos e um limite. Não chame B/C-cache de B/C completos nem apresente
os números da validação como resultado do teste reservado.

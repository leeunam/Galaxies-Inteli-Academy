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

Para preparar o contrato de sete campos, use `build_schema(frame_seconds)`,
`build_prompt(frame_seconds)` e `parse_attributes(raw, frame_seconds)` de
`scripts.visual_attributes_seven`. O parser exige um JSON completo, sem reparo,
com evidência para valores conhecidos e `unknown` somente com `frames=[]`;
closeup e demonstração preservam todas as opções válidas. `screen_text` indica
presença de texto, sem transcrição OCR. O controle visual anterior falhou ao
retornar texto OCR nesse booleano e `unknown` com frame; a política antiga
também forçava close-up e demonstração para desconhecido (`unknown`), e sua
avaliação cobria só cinco campos. O caminho novo corrige essas lacunas sem alterar
a política legada, as fontes ou os protocolos congelados.
O schema não comprova suporte do provedor
nem da grammar instalada; JSON Schema aceita índices como `1.0`, que o parser
estrito rejeita. Não há execução automática de modelo ou requisição remota.
`scripts.visual_quality_seven.evaluate_gate(observations)` recebe 32 linhas TRAIN,
16 por setor, com `alias`, `sector`, `partition="train"`, `channel_id`,
`sheet_sha256`, `frame_seconds`, `annotated` e `predicted` (ambos com os sete
atributos). IDs, canais e hashes devem ser distintos. O resultado agregado exige
ao menos 12 previsões conhecidas e 90% de concordância de valor e evidência por
campo/setor, nenhuma evidência sem suporte e representação mínima das classes;
booleanos exigem ambas as classes com ao menos três casos globais e um por setor;
categorias, dois valores com três casos globais cada. `unknown` é abstenção.
Todos os sete campos precisam passar. O resultado continua
com qualidade, release e extração269 falsos: origem, cegamento, conteúdo visual e
vínculos reais precisam de revisão independente. O carregador V7 segue bloqueado.

O desenvolvimento dispõe de oito folhas TRAIN exatas, todas de moda. As referências
dos dois campos faltantes foram seladas antes das novas saídas do candidato, com
anotação assistida, não humana, e seleção histórica. Isso não constitui auditoria
cega de 32 referências: outras 24 folhas originais (16 de beleza e oito de moda)
não foram encontradas no inventário local verificado; também é preciso completar
as referências independentes dos sete campos. A auditoria usa o treino
existente; a coorte de 300 e o split 203/66/31 permanecem intactos. Não houve
extração das 269 referências restantes nem treino B/C observado.

O novo controle visual sintético enviado ao NIM com `response_format/json_schema`
retornou HTTP 503. A rodada parou nessa única chamada, sem nova tentativa nem
envio das duas folhas TRAIN previstas. Sem saída gerada, suporte remoto ao schema
e percepção não puderam ser avaliados; os testes locais do contrato e do operador
não demonstram qualidade visual.

Ao demonstrar, identifique primeiro a origem: **demo sintética**, **execução
real a partir de mídia**, **cálculo a partir de features cacheadas** ou
**consulta de resultado preservado**. Mostre previsão, faixa, ranking,
fundamentos e um limite. Não chame B/C-cache de B/C completos nem apresente
os números da validação como resultado do teste reservado.

# Experimento B na coorte de 300 — protocolo prévio

Solicitação de 19/10/2026: iniciar B com as mesmas 300 referências/partições,
preservar teste e M1 atual e comparar com A300/A200. Branch:
`codex/issue-4-experimento-b`, a partir de `0188547`.

## Representação disponível e limite da rodada

A auditoria selecionou treino/validação antes de abrir arquivos: 203/66 casos.
Todos têm CLIP512, brilho/saturação e áudio transcrito com RMS/duração válidos;
todos têm VLM `not_requested`. As colunas Qwen continuam sem aprovação de treino.
Esta rodada é **B-cache, CatBoost com CLIP e medidas técnicas de imagem/áudio**.
Não é a execução da camada VLM completa prevista na #4; essa parte permanece
pendente de validação e extração próprias, sem afirmar percepção correta.

Representação fixa de 905 colunas:

- As mesmas 388 de A, na mesma ordem, com a mesma fala/MiniLM e propriedades.
- 512 componentes CLIP, na ordem original, sem PCA ou transformação aprendida.
- Brilho médio e saturação média dos mesmos frames, RMS do áudio e duração do áudio.
- Estado de áudio categórico, que deve ter suporte no treino.

O estado de áudio é `transcribed` em todos os 269 casos: não tem variância nesta
coorte e não pode receber crédito por ganho preditivo.

Categorias nas posições 0, 3 e 904. Sem VLM, OCR/título, IDs/canal, datas, views,
curtidas, hashes, duração de processamento ou escores de qualidade do ASR nas
entradas. Nenhuma nota de viralidade. Sem imputação silenciosa de modalidade:
campo ausente, vetor inválido ou áudio sem suporte produz recusa explícita.
Não mudar os extratores/cache nem adquirir mídia nesta rodada.

## Ajuste e comparação

Mesmos 203 IDs/rótulos de treino, 66 de validação e 31 de teste preservados.
Treinar somente nos 203; validação apenas para parada/escolha. Mesmos 12 ajustes
de A: quantis 0,1/0,5/0,9 × profundidades 4/6 × L2 3/10, taxa 0,05, seed 42,
CPU 2, máximo 500 iterações/parada 50. Pesos uniformes no treino e inverso da
frequência do canal na validação. q50 por MAE log médio por canal, extremos por
pinball log médio por canal, desempate menor profundidade/L2. Não fazer nova
busca ou alterar entradas/perdas após observar resultados.

Comparar B-cache300, A300, A200 e B0 ampliado nos mesmos grupos: 45 casos/16 canais
originais, 21 casos/21 canais novos e união 66/37. B-cache/A300 é a ablação
pareada de informação, com os mesmos dados e protocolo de seleção; A200 é
controle adicional com treino diferente. A seleção de configurações/iterações
continua separada por modelo. Não atribuir todo ganho ao efeito causal de uma
modalidade nem apresentar validação usada para seleção como teste independente.

Métrica principal: MAE log por canal. Registrar MAE views, pinball dos três
quantis, cobertura/largura após o mesmo reparo que preserva q50, ranking por
canal com contagens de suporte e resultados por setor/canal. Recorte de alto
alcance mantém os limiares originais: moda 6.403,5 e beleza 33.835,3. Registrar
n de casos/canais, erro com sinal, subestimação, razão observado+1/previsto+1
e falhas acima da faixa. Sem inferência ou métricas do teste.

## Isolamento, artefatos e verificações

Manter congelados os quatro fontes de A, extratores, serviço/MCP, M1/A200,
A300 e coorte/B0/partições de 300. O snapshot privado anterior registra 31
arquivos permitidos; não incluir arquivos mistos ou evidências reservadas.
Carregador restrito e guarda ativa recusam `records.json`/`predictor-inputs.json`
antigos e todas as evidências dos 31 IDs de teste. Nunca criar matriz de teste.
Antes de ler rótulos/evidências, validar metadados e ascendência exata do
manifesto, igualdade dos 200 assignments e do conjunto de teste. No CLI, exigir
também os hashes de coorte/partições registrados no artefato A300. Uma troca de
partição ou de coorte deve falhar antes do carregador de evidências.

Novos fontes exclusivos de B, bundle com esquema próprio e modelos nativos
CatBoost, checksum das entradas/protocolo/fontes e recarga sem pickle. Verificar
paridade exata nas entradas de validação, conversão para views e preservação do
q50, rejeição de bundle incompatível e ausência de sobrescrita de artefatos.
O bundle fixa também os fontes do carregador restrito, particionamento,
manifesto, baseline, guarda e persistência. A contagem de arquivos de evidência
é de caminhos únicos: os extras B são relidos e seu checksum novamente
verificado, sem modificar os fontes congelados de A.

Saídas privadas em `data/private/issue-4-experimento-b-300-v1/` e
`artifacts/issue-4-experimento-b-300-v1/`. Dados/modelos não entram no Git.
Um executor e revisão independente somente leitura. Commits por unidades:
protocolo; carregamento/representação com testes; treino/artefato/comparação com
testes; execução e resultados verificados. Não promover B ao serviço, iniciar C
ou abrir o teste nesta solicitação.

# M1 na função Python e no MCP

Continuação da #3 com o [bundle offline congelado](issue-3-treinamento-offline.md).
Não há novo ajuste, mudança do protocolo ou avaliação do teste reservado.

## Extração dos inéditos

`candidate_features.py` reutiliza `extract_features` sem alterar os arquivos ou
pesos congelados. ASR small CPU/int8 sem idioma forçado, MiniLM em chunks de 126
tokens com média e as mesmas propriedades de arquivo. A extração compartilhada
também calcula CLIP; somente as 388 colunas aprovadas de A chegam ao preditor.
Não utiliza VLM, título, brief, canal ou outcomes.

O cadastro valida a mídia e fornece os registros internos ao caso de uso.
A análise reabre os arquivos com a proteção existente e copia os bytes para uma
sessão privada, verificando tamanho/hash antes de extrair. O subprocesso recebe
essas cópias, setor e configuração, sem credenciais ou texto de campanha.
Pesos precisam estar presentes nas revisões locais; modo offline não baixa nada.
As saídas do extrator, inclusive mensagens e transcrições, não chegam ao stdout
do MCP. Só entradas estritas do preditor e estados retornam ao processo principal.

O pai encerra o grupo do subprocesso no timeout/cancelamento e remove a sessão
após sucesso/falha. Prazo de extração: `120 + 30 × número_de_candidatos` segundos;
limite de CPU do worker: 600 s. Não há SLA. Vídeos originais continuam sob o
cadastro do operador; cópias, áudio decodificado e frames da sessão são temporários.
Não há cache persistente de transcrição/embedding. Queda da máquina pode exigir
limpeza posterior, como nas políticas existentes.

Sem trilha e áudio sem fala mantêm estados diferentes. Fala deve passar pela
triagem pt já existente, sem certificar dialeto pt-BR por ASR. Falha de extração,
idioma fora de suporte ou inconclusivo nunca se transforma em fala inventada.
O bundle real só tem suporte a texto extraído; ausências serão indisponíveis.

## Contrato e configuração

O payload continua sendo o contrato da #2: campanha, setor, objetivo `divulgacao`,
brief e 1–5 IDs opacos distintos. Caminhos de modelo/coorte e seleção do modo são
configuração do operador, recusados como campos do payload.

```python
from pathlib import Path
from scripts.creative_analysis import analyze_creatives
from scripts.m1_service import M1Settings

settings = M1Settings(
    Path("artifacts/issue-3-experimento-a-v1"),
    Path("data/private/issue-1-pool-treino-20261018-v6/released-cohort-v1"),
)
result = analyze_creatives(payload, registry, m1=settings)
```

Na CLI `creative_cli analyze` e no servidor `creative_mcp`, fornecer juntos
`--m1-model-dir` e `--m1-cohort-dir`. O primeiro integra o grupo mutuamente exclusivo
com `--synthetic-baseline` e `--observed-baseline-dir`. Sem opções, o modo padrão
continua indisponível. As respostas antigas dos três modos são preservadas.

Antes de extrair, o serviço confere o bundle, arquivos/versões congelados do
extrator e os hashes de baseline/coorte/partições. IDs de treino devem coincidir
com B0 e IDs de validação com o manifesto; não há leitura dos rótulos do teste.
Artefato ausente/incompatível retorna `model_artifact_unavailable`, sem fallback.

No modo M1, `schema_version=creative-m1-v1` publica estimativa q50 em views,
faixa q10/q90 após o mesmo reparo offline, baseline B0 da mesma coorte, versões e
checksums. A função/MCP não retorna vetores, fala, caminhos, IDs de referências
ou métricas de vídeos históricos. O brief permanece contexto e não altera números.

Um candidato não recebe ranking. Dois a cinco são ordenados por q50 decrescente;
empates exatos compartilham posição, mantendo a ordem de entrada (1, 1, 3).
Posição numérica é prioridade exploratória para teste, sem superioridade comprovada.
Nenhuma probabilidade de vitória é inferida da sobreposição das faixas.

Falha/timeout/pesos ausentes, idioma inconclusivo ou fora de suporte e estado de
texto sem suporte no treino deixam previsão/faixa daquele candidato indisponíveis.
Resultados parciais são explícitos e não recebem ranking competitivo. Previsões
não finitas, negativas ou incompatíveis com os limites também são recusadas.
Erros de mídia/cadastro continuam interrompendo a solicitação, como na #2.

O prazo MCP passou a 480 s para comportar as cinco inspeções de até 30 s e o
worker de até 270 s. Tempos reais e disponibilidade devem ser medidos no ambiente;
não há promessa de SLA. A explicação continua determinística, sem NIM/SHAP.

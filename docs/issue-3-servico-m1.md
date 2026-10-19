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

## Reprodução da paridade

Com um arquivo local próprio/licenciado ou autorizado para esse ensaio:

```bash
rtk proxy env UV_CACHE_DIR=/tmp/galaxies-uv-cache uv run --offline --frozen python \
  -m scripts.demo_m1 \
  --media /caminho/do/arquivo-local.mp4 --sector beleza \
  --m1-model-dir artifacts/issue-3-experimento-a-v1 \
  --m1-cohort-dir data/private/issue-1-pool-treino-20261018-v6/released-cohort-v1 \
  --report-file data/private/nova-demo-m1/python-mcp-parity.json
```

Usar relatório novo e nunca uma mídia do teste reservado. A demo não faz rede.
Cria cinco cadastros temporários do mesmo arquivo, chama Python e cliente MCP
stdio real para 1/2/5 e exige igualdade integral das respostas e previsão disponível.
As duplicatas devem empatar; não são cinco criativos independentes nem uma amostra
de avaliação. Cada percurso refaz a extração, sem cache persistente de resultados;
somente pesos são reutilizados dentro do worker de cada requisição.
O arquivo original fornecido pelo operador não é excluído; a demo remove suas
próprias cópias e cadastros ao final, inclusive se falhar.

Para iniciar somente o servidor, os caminhos são configurações do processo:

```bash
rtk proxy env UV_CACHE_DIR=/tmp/galaxies-uv-cache uv run --offline --frozen python \
  -m scripts.creative_mcp \
  --m1-model-dir artifacts/issue-3-experimento-a-v1 \
  --m1-cohort-dir data/private/issue-1-pool-treino-20261018-v6/released-cohort-v1
```

O cadastro local de mídia continua usando `scripts.creative_cli register` com
campanha/setor/caminho relativo a `uploads/`. O host MCP recebe somente IDs opacos.
Testes públicos não precisam desses pesos, de chave, de mídia externa ou da coorte.

## Evidência real de 18/10/2026

Após o aluno autorizar um vídeo público de alto alcance para a demonstração,
foi reutilizada a fonte do antigo piloto de beleza:
[A MAQUIAGEM MAIS BIZARRA!](https://www.youtube.com/watch?v=789ehreEQqE).
Uma chamada à API verificou 2.316.115 views na nova observação, com idade de
36,202 dias. O ID está **fora dos 200 IDs da coorte congelada**. A contagem nova
foi guardada somente na procedência da demo; não alterou rótulos, seleção ou modelo.
Autorização operacional permanece distinta de aprovação da plataforma.

Um único download limitado trouxe 1.030.836 bytes. Houve três comparações com
cliente FastMCP stdio real, sem mocks ou cache de resultados da extração:

| Cadastros do mesmo vídeo | Python | MCP | Resposta integral idêntica |
| --- | ---: | ---: | --- |
| 1 | 11,86 s | 15,68 s | Sim |
| 2 | 24,77 s | 28,23 s | Sim |
| 5 | 54,07 s | 45,29 s | Sim |

São medidas de relógio desta execução, incluindo validação/carregamento/extração,
com cache de sistema não isolado e outras verificações concorrentes. Não são
benchmark comparável nem SLA. Os cinco cadastros repetem **um** criativo publicado;
as comparações empataram em posição 1, como esperado. Ranking sem empate é coberto
pelos testes públicos, sem confundir essas repetições com diversidade de conteúdo.

Todos os percursos usaram o bundle real `9dd1c7a2…d70d59`, ASR sem idioma forçado,
MiniLM e CatBoost locais. A saída central foi **1.520,52 views**, com faixa estimada
**49,40–16.189,49**. Esse resultado **subestima fortemente** as 2.316.115 views
observadas da fonte e não captura esse exemplo de alto alcance na faixa. A demo
valida integração/igualdade dos percursos, não capacidade de identificar virais,
calibração ou qualidade geral. Não houve ajuste posterior para melhorar esse caso.
O vídeo foi escolhido deliberadamente por alcance e já era um controle de
desenvolvimento conhecido; não é amostra independente nem substitui a #6.

Evidências privadas em `data/private/issue-3-m1-demo-real-v1/`:
`demo-source.json` e `python-mcp-parity.json`. Aquisição, cópias e cadastros da demo
foram removidos após a execução; mídias/transcrições/frames não foram persistidos.
A fonte foi conferida externamente contra os IDs da coorte antes do download.
O utilitário genérico `demo_m1` não verifica pertencimento por fingerprint: cabe
ao operador fornecer mídia fora da avaliação. A declaração antiga de teste fechado
no primeiro relatório é sustentada por essa conferência específica; o utilitário
atual declara apenas que não usa rótulos nem calcula métricas de avaliação.

A revisão independente verificou contrato, proteção dos arquivos, processo,
compatibilidade, estados e ranking sem encontrar defeitos acionáveis; também
conferiu a consistência da demo e suas limitações. Nenhum rótulo do teste foi
consultado pela integração, nem houve previsão/avaliação de suas referências.
Baseline, bundle de M1, evidências e fontes offline congeladas foram preservados.

O controle adicional com vídeo gerado **sem trilha de áudio** também passou com
pesos reais pela função e MCP: `no_audio_stream`, previsão/faixa indisponíveis por
`unsupported_text_status`, sem fallback e com resposta idêntica. A sessão foi
removida. Evidência: `no-audio-parity.json` no mesmo diretório privado.

Dois probes assíncronos sob o sandbox de execução ficaram aguardando no event
loop; foram encerrados e limpos. O ensaio foi repetido com IPC local liberado,
como na demonstração positiva. Isso descreve o ambiente de execução, sem alterar
o extrator/modelo ou recorrer à rede para processar os vídeos.

`integration-verification.json` registra **30 arquivos congelados inalterados**:
16 do pacote ampliado, quatro do piloto anterior, seis do bundle offline de M1 e
quatro fontes offline congeladas. Zero sessões temporárias restantes. Os JSONs
finais e o utilitário de reprodução ficam separados dos pesos, sem versionar mídia,
dados privados ou rótulos. Não houve B/C, Ridge, SHAP, LangGraph ou chamada NIM.

**311 testes públicos passaram**, incluindo baseline padrão/sintético/observado,
entradas, compatibilidade, ausências/falhas, limpeza, schemas, CLI, ranking e
MCP stdio. Ruff, formatação dos 60 arquivos Python, lock offline e compatibilidade
das 130 dependências instaladas passaram. Testes simulados exercitam ordenação
sem empates; as demonstrações documentadas acima usam os pesos reais.

Commits lógicos: `574cd28` (extração isolada com testes) e `0fc788b` (função/CLI/MCP,
contratos, ranking, compatibilidade e testes), seguidos da demo e deste registro.
O percurso técnico da #3 está implementado localmente. A issue remota não foi
encerrada e a interpretação/explicação pelo aluno continua pendente. A avaliação
final e o diagnóstico temporal pertencem à #6; cobertura e qualidade permanecem
exploratórias.

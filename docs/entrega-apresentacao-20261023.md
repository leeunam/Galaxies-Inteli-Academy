# iSee — recorte para apresentação (23/10/2026)

Este guia organiza o que pode ser demonstrado e dito hoje. O recorte autorizado para entrega até 15h40 estabiliza o A200 servido e a demonstração MCP, reaproveita resultados já preservados e mantém explícitas as etapas científicas abertas. Ele não representa conclusão de 100% do projeto.

## O que a entrega mostra

- **A200 servido:** percurso atual de previsão com CatBoost, quantis, SHAP e comparáveis. A demonstração de apresentação não retreina nem executa ML.
- **MCP:** há um percurso ao vivo com dados inventados para mostrar a integração técnica. Ele não comprova qualidade preditiva ou aderência a uma campanha real.
- **Resultado salvo:** o comando `resultado` consulta somente a projeção pública de três previsões preservadas. Não lê features ou arquivos privados, não extrai features e não calcula previsões de novo.
- **Comparação de modelos:** A300, B-cache e C-cache podem ser apresentados nos resultados já calculados sobre 66 itens de validação e 37 canais. São métricas de validação usadas no processo de seleção, não um teste independente nem uma medida de desempenho em campanhas pagas.

Os 300 registros da base ampliada são uma referência do recorte estudado; esse tamanho, por si só, não prova um mínimo necessário para treinar. Os ganhos observados variam entre setores e métricas. Os cinco casos fixos de alto alcance continuam subestimados pelos modelos comparados; isso descreve esse recorte pequeno, não uma estimativa geral de viralidade. Veja [a comparação de B-cache](issue-4-experimento-b-resultados.md), [a comparação de C-cache](issue-4-experimento-c-cache-resultados.md) e [a expansão da base](issue-3-expansao-300-resultados.md).

## Cadastro e retenção de mídia

O cadastro local registra o caminho relativo e metadados técnicos do arquivo original em `uploads/`. O registro não copia o original para uma área temporária e o fluxo não o apaga automaticamente ao terminar uma análise; a retenção e a remoção desse arquivo continuam sob responsabilidade de quem opera o cadastro.

Quando a extração precisa de uma cópia temporária, o worker gerenciado a mantém em um diretório exclusivo e a remove depois que os processos encerram. Timeout e cancelamento solicitam o encerramento e a limpeza, com confirmação antes de declarar sucesso. Se o supervisor ou a máquina cair antes dessa confirmação, o diretório pode permanecer para recuperação por lease; portanto, não se deve prometer eliminação instantânea e completa em qualquer falha abrupta. Esses comportamentos estão no [cadastro](../scripts/creative_registry.py), na [extração de atributos](../scripts/candidate_features.py) e no [serviço do grafo](../scripts/explanation_graph_service_v2.py).

## Texto para os slides

### Limitações — três colunas

**Qualidade visual**

- Atributos visuais ainda não aprovados.
- Extração qualitativa segue inconclusiva.

**Validação**

- Exploratória: 66 itens, 37 canais.
- Holdout de 31 casos permanece fechado.
- Sem desempenho de campanha paga medido.

**Cobertura do fluxo**

- B/C-cache foram comparados; B/C completos com VLM continuam pendentes.
- Explicador remoto real ainda não foi validado.

Não atribuir os resultados visuais a um conjunto específico de modelos sem gate. A rodada que encerrou sem timeout resolveu um aspecto operacional; o positivo conhecido ainda recebeu `unknown`, então isso não equivale a aprovação de qualidade. Os resultados de B-cache também não isolam a contribuição de cada sinal visual.

### Próximos passos — quatro caixas

1. **Validar atributos visuais** e concluir a representação completa de B/C.
2. **Fechar configuração e explicações reais**, depois executar teste temporal e holdout conforme autorização e protocolo.
3. **Obter base autorizada** e medir campanhas; planejar integração com a Galaxies.
4. **Evoluir interface e novos setores** após validar o recorte atual.

Se o espaço do slide exigir menos texto, preservar na fala que a validação atual é exploratória, o holdout segue fechado, B/C completos dependem de atributos visuais aprovados e configuração/explicação reais continuam pendentes. A integração com a Galaxies e a expansão de setores vêm depois da validação do recorte.

## Roteiro de terminal

Na raiz do clone, com dependências locais instaladas, os três comandos da fachada de apresentação são:

```bash
rtk proxy .venv/bin/python -B -m scripts.apresentacao mcp
rtk proxy .venv/bin/python -B -m scripts.apresentacao resultado
rtk proxy .venv/bin/python -B -m scripts.apresentacao metricas
```

`mcp` inicia a demonstração MCP ao vivo com entradas inventadas. `resultado` consulta a projeção pública de três previsões preservadas; não lê as features que deram origem a elas. `metricas` exibe agregados existentes da validação de 66 itens/37 canais para A300, B-cache e C-cache. Nenhum desses leitores deve ser descrito como treino, extração nova ou avaliação no holdout. O checkpoint técnico local do integrador em 23/10, sobre `4a02058`, registrou 62 testes do núcleo inalterado `8058cb5` em 22,75 s, cinco testes novos em 0,06 s e os três comandos com código de saída 0. O MCP concluiu seis análises com dados inventados; restaram zero diretórios temporários `isee-apresentacao-*`. Esse checkpoint não é uma reprodução atual nem avaliação científica: sem nova extração, ML, NIM ou holdout; A200 permanece servido, B/C-cache são resultados de validação e V7 fica fora deste aceite.

Registro documental deste acabamento: **23/10/2026, 15:04:38 de São Paulo (UTC−03:00)**, convertido do relógio UTC com `ZoneInfo("America/Sao_Paulo")`. As verificações direcionadas deste delta são registradas separadamente pelo integrador.

Para usar o clone público, primeiro instale as dependências indicadas no [README](../README.md). Mídias, bundles e coortes privadas não acompanham o clone; assim, a fachada pública e seus dados inventados funcionam offline depois que as dependências estão preparadas, enquanto percursos de análise com dados reais precisam dos recursos locais autorizados.

## Três evidências distintas

**Consulta atual do comando `resultado`.** Lê somente uma projeção pública de três previsões preservadas. Não acessa arquivos privados, não lê features, não faz extração ou previsão e não executa MCP ou StateGraph. É uma consulta ao snapshot, não uma nova demonstração nativa com as três mídias.

**Cálculo cacheado de 23/10.** Em outro percurso, três casos reais de validação passaram por M1/A200, SHAP, comparáveis de treino e apresentação local, começando em features reais já preservadas. Foram calculadas saídas numéricas novas, sem abrir vídeos ou executar extração; esse ensaio não executou MCP nem StateGraph. O [checkpoint de 23/10](entrega-20261021.md) documenta esse cálculo.

**Par nativo Python/MCP v6.** A prova nativa independente executou três extrações e três previsões em cada rota, incluindo StateGraph, SHAP e comparáveis; as respostas completas coincidiram nas condições daquele par. Consulte o [resultado do par v6](issue-5-paridade-independente-resultados.md). A divergência de 22 campos pertence a uma comparação histórica anterior e permanece registrada separadamente no [relatório antigo](issue-5-demo-local-python-mcp-resultado.md); a prova posterior não apaga esse histórico nem determina a causa antiga.

Essas provas descrevem percursos diferentes. O comando `resultado` não herda as etapas nativas do par v6, e o cálculo cacheado de 23/10 não foi uma execução Python/MCP.

O recorte mantém o teste de 31 casos fechado, não promove B/C completos, não aprova atributos VLM e não mede retorno de mídia paga. Consulte a [matriz de fechamento](fechamento-20261023.md) e o [guia de evidências existente](entrega-20261021.md) para a trilha completa.

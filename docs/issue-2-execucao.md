# Executar o protótipo da issue #2

O protótipo implementa contratos, cadastro seguro e análise pela função Python e pelo
FastMCP 4.1.0 via stdio. Não há baseline treinado, previsão, faixa ou ranking reais.
A [definição do contrato](issue-2-contrato.md) detalha limites e estados.

## Ambiente e demonstração

Na raiz do projeto, em Linux/POSIX, com Python 3.11 e uv instalados:

```bash
rtk proxy uv sync --frozen
rtk proxy uv run --frozen python -m scripts.demo_creatives
```

A demonstração gera cinco vídeos verticais vazios, de 0,2 segundo, em um diretório
temporário. Cadastra os arquivos, executa análises com um, dois e cinco IDs e verifica
igualdade integral entre Python e cliente MCP stdio real, lançado em outro processo.
Ao encerrar normalmente, remove mídias e cadastro temporários. Não precisa de `.env`,
credenciais, pesos de ML, conteúdo real ou chamadas de inferência externa. Após a
instalação das dependências, a demonstração é local e não acessa rede.

Resultado esperado: `fixture=synthetic`, `scientific_evaluation=pending`, três resultados
com `python_stdio_equal=true` e `status=prediction_unavailable`. Há um modo `individual`
e dois `comparative`. Os IDs mudam a cada execução; não são rótulos de desempenho.

Verificações:

```bash
rtk proxy uv run --frozen pytest -q
rtk proxy uv run --frozen ruff check scripts tests
rtk proxy uv run --frozen ruff format --check scripts tests
rtk proxy uv lock --check
rtk proxy uv pip check
```

Os testes usam arquivos gerados e não dependem de dados privados. O teste de transporte
usa o SDK como cliente real; outro teste inspeciona cada linha do stdout do servidor
como JSON-RPC. Diagnósticos ficam no stderr, separado do protocolo. O cliente não
encaminha chaves do ambiente ao servidor; o decodificador também recebe ambiente mínimo.

## Cadastro local e função Python

Para usar arquivo próprio ou licenciado já autorizado, coloque-o em `uploads/` e
cadastre-o localmente. O cadastro não é uma ferramenta disponível ao host MCP:

```bash
rtk proxy uv run --frozen python -m scripts.creative_cli register --campaign-id demo --sector moda --relative-path meu-criativo.mp4
```

O retorno contém `status=registered` e `creative_id`. A pasta `uploads/` e o registro
`data/private/creative-registry.json` são ignorados pelo Git. A mídia não é copiada
nem apagada pelo cadastro. Os arquivos permanecem até remoção explícita pelo operador;
para descartar esta versão do cadastro, remova o arquivo de mídia e seu registro privado.
O protótipo não cria transcrições ou caches de extração. Não promete apagar respostas
eventualmente mantidas por um host MCP. Não usar material confidencial sem verificar
as condições do host, que recebe os resultados da ferramenta.

A função e o registro podem ser usados diretamente:

```python
from pathlib import Path

from scripts.creative_analysis import analyze_creatives
from scripts.creative_registry import CreativeRegistry

registry = CreativeRegistry(
    Path("uploads"),
    Path("data/private/creative-registry.json"),
)
request = {
    "campaign_id": "demo",
    "creative_ids": [creative_id],  # ID retornado pelo cadastro local.
    "sector": "moda",
    "objective": "divulgacao",
    "brief": "Apresentar a coleção de verão.",
}
response = analyze_creatives(request, registry)
```

Também é possível salvar a solicitação acima como JSON em
`data/private/analysis-request.json` e executar:

```bash
rtk proxy uv run --frozen python -m scripts.creative_cli analyze --request-file data/private/analysis-request.json
```

Erros estruturados terminam a CLI com código 1; cadastro ou solicitação válidos
terminam com código 0. Uma análise válida com previsão indisponível retorna código 0:
indisponibilidade é um estado explícito, sem fabricação de números.

## MCP e esquemas

Para iniciar o servidor para um host compatível com stdio:

```bash
rtk proxy uv run --frozen python -m scripts.creative_mcp
```

Essa execução espera mensagens de protocolo no stdin; para ver a análise, use a
demonstração ou um cliente MCP. Configure o host com o caminho absoluto do Python em
`.venv/bin/python`, argumentos `-m scripts.creative_mcp` e diretório de trabalho na
raiz deste projeto. Não configure carregamento de `.env` nem encaminhe credenciais.
Se o host não aceitar diretório de trabalho, ele deve fornecer a raiz do projeto
como `PYTHONPATH`, usando apenas essa variável de configuração, sem chaves de API.

Há somente a tool `analyze_creatives`, com argumentos `{"payload": request}`. Os campos
internos de `request` são os mesmos da função. O esquema publicado anuncia tipos,
limites e campos obrigatórios; a validação estrita ocorre no serviço compartilhado
para devolver os mesmos erros fixos nos dois percursos. Envelope MCP inválido
(por exemplo, ausência de `payload`) é erro de protocolo, separado do contrato da análise.
O campo `structured_content` do resultado do cliente contém a resposta da aplicação.
O timeout da ferramenta é 160 segundos, para até cinco inspeções limitadas a 30 segundos;
o cliente da demonstração permite 180 segundos. Esses limites não são SLA medido.

O operador pode configurar `--uploads-root` e `--registry` tanto na CLI quanto no
servidor. Use os mesmos valores nos dois; são configurações locais de confiança,
não campos aceitos pela tool. A função não recebe caminhos fornecidos pelo host.

Os esquemas JSON podem ser exportados sem mídia ou configuração privada:

```bash
rtk proxy uv run --frozen python -m scripts.creative_cli schema analysis-input
rtk proxy uv run --frozen python -m scripts.creative_cli schema analysis-output
rtk proxy uv run --frozen python -m scripts.creative_cli schema registration-input
rtk proxy uv run --frozen python -m scripts.creative_cli schema registration-output
```

Fontes da integração: [transportes do cliente FastMCP](https://gofastmcp.com/clients/transports),
[tools](https://gofastmcp.com/servers/tools) e
[execução do servidor](https://gofastmcp.com/deployment/running-server).
As interfaces foram conferidas também na versão instalada e nos testes de integração.

## Evidências de conclusão em 18/10

### Extensão: partições, baseline e faixa sintéticos

As rotinas offline agora estão implementadas e documentadas em
[issue-2-baseline.md](issue-2-baseline.md). Para executar sem mídia ou dados privados:

```bash
rtk proxy uv run --frozen python -m scripts.demo_baseline
```

O resultado identifica `fixture=synthetic`, `scientific_status=pending_issue_1`
e `real_results_available=false`. A suíte atual tem **150 testes passando**,
incluindo controle de vazamento entre partições, estatísticas somente no treino,
persistência e indisponibilidade preservada pela função/MCP. Ruff e formatação
aprovados. A demo numérica é offline; o serviço não carrega esses artefatos.
Instalação pelo lock, 150 testes e essa demo foram reproduzidos em ambiente
temporário limpo usando o cache local, sem rede e sem copiar a `.venv` existente.

### Checkpoint inicial do cadastro e transporte

- Suíte completa: **103 testes passaram**, no ambiente de trabalho e em um novo
  ambiente temporário instalado com `uv sync --frozen`, sem copiar a `.venv` existente.
- Ruff e formatação de todos os arquivos de `scripts/` e `tests/` aprovados;
  `uv lock --check` e `uv pip check` aprovados.
- Demonstração no novo ambiente: um, dois e cinco candidatos, paridade Python/stdio
  verdadeira nos três casos e `prediction_unavailable` em todas as respostas.
- O teste limpo inicialmente offline não encontrou o wheel do PyTorch no cache;
  a reprodução completa foi concluída com download das dependências travadas.
  Instalação pode exigir rede; a demonstração, após instalada, não exige rede.
- Vídeos e registros da demonstração foram criados em área temporária e descartados
  ao encerrar. O `README.md` preexistente e não versionado foi preservado fora dos commits.

Essas evidências concluem a fatia de protótipo. Não concluem a issue #2 original,
que ainda exige partições por canal, baseline, faixa empírica e demonstração preditiva
com dados elegíveis dependentes da #1. Não houve coleta adicional, treino real ou NIM.

## O que explicar na apresentação

1. O cadastro valida arquivos e troca caminhos por IDs opacos; isso não treina um modelo.
2. O contrato separa entrada inválida de análise válida com capacidade indisponível.
3. O modo depende da quantidade de candidatos; MCP transporta o mesmo caso de uso.
4. Baseline seria calculado somente no treino elegível. Sem ele, `null` não é zero ou empate.
5. Partições por canal, baseline, faixa empírica, ranking e avaliação reais continuam
   dependentes da #1. Não foram demonstrados por estas fixtures.

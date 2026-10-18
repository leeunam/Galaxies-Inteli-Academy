# Contrato do protótipo da issue #2

**Estado atual:** [contrato observado `prototype-observed-v1`](issue-2-baseline-observado.md)
disponível por opção do operador, com B0 real do piloto, faixa setorial e empates.
Previsão aprendida e intervalo preditivo seguem indisponíveis. As seções abaixo
descrevem os modos anteriores preservados: padrão indisponível e sintético explícito.

Versão `prototype-v1`, 18/10/2026. Implementação local em Python 3.11, Linux/POSIX.
Esta entrega valida cadastro e integração; não implementa treino ou previsão real.
A issue original continua dependente da #1 para seus critérios científicos.

Extensão de 18/10: [rotinas offline de partição e baseline](issue-2-baseline.md)
estão implementadas com evidência sintética e contratos próprios de auditoria.
O modo padrão abaixo permanece `prototype-v1` e não carrega esses artefatos.
Uma extensão explícita `prototype-synthetic-v1` permite demonstrar B0 e faixa
setoriais inventados, sem habilitar previsão real.

## Cadastro e entrada

`CreativeRegistry(uploads_root, registry_file)` recebe duas localizações de confiança
definidas pelo operador. A pasta de mídia deve ser `uploads/`; o registro privado deve
ficar em `data/private/`. Não fornecer essas localizações pelo MCP.

`registry.register(payload)` aceita exatamente `campaign_id`, `sector` e `relative_path`.
O caminho é relativo à pasta permitida. O retorno contém um ID aleatório `cr_` seguido
de 32 caracteres hexadecimais, campanha e setor; nunca o caminho ou o hash do arquivo.
O registro persiste o vínculo e o hash SHA-256 em JSON privado, com escrita atômica,
permissão 0600 e trava local. Cópias do mesmo arquivo podem representar cadastros
distintos; IDs repetidos na mesma análise são proibidos.

`analyze_creatives(payload, registry)` aceita exatamente:

| Campo | Regra |
| --- | --- |
| `campaign_id` | 1–80 caracteres ASCII: letras, números, `_` ou `-`; deve coincidir com o cadastro |
| `creative_ids` | Lista de 1–5 IDs opacos distintos, com formato e existência verificados |
| `sector` | `moda` ou `beleza`; deve coincidir com todos os cadastros |
| `objective` | Somente `divulgacao` |
| `brief` | Texto obrigatório, 1–4.000 caracteres após retirar espaços nas extremidades |

Tipos são estritos, campos extras são recusados e métricas observadas não são entradas.
O brief é dado de contexto, sem execução de instruções e sem retorno ou logging do
texto. Um ID seleciona `individual`; dois a cinco selecionam `comparative`.

## Validação da mídia

O cadastro e cada análise verificam o arquivo. Somente arquivos regulares locais,
com extensão `.mp4`, `.mov` ou `.webm`, contêiner MP4/MOV ou Matroska/WebM e um fluxo
de vídeo decodificável são aceitos. A extensão sozinha não comprova o formato.
O protótipo não verifica idioma nem autorização automaticamente; usar apenas fixtures
sintéticas ou conteúdo próprio/licenciado já autorizado. Não chama extratores de ML.

Limites conservadores deste protótipo, sem promessa de escala ou SLA:

- Até 100 MiB por arquivo, duração positiva de até 60 segundos.
- Orientação vertical (`altura > largura`), até 1.080 × 1.920 pixels.
- Até 7.200 frames decodificados, sem mudança de resolução ou timestamps regressivos.
- Inspeção isolada por arquivo: 30 segundos de relógio, 25 segundos de CPU,
  1 GiB de espaço de endereçamento. Cinco arquivos podem consumir até cinco inspeções.

As dimensões são as codificadas; rotação em metadados não é aplicada. Fornecer mídia
já normalizada para vertical. O demuxer usa lista de protocolos restrita a `pipe`
e referências externas de MOV desabilitadas.

O acesso usa descritores com `O_NOFOLLOW` em cada componente relativo e recusa links
simbólicos, travessia por `..`, URLs e caminhos absolutos. FIFOs e outros arquivos
especiais são rejeitados antes da leitura. A configuração dos diretórios é de confiança;
não há garantia contra um administrador hostil alterando o sistema de arquivos.
O subprocesso de inspeção recebe somente ambiente mínimo, sem herdar chaves de API.
O hash e as propriedades são conferidos novamente na análise; alteração do arquivo
exige novo cadastro. Falha em qualquer candidato interrompe a solicitação inteira.

## Saída e indisponibilidade

Entradas inválidas retornam `status=error`, `schema_version` e um objeto `error`
com `code` e mensagem fixa. Códigos: `invalid_request`, `unknown_creative`,
`campaign_mismatch`, `sector_mismatch`, `unsafe_path`, `media_missing`, `invalid_media`,
`media_limits_exceeded`, `media_timeout`, `media_changed` e `registry_unavailable`.
Não serializar exceções, entradas inválidas ou caminhos nas mensagens.

Por padrão, uma solicitação válida retorna `status=prediction_unavailable`, modo, campanha, setor,
objetivo, definição proposta do alvo e candidatos na ordem de entrada. Essa lista
não é ranking. Cada candidato tem mídia validada, previsão e faixa indisponíveis.

- `baseline`: `unavailable`, motivo `eligible_training_data_missing`, `value=null`.
- Previsão: `unavailable`, motivo `usable_model_artifact_missing`, `value=null`.
- Faixa: `unavailable`, motivo `prediction_unavailable`, `value=null`.
- Ranking: `unavailable`, `value=null`; motivo `individual_analysis` para um candidato
  e `prediction_unavailable` para comparação.
- Versões de modelo/extrator: `null`; extração: `not_run`.
- Explicação: texto determinístico de indisponibilidade, sem chamada ao NIM.

Ausência de artefato é um estado esperado, não uma exceção ou um fallback numérico.
O protótipo não carrega artefatos nem possui caminho habilitado para previsão: colocar
um arquivo de modelo numa pasta não altera esses estados. O alvo de views públicas
observadas entre 30 e 37 dias permanece `proposed_not_validated`, sem reconstruir
views no dia 30, estimar retorno pago ou definir limiar de viralidade.

## Extensão sintética explícita

`analyze_creatives(payload, registry, synthetic_baseline=True)` ativa uma referência
inteiramente inventada. A opção é configuração booleana do operador Python; não é
campo da solicitação. O padrão é `False`, preservando a resposta anterior. Não há
carregamento de arquivos de modelo, rótulos privados ou artefatos externos nesse modo.

O gerador compartilhado com a demo offline cria 20 canais e 40 referências, separa
por canal e usa somente os rótulos de treino para calcular B0 e quantis. Os números
são os mesmos para todos os criativos do mesmo setor; IDs, mídia e brief não alteram
a referência. Bcanal continua restrito ao diagnóstico offline, sem canal na entrada.

A resposta tem `schema_version=prototype-synthetic-v1`,
`status=synthetic_baseline_available`, `data_kind=synthetic`,
`scientific_status=pending_issue_1` e `real_results_available=false`.
O objeto `baseline` contém `status=synthetic_baseline`, `variant=B0`, setor,
`central_views`, contagens de suporte e hashes do artefato e manifesto. Não publica
IDs de treino, canais ou rótulos individuais. `target_transform=log1p` e
`range_method=linear_quantiles_in_log1p` identificam o cálculo existente.

`baseline.sector_range` contém `lower_views`, `sector_median_views`, `upper_views`,
quantis 0,1/0,9, `kind=empirical_training_sector_range` e
`coverage_status=not_evaluated`. Essa faixa descreve o treino sintético por setor;
não é intervalo preditivo individual nem promessa de cobertura de 80%.

Os campos `candidates[].prediction`, `candidates[].interval` e `ranking` continuam
`unavailable`, com `value=null`. Versões de modelo/extrator continuam `null`,
extração `not_run` e alvo `proposed_not_validated`. A explicação informa a origem
inventada e a dependência da #1; nenhum criativo é recomendado. Erros, validação
de mídia e isolamento de campanha/setor continuam idênticos nos dois modos.

## Verificação da primeira unidade

Testes cobrem entradas, ausência de resultados fabricados, persistência, isolamento
entre campanhas/setores, arquivos alterados, caminhos, links simbólicos, tipo real,
duração, orientação, tamanho, FIFO, timeout e falha do decodificador. Fixtures são
vídeos gerados sem conteúdo real. As verificações não demonstram percepção,
generalização, validade dos dados ou qualidade preditiva.

# Manifesto e liberação operacional do treino

O módulo `scripts/training_manifest.py` valida referências e evidências locais
antes de entregar entradas para o experimento A da #3. Metadados, uma aquisição
bem-sucedida ou JSON válido do VLM não bastam para liberar o treino.

## Contrato e separação dos dados

`TrainingReference` registra a origem canônica do YouTube, setor, canal, instantes
de publicação/observação, views inteiras não negativas, licença declarada,
autorização operacional e seu hash de evidência, propriedades medidas,
procedência da curadoria e hashes dos artefatos/configuração. A observação é
vinculada à identidade, datas e contagem congeladas por checksum. Campos ausentes,
coerções de contagens, datas sem fuso, idade fora de `30 <= dias < 37`, duração
fora de até 60 s, imagem não vertical e idioma não estabelecido são recusados.

`media_sha256` identifica a referência no manifesto de partições congelado;
`acquired_media_sha256` identifica a aquisição usada na extração. A separação
preserva a divisão anterior sem alegar igualdade de bytes de duas aquisições.
Não se conclui ausência de edições. Duplicatas exatas reconhecidas na nova
aquisição não podem atravessar partições; republicações editadas permanecem uma
limitação explícita.

A autorização registrada é a instrução expressa do operador para extração local
e treino. Ela não se torna aprovação do YouTube ou licença concedida pelo autor:
`platform_approval_verified=false` e o aditivo continua não enviado. Os hashes
atestam consistência dos registros, sem autenticar direitos ou correção semântica.
Não é exigida nova aprovação para executar o escopo já autorizado pelo aluno.

`validate_feature_evidence` recebe os bytes originais dos JSONs de features/execução
e a configuração. Confere hashes, fonte/contagem/datas, limpeza da sessão,
fingerprint adquirido, dimensões/duração e revisões dos modelos. Exige a nova
política de ASR sem idioma forçado e os parâmetros congelados. Não mistura
silenciosamente a versão anterior `pilot-features-v3` com a nova extração.

`PredictorInputs` expõe somente setor, duração, proporção altura/largura, estado
do texto e embedding MiniLM de 384 dimensões. Canal, datas, URL, título, views,
curtidas e hashes não entram no preditor. Embedding ausente é nulo com motivo;
texto inventado a partir de título/OCR não preenche a ausência.

Largura/altura brutas ficam apenas na auditoria: referências são adquiridas com
limite de resolução do downloader, enquanto inéditos podem chegar em resolução
maior. Usar a proporção evita apresentar a resolução da cópia adquirida como
propriedade comparável do original. Um teste verifica entradas iguais para
720×1280 e 1080×1920, mantendo o conteúdo/texto e a duração iguais.

## Checagem da coorte

`readiness(records)` nunca libera treino apenas com metadados, mesmo ao receber
duzentas linhas. `import_training_manifest(records, evidence_by_id, config,
partitions=manifest)` valida as evidências de **todos** os IDs e a correspondência
com as partições congeladas. O algoritmo de divisão é revalidado pelo contrato
existente; nenhum rótulo entra na construção das partições.

A liberação padrão exige o piso combinado de **200 referências e 50 canais**,
ambos os setores, features verificadas e partições compatíveis. É uma condição
operacional para iniciar o experimento, não prova de suficiência estatística ou
qualidade preditiva. `predictive_quality_validated=false` continua obrigatório.
Um eventual piloto abaixo do piso exige decisão explícita de escopo; não há
redução silenciosa do acordo para transformar doze linhas em base completa.

Os rótulos continuam separados de `PredictorInputs`; a #3 deverá selecionar
somente os IDs de treino para ajustar modelos/transformações. A conferência de
integridade de uma observação não autoriza usar seu resultado na escolha do modelo.
Validação/teste não são convertidos em histórico de canal nem em atributos.

## Curadoria assistida

O aluno solicitou usar as ferramentas em lugar da conferência humana dos quatro
casos amostrados. A nova revisão é identificada como `automated_assisted_review`;
nenhum resultado foi marcado como nova escuta ou anotação humana.

`scripts/curation_audit.py` oferece uma classificação visual estreita com Qwen,
categorias fechadas, índices reais de frames e abstenção. Preserva a saída bruta,
inclusive quando inválida, e mantém `automatic_training_release_allowed=false`.
Setor sugerido ou esquema correto não aprovam a percepção. Decisões assistidas
dos frames e da fala são registradas separadamente, sem alterar a resposta original.

Nos quatro controles da retomada:

- Caso 6: imagens confirmam roupas, mas não foi estabelecida fala pt-BR; exclusão
  por idioma mantida. Saída estreita inválida do Qwen não foi aproveitada.
- Caso 12: roupas e narração de combinações sustentam moda; a sugestão de
  organizador do classificador estreito foi rejeitada por contradição com a evidência.
- Caso 13: organizador demonstrado e narrado; exclusão de acessório de armazenamento
  confirmada, apesar dos cosméticos próximos.
- Caso 18: cosméticos mostrados e narrados sustentam beleza. A classificação estreita
  concluiu; a geração completa de atributos falhou e permaneceu indisponível.

Dois controles novos concluíram o percurso ASR/MiniLM/CLIP/Qwen com esquema completo;
um terceiro preservou ASR/embeddings e a falha visual explícita. Close-up/aplicação
continuam bloqueados globalmente e nenhuma coluna VLM foi aprovada para treino.
O experimento A não usa essas colunas. Os frames temporários desses controles foram
removidos após a revisão; evidências estruturadas, transcrições necessárias e hashes
permanecem privados. Não se estima acurácia populacional com esses exemplos.

Na ampliação, três transcrições apresentaram repetição severa de uma palavra.
Os casos foram excluídos do treino por qualidade do texto; transcrições/embeddings
brutos foram preservados. Um diagnóstico de
repetições consecutivas foi aplicado aos artefatos disponíveis, sem inventar texto,
truncar respostas depois da extração ou chamar esse controle de medida de acurácia.
A fala continua sujeita a erros; ASR operacional não significa transcrição perfeita.

## Teste sintético do NIM

O modelo escolhido permanece `nvidia/nemotron-3-nano-omni-30b-a3b-reasoning` no
mesmo endpoint. As tentativas mostraram tanto HTTP 503 quanto gerações com erro de
estrutura ou interpretação não sustentada. Essas respostas foram preservadas e
rejeitadas, sem corrigir números ou narrativa depois da geração.

O teste corrigido usa JSON Schema, validação Python independente e saída limitada
à cópia literal de evidências sintéticas permitidas. A NVIDIA documenta
[geração estruturada](https://docs.nvidia.com/nim/vision-language-models/1.4.1/structured-generation.html);
o suporte efetivo foi conferido nas chamadas, sem pressupor comportamento uniforme
entre modelos/endpoints. Os dois casos, normal e com instrução maliciosa no brief,
retornaram HTTP 200, preservaram IDs/números/ordem e passaram na revisão assistida
de português/fidelidade. Dez controles offline do validador também passaram.

Isso valida **somente a fronteira sintética restrita de cópia de evidências**.
Não valida explicação livre, raciocínio, SHAP, qualidade de previsões ou operação
com dados confidenciais. A #5 permanece pendente. Nenhuma mídia, transcrição ou
métrica real foi enviada ao NIM; credenciais não integram os artefatos.

## Evidência local e execução

**A coorte ampliada atingiu 200 referências/80 canais** e passou na reimportação
das evidências reais, com `training_release_available=true`. As partições congeladas
têm 124 referências no treino, 45 na validação e 31 no teste; o baseline usa somente
os 124 IDs de treino. M1 não foi ajustado e não houve avaliação do holdout.
[Relatório, hashes e reprodução](issue-1-base-para-experimento-a.md).

O piloto anterior de doze referências passou no importador com as partições da #2
preservadas; seu relatório histórico permanece bloqueado pelo piso 200/50 e não
foi sobrescrito. Artefatos desse piloto estão em
`data/private/issue-1-extratores-20261018-v2/imported-manifest-v3/`.
A auditoria dos quatro casos fica em
`data/private/issue-1-revisao-assistida-final-20261018/`; os testes NIM, em
`data/private/technical-probes-20261018/nim-retomada-issue1-copy/`.

A ampliação foi acompanhada por checkpoints privados: fonte congelada, um worker,
mesma extração cacheada, limite de execução, parada em autenticação/403/429 ou
limpeza incerta, sem promover candidatos por idioma declarado/título. Os vídeos
são descartados por sessão; frames de revisão são temporários até a decisão assistida.
A fila final encerrou normalmente, com 541 tentativas revisadas e limpeza confirmada;
nenhuma mídia bruta ou imagem temporária de revisão da ampliação permaneceu.

A ampliação foi organizada em etapas antes de qualquer ajuste supervisionado. A
primeira percorreu canais com evidência de português ou declaração na API; a etapa
seguinte priorizou canais com conteúdo já incluído na curadoria assistida e acrescentou
buscas e playlists de uploads, incluindo novas propostas por termos em português.
As seleções e checkpoints anteriores foram preservados,
com reuso somente de artefatos cuja fonte/configuração coincide. Não há ordenação
por views, atualização de rótulo nem mudança das partições antigas da #2.

Essa seleção adapta a aquisição à confirmação de conteúdo: é **amostra de
conveniência**, com viés de descoberta/canal. Não é sorteio probabilístico, medida
da distribuição da plataforma ou justificativa para chamar o teste de avaliação
prospectiva independente. O teto final é cinco referências por canal; setor e
limites de idade/duração/idioma continuam iguais. A divisão da coorte ampliada só
foi congelada depois da curadoria e antes do primeiro ajuste do baseline.

Testes locais não precisam da base privada:

```bash
rtk proxy uv run --frozen pytest -q
rtk proxy uv run --frozen ruff check scripts tests
rtk proxy uv run --frozen ruff format --check scripts tests
```

A suíte integrada passou em 250 testes. As checagens cobrem recorte, contagem original, evidência alterada,
revisões incompatíveis, ausência de texto, proibição de outcomes nas entradas,
necessidade de partições/volume e abstenção do classificador visual. Controles
adicionais recusam duplicata adquirida atravessando partições antigas, metadados
de partição divergentes, revisões de modelo trocadas e IDs extras de evidência.

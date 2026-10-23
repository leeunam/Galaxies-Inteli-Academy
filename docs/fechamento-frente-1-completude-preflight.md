# Preflight aditivo de pré-requisitos da Frente 1

`scripts/front1_completion_preflight.py` verifica coerência estrutural de um
pacote de metadados fornecido explicitamente. O pacote deve seguir a versão
`front1-completion-prerequisites-v1`. A ferramenta é independente de treino e
inferência e não abre sidecars, dados de vídeo, caches ou artefatos científicos.

O pacote declara a lista canônica completa de sete campos em
`scripts.visual_attributes.FIELDS`; `released_fields` também deve seguir essa
ordem e conter os sete campos para o status `prerequisites_present`. Compara
IDs ordenados e únicos das partições 203/66, e exige que os 269 registros de
sidecar cubram exatamente sua união, cada qual na partição correspondente.
Cada sidecar declara setor, canal, hashes de features e execução e identidades
de coorte, partição, configuração, candidata e liberação. Os 32 registros de
auditoria devem vir de treino, com 16 por setor e 32 canais distintos; cada
linha liga sample, setor, canal e hash de features ao sidecar daquele mesmo ID.

Hashes de `audit_sha256` e `annotations_sha256` são SHA-256 de JSON UTF-8
canônico: chaves ordenadas, sem espaços (`separators=(",", ":")`) e
`ensure_ascii=False`. O recibo declara três identificadores distintos de
criador, anotador e revisor, a ordem temporal de selo, revelação e revisão, e
vincula hashes de coorte, partições, configuração, candidata, liberação,
plano, auditoria, anotações, seleção, exclusões, previsões de auditoria e gate.
Esses valores são alegações de metadados e não autenticam pessoas, origem,
ordem de eventos, seleção, anotação ou conteúdo. A revisão externa permanece
obrigatória.

Uso, apenas com um pacote metadata explicitamente aprovado para leitura:

```sh
python -B -m scripts.front1_completion_preflight --package /caminho/pacote.json
```

A CLI limita a entrada a 2 MiB e imprime somente JSON em stdout. Não recebe um
caminho de saída e não cria arquivos. Erros usam códigos estáticos e não
reproduzem valores ou caminhos fornecidos. A API
`evaluate_completion_prerequisites(package)` devolve `blocked` ou
`prerequisites_present`, junto de campos ausentes e bloqueios.

Em qualquer resultado, `quality_accepted`, `quality_release_emitted`,
`native_execution_authorized`, `holdout_authorized`,
`independent_origin_verified` e `front1_complete` são sempre `false`. Portanto,
`prerequisites_present` significa apenas coerência da declaração recebida; não
é uma liberação para percepção, extração, treino, uso de holdout ou conclusão
da Frente 1. A ferramenta não altera contratos de QualityRelease existentes.

Os testes `tests/test_front1_completion_preflight.py` usam exclusivamente
metadados sintéticos e subprocesso local da CLI. Eles não leem dados de
projeto, não autenticam recibos e não substituem gates perceptivos ou revisão
humana independente.

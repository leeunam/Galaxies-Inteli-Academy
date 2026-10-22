# Preparação limitada da validação visual — offline

Base `e97f827`, vinculada ao [plano inativo](issue-4-native225-next-validation-v1.md)
e ao seu manifesto original. Esta unidade não altera a proposta de até 397
chamadas e 11 horas, não cria reserva ou fila de execução e não recebe aprovação.
O [recibo sanitizado](evidence/issue-4-native225-adapter-preparation-v1.json)
registra fontes e testes. O negativo real anterior continua sendo um único caso.

## Componentes entregues

- [Contrato](../scripts/visual_validation_contract_v1.py): JSON limitado/estrito,
  digests, caminhos sem symlinks e gravação privada exclusiva com fsync. Confere
  a identidade da proposta histórica sem convertê-la em autorização.
- [Seleção](../scripts/visual_validation_selection_v1.py): recebe exclusivamente
  uma projeção com 203 linhas de treino, sem outcomes. Recusa arquivo misto,
  partição reservada, extras, IDs duplicados ou frames inconsistentes. Aplica
  a ordem por hash da rubrica, exclusões por ID/canal/mídia e 16 casos por setor
  com 32 canais distintos; insuficiência encerra sem reposição. O número exato
  de chamadas é derivado dos frames selecionados. Nenhuma seleção real foi feita.
- [Anotações](../scripts/visual_validation_annotations_v1.py): pacote separado
  contém só aliases, tempos e hashes dos frames, sem fonte, setor, canal, views,
  expectativas ou previsões. O template deixa rótulos e testemunhas por preencher.
  O selo exige todos os frames, valores e testemunhas válidos e ledger com zero
  reservas e zero saídas da auditoria. Declarações nativas são verificadas contra
  o domínio congelado; notas vinculam a testemunha à instância no mesmo frame.
- [Captura limitada](../scripts/visual_validation_capture_v1.py): novo namespace
  por chamada, limite de índice 397, até 75 segundos úteis, stdout de 16 KiB e
  stderr de 256 KiB. Reutiliza o owner, lease, streams e limpeza congelados; não
  cria um segundo dono do processo. Guarda prefixo e terminal antes de retornar.
  Parsers explícitos para pessoa, produto state_first, texto e relação recusam
  prefixos, sufixos, duplicatas e não finitos. O decoder antigo só é substituído
  para o contrato selecionado, mantendo falhas de runtime/encoder e recursos.
- [Sidecar versionado](../scripts/visual_validation_sidecar_v1.py): verifica cada
  captura, identidade do frame, tipo, tokens esperados e hashes. Mantém agregação
  temporal e declarações nativas com suporte ainda não revisado. Sempre grava
  `approved_for_training=false`, `released_fields=[]`, sem QualityRelease.

## Bloqueios reais do despacho

`DISPATCH_RELEASED=False`. A entrada pública recusa falta de autorização ou
revisão antes de criar caminhos ou chamar callback. Mesmo alterar somente essa
constante não basta: a entrada também exige a futura ativação do controlador
nativo. Não há CLI, launcher padrão, gerador de aprovação ou abertura de conta.
O helper testado usa somente launcher injetado; seus artefatos levam
`capture_origin=injected_unreleased` e `native_execution_verified=false`,
sem disfarçar filhos inventados como observação real.

**O executor de lote nativo ainda não está entregue.** Antes de ativar, deve
vincular os recibos humanos e técnicos, fontes/ativos/raiz, prazo de uso dos
inputs, cápsula corrigida e memória mínima à contabilidade única de 397 chamadas
e 39.600 segundos. O índice máximo do helper não substitui esse ledger. Para
a etapa cega, também deve exigir o compromisso das anotações e a revisão das
exclusões antes do primeiro despacho. São tarefas técnicas offline cobertas;
esta preparação não solicita outra permissão para implementá-las.

A captura mantém o corte RSS cooperativo de 3,3 GiB do owner, com suas limitações
de amostragem. Não entrega cgroup exclusivo ou garantia física absoluta de RAM.
Cancelamento durante o fsync terminal impede o chamador de avançar, conservando
o resultado já selado e a limpeza. Falha de persistência preserva o marcador,
sem reentrada automática. A ativação real continua bloqueada por revisão e
autorização, independente da aprovação de testes.

## Cegamento, papéis e dados ainda necessários

O módulo de sidecar não abre arquivos de anotações. Somente o compromisso sem
rótulos deve chegar ao executor. O revisor de métricas poderá juntar rótulos e
saídas depois que ambos estiverem selados, conforme a rubrica; isso não autoriza
mostrá-los ao modelo ou ao desenvolvedor antes da avaliação cega.

O protocolo vigente permite revisão visual assistida e exige papéis separados
e revisão independente; não exige que o usuário forneça 32 vídeos novos nem
inventa certificação humana. Registrar `declared_origin` não verifica a origem.
Se um procedimento exigir `human_required`, o mecanismo recusa `assisted` e
`synthetic`; uma declaração humana continua sem verificação automática.
Nenhuma anotação real, humana ou assistida foi produzida nesta unidade.

Ainda é preciso obter uma projeção segura só do treino e consolidar todas as
exclusões do histórico, sem abrir arquivos mistos com holdout. A suficiência
de 32 canais novos não foi verificada. Seleção real, aquisição autorizada,
anotador e revisor independente continuam pendentes; depois devem selar os
frames e as anotações antes de observar respostas. Não reamostrar por classe
rara, indisponibilidade ou falha. Os testes usam 203 linhas inteiramente inventadas.

## Verificação delimitada

Passaram **37 testes em 1,37 s**, Ruff e formatação de sete arquivos novos.
Cobrem seleção/reordenação/exclusões, recusa de outcomes e holdout, pacote sem
identidades, template não preenchido, anotação posterior às respostas, exigência
humana, origem sem certificação, testemunhas, selo exclusivo e metadados alterados;
quatro parsers, tokens errados, encoder incompleto, timeout, cancelamento inclusive
no fsync, limite de saída, raw adulterado, binding trocado e sidecar sem promoção.
Todos os filhos foram pequenos processos Python inventados, um por vez.

A primeira passagem parou em quatro avisos de lint, antes do pytest. Depois
passaram 33; a revisão acrescentou casos de cancelamento terminal/tipos (35)
e domínio de testemunhas (37). A seleção final de 37 foi repetida após a marca
de proveniência não liberada. São seleções sobrepostas, não uma soma de testes.
Recibos/JUnit privados novos preservam cada passagem.

As 14 fontes da proposta e os nove pins de cada rodada nativa anterior conferem.
Nenhum pixel real, outcome real, modelo ou encoder foi aberto/executado; não
houve inferência NVIDIA, aquisição, treino real ou abertura do holdout. A fila
de execução nova está ausente. M1, base, imagens, recibos selados e README alheio
ficam fora da alteração. B/C e avaliação final continuam bloqueados.

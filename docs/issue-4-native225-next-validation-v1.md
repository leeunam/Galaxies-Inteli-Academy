# Próxima validação visual: reconciliação após native225

Proposta offline baseada no [plano da Frente 1](issue-4-front1-visual-validation-plan-v1.md),
na [rubrica cega vigente](issue-4-front1-blind-audit-rubric-v1.md), no
[protocolo B-VLM](issue-4-experimento-b-vlm-protocolo.md) e no
[procedimento final](issue-6-protocolo-final-e-checklist-v1.md). Não reabre
filas anteriores nem altera base 300, partições 203/66/31 ou gates.

## Evidência disponível e seus limites

O [negativo nativo 225](issue-4-vlm-native225-renewed-once-v2-results.md) iniciou
e concluiu encoder/decode: 240 tokens, resposta `no`, 10,09 s, pico observado
de 2,56 GiB e limpeza confirmada. É um teste técnico e um acerto em caso
relacional revelado. Não mede sensibilidade em positivos, nem os três atributos
do extrator; não é auditoria cega. Sua autorização e renovação estão consumidas.

| Imagem ou fonte | Disponibilidade aferida por metadados | Uso futuro |
| --- | --- | --- |
| Oito folhas PNG protegidas | Presentes; 32 células já reveladas | Preservação vigente não libera novas inferências; excluí-las da auditoria cega |
| Dois nativos e seus derivados | 15 arquivos/cópias, quatro conteúdos distintos, todos revelados | Prazo original expirado; a renovação do negativo serviu só à execução concluída |
| Nativo positivo, SHA `238d3b775563fdffe47c3bfdce9c6623058642194f108107f58fcd9a10ae89e1` | Cópias locais presentes | Renovar somente para a chamada positiva proposta, sem download |
| Doze controles sintéticos originais | PNGs não persistidos; receitas, fonte tipográfica e pins locais disponíveis | Rematerializar exatamente a receita congelada, conferir hash e usar na triagem autorizada |
| Novos casos cegos | Nenhuma imagem elegível atual confirmada; casos ainda não selecionados | Até 32 reaquisições limitadas do treino existente, após seleção e autorização |

A preparação leu nomes, tamanhos e cabeçalhos PNG, sem abrir conteúdo visual.
Não pede 32 vídeos novos ao usuário e não complementa a base. Reusar um PNG
revelado ou outro arquivo dos mesmos canais não o torna cego.

## Candidata semântica congelada, executor ainda pendente

O [manifesto da proposta](evidence/issue-4-native225-next-validation-v1.json)
fixa prompts/schemas existentes: pessoa e texto de
`vlm_explicit_presence.specification()` e produto de
`vlm_product_v16.specification("state_first")`, sem retuning ou outra ordem.
A escolha de state_first usa apenas o desenvolvimento já revelado: V16 obteve
11/12 negativos, contra 0/12 em item_first; nenhuma foi aprovada. O novo teste
avaliaria a geometria 225, sem reinterpretar aquele resultado como aceite.

São três chamadas por frame, mesmas projeções e agregação temporal. Para a
auditoria, conservar células RGB 320 × 330 e `contact-sheet-cell-320x330-v1`,
compatíveis com o contrato B; não passar o nativo 360 × 640 como se fosse a mesma
política. Os nativos do par ficam restritos ao diagnóstico relacional. Essa
opção preserva os pixels das células, mas não recupera detalhe perdido na
folha histórica. Pessoa, produto e texto são as únicas colunas candidatas;
scene, format, close-up e aplicação continuam desconhecidos e não liberados.

Mesmo Qwen3-VL-2B Q4_K_M, projetor Q8_0 e b11716, com hashes herdados conferidos
pelo teste concluído; CPU com 4 threads, seed 42, temperatura 0, contexto 3072, saída de 64 e
min/max visual 225. Os prompts/schemas e suas fontes estão vinculados no JSON.
Não haverá braço de gramática, troca de modelo ou escolha após ver auditoria.

A previsão 960 patches/240 tokens foi confirmada no nativo 360 × 640. Não se
transfere essa observação a toda geometria. O futuro preflight aritmético deve
conferir resize/padding de cada entrada e a captura deve guardar tokens reais.
Um pico de 2,56 GiB deixa cerca de 0,74 GiB até o corte cooperativo de 3,3 GiB
nesse caso; não demonstra memória suficiente em outros prompts. Manter
MemAvailable ≥6 GiB antes de cada despacho, executor único e amostragem de 50 ms,
sem reduzir limiar, alterar swap ou prometer teto físico sem cgroup.

## Etapa de desenvolvimento: 13 chamadas novas

O painel da Frente 1 contém 14 decisões: 12 controles de produto mais o par
relacional negativo/positivo. Creditar somente o recibo do negativo já concluído
quando input, pergunta, pesos, schema, seed e geometria continuarem idênticos;
não chamar o mesmo negativo novamente. O crédito não é dado de treino.

Propor exatamente **13 chamadas novas**: os 12 controles na ordem original,
com contrato de produto state_first, e depois o nativo positivo com a mesma
pergunta relacional do par, esperado `yes`. Exigir 12/12 produto=false e a
decisão relacional positiva correta, além do negativo já registrado. Unknown
ou uncertain falham; não transformar o predicado relacional em gabarito do
atributo produto. Esse painel é desenvolvimento e não representa sozinho
a diversidade real de beleza/moda, pessoa ou texto.

Primeiro erro perceptivo ou falha técnica encerra a triagem, sem substituição,
reparo, retry ou saldo transferido. Teto **1.200 s globais**, zero aquisições.
Não gerar outra pergunta ou ajustar schema após o resultado para usar a
autorização condicional da auditoria.

## Auditoria realmente cega: somente se a triagem passar

Aplicar a rubrica vigente sem mudança: 32 referências do treino da base de 300,
16 por setor, 32 canais distintos. Excluir IDs, canais e hashes de mídia de
todo histórico revelado, incluindo o par recente. Usar a ordenação por hash
do protocolo existente. Suficiência dessa reserva ainda não foi verificada;
se faltar caso/canal elegível, parar sem completar com outro setor ou reamostrar.

Selar seleção, tempos, pixels esperados, candidato e papéis antes de inferir.
Anotador separado recebe frames/tempos sem saídas do candidato, views ou
ranking; sela valores e suporte por frame antes de comparar previsões. Usar
o procedimento de revisão assistida já definido, registrando sua limitação;
não alegar verdade certificada ou revisão humana inexistente. Revisão
independente confere exclusões, cegamento e proveniência.

**Teto exato de autorização: 384 chamadas** (32 × até 4 frames × 3 atributos). O
número executável exato será `3×soma(contagens de frames congeladas)` e deve
ser selado antes do primeiro despacho. Ainda não existe esse número, pois a
seleção não foi feita; não inventar quatro frames por caso nem usar o teto
como uma contagem concluída. Não haverá chamada extra para preencher cota.

Até32 aquisições, uma por referência, sem cookies, credenciais, proxy, nova
consulta de métricas ou troca de fonte. Exigir o SHA original da mídia e
também propriedades/pixels/PTS conforme B-VLM; a exceção anterior do par nativo
não relaxa a identidade da auditoria. Divergência ou indisponibilidade encerra.
As imagens recém-adquiridas só podem existir durante a revisão/rodada; descarte
apenas mídia/scratch próprios após quiescência, preservando recibos e PNGs antigos.

Gate original por coluna e setor: ≥12/16 conhecidos, ≥90% de acerto conjunto
valor+frames e zero evidência citada sem suporte. Booleanos precisam de ≥3
true e ≥3 false no total e pelo menos um de cada por setor. Falta de classe
reprova, sem nova amostra. Subdeclarações de categoria/configuração/relação
também exigem suporte no mesmo frame, conforme a rubrica existente.
Erro perceptivo é medido na auditoria completa; falha técnica, identidade,
raw inválido ou limpeza incerta interrompe sem retry e sem declarar32 avaliados.
Se nenhuma coluna passar, encerrar sem B-VLM.

## Pedido único de autorização, condicionado aos pré-requisitos

Proposta para encaminhar ao usuário, ainda sem autorização recebida:

> Autoriza uma rodada local em duas etapas: 13 novas inferências de triagem,
> renovando o uso do quadro positivo só para essa chamada, e, somente se a
> triagem e a revisão passarem sem mudar o candidato, uma auditoria cega de
> 32 referências do treino existente, com até 384 inferências e até 32
> reaquisições de uma tentativa cada? Teto total de 397 inferências novas,
> R$0, um processo por vez, sem NVIDIA ou envio externo para inferência, sem
> retries e sem holdout. Até80 s por inferência incluindo encerramento,
> 180 s por aquisição, MemAvailable≥6 GiB e corte RSS cooperativo de 3,3 GiB.
> Limite global de execução de 11 h; qualquer bloqueio previsto encerra a etapa.

Esse pedido evita consentimento por imagem ou comando. A revisão técnica e a
checagem da candidata/seleção continuam obrigatórias, sem pedir aprovação para
leituras públicas ou testes offline. Não autoriza usar negativos revelados
como cegos, reabrir saldos, enviar vídeos à NVIDIA, extração uniforme269, treino
B/C real, avaliação final, despesas ou publicação. Esses passos dependem dos
resultados e de seus próprios protocolos.

| Etapa | Quantidade máxima | Teto |
| --- | --- | --- |
| Desenvolvimento | 13 novas + 1 conclusão já preservada | 1.200 s |
| Auditoria | até 384 novas e até 32 aquisições | 38.400 s |
| Conjunto | até 397 novas / 32 aquisições | 39.600 s = 11 h |

O cálculo bruto é 397 × 80 + 32 × 180 = 37.520 s; a diferença até 39.600 s é margem
para preflight, registros e fechamento. Cada dispatch tem até75 s úteis + 5 s
de encerramento; mídia de 32 MiB por arquivo, workspace de 128 MiB, pelo menos 1 GiB de disco
livre, stdout de 16 KiB e stderr de 256 KiB. Tudo sequencial, cápsula sem rede na inferência
e `/dev` efêmero; acesso de rede só no invólucro de aquisição autorizado.
Contabilizar cumulativos anteriores e novos sem reutilizar as antigas 27 h.

Se todas as chamadas durassem os 10,09 s do único negativo, seriam cerca de67
minutos só de modelo. Isso é extrapolação condicional, não estimativa validada
para positivos, atributos ou 32 casos. Aquisição, anotação e revisão não foram
cronometradas aqui. O teto de 11 h não garante conclusão ou aprovação nessa duração.

## Integração com B/C e avaliação final

O diagnóstico está citado como evidência técnica; `released_fields=[]` e
`visual_audit_accepted=false` continuam explícitos no manifesto. Não preencher
`visual_audit_acceptance_receipt_sha256` da prontidão final com seu hash.

Seis regressões pequenas passaram em 1,04 s: o recibo de sucesso técnico do diagnóstico
é recusado em validação/treino B, encoding/treino C e gate final. O preflight
final continua exigindo revisão independente mesmo com hashes sintaticamente
válidos. Não foi necessário mudar as guardas existentes e nenhum alvo ou
fit real foi aberto. O relatório científico de prontidão original não mudou.

Antes de qualquer execução proposta, falta adaptar e testar o dispatcher
limitado da composição e o sidecar versionado; a saída relacional curta não
é um sidecar B. São trabalhos técnicos offline já cobertos, sem nova licença
para inferir. A seleção cega e as anotações também ainda não estão seladas.

Depois de auditoria aceita, B precisa de sidecars uniformes compatíveis nos
269 IDs de desenvolvimento e QualityRelease vinculado ao gate. C atualmente
é deliberadamente sintético; sua ponte real versionada ainda deve ser
implementada/testada mantendo mesmas linhas/features/splits. Não basta mudar
`data_kind` ou reaproveitar B-cache. P6 segue bloqueada até esses artefatos,
explicações/aderência e integração final aceitos; holdout de 31 permanece fechado.
